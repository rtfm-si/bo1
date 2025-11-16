"""Voyage AI embeddings for semantic similarity and research caching.

Uses Voyage AI's voyage-3 model (1024 dimensions) for:
- Semantic similarity search in research cache
- Question matching with cosine similarity
- Cost: ~$0.00006 per 1K tokens (10x cheaper than OpenAI ada-002)
"""

import os
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import voyageai
else:
    try:
        import voyageai
    except ImportError:
        voyageai = None  # type: ignore[assignment]


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
        Exception: If API call fails
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    api_key = os.getenv("VOYAGEAI_API_KEY")
    if not api_key:
        raise ValueError("VOYAGEAI_API_KEY environment variable not set")

    if voyageai is None:
        raise ImportError("voyageai package is not installed. Install with: pip install voyageai")

    # voyageai does not explicitly export Client in stubs, but it exists at runtime
    client = voyageai.Client(api_key=api_key)  # type: ignore[attr-defined]

    try:
        # Voyage AI accepts single string or list of strings
        result = client.embed(
            texts=[text.strip()],
            model=model,
            input_type=input_type,
        )
        # Convert to list[float] to satisfy type checker
        embedding = [float(x) for x in result.embeddings[0]]
        return embedding
    except Exception as e:
        raise Exception(f"Failed to generate embedding: {e}") from e


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
