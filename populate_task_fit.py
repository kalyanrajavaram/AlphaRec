#!/usr/bin/env python3
"""
Populate task_fit scores for all tools in the database.
Uses OpenAI GPT-4o-mini to generate scores based on tool metadata.
"""

import json
import os
import time
from pathlib import Path
from openai import OpenAI

# Task types that need scoring
TASK_TYPES = ["coding", "research", "writing", "design", "communication", "data", "productivity"]

# Batch size for API calls (to avoid rate limits)
BATCH_SIZE = 10

def create_scoring_prompt(tools_batch: list) -> str:
    """Create a prompt to score multiple tools at once."""

    tools_info = []
    for i, tool in enumerate(tools_batch):
        data = tool.get("data", {})
        info = {
            "index": i,
            "name": data.get("name", "Unknown"),
            "description": data.get("description", "")[:300],
            "category": data.get("category", {}).get("primary", ""),
            "secondary_categories": data.get("category", {}).get("secondary", [])[:5],
            "capabilities": data.get("capabilities", {}).get("task_verbs", [])[:10],
            "use_cases": data.get("matching", {}).get("use_cases", [])[:5]
        }
        tools_info.append(info)

    prompt = f"""Score the following AI tools for how well they fit each task type.
Score from 0-10 where:
- 0: Not applicable at all
- 1-3: Marginally useful
- 4-6: Moderately useful
- 7-8: Very useful
- 9-10: Excellent fit / primary purpose

Task types to score:
- coding: Software development, debugging, code generation
- research: Information gathering, fact-finding, analysis
- writing: Content creation, copywriting, documentation
- design: Visual design, UI/UX, graphics, video
- communication: Email, messaging, meetings, collaboration
- data: Data analysis, visualization, spreadsheets
- productivity: Task management, organization, automation

Tools to score:
{json.dumps(tools_info, indent=2)}

Return ONLY a JSON array with objects containing "index" and "task_fit" for each tool.
Example format:
[
  {{"index": 0, "task_fit": {{"coding": 8, "research": 5, "writing": 3, "design": 1, "communication": 2, "data": 4, "productivity": 6}}}},
  {{"index": 1, "task_fit": {{"coding": 2, "research": 9, "writing": 7, "design": 1, "communication": 3, "data": 5, "productivity": 4}}}}
]

Be accurate based on the tool's actual purpose. Return ONLY the JSON array, no other text."""

    return prompt


def score_tools_batch(client: OpenAI, tools_batch: list) -> list:
    """Score a batch of tools using GPT-4o-mini."""

    prompt = create_scoring_prompt(tools_batch)

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an AI tool analyst. Return only valid JSON."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=2000
        )

        result_text = response.choices[0].message.content.strip()

        # Clean up response if needed
        if result_text.startswith("```"):
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]

        scores = json.loads(result_text)
        return scores

    except json.JSONDecodeError as e:
        print(f"  JSON parse error: {e}")
        print(f"  Response: {result_text[:500]}")
        return None
    except Exception as e:
        print(f"  API error: {e}")
        return None


def populate_task_fit(input_file: str, output_file: str = None, resume_from: int = 0):
    """
    Populate task_fit scores for all tools.

    Args:
        input_file: Path to ai_tools_cleaned.json
        output_file: Output path (default: overwrites input)
        resume_from: Index to resume from (for interrupted runs)
    """

    if output_file is None:
        output_file = input_file

    # Check for API key
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY environment variable not set")
        print("Run: export OPENAI_API_KEY='your-key-here'")
        return

    client = OpenAI(api_key=api_key)

    # Load tools
    print(f"Loading tools from {input_file}...")
    with open(input_file, 'r') as f:
        data = json.load(f)

    tools = data.get("tools", [])
    total_tools = len(tools)
    print(f"Found {total_tools} tools")

    # Count tools that already have task_fit
    already_scored = sum(1 for t in tools if t.get("data", {}).get("task_fit"))
    print(f"Already scored: {already_scored}")

    # Find tools needing scores
    tools_to_score = []
    for i, tool in enumerate(tools):
        if not tool.get("data", {}).get("task_fit"):
            tools_to_score.append((i, tool))

    if resume_from > 0:
        tools_to_score = [(i, t) for i, t in tools_to_score if i >= resume_from]

    print(f"Tools to score: {len(tools_to_score)}")

    if not tools_to_score:
        print("All tools already have task_fit scores!")
        return

    # Process in batches
    scored_count = 0
    failed_count = 0

    for batch_start in range(0, len(tools_to_score), BATCH_SIZE):
        batch = tools_to_score[batch_start:batch_start + BATCH_SIZE]
        batch_indices = [i for i, _ in batch]
        batch_tools = [t for _, t in batch]

        print(f"\nProcessing batch {batch_start//BATCH_SIZE + 1}/{(len(tools_to_score) + BATCH_SIZE - 1)//BATCH_SIZE}")
        print(f"  Tools: {[t.get('data', {}).get('name', 'Unknown')[:20] for t in batch_tools]}")

        scores = score_tools_batch(client, batch_tools)

        if scores:
            for score_item in scores:
                idx_in_batch = score_item.get("index")
                task_fit = score_item.get("task_fit")

                if idx_in_batch is not None and task_fit:
                    # Get the actual index in the full tools list
                    actual_idx = batch_indices[idx_in_batch]
                    tools[actual_idx]["data"]["task_fit"] = task_fit
                    scored_count += 1

            print(f"  Scored {len(scores)} tools")
        else:
            failed_count += len(batch)
            print(f"  Failed to score batch")

        # Save progress after each batch
        data["tools"] = tools
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)

        # Rate limiting
        time.sleep(1)

    # Final summary
    print(f"\n{'='*50}")
    print(f"COMPLETE!")
    print(f"  Scored: {scored_count}")
    print(f"  Failed: {failed_count}")
    print(f"  Total with task_fit: {sum(1 for t in tools if t.get('data', {}).get('task_fit'))}/{total_tools}")
    print(f"  Output: {output_file}")


