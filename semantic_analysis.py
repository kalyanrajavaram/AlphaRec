#!/usr/bin/env python3
"""
Semantic Analysis Module for AI Recommendations
Provides deeper behavioral insights without additional API costs.
"""

import re
from collections import defaultdict
from datetime import datetime
from difflib import SequenceMatcher


# Domain categories for classification
DOMAIN_CATEGORIES = {
    "coding": [
        "github.com", "gitlab.com", "bitbucket.org", "stackoverflow.com",
        "stackexchange.com", "dev.to", "medium.com/tag/programming",
        "replit.com", "codepen.io", "jsfiddle.net", "codesandbox.io",
        "leetcode.com", "hackerrank.com", "codeforces.com", "npmjs.com",
        "pypi.org", "crates.io", "docs.python.org", "developer.mozilla.org",
        "w3schools.com", "geeksforgeeks.org"
    ],
    "research": [
        "scholar.google.com", "arxiv.org", "researchgate.net", "academia.edu",
        "jstor.org", "pubmed.ncbi.nlm.nih.gov", "sciencedirect.com",
        "nature.com", "springer.com", "ieee.org", "acm.org", "ssrn.com",
        "wikipedia.org", "britannica.com"
    ],
    "writing": [
        "docs.google.com", "notion.so", "medium.com", "substack.com",
        "wordpress.com", "ghost.org", "grammarly.com", "hemingwayapp.com",
        "quillbot.com", "jasper.ai", "copy.ai"
    ],
    "design": [
        "figma.com", "canva.com", "dribbble.com", "behance.net",
        "adobe.com", "sketch.com", "invisionapp.com", "framer.com",
        "webflow.com", "unsplash.com", "pexels.com"
    ],
    "communication": [
        "gmail.com", "outlook.com", "mail.google.com", "slack.com",
        "discord.com", "teams.microsoft.com", "zoom.us", "meet.google.com",
        "calendly.com", "linkedin.com"
    ],
    "productivity": [
        "trello.com", "asana.com", "monday.com", "clickup.com",
        "airtable.com", "todoist.com", "evernote.com", "roamresearch.com",
        "obsidian.md", "coda.io"
    ],
    "data": [
        "sheets.google.com", "excel.office.com", "airtable.com",
        "tableau.com", "powerbi.com", "looker.com", "metabase.com",
        "kaggle.com", "colab.research.google.com", "jupyter.org",
        "databricks.com", "snowflake.com"
    ],
    "learning": [
        "coursera.org", "udemy.com", "edx.org", "skillshare.com",
        "pluralsight.com", "linkedin.com/learning", "khanacademy.org",
        "codecademy.com", "freecodecamp.org", "youtube.com"
    ],
    "social": [
        "twitter.com", "x.com", "facebook.com", "instagram.com",
        "reddit.com", "tiktok.com", "pinterest.com"
    ],
    "news": [
        "news.google.com", "bbc.com", "cnn.com", "nytimes.com",
        "theverge.com", "techcrunch.com", "wired.com", "arstechnica.com",
        "hackernews.com", "news.ycombinator.com"
    ],
    "shopping": [
        "amazon.com", "ebay.com", "etsy.com", "walmart.com",
        "target.com", "bestbuy.com"
    ],
    "entertainment": [
        "netflix.com", "youtube.com", "spotify.com", "twitch.tv",
        "hulu.com", "disneyplus.com", "hbomax.com"
    ]
}

# App categories
APP_CATEGORIES = {
    "coding": [
        "Visual Studio Code", "VS Code", "PyCharm", "IntelliJ", "WebStorm",
        "Xcode", "Android Studio", "Sublime Text", "Atom", "Vim", "Neovim",
        "Terminal", "iTerm", "Hyper", "Warp", "DataGrip", "Postman", "Insomnia"
    ],
    "writing": [
        "Microsoft Word", "Google Docs", "Pages", "Notion", "Obsidian",
        "Bear", "Ulysses", "iA Writer", "Scrivener", "Typora"
    ],
    "design": [
        "Figma", "Sketch", "Adobe Photoshop", "Adobe Illustrator",
        "Adobe XD", "Canva", "Affinity Designer", "Affinity Photo"
    ],
    "communication": [
        "Slack", "Discord", "Microsoft Teams", "Zoom", "Google Meet",
        "Skype", "Messages", "Mail", "Outlook", "Spark"
    ],
    "data": [
        "Microsoft Excel", "Google Sheets", "Numbers", "Tableau",
        "Power BI", "R Studio", "SPSS", "Stata"
    ],
    "productivity": [
        "Trello", "Asana", "Todoist", "Things", "OmniFocus",
        "Reminders", "Calendar", "Fantastical", "Cron"
    ],
    "browser": [
        "Google Chrome", "Safari", "Firefox", "Microsoft Edge",
        "Brave Browser", "Arc", "Opera"
    ]
}


