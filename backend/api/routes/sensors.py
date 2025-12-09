"""
Sensor Management Routes

Handles sensor CRUD operations, data ingestion, and history retrieval.
Features streaming CSV import with Pydantic validation for industrial-grade data ingestion.
"""

from typing import List
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, insert, desc, func
from backend.database import get_db, AsyncSessionLocal
from backend.models_db import Sensor, SensorReading, AnalysisResultDB, SourceType
from backend.models import SensorCreate, SensorResponse, AnalysisResult, AnalysisMetrics
from backend.schemas.common import PaginationParams, PaginatedResponse
from backend.schemas.sensor import SensorReadingBulk, CSVImportResult
from backend.api.deps import DevUser, DbSession
from datetime import datetime
import logging
import csv
import codecs
import uuid
import math

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sensors", tags=["Sensors"])


@router.get("", response_model=PaginatedResponse[SensorResponse])
async def get_sensors(
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    List sensors with pagination.
    """
    # Count total
    count_stmt = select(func.count()).select_from(Sensor)
    total = await db.scalar(count_stmt)
    
    # Get items
    stmt = select(Sensor).offset((pagination.page - 1) * pagination.size).limit(pagination.size)
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
        
    return PaginatedResponse(
        items=sensor_responses,
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=math.ceil(total / pagination.size)
    )


@router.post("", response_model=SensorResponse)
async def create_sensor(
    sensor: SensorCreate,
    db: DbSession,
    current_user: DevUser = None,
):
    """
    Create a new sensor.
    
    **Authentication**: Required in production, optional in development.
    """
    new_id = str(uuid.uuid4())[:8]
    
    db_sensor = Sensor(
        id=new_id,
        name=sensor.name,
        location=sensor.location,
        source_type=SourceType(sensor.source_type),
        organization_id=sensor.organization_id
    )
    db.add(db_sensor)
    await db.commit()
    await db.refresh(db_sensor)
    
    logger.info(f"Created sensor: {new_id} - {sensor.name}")
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


@router.get("/{sensor_id}/history", response_model=PaginatedResponse[AnalysisResult])
async def get_sensor_history(
    sensor_id: str,
    pagination: PaginationParams = Depends(),
    db: AsyncSession = Depends(get_db)
):
    """
    Get paginated analysis history for a sensor.
    """
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
        total=total,
        page=pagination.page,
        size=pagination.size,
        pages=math.ceil(total / pagination.size) if total else 0
    )


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
    current_user: DevUser = None,
):
    """
    Stream-based CSV import for sensor data with validation.
    
    Industrial-grade ingestion pipeline that processes large CSV files
    in memory-efficient chunks with comprehensive validation.
    
    **Features:**
    - Streaming chunk-based processing (no full file in RAM)
    - Per-row Pydantic validation with error reporting
    - Atomic transaction per chunk with rollback capability
    - Detailed import statistics and error samples
    
    **CSV Format Support:**
    - 3 columns: sensor_id, timestamp, value (sensor_id column ignored, uses form param)
    - 2 columns: timestamp, value
    - 1 column: value only (timestamp = now)
    
    **Authentication:** Required in production, optional in development.
    
    Args:
        file: CSV file upload (multipart/form-data)
        sensor_id: Target sensor ID to import data into
        has_header: Whether CSV has a header row to skip
        timestamp_col: 0-based column index for timestamp
        value_col: 0-based column index for value
        chunk_size: Number of rows to process per batch (default: 5000)
        skip_errors: If True, skip invalid rows; if False, fail on first error
        db: Database session (injected)
        current_user: Authenticated user (optional in dev)
        
    Returns:
        CSVImportResult: Detailed import statistics
        
    Raises:
        HTTPException 400: Invalid CSV format or header issues
        HTTPException 500: Database or processing error
        
    Example:
        ```
        curl -X POST /sensors/upload-csv \\
          -F "file=@data.csv" \\
          -F "sensor_id=pH-01" \\
          -F "chunk_size=10000"
        ```
    """
    import time
    start_time = time.time()
    
    user_info = current_user.username if current_user else "anonymous (dev mode)"
    logger.info(f"CSV upload started for sensor {sensor_id} by user: {user_info}")
    
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
            f"CSV import completed for {sensor_id}: "
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


@router.post("/stream-data")
async def stream_data(
    data: dict,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: DevUser = None,
):
    """
    Stream a single data point and trigger analysis.
    
    **Authentication**: Required in production, optional in development.
    
    Args:
        data: Dictionary with sensor_id, value, and optional timestamp
        background_tasks: FastAPI background tasks
        db: Database session
        current_user: Authenticated user (optional in development)
        
    Returns:
        dict: Reception status
    """
    if "sensor_id" not in data or "value" not in data:
        raise HTTPException(status_code=400, detail="Missing sensor_id or value")
    
    sensor_id = data["sensor_id"]
    value = float(data["value"])
    ts = datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now()
    
    # Insert reading
    reading = SensorReading(sensor_id=sensor_id, value=value, timestamp=ts)
    db.add(reading)
    await db.commit()
    
    # Trigger background analysis
    from backend.api.routes.analytics import run_background_analysis
    background_tasks.add_task(run_background_analysis, sensor_id, AsyncSessionLocal)
    
    logger.info(f"Received data point for sensor {sensor_id}")
    return {"status": "received", "sensor_id": sensor_id, "timestamp": ts.isoformat()}
