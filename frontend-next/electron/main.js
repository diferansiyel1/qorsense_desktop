/**
 * QorSense Desktop - Electron Main Process
 * 
 * Bu dosya, Electron uygulamasının ana sürecidir.
 * "Sidecar Pattern" kullanarak Python backend'i yönetir.
 * 
 * Kritik Görevler:
 * 1. OS tespiti (Windows/Mac)
 * 2. Backend binary'sini spawn etme
 * 3. Health-check ile backend'in hazır olmasını bekleme
 * 4. Graceful shutdown (zombie process önleme)
 * 5. Loading screen gösterme
 * 
 * @author QorSense Team
 */

const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const http = require('http');
const serve = require('electron-serve');

// ============================================================================
// CONFIGURATION
// ============================================================================

const CONFIG = {
    // Backend health check settings
    healthCheckUrl: '/health',
    healthCheckInterval: 500,  // ms
    healthCheckTimeout: 60000, // 60 saniye max bekleme (frozen binary yavaş olabilir)

    // Window settings
    windowWidth: 1400,
    windowHeight: 900,
    minWidth: 1024,
    minHeight: 768,

    // Backend default port (dynamic olarak değişebilir)
    defaultPort: 8000,
};

// ============================================================================
// GLOBAL STATE
// ============================================================================
let mainWindow = null;
let loadingWindow = null;
let backendProcess = null;
let backendPort = CONFIG.defaultPort;

// Production modu için static file server'ı hazırla
// app.getAppPath() asar içini gösterir, electron-serve bunu handle eder
const appServe = app.isPackaged ? serve({ directory: 'out' }) : null;
let isQuitting = false;

// ============================================================================
// OS DETECTION
// ============================================================================

/**
 * İşletim sistemini tespit eder
 * @returns {'windows' | 'mac' | 'linux'}
 */
function getOS() {
    switch (process.platform) {
        case 'win32':
            return 'windows';
        case 'darwin':
            return 'mac';
        default:
            return 'linux';
    }
}

/**
 * Backend binary'sinin yolunu döndürür
 * Development ve production modları için farklı yollar kullanır
 */
function getBackendPath() {
    const os = getOS();
    const isDev = !app.isPackaged;

    // Proje root dizini
    const projectRoot = path.join(__dirname, '../..');

    if (isDev) {
        // Development: venv içindeki Python'u kullan
        // PYTHONPATH'i proje root'una ayarla
        const venvPython = os === 'windows'
            ? path.join(projectRoot, 'venv', 'Scripts', 'python.exe')
            : path.join(projectRoot, 'venv', 'bin', 'python');

        // venv varsa onu kullan, yoksa sistem Python'u
        const pythonCommand = fs.existsSync(venvPython) ? venvPython : 'python3';

        return {
            command: pythonCommand,
            args: [path.join(projectRoot, 'backend', 'run.py'), '--dev'],
            cwd: projectRoot,  // Project root olarak ayarla - PYTHONPATH için önemli
            env: {
                ...process.env,
                PYTHONPATH: projectRoot,  // Backend modülünü bulmak için
                PYTHONUNBUFFERED: '1',
            }
        };
    }

    // Production: Frozen binary'yi çalıştır
    // Binary, extraResources ile pakete dahil edilmiş olacak
    const resourcesPath = process.resourcesPath;
    const binaryName = os === 'windows' ? 'qorsense-backend.exe' : 'qorsense-backend';
    const binaryPath = path.join(resourcesPath, 'backend-binaries', binaryName);

    console.log(`[Electron] Backend binary path: ${binaryPath}`);
    console.log(`[Electron] Binary exists: ${fs.existsSync(binaryPath)}`);

    return {
        command: binaryPath,
        args: [],
        cwd: path.dirname(binaryPath),
        env: {
            ...process.env,
            PYTHONUNBUFFERED: '1',
        }
    };
}


// ============================================================================
// BACKEND PROCESS MANAGEMENT
// ============================================================================

/**
 * Backend sürecini başlatır
 * @returns {Promise<number>} Backend portu
 */
