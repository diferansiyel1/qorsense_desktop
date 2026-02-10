"""
MetricLimitBar: A horizontal gauge widget showing value against limits.

Displays a horizontal bar with three color zones (Green/Yellow/Red)
and a needle indicating the current value position. Optimized for
industrial sensor metric visualization.
"""

from PyQt6.QtCore import Qt, QRectF
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget


class MetricLimitBar(QWidget):
    """
    Horizontal gauge bar displaying a metric value against limit zones.

    Features:
    - Three-zone gradient: Safe (Green) → Warning (Yellow) → Critical (Red)
    - Vertical needle indicating current value position
    - Metric name label above bar
    - Value and unit display to the right

    Example:
        >>> bar = MetricLimitBar(
        ...     name="Lyapunov",
        ...     unit="",
        ...     warning_threshold=0.5,
        ...     critical_threshold=1.0
        ... )
        >>> bar.set_value(0.75)  # Needle at 75% between yellow and red
    """

    # Default theme colors (Fusion Dark)
    COLOR_SAFE = QColor("#10b981")       # Green (Success)
    COLOR_WARNING = QColor("#f59e0b")    # Yellow (Warning)
    COLOR_CRITICAL = QColor("#ef4444")   # Red (Critical)
    COLOR_BACKGROUND = QColor("#2b2b2b")
    COLOR_NEEDLE = QColor("#ffffff")     # White needle
    COLOR_TEXT = QColor("#ededf2")
    COLOR_LABEL_DIM = QColor("#888888")

    def __init__(
        self,
        name: str = "Metric",
        unit: str = "",
        min_value: float = 0.0,
        max_value: float = 1.5,
        warning_threshold: float = 0.7,
        critical_threshold: float = 1.0,
        parent: QWidget | None = None,
    ) -> None:
        """
        Initialize MetricLimitBar.

        Args:
            name: Display name for the metric
            unit: Unit string (e.g., "Hz", "dB", "%")
            min_value: Minimum scale value
            max_value: Maximum scale value
            warning_threshold: Value where yellow zone starts
            critical_threshold: Value where red zone starts
            parent: Parent widget
        """
        super().__init__(parent)

        self.name = name
        self.unit = unit
        self.min_value = min_value
        self.max_value = max_value
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self._value: float | None = None

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the widget layout."""
        self.setMinimumHeight(50)
        self.setMaximumHeight(65)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 3, 5, 3)
        layout.setSpacing(2)

        # Top row: Metric name label
        self.lbl_name = QLabel(self.name)
        self.lbl_name.setStyleSheet("color: #888; font-size: 10px; font-weight: bold;")
        layout.addWidget(self.lbl_name)

        # Bottom row: Bar + Value
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(8)

        # Bar canvas (custom paint)
        self.bar_widget = _BarCanvas(self)
        self.bar_widget.setMinimumHeight(24)
        self.bar_widget.setMaximumHeight(28)
        bottom_layout.addWidget(self.bar_widget, stretch=1)

        # Value label
        self.lbl_value = QLabel("--")
        self.lbl_value.setMinimumWidth(60)
        self.lbl_value.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.lbl_value.setStyleSheet("color: #ededf2; font-size: 12px; font-weight: bold;")
        bottom_layout.addWidget(self.lbl_value)

        layout.addLayout(bottom_layout)

    def set_value(self, value: float | None) -> None:
        """
        Set the current metric value.

        Args:
            value: Metric value (None hides the needle)
        """
        self._value = value
        self.bar_widget.update()

        if value is not None:
            # Format value with appropriate precision
            if abs(value) < 0.01:
                formatted = f"{value:.4f}"
            elif abs(value) < 1.0:
                formatted = f"{value:.3f}"
            elif abs(value) < 100:
                formatted = f"{value:.2f}"
            else:
                formatted = f"{value:.1f}"

            unit_str = f" {self.unit}" if self.unit else ""
            self.lbl_value.setText(f"{formatted}{unit_str}")

            # Color value label based on zone
            if value >= self.critical_threshold:
                self.lbl_value.setStyleSheet("color: #ef4444; font-size: 12px; font-weight: bold;")
            elif value >= self.warning_threshold:
                self.lbl_value.setStyleSheet("color: #f59e0b; font-size: 12px; font-weight: bold;")
            else:
                self.lbl_value.setStyleSheet("color: #10b981; font-size: 12px; font-weight: bold;")
        else:
            self.lbl_value.setText("--")
            self.lbl_value.setStyleSheet("color: #666; font-size: 12px; font-weight: bold;")

    def set_thresholds(
        self,
        warning: float | None = None,
        critical: float | None = None,
        max_val: float | None = None,
    ) -> None:
        """
        Update threshold values.

        Args:
            warning: New warning threshold
            critical: New critical threshold
            max_val: New maximum scale value
        """
        if warning is not None:
            self.warning_threshold = warning
        if critical is not None:
            self.critical_threshold = critical
        if max_val is not None:
            self.max_value = max_val
        self.bar_widget.update()

    def set_name(self, name: str) -> None:
        """Update the metric name label."""
        self.name = name
        self.lbl_name.setText(name)

    def set_unit(self, unit: str) -> None:
        """Update the unit string."""
        self.unit = unit
        if self._value is not None:
            self.set_value(self._value)  # Refresh display

    def reset(self) -> None:
        """Reset to no-value state."""
        self.set_value(None)


class _BarCanvas(QWidget):
    """Internal widget for rendering the gradient bar and needle."""

    def __init__(self, parent: MetricLimitBar) -> None:
        super().__init__(parent)
        self.bar_parent = parent
        self.setMinimumHeight(20)

    def paintEvent(self, event) -> None:
        """Custom paint for gradient bar and needle."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect()
        bar_height = rect.height() - 4
        bar_y = 2
        bar_rect = QRectF(0, bar_y, rect.width(), bar_height)

        # Calculate zone widths based on thresholds
        parent = self.bar_parent
        range_total = parent.max_value - parent.min_value
        if range_total <= 0:
            range_total = 1.0

        warning_pos = (parent.warning_threshold - parent.min_value) / range_total
        critical_pos = (parent.critical_threshold - parent.min_value) / range_total

        # Clamp positions
        warning_pos = max(0.0, min(1.0, warning_pos))
        critical_pos = max(0.0, min(1.0, critical_pos))

        # Create gradient
        gradient = QLinearGradient(0, 0, rect.width(), 0)
        gradient.setColorAt(0.0, MetricLimitBar.COLOR_SAFE)
        gradient.setColorAt(warning_pos * 0.99, MetricLimitBar.COLOR_SAFE)
        gradient.setColorAt(warning_pos, MetricLimitBar.COLOR_WARNING)
        gradient.setColorAt(critical_pos * 0.99, MetricLimitBar.COLOR_WARNING)
        gradient.setColorAt(critical_pos, MetricLimitBar.COLOR_CRITICAL)
        gradient.setColorAt(1.0, MetricLimitBar.COLOR_CRITICAL)

        # Draw background
        painter.fillRect(bar_rect, MetricLimitBar.COLOR_BACKGROUND)

        # Draw gradient bar with rounded corners
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(bar_rect, 4, 4)

        # Draw border
        painter.setPen(QPen(QColor("#444"), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(bar_rect, 4, 4)

        # Draw needle if value is set
        if parent._value is not None:
            needle_pos = (parent._value - parent.min_value) / range_total
            needle_pos = max(0.0, min(1.0, needle_pos))
            needle_x = needle_pos * rect.width()

            # Draw needle (thick vertical line with triangle)
            needle_pen = QPen(MetricLimitBar.COLOR_NEEDLE, 3)
            needle_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(needle_pen)
            painter.drawLine(int(needle_x), int(bar_y), int(needle_x), int(bar_y + bar_height))

            # Draw small triangle pointer at top
            painter.setBrush(QBrush(MetricLimitBar.COLOR_NEEDLE))
            painter.setPen(Qt.PenStyle.NoPen)
            triangle_size = 5
            painter.drawPolygon([
                self._point(needle_x - triangle_size, 0),
                self._point(needle_x + triangle_size, 0),
                self._point(needle_x, bar_y),
            ])

        painter.end()

    def _point(self, x: float, y: float):
        """Create QPointF for polygon."""
        from PyQt6.QtCore import QPointF
        return QPointF(x, y)


class MetricLimitBarStack(QWidget):
    """
    Vertical stack of MetricLimitBar widgets for multiple metrics.

    Example:
        >>> stack = MetricLimitBarStack()
        >>> stack.add_metric("Lyapunov", "", warning=0.5, critical=1.0)
        >>> stack.add_metric("Spectral", "Hz", warning=30, critical=50, max_val=100)
        >>> stack.update_values({"Lyapunov": 0.7, "Spectral": 45.2})
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.bars: dict[str, MetricLimitBar] = {}

        self.layout_main = QVBoxLayout(self)
        self.layout_main.setContentsMargins(5, 5, 5, 5)
        self.layout_main.setSpacing(4)

    def add_metric(
        self,
        key: str,
        name: str,
        unit: str = "",
        min_value: float = 0.0,
        max_value: float = 1.5,
        warning: float = 0.7,
        critical: float = 1.0,
    ) -> MetricLimitBar:
        """
        Add a new metric bar to the stack.

        Args:
            key: Unique identifier for the metric
            name: Display name
            unit: Unit string
            min_value: Scale minimum
            max_value: Scale maximum
            warning: Warning threshold
            critical: Critical threshold

        Returns:
            The created MetricLimitBar
        """
        bar = MetricLimitBar(
            name=name,
            unit=unit,
            min_value=min_value,
            max_value=max_value,
            warning_threshold=warning,
            critical_threshold=critical,
        )
        self.bars[key] = bar
        self.layout_main.addWidget(bar)
        return bar

    def update_values(self, values: dict[str, float | None]) -> None:
        """
        Update multiple metric values at once.

        Args:
            values: Dictionary mapping metric keys to values
        """
        for key, value in values.items():
            if key in self.bars:
                self.bars[key].set_value(value)

    def get_bar(self, key: str) -> MetricLimitBar | None:
        """Get a specific bar by key."""
        return self.bars.get(key)

    def clear_all(self) -> None:
        """Reset all bars to no-value state."""
        for bar in self.bars.values():
            bar.reset()
