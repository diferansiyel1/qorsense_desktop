from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

# Standardized Sensor Catalog: Category -> Sensor Type -> Units
SENSOR_CATALOG = {
    "Proses Analitik": {
        "pH Sensörü": ["pH", "mV"],
        "İletkenlik": ["µS/cm", "mS/cm"],
        "Çözünmüş Oksijen (DO)": ["mg/L", "ppm", "% Saturation"],
        "Bulanıklık": ["NTU", "FNU"],
        "ORP (Redox)": ["mV"]
    },
    "Fiziksel Ölçüm": {
        "Akış (Flow)": ["L/min", "m3/h", "m/s"],
        "Basınç": ["bar", "psi", "Pa"],
        "Sıcaklık": ["°C", "°F", "K"],
        "Seviye": ["mm", "cm", "%"]
    }
}

class SensorConfig(BaseModel):
    slope_critical: float = 0.1
    slope_warning: float = 0.05
    bias_critical: float = 2.0
    bias_warning: float = 1.0
    noise_critical: float = 1.5
    hysteresis_critical: float = 0.5
    dfa_critical: float = 0.8
    min_data_points: int = 50

class SensorCreate(BaseModel):
    name: str
    location: str
    source_type: str = "CSV"
    organization_id: Optional[str] = None
    sensor_type: str  # Required: e.g., "pH Sensörü", "Sıcaklık"
    unit: str  # Required: e.g., "pH", "°C"

class SensorResponse(BaseModel):
    id: str
    name: str
    location: str
    source_type: str
    organization_id: Optional[str] = None
    latest_health_score: Optional[float] = 100.0
    latest_status: Optional[str] = "Normal"
    latest_analysis_timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True

class SensorDataInput(BaseModel):
    sensor_id: str
    sensor_type: str = "Generic"
    values: List[float] = []
    timestamps: Optional[List[str]] = None
    config: Optional[SensorConfig] = SensorConfig()

class AnalysisMetrics(BaseModel):
    bias: float
    slope: float
    snr_db: float
    hysteresis: float
    # Optional fields with defaults for backward compatibility
    noise_std: Optional[float] = 0.0
    hysteresis_x: List[float] = []
    hysteresis_y: List[float] = []
    hurst: Optional[float] = 0.5
    hurst_r2: Optional[float] = 0.0
    dfa_alpha: Optional[float] = None
    dfa_r_squared: Optional[float] = None
    dfa_scales: List[float] = []
    dfa_fluctuations: List[float] = []
    timestamps: Optional[List[str]] = None
    trend: Optional[List[float]] = None
    residuals: Optional[List[float]] = None

class AnalysisResult(BaseModel):
    sensor_id: str
    timestamp: str
    health_score: float
    status: str
    metrics: AnalysisMetrics
    flags: List[str]
    recommendation: str
    diagnosis: str
    prediction: Optional[str] = None

class SyntheticRequest(BaseModel):
    type: str
    length: int = 100

class ReportRequest(BaseModel):
    sensor_id: str
    health_score: float
    metrics: AnalysisMetrics
    diagnosis: str
    # Optional fields with defaults
    status: Optional[str] = "Unknown"
    flags: List[str] = []
    recommendation: str = ""
    data: Optional[List[float]] = None