function startBackend() {
    return new Promise((resolve, reject) => {
        const backendConfig = getBackendPath();

        console.log(`[Electron] Starting backend...`);
        console.log(`[Electron] Command: ${backendConfig.command}`);
        console.log(`[Electron] Args: ${backendConfig.args.join(' ')}`);
        console.log(`[Electron] CWD: ${backendConfig.cwd}`);

        try {
            backendProcess = spawn(
                backendConfig.command,
                backendConfig.args,
                {
                    cwd: backendConfig.cwd,
                    env: backendConfig.env,  // Use env from getBackendPath()
                    // Windows için console window gösterme
                    windowsHide: true,
                    // Detached modunda çalıştırma (graceful shutdown için)
                    detached: false,
                }
            );


            // stdout dinle (port bilgisi için)
            backendProcess.stdout.on('data', (data) => {
                const output = data.toString();
                console.log(`[Backend] ${output}`);

                // Port bilgisini yakala
                const portMatch = output.match(/Port:\s*(\d+)/);
                if (portMatch) {
                    backendPort = parseInt(portMatch[1], 10);
                    console.log(`[Electron] Detected backend port: ${backendPort}`);
                }

                // Server başladı mı kontrol et
                if (output.includes('Starting server') || output.includes('Uvicorn running')) {
                    resolve(backendPort);
                }
            });

            // stderr dinle
            backendProcess.stderr.on('data', (data) => {
                const error = data.toString();
                console.error(`[Backend Error] ${error}`);

                // Uvicorn bazen stderr'e log yazar
                if (error.includes('Started server process') || error.includes('Application startup complete')) {
                    resolve(backendPort);
                }
            });

            // Process çıkışını yakala
            backendProcess.on('exit', (code, signal) => {
                console.log(`[Electron] Backend exited with code ${code}, signal ${signal}`);

                if (!isQuitting && code !== 0) {
                    // Beklenmedik çıkış - kullanıcıya bildir
                    dialog.showErrorBox(
                        'Backend Hatası',
                        `Backend süreci beklenmedik şekilde sonlandı (kod: ${code}).\nUygulama yeniden başlatılması gerekebilir.`
                    );
                }

                backendProcess = null;
            });

            // Hata yakala
            backendProcess.on('error', (error) => {
                console.error(`[Electron] Failed to start backend: ${error.message}`);
                reject(error);
            });

            // Timeout ile resolve et (stdout'tan port alamazsak)
            setTimeout(() => {
                if (backendPort) {
                    resolve(backendPort);
                }
            }, 3000);

        } catch (error) {
            console.error(`[Electron] Backend spawn error: ${error.message}`);
            reject(error);
        }
    });
}

/**
 * Backend'i graceful olarak durdurur
 */
function stopBackend() {
    return new Promise((resolve) => {
        if (!backendProcess) {
            resolve();
            return;
        }

        console.log('[Electron] Stopping backend...');
        isQuitting = true;

        // SIGTERM gönder
        if (process.platform === 'win32') {
            // Windows'ta process.kill farklı çalışır
            spawn('taskkill', ['/pid', backendProcess.pid, '/f', '/t']);
        } else {
            backendProcess.kill('SIGTERM');
        }

        // 5 saniye bekle, hala çalışıyorsa SIGKILL
        const forceKillTimeout = setTimeout(() => {
            if (backendProcess) {
                console.log('[Electron] Force killing backend...');
                backendProcess.kill('SIGKILL');
            }
            resolve();
        }, 5000);

        backendProcess.on('exit', () => {
            clearTimeout(forceKillTimeout);
            console.log('[Electron] Backend stopped');
            resolve();
        });
    });
}

// ============================================================================
// HEALTH CHECK
// ============================================================================

/**
 * Backend'in hazır olup olmadığını kontrol eder
 * @returns {Promise<boolean>}
 */
function checkBackendHealth() {
    return new Promise((resolve) => {
        const options = {
            hostname: '127.0.0.1',
            port: backendPort,
            path: CONFIG.healthCheckUrl,
            method: 'GET',
            timeout: 2000,
        };

        const req = http.request(options, (res) => {
            resolve(res.statusCode === 200);
        });

        req.on('error', () => {
            resolve(false);
        });

        req.on('timeout', () => {
            req.destroy();
            resolve(false);
        });

        req.end();
    });
}

/**
 * Backend hazır olana kadar bekler
 * @returns {Promise<void>}
 */
function waitForBackend() {
    return new Promise((resolve, reject) => {
        const startTime = Date.now();

        const check = async () => {
            const elapsed = Date.now() - startTime;

            if (elapsed > CONFIG.healthCheckTimeout) {
                reject(new Error('Backend health check timeout'));
                return;
            }

            const isHealthy = await checkBackendHealth();

            if (isHealthy) {
                console.log(`[Electron] Backend is ready (${elapsed}ms)`);
                resolve();
            } else {
                setTimeout(check, CONFIG.healthCheckInterval);
            }
        };

        check();
    });
}

// ============================================================================
// WINDOW MANAGEMENT
// ============================================================================

/**
 * Loading ekranını oluşturur
 */
