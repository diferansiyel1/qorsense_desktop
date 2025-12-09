"""
Pydantic Schemas Package.

This package contains all Pydantic schemas for request/response validation.

Modules:
- common: Pagination and shared schemas
- sensor: Sensor data ingestion schemas with strict validation
- auth: Authentication and authorization schemas
"""

from backend.schemas.common import PaginationParams, PaginatedResponse
from backend.schemas.sensor import (
    # Enumerations
    SourceType,
    SensorStatus,
    # Reading schemas
    SensorReadingBase,
    SensorReadingCreate,
    SensorReadingBulk,
    # Sensor management
    SensorCreate,
    SensorResponse,
    # CSV Import
    CSVImportConfig,
    CSVImportResult,
    CSVValidationError,
)
from backend.schemas.auth import (
    # Token schemas
    Token,
    TokenPayload,
    TokenRefreshRequest,
    # User schemas
    UserLogin,
    UserCreate,
    UserResponse,
    UserUpdate,
    # Organization schemas
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    # Registration
    RegisterRequest,
    RegisterResponse,
)

__all__ = [
    # Common
    "PaginationParams",
    "PaginatedResponse",
    # Enums
    "SourceType",
    "SensorStatus",
    # Readings
    "SensorReadingBase",
    "SensorReadingCreate",
    "SensorReadingBulk",
    # Sensors
    "SensorCreate",
    "SensorResponse",
    # CSV Import
    "CSVImportConfig",
    "CSVImportResult",
    "CSVValidationError",
    # Auth - Tokens
    "Token",
    "TokenPayload",
    "TokenRefreshRequest",
    # Auth - Users
    "UserLogin",
    "UserCreate",
    "UserResponse",
    "UserUpdate",
    # Auth - Organizations
    "OrganizationCreate",
    "OrganizationResponse",
    "OrganizationUpdate",
    # Auth - Registration
    "RegisterRequest",
    "RegisterResponse",
]
