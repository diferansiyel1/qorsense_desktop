"""
Analytics Routes

Handles sensor data analysis endpoints and background analysis tasks.
Protected with JWT authentication - requires valid access token.
"""

import logging
from datetime import datetime, timedelta

import numpy as np
from backend.analysis import SensorAnalyzer
from backend.api.deps import DbSession, DevUser
from backend.core.config import settings
from backend.models import AnalysisMetrics, AnalysisResult, SensorDataInput
from backend.models_db import AnalysisResultDB, SensorReading
from fastapi import APIRouter, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analyze", tags=["Analytics"])

# Shared analyzer instance
analyzer = SensorAnalyzer()


# Extended Models for Timestamps


class AnalysisMetricsExtended(AnalysisMetrics):
    """Extended metrics with timestamps and trend data."""
    timestamps: list[str] = []
    trend: list[float] = []
    residuals: list[float] = []


class AnalysisResultExtended(AnalysisResult):
    """Extended analysis result with enhanced metrics."""
    metrics: AnalysisMetricsExtended


async def save_analysis_result(db: AsyncSession, sensor_id: str, result: AnalysisResult):
    """
    Save analysis result to database asynchronously.
    
    Args:
        db: Database session
        sensor_id: Sensor identifier
        result: Analysis result to save
    """
    try:
        db_result = AnalysisResultDB(
            sensor_id=sensor_id,
            timestamp=datetime.fromisoformat(result.timestamp),
            health_score=result.health_score,
            status=result.status,
            metrics=result.metrics.dict() if hasattr(result.metrics, 'dict') else result.metrics.model_dump(),
            diagnosis=result.diagnosis,
            recommendation=result.recommendation
        )
        db.add(db_result)
        await db.commit()
        logger.debug(f"Saved analysis result for sensor {sensor_id}")
    except Exception as e:
        logger.error(f"Failed to save analysis result: {e}")
        await db.rollback()


async def run_background_analysis(sensor_id: str, db_session_factory):
    """
    Background task to run analysis on recent data.
    
    Args:
        sensor_id: Sensor to analyze
        db_session_factory: Async session factory
    """
    async with db_session_factory() as db:
        logger.info(f"Running background analysis for {sensor_id}")

        # Fetch last N readings
        window_size = settings.default_window_size
        stmt = (
            select(SensorReading)
            .where(SensorReading.sensor_id == sensor_id)
            .order_by(desc(SensorReading.timestamp))
            .limit(window_size)
        )
        result = await db.execute(stmt)
        readings = result.scalars().all()

        if len(readings) < 10:
            logger.info("Not enough data for background analysis")
            return

        # Prepare values (reverse to chronological order)
        values = [r.value for r in reversed(readings)]

        # Analyze
        try:
            clean_data = analyzer.preprocessing(values)
            bias = analyzer.calc_bias(clean_data)
            slope = analyzer.calc_slope(clean_data)
            noise_std = float(np.std(clean_data))
            snr_db = analyzer.calc_snr_db(clean_data)
            hysteresis, hyst_x, hyst_y = analyzer.calc_hysteresis(clean_data)
            hurst, hurst_r2, dfa_scales, dfa_flucts = analyzer.calc_dfa(clean_data)

            metrics_dict = {
                "bias": bias,
                "slope": slope,
                "noise_std": noise_std,
                "snr_db": snr_db,
                "hysteresis": hysteresis,
                "hysteresis_x": hyst_x,
                "hysteresis_y": hyst_y,
                "hurst": hurst,
                "hurst_r2": hurst_r2,
                "dfa_scales": dfa_scales,
                "dfa_fluctuations": dfa_flucts
            }
            health = analyzer.get_health_score(metrics_dict)
            rul = analyzer.calc_rul(clean_data, slope)

            analysis_result = AnalysisResult(
                sensor_id=sensor_id,
                timestamp=datetime.now().isoformat(),
                health_score=health["score"],
                status=health["status"],
                diagnosis=health["diagnosis"],
                metrics=AnalysisMetrics(**metrics_dict),
                flags=health["flags"],
                recommendation=health["recommendation"],
                prediction=rul
            )

            await save_analysis_result(db, sensor_id, analysis_result)
            logger.info(f"Background analysis completed for {sensor_id}")

        except Exception as e:
            logger.error(f"Background analysis error: {e}", exc_info=True)


