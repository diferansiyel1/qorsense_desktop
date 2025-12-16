/**
 * QorSense API Client
 * 
 * Type-safe Axios client with automatic token management,
 * request/response interceptors, and error handling.
 * 
 * @module lib/api-client
 */

'use client';

import axios, {
    AxiosInstance,
    AxiosError,
    AxiosRequestConfig,
    InternalAxiosRequestConfig,
    AxiosResponse,
} from 'axios';
import type { ApiError, HttpError, TokenResponse } from '@/types/api';

// ============================================================================
// Configuration
// ============================================================================

/** 
 * API base URL - Dynamic resolution for Electron
 * 
 * Priority:
 * 1. Electron IPC (wenn verfügbar) - dynamischer Port vom Backend
 * 2. Environment variable NEXT_PUBLIC_API_URL
 * 3. Default localhost:8000
 * 
 * Electron modu için: window.electronAPI.getBackendUrl() kullanılır
 * Web modu için: NEXT_PUBLIC_API_URL veya default kullanılır
 */
let API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

/**
 * Initialize API URL from Electron IPC
 * Should be called once on app startup
 */
async function initializeApiUrl(): Promise<string> {
    if (typeof window !== 'undefined' && window.electronAPI) {
        try {
            const url = await window.electronAPI.getBackendUrl();
            API_BASE_URL = url;

            // Update Axios instance defaults
            apiClient.defaults.baseURL = url;

            console.log('[API Client] Electron backend URL set to:', url);
            return url;
        } catch (error) {
            console.warn('[API Client] Failed to get Electron backend URL:', error);
        }
    }
    return API_BASE_URL;
}

/**
 * Check if running in Electron
 */
function isElectron(): boolean {
    return typeof window !== 'undefined' && !!window.electronAPI?.isElectron?.();
}

// Initialize URL on module load (async, updates API_BASE_URL)
if (typeof window !== 'undefined') {
    initializeApiUrl();
}

/** Token storage keys */
const TOKEN_KEYS = {
    ACCESS: 'qorsense_access_token',
    REFRESH: 'qorsense_refresh_token',
} as const;

/** Request timeout in milliseconds */
const REQUEST_TIMEOUT = 30000;

// ============================================================================
// Token Management
// ============================================================================

/**
 * Token storage utilities for managing JWT tokens.
 * Uses localStorage for persistence across sessions.
 */
export const tokenStorage = {
    /** Get access token from storage */
    getAccessToken(): string | null {
        if (typeof window === 'undefined') return null;
        return localStorage.getItem(TOKEN_KEYS.ACCESS);
    },

    /** Get refresh token from storage */
    getRefreshToken(): string | null {
        if (typeof window === 'undefined') return null;
        return localStorage.getItem(TOKEN_KEYS.REFRESH);
    },

    /** Store tokens after login */
    setTokens(tokens: TokenResponse): void {
        if (typeof window === 'undefined') return;
        localStorage.setItem(TOKEN_KEYS.ACCESS, tokens.access_token);
        localStorage.setItem(TOKEN_KEYS.REFRESH, tokens.refresh_token);
    },

    /** Clear all tokens (logout) */
    clearTokens(): void {
        if (typeof window === 'undefined') return;
        localStorage.removeItem(TOKEN_KEYS.ACCESS);
        localStorage.removeItem(TOKEN_KEYS.REFRESH);
    },

    /** Check if user is authenticated */
    isAuthenticated(): boolean {
        return !!this.getAccessToken();
    },
};

// ============================================================================
// API Client Factory
// ============================================================================

/**
 * Create configured Axios instance with interceptors.
 */
