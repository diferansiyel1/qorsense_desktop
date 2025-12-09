/**
 * QorSense API Type Definitions
 * 
 * TypeScript interfaces for all API request/response types.
 * Generated from backend OpenAPI schema.
 * 
 * @module types/api
 */

// ============================================================================
// Enumerations
// ============================================================================

/** Sensor data source type */
export type SourceType = 'CSV' | 'SCADA' | 'IoT' | 'API' | 'MANUAL';

/** Sensor operational status */
export type SensorStatus = 'Normal' | 'Warning' | 'Critical' | 'Unknown' | 'No Data';

/** User role enumeration */
export type UserRole = 'super_admin' | 'org_admin' | 'engineer';

/** Celery task status */
export type TaskStatus =
    | 'PENDING'
    | 'STARTED'
    | 'PROGRESS'
    | 'SUCCESS'
    | 'FAILURE'
    | 'RETRY'
    | 'REVOKED';

// ============================================================================
// Authentication Types
// ============================================================================

/** Login request payload */
export interface LoginRequest {
    email: string;
    password: string;
}

/** Login response with tokens */
export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: 'bearer';
    expires_in: number;
}

/** Refresh token request */
export interface RefreshTokenRequest {
    refresh_token: string;
}

/** User registration request */
export interface RegisterRequest {
    username: string;
    email: string;
    password: string;
    full_name?: string;
}

/** Current user profile */
export interface User {
    id: string;
    email: string;
    full_name: string | null;
    role: UserRole;
    is_active: boolean;
    organization_id: string | null;
    created_at: string;
    last_login: string | null;
}

/** User profile update request */
export interface UpdateProfileRequest {
    email?: string;
    full_name?: string;
    current_password?: string;
    new_password?: string;
}

// ============================================================================
// Sensor Types
// ============================================================================

/** Sensor entity */
export interface Sensor {
    id: string;
    name: string;
    location: string;
    source_type: SourceType;
    organization_id: string | null;
    latest_health_score: number;
    latest_status: SensorStatus;
    latest_analysis_timestamp: string | null;
}

/** Create sensor request */
export interface CreateSensorRequest {
    name: string;
    location: string;
    source_type: SourceType;
    organization_id?: string;
    config?: Record<string, unknown>;
}

/** Sensor reading data point */
export interface SensorReading {
    sensor_id: string;
    timestamp: string;
    value: number;
}

/** Sensor history response */
export interface SensorHistory {
    sensor_id: string;
    readings: SensorReading[];
    total_count: number;
}

// ============================================================================
// Analysis Types
// ============================================================================

/** Analysis metrics */
export interface AnalysisMetrics {
    bias: number;
    slope: number;
    snr_db: number;
    hysteresis: number;
    dfa_alpha: number;
    dfa_r_squared: number;
    timestamps?: string[];
    trend?: number[];
    residuals?: number[];
    // Legacy fields for backward compatibility
    noise_std?: number;
    hurst?: number;
    hysteresis_x?: number[];
    hysteresis_y?: number[];
}

/** Remaining useful life prediction */
export interface RulPrediction {
    rul_hours: number | null;
    rul_days: number | null;
    confidence: number;
    method: string;
}

/** Full analysis result */
export interface AnalysisResult {
    sensor_id: string;
    timestamp: string;
    health_score: number;
    status: SensorStatus;
    diagnosis: string;
    metrics: AnalysisMetrics;
    flags: string[];
    recommendation: string;
    prediction: RulPrediction;
}

/** Analysis request */
export interface AnalysisRequest {
    sensor_id: string;
    sensor_type?: string;
    values?: number[];
    config?: AnalysisConfig;
}

/** Analysis configuration */
export interface AnalysisConfig {
    start_date?: string;
    end_date?: string;
    limit?: number;
    include_trend?: boolean;
}

/** Async analysis request */
export interface AsyncAnalysisRequest {
    sensor_id: string;
    sensor_type?: string;
    values?: number[];
    config?: AnalysisConfig;
    use_async?: boolean;
}

/** Async analysis response */
export interface AsyncAnalysisResponse {
    task_id: string;
    status: string;
    message: string;
    async_mode: boolean;
    poll_url: string;
}

// ============================================================================
// Task Types
// ============================================================================

/** Task status response */
export interface TaskStatusResponse {
    task_id: string;
    status: TaskStatus;
    ready: boolean;
    result: AnalysisResult | null;
    error: string | null;
    progress: number | null;
    message: string | null;
    info: Record<string, unknown> | null;
}

// ============================================================================
// CSV Import Types
// ============================================================================

/** CSV import result */
export interface CSVImportResult {
    success: boolean;
    sensor_id: string;
    total_rows: number;
    imported_rows: number;
    failed_rows: number;
    skipped_rows: number;
    error_samples: string[];
    import_duration_ms: number;
    chunks_processed: number;
}

// ============================================================================
// Report Types
// ============================================================================

/** Report generation request */
export interface ReportRequest {
    sensor_id: string;
    health_score: number;
    diagnosis: string;
    metrics: AnalysisMetrics;
    flags: string[];
    recommendation: string;
    data?: number[];
}

// ============================================================================
// Pagination Types
// ============================================================================

/** Paginated response wrapper */
export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    pages: number;
}

/** Pagination parameters */
export interface PaginationParams {
    page?: number;
    size?: number;
}

// ============================================================================
// API Error Types
// ============================================================================

/** Standard API error response */
export interface ApiError {
    status: number;
    message: string;
    detail?: string;
    errors?: ValidationError[];
}

/** Validation error detail */
export interface ValidationError {
    loc: (string | number)[];
    msg: string;
    type: string;
}

/** HTTP error with additional context */
export interface HttpError extends Error {
    status: number;
    statusText: string;
    data: ApiError;
}

// ============================================================================
// Synthetic Data Types
// ============================================================================

/** Synthetic data generation request */
export interface SyntheticDataRequest {
    n_points?: number;
    pattern_type?: 'stable' | 'drift' | 'degradation' | 'oscillation' | 'step_change';
    noise_level?: number;
    trend_strength?: number;
    seed?: number;
}

/** Synthetic data response */
export interface SyntheticDataResponse {
    data: number[];
    pattern_type: string;
    parameters: Record<string, number>;
}

// ============================================================================
// Health Check Types
// ============================================================================

/** Health check response */
export interface HealthResponse {
    status: 'healthy' | 'degraded' | 'unhealthy';
    version: string;
    environment: string;
    database: boolean;
    redis?: boolean;
    uptime_seconds?: number;
}

// ============================================================================
// Type Guards
// ============================================================================

/** Type guard for API errors */
export function isApiError(error: unknown): error is ApiError {
    return (
        typeof error === 'object' &&
        error !== null &&
        'status' in error &&
        'message' in error
    );
}

/** Type guard for HTTP errors */
export function isHttpError(error: unknown): error is HttpError {
    return (
        error instanceof Error &&
        'status' in error &&
        'data' in error
    );
}

/** Type guard for validation errors */
export function hasValidationErrors(error: ApiError): error is ApiError & { errors: ValidationError[] } {
    return Array.isArray(error.errors) && error.errors.length > 0;
}
