# Testing Checklist

Use this checklist to verify that your AI Activity Recommender is working correctly.

## Pre-Installation Tests

- [ ] macOS version 10.14 or later
- [ ] Python 3.9+ installed (`python3 --version`)
- [ ] Google Chrome installed
- [ ] Terminal has permission to run scripts

## Installation Tests

### Setup Script
- [ ] `./scripts/setup.sh` runs without errors
- [ ] Virtual environment created (`venv/` directory exists)
- [ ] Python dependencies installed (check `pip list`)
- [ ] Database created (`database/activity.db` exists)
- [ ] Database has correct schema (6 tables created)
- [ ] Logs directory created (`logs/` exists)

```bash
# Verify database schema
sqlite3 database/activity.db ".tables"
# Should show: application_usage browsing_history search_queries ...
```

### Extension Installation
- [ ] Icons created (`icon16.png`, `icon48.png`, `icon128.png`)
- [ ] Extension loaded in Chrome without errors
- [ ] Extension ID copied
- [ ] Extension appears in Chrome toolbar

### Native Host Installation
- [ ] `./native-host/install.sh` completed successfully
- [ ] Extension ID entered correctly
- [ ] Manifest file created at:
  `~/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.airecommender.host.json`
- [ ] Manifest contains correct extension ID
- [ ] Manifest path points to correct Python script

```bash
# Verify manifest
cat ~/Library/Application\ Support/Google/Chrome/NativeMessagingHosts/com.airecommender.host.json
```

### macOS Permissions
- [ ] Accessibility permissions granted
- [ ] Terminal (or Python) added to allowed applications
- [ ] Checkbox next to Terminal is checked

## Functional Tests

### Extension Connection
- [ ] Chrome completely restarted
- [ ] Extension icon clickable
- [ ] Popup opens when clicked
- [ ] Status shows "Active" (green)
- [ ] No connection errors in popup

```bash
# Check logs for connection
tail -f logs/native-host.log
# Should show "Native messaging host started" and "Connected to native host"
```

### Browser Tracking
- [ ] Visit 3-5 different websites
- [ ] Stay on each for at least 30 seconds
- [ ] Switch between tabs
- [ ] Wait 1 minute for data to batch

```bash
# Verify data was saved
sqlite3 database/activity.db "SELECT COUNT(*) FROM browsing_history;"
# Should return > 0
```

- [ ] Check extension popup - statistics updated
- [ ] "Sites Visited" shows correct count
- [ ] "Time Tracked" shows non-zero value

### Detailed Browser Tracking Tests
- [ ] Visit a new website
- [ ] Page title captured correctly
- [ ] URL captured correctly
- [ ] Leave the page and duration is calculated
- [ ] Switch to another tab - previous tab duration saved
- [ ] Go idle for 2 minutes - tracking pauses
- [ ] Return active - tracking resumes

```bash
# View recent browsing history
sqlite3 database/activity.db "SELECT url, title, duration_seconds FROM browsing_history ORDER BY visit_time DESC LIMIT 5;"
```

### Google Search Tracking
- [ ] Perform a Google search (e.g., "python tutorials")
- [ ] Search query appears in database
- [ ] Click on 2-3 search results
- [ ] Clicked results recorded with positions
- [ ] Wait 30 seconds for batching

```bash
# Verify search queries
sqlite3 database/activity.db "SELECT query, search_time FROM search_queries ORDER BY search_time DESC LIMIT 3;"

# Verify search clicks
sqlite3 database/activity.db "SELECT result_url, result_title FROM search_result_clicks ORDER BY click_time DESC LIMIT 3;"
```

### Application Tracking
- [ ] Switch to a non-browser application (e.g., VS Code)
- [ ] Stay in the app for at least 1 minute
- [ ] Switch to another app (e.g., Terminal)
- [ ] Wait 10 seconds

```bash
# Verify application tracking
sqlite3 database/activity.db "SELECT app_name, window_title, duration_seconds FROM application_usage ORDER BY start_time DESC LIMIT 5;"
```

- [ ] Application names appear correctly
- [ ] Window titles captured (if permissions allow)
- [ ] Durations calculated
- [ ] Browser detected correctly (is_browser = 1 for Chrome)

### Time Tracking Accuracy
- [ ] Open a specific website
- [ ] Note the time
- [ ] Stay on the page for exactly 2 minutes (120 seconds)
- [ ] Switch to another tab
- [ ] Check the database

```bash
sqlite3 database/activity.db "SELECT url, duration_seconds FROM browsing_history ORDER BY visit_time DESC LIMIT 1;"
# Duration should be close to 120 seconds (±5 seconds acceptable)
```

### Idle Detection
- [ ] Open a website
- [ ] Leave computer idle for 2+ minutes
- [ ] Return and check

```bash
# Last entry should show duration stopped during idle period
sqlite3 database/activity.db "SELECT url, duration_seconds, is_active FROM browsing_history ORDER BY visit_time DESC LIMIT 1;"
```

### Extension Popup UI
- [ ] Click extension icon
- [ ] "Today's Activity" section displays
- [ ] Statistics show real numbers
- [ ] Top sites list populated
- [ ] Tracking toggle works (ON/OFF)
- [ ] UI updates when toggling

