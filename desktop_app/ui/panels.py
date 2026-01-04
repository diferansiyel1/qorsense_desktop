import json
import os

from backend.models import SENSOR_CATALOG
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QAction, QColor
from PyQt6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDockWidget,
    QFormLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
)


class AddSensorDialog(QDialog):
    """
    Dialog for adding a new sensor with cascading ComboBoxes:
    Category -> Sensor Type -> Unit
    Also supports custom (user-defined) sensor types and units.
    """

    CUSTOM_CATEGORY = "Custom"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add New Sensor")
        self.setMinimumWidth(400)

        layout = QVBoxLayout(self)

        # Form layout for inputs
        form_layout = QFormLayout()

        # Sensor Name
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter sensor name...")
        form_layout.addRow("Sensor Name:", self.name_input)

        # Category ComboBox (with Custom option)
        self.category_combo = QComboBox()
        categories = list(SENSOR_CATALOG.keys()) + [self.CUSTOM_CATEGORY]
        self.category_combo.addItems(categories)
        self.category_combo.currentTextChanged.connect(self._on_category_changed)
        form_layout.addRow("Category:", self.category_combo)

        # Sensor Type ComboBox (editable for custom)
        self.type_combo = QComboBox()
        self.type_combo.setEditable(False)  # Will be enabled for custom
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form_layout.addRow("Sensor Type:", self.type_combo)

        # Unit ComboBox (editable for custom)
        self.unit_combo = QComboBox()
        self.unit_combo.setEditable(False)  # Will be enabled for custom
        form_layout.addRow("Unit:", self.unit_combo)

        layout.addLayout(form_layout)

        # Info label for custom mode
        self.custom_hint = QLabel("💡 In custom mode, sensor type and unit can be freely entered.")
        self.custom_hint.setStyleSheet("color: #888; font-style: italic;")
        self.custom_hint.setVisible(False)
        layout.addWidget(self.custom_hint)

        # Dialog buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._validate_and_accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

        # Initialize cascading dropdowns
        self._on_category_changed(self.category_combo.currentText())

    def _on_category_changed(self, category: str):
        """Update sensor type options based on selected category"""
        self.type_combo.clear()
        self.unit_combo.clear()

        if category == self.CUSTOM_CATEGORY:
            # Enable free-text entry for custom sensors
            self.type_combo.setEditable(True)
            self.unit_combo.setEditable(True)
            self.type_combo.setPlaceholderText("Enter sensor type...")
            self.unit_combo.setPlaceholderText("Enter unit...")
            self.custom_hint.setVisible(True)
        else:
            # Use predefined catalog
            self.type_combo.setEditable(False)
            self.unit_combo.setEditable(False)
            self.custom_hint.setVisible(False)
            if category in SENSOR_CATALOG:
                sensor_types = list(SENSOR_CATALOG[category].keys())
                self.type_combo.addItems(sensor_types)

    def _on_type_changed(self, sensor_type: str):
        """Update unit options based on selected sensor type"""
        category = self.category_combo.currentText()

        # Don't clear unit combo if in custom mode and user is typing
        if category == self.CUSTOM_CATEGORY:
            return

        self.unit_combo.clear()
        if category in SENSOR_CATALOG and sensor_type in SENSOR_CATALOG[category]:
            units = SENSOR_CATALOG[category][sensor_type]
            self.unit_combo.addItems(units)

    def _validate_and_accept(self):
        """Validate inputs before accepting the dialog"""
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Warning", "Please enter sensor name.")
            self.name_input.setFocus()
            return

        sensor_type = self.type_combo.currentText().strip()
        if not sensor_type:
            QMessageBox.warning(self, "Warning", "Please enter/select sensor type.")
            self.type_combo.setFocus()
            return

        unit = self.unit_combo.currentText().strip()
        if not unit:
            QMessageBox.warning(self, "Warning", "Please enter/select unit.")
            self.unit_combo.setFocus()
            return

        self.accept()

    def get_sensor_data(self) -> dict:
        """Return the sensor data from the dialog inputs"""
        return {
            "name": self.name_input.text().strip(),
            "category": self.category_combo.currentText(),
            "sensor_type": self.type_combo.currentText().strip(),
            "unit": self.unit_combo.currentText().strip()
        }


