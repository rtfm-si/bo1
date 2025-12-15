"""Embedding visualization service for admin dashboard.

Provides:
- Dimensionality reduction (PCA with UMAP fallback)
- Sample embedding retrieval with metadata
- Cluster statistics computation
"""

import logging
from typing import Any

import numpy as np
from sklearn.decomposition import PCA

from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# UMAP optional - falls back to PCA
try:
    import umap

    UMAP_AVAILABLE = True
except ImportError:
    UMAP_AVAILABLE = False
    logger.info("umap-learn not available, using PCA for dimensionality reduction")


def reduce_dimensions(
    embeddings: list[list[float]],
    method: str = "pca",
    n_components: int = 2,
) -> list[list[float]]:
    """Reduce high-dimensional embeddings to 2D for visualization.

    Args:
        embeddings: List of embedding vectors (e.g., 1024-dim)
        method: 'pca' or 'umap' (falls back to PCA if UMAP unavailable)
        n_components: Target dimensions (default 2)

    Returns:
        List of 2D coordinate pairs [[x1, y1], [x2, y2], ...]
    """
    if not embeddings:
        return []

    arr = np.array(embeddings, dtype=np.float32)

    # Edge case: not enough samples for n_components
    if arr.shape[0] < n_components:
        # Pad output to n_components with zeros
        result = []
        for i in range(arr.shape[0]):
            point = [0.0] * n_components
            point[0] = float(i)  # Spread points on x-axis
            result.append(point)
        return result

    if method == "umap" and UMAP_AVAILABLE and len(embeddings) >= 3:
        # UMAP for better cluster preservation (needs at least 3 samples)
        reducer = umap.UMAP(
            n_components=n_components,
            n_neighbors=min(15, len(embeddings) - 1),
            min_dist=0.1,
            metric="cosine",
            random_state=42,
        )
        reduced = reducer.fit_transform(arr)
    else:
        # PCA fallback - fast and deterministic
        n_comp = min(n_components, arr.shape[0], arr.shape[1])
        pca = PCA(n_components=n_comp, random_state=42)
        reduced = pca.fit_transform(arr)
        # Ensure output has n_components columns (pad if needed)
        if reduced.shape[1] < n_components:
            padding = np.zeros((reduced.shape[0], n_components - reduced.shape[1]))
            reduced = np.hstack([reduced, padding])

    return reduced.tolist()


def get_embedding_stats() -> dict[str, Any]:
    """Get statistics about stored embeddings.

    Returns:
        Dict with counts by type, total dimensions, storage estimates
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Count contributions with embeddings
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM contributions
                WHERE embedding IS NOT NULL
                """
            )
            contribution_count = cur.fetchone()["count"]

            # Count research cache embeddings
            cur.execute(
                """
                SELECT COUNT(*) AS count
                FROM research_cache
                WHERE question_embedding IS NOT NULL
                """
            )
            research_count = cur.fetchone()["count"]

            # Check for context chunks table
            cur.execute(
                """
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'context_chunks'
                )
                """
            )
            has_context = cur.fetchone()["exists"]

            context_count = 0
            if has_context:
                cur.execute(
                    """
                    SELECT COUNT(*) AS count
                    FROM context_chunks
                    WHERE embedding IS NOT NULL
                    """
                )
                context_count = cur.fetchone()["count"]

    total = contribution_count + research_count + context_count
    # Storage estimate: 1024 dims * 4 bytes * count
    storage_mb = (total * 1024 * 4) / (1024 * 1024)

    return {
        "total_embeddings": total,
        "by_type": {
            "contributions": contribution_count,
            "research_cache": research_count,
            "context_chunks": context_count,
        },
        "dimensions": 1024,
        "storage_estimate_mb": round(storage_mb, 2),
        "umap_available": UMAP_AVAILABLE,
    }


