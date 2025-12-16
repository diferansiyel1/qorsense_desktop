import sys
import os
import logging
import pandas as pd
import numpy as np
from typing import Dict, Any, List

# Add project root to path to allow importing backend modules
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from backend.analysis import SensorAnalyzer
    from backend.models import SensorConfig
except ImportError as e:
    # If imports fail (context might be different), we assume we are running from root
    try:
        from backend.analysis import SensorAnalyzer
        from backend.models import SensorConfig
    except ImportError:
        logging.error(f"Critical Import Error: {e}. Check python path.")
        raise

logger = logging.getLogger("AnalyzerBridge")

class AnalyzerBridge:
    def __init__(self):
        """
        Bridge between UI and Backend Analysis Logic.
        Initializes the SensorAnalyzer with default configuration.
        """
        try:
            self.config = SensorConfig()
            self.analyzer = SensorAnalyzer(self.config)
            logger.info("AnalyzerBridge initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize AnalyzerBridge: {e}")
            raise

    def analyze_sensor_data(self, data: List[float]) -> Dict[str, Any]:
        """
        Wraps the backend analysis function with error handling for UI.
        
        Args:
            data (List[float]): Raw sensor data points.
            
        Returns:
            Dict: Analysis results or error dictionary.
        """
        try:
            if not data:
                logger.warning("Empty data received.")
                return {"error": "Empty data received"}

            # Create FRESH analyzer for each call to avoid any state caching
            fresh_analyzer = SensorAnalyzer(self.config)
            
            logger.info(f"Analyzing {len(data)} points. First 3: {data[:3]}, Last 3: {data[-3:]}")
            
            # Call the backend logic with fresh analyzer
            result = fresh_analyzer.analyze(data)
            return result

        except Exception as e:
            logger.error(f"Analysis failed: {e}", exc_info=True)
            return {"error": str(e)}

    def generate_demo_data(self, length: int = 200) -> List[float]:
        """Generates dummy data for testing UI without sensors."""
        t = np.linspace(0, 10, length)
        # Signal + Trend + Noise
        signal = np.sin(2 * np.pi * t) 
        trend = 0.5 * t
        noise = np.random.normal(0, 0.2, length)
        data = signal + trend + noise
        return data.tolist()