function createLoadingWindow() {
    loadingWindow = new BrowserWindow({
        width: 400,
        height: 300,
        frame: false,
        transparent: true,
        resizable: false,
        center: true,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
        },
    });

    // Inline HTML loading screen
    const loadingHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
          font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
          background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
          color: white;
          height: 100vh;
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          -webkit-app-region: drag;
          border-radius: 12px;
          overflow: hidden;
        }
        .logo {
          font-size: 32px;
          font-weight: bold;
          background: linear-gradient(90deg, #00ADB5, #00D4FF);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          margin-bottom: 24px;
        }
        .spinner {
          width: 40px;
          height: 40px;
          border: 3px solid rgba(0, 173, 181, 0.2);
          border-top: 3px solid #00ADB5;
          border-radius: 50%;
          animation: spin 1s linear infinite;
          margin-bottom: 16px;
        }
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        .status {
          font-size: 14px;
          color: rgba(255, 255, 255, 0.7);
        }
      </style>
    </head>
    <body>
      <div class="logo">QorSense</div>
      <div class="spinner"></div>
      <div class="status">Sistem başlatılıyor...</div>
    </body>
    </html>
  `;

    loadingWindow.loadURL(`data:text/html;charset=utf-8,${encodeURIComponent(loadingHtml)}`);
}

/**
 * Ana uygulama penceresini oluşturur
 */
function createMainWindow() {
    mainWindow = new BrowserWindow({
        width: CONFIG.windowWidth,
        height: CONFIG.windowHeight,
        minWidth: CONFIG.minWidth,
        minHeight: CONFIG.minHeight,

        // Başlangıçta gizle
        show: false,

        // =====================================
        // SCADA KIOSK MODE (Opsiyonel)
        // Aşağıdaki satırları açarak tam ekran, 
        // kapatılamaz kiosk modu aktif edilebilir
        // =====================================
        // kiosk: true,
        // fullscreen: true,
        // frame: false,
        // closable: false,
        // minimizable: false,
        // maximizable: false,
        // alwaysOnTop: true,

        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
        },
    });

    // Statik dosyaları yükle
    const isDev = !app.isPackaged;

    if (isDev) {
        // Development: Next.js dev server
        mainWindow.loadURL('http://localhost:3000');

        // DevTools aç
        mainWindow.webContents.openDevTools();
    } else {
        // Production: electron-serve ile app:// protocol üzerinden yükle
        // Bu sayede /_next/static/... gibi absolute path'ler sorunsuz çalışır

        console.log('[Electron] Loading production app via electron-serve...');

        // Önce serve fonksiyonunu çağır (URL şemasını kaydeder)
        appServe(mainWindow).then(() => {
            // app://- protokolü ile index.html yükle
            mainWindow.loadURL('app://-/index.html');
            console.log('[Electron] App loaded via app:// protocol');
        }).catch((err) => {
            console.error('[Electron] Failed to load app:', err);
            dialog.showErrorBox('Yükleme Hatası', 'Uygulama arayüzü yüklenemedi: ' + err.message);
        });
    }

    // Pencere hazır olduğunda göster
    mainWindow.once('ready-to-show', () => {
        // Loading penceresini kapat
        if (loadingWindow) {
            loadingWindow.close();
            loadingWindow = null;
        }

        mainWindow.show();
        mainWindow.focus();
    });

    // Pencere kapatıldığında
    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

// ============================================================================
// IPC HANDLERS
// ============================================================================

// Backend port'unu renderer'a gönder
ipcMain.handle('get-backend-port', () => {
    return backendPort;
});

// Backend URL'ini renderer'a gönder
ipcMain.handle('get-backend-url', () => {
    return `http://127.0.0.1:${backendPort}`;
});

// App bilgilerini renderer'a gönder
ipcMain.handle('get-app-info', () => {
    return {
        version: app.getVersion(),
        name: app.getName(),
        isPackaged: app.isPackaged,
        platform: process.platform,
    };
});

// ============================================================================
// APP LIFECYCLE
// ============================================================================

app.whenReady().then(async () => {
    console.log('[Electron] App ready');
    console.log(`[Electron] Platform: ${getOS()}`);
    console.log(`[Electron] Is Packaged: ${app.isPackaged}`);

    try {
        // 1. Loading screen göster
        createLoadingWindow();

        // 2. Backend'i başlat
        await startBackend();

        // 3. Backend hazır olana kadar bekle
        await waitForBackend();

        // 4. Ana pencereyi aç
        createMainWindow();

    } catch (error) {
        console.error('[Electron] Startup error:', error);

        dialog.showErrorBox(
            'Başlatma Hatası',
            `Uygulama başlatılamadı: ${error.message}\n\nLütfen uygulamayı yeniden başlatın.`
        );

        app.quit();
    }
});

// macOS: Tüm pencereler kapatıldığında uygulamayı kapatma
app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        app.quit();
    }
});

// macOS: Dock'tan tekrar açıldığında
app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
        createMainWindow();
    }
});

// Uygulama kapanmadan önce backend'i durdur
app.on('before-quit', async (event) => {
    if (backendProcess && !isQuitting) {
        event.preventDefault();
        await stopBackend();
        app.quit();
    }
});

// Uygulama sonlandığında
app.on('will-quit', async () => {
    await stopBackend();
});

// ============================================================================
// ERROR HANDLING
// ============================================================================

process.on('uncaughtException', (error) => {
    console.error('[Electron] Uncaught exception:', error);

    dialog.showErrorBox(
        'Kritik Hata',
        `Beklenmedik bir hata oluştu: ${error.message}`
    );
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('[Electron] Unhandled rejection at:', promise, 'reason:', reason);
});
