"""
Celery Application Configuration.

Configures Celery with Redis as broker and result backend.
Provides graceful degradation when Redis is unavailable.
"""

import logging
import os

from celery import Celery
from kombu import Queue

logger = logging.getLogger(__name__)

# Redis connection from environment
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)


def check_redis_connection() -> bool:
    """
    Check if Redis is available.
    
    Returns:
        True if Redis is reachable, False otherwise.
    """
    try:
        import redis
        r = redis.from_url(REDIS_URL, socket_connect_timeout=2)
        r.ping()
        logger.info("✓ Redis connection successful")
        return True
    except Exception as e:
        logger.warning(f"⚠ Redis not available: {e}")
        return False


# Check Redis availability on import
REDIS_AVAILABLE = check_redis_connection()


def create_celery_app() -> Celery:
    """
    Create and configure the Celery application.
    
    Returns:
        Configured Celery application instance.
    """
    app = Celery(
        "qorsense_tasks",
        broker=CELERY_BROKER_URL,
        backend=CELERY_RESULT_BACKEND,
        include=["backend.tasks.analysis_tasks"],
    )

    # Celery configuration
    app.conf.update(
        # Task settings
        task_serializer="json",
        accept_content=["json"],
        result_serializer="json",
        timezone="UTC",
        enable_utc=True,

        # Result backend settings
        result_expires=3600,  # Results expire after 1 hour
        result_extended=True,  # Include task name, args in result

        # Task execution settings
        task_track_started=True,  # Track STARTED state
        task_time_limit=300,  # Hard timeout: 5 minutes
        task_soft_time_limit=240,  # Soft timeout: 4 minutes

        # Retry settings
        task_acks_late=True,  # Acknowledge after task completion
        task_reject_on_worker_lost=True,

        # Default retry policy
        task_default_retry_delay=5,  # 5 seconds between retries
        task_max_retries=3,

        # Worker settings
        worker_prefetch_multiplier=4,
        worker_concurrency=4,  # Number of worker processes

        # Queue configuration
        task_queues=(
            Queue("default", routing_key="default"),
            Queue("analysis", routing_key="analysis.#"),
            Queue("low_priority", routing_key="low.#"),
        ),

        # Default queue
        task_default_queue="default",
        task_default_exchange="tasks",
        task_default_routing_key="default",

        # Task routes
        task_routes={
            "backend.tasks.analysis_tasks.*": {"queue": "analysis"},
        },

        # Broker connection retry
        broker_connection_retry_on_startup=True,
        broker_connection_max_retries=10,
    )

    return app


# Create the Celery app instance
celery_app = create_celery_app()


class CeleryNotAvailableError(Exception):
    """Raised when Celery/Redis is not available and task cannot be queued."""
    pass


def ensure_celery_available() -> None:
    """
    Ensure Celery/Redis is available.
    
    Raises:
        CeleryNotAvailableError: If Redis is not reachable.
    """
    if not REDIS_AVAILABLE:
        raise CeleryNotAvailableError(
            "Redis is not available. Background tasks are disabled. "
            "Please ensure Redis is running at: " + REDIS_URL
        )


def get_task_status(task_id: str) -> dict:
    """
    Get the status of a Celery task.
    
    Args:
        task_id: The task ID to check.
        
    Returns:
        Dictionary with task status information.
    """
    from celery.result import AsyncResult

    result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": result.status,
        "ready": result.ready(),
    }

    if result.ready():
        if result.successful():
            response["result"] = result.get()
        elif result.failed():
            response["error"] = str(result.result)
    elif result.status == "STARTED":
        response["info"] = result.info
    elif result.status == "PENDING":
        response["message"] = "Task is pending execution"

    return response


# Export for use in other modules
__all__ = [
    "celery_app",
    "REDIS_AVAILABLE",
    "ensure_celery_available",
    "get_task_status",
    "CeleryNotAvailableError",
]
