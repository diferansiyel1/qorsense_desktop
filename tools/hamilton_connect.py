import minimalmodbus  # Veya pymodbus, ancak minimalmodbus test için daha pratiktir
import serial
import struct
import time

# --- KONFİGÜRASYON ---
PORT = "COM5"  # Aygıt Yöneticisinden kontrol edip burayı güncelleyin!
SLAVE_ADDRESS = 2  # Hamilton varsayılan ID: 1
BAUDRATE = 19200   # Hamilton varsayılan
BYTESIZE = 8
PARITY = serial.PARITY_NONE
STOPBITS = 2       # KRİTİK AYAR! (Hamilton Parity None iken 2 stop bit ister)

def decode_float(registers):
    """
    Hamilton Float formatı: Big Endian (ABCD). 
    2 register (4 byte) birleştirilip float'a çevrilir.
    """
    if not registers or len(registers) < 2:
        return None
    # Pack 2 unsigned short (H) into bytes, then unpack as float (f)
    raw_bytes = struct.pack('>HH', registers[0], registers[1])
    return struct.unpack('>f', raw_bytes)[0]

def connect_visiferm():
    print(f"--- Pikolab ArGe: VisiFerm Bağlantı Testi ({PORT}) ---")
    
    try:
        # Enstrüman Tanımlama
        instrument = minimalmodbus.Instrument(PORT, SLAVE_ADDRESS)
        instrument.serial.baudrate = BAUDRATE
        instrument.serial.bytesize = BYTESIZE
        instrument.serial.parity   = PARITY
        instrument.serial.stopbits = STOPBITS
        instrument.serial.timeout  = 1.0
        instrument.mode = minimalmodbus.MODE_RTU
        instrument.clear_buffers_before_each_transaction = True

        print(f"Ayarlar: {BAUDRATE} baud, 8-{PARITY}-{STOPBITS}")
        
        # 1. Sensör Bilgisi Okuma (Register 1032 - Firmware Version veya benzeri bir ID)
        # Not: Manualde Register 1032 bahsediliyor, Protokol adresi = 1031
        try:
            # Alternatif: Device Address Limits (Register 4098 -> Adres 4097)
            # Bu genellikle güvenli bir okumadır.
            limits = instrument.read_registers(4097, 4, functioncode=3)
            print(f" Bağlantı BAŞARILI! Cihaz Yanıt Verdi.")
            print(f" Device Address Limits (Raw): {limits}")
        except Exception as e:
            print(f" Temel okuma hatası: {e}")
            print(" -> Kablo bağlantısını ve COM port numarasını kontrol edin.")
            return

        # 2. Oksijen Değeri Okuma (PMC1)
        # Manual Register: 2090 -> Protokol Adresi: 2089
        # Veri Tipi: Float (2 Register)
        try:
            regs_o2 = instrument.read_registers(2089, 10, functioncode=3) 
            # 10 register okuyoruz çünkü manual sayfa 36'da blok okuma öneriliyor
            # Reg 1-2: Unit, Reg 3-4: Value, Reg 5-6: Status...
            
            o2_unit_code = (regs_o2[0] << 16) + regs_o2[1]
            o2_value = decode_float(regs_o2[2:4])
            
            print(f"\n--- Oksijen Ölçümü (PMC1) ---")
            print(f" Ham Veri: {regs_o2}")
            print(f" Oksijen Değeri: {o2_value:.4f}")
            print(f" Birim Kodu: {hex(o2_unit_code)}")
            
        except Exception as e:
            print(f" Oksijen okuma hatası: {e}")

        # 3. Sıcaklık Değeri Okuma (PMC6)
        # Manual Register: 2410 -> Protokol Adresi: 2409
        try:
            regs_temp = instrument.read_registers(2409, 4, functioncode=3)
            temp_value = decode_float(regs_temp[2:4])
            print(f"\n--- Sıcaklık Ölçümü (PMC6) ---")
            print(f" Sıcaklık Değeri: {temp_value:.2f} °C")
            
        except Exception as e:
            print(f" Sıcaklık okuma hatası: {e}")

    except Exception as main_err:
        print(f"\nKRİTİK HATA: Port açılamadı veya cihaz bulunamadı.\nDetay: {main_err}")

if __name__ == "__main__":
    connect_visiferm()