"""
Metrics Collection

Provides Prometheus metrics for application monitoring.
"""

import logging
import time
from collections.abc import Callable
from functools import wraps

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

logger = logging.getLogger(__name__)

# Request Metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"]
)

REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)

# Application Metrics
ANALYSIS_COUNT = Counter(
    "analysis_operations_total",
    "Total analysis operations performed",
    ["sensor_type"]
)

SENSOR_READINGS_COUNT = Counter(
    "sensor_readings_total",
    "Total sensor readings processed",
    ["sensor_id"]
)

DB_OPERATION_LATENCY = Histogram(
    "db_operation_duration_seconds",
    "Database operation latency",
    ["operation", "table"]
)


def track_time(metric: Histogram, labels: dict = None):
    """Decorator to track execution time of a function."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.time() - start_time
                if labels:
                    metric.labels(**labels).observe(duration)
                else:
                    metric.observe(duration)
        return wrapper
    return decorator


def get_metrics():
    """Get latest metrics for scraping."""
    return generate_latest(), CONTENT_TYPE_LATEST
