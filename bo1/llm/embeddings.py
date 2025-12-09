"""Voyage AI embeddings for semantic similarity and research caching.

Uses Voyage AI's voyage-3 model (1024 dimensions) for:
- Semantic similarity search in research cache
- Question matching with cosine similarity
- Cost: ~$0.00006 per 1K tokens (10x cheaper than OpenAI ada-002)

Includes retry logic with exponential backoff and circuit breaker for resilience.
"""

import logging
import os
import time
from typing import TYPE_CHECKING, Any

from bo1.constants import EmbeddingsConfig
from bo1.llm.circuit_breaker import (
    CircuitBreakerOpenError,
    get_service_circuit_breaker,
)
from bo1.llm.context import get_cost_context
from bo1.llm.cost_tracker import CostTracker

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
    """Call Voyage AI API with retry logic and cost tracking.

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
    # Get cost context for attribution
    ctx = get_cost_context()

    # Start cost tracking
    with CostTracker.track_call(
        provider="voyage",
        operation_type="embedding",
        model_name=model,
        session_id=ctx.get("session_id"),
        user_id=ctx.get("user_id"),
        node_name=ctx.get("node_name"),
        phase=ctx.get("phase"),
        persona_name=ctx.get("persona_name"),
        round_number=ctx.get("round_number"),
        sub_problem_index=ctx.get("sub_problem_index"),
    ) as cost_record:
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

                # Estimate tokens (Voyage doesn't return token count)
                # Approximation: ~1.3 tokens per word
                cost_record.input_tokens = int(len(text.split()) * 1.3)

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
                        logger.error(
                            f"Voyage AI embedding failed after {attempt + 1} attempts: {e}"
                        )
                    break

        raise Exception(
            f"Failed to generate embedding after {EMBEDDING_MAX_RETRIES + 1} attempts"
        ) from last_exception


def _call_voyage_batch_api_with_retry(
    client: Any,
    texts: list[str],
    model: str,
    input_type: str | None,
) -> list[list[float]]:
    """Call Voyage AI batch API with retry logic and cost tracking.

    Args:
        client: Voyage AI client
        texts: List of texts to embed
        model: Model name
        input_type: Query or document type

    Returns:
        List of embedding vectors in same order as input

    Raises:
        Exception: If all retries exhausted
    """
    if not texts:
        return []

    # Get cost context for attribution
    ctx = get_cost_context()

    # Start cost tracking
    with CostTracker.track_call(
        provider="voyage",
        operation_type="embedding_batch",
        model_name=model,
        session_id=ctx.get("session_id"),
        user_id=ctx.get("user_id"),
        node_name=ctx.get("node_name"),
        phase=ctx.get("phase"),
        persona_name=ctx.get("persona_name"),
        round_number=ctx.get("round_number"),
        sub_problem_index=ctx.get("sub_problem_index"),
    ) as cost_record:
        last_exception: Exception | None = None
        delay = EMBEDDING_INITIAL_DELAY

        for attempt in range(EMBEDDING_MAX_RETRIES + 1):
            try:
                # Single API call for all texts
                result = client.embed(
                    texts=[t.strip() for t in texts],
                    model=model,
                    input_type=input_type,
                )
                # Convert all embeddings to list[float]
                embeddings = [[float(x) for x in emb] for emb in result.embeddings]

                # Estimate tokens for all texts
                total_words = sum(len(t.split()) for t in texts)
                cost_record.input_tokens = int(total_words * 1.3)

                if attempt > 0:
                    logger.info(f"Voyage AI batch embedding succeeded on attempt {attempt + 1}")

                logger.debug(f"Batch embedding: {len(texts)} texts in single API call")

                return embeddings

            except Exception as e:
                last_exception = e
                error_type = type(e).__name__

                is_rate_limit = "rate" in str(e).lower() or "429" in str(e)
                is_server_error = "500" in str(e) or "502" in str(e) or "503" in str(e)

                if attempt < EMBEDDING_MAX_RETRIES and (is_rate_limit or is_server_error):
                    logger.warning(
                        f"Voyage AI batch embedding attempt {attempt + 1}/{EMBEDDING_MAX_RETRIES + 1} "
                        f"failed ({error_type}): {e}. Retrying in {delay:.1f}s..."
                    )
                    time.sleep(delay)
                    delay *= EMBEDDING_BACKOFF_FACTOR
                else:
                    if attempt > 0:
                        logger.error(
                            f"Voyage AI batch embedding failed after {attempt + 1} attempts: {e}"
                        )
                    break

        raise Exception(
            f"Failed to generate batch embeddings after {EMBEDDING_MAX_RETRIES + 1} attempts"
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
        CircuitBreakerOpenError: If Voyage API circuit breaker is open
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

    # Check circuit breaker before making API call
    breaker = get_service_circuit_breaker("voyage")
    if breaker.state.value == "open":
        logger.warning("Voyage circuit breaker is OPEN - fast-failing embedding request")
        raise CircuitBreakerOpenError(
            "Voyage AI service unavailable (circuit breaker open). Embedding request rejected."
        )

    # mypy doesn't know about voyageai.Client, but it exists at runtime
    client = voyageai.Client(api_key=api_key)  # type: ignore[attr-defined]

    try:
        result: list[float] = breaker.call_sync(
            _call_voyage_api_with_retry, client, text, model, input_type
        )
        return result
    except CircuitBreakerOpenError:
        raise
    except Exception:
        # The retry logic inside _call_voyage_api_with_retry handles retries
        # Circuit breaker records the failure
        raise


def generate_embeddings_batch(
    texts: list[str],
    model: str = "voyage-3",
    input_type: str | None = None,
) -> list[list[float]]:
    """Generate embedding vectors for multiple texts in a single API call.

    More efficient than calling generate_embedding() multiple times - saves
    API overhead and reduces costs by batching.

    Args:
        texts: List of input texts to embed
        model: Voyage AI embedding model (default: voyage-3)
        input_type: Optional - 'query' or 'document' for optimized retrieval

    Returns:
        List of embedding vectors (1024 dimensions each for voyage-3)
        in same order as input texts

    Raises:
        ValueError: If texts is empty or API key is missing
        CircuitBreakerOpenError: If Voyage API circuit breaker is open
        Exception: If API call fails after retries

    Example:
        >>> embeddings = generate_embeddings_batch(
        ...     ["Focus on UX", "Revenue is key", "User experience matters"],
        ...     input_type="document"
        ... )
        >>> len(embeddings)  # 3 embeddings
        3
    """
    if not texts:
        return []

    # Filter out empty texts and track original indices
    valid_texts = []
    valid_indices = []
    for i, text in enumerate(texts):
        if text and text.strip():
            valid_texts.append(text)
            valid_indices.append(i)

    if not valid_texts:
        logger.warning("All texts were empty, returning empty embeddings")
        return [[] for _ in texts]

    api_key = os.getenv("VOYAGE_API_KEY")
    if not api_key or not api_key.strip():
        raise ValueError(
            "VOYAGE_API_KEY environment variable not set. "
            "Set VOYAGE_API_KEY in .env or as environment variable to use embeddings."
        )

    if voyageai is None:
        raise ImportError("voyageai package is not installed. Install with: pip install voyageai")

    # Check circuit breaker before making API call
    breaker = get_service_circuit_breaker("voyage")
    if breaker.state.value == "open":
        logger.warning("Voyage circuit breaker is OPEN - fast-failing batch embedding request")
        raise CircuitBreakerOpenError(
            "Voyage AI service unavailable (circuit breaker open). Batch embedding request rejected."
        )

    client = voyageai.Client(api_key=api_key)  # type: ignore[attr-defined]

    try:
        valid_embeddings: list[list[float]] = breaker.call_sync(
            _call_voyage_batch_api_with_retry, client, valid_texts, model, input_type
        )

        # Reconstruct full result list with empty embeddings for empty texts
        result: list[list[float]] = [[] for _ in texts]
        for idx, emb in zip(valid_indices, valid_embeddings, strict=True):
            result[idx] = emb

        return result
    except CircuitBreakerOpenError:
        raise
    except Exception:
        raise


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
