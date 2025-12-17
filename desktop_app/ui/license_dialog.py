"""
License Dialog for QorSense Desktop Application
Copyright © 2025 Pikolab R&D Ltd. Co. All Rights Reserved.

Fusion-themed license activation dialog.
"""

import os
import sys
import logging

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QLineEdit, QPushButton, QFrame, QMessageBox,
    QApplication
)
from PyQt6.QtGui import QPixmap, QFont, QIcon
from PyQt6.QtCore import Qt

# Import license manager
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.license_manager import LicenseManager

logger = logging.getLogger("LicenseDialog")


class LicenseDialog(QDialog):
    """
    License activation dialog with Fusion theme.
    
    Displays machine ID and allows user to enter license key
    for hardware-locked software activation.
    """
    
    def __init__(self, license_manager: LicenseManager = None, parent=None):
        super().__init__(parent)
        
        self.license_manager = license_manager or LicenseManager()
        self._setup_ui()
        self._apply_styles()
        
    def _setup_ui(self):
        """Initialize the user interface."""
        self.setWindowTitle("QorSense - License Activation")
        self.setFixedSize(500, 420)
        self.setWindowFlags(
            Qt.WindowType.Dialog | 
            Qt.WindowType.WindowTitleHint |
            Qt.WindowType.CustomizeWindowHint
        )
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 25, 30, 25)
        
        # --- Logo Section ---
        logo_container = QHBoxLayout()
        logo_container.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.logo_label = QLabel()
        logo_path = self._get_logo_path()
        if logo_path and os.path.exists(logo_path):
            pixmap = QPixmap(logo_path)
            scaled_pixmap = pixmap.scaledToHeight(80, Qt.TransformationMode.SmoothTransformation)
            self.logo_label.setPixmap(scaled_pixmap)
        else:
            # Fallback text logo
            self.logo_label.setText("QorSense")
            self.logo_label.setFont(QFont("Arial", 28, QFont.Weight.Bold))
            self.logo_label.setStyleSheet("color: #00ADB5;")
        
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_container.addWidget(self.logo_label)
        layout.addLayout(logo_container)
        
        # --- Title ---
        title_label = QLabel("License Activation Required")
        title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.DemiBold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #FFFFFF; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # --- Separator ---
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #444;")
        layout.addWidget(separator)
        
        # --- Machine ID Section ---
        machine_id_label = QLabel("Your Machine ID:")
        machine_id_label.setFont(QFont("Segoe UI", 10))
        machine_id_label.setStyleSheet("color: #AAA;")
        layout.addWidget(machine_id_label)
        
        machine_id_container = QHBoxLayout()
        
        self.machine_id_display = QLineEdit()
        self.machine_id_display.setText(self.license_manager.get_display_machine_id())
        self.machine_id_display.setReadOnly(True)
        self.machine_id_display.setFont(QFont("Consolas", 11))
        self.machine_id_display.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E1E;
                color: #00ADB5;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 8px;
                selection-background-color: #00ADB5;
            }
        """)
        machine_id_container.addWidget(self.machine_id_display)
        
        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setFixedWidth(80)
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_machine_id)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #353535;
                color: #DDD;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #404040;
                border-color: #00ADB5;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
        """)
        machine_id_container.addWidget(self.copy_btn)
        
        layout.addLayout(machine_id_container)
        
        # --- Hint ---
        hint_label = QLabel("💡 Send this Machine ID to Pikolab to receive your license key.")
        hint_label.setFont(QFont("Segoe UI", 9))
        hint_label.setStyleSheet("color: #888; font-style: italic;")
        hint_label.setWordWrap(True)
        layout.addWidget(hint_label)
        
        layout.addSpacing(10)
        
        # --- License Key Input Section ---
        license_key_label = QLabel("License Key:")
        license_key_label.setFont(QFont("Segoe UI", 10))
        license_key_label.setStyleSheet("color: #AAA;")
        layout.addWidget(license_key_label)
        
        self.license_key_input = QLineEdit()
        self.license_key_input.setPlaceholderText("XXXX-XXXX-XXXX-XXXX")
        self.license_key_input.setFont(QFont("Consolas", 13))
        self.license_key_input.setMaxLength(19)  # XXXX-XXXX-XXXX-XXXX = 19 chars
        self.license_key_input.setMinimumHeight(42)  # Balanced height
        self.license_key_input.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E1E;
                color: #FFFFFF;
                border: 2px solid #00ADB5;
                border-radius: 5px;
                padding: 8px 12px;
                font-size: 14px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QLineEdit:focus {
                border-color: #00C4CC;
                background-color: #252525;
            }
            QLineEdit::placeholder {
                color: #666666;
            }
        """)
        self.license_key_input.textChanged.connect(self._format_license_key)
        layout.addWidget(self.license_key_input)
        
        layout.addSpacing(15)
        
        # --- Buttons ---
        button_container = QHBoxLayout()
        button_container.setSpacing(15)
        
        self.register_btn = QPushButton("✓ Register")
        self.register_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.DemiBold))
        self.register_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.register_btn.setMinimumHeight(40)
        self.register_btn.clicked.connect(self._on_register)
        self.register_btn.setStyleSheet("""
            QPushButton {
                background-color: #00ADB5;
                color: #FFF;
                border: none;
                border-radius: 4px;
                padding: 10px 25px;
            }
            QPushButton:hover {
                background-color: #00C4CC;
            }
            QPushButton:pressed {
                background-color: #008B91;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
        """)
        button_container.addWidget(self.register_btn)
        
        self.exit_btn = QPushButton("✕ Exit")
        self.exit_btn.setFont(QFont("Segoe UI", 11))
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.setMinimumHeight(40)
        self.exit_btn.clicked.connect(self._on_exit)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3A;
                color: #DDD;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 10px 25px;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
                border-color: #FF6B6B;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
        """)
        button_container.addWidget(self.exit_btn)
        
        layout.addLayout(button_container)
        
        # --- Footer ---
        layout.addStretch()
        
        footer_separator = QFrame()
        footer_separator.setFrameShape(QFrame.Shape.HLine)
        footer_separator.setStyleSheet("background-color: #333;")
        layout.addWidget(footer_separator)
        
        footer_label = QLabel("Copyright © 2025 Pikolab R&D Ltd. Co. All Rights Reserved.")
        footer_label.setFont(QFont("Segoe UI", 9))
        footer_label.setStyleSheet("color: #666;")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer_label)
    
    def _apply_styles(self):
        """Apply the Fusion dark theme styling."""
        self.setStyleSheet("""
            QDialog {
                background-color: #2B2B2B;
            }
        """)
    
    def _get_logo_path(self) -> str:
        """Get the path to the logo image."""
        # Try multiple possible locations
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
        """Copy machine ID to clipboard."""
        clipboard = QApplication.clipboard()
        clipboard.setText(self.machine_id_display.text())
        
        # Temporary feedback
        original_text = self.copy_btn.text()
        self.copy_btn.setText("✓ Copied!")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #00ADB5;
                color: #FFF;
                border: none;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        # Reset after 1.5 seconds
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(1500, lambda: self._reset_copy_button(original_text))
    
    def _reset_copy_button(self, original_text):
        """Reset copy button to original state."""
        self.copy_btn.setText(original_text)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #353535;
                color: #DDD;
                border: 1px solid #555;
                border-radius: 4px;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #404040;
                border-color: #00ADB5;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
        """)
    
    def _format_license_key(self, text: str):
        """Auto-format license key input with dashes."""
        # Remove existing dashes and non-alphanumeric chars
        clean = ''.join(c for c in text.upper() if c.isalnum())
        
        # Add dashes every 4 characters
        formatted = '-'.join(clean[i:i+4] for i in range(0, len(clean), 4))
        
        # Update only if different to avoid cursor issues
        if formatted != text:
            cursor_pos = self.license_key_input.cursorPosition()
            self.license_key_input.blockSignals(True)
            self.license_key_input.setText(formatted[:19])  # Max 19 chars
            # Adjust cursor position
            new_pos = min(cursor_pos + (len(formatted) - len(text)), len(formatted))
            self.license_key_input.setCursorPosition(new_pos)
            self.license_key_input.blockSignals(False)
    
    def _on_register(self):
        """Handle register button click."""
        license_key = self.license_key_input.text().strip()
        
        if not license_key:
            QMessageBox.warning(
                self, 
                "Invalid Input", 
                "Please enter a license key."
            )
            self.license_key_input.setFocus()
            return
        
        if len(license_key) != 19:
            QMessageBox.warning(
                self, 
                "Invalid Format", 
                "License key must be in format: XXXX-XXXX-XXXX-XXXX"
            )
            self.license_key_input.setFocus()
            return
        
        # Verify license
        if self.license_manager.verify_license(license_key):
            # Save license
            if self.license_manager.save_license(license_key):
                QMessageBox.information(
                    self,
                    "Success",
                    "License activated successfully!\n\nThank you for using QorSense."
                )
                self.accept()  # Close dialog with success
            else:
                QMessageBox.critical(
                    self,
                    "Error",
                    "Failed to save license. Please check file permissions."
                )
        else:
            QMessageBox.critical(
                self,
                "Invalid License",
                "The license key is not valid for this machine.\n\n"
                "Please contact Pikolab support with your Machine ID."
            )
            self.license_key_input.setFocus()
            self.license_key_input.selectAll()
    
    def _on_exit(self):
        """Handle exit button click."""
        self.reject()  # Close dialog with rejection
    
    def closeEvent(self, event):
        """Handle window close event - treat as exit."""
        event.ignore()  # Prevent accidental close
        self._on_exit()


# For standalone testing
if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    from PyQt6.QtGui import QPalette, QColor
    
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Dark palette
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
    app.setPalette(palette)
    
    dialog = LicenseDialog()
    result = dialog.exec()
    
    print(f"Dialog result: {'Accepted' if result else 'Rejected'}")
    sys.exit(0 if result else 1)
