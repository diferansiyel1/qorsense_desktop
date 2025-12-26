"""
Celery Tasks Package.

Contains all background task definitions for the QorSense application.
"""

from backend.tasks.analysis_tasks import (
    analyze_sensor_data,
    batch_analyze,
    calculate_dfa,
    calculate_statistics,
)

__all__ = [
    "analyze_sensor_data",
    "calculate_dfa",
    "calculate_statistics",
    "batch_analyze",
]
