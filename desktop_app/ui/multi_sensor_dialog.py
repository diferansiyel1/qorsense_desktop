"""
Multi-Sensor Connection Dialog.

Advanced dialog for configuring multiple Modbus sensors with shared connection parameters.
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox,
    QPushButton, QRadioButton, QButtonGroup, QStackedWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QDialogButtonBox,
    QMessageBox, QAbstractItemView
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from typing import List, Dict, Any, Optional

from desktop_app.workers.live_worker import list_available_ports


class MultiSensorConnectionDialog(QDialog):
    """
    Dialog for configuring multiple Modbus sensors with shared connection.
    
    Features:
    - Shared connection parameters (IP/Port or COM/Baud)
    - Sensor table for adding multiple sensors
    - Per-sensor: Name, Register Address, Data Type, Scale Factor
    
    Usage:
        >>> dialog = MultiSensorConnectionDialog(parent)
        >>> if dialog.exec() == QDialog.DialogCode.Accepted:
        ...     connection_type = dialog.get_connection_type()
        ...     connection_params = dialog.get_connection_params()
        ...     sensors = dialog.get_sensors()
    """
    
    # Data types supported
    DATA_TYPES = [
        "FLOAT32_BE",      # Big Endian Float
        "FLOAT32_LE",      # Little Endian Float
        "FLOAT32_BS",      # Byte Swapped
        "FLOAT32_WS",      # Word Swapped
        "INT16",
        "UINT16",
        "INT32_BE",
        "UINT32_BE",
    ]
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Multi-Sensor Connection")
        self.setMinimumSize(700, 500)
        
        self._sensors: List[Dict[str, Any]] = []
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # === Connection Type Selection ===
        conn_group = QGroupBox("Connection Type")
        conn_layout = QHBoxLayout(conn_group)
        
        self.radio_tcp = QRadioButton("Modbus TCP")
        self.radio_rtu = QRadioButton("Modbus RTU")
        self.radio_tcp.setChecked(True)
        
        self.conn_button_group = QButtonGroup(self)
        self.conn_button_group.addButton(self.radio_tcp, 0)
        self.conn_button_group.addButton(self.radio_rtu, 1)
        
        conn_layout.addWidget(self.radio_tcp)
        conn_layout.addWidget(self.radio_rtu)
        conn_layout.addStretch()
        layout.addWidget(conn_group)
        
        # === Connection Parameters ===
        self.conn_stack = QStackedWidget()
        
        # TCP Page
        tcp_page = QGroupBox("TCP Connection")
        tcp_layout = QFormLayout(tcp_page)
        
        self.ip_input = QLineEdit("127.0.0.1")
        self.ip_input.setPlaceholderText("192.168.1.100")
        tcp_layout.addRow("IP Address:", self.ip_input)
        
        self.tcp_port_input = QSpinBox()
        self.tcp_port_input.setRange(1, 65535)
        self.tcp_port_input.setValue(5020)
        tcp_layout.addRow("Port:", self.tcp_port_input)
        
        self.conn_stack.addWidget(tcp_page)
        
        # RTU Page
        rtu_page = QGroupBox("RTU Connection")
        rtu_layout = QFormLayout(rtu_page)
        
        # COM Port with refresh
        com_row = QHBoxLayout()
        self.com_port_combo = QComboBox()
        self._refresh_com_ports()
        com_row.addWidget(self.com_port_combo, 1)
        
        btn_refresh = QPushButton("↻")
        btn_refresh.setFixedWidth(30)
        btn_refresh.clicked.connect(self._refresh_com_ports)
        com_row.addWidget(btn_refresh)
        rtu_layout.addRow("COM Port:", com_row)
        
        self.baud_combo = QComboBox()
        self.baud_combo.addItems(["9600", "19200", "38400", "57600", "115200"])
        self.baud_combo.setCurrentText("19200")
        rtu_layout.addRow("Baud Rate:", self.baud_combo)
        
        self.parity_combo = QComboBox()
        self.parity_combo.addItems(["None (N)", "Even (E)", "Odd (O)"])
        self.parity_combo.setCurrentIndex(0)
        rtu_layout.addRow("Parity:", self.parity_combo)
        
        self.stopbits_combo = QComboBox()
        self.stopbits_combo.addItems(["1", "2"])
        self.stopbits_combo.setCurrentText("2")
        rtu_layout.addRow("Stop Bits:", self.stopbits_combo)
        
        self.conn_stack.addWidget(rtu_page)
        layout.addWidget(self.conn_stack)
        
        # Connect radio buttons
        self.radio_tcp.toggled.connect(lambda: self.conn_stack.setCurrentIndex(0))
        self.radio_rtu.toggled.connect(lambda: self.conn_stack.setCurrentIndex(1))
        
        # === Sensor Table ===
        sensor_group = QGroupBox("Sensors")
        sensor_layout = QVBoxLayout(sensor_group)
        
        # Table
        self.sensor_table = QTableWidget(0, 5)
        self.sensor_table.setHorizontalHeaderLabels([
            "Name", "Register", "Data Type", "Scale", ""
        ])
        self.sensor_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.sensor_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.sensor_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.sensor_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.sensor_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        self.sensor_table.setColumnWidth(4, 60)
        self.sensor_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.sensor_table.setAlternatingRowColors(True)
        sensor_layout.addWidget(self.sensor_table)
        
        # Add Sensor Button
        btn_row = QHBoxLayout()
        btn_add = QPushButton("+ Add Sensor")
        btn_add.clicked.connect(self._add_sensor_row)
        btn_row.addWidget(btn_add)
        btn_row.addStretch()
        sensor_layout.addLayout(btn_row)
        
        layout.addWidget(sensor_group, 1)
        
        # Add default sensor
        self._add_sensor_row()
        
        # === Buttons ===
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _refresh_com_ports(self):
        """Refresh available COM ports."""
        self.com_port_combo.clear()
        ports = list_available_ports()
        if ports:
            for port_name, description in ports:
                display = f"{port_name} - {description}" if description else port_name
                self.com_port_combo.addItem(display, port_name)
        else:
            self.com_port_combo.addItem("No ports found", "")
    
    def _add_sensor_row(self):
        """Add a new sensor row to the table."""
        row = self.sensor_table.rowCount()
        self.sensor_table.insertRow(row)
        
        # Name
        name_item = QTableWidgetItem(f"Sensor_{row+1}")
        self.sensor_table.setItem(row, 0, name_item)
        
        # Register Address
        reg_spin = QSpinBox()
        reg_spin.setRange(0, 65535)
        reg_spin.setValue(row * 2)  # Default: 0, 2, 4...
        self.sensor_table.setCellWidget(row, 1, reg_spin)
        
        # Data Type
        type_combo = QComboBox()
        type_combo.addItems(self.DATA_TYPES)
        type_combo.setCurrentText("FLOAT32_BE")
        self.sensor_table.setCellWidget(row, 2, type_combo)
        
        # Scale Factor
        scale_spin = QDoubleSpinBox()
        scale_spin.setRange(0.0001, 10000)
        scale_spin.setValue(1.0)
        scale_spin.setDecimals(4)
        self.sensor_table.setCellWidget(row, 3, scale_spin)
        
        # Remove Button
        btn_remove = QPushButton("✖")
        btn_remove.setFixedWidth(40)
        btn_remove.clicked.connect(lambda: self._remove_sensor_row(row))
        self.sensor_table.setCellWidget(row, 4, btn_remove)
    
    def _remove_sensor_row(self, row: int):
        """Remove sensor row."""
        if self.sensor_table.rowCount() <= 1:
            QMessageBox.warning(self, "Warning", "At least one sensor is required.")
            return
        self.sensor_table.removeRow(row)
        # Update remove button connections
        for r in range(self.sensor_table.rowCount()):
            btn = self.sensor_table.cellWidget(r, 4)
            if btn:
                btn.clicked.disconnect()
                btn.clicked.connect(lambda checked, row=r: self._remove_sensor_row(row))
    
    def _validate_and_accept(self):
        """Validate inputs and accept dialog."""
        # Check for valid sensors
        if self.sensor_table.rowCount() == 0:
            QMessageBox.warning(self, "Validation Error", "Add at least one sensor.")
            return
        
        # Check for duplicate names
        names = set()
        for row in range(self.sensor_table.rowCount()):
            name_item = self.sensor_table.item(row, 0)
            name = name_item.text().strip() if name_item else ""
            if not name:
                QMessageBox.warning(self, "Validation Error", f"Sensor at row {row+1} has no name.")
                return
            if name in names:
                QMessageBox.warning(self, "Validation Error", f"Duplicate sensor name: {name}")
                return
            names.add(name)
        
        self.accept()
    
    def get_connection_type(self) -> str:
        """Return 'TCP' or 'RTU'."""
        return "TCP" if self.radio_tcp.isChecked() else "RTU"
    
    def get_connection_params(self) -> Dict[str, Any]:
        """Return connection parameters."""
        if self.radio_tcp.isChecked():
            return {
                "ip_address": self.ip_input.text(),
                "tcp_port": self.tcp_port_input.value()
            }
        else:
            parity_map = {"None (N)": "N", "Even (E)": "E", "Odd (O)": "O"}
            return {
                "serial_port": self.com_port_combo.currentData() or self.com_port_combo.currentText().split(" - ")[0],
                "baudrate": int(self.baud_combo.currentText()),
                "parity": parity_map.get(self.parity_combo.currentText(), "N"),
                "stopbits": int(self.stopbits_combo.currentText()),
                "bytesize": 8
            }
    
    def get_sensors(self) -> List[Dict[str, Any]]:
        """
        Return list of sensor configurations.
        
        Returns:
            List of dicts with keys: name, register_address, data_type, scale_factor
        """
        sensors = []
        for row in range(self.sensor_table.rowCount()):
            name_item = self.sensor_table.item(row, 0)
            reg_widget = self.sensor_table.cellWidget(row, 1)
            type_widget = self.sensor_table.cellWidget(row, 2)
            scale_widget = self.sensor_table.cellWidget(row, 3)
            
            sensors.append({
                "name": name_item.text().strip() if name_item else f"Sensor_{row+1}",
                "register_address": reg_widget.value() if reg_widget else 0,
                "data_type": type_widget.currentText() if type_widget else "FLOAT32_BE",
                "scale_factor": scale_widget.value() if scale_widget else 1.0,
                "slave_id": 1  # Default slave ID
            })
        return sensors
