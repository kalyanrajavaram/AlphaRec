#!/usr/bin/env python3
"""
Schema Enhancement for AI Tools Database
Adds new fields optimized for semantic matching with user behavior.
"""

import json
from pathlib import Path

# New schema fields to add for better recommendation matching
ENHANCED_SCHEMA = {
    # Maps frustration signals to tools that solve them
    "frustration_triggers": {
        "description": "Behavioral signals that indicate this tool would help",
        "fields": {
            "search_patterns": "Regex patterns in search queries that suggest need for this tool",
            "repeated_search_topics": "Topics where repeated searches indicate this tool would help",
            "error_contexts": "Error types/contexts where this tool provides solutions",
            "bounce_domains": "Domains where quick bounces suggest need for this tool"
        }
    },

    # Maps to task classifications
    "task_fit": {
        "description": "How well tool fits different task types",
        "fields": {
            "coding": "0-10 score for coding tasks",
            "research": "0-10 score for research tasks",
            "writing": "0-10 score for writing tasks",
            "design": "0-10 score for design tasks",
            "communication": "0-10 score for communication tasks",
            "data": "0-10 score for data analysis tasks",
            "productivity": "0-10 score for productivity/organization"
        }
    },

    # Time-based recommendations
    "time_context": {
        "description": "When this tool is most useful",
        "fields": {
            "session_length": "ideal session length: quick (<5min), medium (5-30min), long (30min+)",
            "work_style_fit": "best for: early_bird, night_owl, balanced",
            "frequency": "usage pattern: continuous, periodic, on_demand"
        }
    },

    # Semantic matching signals
    "semantic_signals": {
        "description": "Signals for semantic matching",
        "fields": {
            "problem_statements": "Natural language descriptions of problems this solves",
            "user_quotes": "Things users might say when they need this tool",
            "workflow_gaps": "Workflow inefficiencies this tool addresses",
            "before_after": "What workflow looks like before vs after using this tool"
        }
    }
}


# Frustration trigger mappings for common tools
FRUSTRATION_MAPPINGS = {
    "ChatGPT": {
        "search_patterns": [
            r"how to (write|create|make|build)",
            r"explain .* (code|concept|topic)",
            r"what is .* (meaning|definition)",
            r"help (me )?(with|understand)",
            r"(best|easiest) way to"
        ],
        "repeated_search_topics": [
            "writing help", "code explanation", "how to", "tutorial",
            "example", "template", "draft"
        ],
        "error_contexts": ["writer's block", "stuck on", "don't understand"],
        "bounce_domains": ["stackoverflow.com", "reddit.com", "quora.com"]
    },
    "Claude": {
        "search_patterns": [
            r"(analyze|review|summarize) (document|text|code)",
            r"(long|complex) (document|text|analysis)",
            r"(explain|break down) (complex|technical)"
        ],
        "repeated_search_topics": [
            "document analysis", "code review", "summarize", "explain complex"
        ],
        "error_contexts": ["too long", "too complex", "need to understand"],
        "bounce_domains": ["medium.com", "arxiv.org", "research papers"]
    },
    "Cursor": {
        "search_patterns": [
            r"(ai|code) (assistant|completion|suggestion)",
            r"(faster|better) (coding|programming)",
            r"(vs code|vscode) (ai|extension|plugin)",
            r"(copilot|tabnine) alternative"
        ],
        "repeated_search_topics": [
            "code completion", "ai coding", "faster coding", "code assistant"
        ],
        "error_contexts": ["slow coding", "repetitive code", "boilerplate"],
        "bounce_domains": ["github.com", "stackoverflow.com"]
    },
    "Perplexity": {
        "search_patterns": [
            r"(research|find|search) (information|sources|citations)",
            r"(accurate|reliable|trusted) (information|sources)",
            r"(compare|vs|versus|difference)",
            r"recent (news|updates|developments)"
        ],
        "repeated_search_topics": [
            "research", "find sources", "compare", "latest news", "fact check"
        ],
        "error_contexts": ["can't find", "outdated information", "need sources"],
        "bounce_domains": ["google.com", "wikipedia.org", "news sites"]
    },
    "Notion AI": {
        "search_patterns": [
            r"(organize|manage|track) (notes|tasks|projects)",
            r"(note|knowledge) (taking|management)",
            r"(summarize|outline) (meeting|notes)"
        ],
        "repeated_search_topics": [
            "note organization", "task management", "meeting notes", "knowledge base"
        ],
        "error_contexts": ["disorganized", "can't find notes", "too many notes"],
        "bounce_domains": ["notion.so", "evernote.com", "roamresearch.com"]
    },
    "Midjourney": {
        "search_patterns": [
            r"(create|generate|make) (image|art|illustration)",
            r"(ai|generated) (art|image|picture)",
            r"(visual|graphic) (design|content)"
        ],
        "repeated_search_topics": [
            "ai art", "generate image", "create illustration", "visual content"
        ],
        "error_contexts": ["need image", "can't design", "visual content"],
        "bounce_domains": ["unsplash.com", "shutterstock.com", "canva.com"]
    },
    "GitHub Copilot": {
        "search_patterns": [
            r"(code|function) (completion|suggestion|autocomplete)",
            r"(ai|ml) (pair programmer|coding assistant)",
            r"(write|generate) (code|function|test)"
        ],
        "repeated_search_topics": [
            "code completion", "autocomplete", "generate code", "write tests"
        ],
        "error_contexts": ["slow typing", "boilerplate", "repetitive code"],
        "bounce_domains": ["github.com", "stackoverflow.com"]
    },
    "Grammarly": {
        "search_patterns": [
            r"(grammar|spelling|writing) (check|correction|fix)",
            r"(improve|better) writing",
            r"(professional|clear) (writing|communication)"
        ],
        "repeated_search_topics": [
            "grammar check", "spelling", "improve writing", "proofread"
        ],
        "error_contexts": ["grammar mistake", "unclear writing", "typos"],
        "bounce_domains": ["docs.google.com", "mail.google.com"]
    },
    "Otter.ai": {
        "search_patterns": [
            r"(transcribe|record) (meeting|audio|voice)",
            r"(meeting|audio) (notes|transcription)",
            r"(voice|speech) to text"
        ],
        "repeated_search_topics": [
            "meeting transcription", "voice notes", "audio to text"
        ],
        "error_contexts": ["missed meeting", "can't take notes", "need transcript"],
        "bounce_domains": ["zoom.us", "meet.google.com", "teams.microsoft.com"]
    },
    "Zapier": {
        "search_patterns": [
            r"(automate|connect|integrate) (apps|tools|workflow)",
            r"(no.?code|low.?code) automation",
            r"(sync|transfer) (data|information) between"
        ],
        "repeated_search_topics": [
            "automate workflow", "connect apps", "no code automation"
        ],
        "error_contexts": ["manual work", "repetitive task", "copy paste between apps"],
        "bounce_domains": ["zapier.com", "make.com", "ifttt.com"]
    }
}


