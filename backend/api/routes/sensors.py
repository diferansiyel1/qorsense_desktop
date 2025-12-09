"""
Sensor Management Routes - Multi-Tenant Secured

Handles sensor CRUD operations, data ingestion, and history retrieval.
Features streaming CSV import with Pydantic validation for industrial-grade data ingestion.

Security:
- All endpoints require authentication
- Row-level security: Users can only see/modify their organization's sensors
- Role-based access: DELETE requires ORG_ADMIN or SUPER_ADMIN
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, desc, func, delete
from backend.database import get_db, AsyncSessionLocal
from backend.models_db import Sensor, SensorReading, AnalysisResultDB, SourceType, Role, User
from backend.models import SensorCreate, SensorResponse, AnalysisResult, AnalysisMetrics
from backend.schemas.common import PaginationParams, PaginatedResponse
from backend.schemas.sensor import SensorReadingBulk, CSVImportResult
from backend.api.deps import (
    DbSession,
    CurrentUser,
    CurrentActiveUser,
    RoleChecker,
    get_current_active_user,
)
from datetime import datetime
import logging
import csv
import codecs
import uuid
import math

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sensors", tags=["Sensors"])


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

async def get_sensor_with_org_check(
    sensor_id: str,
    user: User,
    db: AsyncSession
) -> Sensor:
    """
    Get sensor by ID with organization ownership check.
    
    Args:
        sensor_id: Sensor ID to fetch
        user: Current authenticated user
        db: Database session
        
    Returns:
        Sensor object if found and user has access
        
    Raises:
        HTTPException 404: Sensor not found or not owned by user's organization
    """
    result = await db.execute(
        select(Sensor).where(Sensor.id == sensor_id)
    )
    sensor = result.scalar_one_or_none()
    
    if sensor is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensör bulunamadı: {sensor_id}"
        )
    
    # SUPER_ADMIN can access all
    if user.role == Role.SUPER_ADMIN:
        return sensor
    
    # Check organization membership
    if sensor.organization_id != user.organization_id:
        # Return 404 instead of 403 to not leak sensor existence
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Sensör bulunamadı: {sensor_id}"
        )
    
    return sensor


# ==============================================================================
# LIST / READ ENDPOINTS
# ==============================================================================

@router.get("", response_model=PaginatedResponse[SensorResponse])
async def get_sensors(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    List sensors with pagination - filtered by organization.
    
    Users can only see sensors belonging to their organization.
    SUPER_ADMIN can see all sensors.
    
    **Authentication**: Required
    """
    # Build base query with organization filter
    base_query = select(Sensor)
    count_query = select(func.count()).select_from(Sensor)
    
    # Apply org filter (SUPER_ADMIN sees all)
    if current_user.role != Role.SUPER_ADMIN:
        base_query = base_query.where(Sensor.organization_id == current_user.organization_id)
        count_query = count_query.where(Sensor.organization_id == current_user.organization_id)
    
    # Count total
    total = await db.scalar(count_query)
    
    # Get items with pagination
    stmt = base_query.offset((pagination.page - 1) * pagination.size).limit(pagination.size)
    result = await db.execute(stmt)
    sensors = result.scalars().all()
    
    sensor_responses = []
    for s in sensors:
        stmt = (
            select(AnalysisResultDB)
            .where(AnalysisResultDB.sensor_id == s.id)
            .order_by(desc(AnalysisResultDB.timestamp))
            .limit(1)
        )
        res = await db.execute(stmt)
        latest_analysis = res.scalar_one_or_none()
        
        response = SensorResponse(
            id=s.id,
            name=s.name,
            location=s.location,
            source_type=s.source_type,
            organization_id=s.organization_id,
            latest_health_score=latest_analysis.health_score if latest_analysis else 100.0,
            latest_status=latest_analysis.status if latest_analysis else "Normal",
            latest_analysis_timestamp=latest_analysis.timestamp if latest_analysis else None
        )
        sensor_responses.append(response)
    
    logger.info(f"User {current_user.email} listed {len(sensor_responses)} sensors")
    
    return PaginatedResponse(
        items=sensor_responses,
        total=total or 0,
        page=pagination.page,
        size=pagination.size,
        pages=math.ceil(total / pagination.size) if total else 0
    )


