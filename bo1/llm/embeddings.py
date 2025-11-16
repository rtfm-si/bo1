"""OpenAI embeddings for semantic similarity and research caching.

Uses OpenAI's text-embedding-ada-002 model (1536 dimensions) for:
- Semantic similarity search in research cache
- Question matching with cosine similarity
- Cost: ~$0.0001 per 1K tokens (~750 words)
"""

import os
from typing import Any

from openai import OpenAI


def generate_embedding(
    text: str,
    model: str = "text-embedding-ada-002",
) -> list[float]:
    """Generate embedding vector for text.

    Args:
        text: Input text to embed
        model: OpenAI embedding model (default: ada-002)

    Returns:
        Embedding vector (1536 dimensions for ada-002)

    Raises:
        ValueError: If text is empty or API key is missing
        Exception: If API call fails
    """
    if not text or not text.strip():
        raise ValueError("Text cannot be empty")

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    client = OpenAI(api_key=api_key)

    try:
        response = client.embeddings.create(
            input=text.strip(),
            model=model,
        )
        embedding: list[float] = response.data[0].embedding
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
