/**
 * Electron API Type Definitions
 * 
 * TypeScript type definitions for the Electron preload API.
 * This enables type-safe access to window.electronAPI in the renderer.
 */

declare global {
    interface Window {
        /**
         * Electron API exposed via preload script.
         * Only available when running in Electron.
         */
        electronAPI?: {
            /**
             * Get the dynamically assigned backend port
             * @returns The port number where backend is running
             */
            getBackendPort: () => Promise<number>;

            /**
             * Get the full backend URL
             * @returns The complete URL (e.g., "http://127.0.0.1:8000")
             */
            getBackendUrl: () => Promise<string>;

            /**
             * Get application info
             * @returns App metadata including version and platform
             */
            getAppInfo: () => Promise<{
                version: string;
                name: string;
                isPackaged: boolean;
                platform: string;
            }>;

            /**
             * Check if running in Electron
             * @returns Always true when in Electron
             */
            isElectron: () => boolean;

            /**
             * Current platform
             */
            platform: string;
        };
    }
}

export { };
