from PyQt6.QtCore import QThread, pyqtSignal, QObject
from typing import List, Dict, Any
import logging
from desktop_app.core.analyzer_bridge import AnalyzerBridge

logger = logging.getLogger("AnalysisWorker")

class AnalysisWorker(QThread):
    """
    Background worker thread for running heavy analysis.
    Emits signals upon completion or error.
    """
    finished = pyqtSignal(dict) # Emits the result dictionary
    error = pyqtSignal(str)     # Emits error message

    def __init__(self, bridge: AnalyzerBridge, data: List[float]):
        super().__init__()
        self.bridge = bridge
        self.data = data

    def run(self):
        try:
            logger.info(f"Starting analysis in worker thread with {len(self.data)} data points...")
            logger.info(f"Data sample (first 5): {self.data[:5] if len(self.data) >= 5 else self.data}")
            result = self.bridge.analyze_sensor_data(self.data)
            
            if "error" in result:
                self.error.emit(result["error"])
            else:
                self.finished.emit(result)
                
        except Exception as e:
            logger.error(f"Worker thread exception: {e}")
            self.error.emit(str(e))
