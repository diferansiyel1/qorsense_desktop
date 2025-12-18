import logging
import sys
import time
from pymodbus.client import ModbusSerialClient

# Configure Logging
# logging.basicConfig()
# log = logging.getLogger()
# log.setLevel(logging.WARNING) # Suppress debug for scan

def scan_rtu():
    print("--- Modbus RTU Scanner ---")
    port = input(f"Enter Port (e.g. /dev/cu.usbserial...): ").strip()
    if not port:
        print("Port required.")
        return

    baud_rates = [9600, 19200, 38400, 57600, 115200]
    parities = ['N', 'E', 'O']
    stopbits_list = [1, 2]
    slave_ids = range(1, 6) # Scan 1-5
    
    print(f"Scanning port {port}...")
    print(f"Bauds: {baud_rates}")
    print(f"Parities: {parities}")
    print(f"StopBits: {stopbits_list}")
    print(f"IDs: {list(slave_ids)}")
    print("-" * 50)
    
    found = False
    
    for baud in baud_rates:
        for parity in parities:
            for stopbits in stopbits_list:
                print(f"Checking {baud} / {parity} / {stopbits}...", end='\r')
                client = ModbusSerialClient(
                    port=port,
                    baudrate=baud,
                    parity=parity,
                    stopbits=stopbits,
                    bytesize=8,
                    timeout=0.2
                )
                
                if not client.connect():
                    continue
                    
                for slave_id in slave_ids:
                    try:
                        # Try to read register 0, count 1
                        rr = client.read_holding_registers(address=0, count=1, device_id=slave_id)
                        if not rr.isError():
                            print(f"\n[FOUND!] Device detected!")
                            print(f"  Baud: {baud}")
                            print(f"  Parity: {parity}")
                            print(f"  StopBits: {stopbits}")
                            print(f"  Slave ID: {slave_id}")
                            print(f"  Value at Reg 0: {rr.registers}")
                            found = True
                            client.close()
                            return
                    except:
                        pass
                
                client.close()
            
    if not found:
        print("\nScan complete. No devices found.")
        print("Suggestions:")
        print("1. Check wiring (Swap A/B)")
        print("2. Check power supply")
        print("3. Try different register address (tool checks only Reg 0)")

if __name__ == "__main__":
    scan_rtu()
