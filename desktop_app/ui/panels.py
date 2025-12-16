from PyQt6.QtWidgets import (QDockWidget, QTreeWidget, QTreeWidgetItem, 
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

import json
import os
from PyQt6.QtWidgets import (QDockWidget, QTreeWidget, QTreeWidgetItem, 
                             QMenu, QInputDialog, QMessageBox)
from PyQt6.QtGui import QIcon, QAction

class FieldExplorerPanel(QDockWidget):
    # Signal emitted when a sensor is selected (path as string)
    sensor_selected = pyqtSignal(str)
    
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
        
        # Logic for menu items based on selection
        if item is None:
            menu.addAction(add_factory_action)
        else:
            # Simple hierarchy logic: Factory -> Line -> Sensor
            # Determine hierarchy level
            # Level 0 = Factory/Root -> Can add Line
            # Level 1 = Line -> Can add Sensor
            # Level 2 = Sensor -> Leaf (can't add children)
            
            level = 0
            curr = item
            while curr.parent():
                curr = curr.parent()
                level += 1
            
            if level == 0: # Factory level
                 menu.addAction(add_line_action)
            elif level == 1: # Line level (can hold sensors)
                 menu.addAction(add_sensor_action)
            
            menu.addSeparator()
            menu.addAction(remove_action)
            
        menu.exec(self.tree.viewport().mapToGlobal(position))

    def add_factory(self):
        name, ok = QInputDialog.getText(self, "Add Factory", "Factory Name:")
        if ok and name:
            QTreeWidgetItem(self.tree, [name])
            self.save_assets()

    def add_child_item(self, parent_item, type_name):
        if parent_item is None: return
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
                    line["children"].append({"name": sensor_item.text(0)})
                    
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
            with open(self.assets_file, 'r') as f:
                data = json.load(f)
                
            self.tree.clear()
            for factory in data:
                f_item = QTreeWidgetItem(self.tree, [factory["name"]])
                f_item.setExpanded(True)
                for line in factory.get("children", []):
                    l_item = QTreeWidgetItem(f_item, [line["name"]])
                    l_item.setExpanded(True)
                    for sensor in line.get("children", []):
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
