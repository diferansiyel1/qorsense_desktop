"""
Task Status Routes.

Provides endpoints to check status of background Celery tasks.
"""

import logging
from enum import Enum
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tasks", tags=["Tasks"])


class TaskStatus(str, Enum):
    """Celery task status enumeration."""
    PENDING = "PENDING"
    STARTED = "STARTED"
    PROGRESS = "PROGRESS"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class TaskStatusResponse(BaseModel):
    """Response model for task status queries."""
    task_id: str = Field(..., description="Unique task identifier")
    status: TaskStatus = Field(..., description="Current task status")
    ready: bool = Field(..., description="Whether task has completed")
    result: Any | None = Field(None, description="Task result if completed")
    error: str | None = Field(None, description="Error message if failed")
    progress: int | None = Field(None, description="Progress percentage (0-100)")
    message: str | None = Field(None, description="Status message")
    info: dict[str, Any] | None = Field(None, description="Additional task info")


class TaskSubmitResponse(BaseModel):
    """Response model for task submission."""
    task_id: str = Field(..., description="Unique task identifier")
    status: str = Field("PENDING", description="Initial task status")
    message: str = Field(..., description="Submission confirmation message")


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """
    Get the status of a background task.
    
    Queries Celery for the current state of the task.
    
    Args:
        task_id: The unique task identifier returned when task was submitted.
        
    Returns:
        TaskStatusResponse with current status and result if available.
        
    Raises:
        HTTPException 503: If Celery/Redis is not available.
    """
    try:
        from backend.core.celery_app import REDIS_AVAILABLE, celery_app
        from celery.result import AsyncResult

        if not REDIS_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="Task queue is not available. Redis connection failed."
            )

        result = AsyncResult(task_id, app=celery_app)

        response = {
            "task_id": task_id,
            "status": result.status,
            "ready": result.ready(),
            "result": None,
            "error": None,
            "progress": None,
            "message": None,
            "info": None,
        }

        if result.ready():
            if result.successful():
                response["result"] = result.get()
            elif result.failed():
                response["error"] = str(result.result)
        elif result.status == "PROGRESS":
            meta = result.info or {}
            response["progress"] = meta.get("progress")
            response["message"] = meta.get("message")
            response["info"] = meta
        elif result.status == "STARTED":
            response["message"] = "Task is being processed"
            response["info"] = result.info
        elif result.status == "PENDING":
            response["message"] = "Task is queued and waiting for execution"
        elif result.status == "RETRY":
            response["message"] = "Task is being retried"

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting task status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get task status: {str(e)}"
        )


@router.delete("/{task_id}")
async def revoke_task(task_id: str, terminate: bool = False):
    """
    Revoke/cancel a pending or running task.
    
    Args:
        task_id: The task identifier to revoke.
        terminate: If True, terminate even if task has started.
        
    Returns:
        Confirmation of revocation.
    """
    try:
        from backend.core.celery_app import REDIS_AVAILABLE, celery_app

        if not REDIS_AVAILABLE:
            raise HTTPException(
                status_code=503,
                detail="Task queue is not available."
            )

        celery_app.control.revoke(task_id, terminate=terminate)

        logger.info(f"Task {task_id} revoked (terminate={terminate})")

        return {
            "task_id": task_id,
            "status": "REVOKED",
            "message": f"Task revocation requested (terminate={terminate})"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error revoking task: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to revoke task: {str(e)}"
        )


@router.get("/")
async def list_active_tasks():
    """
    List currently active tasks across all workers.
    
    Returns summary of active, scheduled, and reserved tasks.
    """
    try:
        from backend.core.celery_app import REDIS_AVAILABLE, celery_app

        if not REDIS_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "Task queue is not available. Running in synchronous mode."
            }

        # Get task stats from workers
        inspect = celery_app.control.inspect()

        active = inspect.active() or {}
        scheduled = inspect.scheduled() or {}
        reserved = inspect.reserved() or {}

        return {
            "status": "available",
            "workers": list(active.keys()),
            "active_tasks": sum(len(tasks) for tasks in active.values()),
            "scheduled_tasks": sum(len(tasks) for tasks in scheduled.values()),
            "reserved_tasks": sum(len(tasks) for tasks in reserved.values()),
            "details": {
                "active": active,
                "scheduled": scheduled,
                "reserved": reserved,
            }
        }

    except Exception as e:
        logger.warning(f"Could not inspect workers: {e}")
        return {
            "status": "unknown",
            "message": f"Could not connect to workers: {str(e)}"
        }