### Analytics Tools
- [ ] Activate virtual environment
- [ ] Run query tools

```bash
source venv/bin/activate

# Test all reports
python3 analytics/query-tools.py --all

# Specific tests
python3 analytics/query-tools.py --top-sites --days 1
python3 analytics/query-tools.py --search-queries --days 1
python3 analytics/query-tools.py --app-usage --days 1
python3 analytics/query-tools.py --daily-summary
```

- [ ] All reports run without errors
- [ ] Data appears correctly formatted
- [ ] Numbers match database queries

### Data Export
- [ ] Export to CSV

```bash
python3 analytics/export.py --format csv --output ./test-export --days 1
ls test-export/
```

- [ ] `browsing_history.csv` created
- [ ] `search_queries.csv` created
- [ ] `application_usage.csv` created
- [ ] CSV files contain valid data
- [ ] Can open in Excel/Numbers

- [ ] Export to JSON

```bash
python3 analytics/export.py --format json --output ./test-data.json --days 1
cat test-data.json | head -20
```

- [ ] JSON file created
- [ ] Valid JSON structure
- [ ] Contains all data types

### Extension Controls
- [ ] Export button works (check popup)
- [ ] Clear data button shows confirmation
- [ ] Clear data actually removes records

```bash
# Before clearing
sqlite3 database/activity.db "SELECT COUNT(*) FROM browsing_history;"

# Click "Clear Data" in popup and confirm

# After clearing
sqlite3 database/activity.db "SELECT COUNT(*) FROM browsing_history;"
# Should be 0 or significantly reduced
```

### Settings Persistence
- [ ] Toggle tracking OFF
- [ ] Close popup
- [ ] Open popup again
- [ ] Tracking still OFF
- [ ] Restart Chrome
- [ ] Open popup
- [ ] Setting persisted

## Stress Tests

### Rapid Tab Switching
- [ ] Open 10+ tabs
- [ ] Rapidly switch between them
- [ ] Wait 1 minute
- [ ] Check database - all visits recorded
- [ ] No duplicate entries
- [ ] Durations reasonable

### Multiple Searches
- [ ] Perform 5 searches in rapid succession
- [ ] Click results from each
- [ ] Wait for batching
- [ ] All queries recorded
- [ ] All clicks associated correctly

### Long Session
- [ ] Keep browser open for 1+ hour
- [ ] Browse normally
- [ ] Check logs for errors
- [ ] Database size reasonable
- [ ] No memory leaks in extension

### Service Worker Restart
- [ ] Browse for a while
- [ ] Open Chrome task manager (Shift+Esc)
- [ ] Find extension service worker
- [ ] End the process
- [ ] Continue browsing
- [ ] Service worker restarts automatically
- [ ] Tracking continues without data loss

## Error Handling Tests

### Native Host Disconnection
- [ ] Kill the native host process manually
- [ ] Extension shows error state
- [ ] Reconnection attempted
- [ ] Logs show reconnection attempts

### Database Locked
- [ ] Open database in SQLite browser
- [ ] Keep it locked
- [ ] Try to save data
- [ ] Error handled gracefully
- [ ] No crashes

### Permission Revoked
- [ ] Revoke Accessibility permissions
- [ ] Application tracking stops
- [ ] Browser tracking continues
- [ ] Appropriate error logged

## Performance Tests

### Database Size
- [ ] Use for 1 week normally
- [ ] Check database size

```bash
ls -lh database/activity.db
# Should be < 10 MB for normal usage
```

### Query Performance
- [ ] Add 1000+ records
- [ ] Run analytics queries
- [ ] Responses < 1 second
- [ ] Export completes in reasonable time

### Extension Performance
- [ ] Open Chrome task manager
- [ ] Check extension CPU/memory usage
- [ ] Should be minimal when idle
- [ ] Reasonable during active tracking

## Privacy & Security Tests

### Incognito Mode
- [ ] Open incognito window
- [ ] Browse websites
- [ ] Check database
- [ ] No incognito data recorded

### Local Storage Only
- [ ] Monitor network traffic (using DevTools)
- [ ] Browse and track for 10 minutes
- [ ] No external network requests from extension
- [ ] All data stays local

### File Permissions
```bash
ls -l database/activity.db
# Should show: -rw------- (600 permissions, owner only)
```

## Documentation Tests

- [ ] README.md clear and complete
- [ ] INSTALLATION.md steps work
- [ ] QUICKSTART.md accurate timing
- [ ] All file paths in docs are correct
- [ ] Code examples run successfully

## Final Verification

- [ ] All core features working
- [ ] No errors in logs
- [ ] Extension stable over multiple sessions
- [ ] Data accurate and complete
- [ ] Export/import functional
- [ ] Documentation complete

## Test Results Summary

**Date Tested**: _________________

**Tester**: _________________

**Overall Status**: ☐ Pass  ☐ Fail  ☐ Partial

**Issues Found**:

_____________________________

_____________________________

_____________________________

**Notes**:

_____________________________

_____________________________

_____________________________
