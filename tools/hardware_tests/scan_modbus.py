"""
Hamilton VisiFerm Comprehensive Modbus RTU Scanner
===================================================
Scans for devices with multiple parameters:
- Multiple baud rates (9600, 19200, 38400, 57600, 115200)
- Multiple slave IDs (1-32)
- Both Holding and Input registers
- Common VisiFerm register addresses

NOTE: All register addresses are in DECIMAL format (not hex)
NOTE: VisiFerm manual uses 1-based addressing, Modbus protocol uses 0-based
      Manual register 2090 = Protocol address 2089
"""
import time
import struct
import sys

def create_client(port, baudrate, parity='N', stopbits=2):
    """Create Modbus RTU client with specified parameters"""
    from pymodbus.client import ModbusSerialClient
    return ModbusSerialClient(
        port=port,
        baudrate=baudrate,
        parity=parity,
        stopbits=stopbits,
        bytesize=8,
        timeout=0.5,  # Short timeout for fast scanning
    )

def try_read(client, slave_id, address, count=1, reg_type='holding'):
    """Try to read registers, return result or None"""
    try:
        if reg_type == 'holding':
            result = client.read_holding_registers(address=address, count=count, slave=slave_id)
        else:
            result = client.read_input_registers(address=address, count=count, slave=slave_id)
        
        if result and not result.isError():
            return result.registers
    except Exception:
        pass
    return None

def decode_float32_be(regs):
    """Decode Float32 Big Endian from 2 registers"""
    if len(regs) >= 2:
        packed = struct.pack('>HH', regs[0], regs[1])
        return struct.unpack('>f', packed)[0]
    return None

