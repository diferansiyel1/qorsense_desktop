#!/usr/bin/env python3
"""
QorSense Desktop Application Entry Point

Usage:
    python run_desktop.py
"""

import os
import sys

# Ensure project root is in path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Import and run the desktop application
from desktop_app.main import main

if __name__ == "__main__":
    main()
