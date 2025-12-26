"""
Sensor Pydantic Schemas - Industrial Data Ingestion Layer.

This module provides strict validation schemas for sensor data ingestion.
All schemas enforce type safety and data integrity rules required for
production-grade sensor data processing.

Key Features:
- Strict type validation with Pydantic v2
- ISO8601 timestamp validation with timezone awareness
- Value range constraints for industrial sensors
- Comprehensive error messages for debugging
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

# ========================================
# Enumerations
# ========================================

class SourceType(str, Enum):
    """
    Sensor data source type enumeration.
    
    Defines the origin of sensor data for proper routing
    and processing configuration.
    """
    CSV = "CSV"
    SCADA = "SCADA"
    IoT = "IoT"
    API = "API"
    MANUAL = "MANUAL"


class SensorStatus(str, Enum):
    """
    Sensor operational status enumeration.
    
    Used for health monitoring and maintenance scheduling.
    """
    ACTIVE = "active"
    INACTIVE = "inactive"
    MAINTENANCE = "maintenance"
    FAULTY = "faulty"


# ========================================
# Base Schemas
# ========================================

class SensorReadingBase(BaseModel):
    """
    Base schema for a single sensor reading.
    
    This is the fundamental unit of sensor data ingestion.
    All sensor readings must conform to this schema.
    
    Attributes:
        sensor_id: Unique identifier for the sensor (e.g., 'pH-01', 'TEMP-A3')
        timestamp: ISO8601 formatted timestamp with optional timezone
        value: The measured value from the sensor
        
    Validation Rules:
        - sensor_id must be 1-50 characters, alphanumeric with hyphens/underscores
        - timestamp must be valid ISO8601 format
        - value must be within reasonable industrial sensor range
    """
    sensor_id: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r'^[A-Za-z0-9_-]+$',
        description="Unique sensor identifier (alphanumeric, hyphens, underscores)",
        examples=["pH-01", "TEMP_A3", "pressure-sensor-1"]
    )
    timestamp: datetime = Field(
        ...,
        description="Reading timestamp in ISO8601 format"
    )
    value: float = Field(
        ...,
        ge=-1e9,  # Reasonable minimum for industrial sensors
        le=1e9,   # Reasonable maximum for industrial sensors
        description="Measured sensor value"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid",  # Strict: reject unknown fields
    )

    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_timestamp(cls, v: Any) -> datetime:
        """
        Parse and validate timestamp from various input formats.
        
        Supports:
        - datetime objects
        - ISO8601 strings (with or without timezone)
        - Common date formats
        
        Args:
            v: Input value (datetime or string)
            
        Returns:
            Parsed datetime object
            
        Raises:
            ValueError: If timestamp format is invalid
        """
        if isinstance(v, datetime):
            return v

        if isinstance(v, str):
            v = v.strip()

            # Handle common ISO8601 formats
            formats = [
                "%Y-%m-%dT%H:%M:%S.%f%z",  # Full ISO with microseconds and TZ
                "%Y-%m-%dT%H:%M:%S%z",     # ISO with TZ
                "%Y-%m-%dT%H:%M:%S.%f",    # ISO with microseconds
                "%Y-%m-%dT%H:%M:%S",       # Basic ISO
                "%Y-%m-%d %H:%M:%S.%f",    # Space separated with microseconds
                "%Y-%m-%d %H:%M:%S",       # Space separated
                "%Y-%m-%d",                # Date only
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(v, fmt)
                except ValueError:
                    continue

            # Try fromisoformat as last resort (Python 3.11+)
            try:
                return datetime.fromisoformat(v.replace('Z', '+00:00'))
            except ValueError:
                pass

            raise ValueError(
                f"Invalid timestamp format: '{v}'. "
                f"Expected ISO8601 format (e.g., '2024-01-15T10:30:00', "
                f"'2024-01-15T10:30:00.123456', '2024-01-15T10:30:00+03:00')"
            )

        raise ValueError(f"Timestamp must be string or datetime, got {type(v).__name__}")


class SensorReadingCreate(SensorReadingBase):
    """
    Schema for creating a new sensor reading.
    
    Used for single data point ingestion via API.
    Inherits all validation from SensorReadingBase.
    """
    pass


class SensorReadingBulk(BaseModel):
    """
    Schema for validating a single row during bulk CSV import.
    
    More permissive than SensorReadingCreate to handle
    real-world CSV data quality issues while still maintaining
    core data integrity.
    
    Attributes:
        timestamp: Optional - defaults to import time if not provided
        value: The sensor reading value
        
    Note:
        sensor_id is not included here as it's provided at the upload level,
        not per-row in CSV files.
    """
    timestamp: datetime | None = Field(
        default=None,
        description="Reading timestamp (optional, defaults to now)"
    )
    value: float = Field(
        ...,
        ge=-1e9,
        le=1e9,
        description="Measured sensor value"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="ignore",  # Allow extra columns in CSV
    )

    @field_validator('timestamp', mode='before')
    @classmethod
    def parse_optional_timestamp(cls, v: Any) -> datetime | None:
        """
        Parse timestamp with None handling for missing values.
        
        Args:
            v: Input value (datetime, string, or None/empty)
            
        Returns:
            Parsed datetime or None
        """
        if v is None or v == '' or (isinstance(v, str) and v.strip() == ''):
            return None

        # Reuse the robust parser from SensorReadingBase
        return SensorReadingBase.parse_timestamp(v)

    @field_validator('value', mode='before')
    @classmethod
    def parse_value(cls, v: Any) -> float:
        """
        Parse numeric value with robust error handling.
        
        Handles:
        - Numeric types (int, float)
        - String representations
        - Scientific notation
        
        Args:
            v: Input value
            
        Returns:
            Parsed float value
            
        Raises:
            ValueError: If value cannot be parsed as numeric
        """
        if isinstance(v, (int, float)):
            return float(v)

        if isinstance(v, str):
            v = v.strip()
            if v == '' or v.lower() in ('null', 'none', 'nan', 'na', '-'):
                raise ValueError("Empty or null value not allowed")
            try:
                return float(v)
            except ValueError:
                raise ValueError(f"Cannot parse '{v}' as numeric value")

        raise ValueError(f"Value must be numeric, got {type(v).__name__}")


# ========================================
# Sensor Management Schemas
# ========================================

class SensorCreate(BaseModel):
    """
    Schema for registering a new sensor in the system.
    
    Used when adding new sensors to the monitoring platform.
    
    Attributes:
        name: Human-readable sensor name
        location: Physical or logical location
        source_type: Data source type (CSV, SCADA, IoT, etc.)
        organization_id: Optional organization for multi-tenant setups
        config: Optional JSON configuration for source-specific settings
    """
    name: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Human-readable sensor name",
        examples=["pH Sensor - Tank A", "Temperature Probe #3"]
    )
    location: str = Field(
        ...,
        min_length=1,
        max_length=200,
        description="Sensor physical or logical location",
        examples=["Building A - Floor 2", "Production Line 1"]
    )
    source_type: SourceType = Field(
        default=SourceType.CSV,
        description="Data source type"
    )
    organization_id: int | None = Field(
        default=None,
        description="Organization ID for multi-tenant setups"
    )
    config: dict | None = Field(
        default=None,
        description="Source-specific configuration (e.g., SCADA IP, IoT topic)"
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
        extra="forbid",
    )


class SensorResponse(BaseModel):
    """
    Schema for sensor data in API responses.
    
    Includes computed fields for health status and latest analysis.
    
    Attributes:
        id: Unique sensor identifier
        name: Human-readable name
        location: Physical location
        source_type: Data source type
        organization_id: Optional organization ID
        latest_health_score: Most recent health score (0-100)
        latest_status: Current operational status
        latest_analysis_timestamp: When last analysis was performed
    """
    id: str = Field(..., description="Unique sensor identifier")
    name: str = Field(..., description="Sensor name")
    location: str = Field(..., description="Sensor location")
    source_type: SourceType = Field(..., description="Data source type")
    organization_id: int | None = Field(None, description="Organization ID")
    latest_health_score: float = Field(100.0, ge=0, le=100, description="Latest health score")
    latest_status: str = Field("Normal", description="Current status")
    latest_analysis_timestamp: datetime | None = Field(None, description="Last analysis time")

    model_config = ConfigDict(from_attributes=True)


# ========================================
# CSV Import Schemas
# ========================================

class CSVImportConfig(BaseModel):
    """
    Configuration for CSV import operations.
    
    Controls how CSV files are parsed and validated during import.
    
    Attributes:
        has_header: Whether CSV has a header row
        timestamp_column: Column index or name for timestamp
        value_column: Column index or name for value
        sensor_id_column: Optional column for sensor_id (if not provided at upload)
        skip_errors: Whether to skip invalid rows or fail fast
        chunk_size: Number of rows to process per chunk (memory optimization)
        date_format: Optional specific date format string
    """
    has_header: bool = Field(
        default=True,
        description="Whether CSV file has a header row"
    )
    timestamp_column: int | str = Field(
        default=0,
        description="Column index (0-based) or name for timestamp"
    )
    value_column: int | str = Field(
        default=1,
        description="Column index (0-based) or name for value"
    )
    sensor_id_column: int | str | None = Field(
        default=None,
        description="Optional column for sensor_id override"
    )
    skip_errors: bool = Field(
        default=True,
        description="Skip invalid rows instead of failing"
    )
    chunk_size: int = Field(
        default=5000,
        ge=100,
        le=50000,
        description="Rows per processing chunk"
    )
    date_format: str | None = Field(
        default=None,
        description="Specific date format (e.g., '%Y-%m-%d %H:%M:%S')"
    )

    model_config = ConfigDict(extra="forbid")


class CSVImportResult(BaseModel):
    """
    Result summary for CSV import operations.
    
    Provides detailed statistics about the import process
    for logging, monitoring, and user feedback.
    
    Attributes:
        success: Whether import completed (may have partial errors)
        sensor_id: Target sensor identifier
        total_rows: Total rows in the CSV file
        imported_rows: Successfully imported rows
        failed_rows: Rows that failed validation
        skipped_rows: Rows skipped (e.g., empty lines)
        error_samples: Sample of error messages (max 10)
        import_duration_ms: Import processing time
        chunks_processed: Number of chunks processed
    """
    success: bool = Field(..., description="Import completed successfully")
    sensor_id: str = Field(..., description="Target sensor ID")
    total_rows: int = Field(..., ge=0, description="Total rows in CSV")
    imported_rows: int = Field(..., ge=0, description="Successfully imported")
    failed_rows: int = Field(..., ge=0, description="Failed validation")
    skipped_rows: int = Field(0, ge=0, description="Skipped rows (empty)")
    error_samples: list[str] = Field(
        default_factory=list,
        max_length=10,
        description="Sample error messages (max 10)"
    )
    import_duration_ms: int = Field(..., ge=0, description="Processing time in ms")
    chunks_processed: int = Field(1, ge=1, description="Number of chunks")

    @property
    def success_rate(self) -> float:
        """Calculate import success rate as percentage."""
        if self.total_rows == 0:
            return 0.0
        return (self.imported_rows / self.total_rows) * 100

    model_config = ConfigDict(from_attributes=True)


class CSVValidationError(BaseModel):
    """
    Detailed validation error for a CSV row.
    
    Used for comprehensive error reporting during import.
    """
    row_number: int = Field(..., ge=1, description="1-indexed row number")
    column: str | None = Field(None, description="Column name if applicable")
    value: str | None = Field(None, description="Invalid value")
    error: str = Field(..., description="Error description")

    def __str__(self) -> str:
        if self.column:
            return f"Row {self.row_number}, Column '{self.column}': {self.error}"
        return f"Row {self.row_number}: {self.error}"
