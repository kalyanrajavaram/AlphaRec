#!/usr/bin/env python3
"""
Query Tools for Activity Database
Provides functions to analyze browsing and application usage data
"""

import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse


# Database path
DB_PATH = Path(__file__).parent.parent / 'database' / 'activity.db'


def connect_db():
    """Connect to the database"""
    return sqlite3.connect(str(DB_PATH))


def get_top_sites(days=7, limit=10):
    """Get most visited sites in the last N days"""
    conn = connect_db()
    cursor = conn.cursor()

    start_date = datetime.now() - timedelta(days=days)

    cursor.execute('''
        SELECT url, title, COUNT(*) as visits, SUM(duration_seconds) as total_time
        FROM browsing_history
        WHERE visit_time >= ?
        GROUP BY url
        ORDER BY total_time DESC
        LIMIT ?
    ''', (start_date.isoformat(), limit))

    results = cursor.fetchall()
    conn.close()

    print(f"\n=== Top {limit} Sites (Last {days} Days) ===\n")
    for i, (url, title, visits, total_time) in enumerate(results, 1):
        domain = urlparse(url).netloc
        hours = total_time // 3600
        minutes = (total_time % 3600) // 60
        print(f"{i}. {domain}")
        print(f"   Title: {title}")
        print(f"   Visits: {visits}, Time: {hours}h {minutes}m")
        print()


def get_time_by_domain(days=7):
    """Get total time spent per domain"""
    conn = connect_db()
    cursor = conn.cursor()

    start_date = datetime.now() - timedelta(days=days)

    # Get all URLs and their times
    cursor.execute('''
        SELECT url, SUM(duration_seconds) as total_time
        FROM browsing_history
        WHERE visit_time >= ?
        GROUP BY url
        ORDER BY total_time DESC
    ''', (start_date.isoformat(),))

    # Group by domain
    domain_times = {}
    for url, total_time in cursor.fetchall():
        domain = urlparse(url).netloc
        domain_times[domain] = domain_times.get(domain, 0) + total_time

    conn.close()

    # Sort by time
    sorted_domains = sorted(domain_times.items(), key=lambda x: x[1], reverse=True)

    print(f"\n=== Time by Domain (Last {days} Days) ===\n")
    for domain, total_time in sorted_domains[:15]:
        hours = total_time // 3600
        minutes = (total_time % 3600) // 60
        print(f"{domain}: {hours}h {minutes}m")


def get_search_queries(days=7, limit=20):
    """Get recent search queries"""
    conn = connect_db()
    cursor = conn.cursor()

    start_date = datetime.now() - timedelta(days=days)

    cursor.execute('''
        SELECT sq.query, sq.search_time, COUNT(src.id) as clicks
        FROM search_queries sq
        LEFT JOIN search_result_clicks src ON sq.id = src.search_query_id
        WHERE sq.search_time >= ?
        GROUP BY sq.id
        ORDER BY sq.search_time DESC
        LIMIT ?
    ''', (start_date.isoformat(), limit))

    results = cursor.fetchall()
    conn.close()

    print(f"\n=== Search Queries (Last {days} Days) ===\n")
    for query, search_time, clicks in results:
        dt = datetime.fromisoformat(search_time)
        print(f"{dt.strftime('%Y-%m-%d %H:%M')} - \"{query}\" ({clicks} clicks)")


def get_application_usage(days=7):
    """Get application usage statistics"""
    conn = connect_db()
    cursor = conn.cursor()

    start_date = datetime.now() - timedelta(days=days)

    cursor.execute('''
        SELECT app_name, COUNT(*) as sessions, SUM(duration_seconds) as total_time
        FROM application_usage
        WHERE start_time >= ? AND is_browser = 0
        GROUP BY app_name
        ORDER BY total_time DESC
    ''', (start_date.isoformat(),))

    results = cursor.fetchall()
    conn.close()

    print(f"\n=== Application Usage (Last {days} Days) ===\n")
    for app_name, sessions, total_time in results:
        hours = total_time // 3600
        minutes = (total_time % 3600) // 60
        print(f"{app_name}: {hours}h {minutes}m ({sessions} sessions)")


