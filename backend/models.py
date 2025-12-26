"""
Pydantic Models for QorSense Sensor Analysis.

This module defines data models for sensor configuration, analysis input/output,
and sensor-type-specific threshold configurations for industrial process monitoring.
"""
from datetime import datetime
from enum import Enum
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field, field_validator, model_validator

# =============================================================================
# SENSOR CATALOG
# =============================================================================

SENSOR_CATALOG = {
    "Process Analytics": {
        "pH Sensor": ["pH", "mV"],
        "Conductivity": ["µS/cm", "mS/cm"],
        "Dissolved Oxygen (DO)": ["mg/L", "ppm", "% Saturation"],
        "Turbidity": ["NTU", "FNU"],
        "ORP (Redox)": ["mV"]
    },
    "Physical Measurement": {
        "Flow": ["L/min", "m3/h", "m/s"],
        "Pressure": ["bar", "psi", "Pa"],
        "Temperature": ["°C", "°F", "K"],
        "Level": ["mm", "cm", "%"]
    }
}


# =============================================================================
# ERROR CODES
# =============================================================================

class AnalysisErrorCode(str, Enum):
    """Error codes for analysis operations."""
    SUCCESS = "SUCCESS"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    CONSTANT_SIGNAL = "CONSTANT_SIGNAL"
    NAN_VALUES = "NAN_VALUES"
    INF_VALUES = "INF_VALUES"
    INVALID_CONFIG = "INVALID_CONFIG"
    COMPUTATION_ERROR = "COMPUTATION_ERROR"


# =============================================================================
# SENSOR LIMIT CONFIGURATION
# =============================================================================

class SensorLimitConfig(BaseModel):
    """
    Sensor-type-specific thresholds for health scoring.
    
    All thresholds are configurable per sensor type to support
    different process requirements (pH control is tighter than temperature, etc.)
    
    Attributes:
        sensor_type: Type of sensor for identification
        slope_warning/critical: Drift rate thresholds (units/sample)
        bias_warning/critical: Offset from reference thresholds
        noise_warning/critical: Standard deviation of residuals thresholds
        snr_warning/critical: Signal-to-noise ratio thresholds (dB)
        hurst_upper_critical: Upper threshold for Hurst exponent (persistence)
        hurst_lower_warning: Lower threshold for Hurst exponent (anti-persistence)
        hysteresis_critical: Hysteresis score threshold
        
    Example:
        >>> config = SensorLimitConfig(
        ...     sensor_type="pH",
        ...     slope_warning=0.02, slope_critical=0.05,
        ...     bias_warning=0.3, bias_critical=0.5,
        ...     noise_warning=0.1, noise_critical=0.2
        ... )
    """
    # Sensor identification
    sensor_type: Literal["pH", "DO", "Pressure", "Temperature", "Flow", "Conductivity", "Generic"] = "Generic"

    # Slope thresholds (drift detection) - units per sample
    slope_warning: float = Field(default=0.05, ge=0, description="Warning threshold for drift rate")
    slope_critical: float = Field(default=0.1, ge=0, description="Critical threshold for drift rate")

    # Bias thresholds (offset from reference)
    bias_warning: float = Field(default=1.0, ge=0, description="Warning threshold for bias")
    bias_critical: float = Field(default=2.0, ge=0, description="Critical threshold for bias")

    # Noise thresholds (standard deviation of residuals)
    noise_warning: float = Field(default=1.0, ge=0, description="Warning threshold for noise std")
    noise_critical: float = Field(default=2.0, ge=0, description="Critical threshold for noise std")

    # SNR thresholds (dB)
    snr_warning: float = Field(default=20.0, description="Warning threshold for SNR (dB)")
    snr_critical: float = Field(default=10.0, description="Critical threshold for SNR (dB)")

    # DFA/Hurst thresholds
    hurst_upper_critical: float = Field(default=0.8, ge=0.5, le=1.0, description="Upper threshold for Hurst (persistence)")
    hurst_lower_warning: float = Field(default=0.2, ge=0, le=0.5, description="Lower threshold for Hurst (anti-persistence)")

    # Hysteresis threshold
    hysteresis_critical: float = Field(default=0.5, ge=0, description="Critical threshold for hysteresis score")

    # Data requirements
    min_data_points: int = Field(default=50, ge=10, description="Minimum data points required")

    # Scoring weights (optional tuning)
    weight_slope: float = Field(default=1.0, ge=0, description="Weight for slope penalty")
    weight_bias: float = Field(default=1.0, ge=0, description="Weight for bias penalty")
    weight_noise: float = Field(default=1.0, ge=0, description="Weight for noise penalty")
    weight_hurst: float = Field(default=1.0, ge=0, description="Weight for Hurst penalty")

    @model_validator(mode="after")
    def validate_thresholds(self) -> "SensorLimitConfig":
        """Ensure warning thresholds are less than critical thresholds."""
        if self.slope_warning > self.slope_critical:
            self.slope_warning = self.slope_critical * 0.5
        if self.bias_warning > self.bias_critical:
            self.bias_warning = self.bias_critical * 0.5
        if self.noise_warning > self.noise_critical:
            self.noise_warning = self.noise_critical * 0.5
        if self.snr_warning < self.snr_critical:
            self.snr_warning = self.snr_critical * 2.0
        return self


