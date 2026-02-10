"""
QorSense Backend Core Configuration Module.

Provides centralized configuration management using Pydantic Settings.
Configuration is loaded from environment variables and .env file.
Supports PyInstaller frozen binary execution.
"""

import json
import logging
import os
import sys
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# ============================================================================
# PyInstaller Path Helpers
# ============================================================================

def is_frozen() -> bool:
    """Check if running as a frozen PyInstaller binary."""
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


def get_base_path() -> str:
    """
    Get the base path for resource files.
    - Frozen (PyInstaller): sys._MEIPASS
    - Development: backend directory
    """
    if is_frozen():
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_resource_path(relative_path: str) -> str:
    """
    Get absolute path to a resource file.
    Works both in development and frozen binary mode.
    
    Example:
        get_resource_path("assets/logo.png")
    """
    return os.path.join(get_base_path(), relative_path)


def get_data_path() -> str:
    """
    Get path for persistent data files (SQLite, logs).
    In frozen mode, uses executable directory.
    Development: Project Root
    """
    if is_frozen():
        return os.path.dirname(sys.executable)
    # backend/core/config.py -> backend/core -> backend -> root
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================================
# Threshold Manager for Diagnosis Engine
# ============================================================================

_threshold_logger = logging.getLogger("qorsense.thresholds")


