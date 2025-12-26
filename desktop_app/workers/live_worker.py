"""
Production-Ready Modbus TCP/RTU Live Data Worker.

A hardened, configuration-driven sensor monitoring system with:
- Circuit breaker pattern for fault tolerance
- Thread-safe data access with QReadWriteLock
- Structured JSON logging
- Background reconnection with exponential backoff
- Full support for multiple data types and endianness configurations

This module provides the main ModbusWorker class that runs in a separate
QThread and polls configured sensors at specified intervals.
"""
import json
import logging
import threading
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import Any

from PyQt6.QtCore import QMutex, QReadWriteLock, QThread, pyqtSignal

from .modbus_decoder import ModbusDecoder
from .modbus_poller import ModbusPoller

# Local imports
from .models import ConnectionType, DataType, DeviceState, DeviceStatus, SensorConfig

# --- Structured Logger ---

class StructuredLogger:
    """
    JSON-format structured logger for Modbus operations.
    
    Provides consistent, machine-parseable logging for all connection,
    read, and error events. Suitable for centralized log aggregation
    systems like ELK, Splunk, or CloudWatch.
    
    Example output:
        {"timestamp": "2024-12-18T21:30:00Z", "level": "INFO", 
         "event": "connection_established", "sensor_id": "tank1_temp",
         "device": "192.168.1.100:502", "connection_type": "TCP"}
    """

    def __init__(self, logger_name: str = "modbus_worker"):
        """Initialize structured logger."""
        self._logger = logging.getLogger(logger_name)

    def _emit(self, level: str, event: str, sensor_id: str, **kwargs) -> None:
        """Emit a structured log entry."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": level,
            "event": event,
            "sensor_id": sensor_id,
            **kwargs
        }

        log_func = getattr(self._logger, level.lower(), self._logger.info)
        log_func(json.dumps(entry))

    def log_connection(
        self,
        sensor_id: str,
        status: str,
        device: str,
        connection_type: str,
        details: dict[str, Any] | None = None
    ) -> None:
        """Log connection events."""
        self._emit(
            "INFO",
            f"connection_{status}",
            sensor_id,
            device=device,
            connection_type=connection_type,
            **(details or {})
        )

    def log_connection_drop(
        self,
        sensor_id: str,
        device: str,
        retry_count: int,
        reason: str
    ) -> None:
        """Log connection drop events."""
        self._emit(
            "WARNING",
            "connection_drop",
            sensor_id,
            device=device,
            retry_count=retry_count,
            reason=reason
        )

    def log_retry_attempt(
        self,
        sensor_id: str,
        device: str,
        attempt: int,
        delay: float
    ) -> None:
        """Log reconnection retry attempts."""
        self._emit(
            "INFO",
            "retry_attempt",
            sensor_id,
            device=device,
            attempt=attempt,
            delay_seconds=delay
        )

    def log_read_success(
        self,
        sensor_id: str,
        value: float,
        raw_registers: list[int],
        timestamp: float
    ) -> None:
        """Log successful reads."""
        self._emit(
            "DEBUG",
            "read_success",
            sensor_id,
            value=value,
            raw_registers=ModbusDecoder.format_registers(raw_registers) if raw_registers else "[]",
            timestamp=timestamp
        )

    def log_read_error(
        self,
        sensor_id: str,
        error: str,
        failure_count: int
    ) -> None:
        """Log read errors."""
        self._emit(
            "WARNING",
            "read_error",
            sensor_id,
            error=error,
            failure_count=failure_count
        )

    def log_circuit_state_change(
        self,
        sensor_id: str,
        old_state: str,
        new_state: str
    ) -> None:
        """Log circuit breaker state changes."""
        level = "WARNING" if new_state == "OPEN" else "INFO"
        self._emit(
            level,
            "circuit_state_change",
            sensor_id,
            old_state=old_state,
            new_state=new_state
        )

    def log_critical_error(
        self,
        sensor_id: str,
        error_type: str,
        message: str,
        traceback: str | None = None
    ) -> None:
        """Log critical errors."""
        self._emit(
            "ERROR",
            "critical_error",
            sensor_id,
            error_type=error_type,
            message=message,
            traceback=traceback
        )


# --- Thread-Safe Data Buffer ---

class ThreadSafeDataBuffer:
    """
    Thread-safe buffer for sensor data with read/write locking.
    
    Uses QReadWriteLock for efficient concurrent access:
    - Multiple readers can access simultaneously
    - Writers get exclusive access
    
    The buffer automatically rotates to prevent memory overflow,
    keeping only the most recent samples.
    
    Example:
        >>> buffer = ThreadSafeDataBuffer(max_size=1000)
        >>> buffer.write("sensor_1", 42.5, time.time())
        >>> latest = buffer.read_latest("sensor_1", count=10)
    """

    def __init__(self, max_size: int = 10000):
        """
        Initialize the buffer.
        
        Args:
            max_size: Maximum samples per sensor before rotation
        """
        self._lock = QReadWriteLock()
        self._data: dict[str, list[tuple[float, float]]] = {}
        self._max_size = max_size
        self._latest_values: dict[str, tuple[float, float]] = {}

    def write(self, sensor_id: str, value: float, timestamp: float) -> None:
        """
        Write a sample to the buffer.
        
        Thread-safe with exclusive write lock.
        
        Args:
            sensor_id: Sensor identifier
            value: Sensor value
            timestamp: Unix timestamp
        """
        self._lock.lockForWrite()
        try:
            if sensor_id not in self._data:
                self._data[sensor_id] = []

            self._data[sensor_id].append((value, timestamp))
            self._latest_values[sensor_id] = (value, timestamp)

            # Rotate if exceeding max size
            if len(self._data[sensor_id]) > self._max_size:
                # Keep last 80% to avoid frequent rotations
                keep_count = int(self._max_size * 0.8)
                self._data[sensor_id] = self._data[sensor_id][-keep_count:]
        finally:
            self._lock.unlock()

    def read_latest(
        self,
        sensor_id: str,
        count: int = 100
    ) -> list[tuple[float, float]]:
        """
        Read the latest N samples for a sensor.
        
        Thread-safe with shared read lock.
        
        Args:
            sensor_id: Sensor identifier
            count: Number of samples to retrieve
            
        Returns:
            List of (value, timestamp) tuples, newest last
        """
        self._lock.lockForRead()
        try:
            if sensor_id not in self._data:
                return []
            return self._data[sensor_id][-count:]
        finally:
            self._lock.unlock()

    def read_all(self, sensor_id: str) -> list[tuple[float, float]]:
        """
        Read all samples for a sensor.
        
        Args:
            sensor_id: Sensor identifier
            
        Returns:
            List of (value, timestamp) tuples
        """
        self._lock.lockForRead()
        try:
            if sensor_id not in self._data:
                return []
            return list(self._data[sensor_id])
        finally:
            self._lock.unlock()

    def get_latest_value(self, sensor_id: str) -> tuple[float, float] | None:
        """
        Get the most recent value for a sensor.
        
        Args:
            sensor_id: Sensor identifier
            
        Returns:
            (value, timestamp) tuple or None
        """
        self._lock.lockForRead()
        try:
            return self._latest_values.get(sensor_id)
        finally:
            self._lock.unlock()

    def get_all_latest_values(self) -> dict[str, tuple[float, float]]:
        """
        Get the most recent value for all sensors.
        
        Returns:
            Dictionary of sensor_id -> (value, timestamp)
        """
        self._lock.lockForRead()
        try:
            return dict(self._latest_values)
        finally:
            self._lock.unlock()

    def clear(self, sensor_id: str | None = None) -> None:
        """
        Clear buffer data.
        
        Args:
            sensor_id: Specific sensor to clear, or None for all
        """
        self._lock.lockForWrite()
        try:
            if sensor_id:
                self._data.pop(sensor_id, None)
                self._latest_values.pop(sensor_id, None)
            else:
                self._data.clear()
                self._latest_values.clear()
        finally:
            self._lock.unlock()

    def get_sample_count(self, sensor_id: str) -> int:
        """Get number of samples for a sensor."""
        self._lock.lockForRead()
        try:
            return len(self._data.get(sensor_id, []))
        finally:
            self._lock.unlock()


# --- Reconnection Manager ---

class ReconnectionManager:
    """
    Background reconnection manager with exponential backoff.
    
    Handles reconnection attempts for offline devices in a separate
    thread to prevent blocking the main polling loop.
    """

    def __init__(
        self,
        poller: ModbusPoller,
        logger: StructuredLogger,
        on_device_recovered: Callable[[str], None] | None = None
    ):
        """
        Initialize the manager.
        
        Args:
            poller: ModbusPoller instance to reconnect devices on
            logger: Structured logger for logging attempts
            on_device_recovered: Callback when device comes back online
        """
        self._poller = poller
        self._logger = logger
        self._on_device_recovered = on_device_recovered

        self._pending_devices: dict[str, DeviceState] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread: threading.Thread | None = None

    def schedule_reconnect(self, sensor_id: str, config: SensorConfig) -> None:
        """
        Schedule a device for reconnection.
        
        Args:
            sensor_id: Sensor identifier
            config: Sensor configuration
        """
        with self._lock:
            if sensor_id not in self._pending_devices:
                state = DeviceState(
                    sensor_id=sensor_id,
                    status=DeviceStatus.RECONNECTING,
                    reconnect_attempt=0
                )
                self._pending_devices[sensor_id] = state

            state = self._pending_devices[sensor_id]
            state.reconnect_attempt += 1

            # Calculate backoff delay
            delay = min(2 ** state.reconnect_attempt, 60)  # Cap at 60s
            state.next_retry_time = time.time() + delay

            self._logger.log_retry_attempt(
                sensor_id,
                config.get_connection_key(),
                state.reconnect_attempt,
                delay
            )

    def cancel_reconnect(self, sensor_id: str) -> None:
        """Cancel pending reconnection for a device."""
        with self._lock:
            self._pending_devices.pop(sensor_id, None)

    def start(self) -> None:
        """Start the reconnection thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(
            target=self._reconnection_loop,
            daemon=True,
            name="ModbusReconnectionManager"
        )
        self._thread.start()

    def stop(self) -> None:
        """Stop the reconnection thread."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _reconnection_loop(self) -> None:
        """Background reconnection loop."""
        while self._running:
            now = time.time()
            devices_to_retry: list[str] = []

            with self._lock:
                for sensor_id, state in self._pending_devices.items():
                    if state.next_retry_time and now >= state.next_retry_time:
                        devices_to_retry.append(sensor_id)

            for sensor_id in devices_to_retry:
                self._attempt_reconnect(sensor_id)

            time.sleep(1.0)  # Check every second

    def _attempt_reconnect(self, sensor_id: str) -> None:
        """Attempt to reconnect a device."""
        # Try a test poll
        value, timestamp, error = self._poller.poll_sensor(sensor_id)

        if error is None:
            # Success! Device is back online
            with self._lock:
                self._pending_devices.pop(sensor_id, None)

            if self._on_device_recovered:
                self._on_device_recovered(sensor_id)
        else:
            # Still failing, reschedule with longer delay
            config = self._poller._sensors.get(sensor_id)
            if config:
                self.schedule_reconnect(sensor_id, config)


# --- Main ModbusWorker Class ---

class ModbusWorker(QThread):
    """
    Production-ready background worker for Modbus sensor polling.
    
    Features:
    - Configuration-driven: Accepts List[SensorConfig] instead of hardcoded params
    - Circuit breaker: Marks failing devices as OFFLINE after 3 failures
    - Thread-safe: Uses QReadWriteLock for data buffer access
    - Structured logging: JSON format for all events
    - Background reconnection: Exponential backoff for offline devices
    
    Signals:
        data_received(float, float): Emits (value, timestamp) for the first/primary sensor
        error_occurred(str): Emits error message on failures
        connection_status(bool): Emits True=connected, False=disconnected
        
        sensor_data_received(str, float, float): Emits (sensor_id, value, timestamp)
        device_status_changed(str, str): Emits (sensor_id, status) when device status changes
        batch_data_received(dict): Emits {sensor_id: (value, timestamp, error)}
    
    Example:
        >>> from desktop_app.workers.models import SensorConfig, ConnectionType, DataType
        >>> 
        >>> configs = [
        ...     SensorConfig(
        ...         name="tank1_temp",
        ...         connection_type=ConnectionType.TCP,
        ...         ip="192.168.1.100",
        ...         port=502,
        ...         slave_id=1,
        ...         register_address=100,
        ...         data_type=DataType.FLOAT32_BE
        ...     ),
        ...     SensorConfig(
        ...         name="tank1_pressure",
        ...         connection_type=ConnectionType.TCP,
        ...         ip="192.168.1.100",
        ...         port=502,
        ...         slave_id=1,
        ...         register_address=102,
        ...         data_type=DataType.FLOAT32_BE
        ...     )
        ... ]
        >>> 
        >>> worker = ModbusWorker(sensors=configs)
        >>> worker.data_received.connect(on_data)
        >>> worker.start()
    """

    # Legacy signals (for backward compatibility)
    data_received = pyqtSignal(float, float)  # (value, timestamp)
    error_occurred = pyqtSignal(str)
    connection_status = pyqtSignal(bool)  # True = connected

    # Enhanced signals
    sensor_data_received = pyqtSignal(str, float, float)  # (sensor_id, value, timestamp)
    device_status_changed = pyqtSignal(str, str)  # (sensor_id, status)
    batch_data_received = pyqtSignal(dict)  # {sensor_id: (value, timestamp, error)}

    def __init__(
        self,
        sensors: list[SensorConfig] | None = None,
        poll_interval: float = 1.0,
        buffer_size: int = 10000,
        # Legacy parameters for backward compatibility
        connection_type: str = "TCP",
        ip_address: str = "192.168.1.100",
        tcp_port: int = 502,
        serial_port: str = "COM1",
        baudrate: int = 9600,
        parity: str = "N",
        stopbits: int = 1,
        bytesize: int = 8,
        register_address: int = 0,
        slave_id: int = 1,
        scale_factor: float = 1.0,
        read_interval: float = 1.0,
        parent=None
    ):
        """
        Initialize the Modbus worker.
        
        Args:
            sensors: List of SensorConfig objects (preferred)
            poll_interval: Default polling interval in seconds
            buffer_size: Maximum samples per sensor in buffer
            
            Legacy Parameters (for backward compatibility):
                connection_type, ip_address, tcp_port, serial_port,
                baudrate, parity, stopbits, bytesize, register_address,
                slave_id, scale_factor, read_interval
        """
        super().__init__(parent)

        # Initialize components
        self._logger = StructuredLogger("modbus_worker")
        self._poller = ModbusPoller()
        self._data_buffer = ThreadSafeDataBuffer(max_size=buffer_size)
        self._reconnection_manager = ReconnectionManager(
            self._poller,
            self._logger,
            on_device_recovered=self._on_device_recovered
        )

        # State
        self._running = False
        self._poll_interval = poll_interval or read_interval
        self._primary_sensor_id: str | None = None
        self._device_statuses: dict[str, DeviceStatus] = {}
        self._status_lock = QMutex()

        # Add sensors
        if sensors:
            for config in sensors:
                self._add_sensor(config)
        elif connection_type:
            # Legacy mode: Create single sensor from parameters
            legacy_config = self._create_legacy_config(
                connection_type=connection_type,
                ip_address=ip_address,
                tcp_port=tcp_port,
                serial_port=serial_port,
                baudrate=baudrate,
                parity=parity,
                stopbits=stopbits,
                bytesize=bytesize,
                register_address=register_address,
                slave_id=slave_id,
                scale_factor=scale_factor,
                read_interval=read_interval
            )
            self._add_sensor(legacy_config)

    def _create_legacy_config(
        self,
        connection_type: str,
        ip_address: str,
        tcp_port: int,
        serial_port: str,
        baudrate: int,
        parity: str,
        stopbits: int,
        bytesize: int,
        register_address: int,
        slave_id: int,
        scale_factor: float,
        read_interval: float
    ) -> SensorConfig:
        """Create SensorConfig from legacy parameters."""
        conn_type = ConnectionType.TCP if connection_type.upper() == "TCP" else ConnectionType.RTU

        return SensorConfig(
            name="legacy_sensor",
            connection_type=conn_type,
            ip=ip_address,
            port=tcp_port,
            serial_port=serial_port,
            baudrate=baudrate,
            parity=parity.upper() if parity else "N",
            stopbits=stopbits,
            bytesize=bytesize,
            slave_id=slave_id,
            register_address=register_address,
            data_type=DataType.FLOAT32_BE,
            scale_factor=scale_factor,
            poll_interval=read_interval
        )

    def _add_sensor(self, config: SensorConfig) -> None:
        """Add a sensor to the poller."""
        self._poller.add_sensor(config)

        # Set first sensor as primary (for legacy signal compatibility)
        if self._primary_sensor_id is None:
            self._primary_sensor_id = config.name

        # Initialize status
        self._status_lock.lock()
        try:
            self._device_statuses[config.name] = DeviceStatus.UNKNOWN
        finally:
            self._status_lock.unlock()

    def add_sensor(self, config: SensorConfig) -> None:
        """
        Add a sensor at runtime.
        
        Args:
            config: Sensor configuration
        """
        self._add_sensor(config)

    def remove_sensor(self, sensor_id: str) -> bool:
        """
        Remove a sensor at runtime.
        
        Args:
            sensor_id: Sensor identifier
            
        Returns:
            True if removed, False if not found
        """
        result = self._poller.remove_sensor(sensor_id)
        if result:
            self._status_lock.lock()
            try:
                self._device_statuses.pop(sensor_id, None)
            finally:
                self._status_lock.unlock()
            self._data_buffer.clear(sensor_id)
        return result

    def run(self) -> None:
        """Main worker loop - polls sensors continuously."""
        self._running = True
        self._reconnection_manager.start()

        self._logger._emit("INFO", "worker_started", "system",
                          sensor_count=len(self._poller._sensors))

        # Initial connection status
        self.connection_status.emit(True)

        try:
            while self._running:
                cycle_start = time.time()

                # Poll all sensors
                results = self._poller.poll_all()

                # Process results
                for sensor_id, (value, timestamp, error) in results.items():
                    self._process_result(sensor_id, value, timestamp, error)

                # Emit batch signal
                if results:
                    self.batch_data_received.emit(results)

                # Calculate sleep time to maintain interval
                elapsed = time.time() - cycle_start
                sleep_time = max(0, self._poll_interval - elapsed)

                if sleep_time > 0:
                    # Use interruptible sleep
                    for _ in range(int(sleep_time * 10)):
                        if not self._running:
                            break
                        time.sleep(0.1)

        except Exception as e:
            self._logger.log_critical_error(
                "system",
                type(e).__name__,
                str(e)
            )
            self.error_occurred.emit(f"Worker crashed: {e}")

        finally:
            self._cleanup()

    def _process_result(
        self,
        sensor_id: str,
        value: float | None,
        timestamp: float,
        error: str | None
    ) -> None:
        """Process a poll result for a sensor."""
        config = self._poller._sensors.get(sensor_id)
        if not config:
            return

        # Get current and new status
        new_status = self._poller.get_sensor_status(sensor_id)

        self._status_lock.lock()
        try:
            old_status = self._device_statuses.get(sensor_id, DeviceStatus.UNKNOWN)
            self._device_statuses[sensor_id] = new_status
        finally:
            self._status_lock.unlock()

        # Emit status change if changed
        if old_status != new_status:
            self.device_status_changed.emit(sensor_id, new_status.value)
            self._logger.log_circuit_state_change(
                sensor_id,
                old_status.value,
                new_status.value
            )

            # Handle offline devices
            if new_status == DeviceStatus.OFFLINE:
                self._reconnection_manager.schedule_reconnect(sensor_id, config)

        if error:
            # Error occurred
            cb = self._poller._circuit_breakers.get(sensor_id)
            failure_count = cb.failure_count if cb else 0

            self._logger.log_read_error(sensor_id, error, failure_count)

            # Emit error for primary sensor (legacy compatibility)
            if sensor_id == self._primary_sensor_id:
                self.error_occurred.emit(error)

        elif value is not None:
            # Success - store data
            self._data_buffer.write(sensor_id, value, timestamp)

            # Emit signals
            self.sensor_data_received.emit(sensor_id, value, timestamp)

            # Legacy signal for primary sensor
            if sensor_id == self._primary_sensor_id:
                self.data_received.emit(value, timestamp)

    def _on_device_recovered(self, sensor_id: str) -> None:
        """Handle device recovery callback."""
        self._logger._emit("INFO", "device_recovered", sensor_id)

        # Update status
        self._status_lock.lock()
        try:
            self._device_statuses[sensor_id] = DeviceStatus.ONLINE
        finally:
            self._status_lock.unlock()

        self.device_status_changed.emit(sensor_id, DeviceStatus.ONLINE.value)

    def _cleanup(self) -> None:
        """Cleanup resources on stop."""
        self._reconnection_manager.stop()
        self._poller.disconnect_all()
        self.connection_status.emit(False)

        self._logger._emit("INFO", "worker_stopped", "system")

    def stop(self) -> None:
        """Stop the worker thread gracefully."""
        self._running = False

        # Wait for thread to finish
        if self.isRunning():
            self.wait(5000)

    # --- Data Access Methods ---

    def get_latest_value(self, sensor_id: str) -> tuple[float, float] | None:
        """
        Get the most recent value for a sensor.
        
        Args:
            sensor_id: Sensor identifier
            
        Returns:
            (value, timestamp) tuple or None
        """
        return self._data_buffer.get_latest_value(sensor_id)

    def get_data_buffer(
        self,
        sensor_id: str,
        count: int | None = None
    ) -> list[tuple[float, float]]:
        """
        Get buffered data for a sensor.
        
        Args:
            sensor_id: Sensor identifier
            count: Number of samples (None for all)
            
        Returns:
            List of (value, timestamp) tuples
        """
        if count:
            return self._data_buffer.read_latest(sensor_id, count)
        return self._data_buffer.read_all(sensor_id)

    def get_sensor_status(self, sensor_id: str) -> DeviceStatus:
        """
        Get current status of a sensor.
        
        Args:
            sensor_id: Sensor identifier
            
        Returns:
            DeviceStatus enum value
        """
        self._status_lock.lock()
        try:
            return self._device_statuses.get(sensor_id, DeviceStatus.UNKNOWN)
        finally:
            self._status_lock.unlock()

    def get_all_sensor_statuses(self) -> dict[str, DeviceStatus]:
        """
        Get status of all sensors.
        
        Returns:
            Dictionary of sensor_id -> DeviceStatus
        """
        self._status_lock.lock()
        try:
            return dict(self._device_statuses)
        finally:
            self._status_lock.unlock()

    def get_status_summary(self) -> dict[str, Any]:
        """
        Get complete status summary.
        
        Returns:
            Dictionary with sensor counts, statuses, etc.
        """
        return {
            "running": self._running,
            "poll_interval": self._poll_interval,
            "primary_sensor": self._primary_sensor_id,
            "poller": self._poller.get_status_summary()
        }

    # --- Legacy Properties (for backward compatibility) ---

    @property
    def is_running(self) -> bool:
        """Check if worker is running."""
        return self._running

    @is_running.setter
    def is_running(self, value: bool) -> None:
        """Set running state (legacy compatibility)."""
        self._running = value


# --- Utility Functions ---

def list_available_ports() -> list[tuple[str, str]]:
    """
    List available serial (COM) ports on the system.
    
    Returns:
        List of tuples: [(port_name, description), ...]
        Example: [("COM3", "USB Serial Port"), ("/dev/ttyUSB0", "CP2102")]
    """
    try:
        import serial.tools.list_ports
        ports = serial.tools.list_ports.comports()
        return [(port.device, port.description) for port in ports]
    except ImportError:
        logging.getLogger(__name__).warning("pyserial not installed. Cannot list ports.")
        return []
    except Exception as e:
        logging.getLogger(__name__).error(f"Error listing ports: {e}")
        return []


# --- Legacy Compatibility ---

class ModbusConnectionConfig:
    """
    Legacy configuration data class for Modbus connections.
    
    Deprecated: Use SensorConfig from models.py instead.
    """

    def __init__(
        self,
        connection_type: str = "TCP",
        ip_address: str = "192.168.1.100",
        tcp_port: int = 502,
        serial_port: str = "COM1",
        baudrate: int = 9600,
        parity: str = "N",
        stopbits: int = 1,
        bytesize: int = 8,
        register_address: int = 0,
        slave_id: int = 1,
        scale_factor: float = 1.0,
        data_type: str = "float32_be",
        read_interval: float = 1.0,
        name: str = "Modbus Sensor"
    ):
        """Initialize legacy config (deprecated)."""
        import warnings
        warnings.warn(
            "ModbusConnectionConfig is deprecated. Use SensorConfig from models.py",
            DeprecationWarning,
            stacklevel=2
        )

        self.connection_type = connection_type
        self.ip_address = ip_address
        self.tcp_port = tcp_port
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.parity = parity
        self.stopbits = stopbits
        self.bytesize = bytesize
        self.register_address = register_address
        self.slave_id = slave_id
        self.scale_factor = scale_factor
        self.data_type = data_type
        self.read_interval = read_interval
        self.name = name

    def to_sensor_config(self) -> SensorConfig:
        """Convert to new SensorConfig format."""
        conn_type = ConnectionType.TCP if self.connection_type.upper() == "TCP" else ConnectionType.RTU

        # Map legacy data_type string to enum
        data_type_map = {
            "float32_be": DataType.FLOAT32_BE,
            "float32_le": DataType.FLOAT32_LE,
            "float32_bs": DataType.FLOAT32_BS,
            "float32_ws": DataType.FLOAT32_WS,
            "int16": DataType.INT16,
            "uint16": DataType.UINT16,
            "int32_be": DataType.INT32_BE,
            "int32_le": DataType.INT32_LE,
            "uint32_be": DataType.UINT32_BE,
            "uint32_le": DataType.UINT32_LE,
        }
        dt = data_type_map.get(self.data_type.lower(), DataType.FLOAT32_BE)

        return SensorConfig(
            name=self.name,
            connection_type=conn_type,
            ip=self.ip_address,
            port=self.tcp_port,
            serial_port=self.serial_port,
            baudrate=self.baudrate,
            parity=self.parity.upper() if self.parity else "N",
            stopbits=self.stopbits,
            bytesize=self.bytesize,
            slave_id=self.slave_id,
            register_address=self.register_address,
            data_type=dt,
            scale_factor=self.scale_factor,
            poll_interval=self.read_interval
        )

    def to_dict(self) -> dict:
        """Convert to dictionary (legacy method)."""
        return {
            "connection_type": self.connection_type,
            "ip_address": self.ip_address,
            "tcp_port": self.tcp_port,
            "serial_port": self.serial_port,
            "baudrate": self.baudrate,
            "parity": self.parity,
            "stopbits": self.stopbits,
            "bytesize": self.bytesize,
            "register_address": self.register_address,
            "slave_id": self.slave_id,
            "scale_factor": self.scale_factor,
            "data_type": self.data_type,
            "read_interval": self.read_interval,
            "name": self.name
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ModbusConnectionConfig":
        """Create from dictionary (legacy method)."""
        return cls(**data)
