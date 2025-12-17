"""
Pikolab License Key Generator Tool
Copyright © 2025 Pikolab R&D Ltd. Co. All Rights Reserved.

Standalone application for generating license keys from customer Machine IDs.
FOR INTERNAL PIKOLAB USE ONLY - DO NOT DISTRIBUTE!
"""

import sys
import os

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFrame, QMessageBox,
    QGroupBox, QFormLayout
)
from PyQt6.QtGui import QFont, QPalette, QColor, QClipboard
from PyQt6.QtCore import Qt

# Add project root to path for importing LicenseManager
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.license_manager import LicenseManager


class LicenseGeneratorWindow(QMainWindow):
    """
    Admin tool for generating license keys.
    
    Usage:
    1. Customer sends their Machine ID (displayed in License Dialog)
    2. Admin pastes Machine ID here
    3. Tool generates the valid license key
    4. Admin sends key to customer
    """
    
    def __init__(self):
        super().__init__()
        self.license_manager = LicenseManager()
        self._setup_ui()
        self._apply_styles()
        
    def _setup_ui(self):
        self.setWindowTitle("Pikolab License Key Generator")
        self.setFixedSize(600, 500)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # --- Header ---
        header_label = QLabel("🔑 Pikolab License Key Generator")
        header_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        header_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_label.setStyleSheet("color: #00ADB5;")
        layout.addWidget(header_label)
        
        warning_label = QLabel("⚠️ FOR INTERNAL USE ONLY - DO NOT DISTRIBUTE!")
        warning_label.setFont(QFont("Segoe UI", 10))
        warning_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        warning_label.setStyleSheet("color: #FF6B6B; font-weight: bold;")
        layout.addWidget(warning_label)
        
        # --- Separator ---
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #444;")
        layout.addWidget(separator)
        
        # --- Input Section ---
        input_group = QGroupBox("Müşteri Bilgileri")
        input_group.setFont(QFont("Segoe UI", 11))
        input_layout = QFormLayout(input_group)
        input_layout.setSpacing(15)
        
        # Machine ID Input
        self.machine_id_input = QLineEdit()
        self.machine_id_input.setPlaceholderText("Örn: A35C7B79-BFE9-BE24-2EBB-9160AAB960CC")
        self.machine_id_input.setFont(QFont("Consolas", 12))
        self.machine_id_input.setMinimumHeight(40)
        self.machine_id_input.setStyleSheet("""
            QLineEdit {
                background-color: #2A2A2A;
                color: #00ADB5;
                border: 2px solid #444;
                border-radius: 5px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border-color: #00ADB5;
            }
        """)
        input_layout.addRow("Machine ID:", self.machine_id_input)
        
        # Customer Name (optional, for reference)
        self.customer_name_input = QLineEdit()
        self.customer_name_input.setPlaceholderText("(İsteğe bağlı)")
        self.customer_name_input.setFont(QFont("Segoe UI", 11))
        self.customer_name_input.setMinimumHeight(35)
        self.customer_name_input.setStyleSheet("""
            QLineEdit {
                background-color: #2A2A2A;
                color: #FFF;
                border: 1px solid #444;
                border-radius: 5px;
                padding: 8px 12px;
            }
            QLineEdit:focus {
                border-color: #00ADB5;
            }
        """)
        input_layout.addRow("Müşteri Adı:", self.customer_name_input)
        
        layout.addWidget(input_group)
        
        # --- Generate Button ---
        self.generate_btn = QPushButton("🔐 LİSANS ANAHTARI OLUŞTUR")
        self.generate_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.generate_btn.setMinimumHeight(50)
        self.generate_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.generate_btn.clicked.connect(self._generate_license)
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #00ADB5;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 12px;
            }
            QPushButton:hover {
                background-color: #00C4CC;
            }
            QPushButton:pressed {
                background-color: #008B91;
            }
        """)
        layout.addWidget(self.generate_btn)
        
        # --- Result Section ---
        result_group = QGroupBox("Oluşturulan Lisans Anahtarı")
        result_group.setFont(QFont("Segoe UI", 11))
        result_layout = QVBoxLayout(result_group)
        
        self.result_display = QLineEdit()
        self.result_display.setReadOnly(True)
        self.result_display.setFont(QFont("Consolas", 18, QFont.Weight.Bold))
        self.result_display.setMinimumHeight(55)
        self.result_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.result_display.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E1E;
                color: #32CD32;
                border: 2px solid #32CD32;
                border-radius: 6px;
                padding: 10px;
                letter-spacing: 3px;
            }
        """)
        result_layout.addWidget(self.result_display)
        
        # Copy Button
        self.copy_btn = QPushButton("📋 Panoya Kopyala")
        self.copy_btn.setFont(QFont("Segoe UI", 10))
        self.copy_btn.setMinimumHeight(35)
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3A;
                color: #DDD;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
                border-color: #32CD32;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
        """)
        result_layout.addWidget(self.copy_btn)
        
        layout.addWidget(result_group)
        
        # --- Footer ---
        layout.addStretch()
        footer_label = QLabel("Copyright © 2025 Pikolab R&D Ltd. Co. All Rights Reserved.")
        footer_label.setFont(QFont("Segoe UI", 9))
        footer_label.setStyleSheet("color: #666;")
        footer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(footer_label)
    
    def _apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2B2B2B;
            }
            QGroupBox {
                background-color: #353535;
                border: 1px solid #444;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
                color: #AAA;
            }
            QLabel {
                color: #DDD;
            }
        """)
    
    def _generate_license(self):
        """Generate license key from Machine ID."""
        machine_id_input = self.machine_id_input.text().strip()
        
        if not machine_id_input:
            QMessageBox.warning(self, "Uyarı", "Lütfen Machine ID girin!")
            self.machine_id_input.setFocus()
            return
        
        # Clean the Machine ID (remove dashes, spaces, convert to uppercase)
        clean_id = machine_id_input.replace("-", "").replace(" ", "").upper()
        
        # Validate length (should be 32 hex characters)
        if len(clean_id) != 32 or not all(c in '0123456789ABCDEF' for c in clean_id):
            QMessageBox.warning(
                self, 
                "Geçersiz Format", 
                "Machine ID 32 karakter hexadecimal olmalıdır.\n\n"
                "Örnek: A35C7B79-BFE9-BE24-2EBB-9160AAB960CC"
            )
            return
        
        # Generate license key
        license_key = self.license_manager.generate_license_key(clean_id)
        
        # Display result
        self.result_display.setText(license_key)
        self.result_display.setStyleSheet("""
            QLineEdit {
                background-color: #1E1E1E;
                color: #32CD32;
                border: 2px solid #32CD32;
                border-radius: 6px;
                padding: 10px;
                letter-spacing: 3px;
            }
        """)
        
        # Log to console (for records)
        customer = self.customer_name_input.text().strip() or "Unknown"
        print(f"[LICENSE GENERATED] Customer: {customer} | Machine: {machine_id_input} | Key: {license_key}")
    
    def _copy_to_clipboard(self):
        """Copy the generated license key to clipboard."""
        license_key = self.result_display.text()
        
        if not license_key:
            QMessageBox.warning(self, "Uyarı", "Önce bir lisans anahtarı oluşturun!")
            return
        
        clipboard = QApplication.clipboard()
        clipboard.setText(license_key)
        
        # Visual feedback
        self.copy_btn.setText("✓ Kopyalandı!")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #32CD32;
                color: white;
                border: none;
                border-radius: 5px;
                padding: 8px 15px;
            }
        """)
        
        # Reset after 2 seconds
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(2000, self._reset_copy_button)
    
    def _reset_copy_button(self):
        self.copy_btn.setText("📋 Panoya Kopyala")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #3A3A3A;
                color: #DDD;
                border: 1px solid #555;
                border-radius: 5px;
                padding: 8px 15px;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
                border-color: #32CD32;
            }
            QPushButton:pressed {
                background-color: #2A2A2A;
            }
        """)


def apply_dark_theme(app):
    """Apply Fusion dark theme."""
    app.setStyle("Fusion")
    
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.Text, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 220, 220))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(0, 173, 181))
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    
    app.setPalette(palette)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    
    window = LicenseGeneratorWindow()
    window.show()
    
    sys.exit(app.exec())
