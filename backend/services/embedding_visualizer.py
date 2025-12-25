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

# UMAP is lazy-loaded to avoid 7s import overhead at startup
# Only loaded when UMAP method is explicitly requested
_umap_module: Any = None
_umap_check_done: bool = False


def _get_umap() -> Any:
    """Lazy-load UMAP module on first use."""
    global _umap_module, _umap_check_done
    if not _umap_check_done:
        _umap_check_done = True
        try:
            import umap as _umap

            _umap_module = _umap
            logger.info("umap-learn loaded for dimensionality reduction")
        except ImportError:
            logger.info("umap-learn not available, using PCA for dimensionality reduction")
    return _umap_module


def is_umap_available() -> bool:
    """Check if UMAP is available (triggers lazy load)."""
    return _get_umap() is not None


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

    umap_mod = _get_umap()
    if method == "umap" and umap_mod is not None and len(embeddings) >= 3:
        # UMAP for better cluster preservation (needs at least 3 samples)
        reducer = umap_mod.UMAP(
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
        "umap_available": is_umap_available(),
    }


def get_distinct_categories() -> list[dict[str, Any]]:
    """Get distinct research cache categories with counts.

    Returns:
        List of dicts with 'category' and 'count'
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT category, COUNT(*) as count
                FROM research_cache
                WHERE question_embedding IS NOT NULL AND category IS NOT NULL
                GROUP BY category
                ORDER BY count DESC
                """
            )
            return [{"category": row["category"], "count": row["count"]} for row in cur.fetchall()]


def get_sample_embeddings(
    embedding_type: str = "all",
    limit: int = 500,
    category: str | None = None,
) -> list[dict[str, Any]]:
    """Retrieve sample embeddings with metadata for visualization.

    Args:
        embedding_type: 'contributions', 'research', 'context', or 'all'
        limit: Maximum samples to return
        category: Filter research embeddings by category (e.g., 'saas_metrics', 'pricing')

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
                if category:
                    cur.execute(
                        """
                        SELECT
                            question_embedding::text AS embedding,
                            'research' AS type,
                            LEFT(question, 100) AS preview,
                            category,
                            industry,
                            research_date::text AS created_at
                        FROM research_cache
                        WHERE question_embedding IS NOT NULL AND category = %s
                        ORDER BY research_date DESC
                        LIMIT %s
                        """,
                        (category, per_type_limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT
                            question_embedding::text AS embedding,
                            'research' AS type,
                            LEFT(question, 100) AS preview,
                            category,
                            industry,
                            research_date::text AS created_at
                        FROM research_cache
                        WHERE question_embedding IS NOT NULL
                        ORDER BY research_date DESC
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


def compute_clusters(
    coords: list[tuple[float, float]],
    min_k: int = 2,
    max_k: int = 8,
) -> tuple[list[int], list[tuple[float, float]]]:
    """Compute K-means clusters on 2D coordinates with automatic k selection.

    Uses silhouette score to pick optimal k between min_k and max_k.

    Args:
        coords: List of (x, y) coordinate pairs
        min_k: Minimum number of clusters
        max_k: Maximum number of clusters

    Returns:
        Tuple of (cluster_assignments, centroids)
        - cluster_assignments: List of cluster IDs (0-indexed) for each point
        - centroids: List of (x, y) centroid coordinates for each cluster
    """
    from sklearn.cluster import KMeans
    from sklearn.metrics import silhouette_score

    n_points = len(coords)
    if n_points < 20:
        # Too few points for meaningful clustering
        return [0] * n_points, [(0.0, 0.0)]

    arr = np.array(coords, dtype=np.float32)

    # Clamp k range to available points
    max_k = min(max_k, n_points - 1)
    if min_k > max_k:
        min_k = max_k

    best_k = min_k
    best_score = -1.0
    best_labels: list[int] = []
    best_centroids: list[tuple[float, float]] = []

    for k in range(min_k, max_k + 1):
        km = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = km.fit_predict(arr)
        score = silhouette_score(arr, labels)
        if score > best_score:
            best_score = score
            best_k = k
            best_labels = labels.tolist()
            best_centroids = [(float(c[0]), float(c[1])) for c in km.cluster_centers_]

    logger.info(f"K-means: selected k={best_k} with silhouette={best_score:.3f}")
    return best_labels, best_centroids


def generate_cluster_labels(
    cluster_assignments: list[int],
    previews: list[str],
    centroids: list[tuple[float, float]],
    coords: list[tuple[float, float]],
) -> dict[int, str]:
    """Generate human-readable labels for clusters based on text previews.

    For each cluster, finds the points closest to centroid and extracts common patterns.

    Args:
        cluster_assignments: Cluster ID for each point
        previews: Text preview for each point
        centroids: (x, y) centroid for each cluster
        coords: (x, y) coordinates for each point

    Returns:
        Dict mapping cluster_id to label string
    """
    from collections import Counter

    n_clusters = len(centroids)
    labels: dict[int, str] = {}

    for cluster_id in range(n_clusters):
        # Find points in this cluster
        cluster_indices = [i for i, c in enumerate(cluster_assignments) if c == cluster_id]
        if not cluster_indices:
            labels[cluster_id] = f"Cluster {cluster_id + 1}"
            continue

        # Sort by distance to centroid
        cx, cy = centroids[cluster_id]
        distances = [
            (i, (coords[i][0] - cx) ** 2 + (coords[i][1] - cy) ** 2) for i in cluster_indices
        ]
        distances.sort(key=lambda x: x[1])

        # Take 5 closest points
        sample_indices = [d[0] for d in distances[:5]]
        sample_texts = [previews[i] for i in sample_indices]

        # Extract 2-word ngrams and find most common
        ngrams: list[str] = []
        for text in sample_texts:
            words = text.lower().split()[:10]  # First 10 words
            for i in range(len(words) - 1):
                ngram = f"{words[i]} {words[i + 1]}"
                # Filter out common stopwords
                if not any(w in ngram for w in ["the ", " the", "to ", " to", " a ", "of ", " of"]):
                    ngrams.append(ngram)

        if ngrams:
            most_common = Counter(ngrams).most_common(1)
            if most_common and most_common[0][1] >= 2:
                labels[cluster_id] = most_common[0][0].title()
            else:
                # Fall back to first 20 chars of centroid's preview
                labels[cluster_id] = previews[sample_indices[0]][:20].strip() + "..."
        else:
            labels[cluster_id] = f"Cluster {cluster_id + 1}"

    return labels
