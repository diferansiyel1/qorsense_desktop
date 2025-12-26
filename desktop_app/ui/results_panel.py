from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QFrame, QGridLayout, QLabel, QProgressBar, QVBoxLayout, QWidget


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

    def update_metrics(self, data):
        # data is the metrics dict
        import logging
        logger = logging.getLogger("ResultsPanel")
        logger.info(f"ResultsPanel.update_metrics called with data: slope={data.get('slope')}, hurst={data.get('hurst')}")

        self.metrics["slope"].setText(f"{data.get('slope', 0):.2e}")
        self.metrics["noise"].setText(f"{data.get('noise_std', 0):.2f}")
        self.metrics["snr"].setText(f"{data.get('snr_db', 0):.1f}")
        self.metrics["hyst"].setText(f"{data.get('hysteresis', 0):.2f}")
        self.metrics["hurst"].setText(f"{data.get('hurst', 0):.3f}")
        self.metrics["hurst_r2"].setText(f"{data.get('hurst_r2', 0):.2f}")

class DiagnosisBox(QWidget):
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
        self.setFixedWidth(250)

        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(15, 20, 15, 20)

        self.gauge = HealthScoreGauge()
        layout.addWidget(self.gauge)

        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #333;")
        layout.addWidget(line)

        self.grid = MetricsGrid()
        layout.addWidget(self.grid)

        self.diagnosis = DiagnosisBox()
        layout.addWidget(self.diagnosis)

        layout.addStretch()

    def update_results(self, result):
        health = result.get("health", {})
        metrics = result.get("metrics", {})

        self.gauge.set_score(health.get("score", 0), health.get("status", "Green"))
        self.grid.update_metrics(metrics)
        self.diagnosis.set_diagnosis(health.get("diagnosis", "Unknown"))

    def clear(self):
        """Reset all result displays to empty state"""
        self.gauge.set_score(0, "Green")

        # Reset grid metrics
        for key, lbl in self.grid.metrics.items():
            lbl.setText("--")

        self.diagnosis.set_diagnosis("System Ready")
