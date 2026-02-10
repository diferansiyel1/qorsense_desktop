from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QFileDialog, QFrame, QGridLayout, QLabel, QProgressBar, 
    QPushButton, QScrollArea, QVBoxLayout, QWidget
)


class HealthScoreGauge(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 5, 0, 5)

        # Title
        title = QLabel("SYSTEM HEALTH SCORE")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #aaaaaa; font-weight: bold; font-size: 12px;")
        layout.addWidget(title)

        # Score Value
        self.lbl_score = QLabel("--%")
        self.lbl_score.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_score.setFont(QFont("Arial", 36, QFont.Weight.Bold))
        self.lbl_score.setStyleSheet("color: #00ffff;")
        layout.addWidget(self.lbl_score)

        # Progress Bar as Bar Gauge
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        self.bar.setFixedHeight(10)
        self.bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 5px;
                background-color: #222;
            }
            QProgressBar::chunk {
                background-color: #00ffff;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.bar)

    def set_score(self, score, status="Green"):
        self.lbl_score.setText(f"{score:.1f}%")
        self.bar.setValue(int(score))

        color = "#32c850" # Green
        if status == "Yellow": color = "#ffae00"
        elif status == "Red": color = "#ff3333"

        self.lbl_score.setStyleSheet(f"color: {color};")
        self.bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #444;
                border-radius: 5px;
                background-color: #222;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 4px;
            }}
        """)

class MetricsGrid(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(15)

        # Metric Labels
        self.metrics = {}
        self.create_metric_widget("Slope (Trend)", 0, 0, "slope")
        self.create_metric_widget("Noise (StdDev)", 0, 1, "noise")
        self.create_metric_widget("SNR (dB)", 1, 0, "snr")
        self.create_metric_widget("Hysteresis", 1, 1, "hyst")
        self.create_metric_widget("DFA (α)", 2, 0, "hurst")
        self.create_metric_widget("DFA R²", 2, 1, "hurst_r2")
        # === NEW METRICS ===
        self.create_metric_widget("Kurtosis", 3, 0, "kurtosis")
        self.create_metric_widget("SampEn", 3, 1, "sampen")
        self.create_metric_widget("Spectral (Hz)", 4, 0, "spectral")
        self.create_metric_widget("AE Error", 4, 1, "ae_error")

    def create_metric_widget(self, name, r, c, key):
        frame = QFrame()
        frame.setStyleSheet("background-color: #2a2a2a; border-radius: 4px;")
        vbox = QVBoxLayout(frame)
        vbox.setContentsMargins(5, 5, 5, 5)

        lbl_name = QLabel(name)
        lbl_name.setStyleSheet("color: #888; font-size: 10px;")
        lbl_name.setAlignment(Qt.AlignmentFlag.AlignCenter)

        lbl_val = QLabel("--")
        lbl_val.setStyleSheet("color: white; font-weight: bold; font-size: 14px;")
        lbl_val.setAlignment(Qt.AlignmentFlag.AlignCenter)

        vbox.addWidget(lbl_name)
        vbox.addWidget(lbl_val)

        self.layout.addWidget(frame, r, c)
        self.metrics[key] = lbl_val

    def update_metrics(self, data, unit: str = ""):
        # data is the metrics dict
        import logging
        logger = logging.getLogger("ResultsPanel")
        logger.info(f"ResultsPanel.update_metrics called with data: slope={data.get('slope')}, hurst={data.get('hurst')}")

        u_str = f" {unit}" if unit else ""

        self.metrics["slope"].setText(f"{data.get('slope', 0):.2e}")
        self.metrics["noise"].setText(f"{data.get('noise_std', 0):.2f}{u_str}")
        self.metrics["snr"].setText(f"{data.get('snr_db', 0):.1f}")
        self.metrics["hyst"].setText(f"{data.get('hysteresis', 0):.2f}")
        self.metrics["hurst"].setText(f"{data.get('hurst', 0):.3f}")
        self.metrics["hurst_r2"].setText(f"{data.get('hurst_r2', 0):.2f}")
        
        # === NEW METRICS ===
        kurtosis = data.get("kurtosis")
        self.metrics["kurtosis"].setText(f"{kurtosis:.2f}" if kurtosis is not None else "--")
        
        sampen = data.get("sampen")
        self.metrics["sampen"].setText(f"{sampen:.3f}" if sampen is not None else "--")
        
        spectral = data.get("spectral_centroid")
        self.metrics["spectral"].setText(f"{spectral:.2f}" if spectral is not None else "--")
        
        ae_error = data.get("ae_error")
        # AE error is typically mean squared error, so unit might be unit^2, 
        # but for simplicity we often track it relative to signal magnitude.
        # Let's add unit just to show scale context if provided.
        self.metrics["ae_error"].setText(f"{ae_error:.4f}" if ae_error is not None else "--")

class LyapunovPanel(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #222; border-radius: 6px; border: 1px solid #333;")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # Header
        lbl_title = QLabel("LYAPUNOV KARARLILIK ANALİZİ")
        lbl_title.setStyleSheet("color: #888; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        lbl_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_title)
        
        # Value Label
        self.lbl_value = QLabel("λ = --")
        self.lbl_value.setStyleSheet("color: white; font-size: 18px; font-weight: bold; margin-top: 5px;")
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_value)
        
        # Status Label
        self.lbl_status = QLabel("---")
        self.lbl_status.setStyleSheet("color: #666; font-size: 12px;")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.lbl_status)

    def update_data(self, value, status):
        self.lbl_value.setText(f"λ = {value:.4f}")
        self.lbl_status.setText(status)
        
        # Color coding
        # "KAOTİK (Kritik)", "KARARSIZ (Uyarı)", "STABİL (Normal)"
        if "KAOTİK" in status:
             color = "#ff4d4d" # Red
        elif "KARARSIZ" in status:
             color = "#ffcc00" # Yellow
        elif "STABİL" in status:
             color = "#00cc66" # Green
        else:
             color = "#aaaaaa"
             
        self.lbl_status.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 13px;")

    def reset(self):
        self.lbl_value.setText("λ = --")
        self.lbl_status.setText("---")
        self.lbl_status.setStyleSheet("color: #666; font-size: 12px;")


class SensorTypeBadge(QFrame):
    """Badge displaying the active sensor type for context-aware analysis."""
    
    # Sensor type display configuration
    SENSOR_DISPLAY = {
        "GENERIC": ("🔧", "Generic", "#888"),
        "PH": ("🧪", "pH Probe", "#4FC3F7"),
        "DO": ("💨", "Dissolved O₂", "#81C784"),
        "VISCOSITY": ("🌡️", "Viscosity", "#FFB74D"),
        "FLOW_MAG": ("💧", "Flow (Mag)", "#64B5F6"),
        "FLOW_CORIOLIS": ("⚖️", "Flow (Coriolis)", "#BA68C8"),
        "TEMP": ("🌡️", "Temperature", "#EF5350"),
        "PRESSURE": ("📊", "Pressure", "#42A5F5"),
        "CONDUCTIVITY": ("⚡", "Conductivity", "#26A69A"),
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            background-color: #1a3a4a;
            border-radius: 8px;
            border: 1px solid #2a5a7a;
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)
        
        # Header
        header = QLabel("SENSOR TYPE")
        header.setStyleSheet("color: #4FC3F7; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Type label
        self.type_label = QLabel("🔧 Generic")
        self.type_label.setStyleSheet("color: #888; font-size: 14px; font-weight: bold;")
        self.type_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.type_label)
    
    def set_sensor_type(self, sensor_type: str):
        """Update the badge with the given sensor type."""
        emoji, display, color = self.SENSOR_DISPLAY.get(
            sensor_type.upper(), 
            ("🔧", sensor_type, "#888")
        )
        
        self.type_label.setText(f"{emoji} {display}")
        self.type_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
        self.setStyleSheet(f"""
            background-color: {self._darken_color(color)};
            border-radius: 8px;
            border: 1px solid {color};
        """)
    
    def _darken_color(self, hex_color: str) -> str:
        """Create a darkened version of the color for background."""
        # Simple approximation - just use dark base with slight tint
        return "#1a2a3a"
    
    def reset(self):
        """Reset to default state."""
        self.set_sensor_type("GENERIC")



class RootCauseBadge(QFrame):
    """Colored badge displaying the root cause diagnosis."""
    
    # Color mapping for root causes (expanded for polymorphic diagnoses)
    COLORS = {
        # Critical (Red)
        "HARD_FAILURE": ("#ff1744", "🔴"),
        "FROZEN_SENSOR": ("#ff4d4d", "❄️"),
        "SENSOR_FROZEN": ("#ff4d4d", "❄️"),  # Legacy alias
        
        # Mechanical (Orange/Red)
        "MECHANICAL_FAILURE": ("#e74c3c", "⚙️"),
        "ROD_BENT": ("#e74c3c", "🔧"),
        
        # Electronic (Purple)
        "ELECTRONIC_FAILURE": ("#9b59b6", "🔌"),
        "CRACKED_GLASS": ("#9b59b6", "💎"),
        "REFERENCE_LEAK": ("#9b59b6", "💧"),
        
        # EMI/Noise (Yellow)
        "EMI_NOISE": ("#f39c12", "⚡"),
        "GROUND_LOOP_EMI": ("#f39c12", "⚡"),
        "ELECTRICAL_NOISE": ("#f39c12", "⚡"),
        
        # Process/Transient (Blue)
        "BUBBLE_DETECTED": ("#3498db", "🫧"),
        "PROCESS_DISTURBANCE": ("#3498db", "🌊"),
        "PROCESS_TURBULENCE": ("#3498db", "💨"),
        "CAVITATION": ("#3498db", "🫧"),
        
        # Fouling/Drift (Orange/Yellow)
        "FOULING": ("#f1c40f", "🧪"),
        "SENSOR_FOULING": ("#f1c40f", "🧪"),
        "DRIFT_AGING": ("#e67e22", "📉"),
        "SENSOR_AGING": ("#e67e22", "📉"),
        "ELECTROLYTE_DEPLETION": ("#e67e22", "🔋"),
        
        # Healthy (Green)
        "HEALTHY": ("#2ecc71", "✅"),
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            background-color: #2a2a2a;
            border-radius: 8px;
            padding: 5px;
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)
        
        # Header
        header = QLabel("ROOT CAUSE")
        header.setStyleSheet("color: #888; font-size: 9px; font-weight: bold; letter-spacing: 1px;")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Badge label
        self.badge_label = QLabel("✅ HEALTHY")
        self.badge_label.setStyleSheet("color: #2ecc71; font-size: 14px; font-weight: bold;")
        self.badge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.badge_label)
    
    def set_root_cause(self, root_cause: str):
        """Update the badge with the given root cause."""
        color, emoji = self.COLORS.get(root_cause, ("#aaa", "❓"))
        
        # Format display text - user-friendly labels
        display_map = {
            "HARD_FAILURE": "SIGNAL LOSS",
            "FROZEN_SENSOR": "FROZEN",
            "SENSOR_FROZEN": "FROZEN",
            "MECHANICAL_FAILURE": "MECHANICAL",
            "ROD_BENT": "ROD BENT",
            "ELECTRONIC_FAILURE": "ELECTRONIC",
            "CRACKED_GLASS": "CRACKED GLASS",
            "REFERENCE_LEAK": "REF LEAK",
            "EMI_NOISE": "EMI NOISE",
            "GROUND_LOOP_EMI": "GROUND LOOP",
            "ELECTRICAL_NOISE": "NOISE",
            "BUBBLE_DETECTED": "BUBBLES",
            "PROCESS_DISTURBANCE": "PROCESS",
            "PROCESS_TURBULENCE": "TURBULENCE",
            "CAVITATION": "CAVITATION",
            "FOULING": "FOULING",
            "SENSOR_FOULING": "FOULING",
            "DRIFT_AGING": "AGING/DRIFT",
            "SENSOR_AGING": "AGING",
            "ELECTROLYTE_DEPLETION": "ELECTROLYTE",
            "HEALTHY": "HEALTHY",
        }
        
        display = display_map.get(root_cause, root_cause.replace("_", " "))
        
        self.badge_label.setText(f"{emoji} {display}")
        self.badge_label.setStyleSheet(f"color: {color}; font-size: 14px; font-weight: bold;")
    
    def reset(self):
        """Reset to default healthy state."""
        self.set_root_cause("HEALTHY")


class DiagnosisBox(QWidget):
    """Widget for displaying diagnosis summary text."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        lbl = QLabel("DIAGNOSIS")
        lbl.setStyleSheet("color: #aaaaaa; font-weight: bold; font-size: 12px;")
        layout.addWidget(lbl)

        self.txt_diagnosis = QLabel("System Ready")
        self.txt_diagnosis.setWordWrap(True)
        self.txt_diagnosis.setStyleSheet("color: #ddd; font-size: 13px; padding: 5px; background-color: #2a2a2a; border-radius: 4px;")
        layout.addWidget(self.txt_diagnosis)

    def set_diagnosis(self, text):
        self.txt_diagnosis.setText(text)


class ResultsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: #1e1e1e; border-right: 1px solid #333;")
        self.setFixedWidth(305)  # Slightly wider for scrollbar

        # Main layout for this widget
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Scroll Area
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("""
            QScrollArea {
                background-color: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: #2a2a2a;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #555;
                border-radius: 5px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background: #666;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        main_layout.addWidget(scroll_area)

        # Content widget inside scroll area
        content_widget = QWidget()
        content_widget.setStyleSheet("background-color: #1e1e1e;")
        scroll_area.setWidget(content_widget)

        # Layout for content
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 15, 15, 15)

        # Sensor Type Badge (at very top for context)
        self.sensor_type_badge = SensorTypeBadge()
        layout.addWidget(self.sensor_type_badge)

        # Root Cause Badge
        self.root_cause_badge = RootCauseBadge()
        layout.addWidget(self.root_cause_badge)

        self.gauge = HealthScoreGauge()
        layout.addWidget(self.gauge)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #333;")
        layout.addWidget(line)

        self.grid = MetricsGrid()
        layout.addWidget(self.grid)

        # Lyapunov Panel
        self.lyapunov = LyapunovPanel()
        layout.addWidget(self.lyapunov)

        self.diagnosis = DiagnosisBox()
        layout.addWidget(self.diagnosis)

        # Export Button
        self.btn_export = QPushButton("📥 Export CSV")
        self.btn_export.setMinimumHeight(36)
        self.btn_export.setStyleSheet("""
            QPushButton {
                background-color: #2a6b2a;
                color: white;
                border-radius: 4px;
                padding: 8px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #3a8b3a; }
            QPushButton:disabled { background-color: #333; color: #666; }
        """)
        self.btn_export.setEnabled(False)
        self.btn_export.clicked.connect(self._export_csv)
        layout.addWidget(self.btn_export)

        layout.addStretch()

    def update_results(self, result, sensor_type: str = "GENERIC", sensor_unit: str = ""):
        """Update all result displays with analysis data.
        
        Args:
            result: Analysis result dictionary with 'health' and 'metrics' keys.
            sensor_type: The sensor type for context-aware display.
            sensor_unit: The unit of measurement (e.g., "cP", "pH").
        """
        self._last_result = result  # Store for export
        self.btn_export.setEnabled(True)
        
        health = result.get("health", {})
        metrics = result.get("metrics", {})

        # Update sensor type badge (context-aware display)
        self.sensor_type_badge.set_sensor_type(sensor_type)

        # Update root cause badge
        root_cause = health.get("root_cause") or metrics.get("root_cause", "HEALTHY")
        self.root_cause_badge.set_root_cause(root_cause)

        self.gauge.set_score(health.get("score", 0), health.get("status", "Green"))
        self.grid.update_metrics(metrics, unit=sensor_unit)
        
        # Update Lyapunov
        self.lyapunov.update_data(
            metrics.get("lyapunov", 0.0),
            metrics.get("lyapunov_status", "Unknown")
        )
        
        self.diagnosis.set_diagnosis(health.get("diagnosis", "Unknown"))

    def clear(self):
        """Reset all result displays to empty state"""
        self._last_result = None
        self.btn_export.setEnabled(False)
        
        self.gauge.set_score(0, "Green")

        # Reset grid metrics
        for key, lbl in self.grid.metrics.items():
            lbl.setText("--")

        self.lyapunov.reset()
        self.sensor_type_badge.reset()
        self.root_cause_badge.reset()
        self.diagnosis.set_diagnosis("System Ready")

    def _export_csv(self):
        """Export current analysis results to CSV file."""
        if not hasattr(self, '_last_result') or not self._last_result:
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Export Analysis Results", 
            "analysis_results.csv",
            "CSV Files (*.csv);;All Files (*)"
        )
        if not filepath:
            return
        
        import csv
        from datetime import datetime
        
        metrics = self._last_result.get("metrics", {})
        health = self._last_result.get("health", {})
        
        # Skip array-type metrics
        skip_keys = ("trend", "residuals", "raw_residuals", 
                     "dfa_scales", "dfa_fluctuations",
                     "hysteresis_x", "hysteresis_y")
        
        with open(filepath, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["QorSense Analysis Export"])
            writer.writerow(["Timestamp", datetime.now().isoformat()])
            writer.writerow([])
            
            # Core metrics
            writer.writerow(["Metric", "Value"])
            for key, value in metrics.items():
                if key not in skip_keys:
                    writer.writerow([key, value])
            
            # Health info
            writer.writerow([])
            writer.writerow(["Health Metric", "Value"])
            for key, value in health.items():
                if key != "penalties":
                    writer.writerow([key, value])