def detect_frustration_signals(user_data):
    """
    Detect user frustration from behavioral patterns.
    Returns a dict of frustration signals with scores and evidence.
    """
    frustration = {
        "repeated_searches": [],
        "quick_bounces": [],
        "search_refinements": [],
        "high_tab_switching": False,
        "error_pages_visited": [],
        "frustration_score": 0,  # 0-100
        "pain_points": []
    }

    # 1. Detect repeated similar searches (indicates not finding answers)
    searches = [q["query"].lower().strip() for q in user_data.get("search_queries", [])]
    search_clusters = cluster_similar_strings(searches, threshold=0.6)

    for cluster in search_clusters:
        if len(cluster) >= 2:
            frustration["repeated_searches"].append({
                "queries": cluster,
                "count": len(cluster),
                "topic": cluster[0]
            })
            frustration["pain_points"].append(f"Struggling to find: {cluster[0]}")

    # 2. Detect quick bounces (pages visited < 10 seconds)
    for entry in user_data.get("browsing_history", []):
        duration = entry.get("duration_seconds", 0) or 0
        active_duration = entry.get("active_duration_seconds", 0) or 0

        if 0 < duration < 10 or 0 < active_duration < 5:
            domain = extract_domain(entry.get("url", ""))
            if domain and not is_navigation_page(entry.get("url", "")):
                frustration["quick_bounces"].append({
                    "url": entry["url"],
                    "title": entry.get("title", ""),
                    "duration": duration
                })

    # 3. Detect search refinements (search -> search without clicking)
    search_times = []
    for q in user_data.get("search_queries", []):
        if q.get("search_time"):
            try:
                t = datetime.fromisoformat(q["search_time"].replace("Z", "+00:00"))
                search_times.append((t, q["query"]))
            except:
                pass

    search_times.sort(key=lambda x: x[0])
    for i in range(1, len(search_times)):
        time_diff = (search_times[i][0] - search_times[i-1][0]).total_seconds()
        if time_diff < 30:  # Quick successive searches
            frustration["search_refinements"].append({
                "from": search_times[i-1][1],
                "to": search_times[i][1],
                "seconds_between": time_diff
            })

    # 4. Detect error pages
    error_keywords = ["error", "404", "not found", "failed", "exception",
                      "traceback", "undefined", "null", "crash"]
    for entry in user_data.get("browsing_history", []):
        title = (entry.get("title") or "").lower()
        url = (entry.get("url") or "").lower()
        if any(kw in title or kw in url for kw in error_keywords):
            frustration["error_pages_visited"].append({
                "url": entry["url"],
                "title": entry.get("title", "")
            })
            frustration["pain_points"].append("Encountering errors/bugs")

    # Calculate frustration score
    score = 0
    score += min(len(frustration["repeated_searches"]) * 15, 30)
    score += min(len(frustration["quick_bounces"]) * 2, 20)
    score += min(len(frustration["search_refinements"]) * 5, 25)
    score += min(len(frustration["error_pages_visited"]) * 10, 25)
    frustration["frustration_score"] = min(score, 100)

    # Deduplicate pain points
    frustration["pain_points"] = list(set(frustration["pain_points"]))[:5]

    return frustration


def classify_task_sessions(user_data):
    """
    Classify browsing/app sessions into task categories.
    Returns session breakdown and dominant task type.
    """
    sessions = {
        "coding": {"duration": 0, "activities": []},
        "research": {"duration": 0, "activities": []},
        "writing": {"duration": 0, "activities": []},
        "design": {"duration": 0, "activities": []},
        "communication": {"duration": 0, "activities": []},
        "data": {"duration": 0, "activities": []},
        "productivity": {"duration": 0, "activities": []},
        "learning": {"duration": 0, "activities": []},
        "other": {"duration": 0, "activities": []}
    }

    # Classify browsing by domain
    for entry in user_data.get("browsing_history", []):
        url = entry.get("url", "")
        duration = entry.get("active_duration_seconds") or entry.get("duration_seconds") or 0
        domain = extract_domain(url)

        category = categorize_domain(domain)
        if category in sessions:
            sessions[category]["duration"] += duration
            if domain not in [a["domain"] for a in sessions[category]["activities"]]:
                sessions[category]["activities"].append({
                    "domain": domain,
                    "duration": duration
                })

    # Classify app usage
    for app in user_data.get("application_usage", []):
        app_name = app.get("app_name", "")
        duration = app.get("duration_seconds", 0) or 0

        category = categorize_app(app_name)
        if category in sessions:
            sessions[category]["duration"] += duration

    # Calculate percentages and find dominant
    total_time = sum(s["duration"] for s in sessions.values())
    dominant_task = "other"
    max_duration = 0

    task_breakdown = {}
    for task, data in sessions.items():
        if total_time > 0:
            percentage = (data["duration"] / total_time) * 100
            task_breakdown[task] = {
                "duration_seconds": data["duration"],
                "percentage": round(percentage, 1),
                "top_activities": sorted(data["activities"],
                                        key=lambda x: x["duration"],
                                        reverse=True)[:3]
            }
            if data["duration"] > max_duration and task != "other":
                max_duration = data["duration"]
                dominant_task = task

    return {
        "breakdown": task_breakdown,
        "dominant_task": dominant_task,
        "total_tracked_seconds": total_time
    }


