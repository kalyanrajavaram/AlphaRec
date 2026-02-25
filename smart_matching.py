#!/usr/bin/env python3
"""
Smart Matching Module
Matches tools to users based on semantic analysis signals.
Uses local scoring before sending to LLM to improve recommendations.
"""

import re
from collections import defaultdict
from typing import List, Dict, Any


def calculate_tool_relevance_scores(
    tools: List[Dict],
    semantic_profile: Dict,
    max_tools: int = 50
) -> List[Dict]:
    """
    Pre-score tools based on semantic profile to send most relevant to LLM.
    This reduces token usage while improving recommendation quality.

    Returns tools sorted by relevance score.
    """
    scored_tools = []

    # Extract key signals from semantic profile
    frustration = semantic_profile.get("frustration_analysis", {})
    tasks = semantic_profile.get("task_classification", {})
    search_themes = semantic_profile.get("search_themes", {})
    summary = semantic_profile.get("summary", {})

    # Get dominant task and pain points
    dominant_task = summary.get("dominant_task", "other")
    pain_points = frustration.get("pain_points", [])
    repeated_searches = frustration.get("repeated_searches", [])
    search_queries = [r["topic"] for r in repeated_searches]

    # Get task breakdown
    task_breakdown = tasks.get("breakdown", {})

    for tool in tools:
        data = tool.get("data", {})
        score = 0
        reasons = []

        # 1. Task fit scoring (0-30 points)
        task_fit = data.get("task_fit", {})
        if task_fit:
            # Score based on dominant task
            task_score = task_fit.get(dominant_task, 0)
            score += task_score * 2  # Up to 20 points

            # Bonus for secondary tasks
            for task, breakdown in task_breakdown.items():
                if breakdown.get("percentage", 0) > 10:
                    score += task_fit.get(task, 0) * 0.5
        else:
            # Fallback: match category to dominant task
            category = data.get("category", {}).get("primary", "")
            if category == dominant_task:
                score += 15
                reasons.append(f"matches {dominant_task} work")

        # 2. Pain point matching (0-25 points)
        matching = data.get("matching", {})
        pain_point_keywords = matching.get("pain_points", [])
        for pain in pain_points:
            pain_lower = pain.lower()
            for kw in pain_point_keywords:
                if kw.replace("_", " ") in pain_lower or pain_lower in kw.replace("_", " "):
                    score += 8
                    reasons.append(f"solves: {pain}")
                    break

        # 3. Search pattern matching (0-25 points)
        search_keywords = matching.get("search_keywords", [])
        frustration_triggers = matching.get("frustration_triggers", {})
        trigger_patterns = frustration_triggers.get("search_patterns", [])

        for query in search_queries:
            query_lower = query.lower()
            # Check keyword matches
            for kw in search_keywords:
                if kw.lower() in query_lower or query_lower in kw.lower():
                    score += 5
                    reasons.append(f"matches search: {query}")
                    break
            # Check pattern matches
            for pattern in trigger_patterns:
                try:
                    if re.search(pattern, query_lower, re.I):
                        score += 7
                        reasons.append(f"pattern match: {query}")
                        break
                except:
                    pass

        # 4. Use case matching (0-15 points)
        use_cases = matching.get("use_cases", [])
        themes = search_themes.get("themes", [])
        for theme in themes:
            theme_name = theme.get("theme", "").lower().replace(" ", "_")
            if any(theme_name in uc.lower() or uc.lower() in theme_name for uc in use_cases):
                score += 5
                reasons.append(f"fits theme: {theme['theme']}")

        # 5. Frustration score bonus (0-10 points)
        frustration_score = summary.get("frustration_score", 0)
        if frustration_score > 50:
            # High frustration = prioritize tools that solve problems
            friction = data.get("friction_reduction", {})
            scores = friction.get("scores", {})
            if scores.get("repetitive_task", 0) > 7:
                score += 5
            if scores.get("cognitive_load", 0) > 7:
                score += 5

        # 6. Capability verb matching (0-10 points)
        capabilities = data.get("capabilities", {})
        task_verbs = capabilities.get("task_verbs", [])
        theme_verbs = {
            "coding_help": ["code", "debug", "generate", "explain", "review"],
            "research": ["research", "search", "analyze", "summarize", "compare"],
            "tool_search": ["automate", "integrate", "connect"],
            "troubleshooting": ["fix", "debug", "solve", "diagnose"],
            "learning": ["learn", "explain", "teach", "tutorial"],
            "productivity": ["automate", "organize", "plan", "track"]
        }

        for theme in themes:
            theme_key = theme.get("theme", "").lower().replace(" ", "_")
            expected_verbs = theme_verbs.get(theme_key, [])
            matches = sum(1 for v in expected_verbs if v in [tv.lower() for tv in task_verbs])
            score += matches * 2

        scored_tools.append({
            "tool": tool,
            "score": score,
            "reasons": reasons[:3],  # Top 3 reasons
            "name": data.get("name", "Unknown")
        })

    # Sort by score and return top tools
    scored_tools.sort(key=lambda x: x["score"], reverse=True)

    return scored_tools[:max_tools]


