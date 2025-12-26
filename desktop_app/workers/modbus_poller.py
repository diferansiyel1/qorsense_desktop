"""
Modbus Poller Implementation.

Provides a unified polling interface for both Modbus TCP and RTU connections
with connection pooling, circuit breaker integration, and structured logging.
"""
import logging
import time
from typing import Any

from .circuit_breaker import CircuitBreaker, CircuitBreakerConfig, CircuitOpenError
from .modbus_decoder import ModbusDecoder
from .models import ConnectionType, DeviceStatus, SensorConfig

# Structured logger
logger = logging.getLogger(__name__)


class ModbusConnection:
    """
    Wrapper for a Modbus client connection.
    
    Manages the lifecycle of a pymodbus client (TCP or RTU) and provides
    a consistent interface for reading registers.
    """

    def __init__(self, config: SensorConfig):
        """
        Initialize a Modbus connection.
        
        Args:
            config: Sensor configuration with connection parameters
        """
        self.config = config
        self._client: Any | None = None
        self._connected = False
        self._last_error: str | None = None

    @property
    def is_connected(self) -> bool:
        """Check if client is connected."""
        if self._client is None:
            return False
        try:
            return self._client.connected
        except AttributeError:
            return self._connected

    def connect(self) -> bool:
        """
        Establish connection to the Modbus device.
        
        Returns:
            True if connected successfully, False otherwise
        """
        try:
            self._client = self._create_client()
            result = self._client.connect()
            self._connected = result
            if not result:
                self._last_error = "Connection refused"
            return result
        except Exception as e:
            self._last_error = str(e)
            self._connected = False
            return False

    def disconnect(self) -> None:
        """Close the connection."""
        if self._client is not None:
            try:
                self._client.close()
            except Exception:
                pass
            self._client = None
            self._connected = False

    def _create_client(self) -> Any:
        """
        Create the appropriate pymodbus client.
        
        Returns:
            ModbusTcpClient or ModbusSerialClient instance
            
        Raises:
            ImportError: If pymodbus is not installed
        """
        if self.config.connection_type == ConnectionType.TCP:
            from pymodbus.client import ModbusTcpClient
            return ModbusTcpClient(
                host=self.config.ip,
                port=self.config.port,
                timeout=self.config.timeout
            )
        # RTU
        from pymodbus.client import ModbusSerialClient
        return ModbusSerialClient(
            port=self.config.serial_port,
            baudrate=self.config.baudrate,
            parity=self.config.parity,
            stopbits=self.config.stopbits,
            bytesize=self.config.bytesize,
            timeout=self.config.timeout
        )

    def read_registers(
        self,
        address: int,
        count: int,
        slave_id: int,
        function_code: int = 3
    ) -> list[int]:
        """
        Read holding or input registers.
        
        Args:
            address: Starting register address
            count: Number of registers to read
            slave_id: Modbus slave/unit ID
            function_code: 3 for holding registers, 4 for input registers
            
        Returns:
            List of register values
            
        Raises:
            ModbusReadError: If read fails
        """
        if not self.is_connected:
            raise ModbusReadError("Not connected")

        try:
            # Determine read method based on function code
            if function_code == 3:
                result = self._read_holding_registers(address, count, slave_id)
            elif function_code == 4:
                result = self._read_input_registers(address, count, slave_id)
            else:
                raise ModbusReadError(f"Unsupported function code: {function_code}")

            # Check for errors
            if result is None:
                raise ModbusReadError("No response received")

            if hasattr(result, 'isError') and result.isError():
                raise ModbusReadError(f"Modbus error: {result}")

            return list(result.registers)

        except ModbusReadError:
            raise
        except Exception as e:
            raise ModbusReadError(f"Read failed: {e}")

    def _read_holding_registers(
        self,
        address: int,
        count: int,
        slave_id: int
    ) -> Any:
        """
        Read holding registers with pymodbus version compatibility.
        
        Handles API differences between pymodbus versions:
        - 3.11+: uses device_id parameter
        - 3.0-3.10: uses slave parameter
        - 2.x: uses unit parameter
        """
        # Try pymodbus 3.11+ first (device_id parameter)
        try:
            return self._client.read_holding_registers(
                address,
                count=count,
                device_id=slave_id
            )
        except TypeError:
            pass

        # Try pymodbus 3.0-3.10 (slave parameter as keyword)
        try:
            return self._client.read_holding_registers(
                address,
                count=count,
                slave=slave_id
            )
        except TypeError:
            pass

        # Fallback for pymodbus 2.x (unit parameter)
        return self._client.read_holding_registers(
            address,
            count,
            unit=slave_id
        )

    def _read_input_registers(
        self,
        address: int,
        count: int,
        slave_id: int
    ) -> Any:
        """
        Read input registers with pymodbus version compatibility.
        """
        # Try pymodbus 3.11+ first
        try:
            return self._client.read_input_registers(
                address,
                count=count,
                device_id=slave_id
            )
        except TypeError:
            pass

        # Try pymodbus 3.0-3.10
        try:
            return self._client.read_input_registers(
                address,
                count=count,
                slave=slave_id
            )
        except TypeError:
            pass

        # Fallback for 2.x
        return self._client.read_input_registers(
            address,
            count,
            unit=slave_id
        )


