# AI Activity Recommender

A comprehensive, privacy-first activity tracking system for macOS that monitors browsing behavior and application usage to provide intelligent insights and analytics. All data is stored locally - no cloud services or external data transmission.

## Overview

AI Activity Recommender helps you understand your digital habits through:
- Detailed browsing history and time tracking
- Google search query monitoring and result click analysis
- macOS application usage statistics
- Productivity scoring and daily summaries
- Data export for external analysis

## Features

### Browser Activity Tracking
- **URL & Page Tracking**: Captures full URLs, page titles, and tab information
- **Time Duration**: Measures total time and active time spent on each site
- **Tab Switching**: Detects tab activation and tracks context switches
- **Idle Detection**: 60-second idle threshold to distinguish active vs passive browsing
- **Incognito Protection**: Private browsing sessions are never tracked

### Google Search Tracking
- **Query Extraction**: Captures search queries from Google search URLs
- **Result Click Tracking**: Records which search results you click, including:
  - Result URL and title
  - Position in search results
  - Time spent on clicked page
- **Dynamic Content Handling**: Uses MutationObserver for dynamically loaded results

### Application Usage Monitoring
- **Active App Detection**: Uses macOS Quartz APIs to identify the current window
- **Window Title Capture**: Records window titles and application bundle identifiers
- **Browser Detection**: Distinguishes browser windows from other applications
- **Duration Calculation**: Tracks time spent in each application

### Analytics & Reporting
- **Top Sites Report**: Most visited domains by time spent
- **Search Query Analysis**: Aggregate search patterns
- **Application Usage Stats**: Time per application
- **Daily Summaries**: Day-by-day activity breakdown
- **Productivity Scoring**: Categorizes apps as productive/non-productive

### Privacy & Security
- **Local Storage Only**: No data transmitted to external servers
- **Secure Permissions**: Database file restricted to owner (chmod 600)
- **No Telemetry**: Extension doesn't track itself
- **Data Retention**: Configurable automatic cleanup (default 90 days)

## Architecture

```
+---------------------------------------------------+
|  CHROME BROWSER                                   |
|  +----------------+      +--------------------+   |
|  | Content Script |<---->| Background Worker  |   |
|  | - Searches     |      | - Tab tracking     |   |
|  | - Page metadata|      | - Time calculation |   |
|  +----------------+      | - Data batching    |   |
|                          +---------+----------+   |
+-------------------------------|-------------------+
                                | Native Messaging (JSON/stdio)
                                v
+---------------------------------------------------+
|  NATIVE HOST (Python)                             |
|  +----------------------+  +------------------+   |
|  | Native Host Server   |  | App Tracker      |   |
|  | - Message protocol   |  | - Quartz APIs    |   |
|  | - DB operations      |  | - Window detect  |   |
|  +----------+-----------+  +--------+---------+   |
+-------------|------------------------|------------+
              |                        |
              +------------+-----------+
                           v
+---------------------------------------------------+
|  SQLITE DATABASE (activity.db)                    |
|  - browsing_history     - search_queries          |
|  - search_result_clicks - application_usage       |
|  - user_sessions        - tracking_settings       |
+---------------------------------------------------+
              |
              v
+---------------------------------------------------+
|  ANALYTICS & EXPORT                               |
|  - query-tools.py (CLI analysis)                  |
|  - export.py (CSV/JSON export)                    |
+---------------------------------------------------+
```

## Technology Stack

| Component | Technology |
|-----------|------------|
| Browser Extension | Vanilla JavaScript, Chrome Extension APIs (Manifest V3) |
| Backend | Python 3.9+ with pyobjc-framework-Cocoa, pyobjc-framework-Quartz |
| Database | SQLite 3 with WAL mode |
| Data Analysis | pandas |
| Platform | macOS 10.14+ |
| Browser | Google Chrome |

## System Requirements

- macOS 10.14 (Mojave) or later
- Python 3.9 or higher
- Google Chrome browser
- macOS Accessibility permissions (for application tracking)

## Quick Start

### 1. Run Setup Script

```bash
cd AIRecommender
chmod +x scripts/setup.sh
./scripts/setup.sh
```

