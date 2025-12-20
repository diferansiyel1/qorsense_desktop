"""
Hamilton VisiFerm DO Arc - Kapsamlı Modbus RTU Bağlantı Testi
============================================================
Bu script VisiFerm sensörüne bağlanmak için farklı Slave ID'leri ve 
register adreslerini otomatik olarak test eder.

Kaynak: VisiFerm Programmer's Manual (ODOUM043)
- Register 4096: Device Address (Slave ID) - varsayılan: 1
- Register 2089-2098: PMC1 Oksijen ölçüm bloğu
- Register 2409-2418: PMC6 Sıcaklık ölçüm bloğu
"""

import serial
import struct
import time
import sys

# --- YAPILANDIRMA ---
PORT = "COM5"  # Değiştirin gerekirse
TIMEOUT = 1.0

# Hamilton VisiFerm varsayılan ayarları (Manual'dan)
BAUDRATE = 19200
PARITY = serial.PARITY_NONE  # 'N'
STOPBITS = 2
BYTESIZE = 8

# Test edilecek Slave ID'leri
SLAVE_IDS_TO_TEST = [1, 2, 3, 247]

# Önemli Register Adresleri (Protocol Address = Manual Register - 1)
REGISTERS = {
    "Device Address": 4095,      # Register 4096 -> Slave ID okuma
    "PMC1 O2 Unit": 2088,        # Register 2089
    "PMC1 O2 Value": 2090,       # Register 2091 (Float - 2 register)
    "PMC6 Temp Unit": 2408,      # Register 2409
    "PMC6 Temp Value": 2410,     # Register 2411 (Float - 2 register)
    "Firmware Info": 1031,       # Register 1032
}


def calculate_crc16(data: bytes) -> bytes:
    """Modbus RTU CRC-16 hesapla"""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, 'little')


def build_read_request(slave_id: int, register: int, count: int = 2) -> bytes:
    """Modbus RTU Read Holding Registers (Function Code 3) request oluştur"""
    request = bytes([
        slave_id,
        0x03,  # Function Code: Read Holding Registers
        (register >> 8) & 0xFF,  # Register Address High
        register & 0xFF,         # Register Address Low
        (count >> 8) & 0xFF,     # Number of Registers High
        count & 0xFF             # Number of Registers Low
    ])
    crc = calculate_crc16(request)
    return request + crc


def decode_float32_be(registers: list) -> float:
    """Big Endian Float32 decode"""
    if len(registers) < 2:
        return None
    packed = struct.pack('>HH', registers[0], registers[1])
    return struct.unpack('>f', packed)[0]


def parse_response(response: bytes, expected_slave: int) -> dict:
    """Modbus yanıtını parse et"""
    if len(response) < 5:
        return {"error": f"Yanıt çok kısa: {len(response)} byte"}
    
    slave_id = response[0]
    function_code = response[1]
    
    if slave_id != expected_slave:
        return {"error": f"Yanlış Slave ID: beklenen {expected_slave}, gelen {slave_id}"}
    
    if function_code & 0x80:  # Error response
        error_code = response[2]
        error_messages = {
            1: "Illegal Function",
            2: "Illegal Data Address",
            3: "Illegal Data Value",
            4: "Slave Device Failure"
        }
        return {"error": f"Modbus Hata: {error_messages.get(error_code, f'Kod {error_code}')}"}
    
    if function_code == 0x03:  # Read Holding Registers response
        byte_count = response[2]
        data_bytes = response[3:3+byte_count]
        
        # Convert to 16-bit registers
        registers = []
        for i in range(0, len(data_bytes), 2):
            if i+1 < len(data_bytes):
                reg = (data_bytes[i] << 8) | data_bytes[i+1]
                registers.append(reg)
        
        return {"registers": registers, "raw": response.hex()}
    
    return {"error": f"Beklenmeyen function code: {function_code}"}


