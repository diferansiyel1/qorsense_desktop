import logging

from desktop_app.core.analyzer_bridge import AnalyzerBridge
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger("AnalysisWorker")

class AnalysisWorker(QThread):
    """
    Background worker thread for running heavy analysis.
    Emits signals upon completion or error.
    """
    finished = pyqtSignal(dict) # Emits the result dictionary
    error = pyqtSignal(str)     # Emits error message

    def __init__(
        self, 
        bridge: AnalyzerBridge, 
        data: list[float],
        sensor_type: str = "GENERIC",
        sampling_rate: float = 1.0,
    ):
        super().__init__()
        self.bridge = bridge
        self.data = data
        self.sensor_type = sensor_type
        self.sampling_rate = sampling_rate

    def run(self):
        try:
            logger.info(f"Starting analysis in worker thread with {len(self.data)} data points...")
            logger.info(f"Sensor type: {self.sensor_type}, Sampling rate: {self.sampling_rate}Hz")
            logger.info(f"Data sample (first 5): {self.data[:5] if len(self.data) >= 5 else self.data}")
            result = self.bridge.analyze_sensor_data(
                self.data, 
                sensor_type=self.sensor_type,
                sampling_rate=self.sampling_rate,
            )

            if "error" in result:
                self.error.emit(result["error"])
            else:
                self.finished.emit(result)

        except Exception as e:
            logger.error(f"Worker thread exception: {e}")
            self.error.emit(str(e))

