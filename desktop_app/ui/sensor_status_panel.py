"""
Sensor Status Panel for Multi-Sensor Monitoring.

Displays real-time status of all connected sensors with:
- Color-coded status indicators (Online/Offline/Reconnecting)
- Latest value display
- Click to select sensor for health analysis
"""
from PyQt6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPalette

from typing import Dict, Optional


class SensorStatusItem(QFrame):
    """
    Individual sensor status item showing:
    - Status indicator (colored dot)
    - Sensor name
    - Latest value
    - Status text (Online/Offline/Reconnecting)
    """
    
    clicked = pyqtSignal(str)  # Emits sensor_id when clicked
    
    # Status colors
    COLORS = {
        'online': '#22c55e',      # Green
        'offline': '#ef4444',     # Red
        'reconnecting': '#f59e0b', # Yellow/Orange
        'unknown': '#6b7280'      # Gray
    }
    
    def __init__(self, sensor_id: str, display_name: str = None, parent=None):
        super().__init__(parent)
        self.sensor_id = sensor_id
        self.display_name = display_name or sensor_id
        self._status = 'unknown'
        self._value = None
        self._unit = ''
        self._selected = False
        
        self._setup_ui()
        self._apply_style()
    
    def _setup_ui(self):
        """Initialize UI components."""
        self.setFixedHeight(50)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        layout.setSpacing(10)
        
        # Status indicator (colored circle)
        self.status_dot = QLabel("●")
        self.status_dot.setFixedWidth(20)
        self.status_dot.setFont(QFont("Arial", 14))
        layout.addWidget(self.status_dot)
        
        # Sensor name
        self.name_label = QLabel(self.display_name)
        self.name_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Medium))
        self.name_label.setMinimumWidth(120)
        layout.addWidget(self.name_label, 1)
        
        # Value display
        self.value_label = QLabel("---")
        self.value_label.setFont(QFont("Consolas", 12, QFont.Weight.Bold))
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.value_label.setMinimumWidth(80)
        layout.addWidget(self.value_label)
        
        # Status text
        self.status_label = QLabel("UNKNOWN")
        self.status_label.setFont(QFont("Segoe UI", 9))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.status_label.setMinimumWidth(90)
        layout.addWidget(self.status_label)
    
    def _apply_style(self):
        """Apply dark theme styling."""
        self.setStyleSheet(f"""
            SensorStatusItem {{
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
            }}
            SensorStatusItem:hover {{
                background-color: #3d3d3d;
                border-color: #4d4d4d;
            }}
            QLabel {{
                color: #e0e0e0;
            }}
        """)
        self._update_status_color()
    
    def _update_status_color(self):
        """Update status indicator and text colors."""
        color = self.COLORS.get(self._status, self.COLORS['unknown'])
        self.status_dot.setStyleSheet(f"color: {color};")
        self.status_label.setStyleSheet(f"color: {color};")
    
    def set_status(self, status: str):
        """
        Set sensor status.
        
        Args:
            status: 'online', 'offline', 'reconnecting', or 'unknown'
        """
        self._status = status.lower()
        self.status_label.setText(status.upper())
        self._update_status_color()
    
    def set_value(self, value: float, unit: str = ''):
        """
        Update displayed value.
        
        Args:
            value: Sensor value
            unit: Unit string (e.g., 'pH', '°C')
        """
        self._value = value
        self._unit = unit
        if value is not None:
            self.value_label.setText(f"{value:.2f} {unit}".strip())
        else:
            self.value_label.setText("---")
    
    def set_selected(self, selected: bool):
        """Highlight as selected sensor."""
        self._selected = selected
        if selected:
            self.setStyleSheet(f"""
                SensorStatusItem {{
                    background-color: #1e3a5f;
                    border: 2px solid #3b82f6;
                    border-radius: 6px;
                }}
                QLabel {{
                    color: #e0e0e0;
                }}
            """)
        else:
            self._apply_style()
        self._update_status_color()
    
    def mousePressEvent(self, event):
        """Emit clicked signal on click."""
        self.clicked.emit(self.sensor_id)
        super().mousePressEvent(event)


