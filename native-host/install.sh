#!/bin/bash
# Installation script for Native Messaging Host

set -e

echo "======================================"
echo "AI Activity Recommender - Native Host Installation"
echo "======================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# Native host configuration
HOST_NAME="com.airecommender.host"
NATIVE_HOST_DIR="$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts"
MANIFEST_PATH="$NATIVE_HOST_DIR/$HOST_NAME.json"

echo "Project root: $PROJECT_ROOT"
echo "Native host directory: $NATIVE_HOST_DIR"
echo ""

# Step 1: Make Python scripts executable
echo "Making Python scripts executable..."
chmod +x "$SCRIPT_DIR/native-host-server.py"
chmod +x "$SCRIPT_DIR/app-tracker.py"
echo -e "${GREEN}✓${NC} Python scripts are now executable"
echo ""

# Step 2: Get Chrome extension ID
echo "To complete the installation, you need to provide your Chrome extension ID."
echo ""
echo -e "${YELLOW}How to find your extension ID:${NC}"
echo "1. Open Chrome and go to: chrome://extensions/"
echo "2. Enable 'Developer mode' (toggle in top-right corner)"
echo "3. Load the extension from: $PROJECT_ROOT/chrome-extension"
echo "4. Copy the extension ID (it looks like: abcdefghijklmnopqrstuvwxyz123456)"
echo ""

read -p "Enter your Chrome extension ID: " EXTENSION_ID

if [ -z "$EXTENSION_ID" ]; then
    echo -e "${RED}✗${NC} Extension ID cannot be empty"
    exit 1
fi

echo -e "${GREEN}✓${NC} Extension ID: $EXTENSION_ID"
echo ""

# Step 3: Create native messaging host manifest
echo "Creating native messaging host manifest..."

# Create directory if it doesn't exist
mkdir -p "$NATIVE_HOST_DIR"

# Get absolute path to native-host-server.py
PYTHON_SCRIPT="$SCRIPT_DIR/native-host-server.py"

# Create manifest JSON
cat > "$MANIFEST_PATH" << EOF
{
  "name": "$HOST_NAME",
  "description": "AI Activity Recommender Native Host",
  "path": "$PYTHON_SCRIPT",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://$EXTENSION_ID/"
  ]
}
EOF

echo -e "${GREEN}✓${NC} Manifest created at: $MANIFEST_PATH"
echo ""

# Step 4: Check Python environment
echo "Checking Python environment..."

if [ ! -d "$PROJECT_ROOT/venv" ]; then
    echo -e "${YELLOW}!${NC} Virtual environment not found"
    echo "Please run the setup script first: ./scripts/setup.sh"
    exit 1
fi

echo -e "${GREEN}✓${NC} Virtual environment found"
echo ""

# Step 5: Create logs directory
echo "Creating logs directory..."
mkdir -p "$PROJECT_ROOT/logs"
echo -e "${GREEN}✓${NC} Logs directory created"
echo ""

# Step 6: Test database connection
echo "Testing database setup..."

DB_PATH="$PROJECT_ROOT/database/activity.db"
SCHEMA_PATH="$PROJECT_ROOT/database/schema.sql"

if [ ! -f "$DB_PATH" ]; then
    echo "Initializing database..."
    if [ -f "$SCHEMA_PATH" ]; then
        sqlite3 "$DB_PATH" < "$SCHEMA_PATH"
        echo -e "${GREEN}✓${NC} Database initialized"
    else
        echo -e "${RED}✗${NC} Schema file not found: $SCHEMA_PATH"
        exit 1
    fi
else
    echo -e "${GREEN}✓${NC} Database already exists"
fi

# Set database permissions
chmod 600 "$DB_PATH"
echo -e "${GREEN}✓${NC} Database permissions set (owner read/write only)"
echo ""

# Step 7: macOS Accessibility Permissions
echo "======================================"
echo -e "${YELLOW}IMPORTANT: macOS Permissions Required${NC}"
echo "======================================"
echo ""
echo "For application tracking to work, you must grant Accessibility permissions."
echo ""
echo -e "${YELLOW}Steps to grant permissions:${NC}"
echo "1. Open System Preferences"
echo "2. Go to: Security & Privacy → Privacy → Accessibility"
echo "3. Click the lock icon and enter your password"
echo "4. Click '+' and add one of the following:"
echo "   - Terminal (if running from Terminal)"
echo "   - Python (if running Python directly)"
echo "   - Chrome (to allow Chrome to communicate with the native host)"
echo ""
echo "Without these permissions, application tracking will not work."
echo ""

read -p "Press Enter to continue once you've granted permissions..."

# Step 8: Installation complete
echo ""
echo "======================================"
echo -e "${GREEN}Installation Complete!${NC}"
echo "======================================"
echo ""
echo "Next steps:"
echo "1. Restart Chrome to ensure it recognizes the native host"
echo "2. Open the extension and verify it's tracking activity"
echo "3. Check logs at: $PROJECT_ROOT/logs/native-host.log"
echo ""
echo "Testing the connection:"
echo "  - Click the extension icon in Chrome"
echo "  - You should see activity statistics"
echo ""
echo "Troubleshooting:"
echo "  - If connection fails, check the logs"
echo "  - Ensure Python virtual environment is activated"
echo "  - Verify Accessibility permissions are granted"
echo ""
echo "Manifest location: $MANIFEST_PATH"
echo "Database location: $DB_PATH"
echo ""
