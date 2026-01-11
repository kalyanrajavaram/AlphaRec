#!/usr/bin/env python3
"""
Raw Data CSV Exporter
Exports all raw tracking data to CSV files with complete field documentation
"""

import sqlite3
import csv
import argparse
from datetime import datetime, timedelta
from pathlib import Path


# Database path
DB_PATH = Path(__file__).parent.parent / 'database' / 'activity.db'

# Table definitions with field descriptions
TABLES = {
    'browsing_history': {
        'description': 'All visited web pages with timing data',
        'fields': [
            ('id', 'INTEGER', 'Unique record identifier'),
            ('url', 'TEXT', 'Full page URL'),
            ('title', 'TEXT', 'Page title'),
            ('visit_time', 'TIMESTAMP', 'When page was visited'),
            ('leave_time', 'TIMESTAMP', 'When user left the page'),
            ('duration_seconds', 'INTEGER', 'Total time on page in seconds'),
            ('tab_id', 'INTEGER', 'Browser tab identifier'),
            ('is_active', 'BOOLEAN', 'Whether tab was actively viewed (1=yes, 0=no)'),
            ('active_duration_seconds', 'INTEGER', 'Time actively viewing in seconds'),
            ('created_at', 'TIMESTAMP', 'Record creation timestamp'),
        ]
    },
    'search_queries': {
        'description': 'Search queries made in search engines',
        'fields': [
            ('id', 'INTEGER', 'Unique record identifier'),
            ('query', 'TEXT', 'The search query text'),
            ('search_engine', 'TEXT', 'Search engine used (google, bing, etc.)'),
            ('search_time', 'TIMESTAMP', 'When search was performed'),
            ('results_clicked', 'TEXT', 'Comma-separated clicked result URLs'),
            ('browsing_history_id', 'INTEGER', 'Link to browsing_history record'),
        ]
    },
    'search_result_clicks': {
        'description': 'Clicks on search results',
        'fields': [
            ('id', 'INTEGER', 'Unique record identifier'),
            ('search_query_id', 'INTEGER', 'Link to search_queries record'),
            ('result_url', 'TEXT', 'URL of the clicked result'),
            ('result_title', 'TEXT', 'Title of the clicked result'),
            ('result_position', 'INTEGER', 'Position in search results (1-based)'),
            ('click_time', 'TIMESTAMP', 'When the result was clicked'),
            ('time_on_page_seconds', 'INTEGER', 'Time spent on result page in seconds'),
        ]
    },
    'application_usage': {
        'description': 'Desktop application usage tracking',
        'fields': [
            ('id', 'INTEGER', 'Unique record identifier'),
            ('app_name', 'TEXT', 'Application name'),
            ('app_bundle_id', 'TEXT', 'macOS application bundle identifier'),
            ('window_title', 'TEXT', 'Active window title'),
            ('start_time', 'TIMESTAMP', 'When app became active/focused'),
            ('end_time', 'TIMESTAMP', 'When app lost focus'),
            ('duration_seconds', 'INTEGER', 'Time spent in app in seconds'),
            ('is_browser', 'BOOLEAN', 'Whether app is a browser (1=yes, 0=no)'),
            ('created_at', 'TIMESTAMP', 'Record creation timestamp'),
        ]
    },
    'user_sessions': {
        'description': 'User session tracking',
        'fields': [
            ('id', 'INTEGER', 'Unique record identifier'),
            ('session_start', 'TIMESTAMP', 'Session start time'),
            ('session_end', 'TIMESTAMP', 'Session end time'),
            ('total_active_seconds', 'INTEGER', 'Total active time in seconds'),
            ('total_idle_seconds', 'INTEGER', 'Total idle time in seconds'),
            ('device_info', 'TEXT', 'Device/system information'),
        ]
    },
    'navigation_events': {
        'description': 'Browser navigation events with transition details',
        'fields': [
            ('id', 'INTEGER', 'Unique record identifier'),
            ('url', 'TEXT', 'Navigation destination URL'),
            ('tab_id', 'INTEGER', 'Browser tab identifier'),
            ('opener_tab_id', 'INTEGER', 'Parent/opener tab identifier'),
            ('transition_type', 'TEXT', 'How navigation occurred (link, typed, reload, etc.)'),
            ('transition_qualifiers', 'TEXT', 'Additional transition qualifiers'),
            ('is_spa_navigation', 'BOOLEAN', 'Single-page app navigation (1=yes, 0=no)'),
            ('event_time', 'TIMESTAMP', 'When navigation occurred'),
        ]
    },
    'downloads': {
        'description': 'File downloads',
        'fields': [
            ('id', 'INTEGER', 'Unique record identifier'),
            ('filename', 'TEXT', 'Downloaded file name'),
            ('url', 'TEXT', 'Download source URL'),
            ('mime_type', 'TEXT', 'File MIME type (application/pdf, etc.)'),
            ('file_size', 'INTEGER', 'File size in bytes'),
            ('download_time', 'TIMESTAMP', 'When file was downloaded'),
        ]
    },
    'bookmarks': {
        'description': 'Bookmarked pages',
        'fields': [
            ('id', 'INTEGER', 'Unique record identifier'),
            ('url', 'TEXT', 'Bookmarked page URL'),
            ('title', 'TEXT', 'Bookmark title'),
            ('bookmark_time', 'TIMESTAMP', 'When bookmark was created'),
        ]
    },
    'user_interactions': {
        'description': 'User interactions on pages (privacy-preserving)',
        'fields': [
            ('id', 'INTEGER', 'Unique record identifier'),
            ('url', 'TEXT', 'Page URL where interaction occurred'),
            ('tab_id', 'INTEGER', 'Browser tab identifier'),
            ('interaction_type', 'TEXT', 'Type of interaction (click, scroll, etc.)'),
            ('interaction_data', 'TEXT', 'Additional interaction data (JSON)'),
            ('event_time', 'TIMESTAMP', 'When interaction occurred'),
        ]
    },
}