def analyze_time_patterns(user_data):
    """
    Analyze productivity patterns by time of day.
    Returns insights about when user is most active/productive.
    """
    hourly_activity = defaultdict(lambda: {"duration": 0, "searches": 0, "intensity": []})

    # Analyze browsing by hour
    for entry in user_data.get("browsing_history", []):
        visit_time = entry.get("visit_time", "")
        duration = entry.get("active_duration_seconds") or entry.get("duration_seconds") or 0

        if visit_time:
            try:
                dt = datetime.fromisoformat(visit_time.replace("Z", "+00:00"))
                hour = dt.hour
                hourly_activity[hour]["duration"] += duration
            except:
                pass

    # Analyze searches by hour
    for query in user_data.get("search_queries", []):
        search_time = query.get("search_time", "")
        if search_time:
            try:
                dt = datetime.fromisoformat(search_time.replace("Z", "+00:00"))
                hour = dt.hour
                hourly_activity[hour]["searches"] += 1
            except:
                pass

    # Classify time periods
    periods = {
        "early_morning": {"hours": range(5, 9), "duration": 0, "label": "Early Morning (5-9am)"},
        "morning": {"hours": range(9, 12), "duration": 0, "label": "Morning (9am-12pm)"},
        "afternoon": {"hours": range(12, 17), "duration": 0, "label": "Afternoon (12-5pm)"},
        "evening": {"hours": range(17, 21), "duration": 0, "label": "Evening (5-9pm)"},
        "night": {"hours": list(range(21, 24)) + list(range(0, 5)), "duration": 0, "label": "Night (9pm-5am)"}
    }

    for hour, data in hourly_activity.items():
        for period_name, period_data in periods.items():
            if hour in period_data["hours"]:
                period_data["duration"] += data["duration"]
                break

    # Find peak productivity period
    peak_period = max(periods.items(), key=lambda x: x[1]["duration"])

    # Calculate work pattern
    total = sum(p["duration"] for p in periods.values())
    pattern_breakdown = {}
    for name, data in periods.items():
        if total > 0:
            pattern_breakdown[name] = {
                "label": data["label"],
                "percentage": round((data["duration"] / total) * 100, 1),
                "duration_minutes": round(data["duration"] / 60, 1)
            }

    return {
        "peak_period": peak_period[1]["label"],
        "pattern_breakdown": pattern_breakdown,
        "hourly_data": dict(hourly_activity),
        "work_style": infer_work_style(periods)
    }


def infer_work_style(periods):
    """Infer work style from time patterns."""
    morning = periods["early_morning"]["duration"] + periods["morning"]["duration"]
    afternoon = periods["afternoon"]["duration"]
    evening = periods["evening"]["duration"] + periods["night"]["duration"]

    total = morning + afternoon + evening
    if total == 0:
        return "unknown"

    morning_pct = morning / total
    evening_pct = evening / total

    if morning_pct > 0.5:
        return "early_bird"
    elif evening_pct > 0.5:
        return "night_owl"
    else:
        return "balanced"


