#!/usr/bin/env python3
"""
AI Tool Recommendations PDF Generator
Generates a professional PDF report with personalized AI tool recommendations,
user behavior insights, and workflow speedup suggestions.
"""

import json
import csv
import os
import argparse
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from openai import OpenAI

# PDF generation
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, KeepTogether
)
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie

# Configuration
EXPORTS_DIR = "exports/raw_export_20260110_214327"
TOOLS_FILE = "ai_tools_cleaned.json"
OUTPUT_DIR = Path("exports")


def load_user_data():
    """Load and parse all user behavior data from CSV exports."""
    user_data = {
        "browsing_history": [],
        "search_queries": [],
        "application_usage": [],
        "user_interactions": []
    }

    # Load browsing history
    browsing_path = os.path.join(EXPORTS_DIR, "browsing_history.csv")
    if os.path.exists(browsing_path):
        with open(browsing_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_data["browsing_history"].append({
                    "url": row.get("url", ""),
                    "title": row.get("title", ""),
                    "duration_seconds": int(row.get("duration_seconds", 0) or 0),
                    "active_duration_seconds": int(row.get("active_duration_seconds", 0) or 0),
                    "visit_time": row.get("visit_time", "")
                })

    # Load search queries
    search_path = os.path.join(EXPORTS_DIR, "search_queries.csv")
    if os.path.exists(search_path):
        with open(search_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_data["search_queries"].append({
                    "query": row.get("query", ""),
                    "search_engine": row.get("search_engine", ""),
                    "search_time": row.get("search_time", "")
                })

    # Load application usage
    app_path = os.path.join(EXPORTS_DIR, "application_usage.csv")
    if os.path.exists(app_path):
        with open(app_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_data["application_usage"].append({
                    "app_name": row.get("app_name", ""),
                    "window_title": row.get("window_title", ""),
                    "duration_seconds": int(row.get("duration_seconds", 0) or 0)
                })

    # Load user interactions
    interactions_path = os.path.join(EXPORTS_DIR, "user_interactions.csv")
    if os.path.exists(interactions_path):
        with open(interactions_path, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader:
                user_data["user_interactions"].append({
                    "url": row.get("url", ""),
                    "interaction_type": row.get("interaction_type", ""),
                    "interaction_data": row.get("interaction_data", "")
                })

    return user_data


def analyze_user_behavior(user_data):
    """Extract behavioral insights from user data."""
    insights = {
        "top_domains": defaultdict(int),
        "search_intents": [],
        "active_apps": defaultdict(int),
        "keyboard_intensity": {"light": 0, "moderate": 0, "heavy": 0},
        "ai_tools_used": [],
        "workflow_patterns": []
    }

    # Analyze browsing patterns
    ai_tool_domains = ["claude.ai", "chatgpt.com", "gemini.google.com", "perplexity.ai"]

    for entry in user_data["browsing_history"]:
        url = entry["url"]
        duration = entry["duration_seconds"]

        # Extract domain
        if "://" in url:
            domain = url.split("://")[1].split("/")[0]
            insights["top_domains"][domain] += duration

            # Track AI tool usage
            for ai_domain in ai_tool_domains:
                if ai_domain in url:
                    insights["ai_tools_used"].append({
                        "domain": ai_domain,
                        "duration": duration,
                        "title": entry["title"]
                    })

    # Analyze search queries
    for query in user_data["search_queries"]:
        insights["search_intents"].append(query["query"])

    # Analyze app usage
    for app in user_data["application_usage"]:
        insights["active_apps"][app["app_name"]] += app["duration_seconds"]

    # Analyze interaction intensity
    for interaction in user_data["user_interactions"]:
        if interaction["interaction_type"] == "keyboard_activity":
            try:
                data = json.loads(interaction["interaction_data"])
                level = data.get("level", "light")
                insights["keyboard_intensity"][level] += 1
            except:
                pass

    return insights


def load_ai_tools():
    """Load the AI tools database."""
    with open(TOOLS_FILE, 'r') as f:
        data = json.load(f)
    return data["tools"]


def create_user_profile_summary(insights):
    """Create a concise summary of user behavior for the LLM."""
    # Get top 10 domains by time spent
    sorted_domains = sorted(insights["top_domains"].items(), key=lambda x: x[1], reverse=True)[:10]

    # Get top 5 apps
    sorted_apps = sorted(insights["active_apps"].items(), key=lambda x: x[1], reverse=True)[:5]

    # Format AI tools usage
    ai_usage = {}
    for tool in insights["ai_tools_used"]:
        domain = tool["domain"]
        if domain not in ai_usage:
            ai_usage[domain] = 0
        ai_usage[domain] += tool["duration"]

    summary = f"""
USER BEHAVIOR PROFILE:

## Top Websites by Time Spent:
{chr(10).join([f"- {domain}: {duration}s" for domain, duration in sorted_domains])}

## Search Queries (showing intent):
{chr(10).join([f"- {q}" for q in insights["search_intents"][:15]])}

## Applications Used:
{chr(10).join([f"- {app}: {duration}s" for app, duration in sorted_apps])}

## AI Tools Already Using:
{chr(10).join([f"- {domain}: {duration}s" for domain, duration in ai_usage.items()])}

## Keyboard Activity Pattern:
- Light interactions: {insights["keyboard_intensity"]["light"]}
- Moderate interactions: {insights["keyboard_intensity"]["moderate"]}
- Heavy interactions: {insights["keyboard_intensity"]["heavy"]}
"""
    return summary


def create_tools_summary(tools, limit=100):
    """Create a summary of available AI tools for the LLM."""
    tools_list = []

    for tool in tools[:limit]:
        data = tool["data"]
        tool_info = {
            "name": data["name"],
            "description": data["description"][:200],
            "category": data["category"]["primary"],
            "capabilities": data["capabilities"]["task_verbs"][:5],
            "use_cases": data["matching"].get("use_cases", [])[:3],
            "pricing": data["pricing"]["model"],
            "free_tier": data["pricing"].get("free_tier", False)
        }
        tools_list.append(tool_info)

    return json.dumps(tools_list, indent=2)


def get_structured_recommendations(user_profile: str, tools_summary: str, client: OpenAI):
    """Get AI recommendations in structured JSON format."""

    system_prompt = """You are an AI tool recommendation expert. Based on the user's browsing behavior,
search queries, and application usage patterns, recommend the most relevant AI tools.

IMPORTANT: You MUST respond with valid JSON only. No markdown, no explanation, just JSON.

Return exactly this JSON structure:
{
  "recommendations": [
    {
      "tool_name": "exact tool name from the list",
      "reason": "2-3 sentences explaining why based on their specific behavior",
      "friction_point": "specific pain point this tool addresses",
      "use_case": "concrete example from their workflow",
      "priority": 1
    }
  ],
  "speedups": [
    {
      "description": "specific workflow improvement",
      "time_saved": "estimated time savings (e.g., '2-3 hours/week')"
    }
  ],
  "roadmap": [
    {
      "step": 1,
      "action": "first step to take",
      "tool": "tool name"
    }
  ]
}

Provide exactly 5 recommendations, 3-4 speedups, and 3-5 roadmap steps.
Focus on tools they are NOT already using heavily.
Reference specific behaviors from their data."""

    user_prompt = f"""
{user_profile}

## Available AI Tools:
{tools_summary}

Generate personalized recommendations based on this user's behavior patterns.
Return ONLY valid JSON, no other text."""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=3000,
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)


def enrich_recommendations(recommendations, tools):
    """Enrich recommendations with full tool metadata."""
    tools_by_name = {}
    for tool in tools:
        name = tool["data"]["name"].lower()
        tools_by_name[name] = tool["data"]
        # Also index by aliases
        for alias in tool["data"].get("aliases", []):
            tools_by_name[alias.lower()] = tool["data"]

    enriched = []
    for rec in recommendations:
        tool_name = rec["tool_name"].lower()
        tool_data = tools_by_name.get(tool_name)

        if tool_data:
            enriched.append({
                **rec,
                "url": tool_data.get("url", ""),
                "category": tool_data["category"]["primary"],
                "pricing_model": tool_data["pricing"]["model"],
                "free_tier": tool_data["pricing"].get("free_tier", False),
                "vendor": tool_data.get("vendor", ""),
                "capabilities": tool_data["capabilities"]["task_verbs"][:6]
            })
        else:
            # Use recommendation as-is if tool not found
            enriched.append({
                **rec,
                "url": "",
                "category": "general",
                "pricing_model": "unknown",
                "free_tier": False,
                "vendor": "",
                "capabilities": []
            })

    return enriched


class RecommendationsPDFGenerator:
    """Generate professional PDF reports for AI tool recommendations."""

    # Category colors
    CATEGORY_COLORS = {
        "productivity": colors.HexColor("#4CAF50"),
        "writing": colors.HexColor("#2196F3"),
        "coding": colors.HexColor("#9C27B0"),
        "research": colors.HexColor("#FF9800"),
        "design": colors.HexColor("#E91E63"),
        "data": colors.HexColor("#00BCD4"),
        "automation": colors.HexColor("#795548"),
        "communication": colors.HexColor("#607D8B"),
        "general": colors.HexColor("#9E9E9E")
    }

    def __init__(self, output_path=None):
        if output_path is None:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = OUTPUT_DIR / f'ai_recommendations_{timestamp}.pdf'

        self.output_path = Path(output_path)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the PDF."""
        # Title style
        self.styles.add(ParagraphStyle(
            name='ReportTitle',
            parent=self.styles['Heading1'],
            fontSize=28,
            spaceAfter=10,
            textColor=colors.HexColor('#1a1a2e'),
            alignment=1  # Center
        ))

        # Subtitle
        self.styles.add(ParagraphStyle(
            name='Subtitle',
            parent=self.styles['Normal'],
            fontSize=12,
            spaceAfter=30,
            textColor=colors.HexColor('#666666'),
            alignment=1
        ))

        # Section headers
        self.styles.add(ParagraphStyle(
            name='SectionTitle',
            parent=self.styles['Heading2'],
            fontSize=18,
            spaceBefore=25,
            spaceAfter=12,
            textColor=colors.HexColor('#16213e'),
            borderPadding=5
        ))

        # Card title
        self.styles.add(ParagraphStyle(
            name='CardTitle',
            parent=self.styles['Heading3'],
            fontSize=14,
            spaceBefore=0,
            spaceAfter=6,
            textColor=colors.HexColor('#1a1a2e')
        ))

        # Card body text
        self.styles.add(ParagraphStyle(
            name='CardBody',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceBefore=2,
            spaceAfter=4,
            textColor=colors.HexColor('#333333'),
            leading=14
        ))

        # Card label
        self.styles.add(ParagraphStyle(
            name='CardLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#666666'),
            spaceBefore=6,
            spaceAfter=2
        ))

        # Highlight text
        self.styles.add(ParagraphStyle(
            name='Highlight',
            parent=self.styles['Normal'],
            fontSize=10,
            textColor=colors.HexColor('#16213e'),
            backColor=colors.HexColor('#e8f4f8'),
            borderPadding=8
        ))

        # Speedup text
        self.styles.add(ParagraphStyle(
            name='SpeedupText',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#2e7d32'),
            spaceBefore=4,
            spaceAfter=4,
            leftIndent=15
        ))

        # Roadmap step
        self.styles.add(ParagraphStyle(
            name='RoadmapStep',
            parent=self.styles['Normal'],
            fontSize=11,
            textColor=colors.HexColor('#333333'),
            spaceBefore=6,
            spaceAfter=6,
            leftIndent=20
        ))

        # URL style
        self.styles.add(ParagraphStyle(
            name='URL',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#1976D2')
        ))

    def _format_duration(self, seconds):
        """Format seconds into human-readable duration."""
        if seconds is None or seconds == 0:
            return "0m"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    def _create_pie_chart(self, data, labels, width=280, height=180):
        """Create a pie chart."""
        if not data or sum(data) == 0:
            return None

        drawing = Drawing(width, height)
        pie = Pie()
        pie.x = width // 2 - 50
        pie.y = height // 2 - 45
        pie.width = 90
        pie.height = 90
        pie.data = data
        pie.labels = labels
        pie.slices.strokeWidth = 0.5

        chart_colors = [
            colors.HexColor('#4CAF50'),
            colors.HexColor('#2196F3'),
            colors.HexColor('#FF9800'),
            colors.HexColor('#E91E63'),
            colors.HexColor('#9C27B0'),
        ]

        for i in range(len(data)):
            pie.slices[i].fillColor = chart_colors[i % len(chart_colors)]
            pie.slices[i].popout = 3 if i == 0 else 0

        drawing.add(pie)
        return drawing

    def _create_recommendation_card(self, rec, index):
        """Create a styled recommendation card."""
        elements = []

        # Card header with priority number and tool name
        category = rec.get("category", "general")
        category_color = self.CATEGORY_COLORS.get(category, self.CATEGORY_COLORS["general"])

        # Priority badge and title
        header_text = f"<b>#{index + 1}</b>  {rec['tool_name']}"
        if rec.get("vendor"):
            header_text += f" <font size='9' color='#666666'>by {rec['vendor']}</font>"

        elements.append(Paragraph(header_text, self.styles['CardTitle']))

        # Category and pricing badges
        pricing_text = rec.get('pricing_model', 'Unknown')
        if rec.get('free_tier'):
            pricing_text += " (Free tier available)"

        badge_text = f"<font color='{category_color.hexval()}'>[{category.upper()}]</font>  |  {pricing_text}"
        elements.append(Paragraph(badge_text, self.styles['CardLabel']))
        elements.append(Spacer(1, 8))

        # Why recommended
        elements.append(Paragraph("<b>Why Recommended:</b>", self.styles['CardLabel']))
        elements.append(Paragraph(rec['reason'], self.styles['CardBody']))

        # Friction point
        elements.append(Paragraph("<b>Friction Point Solved:</b>", self.styles['CardLabel']))
        elements.append(Paragraph(rec['friction_point'], self.styles['CardBody']))

        # Use case
        elements.append(Paragraph("<b>Use Case:</b>", self.styles['CardLabel']))
        elements.append(Paragraph(rec['use_case'], self.styles['CardBody']))

        # Capabilities
        if rec.get('capabilities'):
            caps = ", ".join(rec['capabilities'][:6])
            elements.append(Paragraph(f"<b>Key Capabilities:</b> {caps}", self.styles['CardLabel']))

        # URL
        if rec.get('url'):
            elements.append(Spacer(1, 4))
            elements.append(Paragraph(f"Get started: {rec['url']}", self.styles['URL']))

        # Wrap in a table for card-like appearance
        card_content = [[elements]]
        card_table = Table(card_content, colWidths=[480])
        card_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#fafafa')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#e0e0e0')),
            ('LEFTPADDING', (0, 0), (-1, -1), 15),
            ('RIGHTPADDING', (0, 0), (-1, -1), 15),
            ('TOPPADDING', (0, 0), (-1, -1), 12),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ]))

        return KeepTogether([card_table, Spacer(1, 15)])

    def _build_user_profile_section(self, insights):
        """Build the user profile summary section."""
        elements = []
        elements.append(Paragraph("Your Activity Profile", self.styles['SectionTitle']))

        # Top domains table
        sorted_domains = sorted(insights["top_domains"].items(), key=lambda x: x[1], reverse=True)[:8]
        if sorted_domains:
            domain_data = [['Website', 'Time Spent']]
            for domain, duration in sorted_domains:
                domain_data.append([domain[:40], self._format_duration(duration)])

            domain_table = Table(domain_data, colWidths=[300, 100])
            domain_table.setStyle(TableStyle([
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
            elements.append(domain_table)
            elements.append(Spacer(1, 20))

        # Search intents
        if insights["search_intents"]:
            elements.append(Paragraph("<b>Recent Search Topics:</b>", self.styles['CardLabel']))
            search_text = ", ".join(insights["search_intents"][:10])
            elements.append(Paragraph(search_text, self.styles['CardBody']))
            elements.append(Spacer(1, 15))

        # Top apps with pie chart
        sorted_apps = sorted(insights["active_apps"].items(), key=lambda x: x[1], reverse=True)[:5]
        if sorted_apps:
            elements.append(Paragraph("<b>Top Applications:</b>", self.styles['CardLabel']))

            app_data = [app[1] for app in sorted_apps]
            app_labels = [f"{app[0]}\n{self._format_duration(app[1])}" for app in sorted_apps]

            chart = self._create_pie_chart(app_data, app_labels)
            if chart:
                elements.append(chart)

        return elements

    def _build_speedups_section(self, speedups):
        """Build the workflow speedups section."""
        elements = []
        elements.append(Paragraph("Workflow Speedups", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Based on your activity patterns, here are specific efficiency improvements:",
            self.styles['CardBody']
        ))
        elements.append(Spacer(1, 10))

        for speedup in speedups:
            speedup_text = f"<b>{speedup['description']}</b>"
            if speedup.get('time_saved'):
                speedup_text += f"  <font color='#2e7d32'>({speedup['time_saved']})</font>"
            elements.append(Paragraph(f"+ {speedup_text}", self.styles['SpeedupText']))

        return elements

    def _build_roadmap_section(self, roadmap):
        """Build the quick start roadmap section."""
        elements = []
        elements.append(Paragraph("Quick Start Roadmap", self.styles['SectionTitle']))
        elements.append(Paragraph(
            "Recommended order to adopt these tools for maximum impact:",
            self.styles['CardBody']
        ))
        elements.append(Spacer(1, 10))

        for step in roadmap:
            step_text = f"<b>Step {step['step']}:</b> {step['action']}"
            if step.get('tool'):
                step_text += f" <font color='#1976D2'>({step['tool']})</font>"
            elements.append(Paragraph(step_text, self.styles['RoadmapStep']))

        return elements

    def generate(self, insights, recommendations_data, enriched_recs):
        """Generate the complete PDF report."""
        doc = SimpleDocTemplate(
            str(self.output_path),
            pagesize=letter,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        story = []

        # Cover/Header
        story.append(Spacer(1, 40))
        story.append(Paragraph("Your Personalized", self.styles['Subtitle']))
        story.append(Paragraph("AI Tools Report", self.styles['ReportTitle']))
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            f"Generated {datetime.now().strftime('%B %d, %Y at %I:%M %p')}",
            self.styles['Subtitle']
        ))
        story.append(Spacer(1, 10))
        story.append(HRFlowable(width="80%", thickness=2, color=colors.HexColor('#16213e')))
        story.append(Spacer(1, 30))

        # User profile section
        story.extend(self._build_user_profile_section(insights))
        story.append(PageBreak())

        # Recommendations section
        story.append(Paragraph("Recommended AI Tools", self.styles['SectionTitle']))
        story.append(Paragraph(
            "These tools were selected based on your browsing patterns, search queries, and application usage:",
            self.styles['CardBody']
        ))
        story.append(Spacer(1, 15))

        for i, rec in enumerate(enriched_recs):
            story.append(self._create_recommendation_card(rec, i))

        # Speedups section
        if recommendations_data.get('speedups'):
            story.append(PageBreak())
            story.extend(self._build_speedups_section(recommendations_data['speedups']))

        # Roadmap section
        if recommendations_data.get('roadmap'):
            story.append(Spacer(1, 30))
            story.extend(self._build_roadmap_section(recommendations_data['roadmap']))

        # Footer
        story.append(Spacer(1, 40))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor('#e0e0e0')))
        story.append(Spacer(1, 10))
        story.append(Paragraph(
            "This report was generated by AI Activity Recommender using your local activity data. "
            "All data remains on your device and is never transmitted externally.",
            ParagraphStyle(
                name='Footer',
                parent=self.styles['Normal'],
                fontSize=8,
                textColor=colors.HexColor('#666666'),
                alignment=1
            )
        ))

        # Build PDF
        doc.build(story)
        return str(self.output_path)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Generate AI tool recommendations PDF report'
    )
    parser.add_argument('--output', '-o', type=str,
                       help='Output PDF file path')
    parser.add_argument('--tools-limit', type=int, default=100,
                       help='Number of tools to consider (default: 100)')

    args = parser.parse_args()

    print("=" * 60)
    print("AI TOOL RECOMMENDATIONS PDF GENERATOR")
    print("=" * 60)

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\nError: OPENAI_API_KEY environment variable not set.")
        print("Please set it with: export OPENAI_API_KEY='your-key-here'")
        return 1

    client = OpenAI(api_key=api_key)

    try:
        print("\n[1/5] Loading user behavior data...")
        user_data = load_user_data()
        print(f"  - Browsing history: {len(user_data['browsing_history'])} entries")
        print(f"  - Search queries: {len(user_data['search_queries'])} entries")
        print(f"  - App usage: {len(user_data['application_usage'])} entries")

        print("\n[2/5] Analyzing user behavior patterns...")
        insights = analyze_user_behavior(user_data)
        user_profile = create_user_profile_summary(insights)

        print("\n[3/5] Loading AI tools database...")
        tools = load_ai_tools()
        print(f"  - Loaded {len(tools)} AI tools")
        tools_summary = create_tools_summary(tools, limit=args.tools_limit)

        print("\n[4/5] Generating personalized recommendations with GPT-4o...")
        recommendations_data = get_structured_recommendations(user_profile, tools_summary, client)

        # Enrich recommendations with tool metadata
        enriched_recs = enrich_recommendations(
            recommendations_data.get('recommendations', []),
            tools
        )
        print(f"  - Generated {len(enriched_recs)} recommendations")
        print(f"  - Generated {len(recommendations_data.get('speedups', []))} speedup suggestions")

        print("\n[5/5] Generating PDF report...")
        generator = RecommendationsPDFGenerator(output_path=args.output)
        output_file = generator.generate(insights, recommendations_data, enriched_recs)

        print("\n" + "=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"\nPDF report generated: {output_file}")
        print("\nOpen it with: open " + output_file)

        return 0

    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