def connect_db():
    """Connect to the database"""
    return sqlite3.connect(str(DB_PATH))


def export_table_to_csv(table_name, output_dir, start_date=None, end_date=None):
    """Export a single table to CSV"""
    conn = connect_db()
    cursor = conn.cursor()

    table_info = TABLES.get(table_name)
    if not table_info:
        print(f"Unknown table: {table_name}")
        return None

    # Build query
    query = f'SELECT * FROM {table_name}'
    params = []

    # Add date filter if applicable
    time_column = None
    for field_name, _, _ in table_info['fields']:
        if field_name in ['visit_time', 'search_time', 'click_time', 'start_time',
                          'session_start', 'event_time', 'download_time', 'bookmark_time']:
            time_column = field_name
            break

    if time_column and start_date:
        query += f' WHERE {time_column} >= ?'
        params.append(start_date)
        if end_date:
            query += f' AND {time_column} <= ?'
            params.append(end_date)

    query += f' ORDER BY id DESC'

    try:
        cursor.execute(query, params)
        rows = cursor.fetchall()
    except sqlite3.OperationalError as e:
        print(f"Table {table_name} not found or error: {e}")
        conn.close()
        return None

    # Get column names
    columns = [field[0] for field in table_info['fields']]

    # Write CSV
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    csv_file = output_path / f'{table_name}.csv'

    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    conn.close()
    return csv_file, len(rows)


def export_schema_documentation(output_dir):
    """Export schema documentation as CSV"""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Schema overview
    schema_file = output_path / '_schema_documentation.csv'
    with open(schema_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['table_name', 'field_name', 'field_type', 'description'])

        for table_name, table_info in TABLES.items():
            for field_name, field_type, description in table_info['fields']:
                writer.writerow([table_name, field_name, field_type, description])

    # Table summary
    summary_file = output_path / '_tables_summary.csv'
    with open(summary_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['table_name', 'description', 'field_count'])

        for table_name, table_info in TABLES.items():
            writer.writerow([
                table_name,
                table_info['description'],
                len(table_info['fields'])
            ])

    return schema_file, summary_file


def export_all(output_dir, start_date=None, end_date=None, tables=None):
    """Export all tables to CSV files"""
    output_path = Path(output_dir)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    export_dir = output_path / f'raw_export_{timestamp}'
    export_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nExporting raw data to: {export_dir}\n")
    print("-" * 50)

    # Export schema documentation
    schema_file, summary_file = export_schema_documentation(export_dir)
    print(f"Schema documentation: {schema_file.name}")
    print(f"Tables summary: {summary_file.name}")
    print("-" * 50)

    # Export each table
    tables_to_export = tables if tables else TABLES.keys()
    total_records = 0

    for table_name in tables_to_export:
        if table_name not in TABLES:
            print(f"Skipping unknown table: {table_name}")
            continue

        result = export_table_to_csv(table_name, export_dir, start_date, end_date)
        if result:
            csv_file, count = result
            print(f"{table_name}: {count} records -> {csv_file.name}")
            total_records += count
        else:
            print(f"{table_name}: No data or table not found")

    print("-" * 50)
    print(f"Total: {total_records} records exported")
    print(f"Output directory: {export_dir}")

    return str(export_dir)


def print_field_summary():
    """Print a summary of all fields"""
    print("\n" + "=" * 70)
    print("RAW DATA FIELDS SUMMARY")
    print("=" * 70)

    total_fields = 0
    for table_name, table_info in TABLES.items():
        print(f"\n{table_name.upper()}")
        print(f"  Description: {table_info['description']}")
        print(f"  Fields ({len(table_info['fields'])}):")
        for field_name, field_type, description in table_info['fields']:
            print(f"    - {field_name} ({field_type}): {description}")
            total_fields += 1

    print("\n" + "=" * 70)
    print(f"Total: {len(TABLES)} tables, {total_fields} fields")
    print("=" * 70 + "\n")


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(
        description='Export raw tracking data to CSV files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export all data
  python export_raw.py

  # Export last 7 days
  python export_raw.py --days 7

  # Export specific tables
  python export_raw.py --tables browsing_history search_queries

  # Show field summary without exporting
  python export_raw.py --show-fields
        """
    )

    parser.add_argument('--output', type=str, default='./exports',
                       help='Output directory (default: ./exports)')
    parser.add_argument('--days', type=int,
                       help='Export last N days only')
    parser.add_argument('--start', type=str,
                       help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str,
                       help='End date (YYYY-MM-DD)')
    parser.add_argument('--tables', nargs='+',
                       help='Specific tables to export')
    parser.add_argument('--show-fields', action='store_true',
                       help='Show field summary and exit')

    args = parser.parse_args()

    # Show fields summary
    if args.show_fields:
        print_field_summary()
        return 0

    # Check database
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        print("Please run setup.sh first.")
        return 1

    # Calculate date range
    start_date = args.start
    end_date = args.end

    if args.days:
        end_date = datetime.now().isoformat()
        start_date = (datetime.now() - timedelta(days=args.days)).isoformat()

    # Export
    try:
        export_dir = export_all(
            args.output,
            start_date=start_date,
            end_date=end_date,
            tables=args.tables
        )
        print(f"\nExport complete!")
        return 0

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
