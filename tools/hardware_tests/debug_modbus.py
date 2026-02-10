import logging
import sys
from pymodbus.client import ModbusSerialClient, ModbusTcpClient


# Configure Logging
logging.basicConfig()
log = logging.getLogger()
log.setLevel(logging.DEBUG)

def test_rtu_connection():
    print("--- Modbus RTU Diagnostic Tool ---")
    port = input(f"Enter Port (e.g. /dev/cu.usbserial... or COMx): ").strip()
    if not port:
        print("Port is required.")
        return

    baud = input("Enter Baud Rate [19200]: ").strip() or "19200"
    parity = input("Enter Parity (N/E/O) [E]: ").strip().upper() or "E"
    slave_id = input("Enter Slave ID [1]: ").strip() or "1"
    
    print(f"\nTesting connection to {port} @ {baud}bps, Parity={parity}, ID={slave_id}...")
    
    client = ModbusSerialClient(
        port=port,
        baudrate=int(baud),
        parity=parity,
        stopbits=1,
        bytesize=8,
        timeout=2.0
    )
    
    if client.connect():
        print("Successfully opened port.")
    else:
        print("Failed to open port!")
        return

    try:
        # Pymodbus 3.x uses 'slave' or 'device_id' depending on exact version/mixin
        # We will try both naming conventions just in case, but 'device_id' is probable for 3.11+
        # based on previous finding.
        print("\nAttempting to read Holding Registers (Address 0, Count 2)...")
        
        # Try with device_id first
        try:
             rr = client.read_holding_registers(address=0, count=2, device_id=int(slave_id))
        except TypeError:
             # Fallback to slave if device_id fails (unlikely given inspection, but safe)
             rr = client.read_holding_registers(address=0, count=2, slave=int(slave_id))

        if rr.isError():
            print(f"Error reading registers: {rr}")
        else:
            print(f"Success! Registers: {rr.registers}")
            
    except Exception as e:
        print(f"Exception during read: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()
        print("Connection closed.")

if __name__ == "__main__":
    test_rtu_connection()
