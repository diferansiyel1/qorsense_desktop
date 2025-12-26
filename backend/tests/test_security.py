"""
QorSense Test Suite

Initial test infrastructure for critical modules.
Run with: pytest backend/tests/ -v
"""

import pytest
from unittest.mock import patch
import os


class TestSecurityConfig:
    """Tests for security configuration validation."""

    def test_default_secret_key_in_development(self):
        """Verify dev environment allows default secret key with warning."""
        # Default environment is 'development', so this should work
        from backend.core.config import settings
        assert settings.environment == "development"
        assert settings.secret_key is not None

    def test_production_blocks_default_secret_key(self):
        """Verify production environment blocks default secret keys."""
        with patch.dict(os.environ, {
            "ENVIRONMENT": "production",
            "SECRET_KEY": "dev-secret-key-change-in-production"
        }):
            with pytest.raises(RuntimeError, match="SECURITY ERROR"):
                # Force reimport to trigger validation
                import importlib
                import backend.core.config as config_module
                importlib.reload(config_module)


class TestLicenseManager:
    """Tests for license manager security."""

    def test_license_manager_loads(self):
        """Verify license manager initializes correctly."""
        from backend.license_manager import LicenseManager
        lm = LicenseManager()
        machine_id = lm.get_machine_id()
        assert machine_id is not None
        assert len(machine_id) == 32  # SHA-256 truncated to 32 chars

    def test_machine_id_consistency(self):
        """Verify machine ID is deterministic."""
        from backend.license_manager import LicenseManager
        lm1 = LicenseManager()
        lm2 = LicenseManager()
        assert lm1.get_machine_id() == lm2.get_machine_id()

    def test_license_key_format(self):
        """Verify license key format is XXXX-XXXX-XXXX-XXXX."""
        from backend.license_manager import LicenseManager
        lm = LicenseManager()
        machine_id = lm.get_machine_id()
        key = lm.generate_license_key(machine_id)
        assert len(key) == 19  # 16 chars + 3 dashes
        assert key.count("-") == 3


class TestCircuitBreaker:
    """Tests for circuit breaker fault tolerance."""

    def test_circuit_breaker_states(self):
        """Verify circuit breaker state transitions."""
        from desktop_app.workers.circuit_breaker import CircuitBreaker, CircuitState
        
        cb = CircuitBreaker("test_device")
        assert cb.state == CircuitState.CLOSED
        
        # Simulate failures to open circuit
        for _ in range(3):
            cb.record_failure()
        
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_circuit_breaker_recovery(self):
        """Verify circuit breaker can recover after timeout."""
        from desktop_app.workers.circuit_breaker import (
            CircuitBreaker, CircuitBreakerConfig, CircuitState
        )
        import time
        
        config = CircuitBreakerConfig(
            failure_threshold=1,
            recovery_timeout=0.1  # 100ms for fast test
        )
        cb = CircuitBreaker("test_device", config=config)
        
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        
        time.sleep(0.15)  # Wait for recovery timeout
        
        # Should transition to HALF_OPEN
        assert cb.allow_request() is True
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