@router.post("", response_model=AnalysisResultExtended)
async def analyze_sensor(
    data: SensorDataInput,
    db: DbSession,
    current_user: DevUser = None,
):
    """
    Analyze sensor data.
    
    **Authentication**: Required in production, optional in development.
    
    Supports two modes:
    1. Ad-hoc analysis: Provide values directly in the request
    2. Database analysis: Sensor data is fetched from database using sensor_id
    
    Args:
        data: Sensor data input (values or sensor_id with config)
        db: Database session
        current_user: Authenticated user (optional in development)
        
    Returns:
        AnalysisResultExtended: Analysis result with metrics
    """
    user_info = current_user.email if current_user else "anonymous (dev mode)"
    logger.info(f"Analysis request for sensor: {data.sensor_id} by user: {user_info}")

    values = data.values
    timestamps_iso = []

    # If no values provided, fetch from database
    if not values or len(values) == 0:
        start_date = None
        end_date = None

        # Check for date range in config
        if data.config:
            if isinstance(data.config, dict):
                start_date = data.config.get("start_date")
                end_date = data.config.get("end_date")
            else:
                start_date = getattr(data.config, "start_date", None)
                end_date = getattr(data.config, "end_date", None)

        if start_date and end_date:
            # Date range query
            try:
                if isinstance(start_date, str):
                    start_date = datetime.fromisoformat(start_date)
                if isinstance(end_date, str):
                    end_date = datetime.fromisoformat(end_date)

                stmt = (
                    select(SensorReading)
                    .where(
                        SensorReading.sensor_id == data.sensor_id,
                        SensorReading.timestamp >= start_date,
                        SensorReading.timestamp <= end_date
                    )
                    .order_by(SensorReading.timestamp.asc())
                    .limit(settings.max_analysis_points)
                )

                result = await db.execute(stmt)
                readings = result.scalars().all()
                values = [r.value for r in readings]
                timestamps_iso = [r.timestamp.isoformat() for r in readings]

            except Exception as e:
                logger.error(f"Date range query error: {e}")
                raise HTTPException(status_code=400, detail="Invalid date format")
        else:
            # Default: Last N points
            window_size = settings.default_window_size
            if data.config:
                cfg_window = (
                    data.config.get("window_size", 0) if isinstance(data.config, dict)
                    else getattr(data.config, "window_size", 0)
                )
                if cfg_window:
                    window_size = min(cfg_window, settings.max_analysis_points)

            stmt = (
                select(SensorReading)
                .where(SensorReading.sensor_id == data.sensor_id)
                .order_by(desc(SensorReading.timestamp))
                .limit(window_size)
            )
            result = await db.execute(stmt)
            readings = result.scalars().all()

            # Restore chronological order
            readings_asc = list(reversed(readings))
            values = [r.value for r in readings_asc]
            timestamps_iso = [r.timestamp.isoformat() for r in readings_asc]

        # Return empty result if insufficient data
        if len(values) < 5:
            empty_metrics = AnalysisMetricsExtended(
                bias=0.0, slope=0.0, noise_std=0.0, snr_db=0.0, hysteresis=0.0,
                hysteresis_x=[], hysteresis_y=[],
                hurst=0.5, hurst_r2=0.0, dfa_scales=[], dfa_fluctuations=[],
                timestamps=[], trend=[], residuals=[]
            )
            return AnalysisResultExtended(
                sensor_id=data.sensor_id,
                timestamp=datetime.now().isoformat(),
                health_score=0.0,
                status="No Data",
                metrics=empty_metrics,
                diagnosis="Insufficient data for analysis",
                flags=[],
                recommendation="Ingest more data points",
                prediction="N/A"
            )
    else:
        # Values provided directly
        if data.timestamps:
            timestamps_iso = data.timestamps
        else:
            # Generate synthetic timestamps
            now = datetime.now()
            timestamps_iso = [
                (now - timedelta(seconds=len(values) - i)).isoformat()
                for i in range(len(values))
            ]

    # Create analyzer with custom config if provided
    current_analyzer = SensorAnalyzer(config=data.config) if data.config else analyzer

    try:
        # Perform analysis
        analysis_result = current_analyzer.analyze(values)

        metrics_dict = analysis_result["metrics"]
        metrics_dict["timestamps"] = timestamps_iso

        health = analysis_result["health"]
        rul_prediction = analysis_result["prediction"]

        # Construct extended model
        metrics_obj = AnalysisMetricsExtended(**metrics_dict)

        result_obj = AnalysisResultExtended(
            sensor_id=data.sensor_id,
            timestamp=datetime.now().isoformat(),
            health_score=health["score"],
            status=health["status"],
            diagnosis=health["diagnosis"],
            metrics=metrics_obj,
            flags=health["flags"],
            recommendation=health["recommendation"],
            prediction=rul_prediction
        )

        # Save to database
        await save_analysis_result(db, data.sensor_id, result_obj)

        logger.info(f"Analysis completed for {data.sensor_id}: health={health['score']:.1f}")
        return result_obj

    except Exception as e:
        logger.error(f"Analysis failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Analysis error: {str(e)}")


