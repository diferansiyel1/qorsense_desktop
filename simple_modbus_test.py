import serial
import time

def crc16(data):
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, 'little')

PORT = 'COM5'
print(f'Connecting to {PORT}...')

try:
    ser = serial.Serial(PORT, baudrate=19200, parity='N', stopbits=2, bytesize=8, timeout=2)
    print(f'Port opened: {ser.name}')
    print()
    
    for slave_id in [1, 2, 247]:
        print(f'--- Testing Slave ID {slave_id} ---')
        for reg_name, reg_addr in [('DeviceAddr', 4095), ('O2Value', 2090), ('TempValue', 2410)]:
            request = bytes([slave_id, 0x03, (reg_addr >> 8) & 0xFF, reg_addr & 0xFF, 0, 2])
            request = request + crc16(request)
            
            ser.reset_input_buffer()
            ser.reset_output_buffer()
            ser.write(request)
            time.sleep(0.15)
            response = ser.read(256)
            
            status = 'RESPONSE' if response else 'NO RESPONSE'
            print(f'  {reg_name} (Reg {reg_addr}): {status}')
            if response:
                print(f'    TX: {request.hex()}')
                print(f'    RX: {response.hex()}')
                # Parse response
                if len(response) >= 5 and response[1] == 0x03:
                    byte_count = response[2]
                    if byte_count == 4:
                        import struct
                        high = (response[3] << 8) | response[4]
                        low = (response[5] << 8) | response[6]
                        packed = struct.pack('>HH', high, low)
                        value = struct.unpack('>f', packed)[0]
                        print(f'    Float Value: {value}')
        print()
    
    ser.close()
    print('Port closed.')

except serial.SerialException as e:
    print(f'Serial error: {e}')
except Exception as e:
    print(f'Error: {e}')
    import traceback
    traceback.print_exc()
