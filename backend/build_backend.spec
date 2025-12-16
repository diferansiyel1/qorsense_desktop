# -*- mode: python ; coding: utf-8 -*-
"""
QorSense Backend - PyInstaller Spec File

Bu dosya, Python backend'i tek parça (one-file) binary'ye dönüştürür.
SCADA sistemlerinde çalışmak üzere optimize edilmiştir.

Kullanım:
    cd backend
    pyinstaller build_backend.spec

Çıktı:
    dist/qorsense-backend (Unix) veya dist/qorsense-backend.exe (Windows)

KRİTİK NOTLAR:
1. Hidden imports listesi eksik modül hatalarında güncellenmelidir
2. Datas listesi statik dosyaları binary'ye dahil eder
3. sys._MEIPASS runtime'da bu dosyalara erişim sağlar
"""

import sys
import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# ============================================================================
# PROJE AYARLARI
# ============================================================================

# Backend klasörünün yolu
backend_path = os.path.dirname(os.path.abspath(SPEC))

# Binary adı
binary_name = 'qorsense-backend'

# ============================================================================
# HIDDEN IMPORTS
# ============================================================================
# PyInstaller bazı dinamik import'ları otomatik bulamaz.
# Bu liste, runtime'da ihtiyaç duyulan tüm modülleri içerir.

hidden_imports = [
    # FastAPI ve Starlette
    'fastapi',
    'starlette',
    'starlette.middleware',
    'starlette.middleware.cors',
    'starlette.routing',
    'starlette.responses',
    'starlette.requests',
    
    # Uvicorn
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    
    # Pydantic
    'pydantic',
    'pydantic_settings',
    'pydantic.deprecated',
    'pydantic.deprecated.decorator',
    
    # SQLAlchemy (async)
    'sqlalchemy',
    'sqlalchemy.ext.asyncio',
    'sqlalchemy.orm',
    'sqlalchemy.dialects.sqlite',
    'aiosqlite',
    'greenlet',
    
    # Analiz kütüphaneleri
    'numpy',
    'pandas',
    'scipy',
    'scipy.signal',
    'scipy.fft',
    'scipy.stats',
    'sklearn',
    'sklearn.preprocessing',
    
    # Raporlama
    'reportlab',
    'reportlab.lib',
    'reportlab.lib.colors',
    'reportlab.lib.pagesizes',
    'reportlab.platypus',
    'fpdf',
    
    # HTTP
    'httpx',
    'requests',
    
    # Diğer
    'email_validator',
    'passlib',
    'passlib.hash',
    'jose',
    'jose.jwt',
    'prometheus_client',
    'python_multipart',
    'openpyxl',
    'kaleido',
    
    # Backend modülleri
    'backend',
    'backend.main',
    'backend.core',
    'backend.core.config',
    'backend.database',
    'backend.models',
    'backend.models_db',
    'backend.api',
    'backend.api.routes',
    'backend.api.routes.health',
    'backend.api.routes.sensors',
    'backend.api.routes.analytics',
    'backend.api.routes.synthetic',
    'backend.api.routes.reports',
    'backend.api.routes.auth',
    'backend.api.routes.monitoring',
    'backend.api.routes.tasks',
    'backend.analysis',
    'backend.report_gen',
    'backend.middleware',
    'backend.repositories',
    'backend.schemas',
]

# Collect submodules for complex packages
hidden_imports += collect_submodules('uvicorn')
hidden_imports += collect_submodules('starlette')
hidden_imports += collect_submodules('fastapi')

# ============================================================================
# DATA FILES
# ============================================================================
# Statik dosyalar (veritabanı şemaları, asset'ler, vb.)
# Bu dosyalar binary içine gömülür ve sys._MEIPASS ile erişilir.

datas = [
    # Assets klasörü
    (os.path.join(backend_path, 'assets'), 'assets'),
    
    # Alembic migrations (opsiyonel - production'da gerekmeyebilir)
    # (os.path.join(backend_path, 'alembic'), 'alembic'),
    
    # Core config varsayılanları
    (os.path.join(backend_path, 'core'), 'backend/core'),
    
    # API routes
    (os.path.join(backend_path, 'api'), 'backend/api'),
    
    # Schemas
    (os.path.join(backend_path, 'schemas'), 'backend/schemas'),
    
    # Repositories
    (os.path.join(backend_path, 'repositories'), 'backend/repositories'),
    
    # Middleware
    (os.path.join(backend_path, 'middleware'), 'backend/middleware'),
    
    # Tasks
    (os.path.join(backend_path, 'tasks'), 'backend/tasks'),
]

# Collect data files for packages that need them
datas += collect_data_files('plotly', includes=['package_data/**/*'])
datas += collect_data_files('scipy')

# ============================================================================
# BINARIES
# ============================================================================
# Native kütüphaneler (varsa)

binaries = []

# ============================================================================
# ANALYSIS
# ============================================================================

a = Analysis(
    # Entry point
    [os.path.join(backend_path, 'run.py')],
    
    # Paths to search for imports
    pathex=[backend_path, os.path.dirname(backend_path)],
    
    # Binary files to include
    binaries=binaries,
    
    # Data files to include
    datas=datas,
    
    # Hidden imports
    hiddenimports=hidden_imports,
    
    # Hook directories (PyInstaller hooks)
    hookspath=[],
    
    # PyInstaller hooks to use
    hooksconfig={},
    
    # Runtime hooks
    runtime_hooks=[],
    
    # Modules to exclude (boyutu küçültmek için)
    excludes=[
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
        '_pytest',
        'test',
        'tests',
    ],
    
    # Windows manifest (UAC settings)
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    
    # Cipher for bytecode encryption (None = no encryption)
    cipher=None,
    
    # Don't strip symbols (debug için)
    noarchive=False,
)

# ============================================================================
# PYZ (Python bytecode archive)
# ============================================================================

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

# ============================================================================
# EXE (Executable)
# ============================================================================

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    
    # Binary name
    name=binary_name,
    
    # Debug mode
    debug=False,
    
    # Don't strip symbols
    strip=False,
    
    # UPX compression (boyutu küçültür ama başlatmayı yavaşlatabilir)
    upx=True,
    upx_exclude=[],
    
    # Runtime temp directory name
    runtime_tmpdir=None,
    
    # Konsol penceresi
    # True = konsol göster (debug için)
    # False = konsol gizle (production için)
    console=True,  # SCADA için True önerilir (log görünürlüğü)
    
    # Windows için UAC ayarları
    disable_windowed_traceback=False,
    
    # macOS için
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    
    # Icon (varsa)
    # icon=os.path.join(backend_path, 'assets', 'icon.ico'),
)

# ============================================================================
# NOTLAR
# ============================================================================
"""
BUILD SONRASI:

1. Binary'yi test et:
   ./dist/qorsense-backend --version
   ./dist/qorsense-backend --port 8000 --dev

2. Health check:
   curl http://127.0.0.1:8000/health

3. Boyut optimizasyonu:
   - excludes listesine kullanılmayan modülleri ekle
   - UPX'i devre dışı bırak (upx=False) eğer başlatma hızı önemliyse

4. SCADA için:
   - console=True bırak (log görünürlüğü)
   - Kiosk modda çalıştırılacaksa Electron tarafında kontrol et

5. Hata ayıklama:
   - debug=True ve console=True ayarla
   - --log-level=DEBUG ile çalıştır
"""
