"""
Desktop App Workers Package.

This package provides background worker threads for data acquisition
and processing in the QorSense desktop application.

Modules:
    - live_worker: Modbus TCP/RTU sensor polling with circuit breaker
    - models: Pydantic configuration models for sensors
    - modbus_decoder: Data type decoding utilities
    - circuit_breaker: Fault tolerance pattern implementation
    - modbus_poller: Connection pooling and polling engine
    - file_loader: CSV/Excel file loading worker
    - analysis_worker: Signal analysis worker
"""

# Main worker exports
# Analysis (existing)
from .analysis_worker import AnalysisWorker
from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitBreakerRegistry, CircuitOpenError

# File loading (existing)
from .file_loader import FileLoadWorker
from .live_worker import (
    ModbusConnectionConfig,  # Legacy, deprecated
    ModbusWorker,
    StructuredLogger,
    ThreadSafeDataBuffer,
    list_available_ports,
)

# Utility exports
from .modbus_decoder import ModbusDecoder
from .modbus_poller import ModbusConnection, ModbusPoller, ModbusReadError

# Model exports
from .models import CircuitState, ConnectionType, DataType, DeviceState, DeviceStatus, SensorConfig

__all__ = [
    # Main worker
    "ModbusWorker",
    "ModbusConnectionConfig",
    "ThreadSafeDataBuffer",
    "StructuredLogger",
    "list_available_ports",

    # Models
    "SensorConfig",
    "ConnectionType",
    "DataType",
    "DeviceStatus",
    "CircuitState",
    "DeviceState",

    # Utilities
    "ModbusDecoder",
    "CircuitBreaker",
    "CircuitBreakerConfig",
    "CircuitBreakerRegistry",
    "CircuitOpenError",
    "ModbusPoller",
    "ModbusConnection",
    "ModbusReadError",

    # Existing workers
    "FileLoadWorker",
    "AnalysisWorker"
]