# =============================================================================
# PREDEFINED SENSOR LIMIT PRESETS
# =============================================================================

SENSOR_LIMIT_PRESETS: dict[str, SensorLimitConfig] = {
    "pH": SensorLimitConfig(
        sensor_type="pH",
        slope_warning=0.02,
        slope_critical=0.05,
        bias_warning=0.3,
        bias_critical=0.5,
        noise_warning=0.05,
        noise_critical=0.1,
        snr_warning=25.0,
        snr_critical=15.0,
        hurst_upper_critical=0.75,
        hysteresis_critical=0.3,
        min_data_points=100
    ),
    "DO": SensorLimitConfig(
        sensor_type="DO",
        slope_warning=0.5,
        slope_critical=1.0,
        bias_warning=0.5,
        bias_critical=1.0,
        noise_warning=0.2,
        noise_critical=0.5,
        snr_warning=20.0,
        snr_critical=10.0,
        hurst_upper_critical=0.8,
        hysteresis_critical=0.4,
        min_data_points=50
    ),
    "Pressure": SensorLimitConfig(
        sensor_type="Pressure",
        slope_warning=0.1,
        slope_critical=0.3,
        bias_warning=1.0,
        bias_critical=3.0,
        noise_warning=0.5,
        noise_critical=1.5,
        snr_warning=18.0,
        snr_critical=8.0,
        hurst_upper_critical=0.85,
        hysteresis_critical=0.5,
        min_data_points=30
    ),
    "Temperature": SensorLimitConfig(
        sensor_type="Temperature",
        slope_warning=0.1,
        slope_critical=0.5,
        bias_warning=1.0,
        bias_critical=2.0,
        noise_warning=0.3,
        noise_critical=1.0,
        snr_warning=20.0,
        snr_critical=10.0,
        hurst_upper_critical=0.8,
        hysteresis_critical=0.4,
        min_data_points=50
    ),
    "Flow": SensorLimitConfig(
        sensor_type="Flow",
        slope_warning=0.5,
        slope_critical=2.0,
        bias_warning=2.0,
        bias_critical=5.0,
        noise_warning=1.0,
        noise_critical=3.0,
        snr_warning=15.0,
        snr_critical=8.0,
        hurst_upper_critical=0.85,
        hysteresis_critical=0.6,
        min_data_points=30
    ),
    "Conductivity": SensorLimitConfig(
        sensor_type="Conductivity",
        slope_warning=0.1,
        slope_critical=0.3,
        bias_warning=5.0,
        bias_critical=15.0,
        noise_warning=2.0,
        noise_critical=5.0,
        snr_warning=18.0,
        snr_critical=10.0,
        hurst_upper_critical=0.8,
        hysteresis_critical=0.4,
        min_data_points=50
    ),
    "Generic": SensorLimitConfig(
        sensor_type="Generic",
        slope_warning=0.05,
        slope_critical=0.1,
        bias_warning=1.0,
        bias_critical=2.0,
        noise_warning=1.0,
        noise_critical=2.0,
        snr_warning=20.0,
        snr_critical=10.0,
        hurst_upper_critical=0.8,
        hurst_lower_warning=0.2,
        hysteresis_critical=0.5,
        min_data_points=50
    )
}


