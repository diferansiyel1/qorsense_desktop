"""
Health Check Routes

Provides health, liveness, and readiness endpoints for monitoring.
"""

import logging

from backend.core.config import settings
from backend.database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Health"])


@router.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": f"{settings.app_name} Backend Running",
        "version": settings.app_version,
        "environment": settings.environment,
        "database": "Enabled" if "sqlite" in settings.database_url or "postgres" in settings.database_url else "Unknown"
    }


@router.get("/health")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        dict: Health status
    """
    return {
        "status": "healthy",
        "service": settings.app_name,
        "version": settings.app_version
    }


@router.get("/health/live")
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.
    
    Checks if the application is running (doesn't check dependencies).
    
    Returns:
        dict: Liveness status
    """
    return {"status": "alive"}


@router.get("/health/ready")
async def readiness_probe(db: AsyncSession = Depends(get_db)):
    """
    Kubernetes readiness probe endpoint.
    
    Checks if the application is ready to serve traffic (checks database connection).
    
    Args:
        db: Database session
        
    Returns:
        dict: Readiness status
    """
    try:
        # Test database connection
        await db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        return {
            "status": "not_ready",
            "database": "disconnected",
            "error": str(e)
        }
