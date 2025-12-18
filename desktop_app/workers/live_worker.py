"""
Modbus TCP/RTU Hybrid Live Data Worker
Reads sensor data from Modbus devices (TCP or Serial/RTU) in real-time.
"""
import struct
import time
import logging
from typing import Optional, List, Tuple
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger(__name__)


# --- Utility Functions ---

def list_available_ports() -> List[Tuple[str, str]]:
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
        logger.warning("pyserial not installed. Cannot list ports.")
        return []
    except Exception as e:
        logger.error(f"Error listing ports: {e}")
        return []


class ModbusWorker(QThread):
    """
    Background worker thread for reading live data from Modbus TCP or RTU devices.
    
    Supports:
    - Modbus TCP (Ethernet)
    - Modbus RTU (Serial/RS-485)
    
    Signals:
        data_received(float, float): Emits (value, timestamp) when data is read
        error_occurred(str): Emits error message on connection/read failures
        connection_status(bool): Emits connection state changes
    """
    
    # Connection types
    CONNECTION_TCP = "TCP"
    CONNECTION_RTU = "RTU"
    
    data_received = pyqtSignal(float, float)  # (value, timestamp)
    error_occurred = pyqtSignal(str)
    connection_status = pyqtSignal(bool)  # True = connected, False = disconnected
    
    def __init__(
        self,
        connection_type: str = "TCP",
        # TCP parameters
        ip_address: str = "192.168.1.100",
        tcp_port: int = 502,
        # RTU parameters
        serial_port: str = "COM1",
        baudrate: int = 9600,
        parity: str = "N",  # N=None, E=Even, O=Odd
        stopbits: int = 1,
        bytesize: int = 8,
        # Common parameters
        register_address: int = 0,
        slave_id: int = 1,
        scale_factor: float = 1.0,
        read_interval: float = 1.0,
        parent=None
    ):
        """
        Initialize the Modbus worker.
        
        Args:
            connection_type: "TCP" or "RTU"
            
            TCP Parameters:
                ip_address: IP address of the Modbus TCP device
                tcp_port: Modbus TCP port (default: 502)
            
            RTU Parameters:
                serial_port: Serial port name (e.g., "COM3" or "/dev/ttyUSB0")
                baudrate: Baud rate (default: 9600)
                parity: Parity - "N" (None), "E" (Even), "O" (Odd)
                stopbits: Stop bits (1 or 2)
                bytesize: Data bits (7 or 8)
            
            Common Parameters:
                register_address: Starting register address to read
                slave_id: Modbus slave/unit ID (default: 1)
                scale_factor: Factor to multiply raw value (default: 1.0)
                read_interval: Time between reads in seconds (default: 1.0)
        """
        super().__init__(parent)
        
        # Connection type
        self.connection_type = connection_type.upper()
        
        # TCP parameters
        self.ip_address = ip_address
        self.tcp_port = tcp_port
        
        # RTU parameters
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.parity = parity.upper()
        self.stopbits = stopbits
        self.bytesize = bytesize
        
        # Common parameters
        self.register_address = register_address
        self.slave_id = slave_id
        self.scale_factor = scale_factor
        self.read_interval = read_interval
        
        self.is_running = False
        self.client = None
        
    def _create_client(self):
        """Create the appropriate Modbus client based on connection type."""
        if self.connection_type == self.CONNECTION_TCP:
            from pymodbus.client import ModbusTcpClient
            return ModbusTcpClient(
                host=self.ip_address,
                port=self.tcp_port,
                timeout=5.0
            )
        elif self.connection_type == self.CONNECTION_RTU:
            from pymodbus.client import ModbusSerialClient
            return ModbusSerialClient(
                port=self.serial_port,
                baudrate=self.baudrate,
                parity=self.parity,
                stopbits=self.stopbits,
                bytesize=self.bytesize,
                timeout=3.0,
            )
        else:
            raise ValueError(f"Unknown connection type: {self.connection_type}")
    
    def _get_connection_string(self) -> str:
        """Get a human-readable connection string for logging."""
        if self.connection_type == self.CONNECTION_TCP:
            return f"{self.ip_address}:{self.tcp_port}"
        else:
            return f"{self.serial_port} @ {self.baudrate}bps"
        
    def run(self):
        """Main worker loop - connects and reads data continuously."""
        try:
            from pymodbus.exceptions import ModbusException
        except ImportError as e:
            self.error_occurred.emit(f"pymodbus not installed: {e}")
            return
        
        self.is_running = True
        reconnect_delay = 1.0
        max_reconnect_delay = 30.0
        conn_str = self._get_connection_string()
        
        while self.is_running:
            try:
                # Create and connect client
                logger.info(f"Creating {self.connection_type} client for {conn_str}")
                self.client = self._create_client()
                
                if not self.client.connect():
                    self.error_occurred.emit(f"Failed to connect to {conn_str}")
                    self.connection_status.emit(False)
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                    continue
                
                logger.info(f"Connected to Modbus device at {conn_str}")
                self.connection_status.emit(True)
                reconnect_delay = 1.0  # Reset on successful connection
                
                # Read loop
                while self.is_running and self.client.connected:
                    try:
                        # Read 2 registers for Float32 (Big Endian)
                        # pymodbus 3.10+ uses 'device_id' instead of 'slave'
                        try:
                            # pymodbus 3.10+
                            result = self.client.read_holding_registers(
                                address=self.register_address,
                                count=2,
                                device_id=self.slave_id
                            )
                        except TypeError:
                            try:
                                # pymodbus 3.0-3.9
                                result = self.client.read_holding_registers(
                                    address=self.register_address,
                                    count=2,
                                    slave=self.slave_id
                                )
                            except TypeError:
                                # pymodbus 2.x fallback
                                result = self.client.read_holding_registers(
                                    self.register_address,
                                    2,
                                    unit=self.slave_id
                                )
                        
                        if result.isError():
                            self.error_occurred.emit(f"Read error: {result}")
                            break
                        
                        # Decode Float32 (Big Endian) from 2 registers
                        value = self._decode_float32_be(result.registers)
                        scaled_value = value * self.scale_factor
                        timestamp = time.time()
                        
                        # Emit the data
                        self.data_received.emit(scaled_value, timestamp)
                        logger.debug(f"Read value: {scaled_value:.4f} at {timestamp}")
                        
                        # Wait for next read
                        time.sleep(self.read_interval)
                        
                    except ModbusException as e:
                        self.error_occurred.emit(f"Modbus error: {e}")
                        break
                    except OSError as e:
                        # Handle "Invalid handle" error - serial port lost
                        logger.warning(f"Serial port error (will reconnect): {e}")
                        self.error_occurred.emit(f"Serial port error: {e}")
                        break
                    except Exception as e:
                        self.error_occurred.emit(f"Read error: {e}")
                        break
                
                # Disconnected - cleanup
                self._disconnect()
                self.connection_status.emit(False)
                
                if self.is_running:
                    logger.info(f"Connection lost. Reconnecting in {reconnect_delay}s...")
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
                    
            except Exception as e:
                self.error_occurred.emit(f"Connection error: {e}")
                self._disconnect()
                self.connection_status.emit(False)
                
                if self.is_running:
                    time.sleep(reconnect_delay)
                    reconnect_delay = min(reconnect_delay * 2, max_reconnect_delay)
        
        logger.info("ModbusWorker stopped")
    
    def _decode_float32_be(self, registers: list) -> float:
        """
        Decode Float32 from two 16-bit registers (Big Endian).
        
        Args:
            registers: List of two 16-bit register values
            
        Returns:
            Decoded float value
        """
        if len(registers) < 2:
            return 0.0
        
        # Big Endian: High word first, then Low word
        high_word = registers[0]
        low_word = registers[1]
        
        # Pack as two unsigned shorts (big endian) and unpack as float
        packed = struct.pack('>HH', high_word, low_word)
        value = struct.unpack('>f', packed)[0]
        
        return value
    
    def _disconnect(self):
        """Safely disconnect the Modbus client."""
        if self.client:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None
    
    def stop(self):
        """Stop the worker thread gracefully."""
        self.is_running = False
        self._disconnect()
        
        # Wait for thread to finish (with timeout)
        if self.isRunning():
            self.wait(3000)  # Wait up to 3 seconds


class ModbusConnectionConfig:
    """Configuration data class for Modbus connections."""
    
    def __init__(
        self,
        connection_type: str = "TCP",
        # TCP
        ip_address: str = "192.168.1.100",
        tcp_port: int = 502,
        # RTU
        serial_port: str = "COM1",
        baudrate: int = 9600,
        parity: str = "N",
        stopbits: int = 1,
        bytesize: int = 8,
        # Common
        register_address: int = 0,
        slave_id: int = 1,
        scale_factor: float = 1.0,
        data_type: str = "float32_be",  # float32_be, float32_le, int16, uint16
        read_interval: float = 1.0,
        name: str = "Modbus Sensor"
    ):
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
    
    def to_dict(self) -> dict:
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
        return cls(**data)
