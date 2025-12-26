"""
Rate Limiting Middleware

Implements request rate limiting to prevent abuse.
"""

from backend.core.config import settings
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

# Create limiter instance
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=[f"{settings.rate_limit_per_minute}/minute"] if settings.rate_limit_enabled else [],
    enabled=settings.rate_limit_enabled
)


def get_limiter() -> Limiter:
    """Get rate limiter instance."""
    return limiter


# Rate limit exceeded handler
rate_limit_exceeded_handler = _rate_limit_exceeded_handler
