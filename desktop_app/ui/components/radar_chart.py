"""
RadarChart: Interactive spider/radar chart using Plotly.

Embeds a Plotly Scatterpolar chart inside a QWebEngineView for interactive
visualization of normalized sensor metrics against their critical thresholds.
"""

import json
import logging
from typing import Any

from PyQt6.QtCore import QUrl
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QVBoxLayout, QWidget

logger = logging.getLogger(__name__)

# Plotly HTML template with embedded chart
PLOTLY_HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        body {
            margin: 0;
            padding: 0;
            background-color: #1e1e1e;
            font-family: 'Inter', 'Segoe UI', sans-serif;
        }
        #chart {
            width: 100%;
            height: 100%;
        }
    </style>
</head>
<body>
    <div id="chart"></div>
    <script>
        var data = %DATA%;
        var layout = %LAYOUT%;
        var config = {responsive: true, displayModeBar: false};
        Plotly.newPlot('chart', data, layout, config);
    </script>
</body>
</html>
"""


class RadarChart(QWidget):
    """
    Interactive radar/spider chart for sensor metrics visualization.

    Uses Plotly.js embedded in QWebEngineView for rich interactivity.

    Features:
    - Normalized metric values (0.0-1.5 scale)
    - Red dotted critical limit circle at r=1.0
    - Semi-transparent fill (Blue=Healthy, Red=Critical)
    - Hover tooltips with "Value: X | Limit: Y"

    Example:
        >>> chart = RadarChart()
        >>> chart.update_data({
        ...     "Lyapunov": (0.6, 0.1),  # (current, threshold)
        ...     "Spectral": (25.0, 50.0),
        ...     "AE Error": (0.02, 0.05),
        ... })
    """

    # Default metric configuration with thresholds
    DEFAULT_METRICS = {
        "Lyapunov": {"threshold": 0.1, "unit": ""},
        "Spectral Centroid": {"threshold": 50.0, "unit": "Hz"},
        "AE Error": {"threshold": 0.05, "unit": ""},
        "Kurtosis": {"threshold": 5.0, "unit": ""},
        "Hysteresis": {"threshold": 0.15, "unit": ""},
        "Noise Std": {"threshold": 0.1, "unit": ""},
    }

    # Theme colors
    COLOR_HEALTHY = "rgba(0, 210, 255, 0.4)"        # Cyan semi-transparent
    COLOR_CRITICAL = "rgba(239, 68, 68, 0.4)"      # Red semi-transparent
    COLOR_LINE_HEALTHY = "#00d2ff"
    COLOR_LINE_CRITICAL = "#ef4444"
    COLOR_LIMIT = "#ff6666"
    COLOR_BG = "#1e1e1e"
    COLOR_GRID = "#444444"
    COLOR_TEXT = "#ededf2"

    def __init__(self, parent: QWidget | None = None) -> None:
        """Initialize RadarChart."""
        super().__init__(parent)
        self._metrics_config = dict(self.DEFAULT_METRICS)
        self._current_values: dict[str, tuple[float, float]] = {}
        self._is_critical = False

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the web view."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView()
        self.web_view.setMinimumSize(300, 300)
        layout.addWidget(self.web_view)

        # Initial empty chart
        self._render_chart({})

    def update_data(
        self,
        metrics: dict[str, tuple[float | None, float]],
        is_critical: bool = False,
    ) -> None:
        """
        Update chart with new metric values.

        Args:
            metrics: Dictionary mapping metric names to (value, threshold) tuples.
                     Value can be None to skip that metric.
            is_critical: If True, use red fill color instead of blue.
        """
        self._current_values = {
            k: v for k, v in metrics.items() if v[0] is not None
        }
        self._is_critical = is_critical
        self._render_chart(self._current_values)

    def update_metric(
        self,
        name: str,
        value: float | None,
        threshold: float | None = None,
    ) -> None:
        """
        Update a single metric value.

        Args:
            name: Metric name
            value: Current value (None to remove)
            threshold: Optional new threshold
        """
        if threshold is not None and name in self._metrics_config:
            self._metrics_config[name]["threshold"] = threshold

        old_threshold = self._metrics_config.get(name, {}).get("threshold", 1.0)
        if value is not None:
            self._current_values[name] = (value, threshold or old_threshold)
        elif name in self._current_values:
            del self._current_values[name]

        self._render_chart(self._current_values)

    def set_critical(self, is_critical: bool) -> None:
        """Set critical mode (changes fill color to red)."""
        self._is_critical = is_critical
        self._render_chart(self._current_values)

    def clear(self) -> None:
        """Clear all data and reset chart."""
        self._current_values = {}
        self._is_critical = False
        self._render_chart({})

    def _normalize(self, value: float, threshold: float) -> float:
        """
        Normalize a value relative to its threshold.

        Result: 1.0 means value equals threshold.
        Clamped to max 1.5 to prevent chart explosion.
        """
        if threshold <= 0:
            return 0.0
        normalized = value / threshold
        return min(1.5, max(0.0, normalized))

    def _render_chart(self, values: dict[str, tuple[float, float]]) -> None:
        """Render the Plotly chart to HTML and load it."""
        try:
            html = self._generate_html(values)
            self.web_view.setHtml(html)
        except Exception as e:
            logger.error(f"Failed to render radar chart: {e}")

    def _generate_html(self, values: dict[str, tuple[float, float]]) -> str:
        """Generate the Plotly HTML for the chart."""
        if not values:
            # Empty state
            data_json = json.dumps([])
            layout_json = json.dumps(self._get_layout([]))
            return PLOTLY_HTML_TEMPLATE.replace("%DATA%", data_json).replace("%LAYOUT%", layout_json)

        # Prepare data
        theta = list(values.keys())
        theta.append(theta[0])  # Close the polygon

        # Normalized values
        r_values = []
        hover_texts = []
        for name in theta[:-1]:
            val, thresh = values[name]
            normalized = self._normalize(val, thresh)
            r_values.append(normalized)
            hover_texts.append(f"{name}<br>Value: {val:.3f}<br>Limit: {thresh:.3f}")
        r_values.append(r_values[0])  # Close polygon
        hover_texts.append(hover_texts[0])

        # Limit circle (r=1.0 for all)
        r_limit = [1.0] * len(theta)

        # Check if any value exceeds critical (> 1.0)
        is_critical = self._is_critical or any(r > 1.0 for r in r_values[:-1])

        # Build traces
        traces = []

        # Critical limit circle (dotted red)
        traces.append({
            "type": "scatterpolar",
            "r": r_limit,
            "theta": theta,
            "mode": "lines",
            "name": "Critical Limit",
            "line": {
                "color": self.COLOR_LIMIT,
                "width": 2,
                "dash": "dot",
            },
            "hoverinfo": "skip",
        })

        # Value trace with fill
        fill_color = self.COLOR_CRITICAL if is_critical else self.COLOR_HEALTHY
        line_color = self.COLOR_LINE_CRITICAL if is_critical else self.COLOR_LINE_HEALTHY

        traces.append({
            "type": "scatterpolar",
            "r": r_values,
            "theta": theta,
            "mode": "lines+markers",
            "name": "Current Values",
            "fill": "toself",
            "fillcolor": fill_color,
            "line": {
                "color": line_color,
                "width": 3,
            },
            "marker": {
                "size": 8,
                "color": line_color,
            },
            "text": hover_texts,
            "hoverinfo": "text",
        })

        data_json = json.dumps(traces)
        layout_json = json.dumps(self._get_layout(theta))

        return PLOTLY_HTML_TEMPLATE.replace("%DATA%", data_json).replace("%LAYOUT%", layout_json)

    def _get_layout(self, theta: list[str]) -> dict[str, Any]:
        """Generate Plotly layout configuration."""
        return {
            "polar": {
                "radialaxis": {
                    "visible": True,
                    "range": [0, 1.5],
                    "tickvals": [0.5, 1.0, 1.5],
                    "ticktext": ["0.5", "1.0 (Limit)", "1.5"],
                    "tickfont": {"color": self.COLOR_TEXT, "size": 10},
                    "gridcolor": self.COLOR_GRID,
                    "linecolor": self.COLOR_GRID,
                },
                "angularaxis": {
                    "tickfont": {"color": self.COLOR_TEXT, "size": 11},
                    "gridcolor": self.COLOR_GRID,
                    "linecolor": self.COLOR_GRID,
                },
                "bgcolor": self.COLOR_BG,
            },
            "paper_bgcolor": self.COLOR_BG,
            "plot_bgcolor": self.COLOR_BG,
            "showlegend": False,
            "margin": {"l": 60, "r": 60, "t": 40, "b": 40},
            "font": {
                "color": self.COLOR_TEXT,
                "family": "Inter, Segoe UI, sans-serif",
            },
        }
