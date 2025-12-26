"""
Unit Tests for SensorAnalyzer - Industrial Sensor Analysis Engine.

These tests validate the core analysis algorithms that are critical
for predictive maintenance decisions.
"""

import numpy as np
import pytest
from backend.analysis import SensorAnalyzer, AnalysisOutput
from backend.models import SensorConfig, SensorLimitConfig, BiasResult, DFAResult


class TestSensorAnalyzerPreprocessing:
    """Tests for data preprocessing and validation."""

    def test_preprocessing_valid_data(self):
        """Verify preprocessing handles normal data correctly."""
        analyzer = SensorAnalyzer()
        data = [1.0, 2.0, 3.0, 4.0, 5.0] * 20  # 100 points
        result = analyzer.preprocessing(data)
        
        assert len(result) == 100
        assert not np.any(np.isnan(result))
        assert not np.any(np.isinf(result))

    def test_preprocessing_rejects_insufficient_data(self):
        """Verify preprocessing rejects data below minimum threshold."""
        analyzer = SensorAnalyzer()
        data = [1.0, 2.0, 3.0]  # Too few points
        
        with pytest.raises(ValueError, match="Insufficient data"):
            analyzer.preprocessing(data)

    def test_preprocessing_handles_nan_values(self):
        """Verify preprocessing interpolates NaN values."""
        analyzer = SensorAnalyzer()
        data = [1.0] * 50 + [float('nan')] + [3.0] * 49  # 1 NaN in 100 points
        result = analyzer.preprocessing(data)
        
        assert len(result) == 100
        assert not np.any(np.isnan(result))

    def test_preprocessing_rejects_too_many_nans(self):
        """Verify preprocessing rejects data with >10% NaN."""
        analyzer = SensorAnalyzer()
        data = [1.0] * 50 + [float('nan')] * 60  # 55% valid
        
        with pytest.raises(ValueError, match="Too many NaN"):
            analyzer.preprocessing(data)

    def test_preprocessing_handles_inf_values(self):
        """Verify preprocessing clamps Inf values."""
        analyzer = SensorAnalyzer()
        data = [1.0] * 50 + [float('inf')] + [2.0] * 49
        result = analyzer.preprocessing(data)
        
        assert not np.any(np.isinf(result))


class TestSensorAnalyzerBias:
    """Tests for bias calculation."""

    def test_bias_with_reference_value(self):
        """Verify bias calculation against calibration reference."""
        analyzer = SensorAnalyzer()
        # Data starts at 1.0, ends at 2.0
        data = np.linspace(1.0, 2.0, 100)
        
        result = analyzer.calc_bias(data, reference_value=1.0)
        
        assert isinstance(result, BiasResult)
        # End window mean should be around 2.0, so bias ~1.0
        assert 0.9 < result.absolute < 1.1
        assert result.reference == 1.0

    def test_bias_without_reference(self):
        """Verify bias calculation uses start window as reference."""
        analyzer = SensorAnalyzer()
        data = np.linspace(0.0, 10.0, 100)
        
        result = analyzer.calc_bias(data, reference_value=None)
        
        # Should compare end vs start
        assert result.absolute > 0  # Data is increasing

    def test_bias_stable_signal(self):
        """Verify near-zero bias for stable signal."""
        analyzer = SensorAnalyzer()
        data = np.ones(100) * 5.0  # Constant signal
        
        result = analyzer.calc_bias(data)
        
        assert abs(result.absolute) < 0.01


class TestSensorAnalyzerSlope:
    """Tests for slope (drift) calculation."""

    def test_slope_positive_trend(self):
        """Verify slope detects positive drift."""
        analyzer = SensorAnalyzer()
        data = np.linspace(0, 10, 100)  # Clear upward trend
        
        slope = analyzer.calc_slope(data)
        
        assert slope > 0.09  # Should be ~0.1 per sample

    def test_slope_negative_trend(self):
        """Verify slope detects negative drift."""
        analyzer = SensorAnalyzer()
        data = np.linspace(10, 0, 100)  # Clear downward trend
        
        slope = analyzer.calc_slope(data)
        
        assert slope < -0.09  # Should be ~-0.1 per sample

    def test_slope_flat_signal(self):
        """Verify near-zero slope for flat signal."""
        analyzer = SensorAnalyzer()
        data = np.ones(100) * 5.0
        
        slope = analyzer.calc_slope(data)
        
        assert abs(slope) < 1e-6