def get_sensor_limits(sensor_type: str) -> SensorLimitConfig:
    """
    Get predefined limits for a sensor type.
    
    Args:
        sensor_type: Sensor type name (pH, DO, Pressure, etc.)
        
    Returns:
        SensorLimitConfig for the sensor type, or Generic if not found
    """
    # Normalize sensor type name
    normalized = sensor_type.strip().replace(" ", "").lower()

    for key, config in SENSOR_LIMIT_PRESETS.items():
        if key.lower() == normalized:
            return config

    # Check for partial matches
    if "ph" in normalized:
        return SENSOR_LIMIT_PRESETS["pH"]
    if "oxygen" in normalized or "do" in normalized:
        return SENSOR_LIMIT_PRESETS["DO"]
    if "press" in normalized:
        return SENSOR_LIMIT_PRESETS["Pressure"]
    if "temp" in normalized:
        return SENSOR_LIMIT_PRESETS["Temperature"]
    if "flow" in normalized:
        return SENSOR_LIMIT_PRESETS["Flow"]
    if "conduct" in normalized:
        return SENSOR_LIMIT_PRESETS["Conductivity"]

    return SENSOR_LIMIT_PRESETS["Generic"]


# =============================================================================
# LEGACY SENSOR CONFIG (kept for backward compatibility)
# =============================================================================

class SensorConfig(BaseModel):
    """
    Legacy sensor configuration (deprecated, use SensorLimitConfig).
    
    Kept for backward compatibility with existing code.
    """
    slope_critical: float = 0.1
    slope_warning: float = 0.05
    bias_critical: float = 2.0
    bias_warning: float = 1.0
    noise_critical: float = 1.5
    hysteresis_critical: float = 0.5
    dfa_critical: float = 0.8
    min_data_points: int = 50

    def to_limit_config(self, sensor_type: str = "Generic") -> SensorLimitConfig:
        """Convert to new SensorLimitConfig format."""
        return SensorLimitConfig(
            sensor_type=sensor_type,  # type: ignore
            slope_warning=self.slope_warning,
            slope_critical=self.slope_critical,
            bias_warning=self.bias_warning,
            bias_critical=self.bias_critical,
            noise_warning=self.noise_critical * 0.5,
            noise_critical=self.noise_critical,
            hurst_upper_critical=self.dfa_critical,
            hysteresis_critical=self.hysteresis_critical,
            min_data_points=self.min_data_points
        )


# =============================================================================
# ANALYSIS INPUT/OUTPUT MODELS
# =============================================================================

class AnalysisInput(BaseModel):
    """
    Validated input for sensor analysis.
    
    Performs input validation to catch NaN, Inf, and constant signals
    before analysis starts.
    
    Attributes:
        data: List of sensor values
        sensor_type: Type of sensor (for threshold selection)
        reference_value: Optional calibration reference point
        config: Optional custom limit configuration
        
    Example:
        >>> input_data = AnalysisInput(
        ...     data=[1.0, 1.1, 1.2, 1.15, 1.3, ...],
        ...     sensor_type="pH",
        ...     reference_value=7.0
        ... )
    """
    data: list[float] = Field(..., min_length=10, description="Sensor data values")
    sensor_type: str = Field(default="Generic", description="Sensor type for threshold selection")
    reference_value: float | None = Field(default=None, description="Calibration reference point")
    config: SensorLimitConfig | None = Field(default=None, description="Custom limit configuration")

    @field_validator("data")
    @classmethod
    def validate_data(cls, v: list[float]) -> list[float]:
        """Validate data for NaN, Inf, and constant values."""
        if not v:
            raise ValueError("Data cannot be empty")

        arr = np.array(v, dtype=np.float64)

        # Check for NaN
        nan_count = np.sum(np.isnan(arr))
        if nan_count > 0:
            raise ValueError(f"Data contains {nan_count} NaN values")

        # Check for Inf
        inf_count = np.sum(np.isinf(arr))
        if inf_count > 0:
            raise ValueError(f"Data contains {inf_count} Inf values")

        # Check for constant signal (flat line)
        if np.std(arr) < 1e-10:
            raise ValueError("Constant/flat-line signal detected (zero variance)")

        return v

    def get_effective_config(self) -> SensorLimitConfig:
        """Get the effective configuration (custom or preset)."""
        if self.config is not None:
            return self.config
        return get_sensor_limits(self.sensor_type)


