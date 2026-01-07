"""
License Dialog for QorSense Desktop Application
Copyright © 2025 Pikolab R&D Ltd. Co. All Rights Reserved.

Professional enterprise-grade license activation dialog.
"""

import logging
import os
import sys

from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QPixmap, QColor, QPainter, QLinearGradient
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QGraphicsDropShadowEffect,
)

# Import license manager
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.license_manager import LicenseManager

logger = logging.getLogger("LicenseDialog")


class LicenseDialog(QDialog):
    """
    Professional enterprise-grade license activation dialog.
    
    Refactored to strictly follow Industrial Dark Mode UI/UX guidelines:
    - Consistent input heights (45px)
    - Monospace fonts for data fields
    - Clear visual hierarchy
    """

    # Industrial Dark Mode Palette
    PRIMARY_COLOR = "#00ADB5"       # Cyan (Desaturated slightly)
    PRIMARY_HOVER = "#00C4CC"
    PRIMARY_DARK = "#008B91"
    
    BG_WINDOW = "#1A1A24"
    BG_CARD = "#23232E"
    BG_INPUT = "#181820"
    
    TEXT_PRIMARY = "#E0E0E0"
    TEXT_SECONDARY = "#A0A0B0"
    TEXT_MUTED = "#505060"         # Subtle placeholder
    
    BORDER_COLOR = "#353545"
    SUCCESS_COLOR = "#4CAF50"
    
    FONT_TITLE = ("Segoe UI", 16, QFont.Weight.DemiBold)
    FONT_LABEL = ("Segoe UI", 10, QFont.Weight.Normal)
    FONT_DATA = ("Consolas", 12, QFont.Weight.Normal)  # Monospace

    def __init__(self, license_manager: LicenseManager = None, parent=None):
        super().__init__(parent)

        self.license_manager = license_manager or LicenseManager()
        self._setup_ui()
        self._apply_styles()

    def _setup_ui(self):
        """Initialize the professional user interface."""
        self.setWindowTitle("QorSense - License Activation")
        self.setFixedSize(500, 450)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.CustomizeWindowHint
        )

        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)

        # --- Header Section ---
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(0, 30, 0, 20)
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Logo
        logo_label = QLabel()
        logo_path = self._get_logo_path()
        if logo_path and os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaledToHeight(50, Qt.TransformationMode.SmoothTransformation)
            logo_label.setPixmap(scaled_pixmap)
        else:
            logo_label.setText("QorSense")
            logo_label.setFont(QFont("Arial", 22, QFont.Weight.Bold))
            logo_label.setStyleSheet(f"color: {self.PRIMARY_COLOR};")
        
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(logo_label)
        
        # Subtitle (optional or removed for cleaner look as requested, keeping meaningful context)
        # title_label = QLabel("License Activation") could be here, but let's keep it clean.
        
        main_layout.addWidget(header_widget)

        # --- Content Section ---
        content_widget = QWidget()
        content_widget.setStyleSheet(f"background-color: {self.BG_WINDOW};")
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(40, 10, 40, 30)
        content_layout.setSpacing(25)

        # --- Machine ID Group ---
        machine_group = QVBoxLayout()
        machine_group.setSpacing(8)
        
        lbl_machine = QLabel("Your Machine ID")
        lbl_machine.setFont(QFont(*self.FONT_LABEL))
        lbl_machine.setStyleSheet(f"color: {self.TEXT_SECONDARY};")
        machine_group.addWidget(lbl_machine)

        # Machine ID Input + Copy Button Row
        machine_row = QHBoxLayout()
        machine_row.setSpacing(0)  # Seamless integration

        self.machine_id_display = QLineEdit()
        self.machine_id_display.setText(self.license_manager.get_display_machine_id())
        self.machine_id_display.setReadOnly(True)
        self.machine_id_display.setFixedHeight(45)
        self.machine_id_display.setFont(QFont(*self.FONT_DATA))
        # Reduce brightness slightly to avoid halation
        self.machine_id_display.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.BG_INPUT};
                color: #CCCCCC;  
                border: 1px solid {self.BORDER_COLOR};
                border-right: none;
                border-top-left-radius: 4px;
                border-bottom-left-radius: 4px;
                padding-left: 12px;
            }}
        """)
        machine_row.addWidget(self.machine_id_display)

        self.copy_btn = QPushButton("Copy")
        self.copy_btn.setFixedSize(80, 45)
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_machine_id)
        self.copy_btn.setFont(QFont("Segoe UI", 10))
        self.copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.BG_CARD};
                color: {self.PRIMARY_COLOR};
                border: 1px solid {self.BORDER_COLOR};
                border-left: none;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #2F2F3D;
            }}
            QPushButton:pressed {{
                background-color: {self.BG_INPUT};
            }}
        """)
        machine_row.addWidget(self.copy_btn)
        
        machine_group.addLayout(machine_row)
        content_layout.addLayout(machine_group)

        # --- License Key Group ---
        license_group = QVBoxLayout()
        license_group.setSpacing(8)

        lbl_license = QLabel("Enter License Key")
        lbl_license.setFont(QFont(*self.FONT_LABEL))
        lbl_license.setStyleSheet(f"color: {self.TEXT_SECONDARY};")
        license_group.addWidget(lbl_license)

        self.license_key_input = QLineEdit()
        self.license_key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.license_key_input.setFixedHeight(45)
        self.license_key_input.setFont(QFont(*self.FONT_DATA))
        self.license_key_input.setMaxLength(19)
        self.license_key_input.setAlignment(Qt.AlignmentFlag.AlignLeft) # Standard left align for input
        self.license_key_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {self.BG_INPUT};
                color: {self.TEXT_PRIMARY};
                border: 1px solid {self.BORDER_COLOR};
                border-radius: 4px;
                padding-left: 12px;
                selection-background-color: {self.PRIMARY_COLOR};
                selection-color: #000;
            }}
            QLineEdit:focus {{
                border: 1px solid {self.PRIMARY_COLOR};
            }}
            QLineEdit::placeholder {{
                color: {self.TEXT_MUTED};
            }}
        """)
        self.license_key_input.textChanged.connect(self._format_license_key)
        license_group.addWidget(self.license_key_input)
        
        content_layout.addLayout(license_group)

        content_layout.addSpacing(10)

        # --- Action Buttons ---
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(12)

        self.register_btn = QPushButton("Activate License")
        self.register_btn.setFixedHeight(45)
        self.register_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.register_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.register_btn.clicked.connect(self._on_register)
        self.register_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.PRIMARY_COLOR};
                color: #FFFFFF;
                border: none;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {self.PRIMARY_HOVER};
            }}
            QPushButton:pressed {{
                background-color: {self.PRIMARY_DARK};
            }}
        """)
        
        # Subtle shadow for primary button
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setColor(QColor(0, 173, 181, 60))
        shadow.setOffset(0, 2)
        self.register_btn.setGraphicsEffect(shadow)
        
        btn_layout.addWidget(self.register_btn)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setFixedHeight(35)
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.setFont(QFont("Segoe UI", 10))
        self.exit_btn.clicked.connect(self._on_exit)
        self.exit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: transparent;
                color: {self.TEXT_MUTED};
                border: none;
            }}
            QPushButton:hover {{
                color: {self.TEXT_SECONDARY};
            }}
        """)
        btn_layout.addWidget(self.exit_btn)

        content_layout.addLayout(btn_layout)
        
        main_layout.addWidget(content_widget)

        # --- Footer ---
        footer_widget = QWidget()
        footer_widget.setFixedHeight(30)
        footer_widget.setStyleSheet(f"background-color: {self.BG_WINDOW};")
        footer_layout = QHBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 20, 5)
        footer_layout.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        version_label = QLabel("Enterprise Edition")
        version_label.setFont(QFont("Segoe UI", 8))
        version_label.setStyleSheet(f"color: {self.TEXT_MUTED};")
        footer_layout.addWidget(version_label)
        
        main_layout.addWidget(footer_widget)

    def _apply_styles(self):
        """Apply the global dialog background."""
        self.setStyleSheet(f"background-color: {self.BG_WINDOW};")

    def _get_logo_path(self) -> str:
        """Get the path to the logo image."""
        possible_paths = [
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "resources", "qorsense.png"),
            os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets", "qorsense.png"),
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "qorsense.png"),
        ]

        for path in possible_paths:
            if os.path.exists(path):
                return path
        return None

    def _copy_machine_id(self):
        """Copy machine ID to clipboard with feedback."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.machine_id_display.text())

        # Inline feedback on the button itself
        self.copy_btn.setText("Copied")
        self.copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.BG_CARD};
                color: {self.SUCCESS_COLOR};
                border: 1px solid {self.SUCCESS_COLOR};
                border-left: none;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
        """)

        # Reset after 1.5 seconds
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, self._reset_copy_button)

    def _reset_copy_button(self):
        """Reset copy button to original state."""
        self.copy_btn.setText("Copy")
        self.copy_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.BG_CARD};
                color: {self.PRIMARY_COLOR};
                border: 1px solid {self.BORDER_COLOR};
                border-left: none;
                border-top-right-radius: 4px;
                border-bottom-right-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: #2F2F3D;
            }}
        """)

    def _format_license_key(self, text: str):
        """Auto-format license key input with dashes."""
        clean = ''.join(c for c in text.upper() if c.isalnum())
        formatted = '-'.join(clean[i:i+4] for i in range(0, len(clean), 4))

        if formatted != text:
            cursor_pos = self.license_key_input.cursorPosition()
            self.license_key_input.blockSignals(True)
            self.license_key_input.setText(formatted[:19])
            new_pos = min(cursor_pos + (len(formatted) - len(text)), len(formatted))
            self.license_key_input.setCursorPosition(new_pos)
            self.license_key_input.blockSignals(False)

    def _on_register(self):
        """Handle register button click."""
        license_key = self.license_key_input.text().strip()

        if not license_key:
            QMessageBox.warning(self, "Invalid Input", "Please enter a license key.")
            self.license_key_input.setFocus()
            return

        if len(license_key) != 19:
            QMessageBox.warning(self, "Invalid Format", "License key must be in format: XXXX-XXXX-XXXX-XXXX")
            self.license_key_input.setFocus()
            return

        if self.license_manager.verify_license(license_key):
            if self.license_manager.save_license(license_key):
                QMessageBox.information(self, "Activation Successful", "Your license has been activated successfully.\n\nThank you for choosing QorSense.")
                self.accept()
            else:
                QMessageBox.critical(self, "Error", "Failed to save license. Please check file permissions.")
        else:
            QMessageBox.critical(self, "Invalid License", "The license key is not valid for this machine.\n\nPlease contact Pikolab support.")
            self.license_key_input.setFocus()
            self.license_key_input.selectAll()

    def _on_exit(self):
        """Handle exit button click."""
        self.reject()

    def closeEvent(self, event):
        """Handle window close event."""
        event.ignore()
        self._on_exit()


# For standalone testing
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    dialog = LicenseDialog()
    if dialog.exec():
        print("License Activated")
    else:
        print("Cancelled")
