"""
Sanal PLC (Modbus TCP Server) - Test Amaçlı

Bu script, gerçek bir PLC olmadan Modbus TCP bağlantısını test etmek için
pH ve sıcaklık sensör verilerini simüle eden bir Modbus TCP sunucusu oluşturur.

Kullanım:
    python tools/virtiual_plc.py

Bağlantı:
    IP: 127.0.0.1
    Port: 5020
    Register 0-1: pH değeri (Float32 Big-Endian)
    Register 2-3: Sıcaklık değeri (Float32 Big-Endian)
"""
import logging
import asyncio
import math
import struct
from pymodbus.datastore import (
    ModbusSequentialDataBlock,
    ModbusDeviceContext,
    ModbusServerContext,
)
from pymodbus.server import StartAsyncTcpServer

# --- KONFIGÜRASYON ---
IP_ADDRESS = "127.0.0.1"  # Localhost
PORT = 5020               # Yetki sorunu yaşamamak için 502 yerine 5020 kullandık
UPDATE_RATE = 1.0         # Veri güncelleme hızı (saniye)

# Logger Ayarları
logging.basicConfig(
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
log = logging.getLogger(__name__)


def float_to_registers(value: float) -> list:
    """
    Float32 değerini, live_worker.py'nin beklediği 
    Big-Endian formatında (2 adet 16-bit register) paketler.
    
    Args:
        value: Float değer
        
    Returns:
        2 elemanlı liste [high_word, low_word]
    """
    # >f: Big Endian Float
    packed = struct.pack('>f', value)
    # 2 adet unsigned short (16-bit) olarak ayır
    unpacked = struct.unpack('>HH', packed)
    return list(unpacked)


async def simulation_loop(context: ModbusServerContext):
    """
    Arka planda çalışan ve sensör verilerini simüle eden async döngü.
    """
    log.info("--- SİMÜLASYON BAŞLATILDI: Veriler üretiliyor... ---")
    register_address = 0  # live_worker.py varsayılan adresi
    slave_id = 0  # single=True olduğu için slave_id 0
    
    t = 0.0
    while True:
        try:
            # 1. Veri Üretimi (Matematiksel Simülasyon)
            # pH: 7.0 etrafında salınan sinüs dalgası
            ph_val = 7.0 + (0.5 * math.sin(t * 0.1))
            
            # Sıcaklık: 25.0'dan yavaşça artan trend
            temp_val = 25.0 + (t * 0.01)
            
            # 2. Veriyi Paketleme (Float32 -> Registers)
            ph_registers = float_to_registers(ph_val)
            temp_registers = float_to_registers(temp_val)
            
            # 3. Server Hafızasını Güncelleme
            # Holding Registers (function code 3)
            slave = context[slave_id]
            
            # Register 0-1: pH Değeri
            slave.setValues(3, register_address, ph_registers)
            
            # Register 2-3: Sıcaklık Değeri
            slave.setValues(3, register_address + 2, temp_registers)
            
            # Her 5 saniyede bir log yaz
            if int(t) % 5 == 0:
                log.info(f"Simüle -> pH: {ph_val:.2f} | Temp: {temp_val:.2f}°C")
            
            t += 1.0
            await asyncio.sleep(UPDATE_RATE)
            
        except asyncio.CancelledError:
            log.info("Simülasyon durduruldu.")
            break
        except Exception as e:
            log.error(f"Simülasyon hatası: {e}")
            break


async def run_server():
    """Ana sunucu fonksiyonu."""
    # 1. Veri Bloğu Oluştur (0-100 arası adresleri tutabilen hafıza)
    # pymodbus 3.11+ için ModbusDeviceContext kullanılıyor
    store = ModbusDeviceContext(
        di=ModbusSequentialDataBlock(0, [0]*100),  # Discrete Inputs
        co=ModbusSequentialDataBlock(0, [0]*100),  # Coils
        hr=ModbusSequentialDataBlock(0, [0]*100),  # Holding Registers
        ir=ModbusSequentialDataBlock(0, [0]*100)   # Input Registers
    )
    
    # single=True için devices parametresi kullanılıyor (pymodbus 3.11+)
    context = ModbusServerContext(devices=store, single=True)

    # 2. Simülasyon Task'ını Başlat
    log.info(f"Sanal PLC Başlatılıyor: {IP_ADDRESS}:{PORT}")
    log.info("Uygulamanızdan bu IP ve Port'a bağlanın.")
    log.info("Register 0-1: pH, Register 2-3: Sıcaklık")
    log.info("-" * 50)
    
    # Simülasyon task'ı
    sim_task = asyncio.create_task(simulation_loop(context))
    
    try:
        # 3. TCP Server'ı Başlat
        await StartAsyncTcpServer(
            context=context,
            address=(IP_ADDRESS, PORT)
        )
    except asyncio.CancelledError:
        pass
    finally:
        sim_task.cancel()


if __name__ == "__main__":
    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        log.info("Sunucu kapatıldı (Ctrl+C)")