@router.get("/{sensor_id}", response_model=SensorResponse)
async def get_sensor(
    sensor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get a single sensor by ID.
    
    Users can only access sensors belonging to their organization.
    
    **Authentication**: Required
    """
    sensor = await get_sensor_with_org_check(sensor_id, current_user, db)
    
    # Get latest analysis
    stmt = (
        select(AnalysisResultDB)
        .where(AnalysisResultDB.sensor_id == sensor.id)
        .order_by(desc(AnalysisResultDB.timestamp))
        .limit(1)
    )
    res = await db.execute(stmt)
    latest_analysis = res.scalar_one_or_none()
    
    return SensorResponse(
        id=sensor.id,
        name=sensor.name,
        location=sensor.location,
        source_type=sensor.source_type,
        organization_id=sensor.organization_id,
        latest_health_score=latest_analysis.health_score if latest_analysis else 100.0,
        latest_status=latest_analysis.status if latest_analysis else "Normal",
        latest_analysis_timestamp=latest_analysis.timestamp if latest_analysis else None
    )


@router.get("/{sensor_id}/history", response_model=PaginatedResponse[AnalysisResult])
async def get_sensor_history(
    sensor_id: str,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Get paginated analysis history for a sensor.
    
    Users can only access history for sensors belonging to their organization.
    
    **Authentication**: Required
    """
    # Verify sensor ownership first
    await get_sensor_with_org_check(sensor_id, current_user, db)
    
    # Count total
    count_stmt = (
        select(func.count())
        .select_from(AnalysisResultDB)
        .where(AnalysisResultDB.sensor_id == sensor_id)
    )
    total = await db.scalar(count_stmt)
    
    # Get items
    stmt = (
        select(AnalysisResultDB)
        .where(AnalysisResultDB.sensor_id == sensor_id)
        .order_by(desc(AnalysisResultDB.timestamp))
        .offset((pagination.page - 1) * pagination.size)
        .limit(pagination.size)
    )
    result = await db.execute(stmt)
    history_db = result.scalars().all()
    
    history_pydantic = []
    for item in history_db:
        try:
            metrics_obj = AnalysisMetrics(**item.metrics)
            
            res = AnalysisResult(
                sensor_id=item.sensor_id,
                timestamp=item.timestamp.isoformat(),
                health_score=item.health_score,
                status=item.status,
                diagnosis=item.diagnosis,
                metrics=metrics_obj,
                flags=[],
                recommendation=item.recommendation
            )
            history_pydantic.append(res)
        except Exception as e:
            logger.error(f"Error converting history item {item.id}: {e}")
            continue
            
    return PaginatedResponse(
        items=history_pydantic,
        total=total or 0,
        page=pagination.page,
        size=pagination.size,
        pages=math.ceil(total / pagination.size) if total else 0
    )


# ==============================================================================
# CREATE / UPDATE / DELETE ENDPOINTS  
# ==============================================================================

@router.post("", response_model=SensorResponse, status_code=status.HTTP_201_CREATED)
async def create_sensor(
    sensor: SensorCreate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new sensor.
    
    Sensor is automatically assigned to the current user's organization.
    The organization_id from request body is IGNORED for security.
    
    **Authentication**: Required
    """
    new_id = str(uuid.uuid4())[:8]
    
    # Force organization_id from current user (ignore request body)
    org_id = current_user.organization_id
    
    db_sensor = Sensor(
        id=new_id,
        name=sensor.name,
        location=sensor.location,
        source_type=SourceType(sensor.source_type),
        organization_id=org_id  # Always use current user's org
    )
    db.add(db_sensor)
    await db.commit()
    await db.refresh(db_sensor)
    
    logger.info(f"User {current_user.email} created sensor: {new_id} - {sensor.name} for org {org_id}")
    
    return SensorResponse(
        id=db_sensor.id,
        name=db_sensor.name,
        location=db_sensor.location,
        source_type=db_sensor.source_type,
        organization_id=db_sensor.organization_id,
        latest_health_score=100.0,
        latest_status="Normal",
        latest_analysis_timestamp=None
    )


@router.put("/{sensor_id}", response_model=SensorResponse)
async def update_sensor(
    sensor_id: str,
    sensor_update: SensorCreate,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
):
    """
    Update an existing sensor.
    
    Users can only update sensors belonging to their organization.
    Organization cannot be changed.
    
    **Authentication**: Required
    """
    db_sensor = await get_sensor_with_org_check(sensor_id, current_user, db)
    
    # Update fields (but never change organization)
    db_sensor.name = sensor_update.name
    db_sensor.location = sensor_update.location
    db_sensor.source_type = SourceType(sensor_update.source_type)
    
    await db.commit()
    await db.refresh(db_sensor)
    
    logger.info(f"User {current_user.email} updated sensor: {sensor_id}")
    
    # Get latest analysis for response
    stmt = (
        select(AnalysisResultDB)
        .where(AnalysisResultDB.sensor_id == db_sensor.id)
        .order_by(desc(AnalysisResultDB.timestamp))
        .limit(1)
    )
    res = await db.execute(stmt)
    latest_analysis = res.scalar_one_or_none()
    
    return SensorResponse(
        id=db_sensor.id,
        name=db_sensor.name,
        location=db_sensor.location,
        source_type=db_sensor.source_type,
        organization_id=db_sensor.organization_id,
        latest_health_score=latest_analysis.health_score if latest_analysis else 100.0,
        latest_status=latest_analysis.status if latest_analysis else "Normal",
        latest_analysis_timestamp=latest_analysis.timestamp if latest_analysis else None
    )


@router.delete(
    "/{sensor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(RoleChecker(["org_admin", "super_admin"]))]
)
async def delete_sensor(
    sensor_id: str,
    db: DbSession,
    current_user: User = Depends(get_current_active_user),
):
    """
    Delete a sensor and all its readings/analysis history.
    
    **Authorization**: Requires ORG_ADMIN or SUPER_ADMIN role
    
    Users can only delete sensors belonging to their organization.
    
    **Authentication**: Required
    """
    db_sensor = await get_sensor_with_org_check(sensor_id, current_user, db)
    
    # Delete related readings first
    await db.execute(
        delete(SensorReading).where(SensorReading.sensor_id == sensor_id)
    )
    
    # Delete related analysis results
    await db.execute(
        delete(AnalysisResultDB).where(AnalysisResultDB.sensor_id == sensor_id)
    )
    
    # Delete sensor
    await db.delete(db_sensor)
    await db.commit()
    
    logger.warning(f"User {current_user.email} (role: {current_user.role.value}) deleted sensor: {sensor_id}")
    
    return None


# ==============================================================================
# DATA INGESTION ENDPOINTS
# ==============================================================================

@router.post("/upload-csv", response_model=CSVImportResult)
async def upload_csv(
    file: UploadFile = File(..., description="CSV file to import"),
    sensor_id: str = Form(..., min_length=1, max_length=50, description="Target sensor ID"),
    has_header: bool = Form(default=True, description="CSV has header row"),
    timestamp_col: int = Form(default=0, ge=0, description="Timestamp column index (0-based)"),
    value_col: int = Form(default=1, ge=0, description="Value column index (0-based)"),
    chunk_size: int = Form(default=5000, ge=100, le=50000, description="Rows per chunk"),
    skip_errors: bool = Form(default=True, description="Skip invalid rows vs fail fast"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Stream-based CSV import for sensor data with validation.
    
    Industrial-grade ingestion pipeline that processes large CSV files
    in memory-efficient chunks with comprehensive validation.
    
    **Security**: User must own the target sensor (organization check)
    
    **Features:**
    - Streaming chunk-based processing (no full file in RAM)
    - Per-row Pydantic validation with error reporting
    - Atomic transaction per chunk with rollback capability
    - Detailed import statistics and error samples
    
    **CSV Format Support:**
    - 3 columns: sensor_id, timestamp, value (sensor_id column ignored, uses form param)
    - 2 columns: timestamp, value
    - 1 column: value only (timestamp = now)
    
    **Authentication**: Required
    
    Args:
        file: CSV file upload (multipart/form-data)
        sensor_id: Target sensor ID to import data into
        has_header: Whether CSV has a header row to skip
        timestamp_col: 0-based column index for timestamp
        value_col: 0-based column index for value
        chunk_size: Number of rows to process per batch (default: 5000)
        skip_errors: If True, skip invalid rows; if False, fail on first error
        db: Database session (injected)
        current_user: Authenticated user
        
    Returns:
        CSVImportResult: Detailed import statistics
        
    Raises:
        HTTPException 400: Invalid CSV format or header issues
        HTTPException 404: Sensor not found or not owned by user
        HTTPException 500: Database or processing error
        
    Example:
        ```
        curl -X POST /sensors/upload-csv \\
          -H "Authorization: Bearer <token>" \\
          -F "file=@data.csv" \\
          -F "sensor_id=pH-01" \\
          -F "chunk_size=10000"
        ```
    """
    import time
    start_time = time.time()
    
    # ========================================
    # SECURITY: Verify sensor ownership
    # ========================================
    await get_sensor_with_org_check(sensor_id, current_user, db)
    
    logger.info(f"CSV upload started for sensor {sensor_id} by user: {current_user.email}")
    
    # Validate file type
    if file.content_type and file.content_type not in [
        'text/csv', 
        'application/csv',
        'text/plain',
        'application/octet-stream'  # Some clients send this
    ]:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type: {file.content_type}. Expected CSV file."
        )
    
    # Initialize counters
    total_rows = 0
    imported_rows = 0
    failed_rows = 0
    skipped_rows = 0
    error_samples: List[str] = []
    chunks_processed = 0
    
    try:
        # Create streaming CSV reader
        file_stream = codecs.iterdecode(file.file, 'utf-8', errors='replace')
        reader = csv.reader(file_stream)
        
        # Handle header row
        header = None
        actual_timestamp_col = timestamp_col
        actual_value_col = value_col
        
        if has_header:
            try:
                header = next(reader, None)
                if header is None:
                    raise HTTPException(
                        status_code=400,
                        detail="CSV file is empty or contains only whitespace"
                    )
                logger.debug(f"CSV header: {header}")
                
                # Smart column detection based on actual header
                num_cols = len(header)
                
                if num_cols == 1:
                    # Single column CSV: treat as value only, timestamp = now
                    actual_timestamp_col = -1  # No timestamp column
                    actual_value_col = 0
                    logger.info(f"Single column CSV detected, using column 0 as value")
                elif num_cols == 2:
                    # Two column CSV: assume [timestamp, value]
                    actual_timestamp_col = 0
                    actual_value_col = 1
                    logger.info(f"Two column CSV detected: col 0=timestamp, col 1=value")
                else:
                    # Multi-column: validate requested indices
                    max_required_col = max(timestamp_col, value_col)
                    if num_cols <= max_required_col:
                        raise HTTPException(
                            status_code=400,
                            detail=f"CSV has {num_cols} columns but column index {max_required_col} was requested. "
                                   f"Available columns: {header}"
                        )
            except StopIteration:
                raise HTTPException(
                    status_code=400,
                    detail="CSV file is empty"
                )
        
        # Process CSV in chunks
        chunk_buffer: List[dict] = []
        current_row_num = 1 if has_header else 0
        
        for row in reader:
            current_row_num += 1
            total_rows += 1
            
            # Skip empty rows
            if not row or all(cell.strip() == '' for cell in row):
                skipped_rows += 1
                continue
            
            try:
                # Parse row based on column count
                parsed = _parse_csv_row(
                    row=row,
                    row_num=current_row_num,
                    sensor_id=sensor_id,
                    timestamp_col=actual_timestamp_col,
                    value_col=actual_value_col
                )
                
                # Validate with Pydantic schema
                validated = SensorReadingBulk(
                    timestamp=parsed['timestamp'],
                    value=parsed['value']
                )
                
                # Build insert record
                chunk_buffer.append({
                    "sensor_id": sensor_id,
                    "timestamp": validated.timestamp or datetime.now(),
                    "value": validated.value
                })
                
            except Exception as e:
                failed_rows += 1
                error_msg = f"Row {current_row_num}: {str(e)}"
                
                if len(error_samples) < 10:
                    error_samples.append(error_msg)
                
                if not skip_errors:
                    # Fail fast mode
                    raise HTTPException(
                        status_code=400,
                        detail=f"Validation error at {error_msg}"
                    )
                continue
            
            # Process chunk when buffer is full
            if len(chunk_buffer) >= chunk_size:
                await _process_chunk(db, chunk_buffer, sensor_id, chunks_processed)
                imported_rows += len(chunk_buffer)
                chunks_processed += 1
                chunk_buffer = []
                logger.debug(f"Processed chunk {chunks_processed}, total imported: {imported_rows}")
        
        # Process remaining rows in buffer
        if chunk_buffer:
            await _process_chunk(db, chunk_buffer, sensor_id, chunks_processed)
            imported_rows += len(chunk_buffer)
            chunks_processed += 1
        
        # Final commit
        await db.commit()
        
        # Calculate duration
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Build result
        result = CSVImportResult(
            success=True,
            sensor_id=sensor_id,
            total_rows=total_rows,
            imported_rows=imported_rows,
            failed_rows=failed_rows,
            skipped_rows=skipped_rows,
            error_samples=error_samples,
            import_duration_ms=duration_ms,
            chunks_processed=chunks_processed
        )
        
        logger.info(
            f"CSV import completed for {sensor_id} by {current_user.email}: "
            f"{imported_rows}/{total_rows} rows imported, "
            f"{failed_rows} failed, {skipped_rows} skipped, "
            f"in {duration_ms}ms ({chunks_processed} chunks)"
        )
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"CSV upload fatal error: {e}", exc_info=True)
        await db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"CSV import failed: {str(e)}"
        )


