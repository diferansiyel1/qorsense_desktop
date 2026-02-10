"""
SensorDiagnosisDashboard: Medical MRI-style analysis view for industrial sensors.

Provides comprehensive visualization of Dual-Stream analysis results including:
- Header verdict section with health gauge and root cause badge
- Radar chart and limit bar visualization ("Metric DNA")
- Time-series deep dive with Raw/Clean, FFT, and Phase Space tabs
- Decision tree logic trace footer
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import numpy as np
from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from desktop_app.ui.components.limit_bar import MetricLimitBar, MetricLimitBarStack
from desktop_app.ui.components.radar_chart import RadarChart

logger = logging.getLogger(__name__)


# =============================================================================
# HELPER CLASSES
# =============================================================================


@dataclass
class MetricConfig:
    """Configuration for a single metric."""
    name: str
    key: str
    unit: str
    threshold: float
    max_display: float = 1.5  # Normalized scale max


class DashboardLogic:
    """Helper class for data normalization and unit handling."""

    # Metric to unit mapping
    METRIC_UNITS = {
        "lyapunov": "",
        "spectral_centroid": "Hz",
        "ae_error": "",
        "kurtosis": "",
        "hysteresis": "",
        "noise_std": "",
        "snr_db": "dB",
        "slope": "",
        "bias": "%",
        "sampen": "",
    }

    # Default thresholds for normalization
    DEFAULT_THRESHOLDS = {
        "lyapunov": 0.1,
        "spectral_centroid": 50.0,
        "ae_error": 0.05,
        "kurtosis": 5.0,
        "hysteresis": 0.15,
        "noise_std": 0.1,
        "sampen": 0.01,
    }

    @staticmethod
    def normalize(value: float, threshold: float) -> float:
        """
        Normalize a value relative to its threshold.

        Args:
            value: Current metric value
            threshold: Critical threshold value

        Returns:
            Normalized value, clamped to max 1.5
        """
        if threshold <= 0:
            return 0.0
        normalized = abs(value) / threshold
        return min(1.5, normalized)

    @staticmethod
    def get_unit(metric_key: str) -> str:
        """Get the unit string for a metric."""
        return DashboardLogic.METRIC_UNITS.get(metric_key.lower(), "")

    @staticmethod
    def downsample(data: list | np.ndarray, max_points: int = 5000) -> np.ndarray:
        """
        Downsample data for performance.

        Args:
            data: Time-series data
            max_points: Maximum number of points to return

        Returns:
            Downsampled numpy array
        """
        arr = np.array(data) if not isinstance(data, np.ndarray) else data
        if len(arr) <= max_points:
            return arr
        step = len(arr) // max_points
        return arr[::step][:max_points]


# =============================================================================
# CUSTOM WIDGETS
# =============================================================================


class CircularHealthGauge(QWidget):
    """
    Circular progress gauge showing health score (0-100%).

    Features custom paint event for professional arc rendering.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._score = 0.0
        self._status = "Green"
        self.setMinimumSize(120, 120)
        self.setMaximumSize(160, 160)

    def set_score(self, score: float, status: str = "Green") -> None:
        """Update the health score and status color."""
        self._score = max(0.0, min(100.0, score))
        self._status = status
        self.update()

    def paintEvent(self, event) -> None:
        """Custom paint for circular gauge."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        size = min(rect.width(), rect.height())
        margin = 10
        arc_rect = QRectF(
            (rect.width() - size) / 2 + margin,
            (rect.height() - size) / 2 + margin,
            size - 2 * margin,
            size - 2 * margin,
        )

        # Background arc
        bg_pen = QPen(QColor("#333"), 12)
        bg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(bg_pen)
        painter.drawArc(arc_rect, 225 * 16, -270 * 16)

        # Foreground arc (health score)
        color_map = {
            "Green": QColor("#10b981"),
            "Yellow": QColor("#f59e0b"),
            "Red": QColor("#ef4444"),
        }
        color = color_map.get(self._status, QColor("#10b981"))

        fg_pen = QPen(color, 12)
        fg_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(fg_pen)

        span = int(-270 * 16 * (self._score / 100.0))
        painter.drawArc(arc_rect, 225 * 16, span)

        # Center text
        painter.setPen(Qt.PenStyle.NoPen)
        font = QFont("Inter", 20, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(color)

        text = f"{self._score:.0f}%"
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)

        painter.end()


class StatusBadge(QFrame):
    """
    Large status badge showing root cause with dynamic icon and color.
    """

    STATUS_CONFIG = {
        "HEALTHY": ("✅", "#10b981", "HEALTHY"),
        "HARD_FAILURE": ("🔴", "#ef4444", "SIGNAL LOSS"),
        "FROZEN_SENSOR": ("❄️", "#ef4444", "FROZEN"),
        "MECHANICAL_FAILURE": ("⚙️", "#ef4444", "MECHANICAL"),
        "ELECTRONIC_FAILURE": ("🔌", "#9b59b6", "ELECTRONIC"),
        "EMI_NOISE": ("⚡", "#f59e0b", "EMI NOISE"),
        "BUBBLE_DETECTED": ("🫧", "#3498db", "BUBBLES"),
        "FOULING": ("🧪", "#f1c40f", "FOULING"),
        "DRIFT_AGING": ("📉", "#e67e22", "AGING"),
        "PROCESS_DISTURBANCE": ("🌊", "#3498db", "PROCESS"),
    }

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._root_cause = "HEALTHY"

        self.setStyleSheet("""
            QFrame {
                background-color: #1a3a2a;
                border-radius: 10px;
                border: 2px solid #10b981;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(2)

        # Header
        self.lbl_header = QLabel("ROOT CAUSE")
        self.lbl_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_header.setStyleSheet("color: #888; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(self.lbl_header)

        # Status text
        self.lbl_status = QLabel("✅ HEALTHY")
        self.lbl_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_status.setStyleSheet("color: #10b981; font-size: 18px; font-weight: bold;")
        layout.addWidget(self.lbl_status)

    def set_root_cause(self, root_cause: str) -> None:
        """Update the displayed root cause."""
        self._root_cause = root_cause
        emoji, color, display = self.STATUS_CONFIG.get(
            root_cause, ("❓", "#888", root_cause.replace("_", " "))
        )

        self.lbl_status.setText(f"{emoji} {display}")
        self.lbl_status.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")

        # Update border color
        self.setStyleSheet(f"""
            QFrame {{
                background-color: #1a2a3a;
                border-radius: 10px;
                border: 2px solid {color};
            }}
        """)


class DecisionTreeStepper(QWidget):
    """
    Horizontal stepper showing the decision tree path taken.

    Example: [Signal OK] → [No Freeze] → [Chaos Detected] → [RESULT: MECHANICAL]
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._steps: list[tuple[str, bool]] = []  # (label, is_active)

        self.setMinimumHeight(40)
        self.setStyleSheet("background-color: #1e1e1e; border-radius: 6px;")

        self.layout_main = QHBoxLayout(self)
        self.layout_main.setContentsMargins(10, 5, 10, 5)
        self.layout_main.setSpacing(0)

    def set_path(self, steps: list[tuple[str, bool]]) -> None:
        """
        Set the decision path.

        Args:
            steps: List of (label, is_highlighted) tuples
        """
        self._steps = steps
        self._rebuild_ui()

    def _rebuild_ui(self) -> None:
        """Rebuild the stepper UI."""
        # Clear existing
        while self.layout_main.count():
            item = self.layout_main.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, (label, is_active) in enumerate(self._steps):
            # Add step label
            lbl = QLabel(label)
            color = "#00d2ff" if is_active else "#666"
            weight = "bold" if is_active else "normal"
            lbl.setStyleSheet(f"color: {color}; font-size: 11px; font-weight: {weight};")
            self.layout_main.addWidget(lbl)

            # Add arrow (except for last item)
            if i < len(self._steps) - 1:
                arrow = QLabel(" → ")
                arrow.setStyleSheet("color: #444; font-size: 11px;")
                self.layout_main.addWidget(arrow)

        self.layout_main.addStretch()

    def clear(self) -> None:
        """Clear the stepper."""
        self._steps = []
        self._rebuild_ui()


class TimeSeriesPlot(QWidget):
    """
    Plotly-based time series visualization embedded in QWebEngineView.

    Supports multiple plot types: line overlay, FFT, phase space.
    """

    PLOTLY_TEMPLATE = """
    <!DOCTYPE html>
    <html>
    <head>
        <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
        <style>
            body { margin: 0; background-color: #1e1e1e; }
            #chart { width: 100%; height: 100%; }
        </style>
    </head>
    <body>
        <div id="chart"></div>
        <script>
            var data = %DATA%;
            var layout = %LAYOUT%;
            Plotly.newPlot('chart', data, layout, {responsive: true, displayModeBar: false});
        </script>
    </body>
    </html>
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        layout.addWidget(self.web_view)

    def plot_overlay(
        self,
        raw_data: np.ndarray | None,
        clean_data: np.ndarray | None,
        title: str = "Raw vs Clean Signal",
    ) -> None:
        """Plot raw and clean data overlaid."""
        traces = []

        if raw_data is not None and len(raw_data) > 0:
            raw_ds = DashboardLogic.downsample(raw_data)
            traces.append({
                "y": raw_ds.tolist(),
                "mode": "lines",
                "name": "Raw",
                "line": {"color": "rgba(150, 150, 150, 0.5)", "width": 1},
            })

        if clean_data is not None and len(clean_data) > 0:
            clean_ds = DashboardLogic.downsample(clean_data)
            traces.append({
                "y": clean_ds.tolist(),
                "mode": "lines",
                "name": "Clean",
                "line": {"color": "#00d2ff", "width": 2},
            })

        layout = self._get_base_layout(title, "Sample", "Value")
        self._render(traces, layout)

    def plot_fft(
        self,
        data: np.ndarray | None,
        fs: float = 1.0,
        spectral_centroid: float | None = None,
        title: str = "Frequency Domain (FFT)",
    ) -> None:
        """Plot FFT magnitude spectrum with optional spectral centroid marker."""
        traces = []

        if data is not None and len(data) > 32:
            data_ds = DashboardLogic.downsample(data)

            # Compute FFT
            n = len(data_ds)
            fft_vals = np.abs(np.fft.rfft(data_ds))
            freqs = np.fft.rfftfreq(n, 1.0 / fs)

            traces.append({
                "x": freqs.tolist(),
                "y": fft_vals.tolist(),
                "mode": "lines",
                "name": "Magnitude",
                "line": {"color": "#af5ce0", "width": 2},
                "fill": "tozeroy",
                "fillcolor": "rgba(175, 92, 224, 0.2)",
            })

        layout = self._get_base_layout(title, "Frequency (Hz)", "Amplitude")

        # Add spectral centroid line
        if spectral_centroid is not None:
            layout["shapes"] = [{
                "type": "line",
                "x0": spectral_centroid,
                "x1": spectral_centroid,
                "y0": 0,
                "y1": 1,
                "yref": "paper",
                "line": {"color": "#ef4444", "width": 2, "dash": "dash"},
            }]
            layout["annotations"] = [{
                "x": spectral_centroid,
                "y": 0.95,
                "yref": "paper",
                "text": f"Centroid: {spectral_centroid:.2f} Hz",
                "showarrow": False,
                "font": {"color": "#ef4444", "size": 11},
            }]

        self._render(traces, layout)

    def plot_phase_space(
        self,
        data: np.ndarray | None,
        delay: int = 1,
        title: str = "Phase Space (Chaos View)",
    ) -> None:
        """Plot phase space reconstruction: x=data[t], y=data[t+delay]."""
        traces = []

        if data is not None and len(data) > delay + 10:
            data_ds = DashboardLogic.downsample(data, max_points=2000)
            x = data_ds[:-delay]
            y = data_ds[delay:]

            traces.append({
                "x": x.tolist(),
                "y": y.tolist(),
                "mode": "markers",
                "name": "Phase",
                "marker": {
                    "size": 3,
                    "color": "#00d2ff",
                    "opacity": 0.6,
                },
            })

        layout = self._get_base_layout(title, "x(t)", f"x(t+{delay})")
        self._render(traces, layout)

    def clear(self) -> None:
        """Clear the plot."""
        self._render([], self._get_base_layout("", "", ""))

    def _get_base_layout(self, title: str, xaxis: str, yaxis: str) -> dict:
        """Get base Plotly layout."""
        return {
            "title": {"text": title, "font": {"color": "#ededf2", "size": 14}},
            "paper_bgcolor": "#1e1e1e",
            "plot_bgcolor": "#1e1e1e",
            "font": {"color": "#ededf2"},
            "xaxis": {
                "title": xaxis,
                "gridcolor": "#333",
                "zerolinecolor": "#444",
            },
            "yaxis": {
                "title": yaxis,
                "gridcolor": "#333",
                "zerolinecolor": "#444",
            },
            "margin": {"l": 50, "r": 20, "t": 40, "b": 40},
        }

    def _render(self, traces: list, layout: dict) -> None:
        """Render the chart."""
        try:
            html = self.PLOTLY_TEMPLATE.replace(
                "%DATA%", json.dumps(traces)
            ).replace("%LAYOUT%", json.dumps(layout))
            self.web_view.setHtml(html)
        except Exception as e:
            logger.error(f"Failed to render plot: {e}")


# =============================================================================
# MAIN DASHBOARD
# =============================================================================


class DetailedAnalysisWidget(QWidget):
    """
    Right panel of the dashboard containing all analysis visualizations.

    Structure:
    A. Header Section (Verdict)
    B. Metric DNA (Radar + Limit Bars)
    C. Time Series Tabs
    D. Logic Trace (Decision Tree Stepper)
    """

    # Metric configurations for limit bars
    METRIC_CONFIGS = [
        MetricConfig("Lyapunov", "lyapunov", "", 0.1),
        MetricConfig("Spectral Centroid", "spectral_centroid", "Hz", 50.0),
        MetricConfig("AE Error", "ae_error", "", 0.05),
        MetricConfig("Kurtosis", "kurtosis", "", 5.0),
        MetricConfig("Hysteresis", "hysteresis", "", 0.15),
        MetricConfig("Noise Std", "noise_std", "", 0.1),
    ]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the UI structure."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Scroll Area for content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet("""
            QScrollArea { background-color: #1e1e1e; border: none; }
            QScrollBar:vertical { background: #2a2a2a; width: 10px; }
            QScrollBar::handle:vertical { background: #555; border-radius: 5px; }
        """)

        content = QWidget()
        content.setStyleSheet("background-color: #1e1e1e;")
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(15)
        content_layout.setContentsMargins(5, 5, 5, 5)

        # =====================================================================
        # A. HEADER SECTION (The Verdict)
        # =====================================================================
        header_frame = QFrame()
        header_frame.setStyleSheet("background-color: #252525; border-radius: 8px;")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(15, 15, 15, 15)
        header_layout.setSpacing(20)

        # Status Badge (left)
        self.status_badge = StatusBadge()
        self.status_badge.setMinimumWidth(180)
        header_layout.addWidget(self.status_badge)

        # Health Gauge (center)
        gauge_container = QWidget()
        gauge_layout = QVBoxLayout(gauge_container)
        gauge_layout.setContentsMargins(0, 0, 0, 0)

        gauge_label = QLabel("SYSTEM HEALTH")
        gauge_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        gauge_label.setStyleSheet("color: #888; font-size: 10px; font-weight: bold;")
        gauge_layout.addWidget(gauge_label)

        self.health_gauge = CircularHealthGauge()
        gauge_layout.addWidget(self.health_gauge, alignment=Qt.AlignmentFlag.AlignCenter)

        header_layout.addWidget(gauge_container)

        # AI Confidence (right)
        confidence_container = QWidget()
        confidence_layout = QVBoxLayout(confidence_container)
        confidence_layout.setContentsMargins(0, 0, 0, 0)

        confidence_label = QLabel("AI DIAGNOSIS CONFIDENCE")
        confidence_label.setStyleSheet("color: #888; font-size: 10px; font-weight: bold;")
        confidence_layout.addWidget(confidence_label)

        self.confidence_bar = QProgressBar()
        self.confidence_bar.setRange(0, 100)
        self.confidence_bar.setValue(0)
        self.confidence_bar.setTextVisible(True)
        self.confidence_bar.setFixedHeight(24)
        self.confidence_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                background-color: #222;
                text-align: center;
                color: #ededf2;
            }
            QProgressBar::chunk {
                background-color: #af5ce0;
                border-radius: 3px;
            }
        """)
        confidence_layout.addWidget(self.confidence_bar)
        confidence_layout.addStretch()

        header_layout.addWidget(confidence_container, stretch=1)

        content_layout.addWidget(header_frame)

        # =====================================================================
        # B. METRIC DNA SECTION (50/50 Split)
        # =====================================================================
        dna_frame = QFrame()
        dna_frame.setStyleSheet("background-color: #252525; border-radius: 8px;")
        dna_layout = QHBoxLayout(dna_frame)
        dna_layout.setContentsMargins(10, 10, 10, 10)
        dna_layout.setSpacing(10)

        # Left: Radar Chart
        radar_container = QWidget()
        radar_layout = QVBoxLayout(radar_container)
        radar_layout.setContentsMargins(0, 0, 0, 0)

        radar_label = QLabel("METRIC RADAR")
        radar_label.setStyleSheet("color: #888; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        radar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        radar_layout.addWidget(radar_label)

        self.radar_chart = RadarChart()
        self.radar_chart.setMinimumSize(280, 280)
        radar_layout.addWidget(self.radar_chart)

        dna_layout.addWidget(radar_container, stretch=1)

        # Right: Limit Bars
        bars_container = QWidget()
        bars_layout = QVBoxLayout(bars_container)
        bars_layout.setContentsMargins(0, 0, 0, 0)

        bars_label = QLabel("METRIC ZONES")
        bars_label.setStyleSheet("color: #888; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        bars_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bars_layout.addWidget(bars_label)

        self.limit_bars = MetricLimitBarStack()
        for cfg in self.METRIC_CONFIGS:
            self.limit_bars.add_metric(
                key=cfg.key,
                name=cfg.name,
                unit=cfg.unit,
                min_value=0.0,
                max_value=cfg.threshold * 1.5,
                warning=cfg.threshold * 0.7,
                critical=cfg.threshold,
            )
        bars_layout.addWidget(self.limit_bars)

        dna_layout.addWidget(bars_container, stretch=1)

        content_layout.addWidget(dna_frame)

        # =====================================================================
        # C. TIME SERIES DEEP DIVE (Tabs)
        # =====================================================================
        tabs_frame = QFrame()
        tabs_frame.setStyleSheet("background-color: #252525; border-radius: 8px;")
        tabs_layout = QVBoxLayout(tabs_frame)
        tabs_layout.setContentsMargins(10, 10, 10, 10)

        self.time_tabs = QTabWidget()
        self.time_tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #333;
                background-color: #1e1e1e;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #2a2a2a;
                color: #888;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                color: #00d2ff;
                font-weight: bold;
            }
            QTabBar::tab:hover {
                color: #ededf2;
            }
        """)

        # Tab 1: Raw vs Clean
        self.plot_raw_clean = TimeSeriesPlot()
        self.time_tabs.addTab(self.plot_raw_clean, "📊 Raw vs Clean")

        # Tab 2: Frequency Domain
        self.plot_fft = TimeSeriesPlot()
        self.time_tabs.addTab(self.plot_fft, "📈 Frequency Domain")

        # Tab 3: Phase Space
        self.plot_phase = TimeSeriesPlot()
        self.time_tabs.addTab(self.plot_phase, "🌀 Phase Space")

        tabs_layout.addWidget(self.time_tabs)
        content_layout.addWidget(tabs_frame)

        # =====================================================================
        # D. LOGIC TRACE (Decision Tree Stepper)
        # =====================================================================
        trace_frame = QFrame()
        trace_frame.setStyleSheet("background-color: #252525; border-radius: 8px;")
        trace_layout = QVBoxLayout(trace_frame)
        trace_layout.setContentsMargins(10, 8, 10, 8)

        trace_label = QLabel("DIAGNOSIS PATH")
        trace_label.setStyleSheet("color: #888; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        trace_layout.addWidget(trace_label)

        self.decision_stepper = DecisionTreeStepper()
        trace_layout.addWidget(self.decision_stepper)

        content_layout.addWidget(trace_frame)
        content_layout.addStretch()

        scroll.setWidget(content)
        main_layout.addWidget(scroll)

    def update_results(self, result: dict[str, Any], raw_data: np.ndarray | None = None) -> None:
        """
        Update all dashboard components with analysis results.

        Args:
            result: DiagnosisResult dictionary with keys:
                    - health: {score, status, diagnosis, root_cause}
                    - metrics: {lyapunov, spectral_centroid, ...}
            raw_data: Optional raw time-series for plotting
        """
        health = result.get("health", {})
        metrics = result.get("metrics", {})

        # A. Header
        root_cause = health.get("root_cause") or metrics.get("root_cause", "HEALTHY")
        self.status_badge.set_root_cause(root_cause)

        score = health.get("score", 0)
        status = health.get("status", "Green")
        self.health_gauge.set_score(score, status)

        # Calculate AI confidence based on key metrics
        confidence = self._calculate_confidence(metrics)
        self.confidence_bar.setValue(int(confidence))

        # B. Radar Chart
        radar_data = {}
        for cfg in self.METRIC_CONFIGS:
            val = metrics.get(cfg.key)
            if val is not None:
                radar_data[cfg.name] = (val, cfg.threshold)

        is_critical = status == "Red" or root_cause not in ["HEALTHY"]
        self.radar_chart.update_data(radar_data, is_critical=is_critical)

        # B. Limit Bars
        bar_values = {cfg.key: metrics.get(cfg.key) for cfg in self.METRIC_CONFIGS}
        self.limit_bars.update_values(bar_values)

        # C. Time Series Plots
        clean_data = metrics.get("trend") or metrics.get("clean_data")
        if raw_data is not None or clean_data is not None:
            self.plot_raw_clean.plot_overlay(raw_data, np.array(clean_data) if clean_data else None)

        if raw_data is not None:
            spectral = metrics.get("spectral_centroid")
            fs = metrics.get("sampling_rate", 1.0)
            self.plot_fft.plot_fft(raw_data, fs=fs, spectral_centroid=spectral)
            self.plot_phase.plot_phase_space(raw_data)

        # D. Decision Path
        path = self._build_decision_path(metrics, root_cause)
        self.decision_stepper.set_path(path)

    def _calculate_confidence(self, metrics: dict) -> float:
        """Calculate AI diagnosis confidence based on metric completeness."""
        required = ["lyapunov", "spectral_centroid", "kurtosis", "sampen"]
        present = sum(1 for k in required if metrics.get(k) is not None)
        base_confidence = (present / len(required)) * 100

        # Boost if AE error is available
        if metrics.get("ae_error") is not None:
            base_confidence = min(100, base_confidence * 1.1)

        return base_confidence

    def _build_decision_path(self, metrics: dict, root_cause: str) -> list[tuple[str, bool]]:
        """Build the decision tree path based on metrics."""
        path = []

        # Check signal validity
        raw_val = metrics.get("raw_value")
        if raw_val is not None and 4.0 <= raw_val <= 20.0:
            path.append(("Signal OK", True))
        elif raw_val is not None:
            path.append(("Signal FAIL", True))
            path.append((f"RESULT: {root_cause}", True))
            return path
        else:
            path.append(("Signal Unknown", False))

        # Check frozen
        sampen = metrics.get("sampen")
        noise = metrics.get("noise_std")
        if sampen is not None and sampen >= 0.01 and (noise is None or noise >= 0.001):
            path.append(("Not Frozen", True))
        elif sampen is not None or noise is not None:
            path.append(("FROZEN", True))
            path.append((f"RESULT: {root_cause}", True))
            return path

        # Check chaos/noise
        lyapunov = metrics.get("lyapunov")
        spectral = metrics.get("spectral_centroid")

        if spectral is not None and spectral > 50:
            path.append(("High Freq Noise", True))
        elif lyapunov is not None and lyapunov > 0.1:
            if spectral is not None and spectral < 10:
                path.append(("Chaos (Low Freq)", True))
            else:
                path.append(("Chaos (High Freq)", True))
        else:
            path.append(("Stable", True))

        # Check transient
        kurtosis = metrics.get("kurtosis")
        if kurtosis is not None and kurtosis > 5.0:
            path.append(("Transient Detected", True))

        # Final result
        path.append((f"RESULT: {root_cause}", True))

        return path

    def clear(self) -> None:
        """Reset all displays to default state."""
        self.status_badge.set_root_cause("HEALTHY")
        self.health_gauge.set_score(0, "Green")
        self.confidence_bar.setValue(0)
        self.radar_chart.clear()
        self.limit_bars.clear_all()
        self.plot_raw_clean.clear()
        self.plot_fft.clear()
        self.plot_phase.clear()
        self.decision_stepper.clear()


class SensorDiagnosisDashboard(QWidget):
    """
    Main dashboard widget with sensor list and detailed analysis split view.

    Layout:
    [Left 20%: SensorListPanel] | [Right 80%: DetailedAnalysisWidget]
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Build the main split layout."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #333;
                width: 3px;
            }
            QSplitter::handle:hover {
                background-color: #00d2ff;
            }
        """)

        # Left Panel: Sensor List (placeholder - to be integrated with existing FieldExplorerPanel)
        self.sensor_panel = QWidget()
        self.sensor_panel.setStyleSheet("background-color: #1e1e1e;")
        sensor_layout = QVBoxLayout(self.sensor_panel)
        sensor_layout.setContentsMargins(10, 10, 10, 10)

        sensor_label = QLabel("SENSOR LIST")
        sensor_label.setStyleSheet("color: #888; font-size: 10px; font-weight: bold;")
        sensor_layout.addWidget(sensor_label)

        sensor_placeholder = QLabel("(Import FieldExplorerPanel here)")
        sensor_placeholder.setStyleSheet("color: #555; font-style: italic;")
        sensor_layout.addWidget(sensor_placeholder)
        sensor_layout.addStretch()

        self.splitter.addWidget(self.sensor_panel)

        # Right Panel: Detailed Analysis
        self.analysis_widget = DetailedAnalysisWidget()
        self.splitter.addWidget(self.analysis_widget)

        # Set split ratio (20/80)
        self.splitter.setSizes([200, 800])
        self.splitter.setStretchFactor(0, 0)  # Sensor panel doesn't stretch
        self.splitter.setStretchFactor(1, 1)  # Analysis stretches

        layout.addWidget(self.splitter)

    def set_sensor_panel(self, panel: QWidget) -> None:
        """
        Replace the placeholder sensor panel with the actual panel.

        Args:
            panel: The FieldExplorerPanel or similar widget
        """
        self.splitter.replaceWidget(0, panel)
        self.sensor_panel = panel

    def update_results(self, result: dict[str, Any], raw_data: np.ndarray | None = None) -> None:
        """
        Update the dashboard with analysis results.

        Args:
            result: DiagnosisResult dictionary
            raw_data: Optional raw time-series data
        """
        self.analysis_widget.update_results(result, raw_data)

    def clear(self) -> None:
        """Clear all displays."""
        self.analysis_widget.clear()
