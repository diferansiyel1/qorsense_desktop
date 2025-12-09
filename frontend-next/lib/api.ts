/**
 * QorSense API Service
 * 
 * Type-safe API methods using the configured axios client.
 * All methods are fully typed with request/response interfaces.
 * 
 * @module lib/api
 */

'use client';

import { apiClient, tokenStorage, API_BASE_URL } from './api-client';
import type {
    // Auth
    User,
    LoginRequest,
    TokenResponse,
    RegisterRequest,
    UpdateProfileRequest,
    // Sensor
    Sensor,
    CreateSensorRequest,
    SensorHistory,
    // Analysis
    AnalysisResult,
    AnalysisRequest,
    AsyncAnalysisRequest,
    AsyncAnalysisResponse,
    // Task
    TaskStatusResponse,
    // Common
    PaginatedResponse,
    CSVImportResult,
    SyntheticDataRequest,
    SyntheticDataResponse,
    HealthResponse,
} from '@/types/api';

// ============================================================================
// Authentication API
// ============================================================================

export const authApi = {
    /**
     * Login with email and password.
     * Stores tokens automatically on success.
     */
    async login(credentials: LoginRequest): Promise<TokenResponse> {
        // Use JSON endpoint for email-based login
        const response = await apiClient.post<TokenResponse>('/api/auth/login', {
            email: credentials.email,
            password: credentials.password,
        });

        // Store tokens
        tokenStorage.setTokens(response.data);

        return response.data;
    },

    /**
     * Register a new user.
     */
    async register(data: RegisterRequest): Promise<User> {
        const response = await apiClient.post<User>('/api/auth/register', data);
        return response.data;
    },

    /**
     * Refresh access token.
     */
    async refreshToken(refreshToken: string): Promise<TokenResponse> {
        const response = await apiClient.post<TokenResponse>('/api/auth/refresh', {
            refresh_token: refreshToken,
        });

        tokenStorage.setTokens(response.data);
        return response.data;
    },

    /**
     * Get current user profile.
     */
    async getMe(): Promise<User> {
        const response = await apiClient.get<User>('/api/auth/me');
        return response.data;
    },


    /**
     * Update current user profile.
     */
    async updateProfile(data: UpdateProfileRequest): Promise<User> {
        const response = await apiClient.put<User>('/api/auth/me', data);
        return response.data;
    },

    /**
     * Change password.
     */
    async changePassword(data: UpdateProfileRequest): Promise<void> {
        await apiClient.post('/api/auth/change-password', data);
    },

    /**
     * Logout (clear tokens).
     */
    logout(): void {
        tokenStorage.clearTokens();
        // Optional: Call backend logout endpoint
        apiClient.post('/auth/logout').catch(() => {
            // Ignore errors on logout
        });
    },

    /**
     * Check if user is currently authenticated.
     */
    isAuthenticated(): boolean {
        return tokenStorage.isAuthenticated();
    },
};

// ============================================================================
// Sensors API
// ============================================================================

export const sensorsApi = {
    /**
     * Get all sensors with pagination.
     */
    async getAll(page = 1, size = 20): Promise<Sensor[]> {
        const response = await apiClient.get<PaginatedResponse<Sensor>>('/sensors', {
            params: { page, size },
        });
        return response.data.items;
    },

    /**
     * Get paginated sensors response.
     */
    async getPaginated(page = 1, size = 20): Promise<PaginatedResponse<Sensor>> {
        const response = await apiClient.get<PaginatedResponse<Sensor>>('/sensors', {
            params: { page, size },
        });
        return response.data;
    },

    /**
     * Get a single sensor by ID.
     */
    async getById(id: string): Promise<Sensor> {
        const response = await apiClient.get<Sensor>(`/sensors/${id}`);
        return response.data;
    },

    /**
     * Delete a sensor by ID.
     */
    async delete(id: string): Promise<void> {
        await apiClient.delete(`/sensors/${id}`);
    },

    /**
     * Create a new sensor.
     */
    async create(data: CreateSensorRequest): Promise<Sensor> {
        const response = await apiClient.post<Sensor>('/sensors', data);
        return response.data;
    },

    /**
     * Get sensor reading history.
     */
    async getHistory(sensorId: string, limit = 1000): Promise<SensorHistory> {
        const response = await apiClient.get<SensorHistory>(`/sensors/${sensorId}/history`, {
            params: { limit },
        });
        return response.data;
    },

    /**
     * Upload CSV readings for a sensor.
     * Uses axios for consistent error handling and token management.
     */
    async uploadCsv(sensorId: string, file: File): Promise<CSVImportResult> {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('sensor_id', sensorId);

        console.log('[uploadCsv] Starting upload via Axios:', {
            sensorId,
            fileName: file.name,
            fileSize: file.size
        });

        // Axios automatically sets the Content-Type to multipart/form-data
        // and handles the Authorization header via interceptors
        // We must explicitly unset Content-Type so the browser sets the boundary
        const response = await apiClient.post<CSVImportResult>(
            '/sensors/upload-csv',
            formData,
            {
                headers: {
                    'Content-Type': undefined
                }
            }
        );

        return response.data;
    },
};

// ============================================================================
// Analysis API
// ============================================================================

export const analysisApi = {
    /**
     * Run synchronous analysis on a sensor.
     */
    async analyze(request: AnalysisRequest): Promise<AnalysisResult> {
        const response = await apiClient.post<AnalysisResult>('/analyze', {
            sensor_id: request.sensor_id,
            sensor_type: request.sensor_type || 'Generic',
            values: request.values || [],
            config: request.config,
        });
        return response.data;
    },

    /**
     * Submit async analysis task.
     */
    async analyzeAsync(request: AsyncAnalysisRequest): Promise<AsyncAnalysisResponse> {
        const response = await apiClient.post<AsyncAnalysisResponse>('/analyze/async', request);
        return response.data;
    },
};

