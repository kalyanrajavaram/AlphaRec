#!/bin/bash
# Complete Setup Script for AI Activity Recommender

set -e

echo "======================================"
echo "AI Activity Recommender - Complete Setup"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "Project root: $PROJECT_ROOT"
echo ""

# Step 1: Check system requirements
echo -e "${BLUE}Step 1: Checking system requirements${NC}"
echo "--------------------------------------"

# Check macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo -e "${RED}✗${NC} This script is designed for macOS only"
    exit 1
fi
echo -e "${GREEN}✓${NC} Running on macOS"

# Check Python version
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓${NC} Python 3 found: $PYTHON_VERSION"
else
    echo -e "${RED}✗${NC} Python 3 not found. Please install Python 3.9 or higher"
    exit 1
fi

# Check if Chrome is installed
if [ -d "/Applications/Google Chrome.app" ]; then
    echo -e "${GREEN}✓${NC} Google Chrome found"
else
    echo -e "${YELLOW}!${NC} Google Chrome not found. Please install it to use the extension"
fi

echo ""

# Step 2: Create Python virtual environment
echo -e "${BLUE}Step 2: Creating Python virtual environment${NC}"
echo "--------------------------------------"

cd "$PROJECT_ROOT"

if [ -d "venv" ]; then
    echo -e "${YELLOW}!${NC} Virtual environment already exists"
    read -p "Remove and recreate? (y/n): " RECREATE
    if [ "$RECREATE" = "y" ]; then
        rm -rf venv
        python3 -m venv venv
        echo -e "${GREEN}✓${NC} Virtual environment recreated"
    fi
else
    python3 -m venv venv
    echo -e "${GREEN}✓${NC} Virtual environment created"
fi

echo ""

# Step 3: Install Python dependencies
echo -e "${BLUE}Step 3: Installing Python dependencies${NC}"
echo "--------------------------------------"

source venv/bin/activate

pip install --upgrade pip > /dev/null 2>&1
pip install -r native-host/requirements.txt

echo -e "${GREEN}✓${NC} Python dependencies installed"
echo ""

# Step 4: Initialize database
echo -e "${BLUE}Step 4: Initializing database${NC}"
echo "--------------------------------------"

DB_PATH="$PROJECT_ROOT/database/activity.db"
SCHEMA_PATH="$PROJECT_ROOT/database/schema.sql"

if [ -f "$DB_PATH" ]; then
    echo -e "${YELLOW}!${NC} Database already exists"
    read -p "Keep existing database? (y/n): " KEEP_DB
    if [ "$KEEP_DB" != "y" ]; then
        rm "$DB_PATH"
        sqlite3 "$DB_PATH" < "$SCHEMA_PATH"
        echo -e "${GREEN}✓${NC} Database recreated"
    else
        echo -e "${GREEN}✓${NC} Keeping existing database"
    fi
else
    sqlite3 "$DB_PATH" < "$SCHEMA_PATH"
    echo -e "${GREEN}✓${NC} Database initialized"
fi

# Set secure permissions
chmod 600 "$DB_PATH"
echo -e "${GREEN}✓${NC} Database permissions set"
echo ""

# Step 5: Create necessary directories
echo -e "${BLUE}Step 5: Creating necessary directories${NC}"
echo "--------------------------------------"

mkdir -p "$PROJECT_ROOT/logs"
mkdir -p "$PROJECT_ROOT/exports"

echo -e "${GREEN}✓${NC} Directories created"
echo ""

# Step 6: Make scripts executable
echo -e "${BLUE}Step 6: Making scripts executable${NC}"
echo "--------------------------------------"

chmod +x "$PROJECT_ROOT/native-host/native-host-server.py"
chmod +x "$PROJECT_ROOT/native-host/app-tracker.py"
chmod +x "$PROJECT_ROOT/native-host/install.sh"
chmod +x "$PROJECT_ROOT/analytics/query-tools.py"
chmod +x "$PROJECT_ROOT/analytics/export.py"

echo -e "${GREEN}✓${NC} Scripts are now executable"
echo ""

# Step 7: Chrome Extension Setup Instructions
echo -e "${BLUE}Step 7: Chrome Extension Setup${NC}"
echo "--------------------------------------"
echo ""
echo -e "${YELLOW}To install the Chrome extension:${NC}"
echo ""
echo "1. Open Google Chrome"
echo "2. Go to: chrome://extensions/"
echo "3. Enable 'Developer mode' (toggle in top-right)"
echo "4. Click 'Load unpacked'"
echo "5. Select folder: $PROJECT_ROOT/chrome-extension"
echo ""
echo -e "${YELLOW}NOTE:${NC} You'll need placeholder icons for the extension."
echo "The extension will still work without icons, but Chrome may show warnings."
echo ""

# Create placeholder icons
echo "Creating placeholder icon..."
# This creates a simple 128x128 PNG (base64 encoded 1x1 transparent pixel, scaled)
# For production, you should create proper icons
mkdir -p "$PROJECT_ROOT/chrome-extension/icons"

# Create a simple text file as placeholder
cat > "$PROJECT_ROOT/chrome-extension/icons/README.txt" << EOF
Place your extension icons here:
- icon16.png (16x16 pixels)
- icon48.png (48x48 pixels)
- icon128.png (128x128 pixels)

You can create simple icons or download from icon generators online.
EOF

echo -e "${GREEN}✓${NC} Icon directory created (add your icon files)"
echo ""

read -p "Press Enter once you've loaded the extension in Chrome..."
echo ""

# Step 8: Native Host Installation
echo -e "${BLUE}Step 8: Installing Native Messaging Host${NC}"
echo "--------------------------------------"
echo ""

cd "$PROJECT_ROOT/native-host"
bash install.sh

echo ""

# Step 9: Final instructions
echo ""
echo "======================================"
echo -e "${GREEN}Setup Complete!${NC}"
echo "======================================"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo ""
echo "1. Grant macOS Accessibility permissions:"
echo "   System Preferences → Security & Privacy → Privacy → Accessibility"
echo "   Add Terminal and/or Python to the list"
echo ""
echo "2. Restart Chrome to ensure native host connection"
echo ""
echo "3. Click the extension icon to verify it's working"
echo ""
echo -e "${YELLOW}Testing the system:${NC}"
echo ""
echo "   # View statistics"
echo "   python3 analytics/query-tools.py --all"
echo ""
echo "   # Export data"
echo "   python3 analytics/export.py --format csv --output ./exports"
echo ""
echo -e "${YELLOW}Files locations:${NC}"
echo "   Database: $DB_PATH"
echo "   Logs: $PROJECT_ROOT/logs/"
echo "   Extension: $PROJECT_ROOT/chrome-extension/"
echo ""
echo -e "${YELLOW}Troubleshooting:${NC}"
echo "   - Check logs in: $PROJECT_ROOT/logs/native-host.log"
echo "   - Verify extension ID matches in native host manifest"
echo "   - Ensure Accessibility permissions are granted"
echo ""

deactivate
