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

    def __init__(self, parent=None):
        super().__init__("Field Explorer", parent)
        self.setAllowedAreas(Qt.DockWidgetArea.LeftDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Sensors / Assets")
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemClicked.connect(self.on_item_clicked)

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
        # Only emit for leaf nodes (sensors)
        if item.childCount() == 0:
            path = self.get_item_path(item)
            self.sensor_selected.emit(path)

    def show_context_menu(self, position):
        item = self.tree.itemAt(position)
        menu = QMenu()

        # Actions
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

            if level == 0: # Factory level
                 menu.addAction(add_line_action)
            elif level == 1: # Line level (can hold sensors)
                 menu.addAction(add_sensor_action)
            elif level == 2: # Sensor level (leaf node)
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
