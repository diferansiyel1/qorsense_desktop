import logging
import os
import sys
from datetime import datetime

import numpy as np
from backend.models import SENSOR_CATALOG, SensorConfig
from desktop_app.core.analyzer_bridge import AnalyzerBridge
from desktop_app.core.sensor_simulation import (
    generate_fault_sensor_data,
    generate_healthy_sensor_data,
)

# Import modular UI components
from desktop_app.ui.charts import AnalysisDashboard, MultiSensorOscilloscope
from desktop_app.ui.multi_sensor_dialog import MultiSensorConnectionDialog
from desktop_app.ui.panels import AlarmPanel, FieldExplorerPanel
from desktop_app.ui.results_panel import ResultsPanel
from desktop_app.ui.sensor_status_panel import SensorStatusPanel
from desktop_app.workers.analysis_worker import AnalysisWorker
from desktop_app.workers.file_loader import FileLoadWorker

# Import list_available_ports for COM port scanning
from desktop_app.workers.live_worker import ModbusWorker, list_available_ports
from PyQt6.QtCore import Qt, QThread
from PyQt6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

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

    # Hamilton VisiFerm sensor defaults (per VisiFerm Programmer's Manual)
    # VisiFerm uses: 19200 baud, No Parity, 8 data bits, 2 stop bits
    HAMILTON_BAUD = 19200
    HAMILTON_PARITY = "N"  # None (VisiFerm default)
    HAMILTON_STOPBITS = 2   # 2 stop bits when parity=None
    HAMILTON_BYTESIZE = 8

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connection Settings")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)

        # --- Sensor Identity Selection ---
        sensor_group = QGroupBox("Sensör Kimliği")
        sensor_layout = QFormLayout(sensor_group)

        # Collect all sensor types from SENSOR_CATALOG
        all_sensor_types = []
        for category, sensors in SENSOR_CATALOG.items():
            all_sensor_types.extend(sensors.keys())
        all_sensor_types = sorted(set(all_sensor_types))

        self.type_combo = QComboBox()
        self.type_combo.addItems(all_sensor_types)
        self.type_combo.currentTextChanged.connect(self._update_units)
        sensor_layout.addRow("Sensör Tipi:", self.type_combo)

        self.unit_combo = QComboBox()
        sensor_layout.addRow("Birim:", self.unit_combo)

        # Initialize units for first sensor type
        if all_sensor_types:
            self._update_units(all_sensor_types[0])

        layout.addWidget(sensor_group)

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
        self.parity_combo.setCurrentIndex(0)  # None - Hamilton VisiFerm default
        rtu_layout.addRow("Parity:", self.parity_combo)

        # Stop Bits
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "2"])
        self.stopbits_combo.setCurrentText("2")  # Hamilton VisiFerm default (2 when parity=None)
        rtu_layout.addRow("Stop Bits:", self.stopbits_combo)

        # Register Address
        self.rtu_register_input = QSpinBox()
        self.rtu_register_input.setRange(0, 65535)
        self.rtu_register_input.setValue(0)
        rtu_layout.addRow("Register Address:", self.rtu_register_input)

        # Register Count
        self.rtu_register_count_input = QSpinBox()
        self.rtu_register_count_input.setRange(1, 125)
        self.rtu_register_count_input.setValue(2)
        self.rtu_register_count_input.setToolTip("Number of registers to read (Visiferm: 10)")
        rtu_layout.addRow("Register Count:", self.rtu_register_count_input)

        # Value Register Offset
        self.rtu_value_offset_input = QSpinBox()
        self.rtu_value_offset_input.setRange(0, 123)
        self.rtu_value_offset_input.setValue(0)
        self.rtu_value_offset_input.setToolTip("Offset within response where value starts (Visiferm: 2)")
        rtu_layout.addRow("Value Offset:", self.rtu_value_offset_input)

        # Data Type
        self.rtu_datatype_combo = QComboBox()
        self.rtu_datatype_combo.addItems(["float32_be", "float32_le", "float32_ws", "float32_bs", "int16", "uint16"])
        self.rtu_datatype_combo.setCurrentText("float32_ws")  # Visiferm uses word-swapped
        rtu_layout.addRow("Data Type:", self.rtu_datatype_combo)

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

        # Visiferm Preset Buttons
        preset_layout = QHBoxLayout()
        btn_o2 = QPushButton("📍 Visiferm O2")
        btn_o2.setToolTip("Hamilton Visiferm PMC1 (Oxygen)")
        btn_o2.clicked.connect(self._apply_visiferm_o2_preset)
        btn_temp = QPushButton("📍 Visiferm Temp")
        btn_temp.setToolTip("Hamilton Visiferm PMC6 (Temperature)")
        btn_temp.clicked.connect(self._apply_visiferm_temp_preset)
        preset_layout.addWidget(btn_o2)
        preset_layout.addWidget(btn_temp)
        rtu_layout.addRow("Preset:", preset_layout)

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

    def _update_units(self, sensor_type: str):
        """Seçilen sensör tipine göre birim listesini günceller."""
        self.unit_combo.clear()
        # SENSOR_CATALOG yapısını tara (Kategori -> Tip -> Birimler)
        found = False
        for cat_name, sensors in SENSOR_CATALOG.items():
            if sensor_type in sensors:
                self.unit_combo.addItems(sensors[sensor_type])
                found = True
                break
        if not found:
            self.unit_combo.addItem("-")

    def get_metadata(self) -> dict:
        """Seçilen sensör tipi ve birimini döndürür."""
        return {
            "sensor_type": self.type_combo.currentText(),
            "unit": self.unit_combo.currentText()
        }

    def get_source_type(self) -> str:
        """Return selected source type."""
        if self.radio_tcp.isChecked():
            return self.SOURCE_TCP
        if self.radio_rtu.isChecked():
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
            "register_count": self.rtu_register_count_input.value(),
            "value_register_offset": self.rtu_value_offset_input.value(),
            "data_type": self.rtu_datatype_combo.currentText(),
            "slave_id": self.rtu_slave_input.value(),
            "scale_factor": self.rtu_scale_input.value()
        }

    def get_modbus_config(self) -> dict:
        """Return Modbus configuration based on selected type."""
        if self.radio_tcp.isChecked():
            return self.get_tcp_config()
        if self.radio_rtu.isChecked():
            return self.get_rtu_config()
        return {}

    def _apply_visiferm_o2_preset(self):
        """Apply Hamilton Visiferm PMC1 (Oxygen) preset settings."""
        self.baud_combo.setCurrentText("19200")
        self.parity_combo.setCurrentIndex(0)  # None
        self.stopbits_combo.setCurrentText("2")
        self.rtu_register_input.setValue(2089)
        self.rtu_register_count_input.setValue(10)
        self.rtu_value_offset_input.setValue(2)
        self.rtu_datatype_combo.setCurrentText("float32_ws")
        self.rtu_slave_input.setValue(2)
        self.rtu_scale_input.setValue(1.0)

    def _apply_visiferm_temp_preset(self):
        """Apply Hamilton Visiferm PMC6 (Temperature) preset settings."""
        self.baud_combo.setCurrentText("19200")
        self.parity_combo.setCurrentIndex(0)  # None
        self.stopbits_combo.setCurrentText("2")
        self.rtu_register_input.setValue(2409)
        self.rtu_register_count_input.setValue(10)
        self.rtu_value_offset_input.setValue(2)
        self.rtu_datatype_combo.setCurrentText("float32_ws")
        self.rtu_slave_input.setValue(2)
        self.rtu_scale_input.setValue(1.0)


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
        self._selected_live_sensor = None  # Currently selected sensor for analysis

        # --- UI SETUP ---
        self.setup_ui()

    def setup_ui(self):
        # 1. Central Dashboard
        self.dashboard = AnalysisDashboard() # Charts

        # Multi-sensor oscilloscope for live data
        self.multi_oscilloscope = MultiSensorOscilloscope(max_points=300)

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
        self.panel_explorer.load_csv_requested.connect(self.on_csv_load_requested)
        self.panel_explorer.live_sensor_settings_requested.connect(self._show_live_sensor_settings)
        self.panel_explorer.live_sensor_disconnect_requested.connect(self._disconnect_live_sensor)
        self.panel_explorer.live_sensor_selected.connect(self._on_live_sensor_selected)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.panel_explorer)

        # Sensor Status Panel (for multi-sensor monitoring)
        self.sensor_status_panel = SensorStatusPanel(self)
        self.sensor_status_panel.sensor_selected.connect(self._on_live_sensor_selected)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.sensor_status_panel)
        self.sensor_status_panel.setVisible(False)  # Hidden until live mode

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

        # Multi-Sensor Connection Button
        self.btn_multi_sensor = QPushButton("📊 Multi-Sensor")
        self.btn_multi_sensor.setMinimumHeight(40)
        self.btn_multi_sensor.setStyleSheet("""
            QPushButton { 
                background-color: #7c3aed; 
                color: white; 
                font-weight: bold; 
                border-radius: 4px;
                padding: 0 15px;
            }
            QPushButton:hover { background-color: #8b5cf6; }
            QPushButton:pressed { background-color: #6d28d9; }
        """)
        self.btn_multi_sensor.clicked.connect(self.show_multi_sensor_dialog)

        layout.addWidget(self.btn_connect)
        layout.addWidget(self.btn_multi_sensor)
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

        # Healthy Data Action
        healthy_action = sim_menu.addAction("🟢 Run Healthy Data")
        healthy_action.triggered.connect(self.trigger_healthy_simulation)

        sim_menu.addSeparator()

        # Fault Data Submenu
        fault_menu = sim_menu.addMenu("🔴 Run Fault Data")

        fault_actions = [
            ("⚙️ Bearing Degradation", "bearing_degradation"),
            ("📉 Sensor Drift", "sensor_drift"),
            ("⚡ Intermittent Contact", "intermittent_contact"),
            ("🔥 Thermal Runaway", "thermal_runaway"),
            ("💧 Pump Cavitation", "pump_cavitation"),
            ("🔀 Mixed Degradation", "mixed_degradation"),
        ]

        for label, fault_type in fault_actions:
            action = fault_menu.addAction(label)
            action.triggered.connect(lambda checked, ft=fault_type: self.trigger_fault_simulation(ft))

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

    def on_csv_load_requested(self, sensor_path):
        """Handle CSV load request from Field Explorer context menu"""
        # First, select the sensor
        self.current_sensor_path = sensor_path
        self.status_label.setText(f"Selected: {sensor_path}")

        # Then open file dialog for CSV loading
        fname, _ = QFileDialog.getOpenFileName(
            self,
            f"Load CSV Data for {os.path.basename(sensor_path)}",
            "",
            "Data Files (*.csv *.xlsx *.txt);;All Files (*)"
        )
        if fname:
            self.load_file(fname)

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
        """Legacy demo mode - redirects to healthy simulation."""
        self.trigger_healthy_simulation()

    def trigger_healthy_simulation(self):
        """Generate realistic healthy sensor data for testing."""
        self.status_label.setText("🟢 Generating Healthy Sensor Data...")

        # Generate 5 minutes of healthy data at 1Hz
        self.current_data = generate_healthy_sensor_data(n_samples=300, base_value=25.0)

        # Generate time axis
        n_points = len(self.current_data)
        self.sampling_rate = 1.0
        time_axis = np.arange(n_points) / self.sampling_rate

        self.dashboard.oscilloscope.update_data(self.current_data, x=time_axis)
        self.btn_analyze.setEnabled(True)

        self.panel_alarms.add_alarm(
            datetime.now().strftime("%H:%M:%S"),
            "INFO",
            "Simulation",
            f"Generated {n_points} healthy sensor samples"
        )

        self.status_label.setText(f"🟢 Healthy Data: {n_points} samples @ {self.sampling_rate}Hz")
        self.run_analysis_on_current_data()

    def trigger_fault_simulation(self, fault_type: str):
        """Generate sensor data with specific fault pattern.
        
        Args:
            fault_type: One of 'bearing_degradation', 'sensor_drift', 
                       'intermittent_contact', 'thermal_runaway',
                       'pump_cavitation', 'mixed_degradation'
        """
        fault_labels = {
            "bearing_degradation": "⚙️ Bearing Degradation",
            "sensor_drift": "📉 Sensor Drift",
            "intermittent_contact": "⚡ Intermittent Contact",
            "thermal_runaway": "🔥 Thermal Runaway",
            "pump_cavitation": "💧 Pump Cavitation",
            "mixed_degradation": "🔀 Mixed Degradation",
        }

        label = fault_labels.get(fault_type, fault_type)
        self.status_label.setText(f"🔴 Generating {label} Data...")

        # Generate 5 minutes of fault data at 1Hz with 80% severity
        self.current_data = generate_fault_sensor_data(
            fault_type=fault_type,
            n_samples=300,
            base_value=25.0,
            severity=0.8
        )

        # Generate time axis
        n_points = len(self.current_data)
        self.sampling_rate = 1.0
        time_axis = np.arange(n_points) / self.sampling_rate

        self.dashboard.oscilloscope.update_data(self.current_data, x=time_axis)
        self.btn_analyze.setEnabled(True)

        self.panel_alarms.add_alarm(
            datetime.now().strftime("%H:%M:%S"),
            "WARNING",
            "Simulation",
            f"Generated {n_points} samples with fault: {label}"
        )

        self.status_label.setText(f"🔴 Fault Data [{label}]: {n_points} samples")
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
                metadata = dialog.get_metadata()
                logger.info(f"CSV mode selected with sensor: {metadata}")
                self.load_data_dialog()
            elif source_type in (ConnectionDialog.SOURCE_TCP, ConnectionDialog.SOURCE_RTU):
                # Start Modbus live monitoring (TCP or RTU)
                config = dialog.get_modbus_config()
                metadata = dialog.get_metadata()
                logger.info(f"Modbus {source_type.upper()} mode selected with sensor: {metadata}")
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
            # Import SensorConfig from workers.models for proper configuration
            from desktop_app.workers.models import ConnectionType, DataType
            from desktop_app.workers.models import SensorConfig as WorkerSensorConfig

            # Map data_type string to DataType enum
            data_type_map = {
                "float32_be": DataType.FLOAT32_BE,
                "float32_le": DataType.FLOAT32_LE,
                "float32_ws": DataType.FLOAT32_WS,
                "float32_bs": DataType.FLOAT32_BS,
                "int16": DataType.INT16,
                "uint16": DataType.UINT16,
            }
            data_type = data_type_map.get(config.get("data_type", "float32_ws"), DataType.FLOAT32_WS)

            # Create SensorConfig with all parameters
            sensor_config = WorkerSensorConfig(
                name="modbus_sensor",
                connection_type=ConnectionType.RTU,
                serial_port=config.get("serial_port", "COM1"),
                baudrate=config.get("baudrate", 19200),
                parity=config.get("parity", "N"),
                stopbits=config.get("stopbits", 2),
                bytesize=config.get("bytesize", 8),
                slave_id=config.get("slave_id", 1),
                register_address=config.get("register_address", 0),
                register_count=config.get("register_count", 2),
                data_type=data_type,
                scale_factor=config.get("scale_factor", 1.0),
                value_register_offset=config.get("value_register_offset", 0),
                poll_interval=1.0
            )

            self.modbus_worker = ModbusWorker(sensors=[sensor_config])

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
        self._selected_live_sensor = None

        # Clear multi-sensor components
        self.multi_oscilloscope.clear_all()
        for sensor_id in list(self.multi_oscilloscope.sensors.keys()):
            self.multi_oscilloscope.remove_sensor(sensor_id)
        self.sensor_status_panel.clear_all()
        self.sensor_status_panel.setVisible(False)
        self.panel_explorer.clear_live_sensors()  # Clear live sensors from left panel

        # Restore original oscilloscope in dashboard
        self.dashboard.splitter.replaceWidget(0, self.dashboard.oscilloscope)

        # Update UI
        self.btn_stop_live.setVisible(False)
        self.btn_connect.setEnabled(True)
        self.btn_multi_sensor.setEnabled(True)
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

    # =========================================================================
    # MULTI-SENSOR MONITORING
    # =========================================================================

    def show_multi_sensor_dialog(self):
        """Show multi-sensor connection configuration dialog."""
        dialog = MultiSensorConnectionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            connection_type = dialog.get_connection_type()
            connection_params = dialog.get_connection_params()
            sensors = dialog.get_sensors()

            self.start_multi_sensor_monitoring(connection_type, connection_params, sensors)

    def start_multi_sensor_monitoring(self, connection_type: str, connection_params: dict, sensors: list):
        """
        Start monitoring multiple sensors.
        
        Args:
            connection_type: 'TCP' or 'RTU'
            connection_params: Connection parameters (ip/port or serial params)
            sensors: List of sensor configurations
        """
        from desktop_app.workers.models import ConnectionType, DataType
        from desktop_app.workers.models import SensorConfig as WorkerSensorConfig

        # Stop any existing monitoring
        self.stop_live_monitoring()

        # Create SensorConfig objects for each sensor
        sensor_configs = []
        for sensor in sensors:
            # Map data type string to enum
            data_type_map = {
                "FLOAT32_BE": DataType.FLOAT32_BE,
                "FLOAT32_LE": DataType.FLOAT32_LE,
                "FLOAT32_BS": DataType.FLOAT32_BS,
                "FLOAT32_WS": DataType.FLOAT32_WS,
                "INT16": DataType.INT16,
                "UINT16": DataType.UINT16,
                "INT32_BE": DataType.INT32_BE,
                "UINT32_BE": DataType.UINT32_BE,
            }

            config_dict = {
                "name": sensor["name"],
                "register_address": sensor["register_address"],
                "register_count": sensor.get("register_count", 10),
                "value_register_offset": sensor.get("value_register_offset", 2),
                "data_type": data_type_map.get(sensor["data_type"], DataType.FLOAT32_WS),
                "scale_factor": sensor["scale_factor"],
                "slave_id": sensor.get("slave_id", 1),
            }

            if connection_type == "TCP":
                config_dict["connection_type"] = ConnectionType.TCP
                config_dict["ip"] = connection_params.get("ip_address", "127.0.0.1")
                config_dict["port"] = connection_params.get("tcp_port", 502)
            else:
                config_dict["connection_type"] = ConnectionType.RTU
                config_dict["serial_port"] = connection_params.get("serial_port", "COM1")
                config_dict["baudrate"] = connection_params.get("baudrate", 19200)
                config_dict["parity"] = connection_params.get("parity", "N")
                config_dict["stopbits"] = connection_params.get("stopbits", 1)
                config_dict["bytesize"] = connection_params.get("bytesize", 8)

            sensor_configs.append(WorkerSensorConfig(**config_dict))

        # Add sensors to UI components (including Field Explorer)
        for sensor in sensors:
            sensor_name = sensor["name"]
            # Build config for storage
            sensor_config = {
                "connection_type": connection_type,
                "connection_params": connection_params,
                "sensor": sensor
            }
            self.multi_oscilloscope.add_sensor(sensor_name, sensor_name)
            self.sensor_status_panel.add_sensor(sensor_name, sensor_name)
            self.panel_explorer.add_live_sensor(sensor_name, sensor_name, sensor_config, "connecting")

        # Create and start ModbusWorker with multiple sensors
        self.modbus_worker = ModbusWorker(sensors=sensor_configs)

        # Connect signals
        self.modbus_worker.sensor_data_received.connect(self._on_multi_sensor_data)
        self.modbus_worker.error_occurred.connect(self._on_modbus_error)
        self.modbus_worker.connection_status.connect(self._on_modbus_connection_status)
        self.modbus_worker.device_status_changed.connect(self._on_device_status_changed)

        # Start monitoring
        self.modbus_worker.start()

        # Update UI
        self.is_live_mode = True
        self.btn_stop_live.setVisible(True)
        self.btn_connect.setEnabled(False)
        self.btn_multi_sensor.setEnabled(False)
        self.sensor_status_panel.setVisible(True)

        # Switch to multi-sensor oscilloscope in dashboard
        self.dashboard.splitter.replaceWidget(0, self.multi_oscilloscope)

        sensor_count = len(sensors)
        conn_str = f"{connection_type}: {sensor_count} sensor(s)"
        self.lbl_live_status.setText(f"● LIVE ({conn_str})")
        self.lbl_live_status.setVisible(True)
        self.status_label.setText(f"Monitoring {sensor_count} sensors...")

        self.panel_alarms.add_alarm(
            datetime.now().strftime("%H:%M:%S"),
            "INFO",
            "MultiSensor",
            f"Started monitoring {sensor_count} sensors via {connection_type}"
        )

        # Auto-select first sensor for analysis
        if sensors:
            first_sensor_name = sensors[0]["name"]
            self._selected_live_sensor = first_sensor_name
            self.live_data_buffer = []
            self.live_sample_count = 0
            self.status_label.setText(f"Monitoring {sensor_count} sensors | Analysis: {first_sensor_name}")
            self.panel_alarms.add_alarm(
                datetime.now().strftime("%H:%M:%S"),
                "INFO",
                "AutoSelect",
                f"Auto-selected '{first_sensor_name}' for analysis. Click another sensor in status panel to change."
            )

    def _on_multi_sensor_data(self, sensor_id: str, value: float, timestamp: float):
        """Handle data received from multi-sensor worker."""
        # Update oscilloscope
        self.multi_oscilloscope.update_sensor(sensor_id, value, timestamp)

        # Update status panel
        self.sensor_status_panel.update_sensor(sensor_id, value=value, status="online")

        # Buffer data for selected sensor (for analysis)
        if self._selected_live_sensor == sensor_id:
            self.live_data_buffer.append(value)
            self.live_sample_count += 1

            # Trigger analysis periodically
            if self.live_sample_count >= self.ANALYSIS_TRIGGER_COUNT:
                self.live_sample_count = 0
                self._trigger_live_analysis()

    def _on_device_status_changed(self, sensor_id: str, status: str):
        """Handle device status changes from worker."""
        status_text = status.lower()
        self.sensor_status_panel.set_sensor_status(sensor_id, status_text)
        self.panel_explorer.update_live_sensor_status(sensor_id, status_text)

    def _on_live_sensor_selected(self, sensor_id: str):
        """Handle sensor selection from status panel or Field Explorer."""
        self._selected_live_sensor = sensor_id

        # Try to get data buffer from multi_oscilloscope if available
        if hasattr(self.multi_oscilloscope, 'get_sensor_data'):
            try:
                self.live_data_buffer = list(self.multi_oscilloscope.get_sensor_data(sensor_id))
            except Exception:
                self.live_data_buffer = []
        else:
            self.live_data_buffer = []

        self.live_sample_count = 0

        self.status_label.setText(f"Selected: {sensor_id}")
        self.panel_alarms.add_alarm(
            datetime.now().strftime("%H:%M:%S"),
            "INFO",
            "SensorSelect",
            f"Switched analysis target to: {sensor_id}"
        )

    def _show_live_sensor_settings(self, sensor_id: str):
        """Show connection settings dialog for a live sensor."""
        config = self.panel_explorer.get_live_sensor_config(sensor_id)
        if not config:
            QMessageBox.information(
                self,
                "Sensor Settings",
                f"Sensor: {sensor_id}\n\nNo configuration data available."
            )
            return

        # Build info string from config
        conn_type = config.get("connection_type", "Unknown")
        conn_params = config.get("connection_params", {})
        sensor_info = config.get("sensor", {})

        if conn_type == "TCP":
            conn_str = f"IP: {conn_params.get('ip_address', 'N/A')}:{conn_params.get('tcp_port', 502)}"
        else:
            conn_str = f"Port: {conn_params.get('serial_port', 'N/A')} @ {conn_params.get('baudrate', 19200)}bps"

        info_text = f"""Sensor: {sensor_id}

Connection Type: {conn_type}
{conn_str}

Register Address: {sensor_info.get('register_address', 'N/A')}
Data Type: {sensor_info.get('data_type', 'N/A')}
Scale Factor: {sensor_info.get('scale_factor', 1.0)}
"""

        QMessageBox.information(self, f"Settings: {sensor_id}", info_text)

    def _disconnect_live_sensor(self, sensor_id: str):
        """Disconnect a single live sensor (stops all monitoring for now)."""
        # For simplicity, disconnect all monitoring
        # A more advanced implementation would support per-sensor disconnect
        reply = QMessageBox.question(
            self,
            "Disconnect Sensor",
            f"Disconnect '{sensor_id}'?\n\nNote: This will stop all live monitoring.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.stop_live_monitoring()

