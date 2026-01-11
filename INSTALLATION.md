# Installation Guide - AI Activity Recommender

Complete step-by-step installation instructions for macOS.

## Prerequisites

Before you begin, ensure you have:

- macOS 10.14 or later
- Python 3.9 or higher installed
- Google Chrome browser
- Administrative access to grant Accessibility permissions

## Installation Steps

### Step 1: Prepare the Project

1. Navigate to the project directory:
   ```bash
   cd /Users/kalyanrajavaram/Downloads/Projects/AIRecommender
   ```

2. Verify all files are present:
   ```bash
   ls -la
   ```

   You should see:
   - `chrome-extension/`
   - `native-host/`
   - `database/`
   - `analytics/`
   - `scripts/`
   - `README.md`

### Step 2: Run the Setup Script

The setup script automates most of the installation process:

```bash
chmod +x scripts/setup.sh
./scripts/setup.sh
```

This script will:
1. Check system requirements (macOS, Python, Chrome)
2. Create a Python virtual environment
3. Install Python dependencies (pyobjc, pandas)
4. Initialize the SQLite database
5. Create necessary directories (logs, exports)
6. Make all scripts executable
7. Guide you through extension installation

**Important**: Follow the prompts carefully and don't skip any steps.

### Step 3: Create Extension Icons (Required)

Chrome extensions require icons. You have two options:

#### Option A: Use Online Icon Generator (Recommended)
1. Go to https://favicon.io/favicon-generator/
2. Create a simple icon (e.g., letter "A" with gradient background)
3. Download the generated icons
4. Rename and copy:
   - `favicon-16x16.png` → `chrome-extension/icons/icon16.png`
   - `favicon-32x32.png` (scale to 48x48) → `chrome-extension/icons/icon48.png`
   - `android-chrome-192x192.png` (scale to 128x128) → `chrome-extension/icons/icon128.png`

