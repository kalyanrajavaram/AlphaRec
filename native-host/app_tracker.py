#!/Users/kalyanrajavaram/Downloads/Projects/AIRecommender/venv/bin/python3
"""
macOS Application Tracker using Quartz framework
Tracks active window and application usage
"""

import time
import sqlite3
import logging
from datetime import datetime
from Quartz import (
    CGWindowListCopyWindowInfo,
    kCGWindowListOptionOnScreenOnly,
    kCGNullWindowID
)
from AppKit import NSWorkspace


# Browser bundle identifiers
BROWSER_BUNDLE_IDS = {
    'com.google.Chrome',
    'com.google.Chrome.canary',
    'org.mozilla.firefox',
    'com.apple.Safari',
    'com.microsoft.edgemac',
    'com.brave.Browser',
    'com.operasoftware.Opera'
}


class AppTracker:
    """Track active macOS applications and windows"""

    def __init__(self, db_path):
        self.db_path = db_path
        self.db_connection = None
        self.current_app = None
        self.current_window_title = None
        self.start_time = None

        self.init_database()

    def init_database(self):
        """Initialize database connection"""
        try:
            self.db_connection = sqlite3.connect(self.db_path, check_same_thread=False)
            logging.info('App tracker connected to database')
        except Exception as e:
            logging.error(f'Error connecting to database: {e}')
            raise

    def get_active_window_info(self):
        """Get information about the currently active window using Quartz"""
        try:
            # Get list of all on-screen windows
            window_list = CGWindowListCopyWindowInfo(
                kCGWindowListOptionOnScreenOnly,
                kCGNullWindowID
            )

            # Find the frontmost window (layer 0 is frontmost)
            for window in window_list:
                # Check if window is on screen and has a layer
                layer = window.get('kCGWindowLayer', -1)

                # Layer 0 is the active window layer
                if layer == 0:
                    owner_name = window.get('kCGWindowOwnerName', '')
                    window_title = window.get('kCGWindowName', '')
                    owner_pid = window.get('kCGWindowOwnerPID', 0)

                    # Get bundle ID using NSWorkspace
                    bundle_id = self.get_bundle_id_for_pid(owner_pid)

                    return {
                        'app_name': owner_name,
                        'window_title': window_title,
                        'bundle_id': bundle_id,
                        'pid': owner_pid
                    }

            # Fallback: use NSWorkspace to get active application
            workspace = NSWorkspace.sharedWorkspace()
            active_app = workspace.activeApplication()

            if active_app:
                return {
                    'app_name': active_app.get('NSApplicationName', 'Unknown'),
                    'window_title': '',
                    'bundle_id': active_app.get('NSApplicationBundleIdentifier', ''),
                    'pid': active_app.get('NSApplicationProcessIdentifier', 0)
                }

            return None

        except Exception as e:
            logging.error(f'Error getting active window: {e}')
            return None

    def get_bundle_id_for_pid(self, pid):
        """Get bundle identifier for a process ID"""
        try:
            workspace = NSWorkspace.sharedWorkspace()
            running_apps = workspace.runningApplications()

            for app in running_apps:
                if app.processIdentifier() == pid:
                    return app.bundleIdentifier() or ''

            return ''

        except Exception as e:
            logging.error(f'Error getting bundle ID: {e}')
            return ''

    def is_browser(self, bundle_id):
        """Check if the application is a browser"""
        return bundle_id in BROWSER_BUNDLE_IDS

    def save_current_app_data(self):
        """Save current application usage data to database"""
        if not self.current_app or not self.start_time:
            return

        try:
            end_time = datetime.now()
            duration_seconds = int((end_time - self.start_time).total_seconds())

            # Only save if duration is at least 1 second
            if duration_seconds < 1:
                return

            cursor = self.db_connection.cursor()
            cursor.execute('''
                INSERT INTO application_usage
                (app_name, app_bundle_id, window_title, start_time, end_time, duration_seconds, is_browser)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                self.current_app,
                self.current_bundle_id,
                self.current_window_title,
                self.start_time.isoformat(),
                end_time.isoformat(),
                duration_seconds,
                self.is_browser(self.current_bundle_id)
            ))

            self.db_connection.commit()
            logging.info(f'Saved app usage: {self.current_app} ({duration_seconds}s)')

        except Exception as e:
            logging.error(f'Error saving app data: {e}')

    def track_loop(self, stop_event, poll_interval=1.0):
        """Main tracking loop"""
        logging.info('App tracking started')

        try:
            while not stop_event.is_set():
                # Get current active window
                window_info = self.get_active_window_info()

                if window_info:
                    app_name = window_info['app_name']
                    window_title = window_info['window_title']
                    bundle_id = window_info['bundle_id']

                    # Check if app or window changed
                    if (app_name != self.current_app or
                        window_title != self.current_window_title):

                        # Save previous app data
                        if self.current_app:
                            self.save_current_app_data()

                        # Update current app
                        self.current_app = app_name
                        self.current_window_title = window_title
                        self.current_bundle_id = bundle_id
                        self.start_time = datetime.now()

                        logging.info(f'Active app changed: {app_name} - {window_title}')

                # Sleep for poll interval
                time.sleep(poll_interval)

        except KeyboardInterrupt:
            logging.info('App tracking interrupted')

        finally:
            # Save final app data
            if self.current_app:
                self.save_current_app_data()

            if self.db_connection:
                self.db_connection.close()

            logging.info('App tracking stopped')


def start_tracking(db_path, stop_event):
    """Start application tracking (to be called from thread)"""
    tracker = AppTracker(db_path)
    tracker.track_loop(stop_event)


if __name__ == '__main__':
    # For standalone testing
    import sys
    import threading

    if len(sys.argv) > 1:
        db_path = sys.argv[1]
    else:
        db_path = '../database/activity.db'

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    stop_event = threading.Event()

    try:
        start_tracking(db_path, stop_event)
    except KeyboardInterrupt:
        stop_event.set()
        print('\nTracking stopped')
