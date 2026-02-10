#!/usr/bin/env python
"""
Test script for SensorDiagnosisDashboard.

Run with: source venv/bin/activate && python test_diagnosis_dashboard.py
"""

import sys
import numpy as np

from PyQt6.QtWidgets import QApplication, QMainWindow
from desktop_app.ui.views.diagnosis_dashboard import SensorDiagnosisDashboard


def generate_test_data():
    """Generate sample analysis result data."""
    # Simulate raw signal with some noise and spikes
    t = np.linspace(0, 100, 1000)
    signal = np.sin(2 * np.pi * 0.1 * t) + 0.1 * np.random.randn(len(t))
    signal[500:510] += 2  # Add spike
    
    result = {
        "health": {
            "score": 72.5,
            "status": "Yellow",
            "diagnosis": "Warning: High kurtosis detected indicating transient events. Possible bubbles in sample.",
            "root_cause": "BUBBLE_DETECTED",
        },
        "metrics": {
            "lyapunov": 0.08,
            "spectral_centroid": 25.3,
            "ae_error": 0.03,
            "kurtosis": 6.2,
            "hysteresis": 0.12,
            "noise_std": 0.09,
            "sampen": 0.15,
            "slope": 0.0002,
            "snr_db": 18.5,
            "raw_value": 12.5,
            "sampling_rate": 10.0,
            "trend": (signal - signal.mean()).tolist(),
        },
    }
    
    return result, signal


def main():
    app = QApplication(sys.argv)
    
    # Apply dark theme
    app.setStyle("Fusion")
    app.setStyleSheet("""
        QMainWindow { background-color: #1e1e1e; }
        QWidget { background-color: #1e1e1e; color: #ededf2; }
    """)
    
    window = QMainWindow()
    window.setWindowTitle("Sensor Diagnosis Dashboard - Test")
    window.resize(1400, 900)
    
    dashboard = SensorDiagnosisDashboard()
    window.setCentralWidget(dashboard)
    
    # Load test data
    result, raw_data = generate_test_data()
    dashboard.update_results(result, raw_data)
    
    window.show()
    
    print("Dashboard test window opened.")
    print("Close the window to exit.")
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
