"""
QorSense v1 Backend Main Application

Refactored FastAPI application with modular router architecture.
All endpoint logic has been extracted into dedicated router modules.
"""

import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import logging
from contextlib import asynccontextmanager

# Router imports
from backend.api.routes import analytics, auth, health, reports, sensors, synthetic

# Core imports
from backend.core.config import settings
from backend.database import Base, engine
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# ========================================
# Logging Configuration
# ========================================
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
    handlers=[
        logging.FileHandler(settings.log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# ========================================
# Application Lifespan
# ========================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    
    Handles startup and shutdown events:
    - Startup: Create database tables
    - Shutdown: Dispose database engine
    """
    # Startup
    logger.info(f"🚀 Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Database: {settings.database_url.split('://')[0]}")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        logger.info("✓ Database tables created")

    yield

    # Shutdown
    logger.info("Shutting down backend...")
    await engine.dispose()
    logger.info("✓ Database connections closed")


# ========================================
# FastAPI Application
# ========================================
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Predictive Maintenance Platform for Sensor Analysis",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)


# ========================================
# Middleware Configuration
# ========================================
# Production-safe CORS: Only explicitly allowed origins and methods
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list + ["app://-", "app://index.html"],  # Add Electron origins
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "Accept", "Origin", "X-Requested-With"],
    expose_headers=["X-Request-ID"],
    max_age=600,  # Cache preflight for 10 minutes
)


# ========================================
# Router Registration
# ========================================
# Health check routes (no prefix)
app.include_router(health.router)

# Authentication routes
app.include_router(auth.router)

# API routes (protected endpoints)
app.include_router(sensors.router)
app.include_router(analytics.router)
app.include_router(synthetic.router)
app.include_router(reports.router)
from backend.api.routes import monitoring, tasks

app.include_router(monitoring.router)
app.include_router(tasks.router)

# Metrics Middleware
import time

from backend.core.metrics import REQUEST_COUNT, REQUEST_LATENCY
from starlette.middleware.base import BaseHTTPMiddleware


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        start_time = time.time()
        response = await call_next(request)
        process_time = time.time() - start_time

        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status=response.status_code
        ).inc()

        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(process_time)

        return response

app.add_middleware(MetricsMiddleware)

logger.info("✓ All routers registered")


# ========================================
# Startup Message
# ========================================
@app.on_event("startup")
async def startup_event():
    """Log startup completion."""
    logger.info("=" * 50)
    logger.info(f"{settings.app_name} Backend is ready!")
    logger.info(f"API Documentation: http://{settings.backend_host}:{settings.backend_port}/docs")
    logger.info("=" * 50)


# ========================================
# Application Entry Point
# ========================================
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.backend_host,
        port=settings.backend_port,
        reload=settings.backend_reload and settings.is_development,
        log_level=settings.log_level.lower()
    )
