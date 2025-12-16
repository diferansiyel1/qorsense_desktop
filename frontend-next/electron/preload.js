/**
 * QorSense Desktop - Electron Preload Script
 * 
 * Bu dosya, Electron'un güvenlik modelini koruyarak
 * renderer process'e güvenli API'ler sunar.
 * 
 * contextBridge ile expose edilen API'ler, window.electronAPI
 * üzerinden erişilebilir.
 */

const { contextBridge, ipcRenderer } = require('electron');

// ============================================================================
// SECURE API BRIDGE
// ============================================================================

contextBridge.exposeInMainWorld('electronAPI', {
    /**
     * Backend port numarasını alır
     * @returns {Promise<number>}
     */
    getBackendPort: () => ipcRenderer.invoke('get-backend-port'),

    /**
     * Backend URL'ini alır
     * @returns {Promise<string>}
     */
    getBackendUrl: () => ipcRenderer.invoke('get-backend-url'),

    /**
     * Uygulama bilgilerini alır
     * @returns {Promise<{version: string, name: string, isPackaged: boolean, platform: string}>}
     */
    getAppInfo: () => ipcRenderer.invoke('get-app-info'),

    /**
     * Electron ortamında çalışıp çalışmadığını kontrol eder
     * @returns {boolean}
     */
    isElectron: () => true,

    /**
     * Platform bilgisi
     * @returns {string}
     */
    platform: process.platform,
});

// ============================================================================
// TYPE DEFINITIONS (for TypeScript)
// ============================================================================

/**
 * TypeScript için tip tanımları
 * frontend-next/types/electron.d.ts dosyasına eklenebilir:
 * 
 * declare global {
 *   interface Window {
 *     electronAPI?: {
 *       getBackendPort: () => Promise<number>;
 *       getBackendUrl: () => Promise<string>;
 *       getAppInfo: () => Promise<{
 *         version: string;
 *         name: string;
 *         isPackaged: boolean;
 *         platform: string;
 *       }>;
 *       isElectron: () => boolean;
 *       platform: string;
 *     };
 *   }
 * }
 */

console.log('[Preload] Electron API exposed to renderer');
