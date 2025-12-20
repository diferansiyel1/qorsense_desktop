"""
Hamilton VisiFerm - COM5 Modbus RTU Test (Slave ID 2)
ArcAir'den alinan ayarlar: 19200, None, 8, 2
"""
import serial
import time
import struct

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
SLAVE_ID = 2  # ArcAir'den alinan
BAUDRATE = 19200
PARITY = 'N'
STOPBITS = 2
BYTESIZE = 8
TIMEOUT = 2

print(f'=' * 60)
print(f'  Hamilton VisiFerm Modbus RTU Test')
print(f'  Port: {PORT}, Slave ID: {SLAVE_ID}')
print(f'  {BAUDRATE} baud, Parity={PARITY}, Stop={STOPBITS}, Data={BYTESIZE}')
print(f'=' * 60)

try:
    ser = serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        parity=PARITY,
        stopbits=STOPBITS,
        bytesize=BYTESIZE,
        timeout=TIMEOUT
    )
    print(f'\n[OK] Port acildi: {ser.name}')
    
    # Test edilecek registerlar
    test_registers = [
        ('Device Address', 4095, 2),
        ('O2 Unit', 2088, 2),
        ('O2 Value', 2090, 2),  # Float - 2 register
        ('Temp Unit', 2408, 2),
        ('Temp Value', 2410, 2),  # Float - 2 register
        ('Firmware', 1031, 2),
    ]
    
    print(f'\n--- Modbus RTU Register Okuma Testi ---\n')
    
    for reg_name, reg_addr, count in test_registers:
        # Modbus RTU frame olustur
        request = bytes([SLAVE_ID, 0x03, (reg_addr >> 8) & 0xFF, reg_addr & 0xFF, 0, count])
        request = request + crc16(request)
        
        # Buffer temizle
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Gonder 
        ser.write(request)
        print(f'[TX] {reg_name} (Reg {reg_addr}): {request.hex()}')
        
        # Yanit bekle
        time.sleep(0.2)
        response = ser.read(256)
        
        if response:
            print(f'[RX] {response.hex()}')
            
            # Parse response
            if len(response) >= 5:
                rx_slave = response[0]
                rx_func = response[1]
                
                if rx_func == 0x03:  # Read holding registers response
                    byte_count = response[2]
                    data_bytes = response[3:3+byte_count]
                    
                    # Convert to registers
                    registers = []
                    for i in range(0, len(data_bytes), 2):
                        if i+1 < len(data_bytes):
                            reg = (data_bytes[i] << 8) | data_bytes[i+1]
                            registers.append(reg)
                    
                    print(f'     Registers: {registers}')
                    
                    # Float decode
                    if len(registers) >= 2 and 'Value' in reg_name:
                        packed = struct.pack('>HH', registers[0], registers[1])
                        value = struct.unpack('>f', packed)[0]
                        print(f'     Float Value: {value:.4f}')
                        
                elif rx_func & 0x80:  # Error
                    error_code = response[2]
                    errors = {1: 'Illegal Function', 2: 'Illegal Address', 3: 'Illegal Value', 4: 'Device Failure'}
                    print(f'     ERROR: {errors.get(error_code, f"Code {error_code}")}')
                    
        else:
            print(f'[--] NO RESPONSE')
        
        print()
        time.sleep(0.1)
    
    ser.close()
    print('[OK] Port kapatildi')

except serial.SerialException as e:
    print(f'[HATA] Seri port hatasi: {e}')
except Exception as e:
    print(f'[HATA] {e}')
    import traceback
    traceback.print_exc()