@router.post("/stream-data")
async def stream_data(
    data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Stream a single data point and trigger analysis.
    
    **Security**: User must own the target sensor (organization check)
    
    **Authentication**: Required
    
    Args:
        data: Dictionary with sensor_id, value, and optional timestamp
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Authenticated user
        
    Returns:
        dict: Reception status
    """
    if "sensor_id" not in data or "value" not in data:
        raise HTTPException(status_code=400, detail="Missing sensor_id or value")
    
    sensor_id = data["sensor_id"]
    
    # SECURITY: Verify sensor ownership
    await get_sensor_with_org_check(sensor_id, current_user, db)
    
    value = float(data["value"])
    ts = datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now()
    
    # Insert reading
    reading = SensorReading(sensor_id=sensor_id, value=value, timestamp=ts)
    db.add(reading)
    await db.commit()
    
    # Trigger background analysis
    from backend.api.routes.analytics import run_background_analysis
    background_tasks.add_task(run_background_analysis, sensor_id, AsyncSessionLocal)
    
    logger.info(f"User {current_user.email} streamed data point for sensor {sensor_id}")
    return {"status": "received", "sensor_id": sensor_id, "timestamp": ts.isoformat()}


# ==============================================================================
# HELPER FUNCTIONS (Private)
# ==============================================================================

def _parse_csv_row(
    row: List[str],
    row_num: int,
    sensor_id: str,
    timestamp_col: int,
    value_col: int
) -> dict:
    """
    Parse a single CSV row into sensor reading components.
    
    Handles multiple CSV formats:
    - 3+ columns: Uses specified column indices
    - 2 columns: [timestamp, value]
    - 1 column: [value] with current timestamp
    
    Args:
        row: CSV row as list of strings
        row_num: Row number for error reporting
        sensor_id: Target sensor ID
        timestamp_col: Column index for timestamp
        value_col: Column index for value
        
    Returns:
        Dict with 'timestamp' (str or None) and 'value' (str)
        
    Raises:
        ValueError: If row cannot be parsed
    """
    num_cols = len(row)
    
    # Handle special case: timestamp_col = -1 means no timestamp column
    if timestamp_col < 0:
        # Value-only mode
        if value_col < num_cols:
            val_str = row[value_col].strip()
        elif num_cols >= 1:
            val_str = row[0].strip()
        else:
            raise ValueError("Empty row")
        return {'timestamp': None, 'value': val_str}
    
    # Standard column parsing
    if num_cols >= max(timestamp_col, value_col) + 1:
        # Use specified column indices
        ts_str = row[timestamp_col].strip() if timestamp_col < num_cols else None
        val_str = row[value_col].strip()
    elif num_cols == 2:
        # Assume [timestamp, value]
        ts_str = row[0].strip()
        val_str = row[1].strip()
    elif num_cols == 1:
        # Assume [value] only
        ts_str = None
        val_str = row[0].strip()
    else:
        raise ValueError(f"Empty row or insufficient columns (got {num_cols})")
    
    # Validate value is present
    if not val_str:
        raise ValueError("Missing value in row")
    
    return {
        'timestamp': ts_str if ts_str else None,
        'value': val_str
    }


async def _process_chunk(
    db: AsyncSession,
    chunk: List[dict],
    sensor_id: str,
    chunk_num: int
) -> None:
    """
    Process and insert a chunk of sensor readings into the database.
    
    Uses bulk insert for performance. Does NOT commit - caller
    is responsible for transaction management.
    
    Args:
        db: Database session
        chunk: List of reading dicts with sensor_id, timestamp, value
        sensor_id: Sensor identifier (for logging)
        chunk_num: Chunk number (for logging)
        
    Raises:
        SQLAlchemyError: On database errors
    """
    if not chunk:
        return
    
    try:
        await db.execute(insert(SensorReading), chunk)
        logger.debug(f"Inserted chunk {chunk_num} with {len(chunk)} rows for {sensor_id}")
    except Exception as e:
        logger.error(f"Chunk {chunk_num} insert failed: {e}")
        raise
