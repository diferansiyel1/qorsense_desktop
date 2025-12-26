"""
Analysis Tasks Module.

Contains Celery tasks for CPU-intensive sensor analysis operations.
Tasks are executed asynchronously by Celery workers.
"""

import logging
from datetime import datetime
from typing import Any

import numpy as np
from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="backend.tasks.analysis_tasks.analyze_sensor_data",
    max_retries=3,
    default_retry_delay=5,
    autoretry_for=(ConnectionError, TimeoutError),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    track_started=True,
    acks_late=True,
)
def analyze_sensor_data(
    self,
    sensor_id: str,
    values: list[float],
    sensor_type: str = "Generic",
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Perform comprehensive sensor data analysis.
    
    This is a CPU-intensive task that runs asynchronously.
    Includes DFA analysis, slope calculation, and anomaly detection.
    
    Args:
        self: Celery task instance (for retry access)
        sensor_id: Unique sensor identifier
        values: List of sensor readings
        sensor_type: Type of sensor (Bio, pH, etc.)
        config: Optional analysis configuration
        
    Returns:
        Dictionary containing analysis results and metrics.
        
    Raises:
        MaxRetriesExceededError: After 3 failed attempts.
    """
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Starting analysis for sensor {sensor_id} with {len(values)} values")

    # Update task state to PROGRESS
    self.update_state(
        state="PROGRESS",
        meta={
            "sensor_id": sensor_id,
            "progress": 10,
            "message": "Initializing analysis..."
        }
    )

    try:
        # Import analysis functions
        from backend.analysis import SensorAnalyzer

        analyzer = SensorAnalyzer()

        # Update progress
        self.update_state(
            state="PROGRESS",
            meta={
                "sensor_id": sensor_id,
                "progress": 30,
                "message": "Running DFA analysis..."
            }
        )

        # Perform analysis - note: analyze() takes raw_data, not values
        result = analyzer.analyze(raw_data=values)

        self.update_state(
            state="PROGRESS",
            meta={
                "sensor_id": sensor_id,
                "progress": 90,
                "message": "Finalizing results..."
            }
        )

        # Convert result to dict if it's a Pydantic model
        if hasattr(result, 'model_dump'):
            result_dict = result.model_dump()
        elif hasattr(result, 'dict'):
            result_dict = result.dict()
        else:
            result_dict = result

        logger.info(f"[Task {task_id}] Analysis completed for sensor {sensor_id}")

        return {
            "success": True,
            "sensor_id": sensor_id,
            "task_id": task_id,
            "completed_at": datetime.utcnow().isoformat(),
            "result": result_dict
        }

    except Exception as e:
        logger.error(f"[Task {task_id}] Analysis failed: {e}", exc_info=True)

        # Retry on transient errors
        if self.request.retries < self.max_retries:
            logger.info(f"[Task {task_id}] Retrying... (attempt {self.request.retries + 1}/{self.max_retries})")
            raise self.retry(exc=e)

        # Max retries exceeded
        return {
            "success": False,
            "sensor_id": sensor_id,
            "task_id": task_id,
            "error": str(e),
            "completed_at": datetime.utcnow().isoformat()
        }


@shared_task(
    bind=True,
    name="backend.tasks.analysis_tasks.calculate_dfa",
    max_retries=3,
    default_retry_delay=5,
    track_started=True,
)
def calculate_dfa(
    self,
    values: list[float],
    order: int = 1,
) -> dict[str, Any]:
    """
    Calculate Detrended Fluctuation Analysis (DFA) for time series.
    
    CPU-intensive fractal analysis for long-range correlations.
    
    Args:
        self: Celery task instance
        values: List of sensor readings
        order: Polynomial order for detrending (default: 1)
        
    Returns:
        Dictionary with DFA alpha exponent and fluctuation data.
    """
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Starting DFA calculation with {len(values)} values")

    try:
        from backend.analysis import SensorAnalyzer

        analyzer = SensorAnalyzer()

        # Calculate DFA
        alpha = analyzer._calculate_dfa(values, order=order)

        logger.info(f"[Task {task_id}] DFA completed: alpha={alpha}")

        return {
            "success": True,
            "task_id": task_id,
            "dfa_alpha": alpha,
            "order": order,
            "n_points": len(values),
            "completed_at": datetime.utcnow().isoformat()
        }

    except Exception as e:
        logger.error(f"[Task {task_id}] DFA calculation failed: {e}", exc_info=True)
        return {
            "success": False,
            "task_id": task_id,
            "error": str(e)
        }


@shared_task(
    bind=True,
    name="backend.tasks.analysis_tasks.calculate_statistics",
    max_retries=3,
    default_retry_delay=5,
    track_started=True,
)
def calculate_statistics(
    self,
    values: list[float],
) -> dict[str, Any]:
    """
    Calculate comprehensive statistical metrics for sensor data.
    
    Args:
        self: Celery task instance
        values: List of sensor readings
        
    Returns:
        Dictionary with statistical metrics.
    """
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Calculating statistics for {len(values)} values")

    try:
        arr = np.array(values)

        stats = {
            "success": True,
            "task_id": task_id,
            "n_points": len(values),
            "mean": float(np.mean(arr)),
            "std": float(np.std(arr)),
            "min": float(np.min(arr)),
            "max": float(np.max(arr)),
            "median": float(np.median(arr)),
            "variance": float(np.var(arr)),
            "range": float(np.max(arr) - np.min(arr)),
            "completed_at": datetime.utcnow().isoformat()
        }

        # Add percentiles
        for p in [25, 50, 75, 90, 95, 99]:
            stats[f"p{p}"] = float(np.percentile(arr, p))

        logger.info(f"[Task {task_id}] Statistics calculated")
        return stats

    except Exception as e:
        logger.error(f"[Task {task_id}] Statistics calculation failed: {e}")
        return {
            "success": False,
            "task_id": task_id,
            "error": str(e)
        }


@shared_task(
    bind=True,
    name="backend.tasks.analysis_tasks.batch_analyze",
    max_retries=2,
    default_retry_delay=10,
    track_started=True,
    soft_time_limit=600,
    time_limit=660,
)
def batch_analyze(
    self,
    sensor_ids: list[str],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Batch analysis for multiple sensors.
    
    Long-running task with extended timeouts.
    
    Args:
        self: Celery task instance
        sensor_ids: List of sensor IDs to analyze
        config: Optional shared configuration
        
    Returns:
        Dictionary with results for each sensor.
    """
    task_id = self.request.id
    logger.info(f"[Task {task_id}] Starting batch analysis for {len(sensor_ids)} sensors")

    results = {}
    total = len(sensor_ids)

    for i, sensor_id in enumerate(sensor_ids):
        self.update_state(
            state="PROGRESS",
            meta={
                "current": i + 1,
                "total": total,
                "sensor_id": sensor_id,
                "progress": int((i / total) * 100)
            }
        )

        try:
            # Note: In production, fetch actual data from database
            # This is a placeholder for batch processing structure
            results[sensor_id] = {
                "status": "processed",
                "message": f"Sensor {sensor_id} analyzed"
            }
        except Exception as e:
            results[sensor_id] = {
                "status": "error",
                "error": str(e)
            }

    logger.info(f"[Task {task_id}] Batch analysis completed")

    return {
        "success": True,
        "task_id": task_id,
        "total_sensors": total,
        "results": results,
        "completed_at": datetime.utcnow().isoformat()
    }