The setup script will:
- Create a Python virtual environment
- Install all dependencies
- Initialize the SQLite database
- Create necessary directories (logs, exports)
- Set secure database permissions

### 2. Create Extension Icons

Create PNG icons in `chrome-extension/icons/`:
- `icon16.png` (16x16 pixels)
- `icon48.png` (48x48 pixels)
- `icon128.png` (128x128 pixels)

You can use any icon generator or image editor.

### 3. Load Chrome Extension

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top-right)
3. Click **Load unpacked**
4. Select the `chrome-extension` folder
5. Note the **Extension ID** displayed on the card

### 4. Install Native Host

```bash
cd native-host
./install.sh
```

When prompted, enter the Extension ID from step 3.

### 5. Grant macOS Permissions

1. Open **System Preferences** > **Security & Privacy** > **Privacy** > **Accessibility**
2. Click the lock icon and authenticate
3. Add **Terminal** (or your Python installation) to the allowed list

### 6. Verify Installation

1. Click the extension icon in Chrome
2. You should see tracking status and statistics
3. Browse some websites and check that data appears

## Usage

### Extension Popup Controls

Click the extension icon to:
- View today's statistics
- Toggle tracking on/off
- Export data
- Clear all data (with confirmation)

### Command-Line Analytics

```bash
# Activate virtual environment
source venv/bin/activate

# View all statistics for the last 7 days
python3 analytics/query-tools.py --all

# View top visited sites
python3 analytics/query-tools.py --top-sites --days 30

# View search queries
python3 analytics/query-tools.py --search-queries --days 7

# View application usage
python3 analytics/query-tools.py --app-usage --days 7

# View daily summary for a specific date
python3 analytics/query-tools.py --daily-summary --date 2026-01-09
```

### Data Export

```bash
# Export all data to CSV files
python3 analytics/export.py --format csv --output ./exports

# Export last 30 days to JSON
python3 analytics/export.py --format json --days 30 --output ./my-data.json

# Export only browsing history
python3 analytics/export.py --type browsing --output ./exports
```

## Project Structure

```
AIRecommender/
├── README.md                     # This file
├── INSTALLATION.md               # Detailed setup guide
├── QUICKSTART.md                 # 10-minute quick start
├── PROJECT_SUMMARY.md            # Architecture overview
├── TESTING_CHECKLIST.md          # QA verification checklist
├── package.json                  # NPM project metadata
│
├── chrome-extension/             # Chrome Extension (Manifest V3)
│   ├── manifest.json             # Extension configuration
│   ├── background/
│   │   └── service-worker.js     # Background tracking logic
│   ├── content/
│   │   └── content-script.js     # Page interaction & search tracking
│   ├── popup/
│   │   ├── popup.html            # Extension popup UI
│   │   ├── popup.css             # Popup styling
│   │   └── popup.js              # Popup interactivity
│   └── icons/                    # Extension icons (user-provided)
│
├── native-host/                  # Python Backend
│   ├── native-host-server.py     # Native messaging protocol handler
│   ├── app-tracker.py            # macOS app tracker using Quartz
│   ├── install.sh                # Native host installation script
│   └── requirements.txt          # Python dependencies
│
├── database/
│   ├── schema.sql                # Complete database schema
│   └── activity.db               # SQLite database (created at runtime)
│
├── analytics/                    # Data Analysis Tools
│   ├── query-tools.py            # CLI for querying and analyzing data
│   └── export.py                 # Data export to CSV/JSON
│
├── scripts/
│   └── setup.sh                  # Complete setup automation
│
├── logs/                         # Runtime logs
│   └── native-host.log           # Native messaging logs
│
└── exports/                      # User data exports
```

## Database Schema

| Table | Description |
|-------|-------------|
| `browsing_history` | URLs visited, titles, timestamps, duration, active/passive flags |
| `search_queries` | Search query text, timestamp, search engine |
| `search_result_clicks` | Clicked results with URL, title, position, time on page |
| `application_usage` | App name, bundle ID, window title, duration, browser flag |
| `user_sessions` | Session start/end times, active/idle seconds |
| `tracking_settings` | Configuration: tracking enabled, retention days, version |

