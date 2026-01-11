"""Topic detector for repeated mentor help requests.

Analyzes mentor conversations to detect semantically similar questions
using embedding-based similarity clustering.
"""

import logging
from dataclasses import dataclass
from typing import Any

from bo1.llm.embeddings import (
    cosine_similarity,
    generate_embeddings_batch,
)
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Redis key prefixes
TOPIC_CACHE_PREFIX = "mentor_topic_cache"
EMBEDDING_CACHE_PREFIX = "mentor_msg_embedding"

# Cache TTLs
TOPIC_CACHE_TTL = 3600  # 1 hour for computed topics
EMBEDDING_CACHE_TTL = 86400 * 7  # 7 days for message embeddings


@dataclass
class RepeatedTopic:
    """A cluster of semantically similar questions."""

    topic_summary: str
    count: int
    first_asked: str
    last_asked: str
    conversation_ids: list[str]
    representative_messages: list[str]  # Sample of messages in cluster
    similarity_score: float  # Average pairwise similarity in cluster


@dataclass
class SimilarMessage:
    """A message similar to a search query."""

    conversation_id: str
    content: str
    preview: str  # Truncated content for display
    similarity: float
    timestamp: str


class TopicDetector:
    """Detects repeated help requests using embedding similarity.

    Uses Voyage AI embeddings to identify clusters of semantically
    similar questions from mentor conversations.
    """

    def __init__(self, redis_manager: RedisManager | None = None) -> None:
        """Initialize topic detector.

        Args:
            redis_manager: Optional Redis manager instance
        """
        self._redis = redis_manager or RedisManager()

    def _embedding_cache_key(self, user_id: str, message_hash: str) -> str:
        """Generate cache key for message embedding."""
        return f"{EMBEDDING_CACHE_PREFIX}:{user_id}:{message_hash}"

    def _topic_cache_key(self, user_id: str) -> str:
        """Generate cache key for computed topics."""
        return f"{TOPIC_CACHE_PREFIX}:{user_id}"

    def _hash_message(self, content: str) -> str:
        """Generate stable hash for message content."""
        import hashlib

        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _get_cached_embedding(self, user_id: str, content: str) -> list[float] | None:
        """Get cached embedding for a message."""
        import json

        key = self._embedding_cache_key(user_id, self._hash_message(content))
        data = self._redis.client.get(key)
        if data:
            return json.loads(data)
        return None

    def _cache_embedding(self, user_id: str, content: str, embedding: list[float]) -> None:
        """Cache embedding for a message."""
        import json

        key = self._embedding_cache_key(user_id, self._hash_message(content))
        self._redis.client.setex(key, EMBEDDING_CACHE_TTL, json.dumps(embedding))

    def _get_embeddings_with_cache(
        self, user_id: str, messages: list[dict[str, Any]]
    ) -> list[tuple[dict[str, Any], list[float]]]:
        """Get embeddings for messages, using cache where available.

        Args:
            user_id: User ID for cache key scoping
            messages: List of message dicts with 'content' field

        Returns:
            List of (message, embedding) tuples
        """
        results: list[tuple[dict[str, Any], list[float]]] = []
        to_embed: list[tuple[int, dict[str, Any]]] = []

        # Check cache first
        for i, msg in enumerate(messages):
            content = msg.get("content", "")
            cached = self._get_cached_embedding(user_id, content)
            if cached:
                results.append((msg, cached))
            else:
                to_embed.append((i, msg))

        if not to_embed:
            return results

        # Batch embed uncached messages
        texts = [msg.get("content", "") for _, msg in to_embed]
        try:
            embeddings = generate_embeddings_batch(texts, input_type="document")

            # Cache and add to results
            for (_, msg), embedding in zip(to_embed, embeddings, strict=True):
                if embedding:  # Non-empty embedding
                    content = msg.get("content", "")
                    self._cache_embedding(user_id, content, embedding)
                    results.append((msg, embedding))

        except Exception as e:
            logger.warning(f"Failed to generate embeddings: {e}")
            # Return what we have from cache

        return results

    def _cluster_by_similarity(
        self,
        messages_with_embeddings: list[tuple[dict[str, Any], list[float]]],
        threshold: float,
    ) -> list[list[tuple[dict[str, Any], list[float]]]]:
        """Cluster messages by semantic similarity using greedy clustering.

        Args:
            messages_with_embeddings: List of (message, embedding) tuples
            threshold: Similarity threshold for clustering (0-1)

        Returns:
            List of clusters, each a list of (message, embedding) tuples
        """
        if not messages_with_embeddings:
            return []

        clusters: list[list[tuple[dict[str, Any], list[float]]]] = []
        assigned = set()

        for i, (msg_i, emb_i) in enumerate(messages_with_embeddings):
            if i in assigned:
                continue

            # Start new cluster
            cluster = [(msg_i, emb_i)]
            assigned.add(i)

            # Find similar messages
            for j, (msg_j, emb_j) in enumerate(messages_with_embeddings):
                if j in assigned:
                    continue

                similarity = cosine_similarity(emb_i, emb_j)
                if similarity >= threshold:
                    cluster.append((msg_j, emb_j))
                    assigned.add(j)

            clusters.append(cluster)

        return clusters

    def _compute_cluster_similarity(
        self, cluster: list[tuple[dict[str, Any], list[float]]]
    ) -> float:
        """Compute average pairwise similarity within a cluster."""
        if len(cluster) < 2:
            return 1.0

        total = 0.0
        pairs = 0
        for i, (_, emb_i) in enumerate(cluster):
            for j, (_, emb_j) in enumerate(cluster):
                if j > i:
                    total += cosine_similarity(emb_i, emb_j)
                    pairs += 1

        return total / pairs if pairs > 0 else 1.0

    def _generate_topic_summary(self, messages: list[str]) -> str:
        """Generate a summary for a cluster of messages.

        Uses simple heuristic - takes the shortest message as representative.
        For production, could use LLM to generate proper summary.
        """
        if not messages:
            return "Unknown topic"

        # Use shortest message as representative (often most direct)
        shortest = min(messages, key=len)
        # Truncate if too long
        if len(shortest) > 100:
            return shortest[:97] + "..."
        return shortest

    def detect_repeated_topics(
        self,
        user_id: str,
        messages: list[dict[str, Any]],
        threshold: float = 0.85,
        min_occurrences: int = 3,
    ) -> list[RepeatedTopic]:
        """Detect repeated topics from user messages.

        Args:
            user_id: User ID
            messages: List of message dicts with content, timestamp, conversation_id
            threshold: Similarity threshold (0.7-0.95)
            min_occurrences: Minimum cluster size to report (2-10)

        Returns:
            List of RepeatedTopic instances for clusters meeting min_occurrences
        """
        if not messages:
            return []

        # Get embeddings with caching
        messages_with_embeddings = self._get_embeddings_with_cache(user_id, messages)

        if not messages_with_embeddings:
            return []

        # Cluster by similarity
        clusters = self._cluster_by_similarity(messages_with_embeddings, threshold)

        # Filter by min_occurrences and build results
        results: list[RepeatedTopic] = []
        for cluster in clusters:
            if len(cluster) < min_occurrences:
                continue

            # Extract data from cluster
            contents = [msg.get("content", "") for msg, _ in cluster]
            timestamps = [msg.get("timestamp", "") for msg, _ in cluster]
            conv_ids = list({msg.get("conversation_id", "") for msg, _ in cluster})

            # Sort timestamps to get first/last
            sorted_timestamps = sorted(t for t in timestamps if t)

            results.append(
                RepeatedTopic(
                    topic_summary=self._generate_topic_summary(contents),
                    count=len(cluster),
                    first_asked=sorted_timestamps[0] if sorted_timestamps else "",
                    last_asked=sorted_timestamps[-1] if sorted_timestamps else "",
                    conversation_ids=[c for c in conv_ids if c],
                    representative_messages=contents[:3],  # First 3 as sample
                    similarity_score=self._compute_cluster_similarity(cluster),
                )
            )

        # Sort by count descending
        results.sort(key=lambda t: t.count, reverse=True)
        return results

    def find_similar_messages(
        self,
        user_id: str,
        query: str,
        messages: list[dict[str, Any]],
        threshold: float = 0.7,
        limit: int = 5,
    ) -> list[SimilarMessage]:
        """Find messages semantically similar to a query.

        Args:
            user_id: User ID for embedding cache scoping
            query: Search query string
            messages: List of message dicts with content, timestamp, conversation_id
            threshold: Minimum similarity to include (0.0-1.0)
            limit: Maximum results to return

        Returns:
            List of SimilarMessage instances sorted by similarity descending
        """
        if not query.strip() or not messages:
            return []

        # Get embeddings for existing messages (from cache where available)
        messages_with_embeddings = self._get_embeddings_with_cache(user_id, messages)
        if not messages_with_embeddings:
            return []

        # Embed the query
        try:
            query_embeddings = generate_embeddings_batch([query], input_type="query")
            if not query_embeddings or not query_embeddings[0]:
                logger.warning("Failed to generate query embedding")
                return []
            query_embedding = query_embeddings[0]
        except Exception as e:
            logger.warning(f"Failed to embed query: {e}")
            return []

        # Compute similarities
        results: list[SimilarMessage] = []
        for msg, embedding in messages_with_embeddings:
            similarity = cosine_similarity(query_embedding, embedding)
            if similarity >= threshold:
                content = msg.get("content", "")
                preview = content[:100] + "..." if len(content) > 100 else content
                results.append(
                    SimilarMessage(
                        conversation_id=msg.get("conversation_id", ""),
                        content=content,
                        preview=preview,
                        similarity=similarity,
                        timestamp=msg.get("timestamp", ""),
                    )
                )

        # Sort by similarity descending and limit
        results.sort(key=lambda m: m.similarity, reverse=True)
        return results[:limit]


# Module-level singleton
_topic_detector: TopicDetector | None = None


def get_topic_detector() -> TopicDetector:
    """Get or create the topic detector singleton."""
    global _topic_detector
    if _topic_detector is None:
        _topic_detector = TopicDetector()
    return _topic_detector