#### Option B: Create Simple Colored Squares
Using any image editor (Preview, GIMP, etc.):
1. Create a 128x128 pixel image with a solid color (e.g., purple #667eea)
2. Save as `icon128.png`
3. Scale down to create `icon48.png` (48x48) and `icon16.png` (16x16)
4. Place all three in `chrome-extension/icons/`

### Step 4: Load Chrome Extension

1. Open Google Chrome
2. Navigate to: `chrome://extensions/`
3. Enable "Developer mode" using the toggle in the top-right corner
4. Click "Load unpacked" button
5. Browse to and select: `/Users/kalyanrajavaram/Downloads/Projects/AIRecommender/chrome-extension`
6. The extension should now appear in your extensions list

7. **Important**: Copy the Extension ID
   - It looks like: `abcdefghijklmnopqrstuvwxyz123456`
   - You'll need this for the next step

### Step 5: Install Native Messaging Host

The native messaging host allows the Chrome extension to communicate with the Python backend.

```bash
cd native-host
./install.sh
```

When prompted:
1. Paste the Extension ID you copied from Chrome
2. Press Enter to continue

The script will:
- Create the native host manifest file
- Copy it to Chrome's native messaging hosts directory
- Initialize the database
- Display permission instructions

### Step 6: Grant macOS Accessibility Permissions

**This step is critical for application tracking to work.**

1. Open System Preferences
2. Go to: Security & Privacy → Privacy → Accessibility
3. Click the lock icon (🔒) in the bottom-left and enter your password
4. Click the "+" button
5. Add one or both of:
   - **Terminal** (if you run Python from Terminal)
   - **Python** (located at `/Users/kalyanrajavaram/Downloads/Projects/AIRecommender/venv/bin/python3`)

6. Ensure the checkbox next to the added application is checked
7. Close System Preferences

### Step 7: Restart Chrome

For the native messaging host to connect properly:

1. Completely quit Chrome (Cmd+Q)
2. Relaunch Chrome
3. The extension should now be able to communicate with the native host

### Step 8: Verify Installation

1. Click the extension icon in Chrome's toolbar
2. You should see:
   - Status: "Active" (green badge)
   - Today's Activity section
   - Statistics should show "0" initially

3. Browse a few websites and wait 30-60 seconds
4. Click the extension icon again
5. Statistics should now show your activity

### Step 9: Test the System

#### Test Browser Tracking
```bash
# Activate virtual environment
source venv/bin/activate

# Check browsing history
sqlite3 database/activity.db "SELECT COUNT(*) FROM browsing_history;"
```

Should return a number > 0 if you've browsed websites.

#### Test Application Tracking
```bash
# View application usage
python3 analytics/query-tools.py --app-usage --days 1
```

Should show applications you've used.

#### Test Data Export
```bash
# Export all data
python3 analytics/export.py --format csv --output ./test-export
ls test-export/
```

Should create CSV files with your data.

## Verification Checklist

- [ ] Python virtual environment created
- [ ] Python dependencies installed
- [ ] Database initialized
- [ ] Extension icons created
- [ ] Chrome extension loaded
- [ ] Extension ID copied
- [ ] Native host manifest installed
- [ ] Accessibility permissions granted
- [ ] Chrome restarted
- [ ] Extension shows "Active" status
- [ ] Statistics appear after browsing
- [ ] Application tracking working
- [ ] Data export successful

## Troubleshooting

### Extension shows "Error" status

**Cause**: Native host not connected.

**Solution**:
1. Check that the extension ID in the native host manifest matches your extension
   ```bash
   cat ~/Library/Application\ Support/Google/Chrome/NativeMessagingHosts/com.airecommender.host.json
   ```
2. Verify the path in the manifest points to your native-host-server.py
3. Restart Chrome completely

### No application tracking data

**Cause**: Accessibility permissions not granted.

**Solution**:
1. Re-check System Preferences → Security & Privacy → Privacy → Accessibility
2. Ensure Terminal or Python is in the list and checked
3. Try removing and re-adding the application
4. Restart the native host

### "Permission denied" errors

**Cause**: Scripts not executable or file permissions incorrect.

**Solution**:
```bash
chmod +x scripts/*.sh
chmod +x native-host/*.py
chmod +x analytics/*.py
chmod 600 database/activity.db
```

### Extension not appearing in Chrome

**Cause**: Icons missing or manifest errors.

**Solution**:
1. Create the required icon files (see Step 3)
2. Check Chrome's extension page for error messages
3. Reload the extension

### Database errors

**Cause**: Database not initialized or corrupted.

**Solution**:
```bash
# Backup existing database (if it has data you want to keep)
cp database/activity.db database/activity.db.backup

# Recreate database
rm database/activity.db
sqlite3 database/activity.db < database/schema.sql
```

## Next Steps

Once installation is complete:

1. **Use the Extension**: Browse normally and your activity will be tracked
2. **Review Analytics**: Use the query tools to analyze your data
3. **Export Data**: Regularly export your data for backup
4. **Customize Settings**: Adjust data retention and other preferences in the popup

## Uninstallation

To completely remove the system:

1. Remove Chrome extension:
   - Go to `chrome://extensions/`
   - Click "Remove" on the AI Activity Recommender extension

2. Remove native host:
   ```bash
   rm ~/Library/Application\ Support/Google/Chrome/NativeMessagingHosts/com.airecommender.host.json
   ```

3. Remove project directory:
   ```bash
   rm -rf /Users/kalyanrajavaram/Downloads/Projects/AIRecommender
   ```

4. Revoke Accessibility permissions:
   - System Preferences → Security & Privacy → Privacy → Accessibility
   - Remove Terminal/Python from the list

## Getting Help

If you encounter issues:

1. Check the logs:
   ```bash
   tail -f logs/native-host.log
   ```

2. Review this installation guide carefully
3. Verify each step in the checklist above
4. Check the main README.md for additional troubleshooting tips
