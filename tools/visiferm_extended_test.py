"""
Hamilton Visiferm Extended Test
Testing multiple slave IDs and address offsets
"""
import serial
import struct
import time

def calculate_crc(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc

def build_request(slave_id, function_code, start_address, quantity):
    frame = struct.pack('>BBHH', slave_id, function_code, start_address, quantity)
    crc = calculate_crc(frame)
    frame += struct.pack('<H', crc)
    return frame

def test_request(ser, slave_id, addr, count, desc):
    request = build_request(slave_id, 0x03, addr, count)
    print(f"  Slave {slave_id}, Addr {addr}: TX={request.hex().upper()}", end=" -> ")
    
    ser.reset_input_buffer()
    ser.write(request)
    ser.flush()
    time.sleep(0.15)
    
    response = ser.read(256)
    if response:
        print(f"RX={response.hex().upper()}")
        return True
    else:
        print("(no response)")
        return False

def main():
    PORT = "/dev/cu.usbserial-A190QMF9"
    
    print("=" * 70)
    print("Hamilton Visiferm Extended Test")
    print("=" * 70)
    
    try:
        ser = serial.Serial(
            port=PORT,
            baudrate=19200,
            bytesize=8,
            parity='N',
            stopbits=2,
            timeout=0.5
        )
    except Exception as e:
        print(f"Failed to open port: {e}")
        return
    
    print(f"Port opened: {PORT}\n")
    
    # Test with different slave IDs
    slave_ids = [1, 2, 3, 4, 5]
    
    # Key registers from manual
    test_registers = [
        (4096, 2, "Device Address"),
        (4095, 2, "Device Address -1"),
        (2089, 10, "PMC1 (O2)"),
        (2088, 10, "PMC1 -1"),
        (2409, 10, "PMC6 (Temp)"),
        (2408, 10, "PMC6 -1"),
        (0, 2, "Register 0"),
    ]
    
    found = False
    for slave_id in slave_ids:
        print(f"\n--- Testing Slave ID: {slave_id} ---")
        for addr, count, desc in test_registers:
            if test_request(ser, slave_id, addr, count, desc):
                found = True
                print(f"  *** FOUND RESPONSE! Slave={slave_id}, Addr={addr} ***")
            time.sleep(0.1)
        
        if found:
            break
    
    if not found:
        print("\n" + "=" * 70)
        print("NO RESPONSES RECEIVED FROM ANY CONFIGURATION")
        print("Possible issues:")
        print("1. Cable may be using proprietary Hamilton protocol, not Modbus")
        print("2. RS485 driver direction control issue")
        print("3. Device not in Modbus mode")
        print("=" * 70)
    
    ser.close()

if __name__ == "__main__":
    main()
