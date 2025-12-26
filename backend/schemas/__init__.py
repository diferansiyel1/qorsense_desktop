"""
Pydantic Schemas Package.

This package contains all Pydantic schemas for request/response validation.

Modules:
- common: Pagination and shared schemas
- sensor: Sensor data ingestion schemas with strict validation
- auth: Authentication and authorization schemas
"""

from backend.schemas.auth import (
    # Organization schemas
    OrganizationCreate,
    OrganizationResponse,
    OrganizationUpdate,
    # Registration
    RegisterRequest,
    RegisterResponse,
    # Token schemas
    Token,
    TokenPayload,
    TokenRefreshRequest,
    UserCreate,
    # User schemas
    UserLogin,
    UserResponse,
    UserUpdate,
)
from backend.schemas.common import PaginatedResponse, PaginationParams
from backend.schemas.sensor import (
    # CSV Import
    CSVImportConfig,
    CSVImportResult,
    CSVValidationError,
    # Sensor management
    SensorCreate,
    # Reading schemas
    SensorReadingBase,
    SensorReadingBulk,
    SensorReadingCreate,
    SensorResponse,
    SensorStatus,
    # Enumerations
    SourceType,
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