class SensorStatusPanel(QDockWidget):
    """
    Dock panel showing status of all connected sensors.
    
    Signals:
        sensor_selected(str): Emitted when a sensor is clicked
    """
    
    sensor_selected = pyqtSignal(str)  # sensor_id
    
    def __init__(self, parent=None):
        super().__init__("Sensor Status", parent)
        self.setAllowedAreas(
            Qt.DockWidgetArea.LeftDockWidgetArea | 
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        
        self._sensors: Dict[str, SensorStatusItem] = {}
        self._selected_sensor: Optional[str] = None
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Initialize panel UI."""
        # Main container
        container = QWidget()
        container.setStyleSheet("background-color: #1e1e1e;")
        
        main_layout = QVBoxLayout(container)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Header
        header = QLabel("📡 Live Sensors")
        header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        header.setStyleSheet("color: #ffffff; padding: 5px;")
        main_layout.addWidget(header)
        
        # Scrollable sensor list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
        """)
        
        self._sensor_container = QWidget()
        self._sensor_layout = QVBoxLayout(self._sensor_container)
        self._sensor_layout.setContentsMargins(0, 0, 0, 0)
        self._sensor_layout.setSpacing(5)
        self._sensor_layout.addStretch()
        
        scroll.setWidget(self._sensor_container)
        main_layout.addWidget(scroll, 1)
        
        self.setWidget(container)
    
    def add_sensor(
        self, 
        sensor_id: str, 
        display_name: str = None,
        unit: str = ''
    ) -> None:
        """
        Add a sensor to the panel.
        
        Args:
            sensor_id: Unique sensor identifier
            display_name: Human-readable name
            unit: Value unit string
        """
        if sensor_id in self._sensors:
            return
        
        item = SensorStatusItem(sensor_id, display_name)
        item.clicked.connect(self._on_sensor_clicked)
        item._unit = unit
        
        # Insert before stretch
        self._sensor_layout.insertWidget(
            self._sensor_layout.count() - 1, 
            item
        )
        self._sensors[sensor_id] = item
    
    def remove_sensor(self, sensor_id: str) -> bool:
        """Remove sensor from panel."""
        if sensor_id not in self._sensors:
            return False
        
        item = self._sensors[sensor_id]
        self._sensor_layout.removeWidget(item)
        item.deleteLater()
        del self._sensors[sensor_id]
        return True
    
    def update_sensor(
        self, 
        sensor_id: str, 
        value: float = None, 
        status: str = None
    ) -> None:
        """
        Update sensor value and/or status.
        
        Args:
            sensor_id: Sensor identifier
            value: New value (None to keep current)
            status: New status (None to keep current)
        """
        if sensor_id not in self._sensors:
            return
        
        item = self._sensors[sensor_id]
        if value is not None:
            item.set_value(value, item._unit)
        if status is not None:
            item.set_status(status)
    
    def set_sensor_status(self, sensor_id: str, status: str) -> None:
        """Set sensor status."""
        if sensor_id in self._sensors:
            self._sensors[sensor_id].set_status(status)
    
    def get_selected_sensor(self) -> Optional[str]:
        """Get currently selected sensor ID."""
        return self._selected_sensor
    
    def select_sensor(self, sensor_id: str) -> None:
        """Programmatically select a sensor."""
        self._on_sensor_clicked(sensor_id)
    
    def clear_all(self) -> None:
        """Remove all sensors from panel."""
        for sensor_id in list(self._sensors.keys()):
            self.remove_sensor(sensor_id)
    
    def _on_sensor_clicked(self, sensor_id: str) -> None:
        """Handle sensor item click."""
        # Deselect previous
        if self._selected_sensor and self._selected_sensor in self._sensors:
            self._sensors[self._selected_sensor].set_selected(False)
        
        # Select new
        self._selected_sensor = sensor_id
        if sensor_id in self._sensors:
            self._sensors[sensor_id].set_selected(True)
        
        self.sensor_selected.emit(sensor_id)