class FieldExplorerPanel(QDockWidget):
    # Signal emitted when a sensor is selected (path as string)
    sensor_selected = pyqtSignal(str)
    # Signal emitted when CSV loading is requested for a sensor
    load_csv_requested = pyqtSignal(str)
    # Signal emitted when live sensor settings are requested
    live_sensor_settings_requested = pyqtSignal(str)  # sensor_id
    # Signal emitted when live sensor disconnect is requested
    live_sensor_disconnect_requested = pyqtSignal(str)  # sensor_id
    # Signal emitted when a live sensor is selected
    live_sensor_selected = pyqtSignal(str)  # sensor_id

    def __init__(self, parent=None):
        super().__init__("Field Explorer", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Sensors / Assets")
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemClicked.connect(self.on_item_clicked)

        # Live sensors tracking
        self.live_sensors_root = None  # Root item for live sensors section
        self.live_sensor_items = {}  # {sensor_id: QTreeWidgetItem}
        self.live_sensor_configs = {}  # {sensor_id: config_dict}

        # Load or Init
        self.assets_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets.json")
        self.load_assets()

        self.setWidget(self.tree)

    def get_item_path(self, item):
        """Get full path of item (Factory/Line/Sensor)"""
        path_parts = []
        while item:
            path_parts.insert(0, item.text(0))
            item = item.parent()
        return "/".join(path_parts)

    def on_item_clicked(self, item, column):
        """Handle item selection"""
        # Check if this is a live sensor
        sensor_id = item.data(0, Qt.ItemDataRole.UserRole + 1)  # Live sensor ID
        if sensor_id and sensor_id in self.live_sensor_items:
            self.live_sensor_selected.emit(sensor_id)
            return

        # Only emit for leaf nodes (sensors)
        if item.childCount() == 0:
            path = self.get_item_path(item)
            self.sensor_selected.emit(path)

    def show_context_menu(self, position):
        item = self.tree.itemAt(position)
        menu = QMenu()

        # Check if this is a live sensor item
        if item:
            sensor_id = item.data(0, Qt.ItemDataRole.UserRole + 1)  # Live sensor ID
            if sensor_id and sensor_id in self.live_sensor_items:
                # Live sensor context menu
                settings_action = QAction("⚙️ Connection Settings", self)
                settings_action.triggered.connect(lambda: self.live_sensor_settings_requested.emit(sensor_id))
                menu.addAction(settings_action)

                view_action = QAction("📊 View Data", self)
                view_action.triggered.connect(lambda: self.live_sensor_selected.emit(sensor_id))
                menu.addAction(view_action)

                menu.addSeparator()

                disconnect_action = QAction("🔌 Disconnect", self)
                disconnect_action.triggered.connect(lambda: self.live_sensor_disconnect_requested.emit(sensor_id))
                menu.addAction(disconnect_action)

                menu.exec(self.tree.viewport().mapToGlobal(position))
                return

            # Check if this is the live sensors root (prevent modification)
            if item == self.live_sensors_root:
                # No context menu for the live sensors root itself
                return

        # Actions for regular items
        add_factory_action = QAction("Add Factory", self)
        add_factory_action.triggered.connect(self.add_factory)

        add_line_action = QAction("Add Production Line", self)
        add_line_action.triggered.connect(lambda: self.add_child_item(item, "Line"))

        add_sensor_action = QAction("Add Sensor", self)
        add_sensor_action.triggered.connect(lambda: self.add_child_item(item, "Sensor"))

        remove_action = QAction("Remove Item", self)
        remove_action.triggered.connect(lambda: self.remove_item(item))

        # CSV Load action for sensors
        load_csv_action = QAction("📂 Load CSV Data", self)
        load_csv_action.triggered.connect(lambda: self._request_csv_load(item))

        # Logic for menu items based on selection
        if item is None:
            menu.addAction(add_factory_action)
        else:
            # Simple hierarchy logic: Factory -> Line -> Sensor
            # Determine hierarchy level
            # Level 0 = Factory/Root -> Can add Line
            # Level 1 = Line -> Can add Sensor
            # Level 2 = Sensor -> Leaf (can load CSV data)

            level = 0
            curr = item
            while curr.parent():
                curr = curr.parent()
                level += 1

            if level == 0:  # Factory level
                menu.addAction(add_line_action)
            elif level == 1:  # Line level (can hold sensors)
                menu.addAction(add_sensor_action)
            elif level == 2:  # Sensor level (leaf node)
                menu.addAction(load_csv_action)

            menu.addSeparator()
            menu.addAction(remove_action)

        menu.exec(self.tree.viewport().mapToGlobal(position))

    def _request_csv_load(self, item):
        """Emit signal to request CSV loading for the selected sensor"""
        if item:
            path = self.get_item_path(item)
            self.load_csv_requested.emit(path)

    def add_factory(self):
        name, ok = QInputDialog.getText(self, "Add Factory", "Factory Name:")
        if ok and name:
            QTreeWidgetItem(self.tree, [name])
            self.save_assets()

    def add_child_item(self, parent_item, type_name):
        if parent_item is None:
            return

        if type_name == "Sensor":
            # Use the new AddSensorDialog for sensors
            dialog = AddSensorDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                sensor_data = dialog.get_sensor_data()
                if sensor_data:
                    # Create display name with type and unit info
                    display_name = f"{sensor_data['name']} ({sensor_data['sensor_type']} - {sensor_data['unit']})"
                    item = QTreeWidgetItem(parent_item, [display_name])
                    # Store metadata in item data
                    item.setData(0, Qt.ItemDataRole.UserRole, sensor_data)
                    parent_item.setExpanded(True)
                    self.save_assets()
        else:
            # For other types (Line), use simple input dialog
            name, ok = QInputDialog.getText(self, f"Add {type_name}", f"{type_name} Name:")
            if ok and name:
                item = QTreeWidgetItem(parent_item, [name])
                parent_item.setExpanded(True)
                self.save_assets()

    def remove_item(self, item):
        if item is None: return
        confirm = QMessageBox.question(self, "Confirm Remove",
                                     f"Are you sure you want to remove '{item.text(0)}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if confirm == QMessageBox.StandardButton.Yes:
            parent = item.parent()
            if parent:
                parent.removeChild(item)
            else:
                index = self.tree.indexOfTopLevelItem(item)
                self.tree.takeTopLevelItem(index)
            self.save_assets()

    def save_assets(self):
        data = []
        root = self.tree.invisibleRootItem()
        for i in range(root.childCount()):
            factory_item = root.child(i)
            factory = {"name": factory_item.text(0), "children": []}

            for j in range(factory_item.childCount()):
                line_item = factory_item.child(j)
                line = {"name": line_item.text(0), "children": []}

                for k in range(line_item.childCount()):
                    sensor_item = line_item.child(k)
                    # Get sensor metadata if available
                    sensor_data = sensor_item.data(0, Qt.ItemDataRole.UserRole)
                    if sensor_data and isinstance(sensor_data, dict):
                        sensor_entry = {
                            "name": sensor_data.get("name", sensor_item.text(0)),
                            "sensor_type": sensor_data.get("sensor_type", ""),
                            "unit": sensor_data.get("unit", ""),
                            "category": sensor_data.get("category", "")
                        }
                    else:
                        # Legacy sensors without metadata
                        sensor_entry = {"name": sensor_item.text(0)}
                    line["children"].append(sensor_entry)

                factory["children"].append(line)

            data.append(factory)

        try:
            with open(self.assets_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to save assets: {e}")

    def load_assets(self):
        if not os.path.exists(self.assets_file):
            # Create default demo data
            self.create_demo_assets()
            return

        try:
            with open(self.assets_file) as f:
                data = json.load(f)

            self.tree.clear()
            for factory in data:
                f_item = QTreeWidgetItem(self.tree, [factory["name"]])
                f_item.setExpanded(True)
                for line in factory.get("children", []):
                    l_item = QTreeWidgetItem(f_item, [line["name"]])
                    l_item.setExpanded(True)
                    for sensor in line.get("children", []):
                        # Check for sensor metadata
                        if "sensor_type" in sensor and "unit" in sensor and sensor["sensor_type"]:
                            display_name = f"{sensor['name']} ({sensor['sensor_type']} - {sensor['unit']})"
                            sensor_item = QTreeWidgetItem(l_item, [display_name])
                            # Store metadata
                            sensor_item.setData(0, Qt.ItemDataRole.UserRole, {
                                "name": sensor["name"],
                                "sensor_type": sensor.get("sensor_type", ""),
                                "unit": sensor.get("unit", ""),
                                "category": sensor.get("category", "")
                            })
                        else:
                            # Legacy sensors without metadata
                            QTreeWidgetItem(l_item, [sensor["name"]])

        except Exception as e:
            print(f"Failed to load assets: {e}")
            self.create_demo_assets()

    def create_demo_assets(self):
        root = QTreeWidgetItem(self.tree, ["Factory Main (Demo)"])
        item1 = QTreeWidgetItem(root, ["Production Line A"])
        QTreeWidgetItem(item1, ["Sensor-vib-01"])
        QTreeWidgetItem(item1, ["Sensor-temp-01"])
        root.setExpanded(True)
        item1.setExpanded(True)

    # =========================================================================
    # LIVE SENSOR MANAGEMENT
    # =========================================================================

    def add_live_sensor(self, sensor_id: str, display_name: str = None, config: dict = None, status: str = "connecting"):
        """
        Add a live sensor to the tree under 'Live Sensors' root.

        Args:
            sensor_id: Unique sensor identifier
            display_name: Human-readable name (defaults to sensor_id)
            config: Connection configuration dict to store
            status: Initial status ('connecting', 'online', 'offline', 'error')
        """
        # Create live sensors root if it doesn't exist
        if self.live_sensors_root is None:
            self.live_sensors_root = QTreeWidgetItem(self.tree)
            self.live_sensors_root.setText(0, "🔴 Live Sensors")
            self.live_sensors_root.setForeground(0, QColor("#ff6600"))
            # Insert at top of tree
            self.tree.insertTopLevelItem(0, self.tree.takeTopLevelItem(
                self.tree.indexOfTopLevelItem(self.live_sensors_root)
            ))
            self.live_sensors_root.setExpanded(True)

        # Check if sensor already exists
        if sensor_id in self.live_sensor_items:
            return

        # Create sensor item
        name = display_name or sensor_id
        status_icon = self._get_status_icon(status)
        item = QTreeWidgetItem(self.live_sensors_root, [f"{status_icon} {name}"])

        # Store sensor_id in item data for identification
        item.setData(0, Qt.ItemDataRole.UserRole + 1, sensor_id)

        # Store config
        if config:
            self.live_sensor_configs[sensor_id] = config

        self.live_sensor_items[sensor_id] = item
        self.live_sensors_root.setExpanded(True)

    def remove_live_sensor(self, sensor_id: str):
        """Remove a single live sensor from the tree."""
        if sensor_id in self.live_sensor_items:
            item = self.live_sensor_items.pop(sensor_id)
            if self.live_sensors_root:
                self.live_sensors_root.removeChild(item)

            # Remove config
            self.live_sensor_configs.pop(sensor_id, None)

            # Hide root if no more live sensors
            if self.live_sensors_root and self.live_sensors_root.childCount() == 0:
                idx = self.tree.indexOfTopLevelItem(self.live_sensors_root)
                if idx >= 0:
                    self.tree.takeTopLevelItem(idx)
                self.live_sensors_root = None

    def clear_live_sensors(self):
        """Remove all live sensors from the tree."""
        for sensor_id in list(self.live_sensor_items.keys()):
            self.remove_live_sensor(sensor_id)

        self.live_sensor_items.clear()
        self.live_sensor_configs.clear()

        # Remove root
        if self.live_sensors_root:
            idx = self.tree.indexOfTopLevelItem(self.live_sensors_root)
            if idx >= 0:
                self.tree.takeTopLevelItem(idx)
            self.live_sensors_root = None

    def update_live_sensor_status(self, sensor_id: str, status: str):
        """
        Update the status indicator of a live sensor.

        Args:
            sensor_id: Sensor identifier
            status: 'online', 'offline', 'connecting', 'error', 'reconnecting'
        """
        if sensor_id not in self.live_sensor_items:
            return

        item = self.live_sensor_items[sensor_id]
        current_text = item.text(0)

        # Extract name (remove old status icon)
        name = current_text
        for icon in ["🟢", "🔴", "🟡", "⚠️", "🔄"]:
            if current_text.startswith(icon):
                name = current_text[len(icon):].strip()
                break

        status_icon = self._get_status_icon(status)
        item.setText(0, f"{status_icon} {name}")

        # Update color based on status
        color_map = {
            "online": QColor("#32c850"),
            "offline": QColor("#cc3333"),
            "connecting": QColor("#ff9500"),
            "reconnecting": QColor("#ff9500"),
            "error": QColor("#cc3333"),
        }
        item.setForeground(0, color_map.get(status, QColor("#ffffff")))

    def get_live_sensor_config(self, sensor_id: str) -> dict:
        """Get stored configuration for a live sensor."""
        return self.live_sensor_configs.get(sensor_id, {})

    def _get_status_icon(self, status: str) -> str:
        """Get status icon for display."""
        icons = {
            "online": "🟢",
            "offline": "🔴",
            "connecting": "🟡",
            "reconnecting": "🔄",
            "error": "⚠️",
        }
        return icons.get(status.lower(), "🟡")


class AlarmPanel(QDockWidget):

    def __init__(self, parent=None):
        super().__init__("Alarms & Events", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Severity", "Source", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setAlternatingRowColors(True)

        self.setWidget(self.table)

    def add_alarm(self, timestamp, severity, source, message):
        row = self.table.rowCount()
        self.table.insertRow(row)

        self.table.setItem(row, 0, QTableWidgetItem(timestamp))

        sev_item = QTableWidgetItem(severity)
        if severity == "CRITICAL":
            sev_item.setForeground(QColor(200, 50, 50))
        elif severity == "WARNING":
            sev_item.setForeground(QColor(255, 174, 0))
        elif severity == "INFO":
            sev_item.setForeground(QColor(50, 200, 80))

        self.table.setItem(row, 1, sev_item)
        self.table.setItem(row, 2, QTableWidgetItem(source))
        self.table.setItem(row, 3, QTableWidgetItem(message))
        self.table.scrollToBottom()
