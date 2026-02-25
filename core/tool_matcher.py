"""
Tool Matcher Module - Semantic similarity-based tool matching.

Instead of category matching, this module:
1. Embeds tool descriptions and use cases
2. Computes similarity to user profile
3. Ranks tools by semantic relevance
"""

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from .embeddings import (
    EmbeddingModel,
    cosine_similarity,
    cosine_similarity_matrix,
    find_top_k_similar
)
from .user_profile import UserProfile
from .task_detector import TaskDetectionResult, TASK_TYPES

logger = logging.getLogger(__name__)


@dataclass
class ToolEmbedding:
    """Embedded representation of an AI tool."""
    tool_id: str
    name: str
    embedding: np.ndarray
    description: str
    use_cases: List[str] = field(default_factory=list)
    category: str = ""
    url: str = ""
    pricing: str = ""
    has_free_tier: bool = False


@dataclass
class ToolMatch:
    """A matched tool with relevance scoring."""
    tool: ToolEmbedding
    overall_score: float
    profile_similarity: float  # Similarity to overall user profile
    cluster_similarities: Dict[str, float] = field(default_factory=dict)  # Per-cluster
    matched_needs: List[str] = field(default_factory=list)
    explanation: str = ""


class ToolMatcher:
    """
    Matches tools to user profiles using semantic similarity.

    Usage:
        matcher = ToolMatcher(embedding_model)
        matcher.index_tools(tools)
        matches = matcher.match(user_profile, config)
    """

    def __init__(self, embedding_model: EmbeddingModel):
        self.embedding_model = embedding_model
        self.tool_embeddings: List[ToolEmbedding] = []
        self.embedding_matrix: Optional[np.ndarray] = None
        self._indexed = False
        self._tools_data: Dict[str, Dict[str, Any]] = {}  # tool_id -> full tool data

    def _tool_to_text(self, tool_data: Dict[str, Any]) -> str:
        """
        Convert tool data to a rich text representation for embedding.

        Combines multiple fields for better semantic matching.
        """
        data = tool_data.get("data", tool_data)

        parts = []

        # Name and aliases
        name = data.get("name", "")
        parts.append(name)

        aliases = data.get("aliases", [])
        if aliases:
            parts.append(f"Also known as: {', '.join(aliases)}")

        # Description (most important)
        description = data.get("description", "")
        if description:
            parts.append(description)

        # Capabilities
        capabilities = data.get("capabilities", {})
        task_verbs = capabilities.get("task_verbs", [])
        if task_verbs:
            parts.append(f"Can: {', '.join(task_verbs[:10])}")

        # Use cases
        matching = data.get("matching", {})
        use_cases = matching.get("use_cases", [])
        if use_cases:
            parts.append(f"Use cases: {', '.join(use_cases[:5])}")

        # Pain points it solves
        pain_points = matching.get("pain_points", [])
        if pain_points:
            parts.append(f"Solves: {', '.join(pain_points[:5])}")

        # Category context
        category = data.get("category", {})
        primary = category.get("primary", "")
        if primary:
            parts.append(f"Category: {primary}")

        return " | ".join(parts)

    def index_tools(
        self,
        tools: List[Dict[str, Any]],
        show_progress: bool = True
    ) -> None:
        """
        Index all tools by computing their embeddings.

        Args:
            tools: List of tool dictionaries
            show_progress: Show progress bar
        """
        logger.info(f"Indexing {len(tools)} tools...")

        self.tool_embeddings = []
        self._tools_data = {}
        texts = []

        for tool in tools:
            data = tool.get("data", tool)

            # Extract tool info
            tool_id = data.get("tool_id", data.get("name", "unknown"))
            name = data.get("name", "Unknown")
            description = data.get("description", "")
            category = data.get("category", {}).get("primary", "")
            url = data.get("url", "")
            pricing = data.get("pricing", {}).get("model", "unknown")
            has_free_tier = data.get("pricing", {}).get("free_tier", False)
            use_cases = data.get("matching", {}).get("use_cases", [])

            # Get text for embedding
            text = self._tool_to_text(tool)
            texts.append(text)

            # Store full tool data for task_fit access
            self._tools_data[tool_id] = data

            self.tool_embeddings.append(ToolEmbedding(
                tool_id=tool_id,
                name=name,
                embedding=np.array([]),  # Will fill in after batch embed
                description=description,
                use_cases=use_cases,
                category=category,
                url=url,
                pricing=pricing,
                has_free_tier=has_free_tier
            ))

        # Batch embed all tools
        embeddings = self.embedding_model.embed_batch(texts, show_progress=show_progress)

        # Assign embeddings
        for i, emb in enumerate(embeddings):
            self.tool_embeddings[i].embedding = emb

        # Build matrix for fast similarity computation
        self.embedding_matrix = embeddings
        self._indexed = True

        logger.info(f"Indexed {len(self.tool_embeddings)} tools")

    def match(
        self,
        profile: UserProfile,
        config: Dict[str, Any],
        exclude_tools: Optional[List[str]] = None
    ) -> List[ToolMatch]:
        """
        Match tools to a user profile.

        Args:
            profile: User's semantic profile
            config: Matching configuration
            exclude_tools: Tool names/IDs to exclude (already used)

        Returns:
            List of ToolMatch objects, sorted by score
        """
        if not self._indexed:
            raise ValueError("Tools not indexed. Call index_tools() first.")

        if profile.embedding is None:
            raise ValueError("Profile has no embedding. Build profile first.")

        top_k = config.get("top_k", 50)
        threshold = config.get("similarity_threshold", 0.3)
        exclude_tools = set(exclude_tools or [])

        # Step 1: Compute similarity to overall profile
        profile_similarities = cosine_similarity_matrix(
            profile.embedding.reshape(1, -1),
            self.embedding_matrix
        )[0]

        # Step 2: Compute similarity to each cluster (if available)
        cluster_scores = {}
        if profile.clusters:
            for cluster in profile.clusters:
                if cluster.centroid is not None:
                    sims = cosine_similarity_matrix(
                        cluster.centroid.reshape(1, -1),
                        self.embedding_matrix
                    )[0]
                    cluster_scores[cluster.theme] = sims

        # Step 3: Combine scores
        matches = []
        for i, tool_emb in enumerate(self.tool_embeddings):
            # Skip excluded tools
            if tool_emb.name.lower() in exclude_tools or tool_emb.tool_id in exclude_tools:
                continue

            profile_sim = float(profile_similarities[i])

            # Skip if below threshold
            if profile_sim < threshold:
                continue

            # Get cluster similarities
            cluster_sims = {}
            for theme, sims in cluster_scores.items():
                cluster_sims[theme] = float(sims[i])

            # Compute overall score (profile sim + best cluster sim)
            best_cluster_sim = max(cluster_sims.values()) if cluster_sims else 0
            overall_score = (profile_sim * 0.6) + (best_cluster_sim * 0.4)

            # Find which needs this tool matches
            matched_needs = self._find_matched_needs(tool_emb, profile, cluster_sims)

            matches.append(ToolMatch(
                tool=tool_emb,
                overall_score=overall_score,
                profile_similarity=profile_sim,
                cluster_similarities=cluster_sims,
                matched_needs=matched_needs
            ))

        # Sort by overall score
        matches.sort(key=lambda m: m.overall_score, reverse=True)

        # Return top k
        return matches[:top_k]

    def _find_matched_needs(
        self,
        tool: ToolEmbedding,
        profile: UserProfile,
        cluster_sims: Dict[str, float]
    ) -> List[str]:
        """Find which user needs a tool matches."""
        matched = []

        # Match to high-similarity clusters
        for theme, sim in cluster_sims.items():
            if sim > 0.5:
                matched.append(f"Relevant to: {theme}")

        # Match to inferred needs (simple text matching for now)
        tool_text = f"{tool.name} {tool.description}".lower()
        for need in profile.inferred_needs:
            need_keywords = need.lower().split()
            if any(kw in tool_text for kw in need_keywords if len(kw) > 3):
                matched.append(need)

        return matched[:3]  # Limit to top 3

    def generate_explanation(
        self,
        match: ToolMatch,
        profile: UserProfile
    ) -> str:
        """
        Generate a human-readable explanation for why a tool was matched.
        """
        lines = []

        # Overall relevance
        lines.append(f"**{match.tool.name}** (Score: {match.overall_score:.2f})")
        lines.append(f"Profile match: {match.profile_similarity:.2f}")

        # Best cluster matches
        if match.cluster_similarities:
            best_clusters = sorted(
                match.cluster_similarities.items(),
                key=lambda x: x[1],
                reverse=True
            )[:2]
            for theme, sim in best_clusters:
                if sim > 0.3:
                    lines.append(f"  - Matches '{theme}' theme: {sim:.2f}")

        # Matched needs
        if match.matched_needs:
            lines.append("Addresses:")
            for need in match.matched_needs:
                lines.append(f"  - {need}")

        # Tool details
        if match.tool.use_cases:
            lines.append(f"Use cases: {', '.join(match.tool.use_cases[:3])}")

        return "\n".join(lines)

    def get_already_used_tools(
        self,
        user_data: Dict[str, Any]
    ) -> List[str]:
        """
        Identify AI tools the user is already using.
        """
        known_ai_domains = {
            "claude.ai": "Claude",
            "chatgpt.com": "ChatGPT",
            "chat.openai.com": "ChatGPT",
            "gemini.google.com": "Gemini",
            "perplexity.ai": "Perplexity",
            "copilot.github.com": "GitHub Copilot",
            "copilot.microsoft.com": "Microsoft Copilot",
            "midjourney.com": "Midjourney",
            "notion.ai": "Notion AI",
            "jasper.ai": "Jasper",
            "copy.ai": "Copy.ai",
            "grammarly.com": "Grammarly",
        }

        used_tools = set()

        for entry in user_data.get("browsing_history", []):
            url = entry.get("url", "").lower()
            for domain, tool_name in known_ai_domains.items():
                if domain in url:
                    used_tools.add(tool_name.lower())

        return list(used_tools)

    def match_with_task_context(
        self,
        profile: UserProfile,
        task_result: TaskDetectionResult,
        config: Dict[str, Any],
        exclude_tools: Optional[List[str]] = None
    ) -> List[ToolMatch]:
        """
        Match tools considering inferred task type.

        Enhancement over base match():
        1. Get base semantic matches
        2. Boost scores for tools matching dominant task
        3. Penalize tools that don't fit current task

        Args:
            profile: User's semantic profile
            task_result: Task detection result with task distribution
            config: Matching configuration
            exclude_tools: Tool names/IDs to exclude

        Returns:
            List of ToolMatch objects, sorted by task-adjusted score
        """
        # Get base matches first
        base_matches = self.match(profile, config, exclude_tools)

        if not base_matches:
            return []

        # Get task matching config
        task_config = config.get("task_detection", {}).get("task_matching", {})
        min_task_fit = task_config.get("min_task_fit", 3)
        task_boost_weight = task_config.get("task_boost_weight", 0.2)

        task_dist = task_result.overall_distribution
        dominant_task = task_result.dominant_task

        enhanced_matches = []

        for match in base_matches:
            tool_data = self._tools_data.get(match.tool.tool_id, {})
            task_fit = tool_data.get("task_fit", {})

            # Calculate task-adjusted score
            task_score = 0.0

            if task_fit:
                # Weighted sum of task_fit scores based on task distribution
                for task, probability in task_dist.items():
                    fit = task_fit.get(task, 5) / 10.0  # Normalize to 0-1
                    task_score += fit * probability
            else:
                # No task_fit data - use default 0.5
                task_score = 0.5

            # Check threshold for dominant task
            dominant_fit = task_fit.get(dominant_task, 5) if task_fit else 5

            # Penalize tools that don't fit dominant task
            penalty = 1.0
            if dominant_fit < min_task_fit:
                penalty = 0.7

            # Combine with original score
            adjusted_score = (
                match.overall_score * (1 - task_boost_weight) +
                task_score * task_boost_weight
            ) * penalty

            # Add task fit info to matched_needs
            matched_needs = match.matched_needs.copy()
            if task_fit:
                matched_needs.append(f"Fits {dominant_task} task ({dominant_fit}/10)")

            enhanced_match = ToolMatch(
                tool=match.tool,
                overall_score=adjusted_score,
                profile_similarity=match.profile_similarity,
                cluster_similarities=match.cluster_similarities,
                matched_needs=matched_needs,
                explanation=match.explanation
            )
            enhanced_matches.append(enhanced_match)

        # Re-sort by adjusted score
        enhanced_matches.sort(key=lambda m: m.overall_score, reverse=True)

        return enhanced_matches

    def matches_to_text(
        self,
        matches: List[ToolMatch],
        limit: int = 20
    ) -> str:
        """
        Convert matches to text summary for LLM consumption.
        """
        lines = ["TOP MATCHED TOOLS", "=" * 40, ""]

        for i, match in enumerate(matches[:limit], 1):
            lines.append(f"\n## {i}. {match.tool.name}")
            lines.append(f"Score: {match.overall_score:.3f} | Category: {match.tool.category}")
            lines.append(f"Pricing: {match.tool.pricing} | Free tier: {match.tool.has_free_tier}")
            lines.append(f"\nDescription: {match.tool.description[:300]}...")

            if match.tool.use_cases:
                lines.append(f"\nUse cases: {', '.join(match.tool.use_cases[:3])}")

            if match.matched_needs:
                lines.append(f"\nMatches user needs:")
                for need in match.matched_needs:
                    lines.append(f"  - {need}")

            if match.cluster_similarities:
                best = max(match.cluster_similarities.items(), key=lambda x: x[1])
                lines.append(f"\nBest theme match: '{best[0]}' ({best[1]:.2f})")

        return "\n".join(lines)
