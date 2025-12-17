import sys
import os
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

# Ensure import paths work
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# Import the refactored Window
from desktop_app.ui.main_window import QorSenseMainWindow

# --- THEME SETUP ---
COLOR_BACKGROUND = QColor(43, 43, 43)
COLOR_TEXT = QColor(220, 220, 220)
COLOR_PANEL = QColor(53, 53, 53)
COLOR_ACCENT = QColor(0, 122, 204)

def apply_dark_theme(app):
    """Applies a Fusion-based Dark Industrial Theme."""
    app.setStyle("Fusion")
    palette = QPalette()
    
    palette.setColor(QPalette.ColorRole.Window, COLOR_BACKGROUND)
    palette.setColor(QPalette.ColorRole.WindowText, COLOR_TEXT)
    palette.setColor(QPalette.ColorRole.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.AlternateBase, COLOR_PANEL)
    palette.setColor(QPalette.ColorRole.ToolTipBase, COLOR_TEXT)
    palette.setColor(QPalette.ColorRole.ToolTipText, COLOR_BACKGROUND)
    palette.setColor(QPalette.ColorRole.Text, COLOR_TEXT)
    palette.setColor(QPalette.ColorRole.Button, COLOR_PANEL)
    palette.setColor(QPalette.ColorRole.ButtonText, COLOR_TEXT)
    palette.setColor(QPalette.ColorRole.Link, COLOR_ACCENT)
    palette.setColor(QPalette.ColorRole.Highlight, COLOR_ACCENT)
    palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
    
    app.setPalette(palette)
    app.setStyleSheet("""
        QToolTip { color: #ffffff; background-color: #2a82da; border: 1px solid white; }
        QDockWidget::title { background: #353535; text-align: center; padding: 5px; }
        QHeaderView::section { background-color: #353535; color: white; padding: 4px; border: 0px; }
        QTableWidget { gridline-color: #444; }
    """)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    app = QApplication(sys.argv)
    apply_dark_theme(app)
    
    # --- LICENSE CHECK ---
    from backend.license_manager import LicenseManager
    from desktop_app.ui.license_dialog import LicenseDialog
    
    license_manager = LicenseManager()
    
    # Check if valid license exists
    if not license_manager.is_licensed():
        logging.info("No valid license found. Showing license dialog...")
        
        dialog = LicenseDialog(license_manager)
        result = dialog.exec()
        
        if result != LicenseDialog.DialogCode.Accepted:
            logging.warning("License activation cancelled. Exiting application.")
            sys.exit(1)
        
        # Verify again after dialog
        if not license_manager.is_licensed():
            logging.error("License verification failed after dialog. Exiting.")
            sys.exit(1)
    
    logging.info("License verified. Starting main application...")
    
    window = QorSenseMainWindow()
    window.show()
    
    sys.exit(app.exec())