class ModbusReadError(Exception):
    """Exception raised when Modbus read operation fails."""
    pass


class ModbusPoller:
    """
    High-level Modbus polling engine with connection pooling and circuit breakers.
    
    Features:
    - Automatic connection management
    - Connection pooling per endpoint
    - Circuit breaker integration for fault tolerance
    - Structured JSON logging
    - Data type decoding
    
    Example:
        >>> from desktop_app.workers.models import SensorConfig, DataType
        >>> 
        >>> config = SensorConfig(
        ...     name="temperature",
        ...     ip="192.168.1.100",
        ...     register_address=100,
        ...     data_type=DataType.FLOAT32_BE
        ... )
        >>> 
        >>> poller = ModbusPoller()
        >>> poller.add_sensor(config)
        >>> 
        >>> # Poll all sensors
        >>> results = poller.poll_all()
        >>> for sensor_id, (value, timestamp) in results.items():
        ...     print(f"{sensor_id}: {value}")
    """

    def __init__(
        self,
        circuit_breaker_config: CircuitBreakerConfig | None = None
    ):
        """
        Initialize the poller.
        
        Args:
            circuit_breaker_config: Optional configuration for circuit breakers
        """
        self._sensors: dict[str, SensorConfig] = {}
        self._connections: dict[str, ModbusConnection] = {}
        self._circuit_breakers: dict[str, CircuitBreaker] = {}
        self._decoder = ModbusDecoder()
        self._cb_config = circuit_breaker_config or CircuitBreakerConfig()

    def add_sensor(self, config: SensorConfig) -> None:
        """
        Add a sensor to the poller.
        
        Args:
            config: Sensor configuration
        """
        sensor_id = config.name
        self._sensors[sensor_id] = config

        # Create circuit breaker
        self._circuit_breakers[sensor_id] = CircuitBreaker(
            device_id=sensor_id,
            config=CircuitBreakerConfig(
                failure_threshold=config.max_retries
            )
        )

        # Log addition
        self._log_event("sensor_added", sensor_id, {
            "connection_type": config.connection_type.value,
            "endpoint": config.get_connection_key(),
            "register": config.register_address,
            "data_type": config.data_type.value
        })

    def remove_sensor(self, sensor_id: str) -> bool:
        """
        Remove a sensor from the poller.
        
        Args:
            sensor_id: Sensor name/identifier
            
        Returns:
            True if removed, False if not found
        """
        if sensor_id not in self._sensors:
            return False

        del self._sensors[sensor_id]

        if sensor_id in self._circuit_breakers:
            del self._circuit_breakers[sensor_id]

        # Note: Connection pool is shared, don't disconnect

        self._log_event("sensor_removed", sensor_id, {})
        return True

    def get_sensor_status(self, sensor_id: str) -> DeviceStatus:
        """
        Get current status of a sensor.
        
        Args:
            sensor_id: Sensor name/identifier
            
        Returns:
            DeviceStatus enum value
        """
        cb = self._circuit_breakers.get(sensor_id)
        if cb is None:
            return DeviceStatus.UNKNOWN
        return cb.get_device_status()

    def poll_sensor(
        self,
        sensor_id: str
    ) -> tuple[float | None, float, str | None]:
        """
        Poll a single sensor.
        
        Args:
            sensor_id: Sensor name/identifier
            
        Returns:
            Tuple of (value, timestamp, error_message)
            - value is None if read failed
            - error_message is None if successful
        """
        timestamp = time.time()

        if sensor_id not in self._sensors:
            return None, timestamp, f"Sensor not found: {sensor_id}"

        config = self._sensors[sensor_id]
        cb = self._circuit_breakers.get(sensor_id)

        # Check circuit breaker
        if cb and not cb.allow_request():
            self._log_event("circuit_open", sensor_id, {
                "retry_in": cb.time_until_retry
            })
            return None, timestamp, f"Circuit open, retry in {cb.time_until_retry:.1f}s"

        try:
            # Get or create connection
            connection = self._get_connection(config)

            # Ensure connected
            if not connection.is_connected:
                if not connection.connect():
                    raise ModbusReadError(f"Connection failed: {connection._last_error}")
                self._log_event("connected", sensor_id, {
                    "endpoint": config.get_connection_key()
                })

            # Read registers
            registers = connection.read_registers(
                address=config.register_address,
                count=config.register_count,
                slave_id=config.slave_id,
                function_code=config.function_code
            )

            # Apply value_register_offset for sensors with extended data blocks
            # (e.g., Visiferm returns 10 registers, value is in positions 2-3)
            offset = getattr(config, 'value_register_offset', 0)
            if offset > 0:
                # Get number of registers needed for data type
                type_to_count = {
                    'int16': 1, 'uint16': 1,
                    'float32_be': 2, 'float32_le': 2, 'float32_bs': 2, 'float32_ws': 2,
                    'int32_be': 2, 'int32_le': 2, 'uint32_be': 2, 'uint32_le': 2,
                }
                data_type_str = config.data_type.value if hasattr(config.data_type, 'value') else str(config.data_type)
                reg_count = type_to_count.get(data_type_str, 2)

                if len(registers) >= offset + reg_count:
                    registers = registers[offset:offset + reg_count]

            # Decode value
            raw_value = self._decoder.decode(registers, config.data_type)

            # Apply scaling
            scaled_value = (raw_value * config.scale_factor) + config.offset

            # Record success
            if cb:
                cb.record_success()

            # Log successful read
            self._log_event("read_success", sensor_id, {
                "raw_registers": ModbusDecoder.format_registers(registers),
                "raw_value": raw_value,
                "scaled_value": scaled_value
            }, level="DEBUG")

            return scaled_value, timestamp, None

        except (ModbusReadError, CircuitOpenError) as e:
            error_msg = str(e)
            if cb:
                cb.record_failure()

            self._log_event("read_error", sensor_id, {
                "error": error_msg,
                "failure_count": cb.failure_count if cb else 0
            }, level="WARNING")

            return None, timestamp, error_msg

        except Exception as e:
            error_msg = f"Unexpected error: {e}"
            if cb:
                cb.record_failure()

            self._log_event("read_error", sensor_id, {
                "error": error_msg,
                "exception_type": type(e).__name__
            }, level="ERROR")

            return None, timestamp, error_msg

    def poll_all(self) -> dict[str, tuple[float | None, float, str | None]]:
        """
        Poll all registered sensors.
        
        Returns:
            Dictionary of sensor_id -> (value, timestamp, error)
        """
        results = {}
        for sensor_id in self._sensors:
            results[sensor_id] = self.poll_sensor(sensor_id)
        return results

    def get_healthy_sensors(self) -> list[str]:
        """
        Get list of sensors with ONLINE status.
        
        Returns:
            List of sensor IDs
        """
        return [
            sensor_id
            for sensor_id in self._sensors
            if self.get_sensor_status(sensor_id) == DeviceStatus.ONLINE
        ]

    def get_offline_sensors(self) -> list[str]:
        """
        Get list of sensors with OFFLINE status.
        
        Returns:
            List of sensor IDs
        """
        return [
            sensor_id
            for sensor_id in self._sensors
            if self.get_sensor_status(sensor_id) == DeviceStatus.OFFLINE
        ]

    def _get_connection(self, config: SensorConfig) -> ModbusConnection:
        """
        Get or create a connection for the sensor's endpoint.
        
        Implements connection pooling by endpoint.
        """
        connection_key = config.get_connection_key()

        if connection_key not in self._connections:
            self._connections[connection_key] = ModbusConnection(config)

        return self._connections[connection_key]

    def disconnect_all(self) -> None:
        """Disconnect all connections."""
        for connection in self._connections.values():
            connection.disconnect()
        self._connections.clear()

        self._log_event("disconnected_all", "system", {
            "connection_count": len(self._connections)
        })

    def reset_circuit_breakers(self) -> None:
        """Reset all circuit breakers to CLOSED state."""
        for cb in self._circuit_breakers.values():
            cb.reset()

        self._log_event("circuit_breakers_reset", "system", {
            "count": len(self._circuit_breakers)
        })

    def get_status_summary(self) -> dict[str, Any]:
        """
        Get complete status summary of the poller.
        
        Returns:
            Dictionary with sensor count, status breakdown, etc.
        """
        statuses = {
            DeviceStatus.ONLINE: 0,
            DeviceStatus.OFFLINE: 0,
            DeviceStatus.RECONNECTING: 0,
            DeviceStatus.UNKNOWN: 0
        }

        for sensor_id in self._sensors:
            status = self.get_sensor_status(sensor_id)
            statuses[status] += 1

        return {
            "total_sensors": len(self._sensors),
            "active_connections": len(self._connections),
            "status_breakdown": {
                status.value: count
                for status, count in statuses.items()
            },
            "sensors": {
                sensor_id: {
                    "status": self.get_sensor_status(sensor_id).value,
                    "endpoint": config.get_connection_key(),
                    "circuit_breaker": (
                        self._circuit_breakers[sensor_id].get_status_dict()
                        if sensor_id in self._circuit_breakers else None
                    )
                }
                for sensor_id, config in self._sensors.items()
            }
        }

    def _log_event(
        self,
        event: str,
        sensor_id: str,
        details: dict[str, Any],
        level: str = "INFO"
    ) -> None:
        """
        Log a structured event in JSON format.
        
        Args:
            event: Event name (e.g., "read_success", "connection_error")
            sensor_id: Sensor identifier
            details: Additional event details
            level: Log level (DEBUG, INFO, WARNING, ERROR)
        """
        import json
        from datetime import datetime, timezone

        log_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "sensor_id": sensor_id,
            **details
        }

        log_message = json.dumps(log_entry)

        log_func = getattr(logger, level.lower(), logger.info)
        log_func(log_message)
