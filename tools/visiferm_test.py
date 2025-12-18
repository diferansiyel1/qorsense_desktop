"""
Hamilton Visiferm Modbus Test
Based on ODOUM043 Programmer's Manual
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
    frame = struct.pack('>BBHH', slave_id, function_code, start_address, quantity)
    crc = calculate_crc(frame)
    frame += struct.pack('<H', crc)
    return frame

def parse_float32_le(reg_low, reg_high):
    """Parse Float32 from two registers (Low word first, then High word - Little Endian word order)"""
    # Visiferm uses: Reg1/Reg2 = Low word, Reg3/Reg4 = High word
    # So we pack: high_word, low_word to get Big Endian byte order
    packed = struct.pack('>HH', reg_high, reg_low)
    return struct.unpack('>f', packed)[0]

def main():
    PORT = "/dev/cu.usbserial-A190QMF9"
    BAUD = 19200
    SLAVE_ID = 2  # From user's screenshot
    
    print("=" * 60)
    print("Hamilton Visiferm Modbus Test")
    print("Based on ODOUM043 Programmer's Manual")
    print("=" * 60)
    print(f"Port: {PORT}")
    print(f"Settings: {BAUD}/8N2")
    print(f"Slave ID: {SLAVE_ID}")
    print("-" * 60)
    
    try:
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUD,
            bytesize=8,
            parity='N',
            stopbits=2,
            timeout=2.0,
            write_timeout=2.0
        )
        print(f"Port opened: {ser.name}")
    except Exception as e:
        print(f"Failed to open port: {e}")
        return
    
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    # Test cases from manual:
    # PMC1 (Oxygen): Register 2089 (0x0829), read 10 registers
    # PMC6 (Temperature): Register 2409 (0x0969), read 10 registers  
    # Device Address: Register 4096, read 2 registers
    
    tests = [
        # (start_address, count, description)
        (4096, 2, "Device Address (4096)"),
        (4102, 2, "Baud Rate Code (4102)"),
        (2089, 10, "PMC1 - Oxygen Measurement (2089)"),
        (2409, 10, "PMC6 - Temperature Measurement (2409)"),
        (0, 2, "Register 0 (test)"),
    ]
    
    for addr, count, desc in tests:
        print(f"\nTest: {desc}")
        request = build_request(SLAVE_ID, 0x03, addr, count)
        print(f"  TX: {request.hex().upper()}")
        
        ser.reset_input_buffer()
        ser.write(request)
        ser.flush()
        
        # Wait for response
        time.sleep(0.2)
        
        response = ser.read(256)
        
        if response:
            print(f"  RX: {response.hex().upper()}")
            
            # Parse response
            if len(response) >= 5:
                resp_slave = response[0]
                resp_fc = response[1]
                
                if resp_fc == 0x03:  # Read Holding Registers response
                    byte_count = response[2]
                    print(f"  Slave: {resp_slave}, FC: {resp_fc}, Bytes: {byte_count}")
                    
                    # Extract registers
                    data = response[3:3+byte_count]
                    num_regs = byte_count // 2
                    registers = []
                    for i in range(num_regs):
                        reg_val = struct.unpack('>H', data[i*2:i*2+2])[0]
                        registers.append(reg_val)
                    print(f"  Registers: {registers}")
                    
                    # If this is a measurement (10 registers)
                    if count == 10 and len(registers) >= 4:
                        # Reg1/Reg2 = Physical unit (hex)
                        # Reg3/Reg4 = Measurement value (float, low word first)
                        unit = (registers[1] << 16) | registers[0]
                        value = parse_float32_le(registers[2], registers[3])
                        print(f"  -> Unit Code: 0x{unit:08X}")
                        print(f"  -> Measurement Value: {value:.4f}")
                        
                elif resp_fc & 0x80:  # Exception
                    exception_code = response[2]
                    print(f"  EXCEPTION Code: {exception_code}")
        else:
            print("  RX: (no response)")
        
        time.sleep(0.3)
    
    ser.close()
    print("\n" + "=" * 60)
    print("Test complete.")

if __name__ == "__main__":
    main()