def extract_search_themes(user_data, max_themes=5):
    """
    Group search queries into themes/topics.
    Returns clustered themes instead of raw queries.
    """
    searches = [q["query"] for q in user_data.get("search_queries", []) if q.get("query")]

    if not searches:
        return {"themes": [], "raw_count": 0}

    # Keyword extraction and clustering
    theme_keywords = {
        "coding_help": ["code", "error", "bug", "fix", "how to", "tutorial", "example",
                       "syntax", "function", "api", "library", "package", "install",
                       "python", "javascript", "react", "node", "css", "html", "sql"],
        "research": ["what is", "why", "how does", "explain", "meaning", "definition",
                    "research", "study", "paper", "article", "review"],
        "tool_search": ["best", "top", "vs", "alternative", "comparison", "free",
                       "tool", "app", "software", "platform", "service"],
        "troubleshooting": ["not working", "failed", "error", "issue", "problem",
                           "crash", "slow", "fix", "solve", "debug"],
        "learning": ["learn", "course", "tutorial", "guide", "beginner", "advanced",
                    "certification", "training", "bootcamp"],
        "productivity": ["automate", "faster", "efficient", "workflow", "template",
                        "shortcut", "tip", "hack", "productivity"]
    }

    themes = defaultdict(list)
    uncategorized = []

    for query in searches:
        query_lower = query.lower()
        matched = False

        for theme, keywords in theme_keywords.items():
            if any(kw in query_lower for kw in keywords):
                themes[theme].append(query)
                matched = True
                break

        if not matched:
            uncategorized.append(query)

    # Build theme summaries
    theme_summaries = []
    for theme, queries in sorted(themes.items(), key=lambda x: len(x[1]), reverse=True):
        if queries:
            theme_summaries.append({
                "theme": theme.replace("_", " ").title(),
                "count": len(queries),
                "sample_queries": queries[:3],
                "indicates": get_theme_indication(theme)
            })

    if uncategorized:
        theme_summaries.append({
            "theme": "Other",
            "count": len(uncategorized),
            "sample_queries": uncategorized[:3],
            "indicates": "General browsing and exploration"
        })

    return {
        "themes": theme_summaries[:max_themes],
        "raw_count": len(searches),
        "primary_intent": theme_summaries[0]["theme"] if theme_summaries else "Unknown"
    }


def get_theme_indication(theme):
    """Get what a search theme indicates about user needs."""
    indications = {
        "coding_help": "User needs coding assistance and debugging help",
        "research": "User is researching topics and gathering information",
        "tool_search": "User is actively looking for new tools/solutions",
        "troubleshooting": "User is facing technical issues that need solving",
        "learning": "User wants to learn new skills",
        "productivity": "User wants to improve efficiency and workflows"
    }
    return indications.get(theme, "General information seeking")


# Helper functions

def extract_domain(url):
    """Extract domain from URL."""
    if not url or "://" not in url:
        return ""
    try:
        domain = url.split("://")[1].split("/")[0]
        # Remove www prefix
        if domain.startswith("www."):
            domain = domain[4:]
        return domain
    except:
        return ""


def categorize_domain(domain):
    """Categorize a domain into task type."""
    domain_lower = domain.lower()
    for category, domains in DOMAIN_CATEGORIES.items():
        for d in domains:
            if d in domain_lower or domain_lower in d:
                return category
    return "other"


def categorize_app(app_name):
    """Categorize an application into task type."""
    app_lower = app_name.lower()
    for category, apps in APP_CATEGORIES.items():
        for app in apps:
            if app.lower() in app_lower or app_lower in app.lower():
                return category
    return "other"


def is_navigation_page(url):
    """Check if URL is a navigation/landing page (not content)."""
    nav_patterns = [
        r"^https?://[^/]+/?$",  # Homepage
        r"/login", r"/signin", r"/signup", r"/register",
        r"/search\?", r"/results\?",
        r"google\.com/search",
        r"bing\.com/search"
    ]
    return any(re.search(p, url, re.I) for p in nav_patterns)


def cluster_similar_strings(strings, threshold=0.6):
    """Cluster similar strings together."""
    if not strings:
        return []

    clusters = []
    used = set()

    for i, s1 in enumerate(strings):
        if i in used:
            continue

        cluster = [s1]
        used.add(i)

        for j, s2 in enumerate(strings[i+1:], i+1):
            if j in used:
                continue

            similarity = SequenceMatcher(None, s1, s2).ratio()
            if similarity >= threshold:
                cluster.append(s2)
                used.add(j)

        if len(cluster) >= 1:
            clusters.append(cluster)

    return [c for c in clusters if len(c) >= 2]


def generate_semantic_profile(user_data):
    """
    Generate a complete semantic profile combining all analyses.
    This is the main entry point for semantic analysis.
    """
    frustration = detect_frustration_signals(user_data)
    tasks = classify_task_sessions(user_data)
    time_patterns = analyze_time_patterns(user_data)
    search_themes = extract_search_themes(user_data)

    return {
        "frustration_analysis": frustration,
        "task_classification": tasks,
        "time_patterns": time_patterns,
        "search_themes": search_themes,
        "summary": {
            "frustration_score": frustration["frustration_score"],
            "dominant_task": tasks["dominant_task"],
            "work_style": time_patterns["work_style"],
            "primary_search_intent": search_themes["primary_intent"],
            "key_pain_points": frustration["pain_points"]
        }
    }
