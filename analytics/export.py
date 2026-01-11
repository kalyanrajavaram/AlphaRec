#!/usr/bin/env python3
"""
Export Tools for Activity Database
Export browsing and application data to CSV or JSON
"""

import sqlite3
import csv
import json
import argparse
from datetime import datetime, timedelta
from pathlib import Path


# Database path
DB_PATH = Path(__file__).parent.parent / 'database' / 'activity.db'


def connect_db():
    """Connect to the database"""
    return sqlite3.connect(str(DB_PATH))


def export_browsing_history_csv(output_dir, start_date=None, end_date=None):
    """Export browsing history to CSV"""
    conn = connect_db()
    cursor = conn.cursor()

    query = 'SELECT * FROM browsing_history'
    params = []

    if start_date and end_date:
        query += ' WHERE visit_time >= ? AND visit_time <= ?'
        params = [start_date, end_date]
    elif start_date:
        query += ' WHERE visit_time >= ?'
        params = [start_date]

    query += ' ORDER BY visit_time DESC'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    output_file = Path(output_dir) / 'browsing_history.csv'
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    conn.close()
    print(f"Exported {len(rows)} browsing history records to {output_file}")
    return str(output_file)


def export_search_queries_csv(output_dir, start_date=None, end_date=None):
    """Export search queries to CSV"""
    conn = connect_db()
    cursor = conn.cursor()

    query = '''
        SELECT sq.*,
               GROUP_CONCAT(src.result_url, '; ') as clicked_urls
        FROM search_queries sq
        LEFT JOIN search_result_clicks src ON sq.id = src.search_query_id
    '''
    params = []

    if start_date and end_date:
        query += ' WHERE sq.search_time >= ? AND sq.search_time <= ?'
        params = [start_date, end_date]
    elif start_date:
        query += ' WHERE sq.search_time >= ?'
        params = [start_date]

    query += ' GROUP BY sq.id ORDER BY sq.search_time DESC'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    output_file = Path(output_dir) / 'search_queries.csv'

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    conn.close()
    print(f"Exported {len(rows)} search queries to {output_file}")
    return str(output_file)


def export_application_usage_csv(output_dir, start_date=None, end_date=None):
    """Export application usage to CSV"""
    conn = connect_db()
    cursor = conn.cursor()

    query = 'SELECT * FROM application_usage'
    params = []

    if start_date and end_date:
        query += ' WHERE start_time >= ? AND start_time <= ?'
        params = [start_date, end_date]
    elif start_date:
        query += ' WHERE start_time >= ?'
        params = [start_date]

    query += ' ORDER BY start_time DESC'

    cursor.execute(query, params)
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]

    output_file = Path(output_dir) / 'application_usage.csv'

    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(columns)
        writer.writerows(rows)

    conn.close()
    print(f"Exported {len(rows)} application usage records to {output_file}")
    return str(output_file)


def export_to_json(output_file, start_date=None, end_date=None, data_type='all'):
    """Export data to JSON format"""
    conn = connect_db()
    conn.row_factory = sqlite3.Row  # Enable column access by name
    cursor = conn.cursor()

    data = {}

    # Browsing history
    if data_type in ['all', 'browsing']:
        query = 'SELECT * FROM browsing_history'
        params = []

        if start_date and end_date:
            query += ' WHERE visit_time >= ? AND visit_time <= ?'
            params = [start_date, end_date]
        elif start_date:
            query += ' WHERE visit_time >= ?'
            params = [start_date]

        query += ' ORDER BY visit_time DESC'

        cursor.execute(query, params)
        data['browsing_history'] = [dict(row) for row in cursor.fetchall()]

    # Search queries
    if data_type in ['all', 'searches']:
        query = 'SELECT * FROM search_queries'
        params = []

        if start_date and end_date:
            query += ' WHERE search_time >= ? AND search_time <= ?'
            params = [start_date, end_date]
        elif start_date:
            query += ' WHERE search_time >= ?'
            params = [start_date]

        query += ' ORDER BY search_time DESC'

        cursor.execute(query, params)
        data['search_queries'] = [dict(row) for row in cursor.fetchall()]

        # Add clicks for each query
        for query in data['search_queries']:
            cursor.execute('''
                SELECT * FROM search_result_clicks
                WHERE search_query_id = ?
            ''', (query['id'],))
            query['clicks'] = [dict(row) for row in cursor.fetchall()]

    # Application usage
    if data_type in ['all', 'apps']:
        query = 'SELECT * FROM application_usage'
        params = []

        if start_date and end_date:
            query += ' WHERE start_time >= ? AND start_time <= ?'
            params = [start_date, end_date]
        elif start_date:
            query += ' WHERE start_time >= ?'
            params = [start_date]

        query += ' ORDER BY start_time DESC'

        cursor.execute(query, params)
        data['application_usage'] = [dict(row) for row in cursor.fetchall()]

    # Write JSON
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

    conn.close()

    total_records = sum(len(v) if isinstance(v, list) else 0 for v in data.values())
    print(f"Exported {total_records} total records to {output_path}")
    return str(output_path)


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(description='Export activity tracking data')
    parser.add_argument('--format', choices=['csv', 'json'], default='csv',
                       help='Export format (default: csv)')
    parser.add_argument('--output', type=str, default='./exports',
                       help='Output directory or file (default: ./exports)')
    parser.add_argument('--start', type=str, help='Start date (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='End date (YYYY-MM-DD)')
    parser.add_argument('--type', choices=['all', 'browsing', 'searches', 'apps'],
                       default='all', help='Data type to export (default: all)')
    parser.add_argument('--days', type=int, help='Export last N days')

    args = parser.parse_args()

    # Check if database exists
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        print("Please run setup.sh first.")
        return

    # Calculate date range
    start_date = args.start
    end_date = args.end

    if args.days:
        end_date = datetime.now().isoformat()
        start_date = (datetime.now() - timedelta(days=args.days)).isoformat()

    # Export data
    try:
        if args.format == 'csv':
            print(f"\nExporting data to CSV format...\n")

            if args.type in ['all', 'browsing']:
                export_browsing_history_csv(args.output, start_date, end_date)

            if args.type in ['all', 'searches']:
                export_search_queries_csv(args.output, start_date, end_date)

            if args.type in ['all', 'apps']:
                export_application_usage_csv(args.output, start_date, end_date)

            print(f"\nAll files exported to: {args.output}")

        elif args.format == 'json':
            print(f"\nExporting data to JSON format...\n")
            export_to_json(args.output, start_date, end_date, args.type)

    except Exception as e:
        print(f"Error during export: {e}")


if __name__ == '__main__':
    main()
