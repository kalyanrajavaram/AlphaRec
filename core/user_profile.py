"""
User Profile Module - Build semantic user profiles from behavior data.

Instead of hardcoded categories, this module:
1. Extracts meaningful signals from user data
2. Embeds those signals semantically
3. Clusters to find natural themes
4. Builds a rich profile for matching
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import numpy as np

from .embeddings import EmbeddingModel, cosine_similarity

logger = logging.getLogger(__name__)


@dataclass
class UserSignal:
    """A single signal extracted from user behavior."""
    text: str
    signal_type: str  # "search", "page_title", "app_name"
    weight: float = 1.0
    timestamp: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SemanticCluster:
    """A cluster of semantically similar signals."""
    theme: str  # Auto-generated or LLM-labeled
    signals: List[UserSignal]
    centroid: Optional[np.ndarray] = None
    coherence: float = 0.0  # How tight the cluster is


@dataclass
class UserProfile:
    """Complete semantic profile of a user."""
    # Raw signals
    signals: List[UserSignal]

    # Embeddings
    embedding: Optional[np.ndarray] = None  # Combined user embedding
    signal_embeddings: Optional[np.ndarray] = None  # Individual signal embeddings

    # Discovered themes (from clustering)
    clusters: List[SemanticCluster] = field(default_factory=list)

    # High-level summary
    primary_interests: List[str] = field(default_factory=list)
    inferred_needs: List[str] = field(default_factory=list)

    # Metadata
    total_signals: int = 0
    signal_breakdown: Dict[str, int] = field(default_factory=dict)


class UserProfileBuilder:
    """
    Builds semantic user profiles from raw behavior data.

    Usage:
        builder = UserProfileBuilder(embedding_model)
        profile = builder.build(user_data, config)
    """

    def __init__(self, embedding_model: EmbeddingModel):
        self.embedding_model = embedding_model

    def extract_signals(
        self,
        user_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> List[UserSignal]:
        """
        Extract meaningful signals from raw user data.

        Args:
            user_data: Raw user data (browsing, searches, apps)
            config: Configuration for what to include

        Returns:
            List of UserSignal objects
        """
        signals = []
        weights = config.get("weights", {})

        # Extract from search queries (highest signal)
        if config.get("include_searches", True):
            search_weight = weights.get("searches", 2.0)
            for query in user_data.get("search_queries", []):
                text = query.get("query", "").strip()
                if text and len(text) > 2:
                    signals.append(UserSignal(
                        text=text,
                        signal_type="search",
                        weight=search_weight,
                        timestamp=query.get("search_time"),
                        metadata={"engine": query.get("search_engine", "")}
                    ))

        # Extract from page titles
        if config.get("include_page_titles", True):
            title_weight = weights.get("page_titles", 1.0)
            seen_titles = set()

            for entry in user_data.get("browsing_history", []):
                title = entry.get("title", "").strip()

                # Skip empty, duplicate, or generic titles
                if not title or len(title) < 5:
                    continue
                if title.lower() in seen_titles:
                    continue
                if self._is_generic_title(title):
                    continue

                seen_titles.add(title.lower())
                duration = entry.get("active_duration_seconds") or entry.get("duration_seconds") or 0

                # Weight by time spent (more time = more relevant)
                time_weight = min(1.0 + (duration / 300), 2.0)  # Cap at 2x

                signals.append(UserSignal(
                    text=title,
                    signal_type="page_title",
                    weight=title_weight * time_weight,
                    timestamp=entry.get("visit_time"),
                    metadata={
                        "url": entry.get("url", ""),
                        "duration": duration
                    }
                ))

        # Extract from app names
        if config.get("include_app_names", True):
            app_weight = weights.get("app_names", 0.5)
            app_durations = {}

            for entry in user_data.get("application_usage", []):
                app = entry.get("app_name", "").strip()
                if app:
                    duration = entry.get("duration_seconds", 0) or 0
                    app_durations[app] = app_durations.get(app, 0) + duration

            # Only include apps with significant usage
            for app, duration in app_durations.items():
                if duration > 60:  # At least 1 minute
                    time_weight = min(1.0 + (duration / 600), 2.0)
                    signals.append(UserSignal(
                        text=f"Using {app} application",
                        signal_type="app_name",
                        weight=app_weight * time_weight,
                        metadata={"app": app, "duration": duration}
                    ))

        return signals

    def _is_generic_title(self, title: str) -> bool:
        """Check if a page title is too generic to be useful."""
        generic_patterns = [
            "home", "homepage", "welcome", "dashboard",
            "login", "sign in", "sign up", "register",
            "404", "error", "not found",
            "loading", "please wait",
            "untitled", "new tab"
        ]
        title_lower = title.lower()
        return any(pattern in title_lower for pattern in generic_patterns)

    def cluster_signals(
        self,
        signals: List[UserSignal],
        embeddings: np.ndarray,
        config: Dict[str, Any]
    ) -> List[SemanticCluster]:
        """
        Cluster signals into semantic themes.

        Uses HDBSCAN for automatic cluster detection.
        """
        if len(signals) < 3:
            # Not enough signals to cluster
            return []

        try:
            import hdbscan
        except ImportError:
            logger.warning("hdbscan not installed, skipping clustering")
            return []

        min_cluster_size = config.get("min_cluster_size", 3)
        min_samples = config.get("min_samples", 2)

        clusterer = hdbscan.HDBSCAN(
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            metric="euclidean"
        )

        # Cluster the embeddings
        labels = clusterer.fit_predict(embeddings)

        # Group signals by cluster
        clusters = []
        unique_labels = set(labels) - {-1}  # -1 is noise

        for label in unique_labels:
            cluster_indices = np.where(labels == label)[0]
            cluster_signals = [signals[i] for i in cluster_indices]
            cluster_embeddings = embeddings[cluster_indices]

            # Compute centroid
            centroid = cluster_embeddings.mean(axis=0)

            # Compute coherence (average similarity to centroid)
            similarities = [
                cosine_similarity(emb, centroid)
                for emb in cluster_embeddings
            ]
            coherence = np.mean(similarities)

            # Generate theme label from most representative signals
            theme = self._generate_theme_label(cluster_signals)

            clusters.append(SemanticCluster(
                theme=theme,
                signals=cluster_signals,
                centroid=centroid,
                coherence=coherence
            ))

        # Sort by cluster size (most signals first)
        clusters.sort(key=lambda c: len(c.signals), reverse=True)

        return clusters

    def _generate_theme_label(self, signals: List[UserSignal]) -> str:
        """Generate a descriptive label for a cluster of signals."""
        # Use search queries if available (most explicit)
        searches = [s.text for s in signals if s.signal_type == "search"]
        if searches:
            # Return the shortest search as it's often most specific
            return min(searches, key=len)

        # Otherwise use the shortest page title
        titles = [s.text for s in signals if s.signal_type == "page_title"]
        if titles:
            return min(titles, key=len)

        # Fallback
        return signals[0].text if signals else "Unknown"

    def infer_needs(
        self,
        signals: List[UserSignal],
        clusters: List[SemanticCluster]
    ) -> List[str]:
        """
        Infer user needs from signals and clusters.

        Returns human-readable need statements.
        """
        needs = []

        # From search queries - most explicit signals
        search_signals = [s for s in signals if s.signal_type == "search"]
        for signal in search_signals[:5]:  # Top 5 searches
            text = signal.text.lower()

            # Detect problem-solving intent
            if any(w in text for w in ["how to", "fix", "error", "issue", "problem"]):
                needs.append(f"Troubleshooting: {signal.text}")
            elif any(w in text for w in ["best", "top", "vs", "alternative"]):
                needs.append(f"Evaluating options: {signal.text}")
            elif any(w in text for w in ["learn", "tutorial", "guide", "course"]):
                needs.append(f"Learning: {signal.text}")

        # From clusters - thematic needs
        for cluster in clusters[:3]:  # Top 3 clusters
            if cluster.coherence > 0.5:  # Only tight clusters
                needs.append(f"Focus area: {cluster.theme}")

        return list(set(needs))[:10]  # Dedupe and limit

    def build(
        self,
        user_data: Dict[str, Any],
        config: Dict[str, Any]
    ) -> UserProfile:
        """
        Build a complete semantic user profile.

        Args:
            user_data: Raw user behavior data
            config: Profile building configuration

        Returns:
            UserProfile with embeddings and clusters
        """
        logger.info("Building user profile...")

        # Step 1: Extract signals
        signals = self.extract_signals(user_data, config.get("user_profile", {}))
        logger.info(f"Extracted {len(signals)} signals")

        if not signals:
            logger.warning("No signals extracted from user data")
            return UserProfile(signals=[], total_signals=0)

        # Step 2: Embed all signals
        texts = [s.text for s in signals]
        weights = [s.weight for s in signals]

        signal_embeddings = self.embedding_model.embed_batch(texts, show_progress=True)

        # Step 3: Create combined user embedding (weighted average)
        user_embedding = self.embedding_model.embed_weighted(texts, weights)

        # Step 4: Cluster signals to find themes
        clusters = self.cluster_signals(
            signals,
            signal_embeddings,
            config.get("clustering", {})
        )
        logger.info(f"Found {len(clusters)} semantic clusters")

        # Step 5: Infer needs
        inferred_needs = self.infer_needs(signals, clusters)

        # Step 6: Extract primary interests from clusters
        primary_interests = [c.theme for c in clusters[:5]]

        # Build signal breakdown
        signal_breakdown = {}
        for signal in signals:
            signal_breakdown[signal.signal_type] = signal_breakdown.get(signal.signal_type, 0) + 1

        profile = UserProfile(
            signals=signals,
            embedding=user_embedding,
            signal_embeddings=signal_embeddings,
            clusters=clusters,
            primary_interests=primary_interests,
            inferred_needs=inferred_needs,
            total_signals=len(signals),
            signal_breakdown=signal_breakdown
        )

        logger.info(f"Profile built: {len(signals)} signals, {len(clusters)} clusters")
        return profile

    def profile_to_text(self, profile: UserProfile) -> str:
        """
        Convert profile to text summary for LLM consumption.
        """
        lines = ["USER PROFILE SUMMARY", "=" * 40, ""]

        # Signal breakdown
        lines.append("## Activity Overview")
        for signal_type, count in profile.signal_breakdown.items():
            lines.append(f"- {signal_type}: {count} signals")
        lines.append("")

        # Primary interests
        if profile.primary_interests:
            lines.append("## Primary Interests (from behavior clusters)")
            for interest in profile.primary_interests:
                lines.append(f"- {interest}")
            lines.append("")

        # Inferred needs
        if profile.inferred_needs:
            lines.append("## Inferred Needs")
            for need in profile.inferred_needs:
                lines.append(f"- {need}")
            lines.append("")

        # Top searches (explicit intent)
        searches = [s for s in profile.signals if s.signal_type == "search"][:10]
        if searches:
            lines.append("## Recent Searches (explicit intent)")
            for s in searches:
                lines.append(f"- {s.text}")
            lines.append("")

        # Cluster details
        if profile.clusters:
            lines.append("## Behavior Themes")
            for cluster in profile.clusters[:5]:
                lines.append(f"\n### {cluster.theme}")
                lines.append(f"Signals: {len(cluster.signals)}, Coherence: {cluster.coherence:.2f}")
                sample_texts = [s.text for s in cluster.signals[:3]]
                for text in sample_texts:
                    lines.append(f"  - {text}")

        return "\n".join(lines)