# Task fit scores for tools
TASK_FIT_SCORES = {
    "ChatGPT": {"coding": 8, "research": 8, "writing": 9, "design": 3, "communication": 7, "data": 6, "productivity": 7},
    "Claude": {"coding": 9, "research": 9, "writing": 9, "design": 2, "communication": 7, "data": 7, "productivity": 6},
    "Cursor": {"coding": 10, "research": 3, "writing": 2, "design": 1, "communication": 1, "data": 4, "productivity": 5},
    "Perplexity": {"coding": 4, "research": 10, "writing": 5, "design": 2, "communication": 3, "data": 5, "productivity": 4},
    "Notion AI": {"coding": 2, "research": 5, "writing": 7, "design": 2, "communication": 5, "data": 4, "productivity": 9},
    "Midjourney": {"coding": 0, "research": 2, "writing": 2, "design": 10, "communication": 3, "data": 1, "productivity": 2},
    "DALL-E": {"coding": 0, "research": 2, "writing": 2, "design": 9, "communication": 3, "data": 1, "productivity": 2},
    "GitHub Copilot": {"coding": 10, "research": 2, "writing": 1, "design": 0, "communication": 0, "data": 3, "productivity": 4},
    "Grammarly": {"coding": 1, "research": 2, "writing": 10, "design": 0, "communication": 9, "data": 1, "productivity": 5},
    "Otter.ai": {"coding": 0, "research": 4, "writing": 5, "design": 0, "communication": 9, "data": 3, "productivity": 7},
    "Zapier": {"coding": 2, "research": 1, "writing": 1, "design": 1, "communication": 3, "data": 6, "productivity": 10},
    "Jasper": {"coding": 1, "research": 3, "writing": 10, "design": 2, "communication": 6, "data": 1, "productivity": 4},
    "Copy.ai": {"coding": 0, "research": 2, "writing": 9, "design": 1, "communication": 7, "data": 1, "productivity": 3},
    "Tableau": {"coding": 2, "research": 5, "writing": 1, "design": 3, "communication": 4, "data": 10, "productivity": 5},
    "Figma AI": {"coding": 1, "research": 2, "writing": 1, "design": 10, "communication": 3, "data": 1, "productivity": 4},
    "Canva": {"coding": 0, "research": 1, "writing": 3, "design": 9, "communication": 5, "data": 2, "productivity": 5},
    "Gemini": {"coding": 7, "research": 8, "writing": 8, "design": 3, "communication": 6, "data": 6, "productivity": 7},
    "Microsoft Copilot": {"coding": 6, "research": 7, "writing": 8, "design": 3, "communication": 7, "data": 7, "productivity": 8}
}


