"""
Embeddings Module - Foundation for semantic analysis.

Provides a unified interface for embedding any text (searches, titles, tool descriptions).
Uses sentence-transformers for local, fast, high-quality embeddings.
"""

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import List, Optional, Union

import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """
    Wrapper around sentence-transformers for text embedding.

    Features:
    - Lazy loading (model only loads when first needed)
    - Caching to avoid re-computing embeddings
    - Batch processing for efficiency
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        cache_dir: Optional[str] = None,
        use_cache: bool = True
    ):
        self.model_name = model_name
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.use_cache = use_cache and cache_dir is not None
        self._model = None
        self._dimension = None

        if self.use_cache and self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)

    @property
    def model(self):
        """Lazy load the model."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading embedding model: {self.model_name}")
                self._model = SentenceTransformer(self.model_name)
                self._dimension = self._model.get_sentence_embedding_dimension()
                logger.info(f"Model loaded. Embedding dimension: {self._dimension}")
            except ImportError:
                raise ImportError(
                    "sentence-transformers is required. "
                    "Install with: pip install sentence-transformers"
                )
        return self._model

    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        if self._dimension is None:
            _ = self.model  # Force load
        return self._dimension

    def _cache_key(self, text: str) -> str:
        """Generate cache key for a text string."""
        content = f"{self.model_name}:{text}"
        return hashlib.md5(content.encode()).hexdigest()

    def _get_cached(self, text: str) -> Optional[np.ndarray]:
        """Retrieve embedding from cache if available."""
        if not self.use_cache:
            return None

        cache_path = self.cache_dir / f"{self._cache_key(text)}.npy"
        if cache_path.exists():
            try:
                return np.load(cache_path)
            except Exception as e:
                logger.warning(f"Failed to load cached embedding: {e}")
        return None

    def _save_to_cache(self, text: str, embedding: np.ndarray) -> None:
        """Save embedding to cache."""
        if not self.use_cache:
            return

        cache_path = self.cache_dir / f"{self._cache_key(text)}.npy"
        try:
            np.save(cache_path, embedding)
        except Exception as e:
            logger.warning(f"Failed to cache embedding: {e}")

    def embed(self, text: str) -> np.ndarray:
        """
        Embed a single text string.

        Args:
            text: The text to embed

        Returns:
            numpy array of shape (dimension,)
        """
        if not text or not text.strip():
            return np.zeros(self.dimension)

        # Check cache
        cached = self._get_cached(text)
        if cached is not None:
            return cached

        # Compute embedding
        embedding = self.model.encode(text, convert_to_numpy=True)

        # Cache result
        self._save_to_cache(text, embedding)

        return embedding

    def embed_batch(
        self,
        texts: List[str],
        show_progress: bool = False
    ) -> np.ndarray:
        """
        Embed multiple texts efficiently.

        Args:
            texts: List of texts to embed
            show_progress: Show progress bar

        Returns:
            numpy array of shape (n_texts, dimension)
        """
        if not texts:
            return np.zeros((0, self.dimension))

        # Filter empty texts but track indices
        valid_indices = []
        valid_texts = []
        cached_results = {}

        for i, text in enumerate(texts):
            if text and text.strip():
                cached = self._get_cached(text)
                if cached is not None:
                    cached_results[i] = cached
                else:
                    valid_indices.append(i)
                    valid_texts.append(text)
            # Empty texts will get zero vectors

        # Compute embeddings for non-cached texts
        if valid_texts:
            embeddings = self.model.encode(
                valid_texts,
                convert_to_numpy=True,
                show_progress_bar=show_progress
            )

            # Cache new embeddings
            for idx, (text, emb) in enumerate(zip(valid_texts, embeddings)):
                self._save_to_cache(text, emb)

        # Assemble final result
        result = np.zeros((len(texts), self.dimension))

        # Fill in cached results
        for i, emb in cached_results.items():
            result[i] = emb

        # Fill in newly computed results
        if valid_texts:
            for list_idx, original_idx in enumerate(valid_indices):
                result[original_idx] = embeddings[list_idx]

        return result

    def embed_weighted(
        self,
        texts: List[str],
        weights: Optional[List[float]] = None
    ) -> np.ndarray:
        """
        Create a weighted average embedding from multiple texts.

        Args:
            texts: List of texts
            weights: Optional weights for each text (default: equal weights)

        Returns:
            Single embedding vector (weighted average)
        """
        if not texts:
            return np.zeros(self.dimension)

        embeddings = self.embed_batch(texts)

        if weights is None:
            weights = [1.0] * len(texts)

        weights = np.array(weights)
        weights = weights / weights.sum()  # Normalize

        weighted_embedding = np.average(embeddings, axis=0, weights=weights)

        # Normalize the result
        norm = np.linalg.norm(weighted_embedding)
        if norm > 0:
            weighted_embedding = weighted_embedding / norm

        return weighted_embedding


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        a: First vector
        b: Second vector

    Returns:
        Similarity score between -1 and 1
    """
    norm_a = np.linalg.norm(a)
    norm_b = np.linalg.norm(b)

    if norm_a == 0 or norm_b == 0:
        return 0.0

    return float(np.dot(a, b) / (norm_a * norm_b))


def cosine_similarity_matrix(
    embeddings_a: np.ndarray,
    embeddings_b: np.ndarray
) -> np.ndarray:
    """
    Compute pairwise cosine similarities between two sets of embeddings.

    Args:
        embeddings_a: Shape (n, dim)
        embeddings_b: Shape (m, dim)

    Returns:
        Similarity matrix of shape (n, m)
    """
    # Normalize
    norms_a = np.linalg.norm(embeddings_a, axis=1, keepdims=True)
    norms_b = np.linalg.norm(embeddings_b, axis=1, keepdims=True)

    # Avoid division by zero
    norms_a = np.where(norms_a == 0, 1, norms_a)
    norms_b = np.where(norms_b == 0, 1, norms_b)

    normalized_a = embeddings_a / norms_a
    normalized_b = embeddings_b / norms_b

    return np.dot(normalized_a, normalized_b.T)


def find_top_k_similar(
    query_embedding: np.ndarray,
    candidate_embeddings: np.ndarray,
    k: int = 10
) -> List[tuple]:
    """
    Find the k most similar candidates to a query.

    Args:
        query_embedding: Single query vector (dim,)
        candidate_embeddings: Matrix of candidates (n, dim)
        k: Number of results to return

    Returns:
        List of (index, similarity) tuples, sorted by similarity descending
    """
    similarities = cosine_similarity_matrix(
        query_embedding.reshape(1, -1),
        candidate_embeddings
    )[0]

    # Get top k indices
    top_indices = np.argsort(similarities)[::-1][:k]

    return [(int(idx), float(similarities[idx])) for idx in top_indices]
