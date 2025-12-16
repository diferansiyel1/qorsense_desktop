from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSplitter
from PyQt6.QtCore import Qt
import pyqtgraph as pg

class OscilloscopeWidget(pg.PlotWidget):
    def __init__(self, parent=None, max_points: int = 300):
        super().__init__(parent=parent, title="Raw Sensor Signal (Oscilloscope Mode)")
        self.setBackground('#1e1e1e')
        self.showGrid(x=True, y=True, alpha=0.3)
        self.setLabel('left', 'Amplitude', units='V')
        self.setLabel('bottom', 'Time', units='s')
        self.curve = self.plot(pen=pg.mkPen(color='#00ffff', width=2, style=Qt.PenStyle.SolidLine))
        
        # Real-time buffer
        self.max_points = max_points
        self.data_buffer = []
        self.time_buffer = []
        
    def update_data(self, data, x=None):
        """Update with full dataset (batch mode)."""
        if x is not None:
             self.curve.setData(x=x, y=data)
        else:
             self.curve.setData(data)
    
    def update_realtime(self, value: float, timestamp: float = None):
        """
        Add a single data point for real-time scrolling display.
        Data scrolls from right to left.
        
        Args:
            value: New data point value
            timestamp: Optional timestamp (uses buffer index if not provided)
        """
        import time as _time
        
        # Add new point to buffer
        self.data_buffer.append(value)
        if timestamp is not None:
            self.time_buffer.append(timestamp)
        else:
            self.time_buffer.append(len(self.data_buffer))
        
        # Keep buffer size limited (scrolling window)
        if len(self.data_buffer) > self.max_points:
            self.data_buffer = self.data_buffer[-self.max_points:]
            self.time_buffer = self.time_buffer[-self.max_points:]
        
        # Update plot with relative time (0 = oldest, max = newest)
        if self.time_buffer:
            # Normalize time to start from 0
            t0 = self.time_buffer[0]
            relative_time = [t - t0 for t in self.time_buffer]
            self.curve.setData(x=relative_time, y=self.data_buffer)
        else:
            self.curve.setData(self.data_buffer)
    
    def clear_realtime_buffer(self):
        """Clear the real-time data buffer."""
        self.data_buffer = []
        self.time_buffer = []
        self.curve.setData([], [])
    
    def get_buffer_data(self) -> list:
        """Return copy of current buffer data for analysis."""
        return list(self.data_buffer)

class TrendWidget(pg.PlotWidget):
    def __init__(self, parent=None):
        super().__init__(parent=parent, title="DFA Trend Analysis & Residuals")
        self.setBackground('#1e1e1e')
        self.showGrid(x=True, y=True, alpha=0.3)
        self.legend = self.addLegend()
        self.curve_trend = None
        self.curve_resid = None
        
    def update_data(self, trend, residuals):
        import logging
        logger = logging.getLogger("TrendWidget")
        logger.info(f"TrendWidget.update_data called with trend length={len(trend) if trend else 0}, residuals length={len(residuals) if residuals else 0}")
        if trend:
            logger.info(f"Trend first 3: {trend[:3]}")
        
        # Get the PlotItem and clear it completely
        plot_item = self.getPlotItem()
        plot_item.clear()
        
        # Reset curves
        self.curve_trend = None
        self.curve_resid = None
        
        # Re-add legend
        if self.legend:
            self.legend.clear()
        
        # Plot new data if available
        if trend:
            self.curve_trend = self.plot(trend, name="Trend", pen=pg.mkPen(color='#ffae00', width=3))
            logger.info(f"Plotted trend curve: {self.curve_trend}")
        if residuals:
            self.curve_resid = self.plot(residuals, name="Residuals", pen=pg.mkPen(color='#32c850', width=1, style=Qt.PenStyle.DotLine))
            
        # Force axis rescale to fit new data
        self.autoRange()
        
        # Force scene and viewport invalidation
        scene = self.scene()
        if scene:
            scene.update()
        
        # Force viewport update
        viewport = self.viewport()
        if viewport:
            viewport.update()
        
        logger.info("TrendWidget.update_data completed")

    def clear(self):
        """Clear all plots and reset widget"""
        plot_item = self.getPlotItem()
        plot_item.clear()
        self.curve_trend = None
        self.curve_resid = None
        if self.legend:
            self.legend.clear()
        
        # Force update
        self.repaint()
        self.update()

class AnalysisDashboard(QWidget):
    """Combines the two charts into a split view."""
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        
        self.oscilloscope = OscilloscopeWidget()
        self.trend_view = TrendWidget()
        
        self.splitter.addWidget(self.oscilloscope)
        self.splitter.addWidget(self.trend_view)
        
        layout.addWidget(self.splitter)
