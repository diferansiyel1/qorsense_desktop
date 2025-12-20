"""
Hamilton VisiFerm ARC Air Modbus Bağlantı Teşhis Aracı
------------------------------------------------------
Bu betik Modbus bağlantı sorunlarını tespit etmek için detaylı testler yapar.
"""
import serial
import serial.tools.list_ports
import time
import struct

def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)

def list_all_ports():
    """Tüm COM portlarını detaylı listele"""
    print_header("MEVCUT COM PORTLARI")
    ports = list(serial.tools.list_ports.comports())
    
    if not ports:
        print("❌ HİÇBİR COM PORTU BULUNAMADI!")
        print("   → USB kablosu takılı mı?")
        print("   → Aygıt Yöneticisi'nde sarı ünlem var mı?")
        return None
    
    arc_air_port = None
    for p in ports:
        print(f"\n📌 {p.device}")
        print(f"   Açıklama: {p.description}")
        print(f"   Üretici: {p.manufacturer}")
        print(f"   VID:PID: {p.vid}:{p.pid}")
        print(f"   Hardware ID: {p.hwid}")
        
        # FTDI çipli cihazları kontrol et (Hamilton ARC Air genellikle FTDI kullanır)
        if p.vid == 0x0403:  # FTDI Vendor ID
            print(f"   ✅ FTDI çip tespit edildi - Bu muhtemelen ARC Air kablosu!")
            arc_air_port = p.device
        elif "USB Serial" in (p.description or ""):
            print(f"   ⚠️  USB Seri port - Olası ARC Air kablosu")
            if arc_air_port is None:
                arc_air_port = p.device
    
    return arc_air_port

def test_serial_connection(port):
    """Basit seri port bağlantı testi"""
    print_header(f"SERİ PORT BAĞLANTI TESTİ: {port}")
    
    # Hamilton VisiFerm varsayılan ayarları
    configs = [
        {"baudrate": 19200, "parity": serial.PARITY_NONE, "stopbits": 2, "name": "Hamilton Varsayılan (19200, N, 8, 2)"},
        {"baudrate": 9600, "parity": serial.PARITY_NONE, "stopbits": 2, "name": "Alternatif 1 (9600, N, 8, 2)"},
        {"baudrate": 19200, "parity": serial.PARITY_EVEN, "stopbits": 1, "name": "Alternatif 2 (19200, E, 8, 1)"},
        {"baudrate": 38400, "parity": serial.PARITY_NONE, "stopbits": 2, "name": "Alternatif 3 (38400, N, 8, 2)"},
    ]
    
    for cfg in configs:
        print(f"\n🔄 Test: {cfg['name']}")
        try:
            ser = serial.Serial(
                port=port,
                baudrate=cfg['baudrate'],
                parity=cfg['parity'],
                stopbits=cfg['stopbits'],
                bytesize=8,
                timeout=2
            )
            
            if ser.is_open:
                print(f"   ✅ Port açıldı")
                # Buffer'ları temizle
                ser.reset_input_buffer()
                ser.reset_output_buffer()
                ser.close()
                print(f"   ✅ Port kapatıldı")
                return True
            else:
                print(f"   ❌ Port açılamadı")
        except serial.SerialException as e:
            print(f"   ❌ Hata: {e}")
            if "PermissionError" in str(e) or "Erişim" in str(e):
                print("   → Port başka bir program tarafından kullanılıyor olabilir!")
                print("   → ArcAir yazılımını veya diğer seri terminalleri kapatın.")
            elif "FileNotFoundError" in str(e) or "bulunamadı" in str(e).lower():
                print("   → Port bulunamadı. Kablo bağlantısını kontrol edin.")
    
    return False

def test_modbus_communication(port, slave_ids=[1, 2, 247]):
    """Modbus RTU iletişim testi"""
    print_header(f"MODBUS RTU İLETİŞİM TESTİ: {port}")
    
    try:
        import minimalmodbus
    except ImportError:
        print("❌ minimalmodbus kütüphanesi yüklü değil!")
        print("   pip install minimalmodbus")
        try:
            from pymodbus.client import ModbusSerialClient
        except ImportError:
            print("❌ pymodbus da yüklü değil!")
            return False
    
    found_device = False
    
    for slave_id in slave_ids:
        print(f"\n🔄 Slave ID {slave_id} deneniyor...")
        
        try:
            instrument = minimalmodbus.Instrument(port, slave_id)
            instrument.serial.baudrate = 19200
            instrument.serial.bytesize = 8
            instrument.serial.parity = serial.PARITY_NONE
            instrument.serial.stopbits = 2
            instrument.serial.timeout = 1.0
            instrument.mode = minimalmodbus.MODE_RTU
            instrument.clear_buffers_before_each_transaction = True
            
            # Basit register okuma denemesi
            try:
                # Device Address Limits (güvenli bir register)
                result = instrument.read_registers(4097, 2, functioncode=3)
                print(f"   ✅ YANIT ALINDI! Slave ID: {slave_id}")
                print(f"   📊 Register değerleri: {result}")
                found_device = True
                
                # Daha fazla bilgi oku
                try:
                    # Firmware version veya benzeri
                    info = instrument.read_registers(1031, 2, functioncode=3)
                    print(f"   📊 Cihaz bilgisi: {info}")
                except:
                    pass
                    
                break
                
            except minimalmodbus.NoResponseError:
                print(f"   ⚠️  Yanıt yok - Cihaz bu ID'de değil")
            except minimalmodbus.InvalidResponseError as e:
                print(f"   ⚠️  Geçersiz yanıt: {e}")
            except Exception as e:
                print(f"   ❌ Okuma hatası: {e}")
                
        except Exception as e:
            print(f"   ❌ Bağlantı hatası: {e}")
    
    return found_device

