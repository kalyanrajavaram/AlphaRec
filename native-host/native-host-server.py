#!/Users/kalyanrajavaram/Downloads/Projects/AIRecommender/venv/bin/python3
"""
Native Messaging Host Server for AI Activity Recommender
Handles communication between Chrome extension and local database
"""

import sys
import json
import struct
import sqlite3
import os
import threading
import logging
from datetime import datetime, timedelta
from pathlib import Path

# Add native-host directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

# Setup logging (to file since stdout is used for messaging)
log_file = Path(__file__).parent.parent / 'logs' / 'native-host.log'
log_file.parent.mkdir(exist_ok=True)

logging.basicConfig(
    filename=str(log_file),
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Database path
DB_PATH = Path(__file__).parent.parent / 'database' / 'activity.db'

# Global app tracker thread
app_tracker_thread = None
app_tracker_stop_event = threading.Event()


class NativeMessagingHost:
    """Native messaging host for Chrome extension communication"""

    def __init__(self):
        self.db_connection = None
        self.init_database()

    def init_database(self):
        """Initialize database connection and ensure schema exists"""
        try:
            # Create database directory if it doesn't exist
            DB_PATH.parent.mkdir(parents=True, exist_ok=True)

            # Connect to database
            self.db_connection = sqlite3.connect(str(DB_PATH), check_same_thread=False)
            self.db_connection.execute('PRAGMA journal_mode=WAL')  # Enable WAL mode

            # Load schema if tables don't exist
            schema_path = DB_PATH.parent / 'schema.sql'
            if schema_path.exists():
                with open(schema_path, 'r') as f:
                    schema_sql = f.read()
                    self.db_connection.executescript(schema_sql)
                    self.db_connection.commit()

            logging.info('Database initialized successfully')

        except Exception as e:
            logging.error(f'Error initializing database: {e}')
            raise

    def read_message(self):
        """Read a message from Chrome extension via stdin"""
        try:
            # Read message length (4 bytes)
            raw_length = sys.stdin.buffer.read(4)
            if not raw_length:
                return None

            message_length = struct.unpack('=I', raw_length)[0]

            # Read message
            message_json = sys.stdin.buffer.read(message_length).decode('utf-8')
            message = json.loads(message_json)

            logging.info(f'Received message: {message.get("command", "unknown")}')
            return message

        except Exception as e:
            logging.error(f'Error reading message: {e}')
            return None

    def send_message(self, message):
        """Send a message to Chrome extension via stdout"""
        try:
            message_json = json.dumps(message)
            message_bytes = message_json.encode('utf-8')

            # Write message length (4 bytes)
            sys.stdout.buffer.write(struct.pack('=I', len(message_bytes)))

            # Write message
            sys.stdout.buffer.write(message_bytes)
            sys.stdout.buffer.flush()

            logging.info(f'Sent message: {message.get("status", "unknown")}')

        except Exception as e:
            logging.error(f'Error sending message: {e}')

    def handle_save_browser_data(self, data):
        """Save browsing data to database"""
        try:
            cursor = self.db_connection.cursor()
            saved_count = 0

            for item in data:
                item_type = item.get('type')
                item_data = item.get('data')

                if item_type == 'browsing_history':
                    cursor.execute('''
                        INSERT INTO browsing_history
                        (url, title, visit_time, leave_time, duration_seconds, tab_id, is_active, active_duration_seconds)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item_data.get('url'),
                        item_data.get('title'),
                        item_data.get('visit_time'),
                        item_data.get('leave_time'),
                        item_data.get('duration_seconds'),
                        item_data.get('tab_id'),
                        item_data.get('is_active', 1),
                        item_data.get('active_duration_seconds', 0)
                    ))
                    saved_count += 1

                elif item_type == 'search_query':
                    cursor.execute('''
                        INSERT INTO search_queries
                        (query, search_engine, search_time)
                        VALUES (?, ?, ?)
                    ''', (
                        item_data.get('query'),
                        item_data.get('search_engine', 'google'),
                        item_data.get('search_time')
                    ))
                    saved_count += 1

                elif item_type == 'search_click':
                    # Get the most recent search query to link to
                    cursor.execute('''
                        SELECT id FROM search_queries
                        ORDER BY search_time DESC
                        LIMIT 1
                    ''')
                    result = cursor.fetchone()
                    search_query_id = result[0] if result else None

                    if search_query_id:
                        cursor.execute('''
                            INSERT INTO search_result_clicks
                            (search_query_id, result_url, result_title, result_position, click_time)
                            VALUES (?, ?, ?, ?, ?)
                        ''', (
                            search_query_id,
                            item_data.get('result_url'),
                            item_data.get('result_title'),
                            item_data.get('result_position'),
                            item_data.get('click_time')
                        ))
                        saved_count += 1

                elif item_type == 'navigation_event':
                    cursor.execute('''
                        INSERT INTO navigation_events
                        (url, tab_id, opener_tab_id, transition_type, transition_qualifiers, is_spa_navigation, event_time)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        item_data.get('url'),
                        item_data.get('tab_id'),
                        item_data.get('opener_tab_id'),
                        item_data.get('transition_type'),
                        item_data.get('transition_qualifiers'),
                        item_data.get('is_spa_navigation', False),
                        item_data.get('event_time')
                    ))
                    saved_count += 1

                elif item_type == 'download':
                    cursor.execute('''
                        INSERT INTO downloads
                        (filename, url, mime_type, file_size, download_time)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        item_data.get('filename'),
                        item_data.get('url'),
                        item_data.get('mime_type'),
                        item_data.get('file_size'),
                        item_data.get('download_time')
                    ))
                    saved_count += 1

                elif item_type == 'bookmark':
                    cursor.execute('''
                        INSERT INTO bookmarks
                        (url, title, bookmark_time)
                        VALUES (?, ?, ?)
                    ''', (
                        item_data.get('url'),
                        item_data.get('title'),
                        item_data.get('bookmark_time')
                    ))
                    saved_count += 1

                elif item_type == 'user_interaction':
                    cursor.execute('''
                        INSERT INTO user_interactions
                        (url, tab_id, interaction_type, interaction_data, event_time)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        item_data.get('url'),
                        item_data.get('tab_id'),
                        item_data.get('interaction_type'),
                        item_data.get('interaction_data'),
                        item_data.get('event_time')
                    ))
                    saved_count += 1

            self.db_connection.commit()
            logging.info(f'Saved {saved_count} items to database')

            return {'status': 'success', 'saved': saved_count}

        except Exception as e:
            logging.error(f'Error saving browser data: {e}')
            return {'status': 'error', 'message': str(e)}

    def handle_get_stats(self):
        """Get statistics from database"""
        try:
            cursor = self.db_connection.cursor()
            today = datetime.now().date()

            # Get today's browsing stats
            cursor.execute('''
                SELECT COUNT(*), SUM(duration_seconds)
                FROM browsing_history
                WHERE DATE(visit_time) = ?
            ''', (today,))
            sites_count, total_seconds = cursor.fetchone()
            total_seconds = total_seconds or 0

            # Get top sites today
            cursor.execute('''
                SELECT url, title, SUM(duration_seconds) as total_time
                FROM browsing_history
                WHERE DATE(visit_time) = ?
                GROUP BY url
                ORDER BY total_time DESC
                LIMIT 5
            ''', (today,))
            top_sites = [
                {'url': row[0], 'title': row[1], 'time': row[2]}
                for row in cursor.fetchall()
            ]

            # Get search queries count today
            cursor.execute('''
                SELECT COUNT(*)
                FROM search_queries
                WHERE DATE(search_time) = ?
            ''', (today,))
            search_count = cursor.fetchone()[0]

            # Get application usage count today
            cursor.execute('''
                SELECT COUNT(DISTINCT app_name)
                FROM application_usage
                WHERE DATE(start_time) = ?
            ''', (today,))
            app_count = cursor.fetchone()[0]

            stats = {
                'status': 'success',
                'sites_visited': sites_count or 0,
                'total_time_seconds': total_seconds,
                'top_sites': top_sites,
                'search_queries': search_count,
                'applications_used': app_count
            }

            logging.info('Retrieved statistics')
            return stats

        except Exception as e:
            logging.error(f'Error getting stats: {e}')
            return {'status': 'error', 'message': str(e)}

    def handle_update_settings(self, settings):
        """Update tracking settings"""
        try:
            cursor = self.db_connection.cursor()

            if 'tracking_enabled' in settings:
                cursor.execute('''
                    UPDATE tracking_settings
                    SET tracking_enabled = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                ''', (settings['tracking_enabled'],))

            if 'data_retention_days' in settings:
                cursor.execute('''
                    UPDATE tracking_settings
                    SET data_retention_days = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = 1
                ''', (settings['data_retention_days'],))

            self.db_connection.commit()
            logging.info('Updated settings')

            return {'status': 'success'}

        except Exception as e:
            logging.error(f'Error updating settings: {e}')
            return {'status': 'error', 'message': str(e)}

    def handle_start_app_tracking(self):
        """Start application tracking thread"""
        global app_tracker_thread, app_tracker_stop_event

        try:
            if app_tracker_thread and app_tracker_thread.is_alive():
                logging.info('App tracker already running')
                return {'status': 'success', 'message': 'Already running'}

            # Import and start app tracker
            from app_tracker import start_tracking

            app_tracker_stop_event.clear()
            app_tracker_thread = threading.Thread(
                target=start_tracking,
                args=(str(DB_PATH), app_tracker_stop_event)
            )
            app_tracker_thread.daemon = True
            app_tracker_thread.start()

            logging.info('Started app tracking thread')
            return {'status': 'success', 'message': 'Started'}

        except Exception as e:
            logging.error(f'Error starting app tracking: {e}')
            return {'status': 'error', 'message': str(e)}

    def handle_stop_app_tracking(self):
        """Stop application tracking thread"""
        global app_tracker_stop_event

        try:
            app_tracker_stop_event.set()
            logging.info('Stopped app tracking')
            return {'status': 'success'}

        except Exception as e:
            logging.error(f'Error stopping app tracking: {e}')
            return {'status': 'error', 'message': str(e)}

    def handle_message(self, message):
        """Handle incoming message from Chrome extension"""
        command = message.get('command')

        if command == 'save_browser_data':
            response = self.handle_save_browser_data(message.get('data', []))

        elif command == 'get_stats':
            response = self.handle_get_stats()

        elif command == 'update_settings':
            response = self.handle_update_settings(message.get('settings', {}))

        elif command == 'start_app_tracking':
            response = self.handle_start_app_tracking()

        elif command == 'stop_app_tracking':
            response = self.handle_stop_app_tracking()

        else:
            response = {'status': 'error', 'message': f'Unknown command: {command}'}

        return response

    def run(self):
        """Main loop to handle messages"""
        logging.info('Native messaging host started')

        try:
            while True:
                message = self.read_message()
                if message is None:
                    break

                response = self.handle_message(message)
                self.send_message(response)

        except KeyboardInterrupt:
            logging.info('Received interrupt signal')

        finally:
            # Cleanup
            if self.db_connection:
                self.db_connection.close()
            app_tracker_stop_event.set()
            logging.info('Native messaging host stopped')


if __name__ == '__main__':
    host = NativeMessagingHost()
    host.run()
