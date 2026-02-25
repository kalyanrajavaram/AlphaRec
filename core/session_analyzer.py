"""
Session Analyzer Module - Sequence-based pattern detection.

The key insight: individual events are ambiguous, but SEQUENCES reveal intent.

Examples:
  STRUGGLING: search → click → 5s → back → refined search → click → 8s → back → another search
  SUCCESSFUL: search → click → 3 minutes → (topic dropped)
  EXPLORING:  search → click → 30s → different search (unrelated topic)

This module:
1. Groups actions into sequences around topics/intents
2. Classifies sequences as resolved vs unresolved
3. Extracts pain points from unresolved sequences
"""

import logging
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class Action:
    """A single user action with context."""
    timestamp: datetime
    action_type: str  # "search", "page_visit", "app_switch"
    content: str      # Query, URL, or app name
    title: str = ""   # Page title if available
    duration: int = 0 # Seconds spent (for page visits)

    def __repr__(self):
        if self.action_type == "search":
            return f"Search({self.content[:30]})"
        elif self.action_type == "page_visit":
            return f"Visit({self.title[:30] or self.content[:30]}, {self.duration}s)"
        return f"Action({self.action_type})"


@dataclass
class Sequence:
    """A sequence of related actions around a topic/intent."""
    actions: List[Action]
    topic: str                    # Inferred topic
    started_at: datetime = None
    ended_at: datetime = None

    # Outcome
    resolved: bool = False        # Did user find what they needed?
    resolution_signal: str = ""   # What indicated resolution

    # Classification
    sequence_type: str = "unknown"  # "struggling", "successful", "exploring", "quick_answer"
    confidence: float = 0.0

    # Extracted insights
    pain_point: str = ""          # If struggling, what's the pain point
    search_attempts: int = 0      # Number of search refinements
    bounce_count: int = 0         # Quick bounces in sequence
    total_duration: int = 0       # Total time spent

    def __repr__(self):
        return f"Sequence({self.topic[:30]}, {self.sequence_type}, {len(self.actions)} actions)"


@dataclass
class SequenceAnalysis:
    """Complete analysis of user sequences."""
    sequences: List[Sequence]

    # Aggregated insights
    unresolved_sequences: List[Sequence] = field(default_factory=list)
    pain_points: List[str] = field(default_factory=list)
    struggling_topics: List[str] = field(default_factory=list)
    successful_topics: List[str] = field(default_factory=list)

    # Overall metrics
    resolution_rate: float = 0.0  # % of sequences that resolved
    avg_attempts_before_resolution: float = 0.0
    frustration_score: float = 0.0

    summary: str = ""