def verify_task_fit(input_file: str):
    """Verify task_fit scores in the database."""

    with open(input_file, 'r') as f:
        data = json.load(f)

    tools = data.get("tools", [])

    with_scores = 0
    without_scores = 0
    score_distribution = {task: [] for task in TASK_TYPES}

    for tool in tools:
        task_fit = tool.get("data", {}).get("task_fit")
        if task_fit:
            with_scores += 1
            for task, score in task_fit.items():
                if task in score_distribution:
                    score_distribution[task].append(score)
        else:
            without_scores += 1

    print(f"\n{'='*50}")
    print("TASK_FIT VERIFICATION")
    print(f"{'='*50}")
    print(f"With scores: {with_scores}/{len(tools)} ({100*with_scores/len(tools):.1f}%)")
    print(f"Without scores: {without_scores}")

    if with_scores > 0:
        print(f"\nScore distribution by task type:")
        for task in TASK_TYPES:
            scores = score_distribution[task]
            if scores:
                avg = sum(scores) / len(scores)
                print(f"  {task}: avg={avg:.1f}, min={min(scores)}, max={max(scores)}")


def generate_from_category(input_file: str, output_file: str = None):
    """
    Quick method: Generate task_fit from existing category data.
    No API calls needed, but less accurate.
    """

    if output_file is None:
        output_file = input_file

    # Category to task type mapping
    CATEGORY_MAPPING = {
        "productivity": {"productivity": 9, "writing": 5, "communication": 5, "data": 4, "research": 4, "coding": 3, "design": 2},
        "automation": {"productivity": 9, "data": 6, "coding": 5, "communication": 4, "writing": 3, "research": 3, "design": 2},
        "writing": {"writing": 9, "communication": 6, "research": 5, "productivity": 4, "coding": 2, "data": 2, "design": 2},
        "coding": {"coding": 9, "productivity": 5, "data": 5, "research": 4, "writing": 3, "communication": 2, "design": 1},
        "research": {"research": 9, "writing": 5, "data": 5, "productivity": 4, "coding": 3, "communication": 3, "design": 2},
        "image": {"design": 9, "writing": 3, "communication": 3, "productivity": 3, "research": 2, "coding": 1, "data": 1},
        "video": {"design": 8, "communication": 5, "writing": 4, "productivity": 3, "research": 2, "data": 2, "coding": 1},
        "audio": {"communication": 7, "productivity": 5, "writing": 5, "design": 4, "research": 3, "data": 2, "coding": 1},
        "data": {"data": 9, "research": 6, "productivity": 5, "coding": 5, "writing": 3, "communication": 3, "design": 2},
        "communication": {"communication": 9, "productivity": 6, "writing": 5, "research": 3, "data": 2, "coding": 2, "design": 2},
        "design": {"design": 9, "productivity": 4, "communication": 3, "writing": 3, "research": 2, "data": 2, "coding": 1},
        "education": {"research": 7, "writing": 6, "productivity": 5, "communication": 5, "coding": 4, "data": 4, "design": 3},
        "security": {"coding": 6, "data": 5, "research": 5, "productivity": 4, "communication": 3, "writing": 2, "design": 1},
    }

    DEFAULT_SCORES = {"coding": 3, "research": 3, "writing": 3, "design": 3, "communication": 3, "data": 3, "productivity": 3}

    print(f"Loading tools from {input_file}...")
    with open(input_file, 'r') as f:
        data = json.load(f)

    tools = data.get("tools", [])
    updated = 0

    for tool in tools:
        # Skip if already has task_fit
        if tool.get("data", {}).get("task_fit"):
            continue

        category = tool.get("data", {}).get("category", {})
        primary = category.get("primary", "").lower()
        secondary = [s.lower() for s in category.get("secondary", [])]

        # Start with default or primary category mapping
        if primary in CATEGORY_MAPPING:
            task_fit = CATEGORY_MAPPING[primary].copy()
        else:
            task_fit = DEFAULT_SCORES.copy()

        # Boost based on secondary categories
        for sec in secondary:
            if sec in CATEGORY_MAPPING:
                for task, score in CATEGORY_MAPPING[sec].items():
                    # Boost by 1-2 points, cap at 10
                    boost = min(2, score // 4)
                    task_fit[task] = min(10, task_fit.get(task, 0) + boost)

        tool["data"]["task_fit"] = task_fit
        updated += 1

    # Save
    data["tools"] = tools
    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    print(f"Updated {updated} tools with category-based task_fit scores")
    print(f"Saved to {output_file}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Populate task_fit scores for AI tools")
    parser.add_argument("--input", "-i", default="ai_tools_cleaned.json", help="Input JSON file")
    parser.add_argument("--output", "-o", default=None, help="Output JSON file")
    parser.add_argument("--verify", "-v", action="store_true", help="Verify existing scores")
    parser.add_argument("--quick", "-q", action="store_true", help="Quick mode: generate from categories (no API)")
    parser.add_argument("--resume", "-r", type=int, default=0, help="Resume from tool index")

    args = parser.parse_args()

    if args.verify:
        verify_task_fit(args.input)
    elif args.quick:
        generate_from_category(args.input, args.output)
    else:
        populate_task_fit(args.input, args.output, args.resume)