Additional tables for extended tracking:
- `navigation_events` - Transition types, SPA detection
- `downloads` - File download tracking
- `bookmarks` - Bookmark timestamps
- `user_interactions` - Privacy-preserving interaction data

## Troubleshooting

### Extension not connecting to native host

1. Verify native host installation:
   ```bash
   ls ~/Library/Application\ Support/Google/Chrome/NativeMessagingHosts/
   ```

2. Check that the extension ID matches in the native host manifest

3. Review logs:
   ```bash
   tail -f logs/native-host.log
   ```

4. Restart Chrome completely (quit and reopen)

### Application tracking not working

1. Ensure Accessibility permissions are granted in System Preferences

2. Verify Terminal/Python is in the allowed applications list

3. Test the app tracker standalone:
   ```bash
   source venv/bin/activate
   python3 native-host/app-tracker.py database/activity.db
   ```

### No statistics showing

1. Ensure tracking is enabled (check extension popup)

2. Browse some websites and wait 30 seconds for data batching

3. Verify database has data:
   ```bash
   sqlite3 database/activity.db "SELECT COUNT(*) FROM browsing_history;"
   ```

### Permission errors

1. Fix database permissions:
   ```bash
   chmod 600 database/activity.db
   ```

2. Make scripts executable:
   ```bash
   chmod +x native-host/*.py analytics/*.py scripts/*.sh
   ```

## Advanced Configuration

### Change Data Retention Period

Via SQL:
```sql
UPDATE tracking_settings SET data_retention_days = 180 WHERE id = 1;
```

### Exclude Specific Domains

Edit [chrome-extension/background/service-worker.js](chrome-extension/background/service-worker.js) to add domain exclusions in the URL filtering logic.

### Customize Productive Apps

Edit [analytics/query-tools.py](analytics/query-tools.py) in the `get_productivity_score()` function to define which applications are considered productive.

### Adjust Idle Threshold

Modify the idle detection threshold in [chrome-extension/background/service-worker.js](chrome-extension/background/service-worker.js) (default: 60 seconds).

### Change Data Batching Interval

The default batching interval is 30 seconds. Adjust in [chrome-extension/background/service-worker.js](chrome-extension/background/service-worker.js).

## Development

### Adding New Tracking Features

1. **Browser tracking**: Modify `background/service-worker.js`
2. **Page interaction**: Modify `content/content-script.js`
3. **Database tables**: Add to `database/schema.sql`
4. **Analytics**: Extend `analytics/query-tools.py`
5. **Export formats**: Extend `analytics/export.py`
6. **UI updates**: Modify files in `popup/`

### Chrome Extension APIs Used

- `chrome.tabs.*` - Tab management and tracking
- `chrome.webNavigation.*` - URL change detection
- `chrome.idle.*` - Idle state detection
- `chrome.storage.local` - Extension settings storage
- `chrome.runtime.*` - Native messaging and message passing

### Native Messaging Protocol

- **Transport**: stdin/stdout with JSON payloads
- **Framing**: 4-byte little-endian length prefix
- **Commands**: `save_browser_data`, `get_stats`, `export_data`, `clear_data`, `start_app_tracking`

## Known Limitations

- **Chrome only**: Firefox, Safari, and Edge are not supported
- **macOS only**: Application tracking uses macOS-specific Quartz APIs
- **Manual icon creation**: Extension icons must be provided by the user
- **Single profile**: Each Chrome profile requires separate setup
- **Accessibility required**: Full functionality requires macOS Accessibility permissions

## What's NOT Tracked

- Chrome internal pages (`chrome://`)
- Incognito/private browsing sessions
- HTTPS request bodies (only URLs)
- Password fields or sensitive form input
- The extension itself

## Security Considerations

- All data remains on your local machine
- No network requests are made by the tracking system
- Database is only readable by the file owner
- No third-party services or APIs are used
- Consider encrypting your database for additional security

---

**Important**: This system tracks extensive personal data. Ensure your data is secure and backed up appropriately. Use responsibly.