def run_diagnostics():
    """Tüm teşhisleri çalıştır"""
    print("\n" + "🔬" * 30)
    print("  Hamilton VisiFerm ARC Air - Bağlantı Teşhis Aracı")
    print("🔬" * 30)
    
    # 1. Port listesi
    detected_port = list_all_ports()
    
    if detected_port is None:
        print_header("SORUN TESPİT EDİLDİ")
        print("""
❌ Hiçbir COM portu tespit edilmedi.

OLASI SEBEPLER VE ÇÖZÜMLER:
1. USB kablosu takılı değil
   → Kabloyu bilgisayara takın
   
2. Sürücü yüklenmemiş
   → Windows Aygıt Yöneticisi'ni açın
   → "Diğer Cihazlar" altında sarı ünlem var mı kontrol edin
   → FTDI sürücüsünü yükleyin: https://ftdichip.com/drivers/
   
3. Kablo arızalı
   → Farklı bir USB portu deneyin
   → Farklı bir kablo deneyin
        """)
        return
    
    print(f"\n💡 Tespit edilen muhtemel ARC Air portu: {detected_port}")
    
    # 2. Kullanıcıdan port seçimi
    user_port = input(f"\nHangi portu test etmek istersiniz? [{detected_port}]: ").strip()
    if not user_port:
        user_port = detected_port
    
    # 3. Seri port testi
    if not test_serial_connection(user_port):
        print_header("SORUN TESPİT EDİLDİ")
        print("""
❌ Seri port bağlantısı kurulamadı.

OLASI SEBEPLER VE ÇÖZÜMLER:
1. Port başka bir program tarafından kullanılıyor
   → ArcAir yazılımını kapatın
   → Putty, Tera Term gibi terminalleri kapatın
   → Aygıt Yöneticisi'nden portu yeniden etkinleştirin
   
2. Sürücü sorunu
   → Aygıt Yöneticisi'nde cihazı kaldırıp yeniden taratın
   → En güncel FTDI sürücüsünü yükleyin
   
3. Donanım sorunu
   → Farklı USB portu deneyin
   → Kabloyu çıkarıp tekrar takın
        """)
        return
    
    # 4. Modbus testi
    print("\n💡 Seri port başarıyla açıldı. Modbus iletişimi test ediliyor...")
    
    slave_ids = input("\nTest edilecek Slave ID'leri (virgülle ayırın) [1,2,247]: ").strip()
    if slave_ids:
        slave_ids = [int(x.strip()) for x in slave_ids.split(",")]
    else:
        slave_ids = [1, 2, 247]
    
    if test_modbus_communication(user_port, slave_ids):
        print_header("✅ BAĞLANTI BAŞARILI!")
        print("""
Cihaz ile iletişim kuruldu!
Artık uygulamanızda bu ayarları kullanabilirsiniz.
        """)
    else:
        print_header("SORUN TESPİT EDİLDİ")
        print("""
❌ Modbus iletişimi kurulamadı.

OLASI SEBEPLER VE ÇÖZÜMLER:
1. Yanlış Slave ID
   → Sensörün Slave ID'sini ArcAir yazılımından kontrol edin
   → Varsayılan ID: 1 veya 2 olabilir
   
2. Yanlış baud rate
   → ArcAir yazılımından sensör ayarlarını kontrol edin
   → Varsayılan: 19200
   
3. RS485 bağlantı sorunu
   → ARC Air kablosunun sensöre düzgün bağlandığından emin olun
   → Sensör üzerindeki LED'leri kontrol edin
   
4. Sensör beslemesi
   → Sensörün güç aldığından emin olun
   → Biyoreaktör bağlantısını kontrol edin
   
5. Kablo tipi uyumsuzluğu
   → ARC Air USB kablosunun RS485 modeli olduğundan emin olun
   → Bluetooth modeli Modbus RTU desteklemez!

DETAYLI DEBUG İÇİN:
→ hamilton_connect.py dosyasını PORT ve SLAVE_ADDRESS değerlerini 
  güncelleyerek çalıştırın
→ ArcAir yazılımı ile sensöre bağlanıp ayarları doğrulayın
        """)

if __name__ == "__main__":
    run_diagnostics()
