"""
Hamilton ARC Sensor Debug Tool
Tests various Modbus configurations to find the correct one.
"""
import logging
import sys
import time
from pymodbus.client import ModbusSerialClient

# Enable pymodbus debug logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

def test_hamilton():
    print("=" * 60)
    print("Hamilton ARC Sensor Debug Tool")
    print("=" * 60)
    
    # Fixed settings from user's screenshot
    PORT = "/dev/cu.usbserial-A190QMF9"
    BAUD = 19200
    PARITY = 'N'  # None
    STOPBITS = 2
    BYTESIZE = 8
    SLAVE_ID = 2
    
    print(f"Port: {PORT}")
    print(f"Baud: {BAUD}")
    print(f"Parity: {PARITY}")
    print(f"Stop Bits: {STOPBITS}")
    print(f"Slave ID: {SLAVE_ID}")
    print("-" * 60)
    
    client = ModbusSerialClient(
        port=PORT,
        baudrate=BAUD,
        parity=PARITY,
        stopbits=STOPBITS,
        bytesize=BYTESIZE,
        timeout=3.0  # Longer timeout
    )
    
    if not client.connect():
        print("ERROR: Failed to open port!")
        return
    
    print("Port opened successfully.\n")
    
    # Test different function codes and register addresses
    register_addresses = [0, 1, 2, 100, 200, 256, 1000]
    
    print("Testing read_holding_registers (FC 03)...")
    for addr in register_addresses:
        try:
            result = client.read_holding_registers(address=addr, count=2, device_id=SLAVE_ID)
            if not result.isError():
                print(f"  [SUCCESS] Address {addr}: {result.registers}")
            else:
                print(f"  [ERROR] Address {addr}: {result}")
        except Exception as e:
            print(f"  [EXCEPTION] Address {addr}: {e}")
        time.sleep(0.1)
    
    print("\nTesting read_input_registers (FC 04)...")
    for addr in register_addresses:
        try:
            result = client.read_input_registers(address=addr, count=2, device_id=SLAVE_ID)
            if not result.isError():
                print(f"  [SUCCESS] Address {addr}: {result.registers}")
            else:
                print(f"  [ERROR] Address {addr}: {result}")
        except Exception as e:
            print(f"  [EXCEPTION] Address {addr}: {e}")
        time.sleep(0.1)
    
    print("\nTesting read_coils (FC 01)...")
    try:
        result = client.read_coils(address=0, count=8, device_id=SLAVE_ID)
        if not result.isError():
            print(f"  [SUCCESS] Coils: {result.bits}")
        else:
            print(f"  [ERROR]: {result}")
    except Exception as e:
        print(f"  [EXCEPTION]: {e}")
    
    print("\nTesting read_discrete_inputs (FC 02)...")
    try:
        result = client.read_discrete_inputs(address=0, count=8, device_id=SLAVE_ID)
        if not result.isError():
            print(f"  [SUCCESS] Discrete Inputs: {result.bits}")
        else:
            print(f"  [ERROR]: {result}")
    except Exception as e:
        print(f"  [EXCEPTION]: {e}")
    
    client.close()
    print("\n" + "=" * 60)
    print("Test complete.")

if __name__ == "__main__":
    test_hamilton()
