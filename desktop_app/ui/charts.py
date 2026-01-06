import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QSplitter, QVBoxLayout, QWidget


class OscilloscopeWidget(pg.PlotWidget):
    def __init__(self, parent=None, max_points: int = 300, y_unit: str = "V", y_label: str = "Amplitude"):
        super().__init__(parent=parent, title="Raw Sensor Signal (Oscilloscope Mode)")
        self.setBackground('#1e1e1e')
        self.showGrid(x=True, y=True, alpha=0.3)
        self._y_unit = y_unit
        self._y_label = y_label
        self.setLabel('left', y_label, units=y_unit)
        self.setLabel('bottom', 'Time', units='s')
        self.curve = self.plot(pen=pg.mkPen(color='#00ffff', width=2, style=Qt.PenStyle.SolidLine))

        # Real-time buffer
        self.max_points = max_points
        self.data_buffer = []
        self.time_buffer = []

    def set_y_unit(self, unit: str, label: str = None):
        """
        Update the Y-axis unit and optionally the label.
        
        Args:
            unit: The unit string (e.g., 'V', '°C', 'mg/L')
            label: Optional label text (e.g., 'Temperature', 'Dissolved Oxygen')
        """
        self._y_unit = unit
        if label is not None:
            self._y_label = label
        self.setLabel('left', self._y_label, units=self._y_unit)

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


