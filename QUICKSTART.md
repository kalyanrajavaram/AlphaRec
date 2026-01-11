# Quick Start Guide

Get your AI Activity Recommender up and running in 10 minutes!

## 1. Run Setup (2 minutes)

```bash
cd /Users/kalyanrajavaram/Downloads/Projects/AIRecommender
chmod +x scripts/setup.sh
./scripts/setup.sh
```

Follow the prompts. The script will handle most of the setup automatically.

## 2. Create Icons (2 minutes)

**Easiest Method**: Use an online tool

1. Go to https://favicon.io/favicon-generator/
2. Type "A" and choose colors
3. Click "Generate" and download
4. Extract the zip file
5. Copy icons to the extension:
   ```bash
   cp ~/Downloads/favicon_io/android-chrome-512x512.png chrome-extension/icons/icon128.png
   cp ~/Downloads/favicon_io/favicon-32x32.png chrome-extension/icons/icon48.png
   cp ~/Downloads/favicon_io/favicon-16x16.png chrome-extension/icons/icon16.png
   ```

   Note: Scale the 512x512 to 128x128 if needed using Preview or online tools.

## 3. Load Extension (2 minutes)

1. Open Chrome → `chrome://extensions/`
2. Enable "Developer mode" (top-right toggle)
3. Click "Load unpacked"
4. Select: `/Users/kalyanrajavaram/Downloads/Projects/AIRecommender/chrome-extension`
5. **Copy the Extension ID** (long string of letters under the extension name)

## 4. Install Native Host (2 minutes)

```bash
cd native-host
./install.sh
```

When prompted, paste your Extension ID from step 3.

## 5. Grant Permissions (2 minutes)

1. Open System Preferences
2. Security & Privacy → Privacy → Accessibility
3. Click 🔒 and unlock with your password
4. Click "+" and add **Terminal**
5. Check the box next to Terminal

## 6. Restart Chrome

Quit Chrome completely (Cmd+Q) and reopen it.

## 7. Test It!

1. Click the extension icon
2. Should show "Active" status
3. Browse some websites for 1-2 minutes
4. Click extension icon again - you should see statistics!

## Using the Analytics Tools

View your browsing data:

```bash
source venv/bin/activate
python3 analytics/query-tools.py --all
```

Export your data:

```bash
python3 analytics/export.py --format csv --output ./exports
```

## Troubleshooting

**Extension shows "Error"?**
- Restart Chrome completely
- Check that Extension ID matches in both places

**No stats appearing?**
- Wait 30-60 seconds for data to batch
- Check: `sqlite3 database/activity.db "SELECT COUNT(*) FROM browsing_history;"`

**App tracking not working?**
- Verify Accessibility permissions are granted
- Terminal (or Python) must be in the allowed list

## What Gets Tracked?

- ✅ Websites you visit (URL + title)
- ✅ Time spent on each site
- ✅ Google searches and clicked results
- ✅ Applications you use (with Accessibility permission)
- ✅ Window titles
- ❌ Incognito/private browsing (NOT tracked)
- ❌ Chrome internal pages (NOT tracked)

## Daily Usage

The system works automatically in the background. Just use Chrome normally!

To view your data:
- Click the extension icon for quick stats
- Run analytics tools for detailed reports
- Export data anytime for backup

## Next Steps

- Read [README.md](README.md) for full documentation
- Read [INSTALLATION.md](INSTALLATION.md) for detailed setup
- Customize tracking settings in the extension popup
- Set up regular data exports for backup

---

**Privacy Note**: All data stays on your computer. Nothing is sent to external servers.
