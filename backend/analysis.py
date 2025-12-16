import numpy as np
import pandas as pd
from scipy import stats, signal
from typing import Dict, Any, List, Tuple
import logging
from datetime import datetime
from backend.models import SensorConfig

logger = logging.getLogger(__name__)

class SensorAnalyzer:
    def __init__(self, config: SensorConfig = SensorConfig()):
        self.config = config

    def preprocessing(self, data: list) -> np.ndarray:
        """
        Preprocessing pipeline:
        1. Gap check (simple)
        2. Interpolation
        3. Median Filter (Spike removal)
        """
        if len(data) < self.config.min_data_points:
            raise ValueError(f"Insufficient data: {len(data)} points provided, minimum {self.config.min_data_points} required.")

        s = pd.Series(data)
        
        # Gap Limit: Don't fill large gaps (simplified logic here as we don't have timestamps in list)
        # Assuming uniform sampling for now.
        s = s.interpolate(method='linear', limit=5).bfill().ffill()
        
        # Median Filter for Spikes
        # Kernel size 3 or 5 usually good
        s_clean = signal.medfilt(s.values, kernel_size=3)
        
        return s_clean

    def calc_bias(self, data: np.ndarray) -> float:
        """Calculate offset from mean of first 10% vs current."""
        if len(data) < 10: return 0.0
        n_ref = max(1, int(len(data) * 0.1))
        ref_mean = np.mean(data[:n_ref])
        curr_mean = np.mean(data[-n_ref:])
        return float(curr_mean - ref_mean)

    def calc_slope(self, data: np.ndarray) -> float:
        """Calculate linear trend slope."""
        if len(data) < 2: return 0.0
        x = np.arange(len(data))
        slope, _, _, _, _ = stats.linregress(x, data)
        return float(slope)

    def calc_snr_db(self, data: np.ndarray) -> float:
        """
        Calculate SNR in dB.
        Signal = Peak-to-Peak
        Noise = RMS of high-pass filtered signal (or residual after detrending)
        """
        if len(data) < 2: return 0.0
        
        # 1. Estimate Signal Amplitude (Peak-to-Peak)
        # We use the raw range, or robust range (percentiles) to avoid outliers
        signal_pp = np.percentile(data, 95) - np.percentile(data, 5)
        if signal_pp == 0: signal_pp = 1e-6

        # 2. Isolate Noise (High-pass filter or Detrend)
        # Simple approach: Subtract linear trend
        x = np.arange(len(data))
        slope, intercept, _, _, _ = stats.linregress(x, data)
        trend = slope * x + intercept
        noise_component = data - trend
        
        # RMS of noise
        noise_rms = np.sqrt(np.mean(noise_component**2))
        if noise_rms < 1e-9: noise_rms = 1e-9
        
        # 3. Calculate SNR (dB)
        snr_db = 20 * np.log10(signal_pp / noise_rms)
        return float(snr_db)

    def calc_hysteresis(self, data: np.ndarray) -> Tuple[float, List[float], List[float]]:
        """
        Calculate Hysteresis based on Area Difference between Rising and Falling edges.
        Simplified Edge Detection.
        """
        if len(data) < 5: return 0.0, [], []
        
        # Smooth heavily to find "edges" (macro movements)
        smooth = pd.Series(data).rolling(window=5, center=True).mean().bfill().ffill().values
        diffs = np.diff(smooth)
        
        # Threshold for "edge"
        threshold = np.std(diffs) * 0.5
        
        rising_indices = np.where(diffs > threshold)[0]
        falling_indices = np.where(diffs < -threshold)[0]
        
        if len(rising_indices) == 0 or len(falling_indices) == 0:
            return 0.0, [], []
            
        avg_rising_val = np.mean(data[rising_indices])
        avg_falling_val = np.mean(data[falling_indices])
        
        # Area difference proxy: Difference in average values during rising vs falling phases
        # Normalized by range
        data_range = np.ptp(data) if np.ptp(data) > 0 else 1.0
        hysteresis_score = abs(avg_rising_val - avg_falling_val) / data_range
        
        return float(hysteresis_score), data.tolist(), smooth.tolist()

    def calc_dfa(self, data: np.ndarray, order: int = 1) -> Tuple[float, float, List[float], List[float]]:
        """
        DFA with R^2 calculation.
        Returns: (hurst, r_squared, scales, fluctuations)
        """
        try:
            if len(data) == 0: return 0.5, 0.0, [], []

            y = np.cumsum(data - np.mean(data))
            N = len(y)
            if N < 20: return 0.5, 0.0, [], []

            min_scale = 4
            max_scale = N // 4
            if max_scale < min_scale: return 0.5, 0.0, [], []
            
            scales = np.unique(np.logspace(np.log10(min_scale), np.log10(max_scale), num=20).astype(int))
            scales = scales[scales > order + 2]
            
            if len(scales) < 3:
                 scales = np.arange(min_scale, max_scale, max(1, (max_scale - min_scale) // 5))
                 scales = np.unique(scales.astype(int))
                 scales = scales[scales > order + 2]

            if len(scales) < 2: return 0.5, 0.0, [], []

            fluctuations = []
            
            # Vectorized-ish loop (still loop over scales, but inner operations are numpy)
            for scale in scales:
                n_segments = N // scale
                # Reshape data into (n_segments, scale) - truncating end
                segments = y[:n_segments*scale].reshape(n_segments, scale)
                x = np.arange(scale)
                
                # Polyfit for each segment? 
                # np.polyfit can handle multiple columns if we transpose, but let's keep loop for safety/clarity first
                # Optimization:
                total_residual_sq = 0.0
                for seg in segments:
                    coeffs = np.polyfit(x, seg, order)
                    trend = np.polyval(coeffs, x)
                    total_residual_sq += np.sum((seg - trend) ** 2)
                
                f_n = np.sqrt(total_residual_sq / (n_segments * scale))
                fluctuations.append(f_n)
            
            fluctuations = np.array(fluctuations)
            valid_idx = fluctuations > 1e-10
            if np.sum(valid_idx) < 3: return 0.5, 0.0, [], []
                
            log_scales = np.log(scales[valid_idx])
            log_flucts = np.log(fluctuations[valid_idx])
            
            slope, intercept, r_value, p_value, std_err = stats.linregress(log_scales, log_flucts)
            
            return float(slope), float(r_value**2), scales[valid_idx].tolist(), fluctuations[valid_idx].tolist()
            
        except Exception as e:
            logger.warning(f"DFA Calculation Error: {e}")
            return 0.5, 0.0, [], []

    def decompose_signal(self, data: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        """
        Separate signal into Trend and Residuals using Savitzky-Golay filter.
        Trend represents Process Change.
        Residuals represent Noise/Sensor Characteristics.
        """
        if len(data) < self.config.min_data_points:
             return data, np.zeros_like(data)
             
        # Savitzky-Golay filter
        # Window length must be odd and <= data length
        window_length = min(len(data), 51)
        if window_length % 2 == 0: window_length -= 1
        window_length = max(3, window_length)
        
        polyorder = 3
        if window_length <= polyorder:
             polyorder = window_length - 1
             
        try:
            trend = signal.savgol_filter(data, window_length, polyorder)
        except Exception as e:
            logger.warning(f"Golay filter failed: {e}. Using median filter fallback.")
            trend = signal.medfilt(data, kernel_size=min(len(data), 11) if min(len(data), 11) % 2 else min(len(data), 11)-1)

        residuals = data - trend
        return trend, residuals

    def analyze(self, raw_data: list) -> Dict[str, Any]:
        """
        Centralized Analysis Pipeline.
        Returns full analysis result (metrics + health score).
        """
        # 1. Preprocessing
        clean_data = self.preprocessing(raw_data)
        
        # 2. Decomposition (Signal Separation)
        trend, residuals = self.decompose_signal(clean_data)
        
        # 3. Calculate Metrics
        # Slope -> Calculated on TREND
        slope = self.calc_slope(trend)
        
        # Noise -> Calculated on RESIDUALS
        noise_std = float(np.std(residuals))
        
        # DFA -> Calculated on RESIDUALS (Detrended Fluctuation Analysis usually expects detrended data anyway, but explicit usage here is safer)
        hurst, hurst_r2, dfa_scales, dfa_flucts = self.calc_dfa(residuals)
        
        # Metric Helpers (Some still use full data or specific components)
        bias = self.calc_bias(clean_data) # Bias is absolute shift, use clean data (or trend end)
        snr_db = self.calc_snr_db(clean_data) # SNR usually needs both signal (trend) and noise (residuals)
        hysteresis, hyst_x, hyst_y = self.calc_hysteresis(clean_data)
        
        metrics_dict = {
            "bias": bias, 
            "slope": slope, 
            "noise_std": noise_std, 
            "snr_db": snr_db,
            "hysteresis": hysteresis, 
            "hysteresis_x": hyst_x, 
            "hysteresis_y": hyst_y,
            "hurst": hurst, 
            "hurst_r2": hurst_r2, 
            "dfa_scales": dfa_scales, 
            "dfa_fluctuations": dfa_flucts,
            "trend": trend.tolist(),
            "residuals": residuals.tolist()
        }
        
        # 4. Health Decision & RUL
        # We pass metrics_dict to get_health_score, but need to update get_health_score to logic
        health = self.get_health_score(metrics_dict)
        rul_prediction = self.calc_rul(trend, slope) # Use trend for RUL projection

        return {
            "metrics": metrics_dict,
            "health": health,
            "prediction": rul_prediction,
            "components": { # Optional: return components for debugging if needed, but usually too heavy
                # "trend": trend.tolist(),
                # "residuals": residuals.tolist()
            }
        }

    def calc_rul(self, data: np.ndarray, slope: float) -> str:
        """
        Calculate Estimated Remaining Useful Life (RUL).
        Based on linear projection of current trend towards critical bias threshold.
        """
        if abs(slope) < 1e-6:
            return "Stable (> 1 year)"
            
        # Current "level" (intercept of trend at end)
        x = np.arange(len(data))
        _, intercept, _, _, _ = stats.linregress(x, data)
        current_val = slope * (len(data) - 1) + intercept
        
        # Distance to critical threshold
        # We assume critical threshold is defined relative to 0 (absolute bias)
        # In reality, it should be relative to initial baseline, but here data is raw.
        # Let's assume critical deviation is from the *initial* value.
        initial_val = data[0] if len(data) > 0 else 0
        
        # Thresholds
        upper_limit = initial_val + self.config.bias_critical
        lower_limit = initial_val - self.config.bias_critical
        
        if slope > 0:
            dist = upper_limit - current_val
        else:
            dist = current_val - lower_limit
            
        if dist <= 0:
            return "Critical Threshold Exceeded"
            
        # Time steps remaining
        steps = dist / abs(slope)
        
        # Convert steps to time (assuming 1 step = 1 second for demo)
        if steps > 3600 * 24 * 365:
            return "Stable (> 1 year)"
        elif steps > 3600 * 24:
            days = int(steps / (3600 * 24))
            return f"{days} days"
        elif steps > 3600:
            hours = int(steps / 3600)
            return f"{hours} hours"
        else:
            mins = int(steps / 60)
            return f"{mins} mins"

    def get_health_score(self, metrics: Dict[str, float]) -> Dict[str, Any]:
        """Calculate weighted health score with new Decision Logic."""
        score = 100.0
        diagnosis = []
        flags = []
        recommendation = "System operating normally."
        
        # --- Decision Logic Refinement ---
        
        slope = abs(metrics.get("slope", 0))
        noise_std = metrics.get("noise_std", 0)
        
        # --- Dynamic Health Score Logic ---
        
        # 1. Slope (Trend Stability) Penalty
        # Linear penalty proportional to how much it exceeds the limit
        slope_penalty = 0.0
        if slope > self.config.slope_warning:
            # Base penalty 5, plus extra based on magnitude
            # Normalized excess: (slope - warning) / (critical - warning)
            excess = slope - self.config.slope_warning
            range_span = max(1e-9, self.config.slope_critical - self.config.slope_warning)
            factor = min(1.0, excess / range_span) * 20.0 # Max 20 penalty for slope
            
            slope_penalty = 5.0 + factor
            
            if noise_std < 0.5:
                diagnosis.append("Process Shift Detected")
                flags.append("PROCESS_SHIFT")
                recommendation = "Check process parameters."
            else:
                 diagnosis.append("Trend Instability")
                 flags.append("DRIFT")
                 recommendation = "Monitor sensor for drift."

        score -= slope_penalty

        # 2. Bias (Offset) Penalty
        bias = abs(metrics.get("bias", 0))
        bias_penalty = 0.0
        if bias > self.config.bias_warning:
             # Proportional penalty
             # Max penalty 25 for bias
             excess = bias - self.config.bias_warning
             range_span = max(0.1, self.config.bias_critical - self.config.bias_warning)
             # Logarithmic scaling for bias to avoid punishing massive outliers too hard instantly?
             # Let's stick to linear clamped for now.
             factor = min(1.0, excess / range_span) * 20.0
             
             bias_penalty = 5.0 + factor
             diagnosis.append(f"Bias Shift (Avg: {bias:.1f})")
             flags.append("BIAS")
        
        score -= bias_penalty

        # 3. Noise Penalty (Dynamic)
        # Threshold: 2.0 (Strict) -> 10.0 (Very Noisy)
        noise_limit = 2.0
        noise_max = 20.0
        noise_penalty = 0.0
        
        if noise_std > noise_limit:
            # Linear mapping from 2.0 to 20.0
            # If noise is 2.0 -> penalty 0 (technically > so epsilon)
            # If noise is 20.0 -> penalty 30
            
            excess_noise = min(noise_max, noise_std) - noise_limit
            noise_range = noise_max - noise_limit
            penalty_factor = (excess_noise / noise_range) * 25.0
            
            noise_penalty = 5.0 + penalty_factor
            diagnosis.append(f"High Noise (σ={noise_std:.1f})")
            flags.append("NOISE")
            
        score -= noise_penalty
        
        # 4. DFA Validity Check
        hurst_r2 = metrics.get("hurst_r2", 0.0)
        if hurst_r2 < 0.9:
            # Small penalty for unreliability
            score -= 5.0
            diagnosis.append("DFA Unreliable")
        
        # 5. DFA Exponent Check
        hurst = metrics.get("hurst", 0.5)
        if hurst_r2 >= 0.9: # Only penalize hurst if R2 is valid
            if hurst > self.config.dfa_critical:
                 score -= 15.0
                 diagnosis.append("Strong Persistence")
            elif hurst < 0.2:
                 score -= 10.0
                 diagnosis.append("Anti-persistence")

        score = max(0.0, min(100.0, score))
        
        status = "Green"
        if score < 60: status = "Red"
        elif score < 85: status = "Yellow"
            
        if not diagnosis:
            diagnosis.append("System Normal")
            
        return {
            "score": score,
            "status": status,
            "diagnosis": "; ".join(diagnosis),
            "flags": flags,
            "recommendation": recommendation
        }
