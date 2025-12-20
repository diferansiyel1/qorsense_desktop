"""
Pydantic Models for Modbus Sensor Configuration.

This module defines type-safe configuration models for Modbus TCP/RTU sensors,
including data types, connection parameters, and device status tracking.
"""
from enum import Enum
from typing import Literal, Optional, Any
from pydantic import BaseModel, Field, field_validator, model_validator


class DataType(str, Enum):
    """
    Supported data types for Modbus register decoding.
    
    Naming convention: {TYPE}{BITS}_{ENDIANNESS}
    - BE: Big-Endian (network byte order)
    - LE: Little-Endian
    - BS: Byte-Swapped within each 16-bit word
    - WS: Word-Swapped (swap the two 16-bit words)
    """
    # 32-bit Floating Point
    FLOAT32_BE = "float32_be"      # Big-endian (ABCD)
    FLOAT32_LE = "float32_le"      # Little-endian (DCBA)
    FLOAT32_BS = "float32_bs"      # Byte-swapped (BADC)
    FLOAT32_WS = "float32_ws"      # Word-swapped (CDAB)
    
    # 16-bit Integers
    INT16 = "int16"
    UINT16 = "uint16"
    
    # 32-bit Integers
    INT32_BE = "int32_be"
    INT32_LE = "int32_le"
    UINT32_BE = "uint32_be"
    UINT32_LE = "uint32_le"


class ConnectionType(str, Enum):
    """Modbus connection type enumeration."""
    TCP = "TCP"
    RTU = "RTU"


class DeviceStatus(str, Enum):
    """Device connection status for circuit breaker pattern."""
    ONLINE = "ONLINE"
    OFFLINE = "OFFLINE"
    RECONNECTING = "RECONNECTING"
    UNKNOWN = "UNKNOWN"


class CircuitState(str, Enum):
    """Circuit breaker state machine states."""
    CLOSED = "CLOSED"       # Normal operation
    OPEN = "OPEN"           # Failures exceeded threshold, blocking requests
    HALF_OPEN = "HALF_OPEN" # Testing if device recovered


