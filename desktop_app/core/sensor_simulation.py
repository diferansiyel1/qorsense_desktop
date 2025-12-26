"""
Realistic Sensor Simulation Engine for Predictive Maintenance
Generates both healthy and fault sensor data patterns.
"""

import numpy as np
from typing import List, Tuple, Optional
from enum import Enum
import random


class FaultType(Enum):
    """Types of fault patterns for simulation."""
    HEALTHY = "healthy"
    BEARING_DEGRADATION = "bearing_degradation"
    SENSOR_DRIFT = "sensor_drift"
    INTERMITTENT_CONTACT = "intermittent_contact"
    THERMAL_RUNAWAY = "thermal_runaway"
    PUMP_CAVITATION = "pump_cavitation"
    MIXED_DEGRADATION = "mixed_degradation"


class SensorSimulationEngine:
    """
    Generates realistic industrial sensor data for predictive maintenance testing.
    
    Healthy signals simulate:
      - Process dynamics with damped oscillations
      - Setpoint tracking behavior
      - Natural measurement noise
      - Occasional minor disturbances
    
    Fault signals add characteristic degradation patterns.
    """
    
    def __init__(self, 
                 base_value: float = 25.0,
                 sampling_rate: float = 1.0,
                 noise_level: float = 0.02):
        """
        Args:
            base_value: Process setpoint (e.g., 25°C temperature)
            sampling_rate: Samples per second
            noise_level: Base noise as fraction of base_value
        """
        self.base_value = base_value
        self.sampling_rate = sampling_rate
        self.noise_level = noise_level
        
    def generate_healthy_data(self, duration: float = 300.0) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate realistic healthy sensor data.
        
        Args:
            duration: Duration in seconds
            
        Returns:
            Tuple of (data, time_axis)
        """
        n_samples = int(duration * self.sampling_rate)
        t = np.linspace(0, duration, n_samples)
        
        # Base signal with process dynamics
        signal = np.full(n_samples, self.base_value)
        
        # 1. Process oscillations (damped, like thermal mass response)
        # Primary mode - slow oscillation (thermal inertia)
        period1 = 60 + random.uniform(-10, 10)  # ~60s period
        amplitude1 = self.base_value * 0.01  # 1% amplitude
        damping1 = 0.001
        process_osc = amplitude1 * np.sin(2 * np.pi * t / period1) * np.exp(-damping1 * t)
        
        # Secondary mode - faster process dynamics
        period2 = 15 + random.uniform(-3, 3)  # ~15s period
        amplitude2 = self.base_value * 0.005  # 0.5% amplitude
        process_osc += amplitude2 * np.sin(2 * np.pi * t / period2)
        
        signal += process_osc
        
        # 2. Slight linear drift (realistic sensor behavior, auto-corrected)
        max_drift = self.base_value * 0.002  # 0.2% max drift
        drift = max_drift * np.sin(2 * np.pi * t / (duration * 0.8))
        signal += drift
        
        # 3. Measurement noise (Gaussian)
        noise_sigma = self.base_value * self.noise_level
        noise = np.random.normal(0, noise_sigma, n_samples)
        signal += noise
        
        # 4. Occasional disturbances (2% of samples have small bumps)
        n_disturbances = int(n_samples * 0.02)
        disturbance_idx = np.random.choice(n_samples, n_disturbances, replace=False)
        disturbance_mag = np.random.normal(0, noise_sigma * 2, n_disturbances)
        signal[disturbance_idx] += disturbance_mag
        
        # 5. Quantization effect (simulating ADC)
        resolution = self.base_value * 0.001  # 0.1% resolution
        signal = np.round(signal / resolution) * resolution
        
        return signal, t
    
    def generate_fault_data(self, 
                           fault_type: FaultType,
                           duration: float = 300.0,
                           severity: float = 0.8) -> Tuple[np.ndarray, np.ndarray]:
        """
        Generate sensor data with fault patterns.
        
        Args:
            fault_type: Type of fault to simulate
            duration: Duration in seconds
            severity: Fault severity 0-1 (higher = more obvious)
            
        Returns:
            Tuple of (data, time_axis)
        """
        # Start with healthy baseline
        signal, t = self.generate_healthy_data(duration)
        n_samples = len(signal)
        
        if fault_type == FaultType.HEALTHY:
            return signal, t
            
        elif fault_type == FaultType.BEARING_DEGRADATION:
            signal = self._add_bearing_degradation(signal, t, severity)
            
        elif fault_type == FaultType.SENSOR_DRIFT:
            signal = self._add_sensor_drift(signal, t, severity)
            
        elif fault_type == FaultType.INTERMITTENT_CONTACT:
            signal = self._add_intermittent_contact(signal, t, severity)
            
        elif fault_type == FaultType.THERMAL_RUNAWAY:
            signal = self._add_thermal_runaway(signal, t, severity)
            
        elif fault_type == FaultType.PUMP_CAVITATION:
            signal = self._add_pump_cavitation(signal, t, severity)
            
        elif fault_type == FaultType.MIXED_DEGRADATION:
            # Apply multiple subtle faults
            signal = self._add_bearing_degradation(signal, t, severity * 0.4)
            signal = self._add_sensor_drift(signal, t, severity * 0.3)
            signal = self._add_pump_cavitation(signal, t, severity * 0.3)
        
        return signal, t
    
    def _add_bearing_degradation(self, signal: np.ndarray, t: np.ndarray, 
                                  severity: float) -> np.ndarray:
        """
        Bearing wear: Progressive increase in vibration amplitude + harmonics.
        Characteristic signature: Growing RMS + high-frequency content.
        """
        n = len(signal)
        
        # Progressive amplitude growth (exponential)
        growth_rate = 0.008 * severity
        amplitude_envelope = np.exp(growth_rate * t) - 1
        amplitude_envelope = amplitude_envelope / amplitude_envelope.max() * severity
        
        # Base vibration increase
        vibration = amplitude_envelope * self.base_value * 0.15
        
        # Add harmonics (bearing defect frequencies)
        # BPFO (Ball Pass Frequency Outer) - typically 3-5x shaft speed
        bpfo_freq = 3.5  # Hz
        bpfo_component = amplitude_envelope * 0.08 * self.base_value * np.sin(2 * np.pi * bpfo_freq * t)
        
        # Second harmonic
        bpfo_2x = amplitude_envelope * 0.04 * self.base_value * np.sin(4 * np.pi * bpfo_freq * t)
        
        # Impulse-like spikes (increasing frequency towards end)
        spike_probability = 0.001 + amplitude_envelope * 0.015
        spikes = np.random.random(n) < spike_probability
        spike_magnitude = np.random.exponential(self.base_value * 0.1 * severity, n)
        spike_contribution = spikes * spike_magnitude
        
        return signal + vibration + bpfo_component + bpfo_2x + spike_contribution
    
    def _add_sensor_drift(self, signal: np.ndarray, t: np.ndarray,
                          severity: float) -> np.ndarray:
        """
        Sensor drift: Progressive calibration loss.
        Characteristic: Exponential or linear drift from true value.
        """
        duration = t[-1] - t[0]
        
        # Drift pattern: S-curve (starts slow, accelerates, then slows)
        drift_max = self.base_value * 0.2 * severity  # Up to 20% drift
        
        # Sigmoid-like drift profile
        midpoint = duration * 0.6
        steepness = 0.02
        drift = drift_max / (1 + np.exp(-steepness * (t - midpoint)))
        
        # Add some drift noise (not perfectly smooth)
        drift_noise = np.cumsum(np.random.normal(0, 0.001 * self.base_value, len(t)))
        drift_noise = drift_noise - drift_noise.mean()
        drift += drift_noise * severity * 0.3
        
        return signal + drift
    
    def _add_intermittent_contact(self, signal: np.ndarray, t: np.ndarray,
                                   severity: float) -> np.ndarray:
        """
        Intermittent contact: Loose wire or connector.
        Characteristic: Random spikes + occasional dropout periods.
        """
        n = len(signal)
        result = signal.copy()
        
        # Random spikes (both positive and negative)
        n_spikes = int(n * 0.05 * severity)
        spike_idx = np.random.choice(n, n_spikes, replace=False)
        spike_mag = np.random.choice([-1, 1], n_spikes) * np.random.uniform(
            self.base_value * 0.2, self.base_value * 0.5, n_spikes
        )
        result[spike_idx] += spike_mag * severity
        
        # Dropout periods (signal goes to near-zero or saturates)
        n_dropouts = int(3 + severity * 7)
        for _ in range(n_dropouts):
            start = np.random.randint(0, n - 20)
            length = np.random.randint(3, 15)
            end = min(start + length, n)
            
            # Either dropout or saturation
            if np.random.random() > 0.5:
                result[start:end] = self.base_value * 0.05  # Near zero
            else:
                result[start:end] = self.base_value * 1.5  # Saturation
        
        # High-frequency noise bursts
        burst_starts = np.random.choice(n, int(n * 0.02 * severity), replace=False)
        for start in burst_starts:
            length = min(10, n - start)
            result[start:start+length] += np.random.normal(0, self.base_value * 0.1, length)
        
        return result
    
    def _add_thermal_runaway(self, signal: np.ndarray, t: np.ndarray,
                              severity: float) -> np.ndarray:
        """
        Thermal runaway: Uncontrolled heating process.
        Characteristic: Exponential rise with inflection point.
        """
        duration = t[-1] - t[0]
        
        # Normal operation for first ~40% of duration
        transition_start = duration * 0.4
        
        # Exponential thermal rise
        runaway_temp = self.base_value * (0.5 + 0.5 * severity)  # Up to 1.5x base
        
        thermal_rise = np.zeros_like(t)
        mask = t > transition_start
        t_shifted = t[mask] - transition_start
        
        # Exponential with saturation
        tau = duration * 0.3 / severity  # Time constant
        thermal_rise[mask] = runaway_temp * (1 - np.exp(-t_shifted / tau))
        
        # Add thermal fluctuations (instability indicator)
        instability = np.zeros_like(t)
        instability[mask] = (0.02 * self.base_value * severity * 
                            np.sin(2 * np.pi * 0.5 * t_shifted) *
                            (1 - np.exp(-t_shifted / (tau * 2))))
        
        return signal + thermal_rise + instability
    
    def _add_pump_cavitation(self, signal: np.ndarray, t: np.ndarray,
                              severity: float) -> np.ndarray:
        """
        Pump cavitation: Air bubbles in fluid system.
        Characteristic: Irregular oscillations + pressure drops.
        """
        n = len(signal)
        result = signal.copy()
        
        # Irregular pressure oscillations
        # Multiple frequencies beating together
        freq1 = 2.5 + np.random.uniform(-0.5, 0.5)
        freq2 = 3.7 + np.random.uniform(-0.3, 0.3)
        freq3 = 5.2 + np.random.uniform(-0.4, 0.4)
        
        cavitation_osc = (
            0.06 * np.sin(2 * np.pi * freq1 * t) +
            0.04 * np.sin(2 * np.pi * freq2 * t) +
            0.03 * np.sin(2 * np.pi * freq3 * t)
        ) * self.base_value * severity
        
        # Amplitude modulation (cavitation comes and goes)
        mod_freq = 0.1
        modulation = 0.5 + 0.5 * np.sin(2 * np.pi * mod_freq * t)
        cavitation_osc *= modulation
        
        result += cavitation_osc
        
        # Sudden pressure drops (bubble collapse)
        n_collapses = int(5 + severity * 15)
        collapse_idx = np.random.choice(n, n_collapses, replace=False)
        
        for idx in collapse_idx:
            # Sharp drop followed by recovery
            drop_length = min(8, n - idx)
            drop_profile = -self.base_value * 0.15 * severity * np.exp(-np.arange(drop_length) / 2)
            result[idx:idx+drop_length] += drop_profile
        
        # Increased noise during cavitation
        extra_noise = np.random.normal(0, self.base_value * 0.02 * severity, n)
        extra_noise *= modulation
        result += extra_noise
        
        return result


# Convenience functions for direct use
def generate_healthy_sensor_data(n_samples: int = 300, 
                                  base_value: float = 25.0) -> List[float]:
    """Generate healthy sensor data for testing."""
    engine = SensorSimulationEngine(base_value=base_value)
    duration = n_samples  # 1Hz sampling
    signal, _ = engine.generate_healthy_data(duration)
    return signal[:n_samples].tolist()


def generate_fault_sensor_data(fault_type: str, 
                                n_samples: int = 300,
                                base_value: float = 25.0,
                                severity: float = 0.8) -> List[float]:
    """Generate fault sensor data for testing."""
    engine = SensorSimulationEngine(base_value=base_value)
    
    fault_map = {
        "bearing_degradation": FaultType.BEARING_DEGRADATION,
        "sensor_drift": FaultType.SENSOR_DRIFT,
        "intermittent_contact": FaultType.INTERMITTENT_CONTACT,
        "thermal_runaway": FaultType.THERMAL_RUNAWAY,
        "pump_cavitation": FaultType.PUMP_CAVITATION,
        "mixed_degradation": FaultType.MIXED_DEGRADATION,
    }
    
    fault = fault_map.get(fault_type, FaultType.MIXED_DEGRADATION)
    duration = n_samples
    signal, _ = engine.generate_fault_data(fault, duration, severity)
    return signal[:n_samples].tolist()
