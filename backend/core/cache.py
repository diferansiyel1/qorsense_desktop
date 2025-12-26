"""
Caching Layer

Provides caching decorators and utilities using Redis (optional) or in-memory fallback.
"""

import logging
import os
import pickle
from collections.abc import Callable
from functools import wraps

import redis.asyncio as redis

logger = logging.getLogger(__name__)

# Redis Connection (Lazy init)
redis_client: redis.Redis | None = None


async def get_redis() -> redis.Redis | None:
    """Get or initialize Redis client."""
    global redis_client
    if redis_client is None:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                redis_client = redis.from_url(redis_url, encoding="utf-8", decode_responses=False)
                await redis_client.ping()
                logger.info("Connected to Redis cache")
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {e}. Caching disabled.")
                redis_client = None
    return redis_client


def cache(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    Async cache decorator.
    
    Args:
        ttl_seconds: Time to live in seconds
        key_prefix: Prefix for cache key
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            key_parts = [key_prefix, func.__name__]
            key_parts.extend([str(arg) for arg in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = ":".join(key_parts)

            # Try to get from cache
            r = await get_redis()
            if r:
                try:
                    cached_data = await r.get(cache_key)
                    if cached_data:
                        logger.debug(f"Cache hit: {cache_key}")
                        return pickle.loads(cached_data)
                except Exception as e:
                    logger.warning(f"Cache get error: {e}")

            # Execute function
            result = await func(*args, **kwargs)

            # Set to cache
            if r:
                try:
                    await r.setex(cache_key, ttl_seconds, pickle.dumps(result))
                except Exception as e:
                    logger.warning(f"Cache set error: {e}")

            return result
        return wrapper
    return decorator
