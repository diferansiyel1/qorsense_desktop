"""
Metadata Dialog for QorSense Desktop Application.

Provides modal dialog for collecting sensor metadata during data ingestion:
- Sensor Type (pH, Viscosity, Flow, etc.)
- Sampling Rate (Hz)
- Unit (context-sensitive)
"""

import logging
from typing import NamedTuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QVBoxLayout,
)

logger = logging.getLogger("MetadataDialog")


class SensorMetadata(NamedTuple):
    """Result from MetadataDialog."""
    sensor_type: str
    sampling_rate: float
    unit: str


# Sensor type options with default units
SENSOR_OPTIONS = {
    "pH": {"default_unit": "pH", "units": ["pH"]},
    "Dissolved Oxygen": {"default_unit": "mg/L", "units": ["mg/L", "%sat", "ppm"]},
    "Viscosity": {"default_unit": "cP", "units": ["cP", "mPa·s", "Pa·s"]},
    "Flow (Mag)": {"default_unit": "m³/h", "units": ["m³/h", "L/min", "GPM"]},
    "Flow (Coriolis)": {"default_unit": "kg/h", "units": ["kg/h", "kg/min", "m³/h"]},
    "Temperature": {"default_unit": "°C", "units": ["°C", "°F", "K"]},
    "Pressure": {"default_unit": "bar", "units": ["bar", "psi", "kPa", "mbar"]},
    "Conductivity": {"default_unit": "µS/cm", "units": ["µS/cm", "mS/cm", "S/m"]},
    "Generic / Other": {"default_unit": "mA", "units": ["mA", "V", "units"]},
}


