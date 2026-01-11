#!/usr/bin/env python3
"""
PDF Insights Report Generator
Generates comprehensive activity insights reports with visualizations
"""

import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict
from urllib.parse import urlparse
import io

# PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, Image, HRFlowable
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.widgets.markers import makeMarker

# Database path
DB_PATH = Path(__file__).parent.parent / 'database' / 'activity.db'


def connect_db():
    """Connect to the database"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def format_duration(seconds):
    """Format seconds into human-readable duration"""
    if seconds is None or seconds == 0:
        return "0m"
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    return f"{minutes}m"


def get_domain(url):
    """Extract domain from URL"""
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        # Remove www. prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        return domain
    except:
        return url


class InsightsReportGenerator:
    """Generate PDF insights reports from activity data"""

    # App categories for productivity analysis
    PRODUCTIVE_APPS = {
        'Code', 'Visual Studio Code', 'Xcode', 'Terminal', 'iTerm', 'iTerm2',
        'PyCharm', 'Sublime Text', 'Vim', 'Neovim', 'Atom', 'WebStorm',
        'IntelliJ IDEA', 'Android Studio', 'Eclipse',
        'Microsoft Word', 'Pages', 'Keynote', 'Numbers', 'Notes',
        'Excel', 'PowerPoint', 'Google Docs', 'Notion', 'Obsidian',
        'Figma', 'Sketch', 'Adobe Photoshop', 'Adobe Illustrator',
        'Slack', 'Microsoft Teams', 'Zoom', 'Calendar', 'Mail',
        'Finder', 'Preview', 'Safari', 'Firefox', 'Google Chrome'
    }

    DISTRACTION_APPS = {
        'YouTube', 'Netflix', 'Spotify', 'Music', 'TV',
        'Discord', 'Messages', 'WhatsApp', 'Telegram',
        'Twitter', 'Facebook', 'Instagram', 'TikTok', 'Reddit',
        'Steam', 'Epic Games', 'Game Center'
    }

    PRODUCTIVE_DOMAINS = {
        'github.com', 'gitlab.com', 'bitbucket.org', 'stackoverflow.com',
        'docs.python.org', 'developer.mozilla.org', 'w3schools.com',
        'medium.com', 'dev.to', 'hackernews.com', 'arxiv.org',
        'coursera.org', 'udemy.com', 'edx.org', 'linkedin.com',
        'notion.so', 'figma.com', 'trello.com', 'asana.com', 'jira.atlassian.com',
        'aws.amazon.com', 'cloud.google.com', 'azure.microsoft.com',
        'docs.google.com', 'drive.google.com', 'mail.google.com'
    }

    DISTRACTION_DOMAINS = {
        'youtube.com', 'netflix.com', 'twitch.tv', 'reddit.com',
        'twitter.com', 'x.com', 'facebook.com', 'instagram.com', 'tiktok.com',
        'buzzfeed.com', '9gag.com', 'imgur.com'
    }

    def __init__(self, days=7, output_path=None):
        self.days = days
        self.start_date = datetime.now() - timedelta(days=days)
        self.end_date = datetime.now()

        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = Path(__file__).parent.parent / 'exports' / f'insights_report_{timestamp}.pdf'

        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self.conn = connect_db()
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles"""
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#1a1a2e')
        ))

        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.HexColor('#16213e')
        ))

        self.styles.add(ParagraphStyle(
            name='SubSection',
            parent=self.styles['Heading3'],
            fontSize=12,
            spaceBefore=10,
            spaceAfter=6,
            textColor=colors.HexColor('#0f3460')
        ))

        self.styles.add(ParagraphStyle(
            name='InsightText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceBefore=4,
            spaceAfter=4,
            leftIndent=10,
            textColor=colors.HexColor('#333333')
        ))

        self.styles.add(ParagraphStyle(
            name='HighlightGood',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#28a745'),
            leftIndent=10
        ))

        self.styles.add(ParagraphStyle(
            name='HighlightBad',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#dc3545'),
            leftIndent=10
        ))

        self.styles.add(ParagraphStyle(
            name='Stat',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceBefore=2,
            spaceAfter=2
        ))

    def _get_browsing_data(self):
        """Fetch browsing history data"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT url, title, visit_time, duration_seconds, active_duration_seconds
            FROM browsing_history
            WHERE visit_time >= ?
            ORDER BY visit_time DESC
        ''', (self.start_date.isoformat(),))
        return cursor.fetchall()

    def _get_search_data(self):
        """Fetch search query data"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT sq.query, sq.search_time, sq.search_engine,
                   COUNT(src.id) as click_count
            FROM search_queries sq
            LEFT JOIN search_result_clicks src ON sq.id = src.search_query_id
            WHERE sq.search_time >= ?
            GROUP BY sq.id
            ORDER BY sq.search_time DESC
        ''', (self.start_date.isoformat(),))
        return cursor.fetchall()

    def _get_app_data(self):
        """Fetch application usage data"""
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT app_name, window_title, start_time, duration_seconds, is_browser
            FROM application_usage
            WHERE start_time >= ?
            ORDER BY start_time DESC
        ''', (self.start_date.isoformat(),))
        return cursor.fetchall()

    def _analyze_browsing_patterns(self, browsing_data):
        """Analyze browsing patterns and generate insights"""
        if not browsing_data:
            return {
                'total_sites': 0,
                'total_time': 0,
                'domains': {},
                'hourly_activity': defaultdict(int),
                'daily_activity': defaultdict(int),
                'productive_time': 0,
                'distraction_time': 0,
                'insights': []
            }

        domains = defaultdict(lambda: {'visits': 0, 'time': 0, 'titles': set()})
        hourly_activity = defaultdict(int)
        daily_activity = defaultdict(int)
        productive_time = 0
        distraction_time = 0
        total_time = 0

        for row in browsing_data:
            url = row['url']
            domain = get_domain(url)
            duration = row['duration_seconds'] or 0

            domains[domain]['visits'] += 1
            domains[domain]['time'] += duration
            if row['title']:
                domains[domain]['titles'].add(row['title'][:50])

            total_time += duration

            # Hourly activity
            try:
                visit_time = datetime.fromisoformat(row['visit_time'])
                hourly_activity[visit_time.hour] += duration
                daily_activity[visit_time.strftime('%Y-%m-%d')] += duration
            except:
                pass

            # Categorize
            if any(pd in domain for pd in self.PRODUCTIVE_DOMAINS):
                productive_time += duration
            elif any(dd in domain for dd in self.DISTRACTION_DOMAINS):
                distraction_time += duration

        # Generate insights
        insights = []

        # Top domain insight
        if domains:
            top_domain = max(domains.items(), key=lambda x: x[1]['time'])
            insights.append(f"Most time spent on: {top_domain[0]} ({format_duration(top_domain[1]['time'])})")

        # Peak hours insight
        if hourly_activity:
            peak_hour = max(hourly_activity.items(), key=lambda x: x[1])
            insights.append(f"Peak browsing hour: {peak_hour[0]}:00 - {peak_hour[0]+1}:00")

        # Productivity ratio
        if total_time > 0:
            prod_ratio = (productive_time / total_time) * 100
            if prod_ratio >= 60:
                insights.append(f"Great focus! {prod_ratio:.0f}% of browsing was productive")
            elif prod_ratio < 40:
                insights.append(f"Consider reducing distractions. Only {prod_ratio:.0f}% was productive browsing")

        # Visit frequency
        if domains:
            avg_visits = sum(d['visits'] for d in domains.values()) / len(domains)
            frequent_sites = [d for d, v in domains.items() if v['visits'] > avg_visits * 2]
            if frequent_sites:
                insights.append(f"Frequently revisited: {', '.join(frequent_sites[:3])}")

        return {
            'total_sites': len(domains),
            'total_time': total_time,
            'domains': dict(domains),
            'hourly_activity': dict(hourly_activity),
            'daily_activity': dict(daily_activity),
            'productive_time': productive_time,
            'distraction_time': distraction_time,
            'insights': insights
        }

    def _analyze_search_patterns(self, search_data):
        """Analyze search patterns and generate insights"""
        if not search_data:
            return {
                'total_searches': 0,
                'topics': defaultdict(int),
                'daily_searches': defaultdict(int),
                'avg_clicks': 0,
                'insights': []
            }

        total_searches = len(search_data)
        total_clicks = sum(row['click_count'] or 0 for row in search_data)
        topics = defaultdict(int)
        daily_searches = defaultdict(int)
        queries = []

        for row in search_data:
            query = row['query']
            queries.append(query.lower())

            try:
                search_time = datetime.fromisoformat(row['search_time'])
                daily_searches[search_time.strftime('%Y-%m-%d')] += 1
            except:
                pass

            # Simple topic extraction (first significant word)
            words = query.lower().split()
            for word in words:
                if len(word) > 3 and word not in ['what', 'how', 'where', 'when', 'why', 'does', 'this', 'that', 'with', 'from']:
                    topics[word] += 1

        # Generate insights
        insights = []

        if total_searches > 0:
            avg_clicks = total_clicks / total_searches
            insights.append(f"Average {avg_clicks:.1f} results clicked per search")

            if avg_clicks < 1:
                insights.append("Tip: Consider refining searches - low click-through rate")

        if topics:
            top_topics = sorted(topics.items(), key=lambda x: x[1], reverse=True)[:5]
            topic_str = ', '.join([t[0] for t in top_topics])
            insights.append(f"Common search topics: {topic_str}")

        # Search patterns
        if daily_searches:
            avg_daily = total_searches / len(daily_searches)
            insights.append(f"Average {avg_daily:.1f} searches per day")

        return {
            'total_searches': total_searches,
            'topics': dict(topics),
            'daily_searches': dict(daily_searches),
            'avg_clicks': total_clicks / total_searches if total_searches > 0 else 0,
            'queries': queries[:20],  # Recent queries
            'insights': insights
        }

    def _analyze_app_usage(self, app_data):
        """Analyze application usage and generate insights"""
        if not app_data:
            return {
                'total_apps': 0,
                'total_time': 0,
                'apps': {},
                'productive_time': 0,
                'distraction_time': 0,
                'focus_score': 0,
                'insights': []
            }

        apps = defaultdict(lambda: {'time': 0, 'sessions': 0})
        productive_time = 0
        distraction_time = 0
        total_time = 0
        hourly_switches = defaultdict(int)

        prev_app = None
        for row in app_data:
            app_name = row['app_name']
            duration = row['duration_seconds'] or 0

            apps[app_name]['time'] += duration
            apps[app_name]['sessions'] += 1
            total_time += duration

            # Track app switches
            if prev_app and prev_app != app_name:
                try:
                    start_time = datetime.fromisoformat(row['start_time'])
                    hourly_switches[start_time.hour] += 1
                except:
                    pass
            prev_app = app_name

            # Categorize
            if app_name in self.PRODUCTIVE_APPS:
                productive_time += duration
            elif app_name in self.DISTRACTION_APPS:
                distraction_time += duration

        # Calculate focus score (based on app switching frequency and productive time)
        total_sessions = sum(a['sessions'] for a in apps.values())
        if total_sessions > 0 and total_time > 0:
            avg_session_length = total_time / total_sessions
            prod_ratio = productive_time / total_time
            # Score: longer sessions and more productive time = higher score
            focus_score = min(100, (avg_session_length / 60) * 10 + (prod_ratio * 50))
        else:
            focus_score = 0

        # Generate insights
        insights = []

        if apps:
            top_app = max(apps.items(), key=lambda x: x[1]['time'])
            insights.append(f"Most used app: {top_app[0]} ({format_duration(top_app[1]['time'])})")

        if total_time > 0:
            prod_pct = (productive_time / total_time) * 100
            insights.append(f"Productivity ratio: {prod_pct:.0f}% productive apps")

            if prod_pct >= 70:
                insights.append("Excellent focus on productive applications!")
            elif prod_pct < 40:
                insights.append("Consider reducing time on entertainment apps")

        if total_sessions > 0:
            avg_session = total_time / total_sessions
            insights.append(f"Average app session: {format_duration(int(avg_session))}")

            if avg_session < 120:  # Less than 2 minutes
                insights.append("High app switching detected - try focusing longer on each task")

        if focus_score > 0:
            if focus_score >= 70:
                insights.append(f"Focus Score: {focus_score:.0f}/100 - Great concentration!")
            elif focus_score >= 40:
                insights.append(f"Focus Score: {focus_score:.0f}/100 - Room for improvement")
            else:
                insights.append(f"Focus Score: {focus_score:.0f}/100 - Consider reducing multitasking")

        return {
            'total_apps': len(apps),
            'total_time': total_time,
            'apps': dict(apps),
            'productive_time': productive_time,
            'distraction_time': distraction_time,
            'focus_score': focus_score,
            'insights': insights
        }

    def _create_pie_chart(self, data, labels, title, width=300, height=200):
        """Create a pie chart"""
        if not data or sum(data) == 0:
            return None

        drawing = Drawing(width, height)
        pie = Pie()
        pie.x = width // 2 - 60
        pie.y = height // 2 - 50
        pie.width = 100
        pie.height = 100
        pie.data = data
        pie.labels = labels
        pie.slices.strokeWidth = 0.5

        # Colors
        chart_colors = [
            colors.HexColor('#4CAF50'),
            colors.HexColor('#2196F3'),
            colors.HexColor('#FF9800'),
            colors.HexColor('#E91E63'),
            colors.HexColor('#9C27B0'),
            colors.HexColor('#00BCD4'),
            colors.HexColor('#8BC34A'),
            colors.HexColor('#FF5722'),
        ]

        for i in range(len(data)):
            pie.slices[i].fillColor = chart_colors[i % len(chart_colors)]
            pie.slices[i].popout = 2 if i == 0 else 0

        drawing.add(pie)
        return drawing

    def _create_bar_chart(self, data, labels, title, width=400, height=200):
        """Create a bar chart"""
        if not data:
            return None

        drawing = Drawing(width, height)
        bc = VerticalBarChart()
        bc.x = 50
        bc.y = 30
        bc.height = height - 60
        bc.width = width - 80
        bc.data = [data]
        bc.categoryAxis.categoryNames = labels
        bc.categoryAxis.labels.angle = 45
        bc.categoryAxis.labels.boxAnchor = 'ne'
        bc.categoryAxis.labels.fontSize = 8
        bc.valueAxis.valueMin = 0
        bc.bars[0].fillColor = colors.HexColor('#2196F3')

        drawing.add(bc)
        return drawing

    def generate(self):
        """Generate the complete PDF report"""
        # Fetch data
        browsing_data = self._get_browsing_data()
        search_data = self._get_search_data()
        app_data = self._get_app_data()

        # Analyze data
        browsing_analysis = self._analyze_browsing_patterns(browsing_data)
        search_analysis = self._analyze_search_patterns(search_data)
        app_analysis = self._analyze_app_usage(app_data)

        # Build PDF
        doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        story = []

        # Title
        story.append(Paragraph("Activity Insights Report", self.styles['ReportTitle']))
        story.append(Paragraph(
            f"Period: {self.start_date.strftime('%B %d, %Y')} - {self.end_date.strftime('%B %d, %Y')}",
            self.styles['Normal']
        ))
        story.append(Paragraph(
            f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            self.styles['Normal']
        ))
        story.append(Spacer(1, 20))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0')))
        story.append(Spacer(1, 20))

        # Executive Summary
        story.append(Paragraph("Executive Summary", self.styles['SectionTitle']))

        summary_data = [
            ['Metric', 'Value'],
            ['Total Browsing Time', format_duration(browsing_analysis['total_time'])],
            ['Unique Sites Visited', str(browsing_analysis['total_sites'])],
            ['Total Searches', str(search_analysis['total_searches'])],
            ['Applications Used', str(app_analysis['total_apps'])],
            ['App Usage Time', format_duration(app_analysis['total_time'])],
            ['Focus Score', f"{app_analysis['focus_score']:.0f}/100"],
        ]

        summary_table = Table(summary_data, colWidths=[200, 200])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8f9fa')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
        ]))
        story.append(summary_table)
        story.append(Spacer(1, 30))

        # Key Insights Section
        story.append(Paragraph("Key Insights", self.styles['SectionTitle']))

        all_insights = []
        all_insights.extend(browsing_analysis['insights'])
        all_insights.extend(search_analysis['insights'])
        all_insights.extend(app_analysis['insights'])

        if all_insights:
            for insight in all_insights:
                # Color code based on content
                if any(word in insight.lower() for word in ['great', 'excellent', 'good']):
                    story.append(Paragraph(f"✓ {insight}", self.styles['HighlightGood']))
                elif any(word in insight.lower() for word in ['consider', 'reduce', 'tip', 'low']):
                    story.append(Paragraph(f"! {insight}", self.styles['HighlightBad']))
                else:
                    story.append(Paragraph(f"• {insight}", self.styles['InsightText']))
        else:
            story.append(Paragraph("No activity data available for this period.", self.styles['InsightText']))

        story.append(Spacer(1, 20))

        # Browsing Analysis Section
        story.append(Paragraph("Browsing Analysis", self.styles['SectionTitle']))

        if browsing_analysis['domains']:
            # Top Sites Table
            story.append(Paragraph("Top Sites by Time Spent", self.styles['SubSection']))

            top_domains = sorted(
                browsing_analysis['domains'].items(),
                key=lambda x: x[1]['time'],
                reverse=True
            )[:10]

            sites_data = [['Site', 'Visits', 'Time Spent']]
            for domain, stats in top_domains:
                sites_data.append([
                    domain[:40],
                    str(stats['visits']),
                    format_duration(stats['time'])
                ])

            sites_table = Table(sites_data, colWidths=[250, 80, 100])
            sites_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            story.append(sites_table)
            story.append(Spacer(1, 15))

            # Productivity breakdown
            story.append(Paragraph("Browsing Productivity", self.styles['SubSection']))
            productive = browsing_analysis['productive_time']
            distraction = browsing_analysis['distraction_time']
            other = browsing_analysis['total_time'] - productive - distraction

            if productive + distraction + other > 0:
                prod_data = [productive, distraction, other]
                prod_labels = [
                    f"Productive\n{format_duration(productive)}",
                    f"Distracting\n{format_duration(distraction)}",
                    f"Other\n{format_duration(other)}"
                ]
                chart = self._create_pie_chart(prod_data, prod_labels, "Browsing Categories")
                if chart:
                    story.append(chart)
        else:
            story.append(Paragraph("No browsing data available for this period.", self.styles['InsightText']))

        story.append(Spacer(1, 20))

        # Search Analysis Section
        story.append(Paragraph("Search Activity", self.styles['SectionTitle']))

        if search_analysis['total_searches'] > 0:
            story.append(Paragraph(f"Total searches: {search_analysis['total_searches']}", self.styles['Stat']))
            story.append(Paragraph(f"Average clicks per search: {search_analysis['avg_clicks']:.1f}", self.styles['Stat']))

            if search_analysis['topics']:
                story.append(Spacer(1, 10))
                story.append(Paragraph("Top Search Topics", self.styles['SubSection']))

                top_topics = sorted(search_analysis['topics'].items(), key=lambda x: x[1], reverse=True)[:8]
                topic_data = [['Topic', 'Frequency']]
                for topic, count in top_topics:
                    topic_data.append([topic.capitalize(), str(count)])

                topic_table = Table(topic_data, colWidths=[200, 80])
                topic_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0f3460')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ]))
                story.append(topic_table)
        else:
            story.append(Paragraph("No search data available for this period.", self.styles['InsightText']))

        story.append(Spacer(1, 20))

        # Application Usage Section
        story.append(Paragraph("Application Usage", self.styles['SectionTitle']))

        if app_analysis['apps']:
            story.append(Paragraph("Top Applications", self.styles['SubSection']))

            top_apps = sorted(
                app_analysis['apps'].items(),
                key=lambda x: x[1]['time'],
                reverse=True
            )[:10]

            apps_data = [['Application', 'Sessions', 'Total Time']]
            for app_name, stats in top_apps:
                apps_data.append([
                    app_name[:35],
                    str(stats['sessions']),
                    format_duration(stats['time'])
                ])

            apps_table = Table(apps_data, colWidths=[220, 80, 100])
            apps_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1a1a2e')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            story.append(apps_table)
            story.append(Spacer(1, 15))

            # App productivity breakdown
            story.append(Paragraph("App Usage Categories", self.styles['SubSection']))
            prod_time = app_analysis['productive_time']
            dist_time = app_analysis['distraction_time']
            other_time = app_analysis['total_time'] - prod_time - dist_time

            if prod_time + dist_time + other_time > 0:
                app_prod_data = [prod_time, dist_time, other_time]
                app_prod_labels = [
                    f"Productive\n{format_duration(prod_time)}",
                    f"Entertainment\n{format_duration(dist_time)}",
                    f"Other\n{format_duration(other_time)}"
                ]
                chart = self._create_pie_chart(app_prod_data, app_prod_labels, "App Categories")
                if chart:
                    story.append(chart)
        else:
            story.append(Paragraph("No application usage data available for this period.", self.styles['InsightText']))

        story.append(Spacer(1, 30))

        # Daily Activity Section
        story.append(Paragraph("Daily Activity Trends", self.styles['SectionTitle']))

        if browsing_analysis['daily_activity']:
            daily_data = []
            daily_labels = []

            for date_str in sorted(browsing_analysis['daily_activity'].keys()):
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    daily_labels.append(date_obj.strftime('%m/%d'))
                    daily_data.append(browsing_analysis['daily_activity'][date_str] / 60)  # Convert to minutes
                except:
                    pass

            if daily_data and len(daily_data) > 1:
                daily_table_data = [['Date', 'Browsing Time']]
                for i, label in enumerate(daily_labels):
                    daily_table_data.append([label, format_duration(int(daily_data[i] * 60))])

                daily_table = Table(daily_table_data, colWidths=[100, 120])
                daily_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#16213e')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dee2e6')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ]))
                story.append(daily_table)

        story.append(Spacer(1, 30))

        # Recommendations Section
        story.append(Paragraph("Recommendations", self.styles['SectionTitle']))

        recommendations = []

        # Based on productivity score
        if app_analysis['focus_score'] < 50:
            recommendations.append("Try using focus apps or website blockers during work hours to improve concentration.")

        if app_analysis['productive_time'] > 0 and app_analysis['total_time'] > 0:
            prod_ratio = app_analysis['productive_time'] / app_analysis['total_time']
            if prod_ratio < 0.5:
                recommendations.append("Consider scheduling dedicated focus time blocks for deep work.")

        # Based on browsing patterns
        if browsing_analysis['distraction_time'] > browsing_analysis['productive_time']:
            recommendations.append("Review your bookmarks and consider removing easy access to distracting sites.")

        # Based on search patterns
        if search_analysis['avg_clicks'] < 1:
            recommendations.append("Your search queries might be too broad. Try using more specific terms.")

        # Default recommendation
        if not recommendations:
            recommendations.append("Keep up the good work! Your activity patterns show healthy digital habits.")

        for rec in recommendations:
            story.append(Paragraph(f"→ {rec}", self.styles['InsightText']))

        story.append(Spacer(1, 30))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0')))
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "This report was automatically generated by AI Activity Recommender. All data is stored locally on your device.",
            ParagraphStyle(
                name='Footer',
                parent=self.styles['Normal'],
                fontSize=8,
                textColor=colors.HexColor('#666666'),
                alignment=1  # Center
            )
        ))

        # Build PDF
        doc.build(story)
        self.conn.close()

        return str(self.output_path)


def main():
    """Command-line interface"""
    parser = argparse.ArgumentParser(description='Generate PDF insights report')
    parser.add_argument('--days', type=int, default=7,
                       help='Number of days to analyze (default: 7)')
    parser.add_argument('--output', type=str,
                       help='Output PDF file path')

    args = parser.parse_args()

    # Check if database exists
    if not DB_PATH.exists():
        print(f"Error: Database not found at {DB_PATH}")
        print("Please run setup.sh first to initialize the database.")
        return 1

    try:
        print(f"\nGenerating insights report for the last {args.days} days...\n")

        generator = InsightsReportGenerator(
            days=args.days,
            output_path=args.output
        )

        output_file = generator.generate()

        print(f"Report generated successfully!")
        print(f"Output: {output_file}")

        return 0

    except ImportError as e:
        print(f"Error: Missing required package - {e}")
        print("\nPlease install reportlab:")
        print("  pip install reportlab")
        return 1

    except Exception as e:
        print(f"Error generating report: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    exit(main())