// ============================================================================
// Tasks API
// ============================================================================

export const tasksApi = {
    /**
     * Get task status by ID.
     */
    async getStatus(taskId: string): Promise<TaskStatusResponse> {
        const response = await apiClient.get<TaskStatusResponse>(`/tasks/${taskId}`);
        return response.data;
    },

    /**
     * Revoke a pending task.
     */
    async revoke(taskId: string, terminate = false): Promise<void> {
        await apiClient.delete(`/tasks/${taskId}`, {
            params: { terminate },
        });
    },

    /**
     * Poll task until completion.
     * Returns result or throws on failure.
     */
    async pollUntilComplete(
        taskId: string,
        options: { intervalMs?: number; maxAttempts?: number } = {}
    ): Promise<AnalysisResult> {
        const { intervalMs = 1000, maxAttempts = 60 } = options;

        for (let attempt = 0; attempt < maxAttempts; attempt++) {
            const status = await this.getStatus(taskId);

            if (status.status === 'SUCCESS' && status.result) {
                return status.result;
            }

            if (status.status === 'FAILURE') {
                throw new Error(status.error || 'Task failed');
            }

            if (['PENDING', 'STARTED', 'PROGRESS', 'RETRY'].includes(status.status)) {
                await new Promise((resolve) => setTimeout(resolve, intervalMs));
                continue;
            }

            throw new Error(`Unexpected task status: ${status.status}`);
        }

        throw new Error('Task polling timeout');
    },
};

// ============================================================================
// Reports API
// ============================================================================

export const reportsApi = {
    /**
     * Generate PDF report.
     * Returns blob for download.
     */
    async generatePdf(result: AnalysisResult, rawData: number[]): Promise<Blob> {
        const response = await apiClient.post(
            '/reports/generate',
            {
                sensor_id: result.sensor_id,
                health_score: result.health_score,
                diagnosis: result.diagnosis,
                metrics: result.metrics,
                flags: result.flags,
                recommendation: result.recommendation,
                data: rawData,
            },
            { responseType: 'blob' }
        );
        return response.data;
    },

    /**
     * Download PDF report with auto-save.
     */
    async downloadPdf(result: AnalysisResult, rawData: number[]): Promise<void> {
        const blob = await this.generatePdf(result, rawData);

        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = `report_${result.sensor_id}_${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
    },
};

// ============================================================================
// Synthetic Data API
// ============================================================================

export const syntheticApi = {
    /**
     * Generate synthetic sensor data.
     */
    async generate(request: SyntheticDataRequest = {}): Promise<number[]> {
        const response = await apiClient.post<SyntheticDataResponse>('/synthetic/generate', {
            n_points: request.n_points || 1000,
            pattern_type: request.pattern_type || 'stable',
            noise_level: request.noise_level || 0.1,
            trend_strength: request.trend_strength || 0.0,
            seed: request.seed,
        });
        return response.data.data;
    },
};

// ============================================================================
// Health API
// ============================================================================

export const healthApi = {
    /**
     * Check API health status.
     */
    async check(): Promise<HealthResponse> {
        const response = await apiClient.get<HealthResponse>('/health');
        return response.data;
    },

    /**
     * Simple ping check.
     */
    async ping(): Promise<boolean> {
        try {
            await apiClient.get('/');
            return true;
        } catch {
            return false;
        }
    },
};

// ============================================================================
// Unified API Export
// ============================================================================

/**
 * Unified API object for convenient access to all endpoints.
 * Includes legacy method aliases for backward compatibility.
 */
export const api = {
    auth: authApi,
    sensors: sensorsApi,
    analysis: analysisApi,
    tasks: tasksApi,
    reports: reportsApi,
    synthetic: syntheticApi,
    health: healthApi,

    // =========================================================================
    // Legacy Methods (for backward compatibility with existing components)
    // =========================================================================

    /** @deprecated Use api.health.ping() */
    healthCheck: async () => healthApi.ping(),

    /** @deprecated Use api.sensors.getAll() */
    getSensors: async () => sensorsApi.getAll(),

    /** @deprecated Use api.sensors.create() */
    createSensor: async (data: CreateSensorRequest) => sensorsApi.create(data),

    /** @deprecated Use api.sensors.uploadCsv() */
    uploadReadings: async (sensorId: string, formData: FormData) => {
        const file = formData.get('file') as File;
        return sensorsApi.uploadCsv(sensorId, file);
    },

    /** @deprecated Use api.analysis.analyze() */
    analyzeSensor: async (sensorId: string, config?: { start_date?: string; end_date?: string }) => {
        return analysisApi.analyze({
            sensor_id: sensorId,
            sensor_type: 'Bio',
            values: [],
            config,
        });
    },

    /** @deprecated Use api.sensors.getHistory() */
    getSensorHistory: async (sensorId: string) => sensorsApi.getHistory(sensorId),

    /** @deprecated Use api.synthetic.generate() */
    generateSynthetic: async (req: SyntheticDataRequest) => syntheticApi.generate(req),

    /** @deprecated Use api.reports.generatePdf() */
    generateReport: async (result: AnalysisResult, rawData: number[]) => {
        return reportsApi.generatePdf(result, rawData);
    },
};

// Re-export client and storage for advanced use cases
export { apiClient, tokenStorage, API_BASE_URL };

// ============================================================================
// Type Re-exports for Backward Compatibility
// ============================================================================

// Re-export Sensor type for components importing from @/lib/api
export type { Sensor, CreateSensorRequest as CreateSensorData } from '@/types/api';

// Default export
export default api;