class MultiSensorOscilloscope(pg.PlotWidget):
    """
    Multi-sensor oscilloscope with separate traces for each sensor.
    
    Features:
    - Unique color per sensor
    - Legend with sensor names
    - Independent data buffers per sensor
    - Per-sensor unit display on Y-axis
    - Click to select sensor
    
    Example:
        >>> scope = MultiSensorOscilloscope(max_points=300)
        >>> scope.add_sensor("ph_sensor", "pH Sensor", unit="pH")
        >>> scope.add_sensor("temperature", "Temperature", unit="°C")
        >>> scope.update_sensor("ph_sensor", 7.12, time.time())
    """

    # Predefined color palette for sensors
    COLORS = [
        '#00ffff',  # Cyan
        '#ff6b6b',  # Red/Pink
        '#4ecdc4',  # Teal
        '#ffbe0b',  # Yellow
        '#fb5607',  # Orange
        '#a855f7',  # Purple
        '#22c55e',  # Green
        '#3b82f6',  # Blue
    ]

    def __init__(self, parent=None, max_points: int = 300):
        """
        Initialize multi-sensor oscilloscope.
        
        Args:
            parent: Parent widget
            max_points: Maximum points per sensor buffer
        """
        super().__init__(parent=parent, title="Multi-Sensor Live Data")
        self.setBackground('#1e1e1e')
        self.showGrid(x=True, y=True, alpha=0.3)
        self._current_y_label = 'Value'
        self._current_y_unit = ''
        self.setLabel('left', self._current_y_label)
        self.setLabel('bottom', 'Time', units='s')

        self.max_points = max_points
        self.sensors: dict = {}  # {sensor_id: {curve, data, time, color, name, unit}}
        self._color_index = 0
        self._selected_sensor_id = None  # For Y-label display

        # Add legend
        self.legend = self.addLegend(offset=(10, 10))

        # Enable mouse tracking for tooltips
        self.setMouseEnabled(x=True, y=True)

    def add_sensor(self, sensor_id: str, display_name: str = None, color: str = None, unit: str = "") -> None:
        """
        Add a new sensor trace to the graph.
        
        Args:
            sensor_id: Unique sensor identifier
            display_name: Name shown in legend (defaults to sensor_id)
            color: Hex color code (auto-assigned if None)
            unit: Unit for this sensor's values (e.g., '°C', 'mg/L', 'bar')
        """
        if sensor_id in self.sensors:
            return  # Already exists

        # Assign color
        if color is None:
            color = self.COLORS[self._color_index % len(self.COLORS)]
            self._color_index += 1

        # Create curve
        name = display_name or sensor_id
        curve = self.plot(
            [], [],
            pen=pg.mkPen(color=color, width=2),
            name=name
        )

        # Store sensor info with unit
        self.sensors[sensor_id] = {
            'curve': curve,
            'data': [],
            'time': [],
            'color': color,
            'name': name,
            'unit': unit
        }

        # Update Y-label if this is the first sensor or selected
        if len(self.sensors) == 1:
            self._selected_sensor_id = sensor_id
            self._update_y_label_for_sensor(sensor_id)

    def update_sensor(self, sensor_id: str, value: float, timestamp: float = None) -> None:
        """
        Update a specific sensor's data.
        
        Args:
            sensor_id: Sensor identifier
            value: New data value
            timestamp: Unix timestamp (uses monotonic if None)
        """
        if sensor_id not in self.sensors:
            # Auto-add sensor if not exists
            self.add_sensor(sensor_id)

        sensor = self.sensors[sensor_id]

        # Add to buffers
        sensor['data'].append(value)
        if timestamp is not None:
            sensor['time'].append(timestamp)
        else:
            import time
            sensor['time'].append(time.time())

        # Limit buffer size
        if len(sensor['data']) > self.max_points:
            sensor['data'] = sensor['data'][-self.max_points:]
            sensor['time'] = sensor['time'][-self.max_points:]

        # Update curve with relative time
        if sensor['time']:
            t0 = sensor['time'][0]
            rel_time = [t - t0 for t in sensor['time']]
            sensor['curve'].setData(x=rel_time, y=sensor['data'])

    def remove_sensor(self, sensor_id: str) -> bool:
        """
        Remove sensor trace from graph.
        
        Args:
            sensor_id: Sensor identifier
            
        Returns:
            True if removed, False if not found
        """
        if sensor_id not in self.sensors:
            return False

        sensor = self.sensors[sensor_id]
        self.removeItem(sensor['curve'])
        del self.sensors[sensor_id]
        return True

    def clear_sensor(self, sensor_id: str) -> None:
        """Clear data buffer for a specific sensor."""
        if sensor_id in self.sensors:
            sensor = self.sensors[sensor_id]
            sensor['data'] = []
            sensor['time'] = []
            sensor['curve'].setData([], [])

    def clear_all(self) -> None:
        """Clear all sensor data buffers."""
        for sensor_id in self.sensors:
            self.clear_sensor(sensor_id)

    def get_sensor_data(self, sensor_id: str) -> list:
        """Get copy of sensor's data buffer."""
        if sensor_id in self.sensors:
            return list(self.sensors[sensor_id]['data'])
        return []

    def get_all_sensor_ids(self) -> list:
        """Get list of all sensor IDs."""
        return list(self.sensors.keys())

    def set_sensor_visible(self, sensor_id: str, visible: bool) -> None:
        """Show/hide a sensor trace."""
        if sensor_id in self.sensors:
            self.sensors[sensor_id]['curve'].setVisible(visible)

    def select_sensor(self, sensor_id: str) -> None:
        """
        Select a sensor to display its unit on Y-axis.
        
        Args:
            sensor_id: Sensor identifier to select
        """
        if sensor_id in self.sensors:
            self._selected_sensor_id = sensor_id
            self._update_y_label_for_sensor(sensor_id)

    def _update_y_label_for_sensor(self, sensor_id: str) -> None:
        """
        Update Y-axis label based on selected sensor's unit.
        
        Args:
            sensor_id: Sensor identifier
        """
        if sensor_id not in self.sensors:
            return
        
        sensor = self.sensors[sensor_id]
        unit = sensor.get('unit', '')
        name = sensor.get('name', 'Value')
        
        if unit:
            self.setLabel('left', name, units=unit)
            self._current_y_label = name
            self._current_y_unit = unit
        else:
            self.setLabel('left', name)
            self._current_y_label = name
            self._current_y_unit = ''

    def set_y_unit(self, unit: str, label: str = "Value") -> None:
        """
        Manually set Y-axis unit and label.
        
        Args:
            unit: Unit string (e.g., 'V', '°C', 'mg/L')
            label: Label text
        """
        self._current_y_label = label
        self._current_y_unit = unit
        if unit:
            self.setLabel('left', label, units=unit)
        else:
            self.setLabel('left', label)



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