def create_smart_tools_summary(
    scored_tools: List[Dict],
    include_scores: bool = False
) -> str:
    """
    Create a tools summary that includes relevance signals.
    This helps the LLM make better recommendations.
    """
    import json

    tools_list = []
    for item in scored_tools:
        tool = item["tool"]
        data = tool.get("data", {})

        tool_info = {
            "name": data.get("name"),
            "description": data.get("description", "")[:200],
            "category": data.get("category", {}).get("primary"),
            "capabilities": data.get("capabilities", {}).get("task_verbs", [])[:5],
            "use_cases": data.get("matching", {}).get("use_cases", [])[:3],
            "pricing": data.get("pricing", {}).get("model"),
            "free_tier": data.get("pricing", {}).get("free_tier", False),
            "pain_points_solved": data.get("matching", {}).get("pain_points", [])[:3]
        }

        # Add task fit if available
        task_fit = data.get("task_fit")
        if task_fit:
            tool_info["task_fit"] = task_fit

        # Add problem statements if available
        problem_statements = data.get("matching", {}).get("problem_statements")
        if problem_statements:
            tool_info["solves_problems"] = problem_statements[:2]

        if include_scores:
            tool_info["relevance_score"] = item["score"]
            tool_info["match_reasons"] = item["reasons"]

        tools_list.append(tool_info)

    return json.dumps(tools_list, indent=2)


def filter_already_used_tools(
    tools: List[Dict],
    semantic_profile: Dict,
    user_data: Dict
) -> List[Dict]:
    """
    Filter out tools the user is already heavily using.
    We want to recommend NEW tools, not what they already have.
    """
    # Detect AI tools from browsing
    ai_domains = {
        "chatgpt.com": "ChatGPT",
        "chat.openai.com": "ChatGPT",
        "claude.ai": "Claude",
        "gemini.google.com": "Gemini",
        "perplexity.ai": "Perplexity",
        "github.dev": "GitHub Copilot",
        "copilot.github.com": "GitHub Copilot",
        "notion.so": "Notion AI",
        "grammarly.com": "Grammarly",
        "jasper.ai": "Jasper",
        "midjourney.com": "Midjourney",
        "canva.com": "Canva"
    }

    # Find tools user is already using
    used_tools = set()
    for entry in user_data.get("browsing_history", []):
        url = entry.get("url", "").lower()
        duration = entry.get("active_duration_seconds") or entry.get("duration_seconds") or 0

        # Only count as "used" if spent significant time
        if duration > 300:  # More than 5 minutes
            for domain, tool_name in ai_domains.items():
                if domain in url:
                    used_tools.add(tool_name.lower())

    # Filter tools
    filtered = []
    for tool in tools:
        name = tool.get("data", {}).get("name", "").lower()
        if name not in used_tools:
            filtered.append(tool)
        else:
            # Keep the tool but mark it
            tool["data"]["user_already_uses"] = True
            filtered.append(tool)

    return filtered


def get_contextual_prompt_additions(semantic_profile: Dict) -> str:
    """
    Generate additional prompt context based on semantic analysis.
    This helps the LLM understand what to prioritize.
    """
    summary = semantic_profile.get("summary", {})
    frustration = semantic_profile.get("frustration_analysis", {})

    additions = []

    # Frustration level guidance
    frustration_score = summary.get("frustration_score", 0)
    if frustration_score > 70:
        additions.append(
            "IMPORTANT: User shows HIGH frustration signals. "
            "Prioritize tools that immediately solve their pain points. "
            "Focus on ease of use and quick wins."
        )
    elif frustration_score > 40:
        additions.append(
            "User shows moderate frustration. "
            "Balance between solving immediate problems and workflow improvements."
        )

    # Work style guidance
    work_style = summary.get("work_style")
    if work_style == "night_owl":
        additions.append(
            "User works late hours. Consider tools that help with focus and "
            "async collaboration."
        )
    elif work_style == "early_bird":
        additions.append(
            "User is most productive in mornings. Consider tools that help "
            "with planning and organization."
        )

    # Task type guidance
    dominant = summary.get("dominant_task")
    if dominant == "coding":
        additions.append(
            "User primarily does coding work. Prioritize developer tools, "
            "code assistants, and technical documentation helpers."
        )
    elif dominant == "research":
        additions.append(
            "User does significant research. Prioritize tools for "
            "information gathering, citation, and knowledge management."
        )
    elif dominant == "writing":
        additions.append(
            "User does significant writing. Prioritize content creation, "
            "editing, and grammar tools."
        )

    # Pain point guidance
    pain_points = frustration.get("pain_points", [])
    if pain_points:
        additions.append(
            f"Detected pain points to address: {', '.join(pain_points[:3])}"
        )

    return "\n".join(additions)
