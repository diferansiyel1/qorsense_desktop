"""
Raw Serial Modbus RTU Test with RTS/DTR control
Some USB-RS485 converters use RTS or DTR to switch between TX and RX modes.
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

def test_with_rts_control(rts_on_send=True, dtr_on_send=False):
    PORT = "/dev/cu.usbserial-A190QMF9"
    BAUD = 19200
    SLAVE_ID = 2
    
    print(f"\n--- Testing with RTS_ON_SEND={rts_on_send}, DTR_ON_SEND={dtr_on_send} ---")
    
    try:
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUD,
            bytesize=8,
            parity='N',
            stopbits=2,
            timeout=1.0,
            write_timeout=1.0,
            rtscts=False,
            dsrdtr=False
        )
    except Exception as e:
        print(f"Failed to open port: {e}")
        return
    
    # Initial state
    ser.rts = not rts_on_send
    ser.dtr = not dtr_on_send
    time.sleep(0.01)
    
    # Clear buffers
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    
    # Build request: Read Holding Registers @ address 0, count 2
    request = build_request(SLAVE_ID, 0x03, 0, 2)
    print(f"TX: {request.hex().upper()}")
    
    # Set RTS/DTR for transmit
    if rts_on_send:
        ser.rts = True
    if dtr_on_send:
        ser.dtr = True
    time.sleep(0.001)  # Small delay
    
    # Send
    ser.write(request)
    ser.flush()
    
    # Calculate transmission time
    bits_per_char = 1 + 8 + 0 + 2  # start + data + parity(none) + stop
    tx_time = (len(request) * bits_per_char) / BAUD
    time.sleep(tx_time + 0.01)  # Wait for transmission + margin
    
    # Switch to receive
    if rts_on_send:
        ser.rts = False
    if dtr_on_send:
        ser.dtr = False
    
    # Wait for response
    time.sleep(0.1)
    
    # Read response
    response = ser.read(256)
    
    if response:
        print(f"RX: {response.hex().upper()}")
    else:
        print("RX: (no response)")
    
    ser.close()

def main():
    print("=" * 60)
    print("Modbus RTU with RTS/DTR Control Test")
    print("=" * 60)
    
    # Test different RTS/DTR combinations
    combinations = [
        (False, False),  # No control
        (True, False),   # RTS for TX enable
        (False, True),   # DTR for TX enable
        (True, True),    # Both
    ]
    
    for rts, dtr in combinations:
        test_with_rts_control(rts_on_send=rts, dtr_on_send=dtr)
        time.sleep(0.5)
    
    print("\n" + "=" * 60)
    print("Test complete.")

if __name__ == "__main__":
    main()
