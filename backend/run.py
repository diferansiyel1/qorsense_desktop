#!/usr/bin/env python3
"""
QorSense Backend - PyInstaller Entry Point

Bu dosya, PyInstaller ile frozen binary oluşturulduğunda ana giriş noktasıdır.
Sidecar Pattern için optimize edilmiştir.

Kritik Özellikler:
1. sys._MEIPASS ile doğru path çözümlemesi
2. Dinamik port ataması (Electron ile haberleşme için)
3. Production modunda docs/swagger kapatma
4. Graceful shutdown desteği
"""

import argparse
import os
import signal
import socket
import sys
from contextlib import closing

# ============================================================================
# PATH FIX: PyInstaller sys._MEIPASS Çözümlemesi
# ============================================================================
# PyInstaller, uygulamayı çalıştırırken tüm dosyaları geçici bir klasöre çıkarır.
# Bu geçici klasörün yolu sys._MEIPASS içinde saklanır.
# Frozen binary'de doğru path'leri bulmak için bu değeri kullanmalıyız.

def get_base_path() -> str:
    """
    Base path'i döndürür:
    - Frozen (PyInstaller): sys._MEIPASS
    - Development: Script'in bulunduğu klasör
    """
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        # PyInstaller frozen binary
        return sys._MEIPASS
    # Normal Python çalıştırma
    return os.path.dirname(os.path.abspath(__file__))


def get_resource_path(relative_path: str) -> str:
    """
    Kaynak dosyalarının mutlak yolunu döndürür.
    PyInstaller frozen binary'de sys._MEIPASS kullanır.
    
    Örnek:
        get_resource_path("assets/logo.png") 
        -> "/tmp/_MEI123456/assets/logo.png" (frozen)
        -> "/home/user/project/backend/assets/logo.png" (dev)
    """
    base_path = get_base_path()
    return os.path.join(base_path, relative_path)


def get_data_path() -> str:
    """
    Kalıcı veri dosyaları için path döndürür (SQLite, logs, vb.)
    Frozen binary'de executable'ın yanına yazılır.
    """
    if getattr(sys, 'frozen', False):
        # Frozen: executable'ın bulunduğu klasör
        return os.path.dirname(sys.executable)
    # Development: backend klasörü
    return os.path.dirname(os.path.abspath(__file__))


# ============================================================================
# PORT YÖNETİMİ
# ============================================================================

def find_free_port(start_port: int = 8000, max_attempts: int = 100) -> int:
    """
    Boş bir port bulur.
    Electron bu portu dinleyerek backend ile haberleşir.
    """
    for port in range(start_port, start_port + max_attempts):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            try:
                sock.bind(('127.0.0.1', port))
                return port
            except OSError:
                continue
    raise RuntimeError(f"No free port found in range {start_port}-{start_port + max_attempts}")


def write_port_file(port: int, filepath: str = None):
    """
    Port numarasını bir dosyaya yazar.
    Electron bu dosyayı okuyarak hangi porta bağlanacağını öğrenir.
    """
    if filepath is None:
        filepath = os.path.join(get_data_path(), ".backend_port")

    with open(filepath, 'w') as f:
        f.write(str(port))

    return filepath


# ============================================================================
# ENVIRONMENT SETUP
# ============================================================================

def setup_environment(port: int, production: bool = True):
    """
    Çevre değişkenlerini ayarlar.
    Production modunda docs/swagger kapatılır.
    """
    # Port ayarla
    os.environ['BACKEND_PORT'] = str(port)
    os.environ['BACKEND_HOST'] = '127.0.0.1'

    # Frozen binary tespiti
    if getattr(sys, 'frozen', False):
        os.environ['QORSENSE_FROZEN'] = '1'

    # Production mode
    if production:
        os.environ['ENVIRONMENT'] = 'production'
        # Docs'u kapatmak için settings'e sinyal gönder
        os.environ['DISABLE_DOCS'] = '1'

    # Database path - kalıcı veri klasöründe
    db_path = os.path.join(get_data_path(), 'qorsense.db')
    os.environ['DATABASE_URL'] = f'sqlite+aiosqlite:///{db_path}'

    # Log file path
    log_path = os.path.join(get_data_path(), 'backend.log')
    os.environ['LOG_FILE'] = log_path

    # CORS - localhost için explicit portlar (Electron için)
    # Not: Starlette wildcard (*) desteklemez, explicit port gerekir
    os.environ['CORS_ORIGINS'] = 'http://localhost:3000,http://localhost:3001,http://127.0.0.1:3000,http://127.0.0.1:3001,http://localhost:8000,http://127.0.0.1:8000'


# ============================================================================
# GRACEFUL SHUTDOWN
# ============================================================================

shutdown_requested = False

def signal_handler(signum, frame):
    """Graceful shutdown için sinyal handler."""
    global shutdown_requested
    print(f"\n[QorSense] Shutdown sinyali alındı ({signum}). Kapatılıyor...")
    shutdown_requested = True
    sys.exit(0)


def setup_signal_handlers():
    """SIGINT ve SIGTERM sinyallerini yakala."""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Windows için SIGBREAK
    if sys.platform == 'win32':
        signal.signal(signal.SIGBREAK, signal_handler)


# ============================================================================
# MAIN ENTRY POINT
# ============================================================================

def main():
    """Ana giriş noktası."""
    parser = argparse.ArgumentParser(description='QorSense Backend Server')
    parser.add_argument(
        '--port',
        type=int,
        default=0,
        help='Backend port (0 = otomatik bul)'
    )
    parser.add_argument(
        '--dev',
        action='store_true',
        help='Development mode (docs/swagger aktif)'
    )
    parser.add_argument(
        '--version',
        action='store_true',
        help='Versiyon bilgisini göster'
    )

    args = parser.parse_args()

    # Version check
    if args.version:
        print("QorSense Backend v1.0.0")
        print(f"Frozen: {getattr(sys, 'frozen', False)}")
        print(f"Base Path: {get_base_path()}")
        print(f"Data Path: {get_data_path()}")
        sys.exit(0)

    # Port belirleme
    if args.port > 0:
        port = args.port
    else:
        port = find_free_port()

    print(f"[QorSense] Port: {port}")
    print(f"[QorSense] Mode: {'Development' if args.dev else 'Production'}")
    print(f"[QorSense] Frozen: {getattr(sys, 'frozen', False)}")

    # Environment setup
    setup_environment(port, production=not args.dev)

    # Port dosyasını yaz (Electron için)
    port_file = write_port_file(port)
    print(f"[QorSense] Port file: {port_file}")

    # Signal handlers
    setup_signal_handlers()

    # Path'i ayarla (frozen binary için gerekli)
    base_path = get_base_path()
    if base_path not in sys.path:
        sys.path.insert(0, base_path)

    # Backend'i import et ve başlat
    try:
        import uvicorn
        from backend.main import app

        # Production modunda docs'u kapat
        if not args.dev and os.environ.get('DISABLE_DOCS') == '1':
            app.docs_url = None
            app.redoc_url = None
            app.openapi_url = None
            print("[QorSense] Swagger/Docs devre dışı (production mode)")

        print(f"[QorSense] Starting server at http://127.0.0.1:{port}")
        print("=" * 50)

        uvicorn.run(
            app,
            host='127.0.0.1',
            port=port,
            log_level='info',
            # Frozen binary'de reload kullanma
            reload=False
        )

    except Exception as e:
        print(f"[QorSense] ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
