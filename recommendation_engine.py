#!/usr/bin/env python3
"""
AI Tool Recommendation Engine
Uses user behavior data to recommend relevant AI tools via OpenAI API.
"""

import json
import csv
import os
from collections import defaultdict
from datetime import datetime
from openai import OpenAI

# Configuration
EXPORTS_DIR = "exports/raw_export_20260110_214327"
TOOLS_FILE = "ai_tools_cleaned.json"


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


def create_tools_summary(tools, limit=50):
    """Create a summary of available AI tools for the LLM."""
    tools_list = []

    for tool in tools[:limit]:
        data = tool["data"]
        tool_info = {
            "name": data["name"],
            "description": data["description"],
            "category": data["category"]["primary"],
            "capabilities": data["capabilities"]["task_verbs"][:5],
            "use_cases": data["matching"].get("use_cases", [])[:3],
            "pricing": data["pricing"]["model"],
            "free_tier": data["pricing"].get("free_tier", False)
        }
        tools_list.append(tool_info)

    return json.dumps(tools_list, indent=2)


def get_recommendations(user_profile: str, tools_summary: str, client: OpenAI):
    """Use OpenAI to generate personalized recommendations."""

    system_prompt = """You are an AI tool recommendation expert. Based on the user's browsing behavior,
search queries, and application usage patterns, recommend the most relevant AI tools that could
reduce friction in their workflow.

For each recommendation:
1. Explain WHY this tool is relevant based on their specific behavior
2. Identify the friction point it addresses
3. Provide a concrete use case based on their activity

Be specific and reference actual patterns from their data. Limit to 5-7 top recommendations."""

    user_prompt = f"""
{user_profile}

## Available AI Tools:
{tools_summary}

Based on this user's behavior patterns, recommend the most relevant AI tools that would reduce friction in their workflow.
Focus on tools they are NOT already using heavily. Reference specific behaviors from their data to justify each recommendation.
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7,
        max_tokens=2000
    )

    return response.choices[0].message.content


def main():
    print("=" * 60)
    print("AI TOOL RECOMMENDATION ENGINE")
    print("=" * 60)

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("\nError: OPENAI_API_KEY environment variable not set.")
        print("Please set it with: export OPENAI_API_KEY='your-key-here'")
        return

    client = OpenAI(api_key=api_key)

    print("\n[1/4] Loading user behavior data...")
    user_data = load_user_data()
    print(f"  - Browsing history: {len(user_data['browsing_history'])} entries")
    print(f"  - Search queries: {len(user_data['search_queries'])} entries")
    print(f"  - App usage: {len(user_data['application_usage'])} entries")
    print(f"  - Interactions: {len(user_data['user_interactions'])} entries")

    print("\n[2/4] Analyzing user behavior patterns...")
    insights = analyze_user_behavior(user_data)
    user_profile = create_user_profile_summary(insights)
    print(user_profile)

    print("\n[3/4] Loading AI tools database...")
    tools = load_ai_tools()
    print(f"  - Loaded {len(tools)} AI tools")
    tools_summary = create_tools_summary(tools, limit=100)

    print("\n[4/4] Generating personalized recommendations with GPT-4...")
    print("-" * 60)

    recommendations = get_recommendations(user_profile, tools_summary, client)

    print("\n" + "=" * 60)
    print("PERSONALIZED AI TOOL RECOMMENDATIONS")
    print("=" * 60)
    print(recommendations)

    # Save recommendations to file
    output_file = "recommendations_output.md"
    with open(output_file, 'w') as f:
        f.write("# AI Tool Recommendations\n\n")
        f.write(f"Generated: {datetime.now().isoformat()}\n\n")
        f.write("## User Profile Summary\n")
        f.write(user_profile)
        f.write("\n## Recommendations\n\n")
        f.write(recommendations)

    print(f"\n\nRecommendations saved to: {output_file}")


if __name__ == "__main__":
    main()
