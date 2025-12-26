"""
Monitoring Routes

Exposes application metrics and advanced health checks.
"""

from backend.core.cache import get_redis
from backend.core.metrics import get_metrics
from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

@router.get("/metrics")
async def metrics():
    """
    Expose Prometheus metrics.
    """
    data, content_type = get_metrics()
    return Response(content=data, media_type=content_type)

@router.get("/health/redis")
async def redis_health():
    """
    Check Redis connection status.
    """
    redis = await get_redis()
    if not redis:
        return {"status": "down", "details": "Redis not connected"}

    try:
        await redis.ping()
        return {"status": "up", "details": "Redis connected"}
    except Exception as e:
        return {"status": "down", "details": str(e)}