def get_sample_embeddings(
    embedding_type: str = "all",
    limit: int = 500,
) -> list[dict[str, Any]]:
    """Retrieve sample embeddings with metadata for visualization.

    Args:
        embedding_type: 'contributions', 'research', 'context', or 'all'
        limit: Maximum samples to return

    Returns:
        List of dicts with 'embedding', 'type', 'preview', 'created_at'
    """
    samples: list[dict[str, Any]] = []
    per_type_limit = limit if embedding_type != "all" else limit // 3

    with db_session() as conn:
        with conn.cursor() as cur:
            # Contributions
            if embedding_type in ("all", "contributions"):
                cur.execute(
                    """
                    SELECT
                        embedding::text AS embedding,
                        'contribution' AS type,
                        LEFT(content, 100) AS preview,
                        persona_code,
                        session_id,
                        created_at::text AS created_at
                    FROM contributions
                    WHERE embedding IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (per_type_limit,),
                )
                for row in cur.fetchall():
                    # Parse embedding from pgvector text format
                    emb_str = row["embedding"]
                    if emb_str and emb_str.startswith("[") and emb_str.endswith("]"):
                        emb = [float(x) for x in emb_str[1:-1].split(",")]
                    else:
                        continue
                    samples.append(
                        {
                            "embedding": emb,
                            "type": "contribution",
                            "preview": row["preview"],
                            "metadata": {
                                "persona": row["persona_code"],
                                "session_id": row["session_id"],
                            },
                            "created_at": row["created_at"],
                        }
                    )

            # Research cache
            if embedding_type in ("all", "research"):
                cur.execute(
                    """
                    SELECT
                        question_embedding::text AS embedding,
                        'research' AS type,
                        LEFT(question, 100) AS preview,
                        category,
                        industry,
                        created_at::text AS created_at
                    FROM research_cache
                    WHERE question_embedding IS NOT NULL
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (per_type_limit,),
                )
                for row in cur.fetchall():
                    emb_str = row["embedding"]
                    if emb_str and emb_str.startswith("[") and emb_str.endswith("]"):
                        emb = [float(x) for x in emb_str[1:-1].split(",")]
                    else:
                        continue
                    samples.append(
                        {
                            "embedding": emb,
                            "type": "research",
                            "preview": row["preview"],
                            "metadata": {
                                "category": row["category"],
                                "industry": row["industry"],
                            },
                            "created_at": row["created_at"],
                        }
                    )

            # Context chunks (if table exists)
            if embedding_type in ("all", "context"):
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'context_chunks'
                    )
                    """
                )
                if cur.fetchone()["exists"]:
                    cur.execute(
                        """
                        SELECT
                            embedding::text AS embedding,
                            'context' AS type,
                            LEFT(content, 100) AS preview,
                            source_type,
                            created_at::text AS created_at
                        FROM context_chunks
                        WHERE embedding IS NOT NULL
                        ORDER BY created_at DESC
                        LIMIT %s
                        """,
                        (per_type_limit,),
                    )
                    for row in cur.fetchall():
                        emb_str = row["embedding"]
                        if emb_str and emb_str.startswith("[") and emb_str.endswith("]"):
                            emb = [float(x) for x in emb_str[1:-1].split(",")]
                        else:
                            continue
                        samples.append(
                            {
                                "embedding": emb,
                                "type": "context",
                                "preview": row["preview"],
                                "metadata": {"source_type": row["source_type"]},
                                "created_at": row["created_at"],
                            }
                        )

    return samples[:limit]


def compute_2d_coordinates(
    samples: list[dict[str, Any]],
    method: str = "pca",
) -> list[dict[str, Any]]:
    """Compute 2D coordinates for sample embeddings.

    Args:
        samples: Output from get_sample_embeddings
        method: 'pca' or 'umap'

    Returns:
        Samples with added 'x' and 'y' fields
    """
    if not samples:
        return []

    embeddings = [s["embedding"] for s in samples]
    coords = reduce_dimensions(embeddings, method=method)

    result = []
    for sample, (x, y) in zip(samples, coords, strict=True):
        result.append(
            {
                "x": float(x),
                "y": float(y),
                "type": sample["type"],
                "preview": sample["preview"],
                "metadata": sample["metadata"],
                "created_at": sample["created_at"],
            }
        )

    return result
