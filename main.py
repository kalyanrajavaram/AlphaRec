#!/usr/bin/env python3
"""
AlphaRec - AI Tool Recommendation Engine (v2)

Semantic approach using embeddings for intelligent tool matching.

Usage:
    python main.py                    # Run with default config
    python main.py --config my.yaml   # Run with custom config
    python main.py --no-llm           # Run without LLM (just matching)
"""

import argparse
import logging
import os
import sys
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from data.loader import DataLoader, load_config
from core.embeddings import EmbeddingModel
from core.user_profile import UserProfileBuilder
from core.tool_matcher import ToolMatcher
from core.session_analyzer import SequenceAnalyzer
from core.task_detector import TaskDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class AlphaRec:
    """
    Main orchestrator for the recommendation pipeline.

    Pipeline:
    1. Load data (user behavior + tools)
    2. Build semantic user profile
    3. Analyze sessions for frustration
    4. Match tools semantically
    5. Generate recommendations with LLM (optional)
    """

    def __init__(self, config: dict):
        self.config = config

        # Initialize components
        emb_config = config.get("embeddings", {})
        self.embedding_model = EmbeddingModel(
            model_name=emb_config.get("model_name", "all-MiniLM-L6-v2"),
            cache_dir=emb_config.get("cache_dir", ".embedding_cache"),
            use_cache=emb_config.get("cache_embeddings", True)
        )

        self.data_loader = DataLoader(config)
        self.profile_builder = UserProfileBuilder(self.embedding_model)
        self.tool_matcher = ToolMatcher(self.embedding_model)
        self.sequence_analyzer = SequenceAnalyzer(config)
        self.task_detector = TaskDetector(config)

        # State
        self.user_data = None
        self.tools = None
        self.profile = None
        self.sequence_analysis = None  # Renamed from frustration
        self.task_result = None
        self.matches = None

    def load_data(self):
        """Step 1: Load user data and tools."""
        logger.info("=" * 60)
        logger.info("STEP 1: Loading data")
        logger.info("=" * 60)

        self.user_data = self.data_loader.load_user_data()
        stats = self.data_loader.get_data_stats(self.user_data)

        print("\nData Statistics:")
        print(f"  Browsing entries: {stats['browsing_entries']}")
        print(f"  Search queries: {stats['search_queries']}")
        print(f"  App usage entries: {stats['app_usage_entries']}")
        print(f"  Total browsing time: {stats['total_browsing_minutes']} minutes")
        print(f"  Unique domains: {stats['unique_domains']}")
        print(f"  Unique apps: {stats['unique_apps']}")

        self.tools = self.data_loader.load_tools()
        print(f"\nLoaded {len(self.tools)} AI tools")

    def build_profile(self):
        """Step 2: Build semantic user profile."""
        logger.info("=" * 60)
        logger.info("STEP 2: Building semantic user profile")
        logger.info("=" * 60)

        self.profile = self.profile_builder.build(self.user_data, self.config)

        print(f"\nProfile Summary:")
        print(f"  Total signals: {self.profile.total_signals}")
        print(f"  Signal breakdown: {self.profile.signal_breakdown}")
        print(f"  Clusters found: {len(self.profile.clusters)}")

        if self.profile.primary_interests:
            print(f"\nPrimary Interests:")
            for interest in self.profile.primary_interests[:5]:
                print(f"  - {interest}")

        if self.profile.inferred_needs:
            print(f"\nInferred Needs:")
            for need in self.profile.inferred_needs[:5]:
                print(f"  - {need}")

    def analyze_sequences(self):
        """Step 3: Analyze behavior sequences to find pain points."""
        logger.info("=" * 60)
        logger.info("STEP 3: Analyzing behavior sequences")
        logger.info("=" * 60)

        self.sequence_analysis = self.sequence_analyzer.analyze(self.user_data)

        print(f"\nSequence Analysis:")
        print(f"  Total sequences: {len(self.sequence_analysis.sequences)}")
        print(f"  Resolution rate: {self.sequence_analysis.resolution_rate:.0%}")
        print(f"  Frustration score: {self.sequence_analysis.frustration_score:.0f}/100")
        print(f"  Summary: {self.sequence_analysis.summary}")

        # Show struggling sequences (the gold)
        struggling = [s for s in self.sequence_analysis.sequences if s.sequence_type == "struggling"]
        if struggling:
            print(f"\nStruggling Sequences ({len(struggling)} found):")
            for seq in struggling[:3]:
                print(f"  - {seq.topic}")
                print(f"    Attempts: {seq.search_attempts} searches, {seq.bounce_count} bounces")
                if seq.pain_point:
                    print(f"    Pain point: {seq.pain_point}")

        if self.sequence_analysis.pain_points:
            print(f"\nExtracted Pain Points:")
            for pp in self.sequence_analysis.pain_points[:5]:
                print(f"  - {pp}")

    def detect_tasks(self):
        """Step 3.5: Detect user's current task from behavior patterns."""
        task_config = self.config.get("task_detection", {})
        if not task_config.get("enabled", True):
            logger.info("Task detection disabled, skipping...")
            return

        logger.info("=" * 60)
        logger.info("STEP 3.5: Detecting task type from behavior")
        logger.info("=" * 60)

        self.task_result = self.task_detector.detect(self.user_data)

        print(f"\nTask Detection:")
        print(f"  Dominant task: {self.task_result.dominant_task.upper()}")
        print(f"  Confidence: {self.task_result.confidence:.0%}")

        print(f"\n  Task Distribution:")
        sorted_tasks = sorted(self.task_result.overall_distribution.items(),
                              key=lambda x: x[1], reverse=True)
        for task, prob in sorted_tasks:
            bar = "=" * int(prob * 20)
            print(f"    {task:15} [{bar:20}] {prob:.0%}")

        if self.task_result.detected_patterns:
            print(f"\n  Recurring Patterns ({len(self.task_result.detected_patterns)} found):")
            for pattern in self.task_result.detected_patterns[:3]:
                seq_str = " -> ".join(pattern.sequence)
                print(f"    {seq_str} ({pattern.occurrences}x)")

        if self.task_result.contributing_signals:
            print(f"\n  Contributing Signals:")
            for signal in self.task_result.contributing_signals:
                print(f"    - {signal}")

    def match_tools(self):
        """Step 4: Match tools semantically."""
        logger.info("=" * 60)
        logger.info("STEP 4: Matching tools semantically")
        logger.info("=" * 60)

        # Index tools (one-time)
        self.tool_matcher.index_tools(self.tools, show_progress=True)

        # Get already-used tools to exclude
        exclude = self.tool_matcher.get_already_used_tools(self.user_data)
        if exclude:
            print(f"\nExcluding already-used tools: {exclude}")

        # Match with task context if available
        if self.task_result:
            print(f"\nUsing task context: {self.task_result.dominant_task} ({self.task_result.confidence:.0%})")
            self.matches = self.tool_matcher.match_with_task_context(
                self.profile,
                self.task_result,
                self.config,
                exclude_tools=exclude
            )
        else:
            self.matches = self.tool_matcher.match(
                self.profile,
                self.config.get("matching", {}),
                exclude_tools=exclude
            )

        print(f"\nTop Matches:")
        for i, match in enumerate(self.matches[:10], 1):
            print(f"  {i}. {match.tool.name} (score: {match.overall_score:.3f})")
            if match.matched_needs:
                print(f"     Matches: {', '.join(match.matched_needs[:2])}")

    def generate_llm_recommendations(self):
        """Step 5: Generate detailed recommendations with LLM."""
        logger.info("=" * 60)
        logger.info("STEP 5: Generating LLM recommendations")
        logger.info("=" * 60)

        llm_config = self.config.get("llm", {})
        provider = llm_config.get("provider", "openai")

        if provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not set, skipping LLM recommendations")
                return None

            try:
                from openai import OpenAI
                client = OpenAI(api_key=api_key)
            except ImportError:
                logger.warning("openai package not installed, skipping LLM")
                return None

            # Build context for LLM
            profile_text = self.profile_builder.profile_to_text(self.profile)
            sequence_text = self.sequence_analyzer.analysis_to_text(self.sequence_analysis)
            tools_text = self.tool_matcher.matches_to_text(self.matches, limit=20)

            system_prompt = """You are an AI tool recommendation expert. Based on the user's behavior sequences
and identified pain points, provide highly targeted recommendations.

IMPORTANT: The sequence analysis shows EXACTLY where the user struggled - these are real pain points
extracted from their actual behavior patterns (search → bounce → refine → fail sequences).

For each recommendation:
1. Reference the SPECIFIC struggling sequence it addresses
2. Explain how the tool would have helped in that exact situation
3. Give a concrete example based on their actual searches

Be specific. Don't be generic. Reference their actual pain points."""

            user_prompt = f"""
{profile_text}

{sequence_text}

{tools_text}

Based on the STRUGGLING SEQUENCES above (these are verified pain points where the user
couldn't find what they needed), recommend 5-7 AI tools that would directly address these issues.

For each recommendation, explicitly connect it to one of their struggling sequences.
"""

            print("\nGenerating LLM recommendations...")
            response = client.chat.completions.create(
                model=llm_config.get("model", "gpt-4o"),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=llm_config.get("temperature", 0.7),
                max_tokens=llm_config.get("max_tokens", 2000)
            )

            return response.choices[0].message.content

        else:
            logger.warning(f"Unknown LLM provider: {provider}")
            return None

    def run(self, use_llm: bool = True) -> dict:
        """
        Run the full recommendation pipeline.

        Args:
            use_llm: Whether to use LLM for final recommendations

        Returns:
            Dictionary with all results
        """
        print("\n" + "=" * 60)
        print("ALPHAREC - AI TOOL RECOMMENDATION ENGINE (v2)")
        print("=" * 60)

        # Run pipeline
        self.load_data()
        self.build_profile()
        self.analyze_sequences()
        self.detect_tasks()
        self.match_tools()

        llm_recommendations = None
        if use_llm:
            llm_recommendations = self.generate_llm_recommendations()

        # Compile results
        results = {
            "timestamp": datetime.now().isoformat(),
            "data_stats": self.data_loader.get_data_stats(self.user_data),
            "profile": {
                "total_signals": self.profile.total_signals,
                "signal_breakdown": self.profile.signal_breakdown,
                "primary_interests": self.profile.primary_interests,
                "inferred_needs": self.profile.inferred_needs,
                "cluster_count": len(self.profile.clusters)
            },
            "sequence_analysis": {
                "total_sequences": len(self.sequence_analysis.sequences),
                "resolution_rate": self.sequence_analysis.resolution_rate,
                "frustration_score": self.sequence_analysis.frustration_score,
                "summary": self.sequence_analysis.summary,
                "pain_points": self.sequence_analysis.pain_points,
                "struggling_topics": self.sequence_analysis.struggling_topics
            },
            "task_detection": {
                "dominant_task": self.task_result.dominant_task if self.task_result else None,
                "confidence": self.task_result.confidence if self.task_result else None,
                "task_distribution": self.task_result.overall_distribution if self.task_result else {},
                "detected_patterns": [
                    {
                        "sequence": p.sequence,
                        "occurrences": p.occurrences,
                        "avg_duration": p.avg_duration
                    }
                    for p in (self.task_result.detected_patterns[:10] if self.task_result else [])
                ],
                "time_breakdown": self.task_result.time_breakdown if self.task_result else {}
            } if self.task_result else None,
            "top_matches": [
                {
                    "name": m.tool.name,
                    "score": m.overall_score,
                    "category": m.tool.category,
                    "url": m.tool.url,
                    "matched_needs": m.matched_needs
                }
                for m in self.matches[:20]
            ],
            "llm_recommendations": llm_recommendations
        }

        # Print final recommendations
        if llm_recommendations:
            print("\n" + "=" * 60)
            print("FINAL RECOMMENDATIONS")
            print("=" * 60)
            print(llm_recommendations)

        return results

    def save_results(self, results: dict, output_path: str = "results.json"):
        """Save results to JSON file."""
        import json

        # Remove non-serializable items
        clean_results = {
            k: v for k, v in results.items()
            if k != "profile"  # Profile has numpy arrays
        }

        with open(output_path, 'w') as f:
            json.dump(clean_results, f, indent=2, default=str)

        print(f"\nResults saved to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="AlphaRec - AI Tool Recommendations")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file"
    )
    parser.add_argument(
        "--no-llm",
        action="store_true",
        help="Skip LLM recommendation generation"
    )
    parser.add_argument(
        "--output",
        default="results.json",
        help="Output file for results"
    )
    args = parser.parse_args()

    # Load config
    config = load_config(args.config)

    # Run pipeline
    alpharec = AlphaRec(config)
    results = alpharec.run(use_llm=not args.no_llm)

    # Save results
    alpharec.save_results(results, args.output)


if __name__ == "__main__":
    main()