function createApiClient(): AxiosInstance {
    const client = axios.create({
        baseURL: API_BASE_URL,
        timeout: REQUEST_TIMEOUT,
        headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        },
    });

    // -------------------------------------------------------------------------
    // Request Interceptor: Add Authorization Header
    // -------------------------------------------------------------------------
    client.interceptors.request.use(
        (config: InternalAxiosRequestConfig) => {
            const token = tokenStorage.getAccessToken();

            if (token && config.headers) {
                config.headers.Authorization = `Bearer ${token}`;
            }

            return config;
        },
        (error: AxiosError) => {
            console.error('[API Client] Request error:', error.message);
            return Promise.reject(error);
        }
    );

    // -------------------------------------------------------------------------
    // Response Interceptor: Handle Errors and Token Refresh
    // -------------------------------------------------------------------------
    client.interceptors.response.use(
        (response: AxiosResponse) => response,
        async (error: AxiosError<ApiError>) => {
            const originalRequest = error.config as InternalAxiosRequestConfig & { _retry?: boolean };

            // Handle 401 Unauthorized
            if (error.response?.status === 401 && !originalRequest._retry) {
                originalRequest._retry = true;

                const refreshToken = tokenStorage.getRefreshToken();

                if (refreshToken) {
                    try {
                        // Attempt token refresh
                        const response = await axios.post<TokenResponse>(
                            `${API_BASE_URL}/api/auth/refresh`,
                            { refresh_token: refreshToken }
                        );

                        tokenStorage.setTokens(response.data);

                        // Retry original request with new token
                        if (originalRequest.headers) {
                            originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`;
                        }

                        return client(originalRequest);
                    } catch (refreshError) {
                        // Refresh failed, force logout
                        console.warn('[API Client] Token refresh failed, logging out');
                        handleLogout();
                        return Promise.reject(refreshError);
                    }
                } else {
                    // No refresh token, redirect to login
                    handleLogout();
                }
            }

            // Transform error to standard format
            const apiError = transformError(error);
            return Promise.reject(apiError);
        }
    );

    return client;
}

// ============================================================================
// Error Handling
// ============================================================================

/**
 * Transform Axios error to standardized HttpError.
 */
function transformError(error: AxiosError<ApiError>): HttpError {
    const status = error.response?.status || 500;
    const statusText = error.response?.statusText || 'Unknown Error';

    let message = 'An unexpected error occurred';
    let detail: string | undefined;
    const data = error.response?.data;

    if (data) {
        message = data.message || data.detail || message; // @ts-ignore - detail can be array or string
        detail = typeof data.detail === 'string' ? data.detail : undefined;
    } else if (error.message) {
        message = error.message;
    }

    // Handle specific error codes
    switch (status) {
        case 400:
            message = message || 'Invalid request';
            break;
        case 401:
            message = 'Authentication required';
            break;
        case 403:
            message = 'Access denied';
            break;
        case 404:
            message = 'Resource not found';
            break;
        case 422:
            message = 'Validation error';
            if (Array.isArray(data?.detail)) {
                // Extract first validation error
                const firstError = data.detail[0];
                if (firstError?.msg) {
                    message = `Validation: ${firstError.msg} (${firstError.loc?.join('.')})`;
                }
            } else if (typeof data?.detail === 'string') {
                message = data.detail;
            }
            break;
        case 429:
            message = 'Too many requests';
            break;
        case 500:
            message = message === 'An unexpected error occurred' ? 'Server error' : message;
            break;
        case 502:
        case 503:
        case 504:
            message = 'Service temporarily unavailable';
            break;
    }

    const httpError = new Error(message) as HttpError;
    httpError.status = status;
    httpError.statusText = statusText;
    httpError.data = {
        status,
        message,
        detail,
        errors: error.response?.data?.errors,
    };

    return httpError;
}

/**
 * Handle logout and redirect to login page.
 */
function handleLogout(): void {
    tokenStorage.clearTokens();

    if (typeof window !== 'undefined') {
        // Redirect to login page
        window.location.href = '/login';
    }
}

// ============================================================================
// Singleton Export
// ============================================================================

/** Configured API client instance */
export const apiClient = createApiClient();

/** Export base URL for direct use */
export { API_BASE_URL };

// ============================================================================
// Helper Types
// ============================================================================

/** Request config without data */
export type RequestConfig = Omit<AxiosRequestConfig, 'url' | 'method' | 'data'>;

/** API response wrapper type */
export type ApiResponse<T> = Promise<T>;
