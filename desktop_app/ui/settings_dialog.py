"""
Settings Dialog for QorSense Desktop Application.

Provides configuration UI for:
- Easy Mode: Operator-friendly sensor profile selection and sensitivity
- Expert Mode: Advanced threshold fine-tuning and profile editing
- Auto-Encoder learning reset
"""

import logging
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSlider,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger("SettingsDialog")


# Available sensor profiles (matches SENSOR_PROFILES in analysis.py)
SENSOR_PROFILE_OPTIONS = [
    "Generic",
    "pH",
    "Dissolved Oxygen",
    "Viscosity",
    "Flow (Mag)",
    "Flow (Coriolis)",
    "Temperature",
    "Pressure",
    "Conductivity",
]


class EasyModeTab(QWidget):
    """Easy Mode (Operator View) for simplified configuration."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_sensitivity = 0  # -1 (Low), 0 (Medium), +1 (High)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = QLabel(
            "<h2>🎯 Easy Mode</h2>"
            "<p style='color: #888;'>Simple controls for operators. "
            "Adjust sensitivity and select sensor profile.</p>"
        )
        header.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(header)
        
        # === Sensor Profile Group ===
        profile_group = QGroupBox("Active Sensor Profile")
        profile_layout = QFormLayout(profile_group)
        
        self._profile_combo = QComboBox()
        self._profile_combo.addItems(SENSOR_PROFILE_OPTIONS)
        self._profile_combo.setCurrentText("Generic")
        self._profile_combo.setToolTip(
            "Select the type of sensor being monitored.\n"
            "This affects how diagnosis interprets anomalies."
        )
        profile_layout.addRow("Sensor Type:", self._profile_combo)
        
        layout.addWidget(profile_group)
        
        # === Sensitivity Group ===
        sensitivity_group = QGroupBox("Detection Sensitivity")
        sensitivity_layout = QVBoxLayout(sensitivity_group)
        
        # Description
        sens_desc = QLabel(
            "Adjust how sensitive the analysis is to anomalies. "
            "Low = fewer alerts (may miss issues), High = more alerts (may cause false alarms)."
        )
        sens_desc.setWordWrap(True)
        sens_desc.setStyleSheet("color: #999; font-size: 11px;")
        sensitivity_layout.addWidget(sens_desc)
        
        # Slider with labels
        slider_row = QHBoxLayout()
        
        low_label = QLabel("Low\n(-10%)")
        low_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        low_label.setStyleSheet("color: #64b5f6;")
        slider_row.addWidget(low_label)
        
        self._sensitivity_slider = QSlider(Qt.Orientation.Horizontal)
        self._sensitivity_slider.setRange(-10, 10)  # Smooth range for dragging
        self._sensitivity_slider.setValue(0)
        self._sensitivity_slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self._sensitivity_slider.setTickInterval(5)
        self._sensitivity_slider.setStyleSheet("""
            QSlider::groove:horizontal {
                height: 8px;
                background: #333;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background: #4CAF50;
                width: 20px;
                margin: -6px 0;
                border-radius: 10px;
            }
            QSlider::sub-page:horizontal {
                background: #4CAF50;
                border-radius: 4px;
            }
        """)
        self._sensitivity_slider.valueChanged.connect(self._on_sensitivity_changed)
        slider_row.addWidget(self._sensitivity_slider, stretch=1)
        
        high_label = QLabel("High\n(+10%)")
        high_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        high_label.setStyleSheet("color: #ef5350;")
        slider_row.addWidget(high_label)
        
        sensitivity_layout.addLayout(slider_row)
        
        # Current value display
        self._sensitivity_value_label = QLabel("Current: Normal (0%)")
        self._sensitivity_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._sensitivity_value_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        sensitivity_layout.addWidget(self._sensitivity_value_label)
        
        layout.addWidget(sensitivity_group)
        
        # === Auto-Encoder Group ===
        ae_group = QGroupBox("Auto-Encoder Learning")
        ae_layout = QVBoxLayout(ae_group)
        
        ae_desc = QLabel(
            "The AI learns 'normal' sensor behavior from the first 500 data points. "
            "Reset if the sensor baseline has changed."
        )
        ae_desc.setWordWrap(True)
        ae_desc.setStyleSheet("color: #999; font-size: 11px;")
        ae_layout.addWidget(ae_desc)
        
        self._btn_reset_learning = QPushButton("🔄 Reset Learning")
        self._btn_reset_learning.setMinimumHeight(40)
        self._btn_reset_learning.setStyleSheet("""
            QPushButton {
                background-color: #7c3aed;
                color: white;
                font-size: 13px;
                font-weight: bold;
                border-radius: 6px;
            }
            QPushButton:hover { background-color: #8b5cf6; }
            QPushButton:pressed { background-color: #6d28d9; }
        """)
        self._btn_reset_learning.clicked.connect(self._on_reset_learning)
        ae_layout.addWidget(self._btn_reset_learning)
        
        layout.addWidget(ae_group)
        
        layout.addStretch()
    
    def _on_sensitivity_changed(self, value: int):
        """Update sensitivity display when slider changes."""
        self._current_sensitivity = value
        
        # Map -10..+10 slider value to percentage
        percent = value  # Direct 1:1 mapping
        
        if value < 0:
            text = f"Lower ({percent}%)"
            color = "#64b5f6"
        elif value > 0:
            text = f"Higher (+{percent}%)"
            color = "#ef5350"
        else:
            text = "Normal (0%)"
            color = "#4CAF50"
        
        self._sensitivity_value_label.setText(f"Current: {text}")
        self._sensitivity_value_label.setStyleSheet(f"color: {color}; font-weight: bold;")
    
    def _on_reset_learning(self):
        """Reset the Auto-Encoder model."""
        try:
            from backend.analysis import reset_ae_model
            reset_ae_model()
            
            QMessageBox.information(
                self,
                "Learning Reset",
                "Auto-Encoder model has been reset.\n"
                "It will learn new 'normal' behavior from the next analysis."
            )
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset model: {e}")
    
    def get_settings(self) -> dict[str, Any]:
        """Get Easy Mode settings."""
        # Map display name to profile key
        profile_map = {
            "Generic": "GENERIC",
            "pH": "PH",
            "Dissolved Oxygen": "DO",
            "Viscosity": "VISCOSITY",
            "Flow (Mag)": "FLOW_MAG",
            "Flow (Coriolis)": "FLOW_CORIOLIS",
            "Temperature": "TEMP",
            "Pressure": "PRESSURE",
            "Conductivity": "CONDUCTIVITY",
        }
        
        return {
            "sensor_profile": profile_map.get(self._profile_combo.currentText(), "GENERIC"),
            "sensitivity_modifier": self._current_sensitivity * 0.10,  # -0.1, 0, or +0.1
        }


class ExpertModeTab(QWidget):
    """Expert Mode (Engineer View) for advanced configuration."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self._load_thresholds()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        header = QLabel(
            "<h2>🔧 Expert Mode</h2>"
            "<p style='color: #888;'>Advanced threshold tuning for engineers.</p>"
        )
        header.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(header)
        
        # Warning
        warning = QLabel(
            "⚠️ Modifying these values may affect diagnosis accuracy. "
            "Use caution."
        )
        warning.setStyleSheet(
            "color: #FFB74D; padding: 8px; background: #3d3d00; "
            "border-radius: 4px; font-size: 11px;"
        )
        warning.setWordWrap(True)
        layout.addWidget(warning)
        
        # === Threshold Table ===
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Parameter", "Default", "Current"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setStyleSheet("""
            QTableWidget {
                background-color: #252525;
                gridline-color: #444;
                color: white;
            }
            QHeaderView::section {
                background-color: #333;
                color: white;
                padding: 5px;
                border: 1px solid #444;
            }
            QTableWidget::item {
                padding: 5px;
            }
        """)
        layout.addWidget(self.table)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_reset = QPushButton("🔄 Reset to Factory")
        self.btn_reset.setStyleSheet("""
            QPushButton {
                background-color: #cc5500;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #dd6611; }
        """)
        self.btn_reset.clicked.connect(self._on_reset_factory)
        btn_layout.addWidget(self.btn_reset)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
    
    def _load_thresholds(self):
        """Load thresholds from ThresholdManager."""
        defaults = {}
        factory = {}
        
        try:
            from backend.core.config import threshold_manager
            defaults = threshold_manager.get_all_defaults()
            factory = threshold_manager.FACTORY_DEFAULTS.get("defaults", {})
            logger.info(f"Loaded {len(defaults)} thresholds from manager")
        except Exception as e:
            logger.error(f"Failed to load ThresholdManager: {e}")
            # Use fallback from DiagnosisEngine
            from backend.analysis import DiagnosisEngine
            defaults = DiagnosisEngine.DEFAULT_THRESHOLDS.copy()
            factory = defaults.copy()
        
        if not defaults:
            logger.warning("No defaults found, using DiagnosisEngine defaults")
            from backend.analysis import DiagnosisEngine
            defaults = DiagnosisEngine.DEFAULT_THRESHOLDS.copy()
            factory = defaults.copy()
        
        self.table.setRowCount(len(defaults))
        
        for row, (key, value) in enumerate(sorted(defaults.items())):
            # Parameter name
            name_item = QTableWidgetItem(key)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, name_item)
            
            # Factory default
            factory_val = factory.get(key, "-")
            default_item = QTableWidgetItem(str(factory_val))
            default_item.setFlags(default_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            default_item.setForeground(Qt.GlobalColor.gray)
            self.table.setItem(row, 1, default_item)
            
            # Current value (editable)
            current_item = QTableWidgetItem(str(value))
            self.table.setItem(row, 2, current_item)
        
        self.table.resizeColumnsToContents()
    
    def _on_reset_factory(self):
        """Reset thresholds to factory defaults."""
        reply = QMessageBox.question(
            self,
            "Reset to Factory",
            "Are you sure you want to reset all thresholds to factory defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                from backend.core.config import threshold_manager
                threshold_manager.reset_to_factory()
                self._load_thresholds()
                QMessageBox.information(self, "Reset Complete", "Thresholds reset to factory defaults.")
            except Exception as e:
                # Fallback - just reload the table
                self._load_thresholds()
                QMessageBox.information(self, "Reset Complete", "Thresholds reloaded.")
    
    def save_changes(self) -> bool:
        """Save threshold changes to ThresholdManager."""
        try:
            from backend.core.config import threshold_manager
            
            for row in range(self.table.rowCount()):
                key = self.table.item(row, 0).text()
                value_str = self.table.item(row, 2).text()
                
                # Convert to appropriate type
                try:
                    value = float(value_str)
                except ValueError:
                    value = value_str
                
                threshold_manager.set_threshold(key, value)
            
            return threshold_manager.save()
        except Exception as e:
            logger.error(f"Failed to save thresholds: {e}")
            return False


class SettingsDialog(QDialog):
    """Main settings dialog with Easy/Expert mode tabs."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚙️ Settings")
        self.setMinimumSize(550, 500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1e1e1e;
            }
            QTabWidget::pane {
                border: 1px solid #444;
                background-color: #252525;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #333;
                color: white;
                padding: 10px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #252525;
            }
            QTabBar::tab:hover {
                background-color: #444;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #444;
                border-radius: 4px;
                margin-top: 12px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #4FC3F7;
            }
        """)
        
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        self.easy_mode_tab = EasyModeTab()
        self.tabs.addTab(self.easy_mode_tab, "🎯 Easy Mode")
        
        self.expert_mode_tab = ExpertModeTab()
        self.tabs.addTab(self.expert_mode_tab, "🔧 Expert Mode")
        
        layout.addWidget(self.tabs)
        
        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.setStyleSheet("""
            QPushButton {
                background-color: #007acc;
                color: white;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #0094f7; }
        """)
        button_box.accepted.connect(self._on_save)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _on_save(self):
        """Save all settings and close."""
        # Save Expert Mode thresholds
        self.expert_mode_tab.save_changes()
        
        # Get Easy Mode settings (can be used by caller)
        easy_settings = self.easy_mode_tab.get_settings()
        logger.info(f"Easy Mode settings: {easy_settings}")
        
        self.accept()
    
    def get_easy_mode_settings(self) -> dict[str, Any]:
        """Get the Easy Mode settings after dialog closes."""
        return self.easy_mode_tab.get_settings()
