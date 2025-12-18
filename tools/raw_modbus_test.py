"""
Raw Serial Modbus RTU Test
Manually construct and send Modbus RTU frames to bypass pymodbus.
"""
import serial
import struct
import time

def calculate_crc(data):
    """Calculate Modbus RTU CRC16"""
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
    """Build a Modbus RTU request frame"""
    # Frame without CRC
    frame = struct.pack('>BBHH', slave_id, function_code, start_address, quantity)
    crc = calculate_crc(frame)
    # CRC is little-endian in Modbus RTU
    frame += struct.pack('<H', crc)
    return frame

def main():
    PORT = "/dev/cu.usbserial-A190QMF9"
    BAUD = 19200
    PARITY = 'N'
    STOPBITS = 2
    BYTESIZE = 8
    SLAVE_ID = 2
    
    print("=" * 60)
    print("Raw Serial Modbus RTU Test")
    print("=" * 60)
    print(f"Port: {PORT}")
    print(f"Settings: {BAUD}/{BYTESIZE}{PARITY}{STOPBITS}")
    print(f"Slave ID: {SLAVE_ID}")
    print("-" * 60)
    
    # Open serial port
    try:
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUD,
            bytesize=BYTESIZE,
            parity=PARITY,
            stopbits=STOPBITS,
            timeout=2.0,
            write_timeout=2.0
        )
        print(f"Port opened: {ser.name}")
    except Exception as e:
        print(f"Failed to open port: {e}")
        return
    
    # Clear buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    # Test cases: (function_code, start_address, quantity, description)
    tests = [
        (0x03, 0, 2, "Read Holding Registers @ 0"),
        (0x04, 0, 2, "Read Input Registers @ 0"),
        (0x03, 1, 2, "Read Holding Registers @ 1"),
        (0x04, 1, 2, "Read Input Registers @ 1"),
        (0x03, 100, 2, "Read Holding Registers @ 100"),
        (0x04, 100, 2, "Read Input Registers @ 100"),
    ]
    
    for fc, addr, qty, desc in tests:
        print(f"\nTest: {desc}")
        request = build_request(SLAVE_ID, fc, addr, qty)
        print(f"  TX: {request.hex().upper()}")
        
        # Send request
        ser.write(request)
        ser.flush()
        
        # Wait for response (Modbus RTU needs silence for frame detection)
        time.sleep(0.1)
        
        # Read response
        response = ser.read(256)  # Read up to 256 bytes
        
        if response:
            print(f"  RX: {response.hex().upper()}")
            # Parse response
            if len(response) >= 5:
                resp_slave = response[0]
                resp_fc = response[1]
                print(f"  Slave: {resp_slave}, FC: {resp_fc}")
                if resp_fc == fc:
                    byte_count = response[2]
                    print(f"  Byte Count: {byte_count}")
                    if byte_count == 4:  # 2 registers * 2 bytes
                        reg1 = struct.unpack('>H', response[3:5])[0]
                        reg2 = struct.unpack('>H', response[5:7])[0]
                        print(f"  Registers: {reg1}, {reg2}")
                        # Try to decode as Float32 Big Endian
                        float_val = struct.unpack('>f', response[3:7])[0]
                        print(f"  As Float32 BE: {float_val}")
                elif resp_fc == (fc | 0x80):  # Exception
                    exception_code = response[2]
                    print(f"  EXCEPTION: {exception_code}")
        else:
            print("  RX: (no response)")
        
        time.sleep(0.2)  # Delay between tests
    
    ser.close()
    print("\n" + "=" * 60)
    print("Test complete.")

if __name__ == "__main__":
    main()