class MetadataDialog(QDialog):
    """
    Modal dialog for collecting sensor metadata before analysis.
    
    This dialog is shown when loading data that lacks sensor configuration.
    It ensures that sensor_type, sampling_rate, and unit are defined before
    analysis proceeds.
    
    Example:
        dialog = MetadataDialog(parent)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            metadata = dialog.get_metadata()
            print(f"Sensor: {metadata.sensor_type}")
    """
    
    def __init__(self, parent=None, filename: str = ""):
        """
        Initialize the MetadataDialog.
        
        Args:
            parent: Parent widget
            filename: Name of the file being loaded (for display)
        """
        super().__init__(parent)
        self.setWindowTitle("Sensor Configuration Required")
        self.setMinimumWidth(400)
        self.setModal(True)
        
        self._filename = filename
        self._setup_ui()
        
    def _setup_ui(self):
        """Build the dialog UI."""
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        
        # === Header ===
        header = QLabel(
            "<h3>⚙️ Sensor Configuration</h3>"
            "<p style='color: #888;'>Please provide sensor details for accurate analysis.</p>"
        )
        header.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(header)
        
        # Show filename if provided
        if self._filename:
            file_label = QLabel(f"<b>File:</b> {self._filename}")
            file_label.setStyleSheet("color: #4FC3F7; padding: 8px; background: #1e1e1e; border-radius: 4px;")
            layout.addWidget(file_label)
        
        # === Configuration Group ===
        config_group = QGroupBox("Sensor Details")
        config_layout = QFormLayout(config_group)
        config_layout.setSpacing(12)
        
        # Sensor Type dropdown
        self._sensor_type_combo = QComboBox()
        self._sensor_type_combo.addItems(list(SENSOR_OPTIONS.keys()))
        self._sensor_type_combo.setCurrentText("Generic / Other")
        self._sensor_type_combo.currentTextChanged.connect(self._on_sensor_type_changed)
        config_layout.addRow("Sensor Type:", self._sensor_type_combo)
        
        # Sampling Rate
        self._sampling_rate_spin = QDoubleSpinBox()
        self._sampling_rate_spin.setRange(0.001, 10000.0)
        self._sampling_rate_spin.setValue(1.0)
        self._sampling_rate_spin.setDecimals(3)
        self._sampling_rate_spin.setSuffix(" Hz")
        self._sampling_rate_spin.setToolTip("Data sampling frequency (samples per second)")
        config_layout.addRow("Sampling Rate:", self._sampling_rate_spin)
        
        # Unit dropdown (updates based on sensor type)
        self._unit_combo = QComboBox()
        self._update_units_for_sensor("Generic / Other")
        config_layout.addRow("Unit:", self._unit_combo)
        
        layout.addWidget(config_group)
        
        # === Info Box ===
        info_label = QLabel(
            "<p style='color: #FFB74D;'>"
            "ℹ️ <b>Why is this needed?</b> Different sensor types have different "
            "failure modes. For example, 'chaos' in a viscometer indicates mechanical "
            "failure, while in a pH probe it indicates cracked glass."
            "</p>"
        )
        info_label.setWordWrap(True)
        info_label.setTextFormat(Qt.TextFormat.RichText)
        info_label.setStyleSheet("padding: 12px; background: #2d2d2d; border-radius: 4px;")
        layout.addWidget(info_label)
        
        # === Buttons ===
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Style the OK button
        ok_button = button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_button.setText("Start Analysis")
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 8px 24px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #66BB6A;
            }
        """)
        
        layout.addWidget(button_box)
    
    def _on_sensor_type_changed(self, sensor_type: str):
        """Update available units when sensor type changes."""
        self._update_units_for_sensor(sensor_type)
    
    def _update_units_for_sensor(self, sensor_type: str):
        """Update the units dropdown based on selected sensor type."""
        self._unit_combo.clear()
        
        if sensor_type in SENSOR_OPTIONS:
            options = SENSOR_OPTIONS[sensor_type]
            self._unit_combo.addItems(options["units"])
            self._unit_combo.setCurrentText(options["default_unit"])
        else:
            self._unit_combo.addItems(["units"])
    
    def get_metadata(self) -> SensorMetadata:
        """
        Get the configured sensor metadata.
        
        Returns:
            SensorMetadata with sensor_type, sampling_rate, and unit
        """
        sensor_type_display = self._sensor_type_combo.currentText()
        
        # Convert display name to profile key
        type_mapping = {
            "pH": "PH",
            "Dissolved Oxygen": "DO",
            "Viscosity": "VISCOSITY",
            "Flow (Mag)": "FLOW_MAG",
            "Flow (Coriolis)": "FLOW_CORIOLIS",
            "Temperature": "TEMP",
            "Pressure": "PRESSURE",
            "Conductivity": "CONDUCTIVITY",
            "Generic / Other": "GENERIC",
        }
        
        sensor_type = type_mapping.get(sensor_type_display, "GENERIC")
        
        return SensorMetadata(
            sensor_type=sensor_type,
            sampling_rate=self._sampling_rate_spin.value(),
            unit=self._unit_combo.currentText(),
        )
    
    def set_defaults(
        self, 
        sensor_type: str = "GENERIC", 
        sampling_rate: float = 1.0, 
        unit: str = ""
    ):
        """
        Set default values for the dialog fields.
        
        Args:
            sensor_type: Sensor type key (e.g., "PH", "VISCOSITY")
            sampling_rate: Sampling rate in Hz
            unit: Unit string
        """
        # Reverse mapping for display
        display_mapping = {
            "PH": "pH",
            "DO": "Dissolved Oxygen",
            "VISCOSITY": "Viscosity",
            "FLOW_MAG": "Flow (Mag)",
            "FLOW_CORIOLIS": "Flow (Coriolis)",
            "TEMP": "Temperature",
            "PRESSURE": "Pressure",
            "CONDUCTIVITY": "Conductivity",
            "GENERIC": "Generic / Other",
        }
        
        display_name = display_mapping.get(sensor_type.upper(), "Generic / Other")
        
        # Set sensor type
        idx = self._sensor_type_combo.findText(display_name)
        if idx >= 0:
            self._sensor_type_combo.setCurrentIndex(idx)
        
        # Set sampling rate
        self._sampling_rate_spin.setValue(sampling_rate)
        
        # Set unit if provided
        if unit:
            idx = self._unit_combo.findText(unit)
            if idx >= 0:
                self._unit_combo.setCurrentIndex(idx)