class SensorConfig(BaseModel):
    """
    Configuration for a single Modbus sensor/register.
    
    This model supports both Modbus TCP and RTU connections with full
    configuration of data types, scaling, and fault tolerance parameters.
    
    Attributes:
        name: Human-readable sensor identifier
        connection_type: TCP or RTU connection
        ip: IP address for TCP connections
        port: TCP port (default 502)
        serial_port: Serial port path for RTU connections
        baudrate: Serial baud rate
        parity: Serial parity (N/E/O)
        stopbits: Serial stop bits (1/2)
        bytesize: Serial data bits (7/8)
        slave_id: Modbus slave/unit ID (1-247)
        register_address: Starting register address (0-65535)
        register_count: Number of registers to read
        data_type: Data type for decoding
        scale_factor: Multiplication factor for raw value
        offset: Offset to add after scaling
        timeout: Read timeout in seconds
        max_retries: Max consecutive failures before circuit opens
    
    Example:
        >>> config = SensorConfig(
        ...     name="tank1_temperature",
        ...     connection_type=ConnectionType.TCP,
        ...     ip="192.168.1.100",
        ...     port=502,
        ...     slave_id=1,
        ...     register_address=100,
        ...     data_type=DataType.FLOAT32_BE,
        ...     scale_factor=0.1
        ... )
    """
    # Identification
    name: str = Field(..., min_length=1, max_length=100, description="Sensor identifier")
    
    # Connection type
    connection_type: ConnectionType = Field(
        default=ConnectionType.TCP,
        description="TCP or RTU connection"
    )
    
    # TCP Parameters
    ip: str = Field(
        default="192.168.1.100",
        description="IP address for TCP connections"
    )
    port: int = Field(
        default=502,
        ge=1,
        le=65535,
        description="TCP port number"
    )
    
    # RTU Parameters
    serial_port: str = Field(
        default="/dev/ttyUSB0",
        description="Serial port path (e.g., COM3, /dev/ttyUSB0)"
    )
    baudrate: int = Field(
        default=19200,
        description="Serial baud rate"
    )
    parity: Literal["N", "E", "O"] = Field(
        default="N",
        description="Serial parity: N=None, E=Even, O=Odd"
    )
    stopbits: Literal[1, 2] = Field(
        default=1,
        description="Serial stop bits"
    )
    bytesize: Literal[7, 8] = Field(
        default=8,
        description="Serial data bits"
    )
    
    # Modbus Parameters
    slave_id: int = Field(
        default=1,
        ge=1,
        le=247,
        description="Modbus slave/unit ID"
    )
    register_address: int = Field(
        default=0,
        ge=0,
        le=65535,
        description="Starting register address"
    )
    register_count: int = Field(
        default=2,
        ge=1,
        le=125,
        description="Number of registers to read"
    )
    function_code: int = Field(
        default=3,
        ge=1,
        le=4,
        description="Modbus function code (3=Holding, 4=Input)"
    )
    
    # Data Processing
    data_type: DataType = Field(
        default=DataType.FLOAT32_BE,
        description="Data type for register decoding"
    )
    scale_factor: float = Field(
        default=1.0,
        description="Multiplication factor for raw value"
    )
    offset: float = Field(
        default=0.0,
        description="Offset added after scaling"
    )
    
    # Fault Tolerance
    timeout: float = Field(
        default=3.0,
        gt=0,
        le=60,
        description="Read timeout in seconds"
    )
    max_retries: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Max failures before circuit opens"
    )
    
    # Polling
    poll_interval: float = Field(
        default=1.0,
        gt=0,
        description="Polling interval in seconds"
    )
    
    # Extended data extraction (for Visiferm-style sensors)
    value_register_offset: int = Field(
        default=0,
        ge=0,
        description="Offset within register response where actual value starts (e.g., 2 for Visiferm PMC1/PMC6)"
    )

    @field_validator("ip")
    @classmethod
    def validate_ip(cls, v: str) -> str:
        """Validate IP address format (basic check)."""
        if v and not v.replace(".", "").replace(":", "").isalnum():
            # Allow hostnames and IPs
            pass
        return v.strip()

    @field_validator("baudrate")
    @classmethod
    def validate_baudrate(cls, v: int) -> int:
        """Validate baud rate is a standard value."""
        standard_rates = [300, 1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200]
        if v not in standard_rates:
            # Allow non-standard rates but they may cause issues
            pass
        return v

    @model_validator(mode="after")
    def validate_register_count_for_data_type(self) -> "SensorConfig":
        """Ensure register_count matches data_type requirements."""
        type_to_count = {
            DataType.INT16: 1,
            DataType.UINT16: 1,
            DataType.FLOAT32_BE: 2,
            DataType.FLOAT32_LE: 2,
            DataType.FLOAT32_BS: 2,
            DataType.FLOAT32_WS: 2,
            DataType.INT32_BE: 2,
            DataType.INT32_LE: 2,
            DataType.UINT32_BE: 2,
            DataType.UINT32_LE: 2,
        }
        required = type_to_count.get(self.data_type, 2)
        if self.register_count < required:
            self.register_count = required
        return self

    def get_connection_key(self) -> str:
        """
        Get a unique key for connection pooling.
        
        Returns:
            Unique string identifying the connection endpoint.
        """
        if self.connection_type == ConnectionType.TCP:
            return f"tcp://{self.ip}:{self.port}"
        else:
            # Include all serial parameters to ensure unique connections
            return f"rtu://{self.serial_port}@{self.baudrate}-{self.parity}{self.bytesize}{self.stopbits}"

    def get_display_name(self) -> str:
        """
        Get a human-readable display name.
        
        Returns:
            Formatted string for UI display.
        """
        if self.connection_type == ConnectionType.TCP:
            return f"{self.name} ({self.ip}:{self.port}/Reg{self.register_address})"
        else:
            return f"{self.name} ({self.serial_port}/Reg{self.register_address})"

    class Config:
        """Pydantic model configuration."""
        use_enum_values = False  # Keep enum instances
        validate_assignment = True  # Validate on attribute assignment


class DeviceState(BaseModel):
    """
    Runtime state for a device/sensor connection.
    
    Tracks connection status, failure counts, and timing for
    circuit breaker pattern implementation.
    """
    sensor_id: str
    status: DeviceStatus = DeviceStatus.UNKNOWN
    circuit_state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None
    last_value: Optional[float] = None
    reconnect_attempt: int = 0
    next_retry_time: Optional[float] = None

    class Config:
        """Pydantic model configuration."""
        validate_assignment = True