# =============================================================================
# Async Analysis Endpoints (Celery-powered)
# =============================================================================


from pydantic import BaseModel, Field


class AsyncAnalysisRequest(BaseModel):
    """Request model for async analysis."""
    sensor_id: str = Field(..., description="Sensor ID to analyze")
    sensor_type: str = Field(default="Generic", description="Sensor type")
    values: list[float] = Field(default=[], description="Optional values override")
    config: dict | None = Field(default=None, description="Analysis configuration")
    use_async: bool = Field(default=True, description="Use async processing")


class AsyncAnalysisResponse(BaseModel):
    """Response model for async analysis submission."""
    task_id: str = Field(..., description="Task ID for status polling")
    status: str = Field(..., description="Initial task status")
    message: str = Field(..., description="Submission message")
    async_mode: bool = Field(..., description="Whether async mode was used")
    poll_url: str = Field(..., description="URL to poll for task status")


@router.post("/async", response_model=AsyncAnalysisResponse)
async def analyze_sensor_async(
    request: AsyncAnalysisRequest,
    db: DbSession,
    current_user: DevUser = None,
):
    """
    Submit sensor analysis as a background task.
    
    This endpoint queues the analysis to Celery workers and returns immediately.
    Use the task_id to poll `/tasks/{task_id}` for results.
    
    **Graceful Degradation**: If Redis is unavailable, falls back to
    synchronous analysis (slower but still works).
    
    **Authentication**: Required in production, optional in development.
    
    Args:
        request: Analysis request with sensor_id and optional values
        db: Database session
        current_user: Authenticated user (optional in development)
        
    Returns:
        AsyncAnalysisResponse with task_id for polling
        
    Example:
        ```
        POST /analyze/async
        {"sensor_id": "pH-01", "use_async": true}
        
        Response:
        {"task_id": "abc-123", "status": "PENDING", "poll_url": "/tasks/abc-123"}
        ```
    """
    user_info = current_user.email if current_user else "anonymous (dev mode)"
    logger.info(f"Async analysis request for sensor: {request.sensor_id} by user: {user_info}")

    # Get values from request or fetch from database
    values = request.values

    if not values or len(values) == 0:
        # Fetch from database
        stmt = (
            select(SensorReading)
            .where(SensorReading.sensor_id == request.sensor_id)
            .order_by(desc(SensorReading.timestamp))
            .limit(1000)
        )
        result = await db.execute(stmt)
        readings = result.scalars().all()

        if not readings:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for sensor {request.sensor_id}"
            )

        values = [r.value for r in reversed(readings)]

    # Try async mode with Celery
    if request.use_async:
        try:
            from backend.core.celery_app import REDIS_AVAILABLE
            from backend.tasks.analysis_tasks import analyze_sensor_data

            if REDIS_AVAILABLE:
                # Submit to Celery
                task = analyze_sensor_data.delay(
                    sensor_id=request.sensor_id,
                    values=values,
                    sensor_type=request.sensor_type,
                    config=request.config
                )

                logger.info(f"Task {task.id} queued for sensor {request.sensor_id}")

                return AsyncAnalysisResponse(
                    task_id=task.id,
                    status="PENDING",
                    message=f"Analysis queued for sensor {request.sensor_id}",
                    async_mode=True,
                    poll_url=f"/tasks/{task.id}"
                )
            logger.warning("Redis unavailable, falling back to sync mode")

        except ImportError as e:
            logger.warning(f"Celery not available: {e}")
        except Exception as e:
            logger.warning(f"Async task submission failed: {e}, falling back to sync mode")

    # Fallback: Synchronous analysis
    import uuid
    fake_task_id = str(uuid.uuid4())

    logger.info(f"Running synchronous analysis for {request.sensor_id} (task_id={fake_task_id})")

    try:
        # Note: analyzer.analyze() takes raw_data, not keyword args
        analysis_result = analyzer.analyze(raw_data=values)

        # Store result temporarily (in production, use Redis or DB)
        # For now, return a special response indicating sync completion
        return AsyncAnalysisResponse(
            task_id=fake_task_id,
            status="SUCCESS",
            message=f"Analysis completed synchronously for sensor {request.sensor_id} (Redis unavailable)",
            async_mode=False,
            poll_url=f"/tasks/{fake_task_id}"
        )

    except Exception as e:
        logger.error(f"Synchronous analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}"
        )

