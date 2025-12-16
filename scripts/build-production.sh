#!/bin/bash
# ============================================================================
# QorSense Desktop - Production Build Script
# ============================================================================
# Bu script, uygulamayı kurulabilir bir pakete dönüştürür.
# 
# Kullanım:
#   ./build-production.sh          # Mevcut platform için build
#   ./build-production.sh --mac    # macOS için build
#   ./build-production.sh --win    # Windows için build (cross-compile)
#   ./build-production.sh --all    # Tüm platformlar için build
# ============================================================================

set -e  # Hata olursa dur

# Renk kodları
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Proje root dizini
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_DIR="$PROJECT_ROOT/backend"
FRONTEND_DIR="$PROJECT_ROOT/frontend-next"
RESOURCES_DIR="$PROJECT_ROOT/resources/backend-binaries"

echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           QorSense Desktop - Production Build                ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Platform belirleme
BUILD_TARGET="${1:-current}"
case "$BUILD_TARGET" in
    --mac)
        PLATFORM="mac"
        ;;
    --win)
        PLATFORM="win"
        ;;
    --all)
        PLATFORM="all"
        ;;
    *)
        if [[ "$OSTYPE" == "darwin"* ]]; then
            PLATFORM="mac"
        elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
            PLATFORM="win"
        else
            PLATFORM="linux"
        fi
        ;;
esac

echo -e "${YELLOW}Build Target: $PLATFORM${NC}"
echo ""

# ============================================================================
# STEP 1: Python Backend Build (PyInstaller)
# ============================================================================
echo -e "${GREEN}[1/4] Building Python Backend with PyInstaller...${NC}"

cd "$BACKEND_DIR"

# venv aktif et
if [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
else
    echo -e "${RED}Error: venv not found. Run 'python3 -m venv venv && pip install -r requirements.txt' first.${NC}"
    exit 1
fi

# PyInstaller yüklü mü kontrol et
if ! command -v pyinstaller &> /dev/null; then
    echo -e "${YELLOW}Installing PyInstaller...${NC}"
    pip install pyinstaller
fi

# PyInstaller build
echo -e "${YELLOW}Running PyInstaller...${NC}"
pyinstaller build_backend.spec --noconfirm

# Binary'yi resources klasörüne kopyala
if [[ "$PLATFORM" == "mac" ]] || [[ "$PLATFORM" == "all" ]]; then
    mkdir -p "$RESOURCES_DIR/mac"
    cp "$BACKEND_DIR/dist/qorsense-backend" "$RESOURCES_DIR/mac/" 2>/dev/null || true
    echo -e "${GREEN}✓ macOS backend binary copied${NC}"
fi

if [[ "$PLATFORM" == "win" ]] || [[ "$PLATFORM" == "all" ]]; then
    mkdir -p "$RESOURCES_DIR/win"
    cp "$BACKEND_DIR/dist/qorsense-backend.exe" "$RESOURCES_DIR/win/" 2>/dev/null || true
    echo -e "${GREEN}✓ Windows backend binary copied${NC}"
fi

echo ""

# ============================================================================
# STEP 2: Next.js Static Build
# ============================================================================
echo -e "${GREEN}[2/4] Building Next.js Static Export...${NC}"

cd "$FRONTEND_DIR"

# npm bağımlılıkları kontrol et
if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}Installing npm dependencies...${NC}"
    npm install
fi

# Build
echo -e "${YELLOW}Running Next.js build...${NC}"
npm run build

echo -e "${GREEN}✓ Static export complete (out/ folder)${NC}"
echo ""

# ============================================================================
# STEP 3: Electron Build
# ============================================================================
echo -e "${GREEN}[3/4] Building Electron Application...${NC}"

cd "$FRONTEND_DIR"

if [[ "$PLATFORM" == "mac" ]]; then
    echo -e "${YELLOW}Building for macOS...${NC}"
    npm run electron:build:mac
elif [[ "$PLATFORM" == "win" ]]; then
    echo -e "${YELLOW}Building for Windows...${NC}"
    npm run electron:build:win
elif [[ "$PLATFORM" == "all" ]]; then
    echo -e "${YELLOW}Building for all platforms...${NC}"
    npm run electron:build:all
fi

echo ""

# ============================================================================
# STEP 4: Summary
# ============================================================================
echo -e "${GREEN}[4/4] Build Complete!${NC}"
echo ""
echo -e "${BLUE}╔══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                      Build Artifacts                         ║${NC}"
echo -e "${BLUE}╚══════════════════════════════════════════════════════════════╝${NC}"
echo ""

DIST_DIR="$PROJECT_ROOT/dist"

if [ -d "$DIST_DIR" ]; then
    echo -e "${GREEN}Output files in: $DIST_DIR${NC}"
    ls -la "$DIST_DIR" 2>/dev/null || true
else
    echo -e "${YELLOW}Check frontend-next/dist for output files${NC}"
fi

echo ""
echo -e "${GREEN}✅ Production build completed successfully!${NC}"