class SequenceAnalyzer:
    """
    Analyzes user behavior through sequences, not individual events.

    The algorithm:
    1. Extract all actions chronologically
    2. Group actions into sequences by topic similarity
    3. Classify each sequence (struggling, successful, exploring)
    4. Extract pain points from unresolved/struggling sequences
    """

    def __init__(self, config: Dict[str, Any]):
        seq_config = config.get("sequences", {})

        # Timing thresholds
        self.sequence_gap = seq_config.get("sequence_gap_seconds", 300)  # 5 min = new sequence
        self.quick_bounce = seq_config.get("quick_bounce_seconds", 15)
        self.engaged_threshold = seq_config.get("engaged_threshold_seconds", 60)
        self.deep_engagement = seq_config.get("deep_engagement_seconds", 180)

        # Similarity thresholds
        self.topic_similarity = seq_config.get("topic_similarity_threshold", 0.4)

        # Resolution signals
        self.resolution_gap = seq_config.get("resolution_gap_seconds", 600)  # 10 min no activity on topic = resolved

    def _parse_timestamp(self, ts: str) -> Optional[datetime]:
        """Parse timestamp string to datetime."""
        if not ts:
            return None

        formats = [
            "%Y-%m-%dT%H:%M:%S.%fZ",
            "%Y-%m-%dT%H:%M:%SZ",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
        ]

        # Clean up timezone
        ts_clean = ts.replace("+00:00", "").replace("Z", "")

        for fmt in formats:
            fmt_clean = fmt.replace("Z", "")
            try:
                return datetime.strptime(ts_clean, fmt_clean)
            except ValueError:
                continue
        return None

    def _extract_actions(self, user_data: Dict[str, Any]) -> List[Action]:
        """Extract all actions from user data, sorted chronologically."""
        actions = []

        # Extract searches
        for entry in user_data.get("search_queries", []):
            ts = self._parse_timestamp(entry.get("search_time", ""))
            if ts and entry.get("query"):
                actions.append(Action(
                    timestamp=ts,
                    action_type="search",
                    content=entry["query"],
                    title=entry["query"]
                ))

        # Extract page visits
        for entry in user_data.get("browsing_history", []):
            ts = self._parse_timestamp(entry.get("visit_time", ""))
            if ts:
                duration = entry.get("active_duration_seconds") or entry.get("duration_seconds") or 0
                actions.append(Action(
                    timestamp=ts,
                    action_type="page_visit",
                    content=entry.get("url", ""),
                    title=entry.get("title", ""),
                    duration=duration
                ))

        # Sort by timestamp
        actions.sort(key=lambda a: a.timestamp)
        return actions

    def _text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two text strings."""
        if not text1 or not text2:
            return 0.0

        t1 = text1.lower().strip()
        t2 = text2.lower().strip()

        # Quick exact match check
        if t1 == t2:
            return 1.0

        # Use SequenceMatcher for fuzzy matching
        return SequenceMatcher(None, t1, t2).ratio()

    def _extract_topic_words(self, text: str) -> set:
        """Extract meaningful words from text for topic matching."""
        # Remove common words and extract topic-relevant terms
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'how', 'to', 'what', 'why', 'when', 'where', 'which', 'who',
            'in', 'on', 'at', 'for', 'with', 'from', 'by', 'about',
            'and', 'or', 'but', 'not', 'this', 'that', 'these', 'those',
            'i', 'you', 'we', 'they', 'it', 'my', 'your', 'our',
            'do', 'does', 'did', 'can', 'could', 'will', 'would', 'should'
        }

        words = re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())
        return set(w for w in words if w not in stop_words)

    def _topics_related(self, action1: Action, action2: Action) -> bool:
        """Determine if two actions are about the same topic."""
        text1 = f"{action1.content} {action1.title}"
        text2 = f"{action2.content} {action2.title}"

        # Check text similarity
        if self._text_similarity(text1, text2) > self.topic_similarity:
            return True

        # Check word overlap
        words1 = self._extract_topic_words(text1)
        words2 = self._extract_topic_words(text2)

        if not words1 or not words2:
            return False

        overlap = len(words1 & words2)
        min_words = min(len(words1), len(words2))

        if min_words > 0 and overlap / min_words > 0.3:
            return True

        return False

    def _is_search_results_page(self, action: Action) -> bool:
        """Check if action is visiting a search results page."""
        url = action.content.lower()
        title = action.title.lower()

        search_indicators = [
            'google.com/search', 'bing.com/search', 'duckduckgo.com/',
            'search?q=', 'search?query=', '/search?',
            'search results', 'results for'
        ]

        return any(ind in url or ind in title for ind in search_indicators)

    def _group_into_sequences(self, actions: List[Action]) -> List[Sequence]:
        """Group actions into sequences by topic and time proximity."""
        if not actions:
            return []

        sequences = []
        current_sequence = [actions[0]]
        current_topic_words = self._extract_topic_words(
            f"{actions[0].content} {actions[0].title}"
        )

        for i in range(1, len(actions)):
            prev = actions[i - 1]
            curr = actions[i]

            time_gap = (curr.timestamp - prev.timestamp).total_seconds()

            # Check if this continues the current sequence
            is_related = self._topics_related(
                current_sequence[-1] if current_sequence else prev,
                curr
            )

            # Also check against the first action in sequence (the original search)
            if not is_related and len(current_sequence) > 0:
                is_related = self._topics_related(current_sequence[0], curr)

            if time_gap < self.sequence_gap and is_related:
                # Continue sequence
                current_sequence.append(curr)
                current_topic_words.update(
                    self._extract_topic_words(f"{curr.content} {curr.title}")
                )
            else:
                # End current sequence, start new one
                if len(current_sequence) >= 1:
                    sequences.append(self._build_sequence(current_sequence))

                current_sequence = [curr]
                current_topic_words = self._extract_topic_words(
                    f"{curr.content} {curr.title}"
                )

        # Don't forget last sequence
        if current_sequence:
            sequences.append(self._build_sequence(current_sequence))

        return sequences

    def _build_sequence(self, actions: List[Action]) -> Sequence:
        """Build a Sequence object from a list of actions."""
        # Find the primary topic (usually the first search)
        topic = ""
        for action in actions:
            if action.action_type == "search":
                topic = action.content
                break

        if not topic:
            # Use first page title
            for action in actions:
                if action.title:
                    topic = action.title
                    break

        if not topic:
            topic = actions[0].content[:50] if actions else "Unknown"

        # Count metrics
        searches = [a for a in actions if a.action_type == "search"]
        visits = [a for a in actions if a.action_type == "page_visit"]
        bounces = [v for v in visits if 0 < v.duration < self.quick_bounce]

        total_duration = sum(a.duration for a in actions)

        return Sequence(
            actions=actions,
            topic=topic,
            started_at=actions[0].timestamp if actions else None,
            ended_at=actions[-1].timestamp if actions else None,
            search_attempts=len(searches),
            bounce_count=len(bounces),
            total_duration=total_duration
        )

    def _classify_sequence(self, sequence: Sequence, all_sequences: List[Sequence], idx: int) -> None:
        """Classify a sequence as struggling, successful, exploring, or quick_answer."""
        actions = sequence.actions

        if len(actions) < 2:
            sequence.sequence_type = "single_action"
            sequence.confidence = 0.5
            return

        searches = [a for a in actions if a.action_type == "search"]
        visits = [a for a in actions if a.action_type == "page_visit"
                  and not self._is_search_results_page(a)]
        bounces = [v for v in visits if 0 < v.duration < self.quick_bounce]
        engaged_visits = [v for v in visits if v.duration >= self.engaged_threshold]
        deep_visits = [v for v in visits if v.duration >= self.deep_engagement]

        # Check if topic appears in later sequences (unresolved)
        topic_continues = False
        if idx < len(all_sequences) - 1:
            for later_seq in all_sequences[idx + 1:]:
                if self._topics_related(actions[0], later_seq.actions[0]):
                    topic_continues = True
                    break

        # Classification logic based on sequence patterns

        # Pattern: Multiple searches, many bounces, no deep engagement = STRUGGLING
        if len(searches) >= 2 and len(bounces) >= 2 and len(deep_visits) == 0:
            sequence.sequence_type = "struggling"
            sequence.resolved = False
            sequence.confidence = min(0.5 + (len(bounces) * 0.1) + (len(searches) * 0.1), 0.95)
            sequence.pain_point = f"Couldn't find answer for: {sequence.topic}"
            return

        # Pattern: Search → bounce → refined search → bounce... = STRUGGLING
        if len(searches) >= 3 and len(bounces) >= len(searches) - 1:
            sequence.sequence_type = "struggling"
            sequence.resolved = False
            sequence.confidence = 0.85
            sequence.pain_point = f"Repeated failed attempts: {sequence.topic}"
            return

        # Pattern: Search → deep engagement → topic dropped = SUCCESSFUL
        if len(deep_visits) >= 1 and not topic_continues:
            sequence.sequence_type = "successful"
            sequence.resolved = True
            sequence.resolution_signal = f"Deep engagement ({deep_visits[0].duration}s) then topic dropped"
            sequence.confidence = 0.8
            return

        # Pattern: Search → engaged visit → done = SUCCESSFUL
        if len(engaged_visits) >= 1 and len(searches) <= 2 and not topic_continues:
            sequence.sequence_type = "successful"
            sequence.resolved = True
            sequence.resolution_signal = "Found useful content"
            sequence.confidence = 0.7
            return

        # Pattern: Search → quick click → done (no refinement) = QUICK_ANSWER
        if len(searches) == 1 and len(visits) <= 2 and sequence.total_duration < 60:
            sequence.sequence_type = "quick_answer"
            sequence.resolved = True
            sequence.resolution_signal = "Quick lookup"
            sequence.confidence = 0.6
            return

        # Pattern: Varied topics, no deep focus = EXPLORING
        if len(searches) >= 2 and len(bounces) < len(searches) / 2:
            sequence.sequence_type = "exploring"
            sequence.resolved = True  # Exploring is intentional
            sequence.confidence = 0.5
            return

        # Default: inconclusive
        sequence.sequence_type = "mixed"
        sequence.resolved = not topic_continues
        sequence.confidence = 0.4

    def _extract_pain_point(self, sequence: Sequence) -> str:
        """Extract a descriptive pain point from a struggling sequence."""
        searches = [a.content for a in sequence.actions if a.action_type == "search"]

        if not searches:
            return sequence.topic

        # If multiple searches, they show the refinement journey
        if len(searches) >= 2:
            return f"Tried: {' → '.join(searches[:4])}"

        return searches[0]

    def analyze(self, user_data: Dict[str, Any]) -> SequenceAnalysis:
        """
        Main entry point: analyze user data through sequences.

        Returns comprehensive SequenceAnalysis with pain points and insights.
        """
        logger.info("Extracting actions from user data...")
        actions = self._extract_actions(user_data)
        logger.info(f"Found {len(actions)} actions")

        if not actions:
            return SequenceAnalysis(
                sequences=[],
                summary="No user actions found to analyze"
            )

        logger.info("Grouping actions into sequences...")
        sequences = self._group_into_sequences(actions)
        logger.info(f"Identified {len(sequences)} sequences")

        # Classify each sequence
        logger.info("Classifying sequences...")
        for i, seq in enumerate(sequences):
            self._classify_sequence(seq, sequences, i)

        # Extract insights
        unresolved = [s for s in sequences if not s.resolved]
        struggling = [s for s in sequences if s.sequence_type == "struggling"]
        successful = [s for s in sequences if s.sequence_type == "successful"]

        # Extract pain points from struggling sequences
        pain_points = []
        struggling_topics = []
        for seq in struggling:
            if seq.pain_point:
                pain_points.append(seq.pain_point)
            struggling_topics.append(seq.topic)

        # Also check unresolved non-struggling sequences
        for seq in unresolved:
            if seq.sequence_type != "struggling" and seq.search_attempts >= 2:
                pain_points.append(f"Unresolved: {seq.topic}")

        successful_topics = [s.topic for s in successful]

        # Calculate metrics
        resolution_rate = len([s for s in sequences if s.resolved]) / len(sequences) if sequences else 0

        struggling_attempts = [s.search_attempts for s in struggling]
        avg_attempts = sum(struggling_attempts) / len(struggling_attempts) if struggling_attempts else 0

        # Frustration score based on struggling ratio and severity
        frustration_score = 0
        if sequences:
            struggling_ratio = len(struggling) / len(sequences)
            frustration_score = struggling_ratio * 60  # Base from ratio

            # Add severity (more attempts = more frustrated)
            if avg_attempts > 3:
                frustration_score += 20
            elif avg_attempts > 2:
                frustration_score += 10

            # Add bounce severity
            total_bounces = sum(s.bounce_count for s in struggling)
            if total_bounces > 10:
                frustration_score += 20
            elif total_bounces > 5:
                frustration_score += 10

        frustration_score = min(frustration_score, 100)

        # Generate summary
        if frustration_score > 60:
            summary = f"High frustration: {len(struggling)} struggling sequences detected. User repeatedly failed to find answers."
        elif frustration_score > 30:
            summary = f"Moderate frustration: Some struggling detected ({len(struggling)} sequences). Resolution rate: {resolution_rate:.0%}"
        else:
            summary = f"Low frustration: Most searches resolved successfully. Resolution rate: {resolution_rate:.0%}"

        return SequenceAnalysis(
            sequences=sequences,
            unresolved_sequences=unresolved,
            pain_points=list(set(pain_points))[:10],
            struggling_topics=list(set(struggling_topics))[:10],
            successful_topics=successful_topics[:10],
            resolution_rate=resolution_rate,
            avg_attempts_before_resolution=avg_attempts,
            frustration_score=frustration_score,
            summary=summary
        )

    def analysis_to_text(self, analysis: SequenceAnalysis) -> str:
        """Convert analysis to text for LLM consumption."""
        lines = [
            "SEQUENCE-BASED BEHAVIOR ANALYSIS",
            "=" * 50,
            "",
            f"Total sequences analyzed: {len(analysis.sequences)}",
            f"Resolution rate: {analysis.resolution_rate:.0%}",
            f"Frustration score: {analysis.frustration_score:.0f}/100",
            "",
            f"Summary: {analysis.summary}",
            ""
        ]

        # Struggling sequences (the gold - these are pain points)
        struggling = [s for s in analysis.sequences if s.sequence_type == "struggling"]
        if struggling:
            lines.append("## STRUGGLING SEQUENCES (Pain Points)")
            lines.append("-" * 40)
            for seq in struggling[:5]:
                lines.append(f"\nTopic: {seq.topic}")
                lines.append(f"  Attempts: {seq.search_attempts} searches, {seq.bounce_count} bounces")
                lines.append(f"  Confidence: {seq.confidence:.0%}")
                if seq.pain_point:
                    lines.append(f"  Pain point: {seq.pain_point}")

                # Show the action sequence
                lines.append("  Sequence:")
                for action in seq.actions[:6]:
                    if action.action_type == "search":
                        lines.append(f"    → Search: \"{action.content}\"")
                    else:
                        duration_note = f" ({action.duration}s)" if action.duration else ""
                        title = action.title[:40] if action.title else action.content[:40]
                        lines.append(f"    → Visit: {title}{duration_note}")
                if len(seq.actions) > 6:
                    lines.append(f"    ... and {len(seq.actions) - 6} more actions")

        # Pain points summary
        if analysis.pain_points:
            lines.append("\n## EXTRACTED PAIN POINTS")
            lines.append("-" * 40)
            for pp in analysis.pain_points:
                lines.append(f"  • {pp}")

        # Successful sequences (for context)
        successful = [s for s in analysis.sequences if s.sequence_type == "successful"]
        if successful:
            lines.append(f"\n## SUCCESSFUL RESOLUTIONS ({len(successful)} sequences)")
            lines.append("-" * 40)
            for seq in successful[:3]:
                lines.append(f"  ✓ {seq.topic}")
                if seq.resolution_signal:
                    lines.append(f"    Signal: {seq.resolution_signal}")

        return "\n".join(lines)

    def get_pain_points_for_matching(self, analysis: SequenceAnalysis) -> List[str]:
        """Get pain points in a format suitable for tool matching."""
        points = []

        # From struggling sequences - extract the search queries
        for seq in analysis.sequences:
            if seq.sequence_type == "struggling":
                searches = [a.content for a in seq.actions if a.action_type == "search"]
                points.extend(searches)

        # Add explicit pain points
        points.extend(analysis.pain_points)

        # Deduplicate while preserving order
        seen = set()
        unique = []
        for p in points:
            if p.lower() not in seen:
                seen.add(p.lower())
                unique.append(p)

        return unique[:20]
