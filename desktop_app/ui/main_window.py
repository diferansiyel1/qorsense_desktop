import sys
import os
import logging
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QLabel, QFrame, QMessageBox, QProgressBar,
                             QFileDialog, QInputDialog)
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
from backend.models import SensorConfig

logger = logging.getLogger("MainWindow")

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
        
        self.lbl_system_status = QLabel("SYSTEM: ONLINE")
        self.lbl_system_status.setStyleSheet("color: #32c850; font-weight: bold;")
        
        layout.addWidget(self.btn_analyze)
        layout.addStretch()
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