class TestSensorAnalyzerSNR:
    """Tests for Signal-to-Noise Ratio calculation."""

    def test_snr_clean_signal(self):
        """Verify high SNR for clean signal."""
        analyzer = SensorAnalyzer()
        # Clean sine wave
        data = np.sin(np.linspace(0, 4*np.pi, 100))
        
        snr = analyzer.calc_snr_db(data)
        
        # SNR depends on detrending method - clean sine wave gives ~10 dB
        assert snr > 5  # Should be positive for clean signal

    def test_snr_noisy_signal(self):
        """Verify lower SNR for noisy signal."""
        analyzer = SensorAnalyzer()
        # Sine wave with significant noise
        np.random.seed(42)
        data = np.sin(np.linspace(0, 4*np.pi, 100)) + np.random.normal(0, 0.5, 100)
        
        snr = analyzer.calc_snr_db(data)
        
        # Should be lower than clean signal
        assert snr < 15


class TestSensorAnalyzerDFA:
    """Tests for Detrended Fluctuation Analysis."""

    def test_dfa_random_walk(self):
        """Verify DFA returns valid result for random walk."""
        analyzer = SensorAnalyzer()
        np.random.seed(42)
        # Random walk (cumulative sum creates integrated series)
        data = np.cumsum(np.random.randn(500))
        
        result = analyzer.calc_dfa(data)
        
        assert isinstance(result, DFAResult)
        # Hurst should be positive and R² should indicate good fit
        assert result.hurst > 0
        assert result.r_squared > 0.9  # Good linear fit

    def test_dfa_persistent_signal(self):
        """Verify DFA detects persistent behavior (H > 0.5)."""
        analyzer = SensorAnalyzer()
        # Highly correlated (trending) signal
        data = np.cumsum(np.ones(500) * 0.1 + np.random.randn(500) * 0.01)
        
        result = analyzer.calc_dfa(data)
        
        assert result.hurst > 0.5  # Should be persistent

    def test_dfa_short_data_returns_default(self):
        """Verify DFA handles short data gracefully."""
        analyzer = SensorAnalyzer()
        data = np.array([1.0, 2.0, 3.0])
        
        result = analyzer.calc_dfa(data)
        
        assert result.hurst == 0.5  # Default value


class TestSensorAnalyzerHealth:
    """Tests for health scoring."""

    def test_health_score_healthy_signal(self):
        """Verify high health score for healthy signal."""
        analyzer = SensorAnalyzer()
        metrics = {
            "slope": 0.0001,
            "bias_result": {"absolute": 0.01, "relative": 0.1, "reference": 1.0},
            "noise_std": 0.01,
            "snr_db": 40,
            "hurst": 0.5,
            "hysteresis": 0.01
        }
        
        result = analyzer.get_health_score(metrics)
        
        assert result.score >= 85
        assert result.status == "Green"

    def test_health_score_degraded_signal(self):
        """Verify medium health score for degraded signal."""
        analyzer = SensorAnalyzer()
        config = SensorLimitConfig()  # Default limits
        metrics = {
            "slope": config.slope_warning * 1.5,  # Above warning
            "bias_result": {"absolute": config.bias_warning * 1.5},
            "noise_std": config.noise_warning * 1.5,
            "snr_db": 15,
            "hurst": 0.5
        }
        
        result = analyzer.get_health_score(metrics)
        
        assert result.score < 85
        assert result.status in ["Yellow", "Red"]

    def test_health_score_critical_signal(self):
        """Verify low health score for critical signal."""
        analyzer = SensorAnalyzer()
        config = SensorLimitConfig()
        metrics = {
            "slope": config.slope_critical * 2,  # Way above critical
            "bias_result": {"absolute": config.bias_critical * 2},
            "noise_std": config.noise_critical * 2,
            "snr_db": 5,
            "hurst": 0.95  # Very persistent
        }
        
        result = analyzer.get_health_score(metrics)
        
        assert result.score < 60
        assert result.status == "Red"


class TestSensorAnalyzerDecomposition:
    """Tests for signal decomposition."""

    def test_decomposition_extracts_trend(self):
        """Verify decomposition separates trend from residuals."""
        analyzer = SensorAnalyzer()
        # Signal = trend + noise
        np.random.seed(42)
        trend_true = np.linspace(0, 10, 100)
        noise = np.random.randn(100) * 0.1
        data = trend_true + noise
        
        trend, residuals = analyzer.decompose_signal(data)
        
        assert len(trend) == 100
        assert len(residuals) == 100
        # Trend should roughly follow true trend
        assert np.corrcoef(trend, trend_true)[0, 1] > 0.99

    def test_decomposition_residuals_sum_to_original(self):
        """Verify trend + residuals ≈ original."""
        analyzer = SensorAnalyzer()
        data = np.random.randn(100) + np.linspace(0, 5, 100)
        
        trend, residuals = analyzer.decompose_signal(data)
        reconstructed = trend + residuals
        
        np.testing.assert_allclose(reconstructed, data, rtol=1e-5)
