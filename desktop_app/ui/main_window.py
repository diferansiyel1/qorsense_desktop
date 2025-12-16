import sys
import os
import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFrame, QMessageBox, QProgressBar,
                             QFileDialog, QInputDialog, QDialog, QDialogButtonBox,
                             QRadioButton, QButtonGroup, QFormLayout, QLineEdit,
                             QSpinBox, QDoubleSpinBox, QGroupBox, QStackedWidget,
                             QComboBox)
import numpy as np
from PyQt6.QtCore import Qt, QTimer
from datetime import datetime
import pandas as pd

# Import modular UI components
from desktop_app.ui.charts import AnalysisDashboard
from desktop_app.ui.panels import FieldExplorerPanel, AlarmPanel
from desktop_app.ui.results_panel import ResultsPanel
from desktop_app.core.analyzer_bridge import AnalyzerBridge
from desktop_app.workers.analysis_worker import AnalysisWorker
from desktop_app.workers.file_loader import FileLoadWorker
from desktop_app.workers.live_worker import ModbusWorker
# Import list_available_ports for COM port scanning
from desktop_app.workers.live_worker import list_available_ports
from backend.models import SensorConfig

logger = logging.getLogger("MainWindow")


class ConnectionDialog(QDialog):
    """
    Dialog for configuring data source connection.
    Supports: CSV file, Modbus TCP (Ethernet), Modbus RTU (RS485/USB Serial).
    
    Hamilton VisiWater/Arc sensor defaults:
    - Baud: 19200
    - Parity: Even
    - StopBits: 1
    - Bytesize: 8
    """
    
    SOURCE_CSV = "csv"
    SOURCE_TCP = "tcp"
    SOURCE_RTU = "rtu"
    
    # Hamilton sensor defaults
    HAMILTON_BAUD = 19200
    HAMILTON_PARITY = "E"  # Even
    HAMILTON_STOPBITS = 1
    HAMILTON_BYTESIZE = 8
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connection Settings")
        self.setMinimumWidth(480)
        
        layout = QVBoxLayout(self)
        
        # --- Source Type Selection ---
        source_group = QGroupBox("Data Source")
        source_layout = QVBoxLayout(source_group)
        
        self.radio_csv = QRadioButton("CSV File")
        self.radio_tcp = QRadioButton("Modbus TCP (Ethernet)")
        self.radio_rtu = QRadioButton("Modbus RTU (RS485/USB)")
        self.radio_csv.setChecked(True)
        
        self.source_button_group = QButtonGroup(self)
        self.source_button_group.addButton(self.radio_csv, 0)
        self.source_button_group.addButton(self.radio_tcp, 1)
        self.source_button_group.addButton(self.radio_rtu, 2)
        
        source_layout.addWidget(self.radio_csv)
        source_layout.addWidget(self.radio_tcp)
        source_layout.addWidget(self.radio_rtu)
        layout.addWidget(source_group)
        
        # --- Stacked Widget for Settings ---
        self.settings_stack = QStackedWidget()
        
        # Page 0: Empty (CSV mode)
        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.addWidget(QLabel("Click OK to select a CSV file."))
        self.settings_stack.addWidget(empty_page)
        
        # Page 1: Modbus TCP Settings
        tcp_page = QWidget()
        tcp_layout = QFormLayout(tcp_page)
        
        self.ip_input = QLineEdit("192.168.1.100")
        self.ip_input.setPlaceholderText("e.g., 192.168.1.100")
        tcp_layout.addRow("IP Address:", self.ip_input)
        
        self.tcp_port_input = QSpinBox()
        self.tcp_port_input.setRange(1, 65535)
        self.tcp_port_input.setValue(502)
        tcp_layout.addRow("Port:", self.tcp_port_input)
        
        self.tcp_register_input = QSpinBox()
        self.tcp_register_input.setRange(0, 65535)
        self.tcp_register_input.setValue(0)
        tcp_layout.addRow("Register Address:", self.tcp_register_input)
        
        self.tcp_slave_input = QSpinBox()
        self.tcp_slave_input.setRange(1, 247)
        self.tcp_slave_input.setValue(1)
        tcp_layout.addRow("Slave ID:", self.tcp_slave_input)
        
        self.tcp_scale_input = QDoubleSpinBox()
        self.tcp_scale_input.setRange(0.0001, 10000.0)
        self.tcp_scale_input.setValue(1.0)
        self.tcp_scale_input.setDecimals(4)
        tcp_layout.addRow("Scale Factor:", self.tcp_scale_input)
        
        self.settings_stack.addWidget(tcp_page)
        
        # Page 2: Modbus RTU Settings
        rtu_page = QWidget()
        rtu_layout = QFormLayout(rtu_page)
        
        # COM Port ComboBox (populated dynamically)
        self.com_port_combo = QComboBox()
        self._refresh_com_ports()
        
        # Refresh button for COM ports
        com_port_row = QHBoxLayout()
        com_port_row.addWidget(self.com_port_combo, 1)
        btn_refresh = QPushButton("↻")
        btn_refresh.setFixedWidth(30)
        btn_refresh.setToolTip("Refresh COM ports")
        btn_refresh.clicked.connect(self._refresh_com_ports)
        com_port_row.addWidget(btn_refresh)
        
        rtu_layout.addRow("COM Port:", com_port_row)
        
        # Baud Rate ComboBox
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText(str(self.HAMILTON_BAUD))  # Hamilton default
        rtu_layout.addRow("Baud Rate:", self.baud_combo)
        
        # Parity ComboBox
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None (N)", "Even (E)", "Odd (O)"])
        self.parity_combo.setCurrentIndex(1)  # Even - Hamilton default
        rtu_layout.addRow("Parity:", self.parity_combo)
        
        # Stop Bits
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "2"])
        self.stopbits_combo.setCurrentText("1")  # Hamilton default
        rtu_layout.addRow("Stop Bits:", self.stopbits_combo)
        
        # Register Address
        self.rtu_register_input = QSpinBox()
        self.rtu_register_input.setRange(0, 65535)
        self.rtu_register_input.setValue(0)
        rtu_layout.addRow("Register Address:", self.rtu_register_input)
        
        # Slave ID
        self.rtu_slave_input = QSpinBox()
        self.rtu_slave_input.setRange(1, 247)
        self.rtu_slave_input.setValue(1)
        rtu_layout.addRow("Slave ID:", self.rtu_slave_input)
        
        # Scale Factor
        self.rtu_scale_input = QDoubleSpinBox()
        self.rtu_scale_input.setRange(0.0001, 10000.0)
        self.rtu_scale_input.setValue(1.0)
        self.rtu_scale_input.setDecimals(4)
        rtu_layout.addRow("Scale Factor:", self.rtu_scale_input)
        
        # Hamilton note
        hamilton_note = QLabel("💡 Hamilton VisiWater/Arc: 19200, Even, 1 stop bit")
        hamilton_note.setStyleSheet("color: #888; font-style: italic; font-size: 11px;")
        rtu_layout.addRow("", hamilton_note)
        
        self.settings_stack.addWidget(rtu_page)
        
        layout.addWidget(self.settings_stack)
        
        # --- Dialog Buttons ---
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Connect radio buttons to switch stacked widget page
        self.radio_csv.toggled.connect(lambda: self.settings_stack.setCurrentIndex(0))
        self.radio_tcp.toggled.connect(lambda: self.settings_stack.setCurrentIndex(1))
        self.radio_rtu.toggled.connect(lambda: self.settings_stack.setCurrentIndex(2))
    
    def _refresh_com_ports(self):
        """Refresh the COM port list from system."""
        self.com_port_combo.clear()
        ports = list_available_ports()
        if ports:
            for port_name, description in ports:
                display = f"{port_name} - {description}" if description else port_name
                self.com_port_combo.addItem(display, port_name)
        else:
            self.com_port_combo.addItem("No ports found", "")
    
    def get_source_type(self) -> str:
        """Return selected source type."""
        if self.radio_tcp.isChecked():
            return self.SOURCE_TCP
        elif self.radio_rtu.isChecked():
            return self.SOURCE_RTU
        return self.SOURCE_CSV
    
    def get_tcp_config(self) -> dict:
        """Return Modbus TCP configuration."""
        return {
            "connection_type": "TCP",
            "ip_address": self.ip_input.text().strip(),
            "tcp_port": self.tcp_port_input.value(),
            "register_address": self.tcp_register_input.value(),
            "slave_id": self.tcp_slave_input.value(),
            "scale_factor": self.tcp_scale_input.value()
        }
    
    def get_rtu_config(self) -> dict:
        """Return Modbus RTU configuration."""
        # Extract parity letter from combo text
        parity_text = self.parity_combo.currentText()
        parity = "N"
        if "Even" in parity_text:
            parity = "E"
        elif "Odd" in parity_text:
            parity = "O"
        
        return {
            "connection_type": "RTU",
            "serial_port": self.com_port_combo.currentData() or self.com_port_combo.currentText().split(" - ")[0],
            "baudrate": int(self.baud_combo.currentText()),
            "parity": parity,
            "stopbits": int(self.stopbits_combo.currentText()),
            "bytesize": 8,  # Fixed at 8 for Modbus RTU
            "register_address": self.rtu_register_input.value(),
            "slave_id": self.rtu_slave_input.value(),
            "scale_factor": self.rtu_scale_input.value()
        }
    
    def get_modbus_config(self) -> dict:
        """Return Modbus configuration based on selected type."""
        if self.radio_tcp.isChecked():
            return self.get_tcp_config()
        elif self.radio_rtu.isChecked():
            return self.get_rtu_config()
        return {}


class QorSenseMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QorSense Mission-Control v3.0")
        self.resize(1280, 800)
        
        # --- CORE LOGIC ---
        try:
            self.bridge = AnalyzerBridge()
        except Exception as e:
            QMessageBox.critical(self, "Initialization Error", f"Core Bridge Failed: {e}")
            sys.exit(1)
            
        self.config = SensorConfig()
        
        # Data Management
        self.sensor_data = {} # path -> data (list/numpy)
        self.sensor_analysis_results = {} # path -> analysis result dict
        self.current_data = None
        self.current_sensor_path = None
        self.sampling_rate = 1.0
        
        # Workers
        self.loader_worker = None # For file loading
        self.analysis_worker = None # For analysis tasks
        self.analysis_thread = None # To run analysis_worker in a separate thread
        self.modbus_worker = None  # For Modbus TCP live data
        
        # Live Data Management
        self.live_data_buffer = []  # Buffer for live Modbus data
        self.live_sample_count = 0  # Counter for triggering analysis
        self.ANALYSIS_TRIGGER_COUNT = 60  # Trigger analysis every 60 samples (1 minute at 1Hz)
        self.is_live_mode = False  # Flag for live monitoring mode
        
        # --- UI SETUP ---
        self.setup_ui()
        
    def setup_ui(self):
        # 1. Central Dashboard
        self.dashboard = AnalysisDashboard() # Charts
        
        # 2. Control Stripe (Top)
        control_panel = self.create_control_panel()
        
        # 3. Main Split (Left: Results/Charts, Right: Explorer... wait, sticking to layout)
        # Actually, let's put ResultsPanel on the Right of Charts
        
        lower_layout = QHBoxLayout()
        lower_layout.addWidget(self.dashboard, stretch=1)
        
        self.results_panel = ResultsPanel()
        self.results_panel.setVisible(False) # Hide initially
        lower_layout.addWidget(self.results_panel, stretch=0)
        
        # Combined Central Widget
        central_layout = QVBoxLayout()
        central_layout.setContentsMargins(5, 5, 5, 5)
        central_layout.addWidget(control_panel)
        central_layout.addLayout(lower_layout)
        
        central_widget = QWidget()
        central_widget.setLayout(central_layout)
        self.setCentralWidget(central_widget)
        
        # 3. Docks
        self.panel_explorer = FieldExplorerPanel(self)
        self.panel_explorer.sensor_selected.connect(self.on_sensor_selected)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.panel_explorer)
        
        self.panel_alarms = AlarmPanel(self)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self.panel_alarms)
        
        # 4. Status Bar
        self.status_label = QLabel("Ready")
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        self.statusBar().addPermanentWidget(self.status_label, 1)
        self.statusBar().addPermanentWidget(self.progress_bar)
        
        # 5. Menu
        self.create_menu()

    def create_control_panel(self):
        panel = QFrame()
        panel.setStyleSheet("background-color: #353535; border-radius: 5px;")
        layout = QHBoxLayout(panel)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Connection Settings Button
        self.btn_connect = QPushButton("⚙ Connection")
        self.btn_connect.setMinimumHeight(40)
        self.btn_connect.setStyleSheet("""
            QPushButton { 
                background-color: #4a4a4a; 
                color: white; 
                font-weight: bold; 
                border-radius: 4px;
                padding: 0 15px;
            }
            QPushButton:hover { background-color: #5a5a5a; }
            QPushButton:pressed { background-color: #3a3a3a; }
        """)
        self.btn_connect.clicked.connect(self.show_connection_dialog)
        
        # Stop Live Button (initially hidden)
        self.btn_stop_live = QPushButton("⏹ Stop Live")
        self.btn_stop_live.setMinimumHeight(40)
        self.btn_stop_live.setStyleSheet("""
            QPushButton { 
                background-color: #cc3333; 
                color: white; 
                font-weight: bold; 
                border-radius: 4px;
                padding: 0 15px;
            }
            QPushButton:hover { background-color: #dd4444; }
            QPushButton:pressed { background-color: #bb2222; }
        """)
        self.btn_stop_live.clicked.connect(self.stop_live_monitoring)
        self.btn_stop_live.setVisible(False)
        
        # Analyze Button
        self.btn_analyze = QPushButton("ANALYZE SIGNAL")
        self.btn_analyze.setMinimumHeight(40)
        self.btn_analyze.setStyleSheet("""
            QPushButton { 
                background-color: #007acc; 
                color: white; 
                font-weight: bold; 
                border-radius: 4px;
            }
            QPushButton:hover { background-color: #0094f7; }
            QPushButton:pressed { background-color: #005c99; }
            QPushButton:disabled { background-color: #555; color: #aaa; }
        """)
        self.btn_analyze.clicked.connect(self.run_analysis_on_current_data)
        self.btn_analyze.setEnabled(False) # Disabled until data is loaded
        
        # Live Status Indicator
        self.lbl_live_status = QLabel("")
        self.lbl_live_status.setStyleSheet("color: #ff6600; font-weight: bold;")
        self.lbl_live_status.setVisible(False)
        
        self.lbl_system_status = QLabel("SYSTEM: ONLINE")
        self.lbl_system_status.setStyleSheet("color: #32c850; font-weight: bold;")
        
        layout.addWidget(self.btn_connect)
        layout.addWidget(self.btn_stop_live)
        layout.addWidget(self.btn_analyze)
        layout.addStretch()
        layout.addWidget(self.lbl_live_status)
        layout.addWidget(self.lbl_system_status)
        return panel

    def create_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("&File")
        
        load_action = file_menu.addAction("Load CSV/Excel...")
        load_action.setShortcut("Ctrl+O")
        load_action.triggered.connect(self.load_data_dialog)
        
        file_menu.addSeparator()
        
        exit_action = file_menu.addAction("Exit")
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        
        view_menu = menubar.addMenu("&View")
        view_menu.addAction("Toggle Explorer").triggered.connect(lambda: self.panel_explorer.setVisible(not self.panel_explorer.isVisible()))
        view_menu.addAction("Toggle Alarms").triggered.connect(lambda: self.panel_alarms.setVisible(not self.panel_alarms.isVisible()))

        sim_menu = menubar.addMenu("&Simulation")
        sim_menu.addAction("Run Demo Data").triggered.connect(self.trigger_demo_mode)

    # --- LOGIC ---

    def load_data_dialog(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Open Sensor Data", "", "Data Files (*.csv *.xlsx *.txt);;All Files (*)")
        if fname:
            self.load_file(fname)

    def load_file(self, filepath):
        self.status_label.setText(f"Loading {os.path.basename(filepath)}...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Indeterminate spinner
        self.btn_analyze.setEnabled(False)
        
        # Start Worker
        self.loader_worker = FileLoadWorker(filepath)
        self.loader_worker.finished.connect(self.on_file_loaded)
        self.loader_worker.error.connect(self.on_load_error)
        self.loader_worker.start()

    def on_file_loaded(self, data_dict, filepath):
        self.progress_bar.setVisible(False)
        self.loader_worker = None
        
        try:
            # Smart Column Selection from the Loaded Data Dictionary
            value_col = None
            candidates = ['value', 'signal', 'data', 'sensor_value', 'v']
            cols_lower = {col.lower(): col for col in data_dict.keys()}
            
            for candidate in candidates:
                if candidate in cols_lower:
                    value_col = cols_lower[candidate]
                    break
            
            if value_col is None:
                numeric_cols = list(data_dict.keys())
                if len(numeric_cols) == 1:
                    value_col = numeric_cols[0]
                else:
                    # Ask User (Now we are in Main Thread, so safe to popup)
                    col, ok = QInputDialog.getItem(self, "Select Signal Column", 
                                                 "Multiple numeric columns found.\nPlease select the sensor data column:", 
                                                 numeric_cols, 0, False)
                    if ok and col:
                        value_col = col
                    else:
                        self.status_label.setText("Load Cancelled")
                        return

            self.current_data = data_dict[value_col]
            
            # --- Sampling Rate Logic ---
            # If we don't have a time column, ask for Sampling Rate
            time_col = None
            for col in data_dict.keys():
                if 'time' in col.lower() or 'date' in col.lower():
                    time_col = col
                    break
            
            time_axis = None
            self.sampling_rate = 1.0
            
            if time_col:
                # Use existing time column (simplified, assuming floats or simple conversion)
                # In real app, might need datetime parsing
                pass 
            else:
                # Ask User for Rate
                rate, ok = QInputDialog.getDouble(self, "Sampling Rate", 
                                                "Enter Sampling Rate (Hz):\n(1.0 Hz = 1 sample/sec)", 
                                                value=1.0, min=0.001, max=100000.0, decimals=3)
                if ok:
                    self.sampling_rate = rate
                
                # Generate Time Axis
                n_points = len(self.current_data)
                time_axis = np.arange(n_points) / self.sampling_rate
            
            # Update UI
            self.dashboard.oscilloscope.update_data(self.current_data, x=time_axis)
            self.btn_analyze.setEnabled(True)
            
            # Store data for this sensor
            if self.current_sensor_path:
                self.sensor_data[self.current_sensor_path] = self.current_data
                self.status_label.setText(f"Loaded {len(self.current_data)} pts → {self.current_sensor_path}")
            else:
                self.status_label.setText(f"Loaded {len(self.current_data)} points (no sensor selected)")
            
            self.panel_alarms.add_alarm(datetime.now().strftime("%H:%M:%S"), "INFO", "System", f"File Loaded: {os.path.basename(filepath)}")
            
        except Exception as e:
             self.on_load_error(str(e))
    
    def on_sensor_selected(self, sensor_path):
        """Handle sensor selection from Field Explorer"""
        self.current_sensor_path = sensor_path
        self.status_label.setText(f"Selected: {sensor_path}")
        
        # Update Oscilloscope
        if self.current_sensor_path in self.sensor_data:
            self.current_data = self.sensor_data[self.current_sensor_path]
            # Time axis recreation (simplified, assumes 1Hz or stored with data if dict)
            # For now, just using indices or recreating based on stored sampling rate if available
            # Note: A robust implementation would store (data, time_axis) tuple
            n_points = len(self.current_data)
            self.sampling_rate = getattr(self, 'sampling_rate', 1.0) # Ensure sampling_rate exists
            time_axis = np.arange(n_points) / self.sampling_rate # Reusing last rate, improvable
            self.dashboard.oscilloscope.update_data(self.current_data, x=time_axis)
            self.status_label.setText(f"Selected: {self.current_sensor_path} ({n_points} pts)")
            self.btn_analyze.setEnabled(True)
        else:
            self.current_data = None
            self.dashboard.oscilloscope.update_data([], x=None)
            self.status_label.setText(f"Selected: {self.current_sensor_path} (No Data)")
            self.btn_analyze.setEnabled(False)
            
        # CLEAR ANALYSIS RESULTS ON SENSOR SWITCH (First clear, then check for cached result)
        # Use QTimer to ensure it happens after any pending events
        # BUT if we have cached results, we should restore them instead of just clearing!
        
        from PyQt6.QtCore import QTimer
        # Use lambda to capture current path for consistency, though self.current_sensor_path is fine
        QTimer.singleShot(0, self._update_analysis_view)

    def _update_analysis_view(self):
        """Restores cached results if available, otherwise clears view"""
        if self.current_sensor_path and self.current_sensor_path in self.sensor_analysis_results:
            # Restore cached result
            result = self.sensor_analysis_results[self.current_sensor_path]
            
            # Restore Metrics & Health
            self.results_panel.setVisible(True)
            self.results_panel.update_results(result)
            
            # Restore Trend Chart
            metrics = result.get("metrics", {})
            trend = metrics.get("trend", [])
            residuals = metrics.get("residuals", [])
            self.dashboard.trend_view.update_data(trend, residuals)
            
            self.panel_alarms.add_alarm(datetime.now().strftime("%H:%M:%S"), "INFO", "System", f"Restored analysis for: {os.path.basename(self.current_sensor_path)}")
        else:
            # No cached analysis, clear view
            self.dashboard.trend_view.clear()
            self.results_panel.clear()
            self.results_panel.setVisible(False)


    def on_load_error(self, error_msg):
        self.progress_bar.setVisible(False)
        self.loader_worker = None
        self.status_label.setText("Load Failed")
        
        if "Out of memory" in error_msg:
             QMessageBox.critical(self, "Memory Error", "The file is too large to load in this version.")
        else:
             QMessageBox.critical(self, "Load Error", f"Could not load file:\n{error_msg}")
             
        logger.error(f"File load error: {error_msg}")

    def trigger_demo_mode(self):
        self.status_label.setText("Generating Demo Data...")
        self.current_data = self.bridge.generate_demo_data(1000)
        self.dashboard.oscilloscope.update_data(self.current_data)
        self.btn_analyze.setEnabled(True)
        self.run_analysis_on_current_data()

    def run_analysis_on_current_data(self):
        if not self.current_data:
            return

        self.btn_analyze.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0) # Indeterminate
        self.status_label.setText("Analyzing...")
        
        # Debug log
        logger.info(f"Running analysis on {len(self.current_data)} data points")
        logger.info(f"Data sample (first 5): {self.current_data[:5] if len(self.current_data) >= 5 else self.current_data}")
        
        # Create a COPY of current_data to prevent race conditions
        data_to_analyze = list(self.current_data)
        
        self.worker = AnalysisWorker(self.bridge, data_to_analyze)
        self.worker.finished.connect(self.on_analysis_finished)
        self.worker.error.connect(self.on_analysis_error)
        self.worker.start()

    def on_analysis_finished(self, result):
        from PyQt6.QtCore import QThread
        logger.info(f"on_analysis_finished running on thread: {QThread.currentThread()} (Main Thread should be: {self.thread()})")
        
        self.cleanup_worker()
        
        # Store result for persistence
        if self.current_sensor_path:
            self.sensor_analysis_results[self.current_sensor_path] = result
        
        # Update Trend Chart
        metrics = result.get("metrics", {})
        trend = metrics.get("trend", [])
        residuals = metrics.get("residuals", [])
        
        logger.info(f"Analysis result: trend length={len(trend)}, residuals length={len(residuals)}")
        if trend:
            logger.info(f"Trend first 3: {trend[:3]}, last 3: {trend[-3:]}")
        
        # Force clear and update on main thread
        self.dashboard.trend_view.update_data(trend, residuals)
        
        # Force Qt to process events and repaint
        from PyQt6.QtWidgets import QApplication
        QApplication.processEvents()
        
        # Update Alarms/Health
        health = result.get("health", {})
        score = health.get("score", 100)
        diagnosis = health.get("diagnosis", "Normal")
        
        self.panel_alarms.add_alarm(datetime.now().strftime("%H:%M:%S"), 
                                    "CRITICAL" if score < 60 else "WARNING" if score < 85 else "INFO",
                                    "AnalysisEngine", 
                                    f"Score: {score:.1f} | {diagnosis}")
        
        self.status_label.setText(f"Analysis Done. Score: {score:.1f}")
        
        # Show Results Panel
        self.results_panel.setVisible(True)
        self.results_panel.update_results(result)

    def on_analysis_error(self, error_msg):
        self.cleanup_worker()
        self.status_label.setText("Error")
        QMessageBox.warning(self, "Analysis Failed", error_msg)
        self.panel_alarms.add_alarm(datetime.now().strftime("%H:%M:%S"), "CRITICAL", "AnalysisEngine", str(error_msg))

    def cleanup_worker(self):
        self.btn_analyze.setEnabled(True)
        self.progress_bar.setVisible(False)
        if self.worker:
            self.worker.quit()
            self.worker.wait()
            self.worker = None

    # --- CONNECTION DIALOG ---
    
    def show_connection_dialog(self):
        """Show the connection settings dialog."""
        dialog = ConnectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            source_type = dialog.get_source_type()
            
            if source_type == ConnectionDialog.SOURCE_CSV:
                # Use existing file dialog
                self.load_data_dialog()
            elif source_type in (ConnectionDialog.SOURCE_TCP, ConnectionDialog.SOURCE_RTU):
                # Start Modbus live monitoring (TCP or RTU)
                config = dialog.get_modbus_config()
                self.start_live_monitoring(config)

    # --- LIVE MONITORING (Modbus TCP/RTU) ---
    
    def start_live_monitoring(self, config: dict):
        """
        Start live Modbus monitoring with UI integration.
        Supports both TCP and RTU connection types.
        
        Args:
            config: Dict with connection_type and relevant parameters
        """
        if self.modbus_worker and self.modbus_worker.isRunning():
            QMessageBox.warning(self, "Warning", "Live monitoring already running. Stop it first.")
            return
        
        connection_type = config.get("connection_type", "TCP")
        
        # Build connection string for logging
        if connection_type == "TCP":
            conn_str = f"{config.get('ip_address')}:{config.get('tcp_port', 502)}"
        else:
            conn_str = f"{config.get('serial_port')} @ {config.get('baudrate')}bps"
        
        logger.info(f"Starting {connection_type} monitoring: {conn_str}")
        
        # Reset live data state
        self.live_data_buffer = []
        self.live_sample_count = 0
        self.is_live_mode = True
        
        # Clear oscilloscope buffer
        self.dashboard.oscilloscope.clear_realtime_buffer()
        
        # Create worker based on connection type
        if connection_type == "TCP":
            self.modbus_worker = ModbusWorker(
                connection_type="TCP",
                ip_address=config.get("ip_address", "192.168.1.100"),
                tcp_port=config.get("tcp_port", 502),
                register_address=config.get("register_address", 0),
                slave_id=config.get("slave_id", 1),
                scale_factor=config.get("scale_factor", 1.0),
                read_interval=1.0
            )
        else:  # RTU
            self.modbus_worker = ModbusWorker(
                connection_type="RTU",
                serial_port=config.get("serial_port", "COM1"),
                baudrate=config.get("baudrate", 19200),
                parity=config.get("parity", "E"),
                stopbits=config.get("stopbits", 1),
                bytesize=config.get("bytesize", 8),
                register_address=config.get("register_address", 0),
                slave_id=config.get("slave_id", 1),
                scale_factor=config.get("scale_factor", 1.0),
                read_interval=1.0
            )
        
        # Connect signals
        self.modbus_worker.data_received.connect(self._on_modbus_data_received)
        self.modbus_worker.error_occurred.connect(self._on_modbus_error)
        self.modbus_worker.connection_status.connect(self._on_modbus_connection_status)
        
        # Start worker
        self.modbus_worker.start()
        
        # Update UI
        self.btn_stop_live.setVisible(True)
        self.btn_connect.setEnabled(False)
        self.lbl_live_status.setText(f"● LIVE ({connection_type})")
        self.lbl_live_status.setVisible(True)
        self.status_label.setText(f"Connecting to {conn_str}...")
        
        self.panel_alarms.add_alarm(
            datetime.now().strftime("%H:%M:%S"), 
            "INFO", 
            "ModbusWorker", 
            f"Started {connection_type} monitoring: {conn_str}"
        )
    
    def stop_live_monitoring(self):
        """Stop the Modbus worker and reset UI."""
        if self.modbus_worker:
            logger.info("Stopping Modbus worker...")
            self.modbus_worker.stop()
            self.modbus_worker = None
        
        # Reset state
        self.is_live_mode = False
        
        # Update UI
        self.btn_stop_live.setVisible(False)
        self.btn_connect.setEnabled(True)
        self.lbl_live_status.setVisible(False)
        self.status_label.setText("Live monitoring stopped")
        
        self.panel_alarms.add_alarm(
            datetime.now().strftime("%H:%M:%S"),
            "INFO",
            "ModbusWorker",
            "Live monitoring stopped"
        )
    
    def _on_modbus_data_received(self, value: float, timestamp: float):
        """Handle incoming Modbus data - update oscilloscope and buffer for analysis."""
        # Update oscilloscope in real-time (scrolling display)
        self.dashboard.oscilloscope.update_realtime(value, timestamp)
        
        # Add to analysis buffer
        self.live_data_buffer.append(value)
        self.live_sample_count += 1
        
        # Update status with sample count
        self.status_label.setText(f"LIVE: {len(self.live_data_buffer)} samples | Last: {value:.2f}")
        
        # Trigger analysis every ANALYSIS_TRIGGER_COUNT samples (60 = 1 minute at 1Hz)
        if self.live_sample_count >= self.ANALYSIS_TRIGGER_COUNT:
            self.live_sample_count = 0  # Reset counter
            self._trigger_live_analysis()
    
    def _trigger_live_analysis(self):
        """Trigger analysis on buffered live data."""
        if len(self.live_data_buffer) < 50:  # Minimum data points required
            logger.warning(f"Not enough data for analysis: {len(self.live_data_buffer)} points")
            return
        
        logger.info(f"Triggering live analysis on {len(self.live_data_buffer)} points")
        
        # Use last 300 points (5 minutes) or all available
        analysis_data = self.live_data_buffer[-300:] if len(self.live_data_buffer) > 300 else list(self.live_data_buffer)
        
        # Set as current data for analysis
        self.current_data = analysis_data
        
        # Run analysis (will update UI when complete)
        self.run_analysis_on_current_data()
        
        self.panel_alarms.add_alarm(
            datetime.now().strftime("%H:%M:%S"),
            "INFO",
            "LiveAnalysis",
            f"Auto-analysis triggered ({len(analysis_data)} points)"
        )
    
    def _on_modbus_error(self, error_msg: str):
        """Handle Modbus errors."""
        logger.error(f"[MODBUS ERROR] {error_msg}")
        self.panel_alarms.add_alarm(
            datetime.now().strftime("%H:%M:%S"),
            "WARNING",
            "ModbusWorker",
            error_msg
        )
    
    def _on_modbus_connection_status(self, connected: bool):
        """Handle Modbus connection status changes."""
        status = "CONNECTED" if connected else "DISCONNECTED"
        logger.info(f"[MODBUS STATUS] {status}")
        
        if connected:
            self.lbl_system_status.setText("SYSTEM: LIVE")
            self.lbl_system_status.setStyleSheet("color: #ff6600; font-weight: bold;")
        else:
            self.lbl_system_status.setText("SYSTEM: OFFLINE")
            self.lbl_system_status.setStyleSheet("color: #cc3333; font-weight: bold;")
        
        self.panel_alarms.add_alarm(
            datetime.now().strftime("%H:%M:%S"),
            "INFO" if connected else "WARNING",
            "ModbusWorker",
            f"Connection: {status}"
        )
