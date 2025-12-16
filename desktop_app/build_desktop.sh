#!/bin/bash
set -e

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Building QorSense Desktop App...${NC}"

# Ensure we are in the project root
cd "$(dirname "$0")/.."

# Check if venv is active or available
if [ -z "$VIRTUAL_ENV" ]; then
    if [ -d "venv" ]; then
        source venv/bin/activate
    else
        echo "Warning: No virtual environment found. Builds might fail if dependencies are missing."
    fi
fi

# Install PyInstaller if missing
if ! command -v pyinstaller &> /dev/null; then
    pip install pyinstaller
fi

# Clean previous builds
rm -rf build dist

echo -e "${GREEN}Starting PyInstaller...${NC}"

# Build command
# --name: Executable name
# --windowed: No console window (GUI mode)
# --onedir: Folder output (easier for debugging assets than onefile)
# --paths: Add root to path so 'backend' and 'desktop_app' can be found
# --hidden-import: Explicitly add backend modules if analysis has dynamic imports (though usually auto-detected)
pyinstaller desktop_app/main.py \
    --name qorsense_monitor \
    --windowed \
    --onedir \
    --paths . \
    --add-data "desktop_app/assets:assets" \
    --clean \
    --noconfirm

echo -e "${BLUE}Build Complete!${NC}"
echo -e "${GREEN}Executable is located in: dist/qorsense_monitor/qorsense_monitor${NC}"
