"""
Unit Tests for SensorAnalyzer - Industrial Sensor Analysis Engine.

These tests validate the core analysis algorithms that are critical
for predictive maintenance decisions.
"""

import numpy as np
import pytest
from backend.analysis import (
    SensorAnalyzer, 
    AnalysisOutput,
    DiagnosisEngine,
    calculate_kurtosis,
    calculate_sampen,
    calculate_spectral_centroid,
)
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


class TestDiagnosisEngine:
    """Tests for the DiagnosisEngine hierarchical decision logic."""
    
    def test_diagnosis_frozen_sensor(self):
        """Verify FROZEN_SENSOR detection with very low SampEn."""
        engine = DiagnosisEngine()
        result = engine.diagnose(
            sampen=0.005,  # Below threshold 0.01 (tighter than before)
            kurtosis=0.5,
            lyapunov=0.01,
            spectral_centroid=10.0,
            ae_error=0.001,
            hysteresis=0.05,
            slope=0.0001,
            noise_std=0.1,
        )
        
        assert result.root_cause == "FROZEN_SENSOR"
        assert result.status == "CRITICAL"
        assert result.health_score == 0.0

    def test_diagnosis_frozen_sensor_low_stddev(self):
        """Verify FROZEN_SENSOR detection with low StdDev."""
        engine = DiagnosisEngine()
        result = engine.diagnose(
            sampen=0.5,  # Normal
            kurtosis=0.5,
            lyapunov=0.01,
            spectral_centroid=10.0,
            ae_error=0.001,
            hysteresis=0.05,
            slope=0.0001,
            noise_std=0.0001,  # Below 0.001 threshold
        )
        
        assert result.root_cause == "FROZEN_SENSOR"
        assert result.status == "CRITICAL"

    def test_diagnosis_bubble_detected(self):
        """Verify transient detection with high kurtosis and low Lyapunov.
        
        Note: With GENERIC sensor profile, transient maps to PROCESS_DISTURBANCE.
        """
        engine = DiagnosisEngine()
        result = engine.diagnose(
            sampen=0.8,  # Normal
            kurtosis=10.0,  # High - above 5.0 limit
            lyapunov=0.01,  # Low - below 0.05 stable limit
            spectral_centroid=10.0,
            ae_error=0.001,
            hysteresis=0.05,
            slope=0.0001,
            noise_std=0.1,
            sensor_type="GENERIC",  # Explicit
        )
        
        assert result.root_cause == "PROCESS_DISTURBANCE"  # GENERIC profile transient
        assert result.status == "INFO"
        assert result.health_score == 95.0  # Transient, minimal penalty

    def test_diagnosis_healthy_default(self):
        """Verify HEALTHY status for normal metrics."""
        engine = DiagnosisEngine()
        result = engine.diagnose(
            sampen=0.8,
            kurtosis=2.0,
            lyapunov=0.02,
            spectral_centroid=10.0,
            ae_error=0.005,
            hysteresis=0.05,
            slope=0.01,
            noise_std=0.1,
        )
        
        assert result.root_cause == "HEALTHY"
        assert result.status == "HEALTHY"
        assert result.health_score == 100.0

    def test_diagnosis_emi_noise(self):
        """Verify EMI_NOISE detection with high spectral centroid."""
        engine = DiagnosisEngine()
        result = engine.diagnose(
            sampen=0.8,
            kurtosis=2.0,
            lyapunov=0.02,
            spectral_centroid=60.0,  # Above 50Hz threshold
            ae_error=0.005,
            hysteresis=0.05,
            slope=0.01,
            noise_std=0.1,
        )
        
        assert result.root_cause == "EMI_NOISE"
        assert result.status == "WARNING"