def get_daily_summary(date=None):
    """Get complete activity summary for a specific date"""
    if date is None:
        date = datetime.now().date()
    elif isinstance(date, str):
        date = datetime.fromisoformat(date).date()

    conn = connect_db()
    cursor = conn.cursor()

    print(f"\n=== Daily Summary: {date} ===\n")

    # Browsing stats
    cursor.execute('''
        SELECT COUNT(*), SUM(duration_seconds)
        FROM browsing_history
        WHERE DATE(visit_time) = ?
    ''', (date,))
    sites_count, browse_time = cursor.fetchone()
    browse_time = browse_time or 0

    print(f"Browsing:")
    print(f"  Sites visited: {sites_count}")
    print(f"  Total time: {browse_time // 3600}h {(browse_time % 3600) // 60}m")
    print()

    # Search stats
    cursor.execute('''
        SELECT COUNT(*)
        FROM search_queries
        WHERE DATE(search_time) = ?
    ''', (date,))
    search_count = cursor.fetchone()[0]
    print(f"Searches: {search_count}")
    print()

    # Application stats
    cursor.execute('''
        SELECT COUNT(*), SUM(duration_seconds)
        FROM application_usage
        WHERE DATE(start_time) = ? AND is_browser = 0
    ''', (date,))
    app_sessions, app_time = cursor.fetchone()
    app_time = app_time or 0

    print(f"Applications:")
    print(f"  Sessions: {app_sessions}")
    print(f"  Total time: {app_time // 3600}h {(app_time % 3600) // 60}m")

    conn.close()


def get_productivity_score(days=7):
    """Calculate productivity score based on app usage"""
    # Define productive apps (you can customize this)
    productive_apps = {
        'Code', 'Visual Studio Code', 'Xcode', 'Terminal',
        'iTerm', 'PyCharm', 'Sublime Text', 'Vim',
        'Microsoft Word', 'Pages', 'Keynote', 'Numbers',
        'Excel', 'PowerPoint'
    }

    conn = connect_db()
    cursor = conn.cursor()

    start_date = datetime.now() - timedelta(days=days)

    # Get total time
    cursor.execute('''
        SELECT SUM(duration_seconds)
        FROM application_usage
        WHERE start_time >= ?
    ''', (start_date.isoformat(),))
    total_time = cursor.fetchone()[0] or 1

    # Get productive time
    placeholders = ','.join('?' * len(productive_apps))
    cursor.execute(f'''
        SELECT SUM(duration_seconds)
        FROM application_usage
        WHERE start_time >= ? AND app_name IN ({placeholders})
    ''', (start_date.isoformat(), *productive_apps))
    productive_time = cursor.fetchone()[0] or 0

    conn.close()

    score = (productive_time / total_time) * 100 if total_time > 0 else 0

    print(f"\n=== Productivity Score (Last {days} Days) ===\n")
    print(f"Productive time: {productive_time // 3600}h {(productive_time % 3600) // 60}m")
    print(f"Total time: {total_time // 3600}h {(total_time % 3600) // 60}m")
    print(f"Score: {score:.1f}%")
    print()


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(description='Query activity tracking data')
    parser.add_argument('--top-sites', action='store_true', help='Show top visited sites')
    parser.add_argument('--time-by-domain', action='store_true', help='Show time by domain')
    parser.add_argument('--search-queries', action='store_true', help='Show search queries')
    parser.add_argument('--app-usage', action='store_true', help='Show application usage')
    parser.add_argument('--daily-summary', action='store_true', help='Show daily summary')
    parser.add_argument('--productivity', action='store_true', help='Show productivity score')
    parser.add_argument('--days', type=int, default=7, help='Number of days to analyze (default: 7)')
    parser.add_argument('--date', type=str, help='Specific date for daily summary (YYYY-MM-DD)')
    parser.add_argument('--all', action='store_true', help='Show all reports')

    args = parser.parse_args()

    # Check if database exists
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        print("Please run setup.sh first.")
        return

    # If no specific query requested, show all
    if not any([args.top_sites, args.time_by_domain, args.search_queries,
                args.app_usage, args.daily_summary, args.productivity]):
        args.all = True

    try:
        if args.all or args.top_sites:
            get_top_sites(days=args.days)

        if args.all or args.time_by_domain:
            get_time_by_domain(days=args.days)

        if args.all or args.search_queries:
            get_search_queries(days=args.days)

        if args.all or args.app_usage:
            get_application_usage(days=args.days)

        if args.all or args.daily_summary:
            get_daily_summary(args.date)

        if args.all or args.productivity:
            get_productivity_score(days=args.days)

    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    main()