class ThresholdManager:
    """
    Manages configurable thresholds for the DiagnosisEngine.
    
    Supports:
    - Global default thresholds
    - Sensor-specific overrides (e.g., PH_SENSOR, DO_SENSOR)
    - JSON persistence
    - Factory reset
    
    Example:
        >>> tm = ThresholdManager()
        >>> tm.get_threshold("lyapunov_limit")
        0.1
        >>> tm.get_threshold("slope_min", sensor_type="PH_SENSOR")
        0.85
    """
    
    # Factory default thresholds (hardcoded)
    FACTORY_DEFAULTS = {
        "defaults": {
            "sampen_min": 0.05,
            "stddev_min": 0.001,
            "kurtosis_limit": 5.0,
            "lyapunov_chaos": 0.1,
            "lyapunov_stable": 0.05,
            "spectral_limit": 45.0,
            "ae_high": 0.05,
            "ae_medium": 0.02,
            "hysteresis_limit": 0.15,
            "slope_normal": 0.001,
            "slope_limit": 0.005,
        },
        "PH_SENSOR": {"slope_min": 0.85},
        "DO_SENSOR": {"slope_min": 0.80},
    }
    
    def __init__(self, config_path: str | None = None):
        """
        Initialize ThresholdManager.
        
        Args:
            config_path: Path to thresholds.json. If None, uses default location.
        """
        if config_path:
            self._config_path = config_path
        else:
            # Default: config/thresholds.json relative to project root
            base = get_data_path()
            self._config_path = os.path.join(base, "config", "thresholds.json")
        
        self._thresholds: dict[str, Any] = {}
        self._load()
    
    def _load(self) -> None:
        """Load thresholds from JSON file, or use factory defaults."""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, "r", encoding="utf-8") as f:
                    self._thresholds = json.load(f)
                _threshold_logger.info(f"Loaded thresholds from {self._config_path}")
            else:
                _threshold_logger.info("Thresholds file not found, using factory defaults")
                self._thresholds = self.FACTORY_DEFAULTS.copy()
        except Exception as e:
            _threshold_logger.warning(f"Failed to load thresholds: {e}. Using factory defaults.")
            self._thresholds = self.FACTORY_DEFAULTS.copy()
    
    def save(self) -> bool:
        """
        Save current thresholds to JSON file.
        
        Returns:
            True if saved successfully, False otherwise.
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self._config_path), exist_ok=True)
            
            with open(self._config_path, "w", encoding="utf-8") as f:
                json.dump(self._thresholds, f, indent=4)
            _threshold_logger.info(f"Saved thresholds to {self._config_path}")
            return True
        except Exception as e:
            _threshold_logger.error(f"Failed to save thresholds: {e}")
            return False
    
    def get_threshold(self, key: str, sensor_type: str | None = None) -> Any:
        """
        Get a threshold value with optional sensor-specific override.
        
        Args:
            key: Threshold key name
            sensor_type: Optional sensor type for override lookup
            
        Returns:
            Threshold value (sensor override if exists, else default)
        """
        # Check sensor-specific override first
        if sensor_type and sensor_type in self._thresholds:
            sensor_overrides = self._thresholds[sensor_type]
            if key in sensor_overrides:
                return sensor_overrides[key]
        
        # Fall back to defaults
        defaults = self._thresholds.get("defaults", {})
        return defaults.get(key)
    
    def set_threshold(self, key: str, value: Any, sensor_type: str | None = None) -> None:
        """
        Set a threshold value.
        
        Args:
            key: Threshold key name
            value: New value
            sensor_type: Optional sensor type for override (else updates defaults)
        """
        if sensor_type:
            if sensor_type not in self._thresholds:
                self._thresholds[sensor_type] = {}
            self._thresholds[sensor_type][key] = value
        else:
            if "defaults" not in self._thresholds:
                self._thresholds["defaults"] = {}
            self._thresholds["defaults"][key] = value
    
    def get_all_defaults(self) -> dict[str, Any]:
        """Get all default threshold values."""
        return self._thresholds.get("defaults", {}).copy()
    
    def get_sensor_overrides(self, sensor_type: str) -> dict[str, Any]:
        """Get sensor-specific overrides."""
        return self._thresholds.get(sensor_type, {}).copy()
    
    def reset_to_factory(self) -> None:
        """Reset all thresholds to factory defaults."""
        self._thresholds = {
            k: v.copy() if isinstance(v, dict) else v
            for k, v in self.FACTORY_DEFAULTS.items()
        }
        _threshold_logger.info("Reset to factory defaults")
    
    @property
    def config_path(self) -> str:
        """Get the config file path."""
        return self._config_path


# Global ThresholdManager instance
threshold_manager = ThresholdManager()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Application Settings
    app_name: str = Field(default="QorSense v1", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(default="development", description="Environment: development, staging, production")

    # Backend Settings
    backend_host: str = Field(default="0.0.0.0", description="Backend host")  # nosec B104 - local desktop
    backend_port: int = Field(default=8000, ge=1024, le=65535, description="Backend port")
    backend_reload: bool = Field(default=True, description="Enable auto-reload")

    # Database Settings
    database_url: str = Field(
        default="sqlite+aiosqlite:///./data/qorsense.db",
        description="Database connection URL"
    )
    database_echo: bool = Field(default=False, description="Echo SQL queries")
    database_pool_size: int = Field(default=5, ge=1, description="Database connection pool size")
    database_max_overflow: int = Field(default=10, ge=0, description="Max overflow connections")

    # CORS Settings
    cors_origins: str = Field(
        default="http://localhost:3000,http://localhost:8501,http://127.0.0.1:3000,http://127.0.0.1:8501",
        description="Comma-separated list of allowed CORS origins"
    )
    cors_allow_credentials: bool = Field(default=True, description="Allow credentials in CORS")

    # Security Settings
    secret_key: str = Field(
        default="dev-secret-key-change-in-production",
        description="Secret key for JWT and encryption"
    )
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    jwt_access_token_expire_minutes: int = Field(default=30, ge=1, description="JWT access token expiry (minutes)")
    jwt_refresh_token_expire_days: int = Field(default=7, ge=1, description="JWT refresh token expiry (days)")
    api_key: str = Field(default="", description="Optional API key for service auth")

    # Logging Settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or text")
    log_file: str = Field(default="logs/backend.log", description="Log file path")
    log_max_bytes: int = Field(default=10485760, description="Max log file size in bytes")
    log_backup_count: int = Field(default=5, ge=0, description="Number of log file backups")

    # Cache Settings
    redis_url: str = Field(default="redis://localhost:6379/0", description="Redis URL")
    cache_enabled: bool = Field(default=False, description="Enable caching")
    cache_ttl: int = Field(default=300, ge=0, description="Cache TTL in seconds")

    # Analysis Settings
    max_analysis_points: int = Field(default=10000, ge=100, description="Maximum data points for analysis")
    default_window_size: int = Field(default=1000, ge=10, description="Default analysis window size")
    enable_background_analysis: bool = Field(default=True, description="Enable background analysis")

    # Rate Limiting
    rate_limit_enabled: bool = Field(default=False, description="Enable rate limiting")
    rate_limit_per_minute: int = Field(default=60, ge=1, description="Max requests per minute")

    # Monitoring
    metrics_enabled: bool = Field(default=False, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, ge=1024, le=65535, description="Metrics endpoint port")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v_upper = v.upper()
        if v_upper not in allowed:
            raise ValueError(f"Log level must be one of {allowed}")
        return v_upper

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment."""
        allowed = ["development", "staging", "production"]
        v_lower = v.lower()
        if v_lower not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v_lower

    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        """Check if running in production."""
        return self.environment == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development."""
        return self.environment == "development"

# Global settings instance
settings = Settings()


# Production security validation
def _validate_production_settings() -> None:
    """Validate that production settings are properly configured."""
    import logging

    logger = logging.getLogger("qorsense.config")

    # Check for default secret key in production
    default_secrets = [
        "dev-secret-key-change-in-production",
        "your-secret-key-change-this-in-production",
        "changeme",
        "secret",
    ]

    if settings.is_production:
        if settings.secret_key in default_secrets:
            raise RuntimeError(
                "🔴 SECURITY ERROR: Cannot use default SECRET_KEY in production! "
                "Generate a secure key using: openssl rand -hex 32"
            )
    elif settings.secret_key in default_secrets:
        logger.warning(
            "⚠️  Using default SECRET_KEY in non-production environment. "
            "Set a unique SECRET_KEY before deploying to production."
        )


# Run validation on import
_validate_production_settings()


def get_settings() -> Settings:
    """Dependency injection for settings."""
    return settings