def test_slave_id(ser: serial.Serial, slave_id: int) -> bool:
    """Belirli bir Slave ID'yi test et"""
    print(f"\n{'='*50}")
    print(f"🔍 Slave ID {slave_id} test ediliyor...")
    print(f"{'='*50}")
    
    found = False
    
    for reg_name, reg_addr in REGISTERS.items():
        # İlk turda sadece Device Address ve Firmware info'yu test et
        if reg_name not in ["Device Address", "Firmware Info", "PMC1 O2 Value"]:
            continue
            
        count = 2 if "Value" in reg_name else 2
        request = build_read_request(slave_id, reg_addr, count)
        
        # Buffer temizle
        ser.reset_input_buffer()
        ser.reset_output_buffer()
        
        # Request gönder
        ser.write(request)
        print(f"  📤 {reg_name} (Reg {reg_addr}) sorgusu gönderildi: {request.hex()}")
        
        # Yanıt bekle
        time.sleep(0.1)  # Frame delay
        response = ser.read(256)
        
        if response:
            print(f"  📥 Yanıt alındı: {response.hex()}")
            result = parse_response(response, slave_id)
            
            if "error" in result:
                print(f"  ⚠️  {result['error']}")
            else:
                print(f"  ✅ Register değerleri: {result['registers']}")
                found = True
                
                # Eğer bu O2 değeriyse, float olarak da göster
                if "Value" in reg_name and len(result['registers']) >= 2:
                    value = decode_float32_be(result['registers'])
                    print(f"  📊 Float değer: {value}")
        else:
            print(f"  ❌ Yanıt yok (timeout)")
    
    return found


def scan_all_slaves(ser: serial.Serial):
    """Tüm olası Slave ID'leri tara"""
    print("\n" + "🔬"*25)
    print("  Hamilton VisiFerm - Slave ID Taraması")
    print("🔬"*25)
    
    found_slaves = []
    
    for slave_id in SLAVE_IDS_TO_TEST:
        if test_slave_id(ser, slave_id):
            found_slaves.append(slave_id)
            print(f"\n🎉 CİHAZ BULUNDU! Slave ID: {slave_id}")
            
            # Cihaz bulunduğunda tüm register'ları oku
            print("\n--- Tüm Register'lar Okunuyor ---")
            for reg_name, reg_addr in REGISTERS.items():
                count = 2
                request = build_read_request(slave_id, reg_addr, count)
                
                ser.reset_input_buffer()
                ser.write(request)
                time.sleep(0.1)
                response = ser.read(256)
                
                if response:
                    result = parse_response(response, slave_id)
                    if "registers" in result:
                        if "Value" in reg_name:
                            value = decode_float32_be(result['registers'])
                            print(f"  {reg_name}: {value:.4f}" if value else f"  {reg_name}: N/A")
                        else:
                            print(f"  {reg_name}: {result['registers']}")
            break  # İlk bulunan cihazda dur
    
    return found_slaves


def main():
    print("\n" + "="*60)
    print("  Hamilton VisiFerm DO Arc - Modbus RTU Test Aracı")
    print("="*60)
    print(f"""
Ayarlar:
  Port: {PORT}
  Baud: {BAUDRATE}
  Parity: None
  Stop Bits: {STOPBITS}
  Timeout: {TIMEOUT}s
""")
    
    try:
        print(f"🔌 {PORT} açılıyor...")
        ser = serial.Serial(
            port=PORT,
            baudrate=BAUDRATE,
            parity=PARITY,
            stopbits=STOPBITS,
            bytesize=BYTESIZE,
            timeout=TIMEOUT
        )
        print(f"✅ Port açıldı: {ser.name}")
        
        # Slave ID taraması yap
        found = scan_all_slaves(ser)
        
        if not found:
            print("\n" + "❌"*25)
            print("  HİÇBİR CİHAZ BULUNAMADI!")
            print("❌"*25)
            print("""
Olası Sebepler:
1. Sensör güç almıyor veya bağlı değil
2. Kablo bağlantısı sorunlu (RX/TX ters mi?)
3. ARC Air USB kablosu Modbus RS485 değil Bluetooth versiyonu olabilir
4. Slave ID listedekilerden farklı (ArcAir ile kontrol edin)
5. Baud rate veya diğer seri ayarları farklı

Öneriler:
→ ArcAir yazılımı ile sensöre bağlanmayı deneyin
→ Sensör üzerindeki LED durumlarını kontrol edin
→ Farklı bir USB port deneyin
""")
        else:
            print("\n" + "✅"*25)
            print(f"  TEST BAŞARILI! Bulunan Slave ID: {found}")
            print("✅"*25)
        
        ser.close()
        print("\n🔌 Port kapatıldı.")
        
    except serial.SerialException as e:
        print(f"\n❌ Seri port hatası: {e}")
        if "PermissionError" in str(e) or "Erişim" in str(e):
            print("→ Port başka bir program tarafından kullanılıyor!")
            print("→ Desktop uygulamasını veya ArcAir'i kapatın.")
    except Exception as e:
        print(f"\n❌ Beklenmeyen hata: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
