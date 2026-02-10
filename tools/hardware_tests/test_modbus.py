"""
Simple Hamilton VisiFerm Modbus RTU Test Script
Tests basic serial connection and register reading
"""
import sys
import time

def test_connection():
    try:
        import serial
        import serial.tools.list_ports
    except ImportError:
        print("ERROR: pyserial not installed. Run: pip install pyserial")
        return False
    
    # List available ports
    print("\n=== Available COM Ports ===")
    ports = serial.tools.list_ports.comports()
    if not ports:
        print("No COM ports found!")
        return False
    
    for port in ports:
        print(f"  {port.device}: {port.description}")
    
    # Get user input for port
    port_name = input("\nEnter COM port (e.g., COM3): ").strip()
    if not port_name:
        print("No port specified, exiting.")
        return False
    
    # Try direct serial connection first
    print(f"\n=== Testing Direct Serial Connection to {port_name} ===")
    try:
        ser = serial.Serial(
            port=port_name,
            baudrate=19200,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_TWO,
            bytesize=serial.EIGHTBITS,
            timeout=2
        )
        print(f"✓ Serial port opened successfully: {ser.name}")
        print(f"  Baudrate: {ser.baudrate}")
        print(f"  Parity: {ser.parity}")
        print(f"  Stop bits: {ser.stopbits}")
        print(f"  Byte size: {ser.bytesize}")
        ser.close()
        print("✓ Serial port closed successfully")
    except Exception as e:
        print(f"✗ Failed to open serial port: {e}")
        return False
    
    # Now test Modbus
    print(f"\n=== Testing Modbus RTU Connection ===")
    try:
        from pymodbus.client import ModbusSerialClient
        from pymodbus.exceptions import ModbusException
    except ImportError:
        print("ERROR: pymodbus not installed. Run: pip install pymodbus")
        return False
    
    # Get register address
    register = input("Enter register address to read (default: 2048): ").strip()
    register = int(register) if register else 2048
    
    slave_id = input("Enter Slave ID (default: 1): ").strip()
    slave_id = int(slave_id) if slave_id else 1
    
    print(f"\nConnecting to {port_name} (19200, N, 8, 2)...")
    print(f"Reading register {register} from slave {slave_id}...")
    
    client = ModbusSerialClient(
        port=port_name,
        baudrate=19200,
        parity='N',
        stopbits=2,
        bytesize=8,
        timeout=3,
    )
    
    try:
        if not client.connect():
            print("✗ Failed to connect to Modbus device")
            return False
        
        print("✓ Modbus client connected")
        
        # Try reading registers
        print(f"\nReading 2 registers starting at address {register}...")
        
        # Try different API versions
        result = None
        for param_name in ['device_id', 'slave', 'unit']:
            try:
                kwargs = {'address': register, 'count': 2, param_name: slave_id}
                result = client.read_holding_registers(**kwargs)
                print(f"  Using parameter: {param_name}")
                break
            except TypeError:
                continue
        
        if result is None:
            print("✗ Could not find correct API parameter")
            return False
        
        if result.isError():
            print(f"✗ Modbus error: {result}")
            return False
        
        print(f"✓ Read successful!")
        print(f"  Raw registers: {result.registers}")
        
        # Decode as Float32 Big Endian
        import struct
        if len(result.registers) >= 2:
            packed = struct.pack('>HH', result.registers[0], result.registers[1])
            value = struct.unpack('>f', packed)[0]
            print(f"  Float32 (BE): {value}")
        
        return True
        
    except ModbusException as e:
        print(f"✗ Modbus exception: {e}")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        client.close()
        print("\nConnection closed.")

if __name__ == "__main__":
    print("=" * 50)
    print("Hamilton VisiFerm Modbus RTU Test")
    print("=" * 50)
    
    success = test_connection()
    
    print("\n" + "=" * 50)
    if success:
        print("TEST PASSED - Connection working!")
    else:
        print("TEST FAILED - Check settings and connections")
    print("=" * 50)
    
    input("\nPress Enter to exit...")
