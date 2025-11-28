"""Voyage AI embeddings for semantic similarity and research caching.

Uses Voyage AI's voyage-3 model (1024 dimensions) for:
- Semantic similarity search in research cache
- Question matching with cosine similarity
- Cost: ~$0.00006 per 1K tokens (10x cheaper than OpenAI ada-002)

Includes retry logic with exponential backoff for resilience.
"""

import logging
import os
import time
from typing import TYPE_CHECKING, Any

from bo1.constants import EmbeddingsConfig

if TYPE_CHECKING:
    import voyageai
else:
    try:
        import voyageai
    except ImportError:
        voyageai = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# Retry configuration - imported from constants for backward compatibility
EMBEDDING_MAX_RETRIES = EmbeddingsConfig.MAX_RETRIES
EMBEDDING_INITIAL_DELAY = EmbeddingsConfig.INITIAL_DELAY
EMBEDDING_BACKOFF_FACTOR = EmbeddingsConfig.BACKOFF_FACTOR
EMBEDDING_REQUEST_TIMEOUT = EmbeddingsConfig.REQUEST_TIMEOUT


def _call_voyage_api_with_retry(
    client: Any,
    text: str,
    model: str,
    input_type: str | None,
) -> list[float]:
    """Call Voyage AI API with retry logic.

    Args:
        client: Voyage AI client
        text: Text to embed
        model: Model name
        input_type: Query or document type

    Returns:
        Embedding vector

    Raises:
        Exception: If all retries exhausted
    """
    last_exception: Exception | None = None
    delay = EMBEDDING_INITIAL_DELAY

    for attempt in range(EMBEDDING_MAX_RETRIES + 1):
        try:
            result = client.embed(
                texts=[text.strip()],
                model=model,
                input_type=input_type,
            )
            # Convert to list[float] to satisfy type checker
            embedding = [float(x) for x in result.embeddings[0]]

            if attempt > 0:
                logger.info(f"Voyage AI embedding succeeded on attempt {attempt + 1}")

            return embedding

        except Exception as e:
            last_exception = e
            error_type = type(e).__name__

            # Check if this is a rate limit error (retry)
            is_rate_limit = "rate" in str(e).lower() or "429" in str(e)
            # Check if this is a server error (retry)
            is_server_error = "500" in str(e) or "502" in str(e) or "503" in str(e)

            if attempt < EMBEDDING_MAX_RETRIES and (is_rate_limit or is_server_error):
                logger.warning(
                    f"Voyage AI embedding attempt {attempt + 1}/{EMBEDDING_MAX_RETRIES + 1} "
                    f"failed ({error_type}): {e}. Retrying in {delay:.1f}s..."
                )
                time.sleep(delay)
                delay *= EMBEDDING_BACKOFF_FACTOR
            else:
                # Non-retryable error or max retries reached
                if attempt > 0:
                    logger.error(f"Voyage AI embedding failed after {attempt + 1} attempts: {e}")
                break

    raise Exception(
        f"Failed to generate embedding after {EMBEDDING_MAX_RETRIES + 1} attempts"
    ) from last_exception


def generate_embedding(
    text: str,
    model: str = "voyage-3",
    input_type: str | None = None,
) -> list[float]:
    """Generate embedding vector for text.

    Args:
        text: Input text to embed
        model: Voyage AI embedding model (default: voyage-3)
        input_type: Optional - 'query' or 'document' for optimized retrieval

    Returns:
        Embedding vector (1024 dimensions for voyage-3)

    Raises:
        ValueError: If text is empty or API key is missing
        Exception: If API call fails after retries
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError(
            "VOYAGE_API_KEY environment variable not set. "
            "Set VOYAGE_API_KEY in .env or as environment variable to use embeddings."
        )

    if voyageai is None:
        raise ImportError("voyageai package is not installed. Install with: pip install voyageai")

    # mypy doesn't know about voyageai.Client, but it exists at runtime
    client = voyageai.Client(api_key=api_key)  # type: ignore[attr-defined]

    return _call_voyage_api_with_retry(client, text, model, input_type)


def cosine_similarity(vec1: list[float], vec2: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        vec1: First embedding vector
        vec2: Second embedding vector

    Returns:
        Cosine similarity score (0.0-1.0, higher = more similar)

    Raises:
        ValueError: If vectors have different dimensions
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"Vectors must have same dimensions (got {len(vec1)} and {len(vec2)})")

    # Dot product
    dot_product = sum(a * b for a, b in zip(vec1, vec2, strict=True))

    # Magnitudes
    magnitude1 = sum(a * a for a in vec1) ** 0.5
    magnitude2 = sum(b * b for b in vec2) ** 0.5

    # Avoid division by zero
    if magnitude1 == 0 or magnitude2 == 0:
        return 0.0

    similarity: float = dot_product / (magnitude1 * magnitude2)
    return similarity


def find_most_similar(
    query_embedding: list[float],
    candidate_embeddings: list[tuple[Any, list[float]]],
    threshold: float = 0.85,
) -> tuple[Any, float] | None:
    """Find most similar candidate to query embedding.

    Args:
        query_embedding: Query vector
        candidate_embeddings: List of (metadata, embedding) tuples
        threshold: Minimum similarity threshold (0.0-1.0)

    Returns:
        Tuple of (metadata, similarity_score) or None if no match above threshold
    """
    best_match = None
    best_score = threshold

    for metadata, embedding in candidate_embeddings:
        score = cosine_similarity(query_embedding, embedding)
        if score > best_score:
            best_score = score
            best_match = (metadata, score)

    return best_match
