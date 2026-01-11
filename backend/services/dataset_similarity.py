"""Dataset similarity service using semantic embeddings.

Finds datasets with similar content by comparing embeddings of
dataset metadata (name, description, columns, insights).
"""

import json
import logging
from dataclasses import dataclass

from bo1.llm.embeddings import cosine_similarity, generate_embeddings_batch
from bo1.state.redis_manager import RedisManager
from bo1.state.repositories.dataset_repository import DatasetRepository

logger = logging.getLogger(__name__)

# Redis key prefixes
EMBEDDING_CACHE_PREFIX = "dataset_embedding"

# Cache TTL - 7 days
EMBEDDING_CACHE_TTL = 86400 * 7

# Maximum columns to include in embedding text (to stay within token limits)
MAX_COLUMNS_FOR_EMBEDDING = 50


@dataclass
class SimilarDataset:
    """A dataset similar to the query dataset."""

    dataset_id: str
    name: str
    similarity: float
    shared_columns: list[str]
    insight_preview: str | None


class DatasetSimilarityService:
    """Find semantically similar datasets using embeddings.

    Uses Voyage AI embeddings to compare dataset metadata text.
    Caches embeddings in Redis for 7 days.
    """

    def __init__(
        self,
        redis_manager: RedisManager | None = None,
        dataset_repo: DatasetRepository | None = None,
    ) -> None:
        """Initialize similarity service.

        Args:
            redis_manager: Optional Redis manager instance
            dataset_repo: Optional dataset repository instance
        """
        self._redis = redis_manager or RedisManager()
        self._repo = dataset_repo or DatasetRepository()

    def _embedding_cache_key(self, dataset_id: str) -> str:
        """Generate cache key for dataset embedding."""
        return f"{EMBEDDING_CACHE_PREFIX}:{dataset_id}"

    def _get_cached_embedding(self, dataset_id: str) -> list[float] | None:
        """Get cached embedding for a dataset."""
        key = self._embedding_cache_key(dataset_id)
        data = self._redis.client.get(key)
        if data:
            return json.loads(data)
        return None

    def _cache_embedding(self, dataset_id: str, embedding: list[float]) -> None:
        """Cache embedding for a dataset."""
        key = self._embedding_cache_key(dataset_id)
        self._redis.client.setex(key, EMBEDDING_CACHE_TTL, json.dumps(embedding))

    def _build_dataset_text(
        self,
        dataset: dict,
        profiles: list[dict] | None = None,
        insights: list[dict] | None = None,
    ) -> str:
        """Build text representation for embedding.

        Concatenates:
        - Dataset name
        - Description (if present)
        - Column names (truncated to MAX_COLUMNS_FOR_EMBEDDING)
        - Recent insights (if present)

        Args:
            dataset: Dataset dict from repository
            profiles: Optional column profiles
            insights: Optional insights list

        Returns:
            Concatenated text for embedding
        """
        parts: list[str] = []

        # Name
        parts.append(f"Dataset: {dataset.get('name', 'Untitled')}")

        # Description
        desc = dataset.get("description")
        if desc:
            parts.append(f"Description: {desc}")

        # Summary
        summary = dataset.get("summary")
        if summary:
            parts.append(f"Summary: {summary}")

        # Column names from profiles
        if profiles:
            column_names = [p.get("column_name", "") for p in profiles[:MAX_COLUMNS_FOR_EMBEDDING]]
            if column_names:
                parts.append(f"Columns: {', '.join(column_names)}")

        # Insights preview
        if insights:
            insight_texts = []
            for ins in insights[:5]:  # First 5 insights
                text = ins.get("text") or ins.get("title") or ins.get("insight")
                if text:
                    insight_texts.append(text)
            if insight_texts:
                parts.append(f"Insights: {' '.join(insight_texts)}")

        return "\n".join(parts)

    def _get_dataset_embedding(
        self,
        dataset_id: str,
        dataset: dict,
        profiles: list[dict] | None = None,
        insights: list[dict] | None = None,
    ) -> list[float] | None:
        """Get embedding for a dataset, using cache if available.

        Args:
            dataset_id: Dataset UUID
            dataset: Dataset dict
            profiles: Optional column profiles
            insights: Optional insights

        Returns:
            Embedding vector or None if generation fails
        """
        # Check cache first
        cached = self._get_cached_embedding(dataset_id)
        if cached:
            return cached

        # Build text and generate embedding
        text = self._build_dataset_text(dataset, profiles, insights)
        if not text.strip():
            logger.warning(f"Empty text for dataset {dataset_id}, skipping embedding")
            return None

        try:
            embeddings = generate_embeddings_batch([text], input_type="document")
            if embeddings and embeddings[0]:
                embedding = embeddings[0]
                self._cache_embedding(dataset_id, embedding)
                return embedding
        except Exception as e:
            logger.warning(f"Failed to generate embedding for dataset {dataset_id}: {e}")

        return None

    def _get_shared_columns(
        self,
        source_profiles: list[dict],
        target_profiles: list[dict],
    ) -> list[str]:
        """Find column names that exist in both datasets.

        Args:
            source_profiles: Profiles of source dataset
            target_profiles: Profiles of target dataset

        Returns:
            List of shared column names
        """
        source_cols = {p.get("column_name", "").lower() for p in source_profiles}
        target_cols = {p.get("column_name", "").lower() for p in target_profiles}

        shared = source_cols & target_cols
        # Return original case from target
        return [
            p.get("column_name", "")
            for p in target_profiles
            if p.get("column_name", "").lower() in shared
        ]

    def find_similar_datasets(
        self,
        user_id: str,
        dataset_id: str,
        threshold: float = 0.6,
        limit: int = 5,
    ) -> list[SimilarDataset]:
        """Find datasets similar to the given dataset.

        Args:
            user_id: User ID to scope search
            dataset_id: Source dataset UUID
            threshold: Minimum similarity score (0.0-1.0)
            limit: Maximum results to return

        Returns:
            List of SimilarDataset sorted by similarity descending
        """
        # Get source dataset
        source_dataset = self._repo.get_by_id(dataset_id, user_id)
        if not source_dataset:
            logger.warning(f"Source dataset {dataset_id} not found for user {user_id}")
            return []

        source_profiles = self._repo.get_profiles(dataset_id)

        # Get source embedding
        source_embedding = self._get_dataset_embedding(
            dataset_id,
            source_dataset,
            source_profiles,
        )
        if not source_embedding:
            logger.warning(f"Could not generate embedding for source dataset {dataset_id}")
            return []

        # Get all user datasets
        all_datasets, _ = self._repo.list_by_user(user_id, limit=200)

        results: list[SimilarDataset] = []
        for dataset in all_datasets:
            # Skip source dataset
            if dataset["id"] == dataset_id:
                continue

            # Get profiles for target
            target_profiles = self._repo.get_profiles(dataset["id"])

            # Get or generate embedding for target
            target_embedding = self._get_dataset_embedding(
                dataset["id"],
                dataset,
                target_profiles,
            )
            if not target_embedding:
                continue

            # Calculate similarity
            similarity = cosine_similarity(source_embedding, target_embedding)
            if similarity < threshold:
                continue

            # Get shared columns
            shared_columns = self._get_shared_columns(source_profiles, target_profiles)

            # Get insight preview (summary or first insight)
            insight_preview = dataset.get("summary")

            results.append(
                SimilarDataset(
                    dataset_id=dataset["id"],
                    name=dataset.get("name", "Untitled"),
                    similarity=round(similarity, 3),
                    shared_columns=shared_columns[:10],  # Limit to 10
                    insight_preview=insight_preview[:200] if insight_preview else None,
                )
            )

        # Sort by similarity descending and limit
        results.sort(key=lambda x: x.similarity, reverse=True)
        return results[:limit]

    def invalidate_cache(self, dataset_id: str) -> bool:
        """Invalidate cached embedding for a dataset.

        Call when dataset metadata changes significantly.

        Args:
            dataset_id: Dataset UUID

        Returns:
            True if cache was invalidated
        """
        key = self._embedding_cache_key(dataset_id)
        return bool(self._redis.client.delete(key))


# Module-level singleton
_similarity_service: DatasetSimilarityService | None = None


def get_similarity_service() -> DatasetSimilarityService:
    """Get or create the similarity service singleton."""
    global _similarity_service
    if _similarity_service is None:
        _similarity_service = DatasetSimilarityService()
    return _similarity_service
