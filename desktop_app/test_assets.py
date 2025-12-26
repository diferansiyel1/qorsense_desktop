
import json
import os
import sys

# Setup Paths
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from desktop_app.ui.panels import FieldExplorerPanel
from PyQt6.QtWidgets import QApplication


def test_asset_persistence():
    print("Testing Asset Persistence...")
    app = QApplication(sys.argv)

    # 1. Init Panel
    panel = FieldExplorerPanel()

    # 2. Verify Demo Data Created (since no assets.json initially)
    # We expect "Factory Main (Demo)"
    root = panel.tree.topLevelItem(0)
    if not root:
        print("FAIL: No root item found.")
        return False

    print(f"Root: {root.text(0)}")

    # 3. Simulate Adding a Factory
    from PyQt6.QtWidgets import QTreeWidgetItem
    new_factory = QTreeWidgetItem(panel.tree, ["Test Factory"])
    panel.save_assets()

    # 4. Check if assets.json exists
    assets_path = panel.assets_file
    if not os.path.exists(assets_path):
        print("FAIL: assets.json not created.")
        return False

    # 5. Load JSON and verify "Test Factory" is there
    with open(assets_path) as f:
        data = json.load(f)

    found = any(f["name"] == "Test Factory" for f in data)
    if found:
        print("PASS: Asset persisted to JSON.")
    else:
        print("FAIL: Test Factory not found in JSON.")
        return False

    # Cleanup
    if os.path.exists(assets_path):
        os.remove(assets_path)

    return True

if __name__ == "__main__":
    try:
        if test_asset_persistence():
            print("ALL TRIALS PASSED")
        else:
            print("TRIALS FAILED")
            sys.exit(1)
    except Exception as e:
        print(f"CRASH: {e}")
        sys.exit(1)