def main():
    print("=" * 70)
    print("Hamilton VisiFerm Comprehensive Modbus RTU Scanner")
    print("=" * 70)
    print("\nNOTE: All addresses are in DECIMAL (not hex)")
    print("NOTE: Manual register X = Protocol address X-1")
    print("      (e.g., Manual 2090 = Protocol 2089)\n")
    
    try:
        from pymodbus.client import ModbusSerialClient
        import serial.tools.list_ports
    except ImportError as e:
        print(f"ERROR: Required module not installed: {e}")
        print("Run: pip install pymodbus pyserial")
        return
    
    # List available ports
    print("=== Available COM Ports ===")
    ports = list(serial.tools.list_ports.comports())
    for i, port in enumerate(ports):
        print(f"  [{i+1}] {port.device}: {port.description}")
    
    if not ports:
        print("No COM ports found!")
        return
    
    # Get port selection
    port_input = input("\nEnter COM port (e.g., COM5) or number: ").strip()
    if port_input.isdigit():
        idx = int(port_input) - 1
        if 0 <= idx < len(ports):
            port_name = ports[idx].device
        else:
            print("Invalid selection")
            return
    else:
        port_name = port_input.upper()
    
    print(f"\nSelected port: {port_name}")
    
    # Parameters to scan
    baud_rates = [19200, 9600, 38400, 57600, 115200]
    parity_options = [('N', 2), ('E', 1), ('N', 1)]  # (parity, stopbits)
    slave_ids = list(range(1, 33))  # 1-32
    
    # VisiFerm common registers (PROTOCOL addresses, 0-based)
    # Manual address - 1 = Protocol address
    test_registers = [
        # Configuration registers
        (4095, "Modbus Address (Manual: 4096)"),
        (4101, "Baud Rate (Manual: 4102)"),
        (4363, "Primary Channel (Manual: 4364)"),
        
        # Measurement registers - trying several possible addresses
        (0, "Register 0"),
        (1, "Register 1"),
        (2047, "Measurement (Manual: 2048)"),
        (2048, "Measurement (Manual: 2049)"),
        (2049, "Temperature? (Manual: 2050)"),
        (2088, "DO Measurement (Manual: 2089)"),
        (2089, "DO Measurement (Manual: 2090)"),
        
        # CPA registers
        (10327, "CPA1 (Manual: 10328)"),
        (11047, "CPA (Manual: 11048)"),
    ]
    
    found_config = None
    
    print("\n" + "=" * 70)
    print("PHASE 1: Scanning for Device")
    print("=" * 70)
    
    # First, try to find the device with any configuration
    for baudrate in baud_rates:
        for parity, stopbits in parity_options:
            parity_name = {'N': 'None', 'E': 'Even', 'O': 'Odd'}[parity]
            print(f"\n--- Trying: {baudrate} baud, {parity_name} parity, {stopbits} stop bits ---")
            
            client = create_client(port_name, baudrate, parity, stopbits)
            if not client.connect():
                print("  Failed to open port")
                continue
            
            # Scan slave IDs
            for slave_id in slave_ids:
                sys.stdout.write(f"\r  Slave ID {slave_id:3d}...")
                sys.stdout.flush()
                
                # Try reading register 0 (usually responds if device exists)
                result = try_read(client, slave_id, 0, 2, 'holding')
                if result:
                    print(f"\r  Slave ID {slave_id:3d}: ✓ FOUND! Response: {result}")
                    found_config = {
                        'port': port_name,
                        'baudrate': baudrate,
                        'parity': parity,
                        'stopbits': stopbits,
                        'slave_id': slave_id
                    }
                    client.close()
                    break
                
                # Also try input registers
                result = try_read(client, slave_id, 0, 2, 'input')
                if result:
                    print(f"\r  Slave ID {slave_id:3d}: ✓ FOUND (Input Registers)! Response: {result}")
                    found_config = {
                        'port': port_name,
                        'baudrate': baudrate,
                        'parity': parity,
                        'stopbits': stopbits,
                        'slave_id': slave_id,
                        'reg_type': 'input'
                    }
                    client.close()
                    break
                
                time.sleep(0.05)  # Small delay between attempts
            
            client.close()
            
            if found_config:
                break
        
        if found_config:
            break
    
    print()  # New line after scanning
    
    if not found_config:
        print("\n" + "=" * 70)
        print("NO DEVICE FOUND!")
        print("=" * 70)
        print("\nChecklist:")
        print("  [ ] Is the VisiFerm sensor powered on?")
        print("  [ ] Is the USB-RS485 adapter properly connected?")
        print("  [ ] Try swapping RS485 A/B wires")
        print("  [ ] Check if sensor LED is blinking (indicates communication)")
        print("  [ ] Is another program using the COM port?")
        print("  [ ] Try a different USB port")
        return
    
    # Device found! Now read registers
    print("\n" + "=" * 70)
    print("DEVICE FOUND!")
    print("=" * 70)
    print(f"  Port:      {found_config['port']}")
    print(f"  Baud Rate: {found_config['baudrate']}")
    print(f"  Parity:    {found_config['parity']}")
    print(f"  Stop Bits: {found_config['stopbits']}")
    print(f"  Slave ID:  {found_config['slave_id']}")
    
    print("\n" + "=" * 70)
    print("PHASE 2: Reading Registers")
    print("=" * 70)
    
    client = create_client(
        found_config['port'],
        found_config['baudrate'],
        found_config['parity'],
        found_config['stopbits']
    )
    client.connect()
    
    reg_type = found_config.get('reg_type', 'holding')
    slave_id = found_config['slave_id']
    
    print(f"\nReading {reg_type.upper()} registers from Slave ID {slave_id}:\n")
    
    working_registers = []
    
    for reg_addr, reg_name in test_registers:
        result = try_read(client, slave_id, reg_addr, 2, reg_type)
        if result:
            float_val = decode_float32_be(result)
            print(f"  ✓ {reg_name}")
            print(f"      Address: {reg_addr} (decimal)")
            print(f"      Raw: {result}")
            if float_val is not None:
                print(f"      Float32: {float_val:.6f}")
            working_registers.append((reg_addr, reg_name, result))
        time.sleep(0.1)
    
    client.close()
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY - Copy these settings to QorSense Desktop:")
    print("=" * 70)
    print(f"""
    Connection Type: Modbus RTU
    COM Port:        {found_config['port']}
    Baud Rate:       {found_config['baudrate']}
    Parity:          {found_config['parity']} ({'None' if found_config['parity'] == 'N' else 'Even' if found_config['parity'] == 'E' else 'Odd'})
    Stop Bits:       {found_config['stopbits']}
    Slave ID:        {found_config['slave_id']}
    """)
    
    if working_registers:
        print("Working register addresses (use in QorSense):")
        for addr, name, _ in working_registers:
            print(f"    {addr} - {name}")

if __name__ == "__main__":
    main()
    input("\nPress Enter to exit...")