class TestMetricFunctions:
    """Tests for individual metric calculation functions."""
    
    def test_calculate_kurtosis_spike_data(self):
        """Kurtosis should be high for spiky data."""
        # Normal distribution with a spike
        data = np.concatenate([np.zeros(100), [100], np.zeros(100)])
        kurtosis = calculate_kurtosis(data)
        
        assert kurtosis is not None
        assert kurtosis > 5.0  # High kurtosis for spikes

    def test_calculate_kurtosis_uniform_data(self):
        """Kurtosis should be low (negative) for uniform data."""
        data = np.random.uniform(-1, 1, 200)
        kurtosis = calculate_kurtosis(data)
        
        assert kurtosis is not None
        assert kurtosis < 5.0  # Uniform has low/negative kurtosis

    def test_calculate_sampen_constant_signal(self):
        """SampEn should be ~0 for constant signal."""
        data = np.ones(100)
        sampen = calculate_sampen(data)
        
        assert sampen == 0.0  # Perfectly regular

    def test_calculate_sampen_random_signal(self):
        """SampEn should be positive for random signal."""
        data = np.random.randn(200)
        sampen = calculate_sampen(data)
        
        assert sampen is not None
        assert sampen > 0.0  # Random signal has entropy

    def test_calculate_spectral_centroid_low_freq(self):
        """Spectral centroid for low frequency signal."""
        # Generate a low frequency sine wave
        t = np.linspace(0, 10, 1000)
        data = np.sin(2 * np.pi * 0.5 * t)  # 0.5 Hz
        centroid = calculate_spectral_centroid(data, fs=100.0)
        
        assert centroid is not None
        assert centroid < 10.0  # Low frequency signal


class TestDualStreamPipeline:
    """Tests for the Dual-Stream Data Pipeline architecture."""
    
    def test_basic_cleanup_preserves_spikes(self):
        """Verify _basic_cleanup preserves spikes (no median filter)."""
        analyzer = SensorAnalyzer()
        # Data with a clear spike that median filter would remove
        data = [0.0] * 50 + [100.0] + [0.0] * 49  # 100 points with spike at index 50
        
        result = analyzer._basic_cleanup(data)
        
        # Spike should be preserved
        assert result[50] == 100.0
        # Surrounding values should still be 0
        assert result[49] == 0.0
        assert result[51] == 0.0
    
    def test_basic_cleanup_handles_nan(self):
        """Verify _basic_cleanup interpolates NaN values."""
        analyzer = SensorAnalyzer()
        data = [1.0, 2.0, float('nan'), 4.0, 5.0] * 20  # 100 points
        
        result = analyzer._basic_cleanup(data)
        
        assert len(result) == 100
        assert not np.any(np.isnan(result))
    
    def test_basic_cleanup_handles_inf(self):
        """Verify _basic_cleanup replaces Inf with mean."""
        analyzer = SensorAnalyzer()
        data = [1.0] * 50 + [float('inf')] + [1.0] * 49
        
        result = analyzer._basic_cleanup(data)
        
        assert not np.any(np.isinf(result))
        # The inf should be replaced with mean (~1.0)
        assert 0.5 < result[50] < 1.5
    
    def test_preprocessing_removes_spikes(self):
        """Verify preprocessing (median filter) removes spikes."""
        analyzer = SensorAnalyzer()
        # Same spike data
        data = [0.0] * 50 + [100.0] + [0.0] * 49
        
        result = analyzer.preprocessing(data)
        
        # Median filter should remove/reduce the spike
        assert result[50] < 50.0  # Spike significantly reduced
    
    def test_dual_stream_kurtosis_difference(self):
        """Verify raw stream preserves high kurtosis from spikes."""
        analyzer = SensorAnalyzer()
        # Data with spikes
        np.random.seed(42)
        base_data = np.random.normal(0, 1, 200).tolist()
        # Add spikes
        base_data[50] = 50.0
        base_data[100] = -50.0
        base_data[150] = 50.0
        
        # Get both streams
        raw_stream = analyzer._basic_cleanup(base_data)
        clean_stream = analyzer.preprocessing(base_data)
        
        raw_kurtosis = calculate_kurtosis(raw_stream)
        clean_kurtosis = calculate_kurtosis(clean_stream)
        
        assert raw_kurtosis is not None
        assert clean_kurtosis is not None
        # Raw stream should have HIGHER kurtosis (spikes preserved)
        assert raw_kurtosis > clean_kurtosis
    
    def test_analyze_returns_raw_residuals(self):
        """Verify analyze() includes raw_residuals in output."""
        analyzer = SensorAnalyzer()
        data = list(np.sin(np.linspace(0, 4*np.pi, 100)) + np.random.randn(100) * 0.1)
        
        result = analyzer.analyze(data)
        
        assert result["error_code"] == "SUCCESS"
        assert "raw_residuals" in result["metrics"]
        assert len(result["metrics"]["raw_residuals"]) == 100