# =============================================================================
# RESULT MODELS
# =============================================================================

class BiasResult(BaseModel):
    """Result of bias calculation."""
    absolute: float = Field(..., description="Absolute bias value")
    relative: float = Field(..., description="Relative bias as percentage")
    reference: float = Field(..., description="Reference value used")


class DFAResult(BaseModel):
    """Result of DFA calculation."""
    hurst: float = Field(..., description="Hurst exponent (slope of log-log plot)")
    r_squared: float = Field(..., description="R² of the linear fit")
    scales: list[float] = Field(default_factory=list, description="Scales used")
    fluctuations: list[float] = Field(default_factory=list, description="Fluctuations at each scale")


class HysteresisResult(BaseModel):
    """Result of hysteresis calculation."""
    score: float = Field(..., description="Hysteresis score (0-1)")
    rising_values: list[float] = Field(default_factory=list, description="Values during rising edges")
    falling_values: list[float] = Field(default_factory=list, description="Values during falling edges")


class HealthResult(BaseModel):
    """Health score calculation result."""
    score: float = Field(..., ge=0, le=100, description="Health score (0-100)")
    status: Literal["Green", "Yellow", "Red"] = Field(..., description="Status color")
    diagnosis: str = Field(..., description="Diagnosis summary")
    flags: list[str] = Field(default_factory=list, description="Active flags")
    recommendation: str = Field(..., description="Recommended action")
    penalties: dict[str, float] = Field(default_factory=dict, description="Penalty breakdown")


# =============================================================================
# API MODELS (existing, kept for compatibility)
# =============================================================================

class SensorCreate(BaseModel):
    name: str
    location: str
    source_type: str = "CSV"
    organization_id: str | None = None
    sensor_type: str
    unit: str


class SensorResponse(BaseModel):
    id: str
    name: str
    location: str
    source_type: str
    organization_id: str | None = None
    latest_health_score: float | None = 100.0
    latest_status: str | None = "Normal"
    latest_analysis_timestamp: datetime | None = None

    class Config:
        from_attributes = True


class SensorDataInput(BaseModel):
    sensor_id: str
    sensor_type: str = "Generic"
    values: list[float] = []
    timestamps: list[str] | None = None
    config: SensorConfig | None = SensorConfig()


class AnalysisMetrics(BaseModel):
    bias: float
    slope: float
    snr_db: float
    hysteresis: float
    noise_std: float | None = 0.0
    hysteresis_x: list[float] = []
    hysteresis_y: list[float] = []
    hurst: float | None = 0.5
    hurst_r2: float | None = 0.0
    dfa_alpha: float | None = None
    dfa_r_squared: float | None = None
    dfa_scales: list[float] = []
    dfa_fluctuations: list[float] = []
    timestamps: list[str] | None = None
    trend: list[float] | None = None
    residuals: list[float] | None = None
    # New fields for enhanced analysis
    bias_result: BiasResult | None = None
    error_code: str | None = None


class AnalysisResult(BaseModel):
    sensor_id: str
    timestamp: str
    health_score: float
    status: str
    metrics: AnalysisMetrics
    flags: list[str]
    recommendation: str
    diagnosis: str
    prediction: str | None = None


class SyntheticRequest(BaseModel):
    type: str
    length: int = 100


class ReportRequest(BaseModel):
    sensor_id: str
    health_score: float
    metrics: AnalysisMetrics
    diagnosis: str
    status: str | None = "Unknown"
    flags: list[str] = []
    recommendation: str = ""
    data: list[float] | None = None