# Problem statements for semantic matching
PROBLEM_STATEMENTS = {
    "ChatGPT": [
        "I need help writing content but don't know where to start",
        "I want to understand complex topics quickly",
        "I need to brainstorm ideas for my project",
        "I'm stuck on a coding problem and need explanation"
    ],
    "Claude": [
        "I have a long document I need to analyze",
        "I need detailed code review and explanation",
        "I want thoughtful, nuanced responses to complex questions",
        "I need help with technical writing and documentation"
    ],
    "Cursor": [
        "I spend too much time writing boilerplate code",
        "I want AI assistance directly in my code editor",
        "I need to code faster without switching contexts",
        "I want intelligent code completion that understands my project"
    ],
    "Perplexity": [
        "I need accurate, cited information for research",
        "I'm tired of sifting through search results",
        "I want answers with sources I can verify",
        "I need to stay updated on recent developments"
    ],
    "Grammarly": [
        "I make grammar mistakes I don't catch",
        "I want my writing to sound more professional",
        "I need to proofread documents quickly",
        "I want to improve my writing style"
    ],
    "Zapier": [
        "I'm copying data between apps manually",
        "I want to automate repetitive workflows",
        "I need apps to talk to each other automatically",
        "I spend too much time on routine tasks"
    ]
}


def enhance_tool_schema(tool_data: dict) -> dict:
    """Add enhanced schema fields to a tool."""
    tool_name = tool_data.get("data", {}).get("name", "")

    # Add frustration triggers if we have mappings
    if tool_name in FRUSTRATION_MAPPINGS:
        if "matching" not in tool_data["data"]:
            tool_data["data"]["matching"] = {}
        tool_data["data"]["matching"]["frustration_triggers"] = FRUSTRATION_MAPPINGS[tool_name]

    # Add task fit scores
    if tool_name in TASK_FIT_SCORES:
        tool_data["data"]["task_fit"] = TASK_FIT_SCORES[tool_name]

    # Add problem statements
    if tool_name in PROBLEM_STATEMENTS:
        if "matching" not in tool_data["data"]:
            tool_data["data"]["matching"] = {}
        tool_data["data"]["matching"]["problem_statements"] = PROBLEM_STATEMENTS[tool_name]

    return tool_data


def enhance_tools_database(input_file: str, output_file: str = None):
    """
    Enhance the entire tools database with new schema fields.
    """
    if output_file is None:
        output_file = input_file.replace(".json", "_enhanced.json")

    print(f"Loading tools from {input_file}...")
    with open(input_file, 'r') as f:
        data = json.load(f)

    tools = data.get("tools", [])
    enhanced_count = 0

    print(f"Enhancing {len(tools)} tools...")
    for i, tool in enumerate(tools):
        tool_name = tool.get("data", {}).get("name", "")
        original = json.dumps(tool)
        enhanced = enhance_tool_schema(tool)

        if json.dumps(enhanced) != original:
            enhanced_count += 1
            tools[i] = enhanced

    data["tools"] = tools
    data["schema_version"] = "2.0"
    data["enhancements"] = {
        "frustration_triggers": "Behavioral signals that indicate need for tool",
        "task_fit": "0-10 scores for how well tool fits each task type",
        "problem_statements": "Natural language problem descriptions"
    }

    print(f"Writing enhanced database to {output_file}...")
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Done! Enhanced {enhanced_count} tools with new schema fields.")
    return output_file


def print_schema_documentation():
    """Print documentation for the enhanced schema."""
    print("\n" + "=" * 60)
    print("ENHANCED AI TOOLS SCHEMA")
    print("=" * 60)

    for section, info in ENHANCED_SCHEMA.items():
        print(f"\n## {section}")
        print(f"   {info['description']}")
        print("   Fields:")
        for field, desc in info['fields'].items():
            print(f"     - {field}: {desc}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enhance AI tools database schema")
    parser.add_argument("--input", "-i", default="ai_tools_cleaned.json",
                       help="Input JSON file")
    parser.add_argument("--output", "-o", default=None,
                       help="Output JSON file (default: input_enhanced.json)")
    parser.add_argument("--docs", action="store_true",
                       help="Print schema documentation")

    args = parser.parse_args()

    if args.docs:
        print_schema_documentation()
    else:
        enhance_tools_database(args.input, args.output)
