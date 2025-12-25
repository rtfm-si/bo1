# Plan: Embeddings Graph Improvements - Category Filtering & Clustering

## Summary

- Add category filter for research embeddings (by category field: saas_metrics, pricing, etc.)
- Implement K-means clustering on 2D projections with automatic label generation
- Display cluster labels in visualization for semantic grouping insight

## Implementation Steps

1. **Extend `/embeddings/sample` endpoint** (`backend/api/admin/embeddings.py`)
   - Add `category: str | None` query parameter to filter research embeddings
   - Pass to `get_sample_embeddings()` for DB-level filtering

2. **Update `get_sample_embeddings()`** (`backend/services/embedding_visualizer.py`)
   - Add `category: str | None` parameter
   - Filter research_cache query: `WHERE category = %s` when provided
   - Return distinct categories in stats for UI dropdown population

3. **Add category stats endpoint** (`backend/api/admin/embeddings.py`)
   - `GET /embeddings/categories` - returns list of distinct categories with counts
   - For populating filter dropdown in UI

4. **Implement clustering** (`backend/services/embedding_visualizer.py`)
   - Add `compute_clusters()` function using sklearn K-means
   - Input: 2D coordinates from `reduce_dimensions()`
   - Auto-determine k using silhouette score (2-8 clusters, pick best)
   - Return cluster assignments for each point

5. **Generate cluster labels** (`backend/services/embedding_visualizer.py`)
   - Add `generate_cluster_labels()` function
   - For each cluster: find centroid, sample 3-5 nearest text previews
   - Use simple heuristic: most common 2-word ngram or first 20 chars of centroid's preview
   - Return `{cluster_id: label}` mapping

6. **Extend response models** (`backend/api/admin/embeddings.py`)
   - Add `cluster_id: int` to `EmbeddingPoint`
   - Add `clusters: list[ClusterInfo]` to `EmbeddingSampleResponse`
   - `ClusterInfo`: `{id: int, label: str, count: int, centroid: {x, y}}`

7. **Update cache key** (`backend/api/admin/embeddings.py`)
   - Include category in cache key: `admin:embeddings:sample:{type}:{category}:{limit}:{method}`

## Tests

- Unit tests:
  - `tests/services/test_embedding_visualizer.py`: test `compute_clusters()` returns valid assignments
  - `tests/services/test_embedding_visualizer.py`: test `generate_cluster_labels()` returns labels for each cluster
  - `tests/api/admin/test_embeddings.py`: test category filter returns only matching embeddings

- Integration tests:
  - Test `/embeddings/sample?category=saas_metrics` returns only saas_metrics research
  - Test cluster labels appear in response when embeddings > 10

- Manual validation:
  - Verify category dropdown populates from available categories
  - Verify cluster visualization shows labeled groups
  - Verify filtering by category updates cluster assignments

## Dependencies & Risks

- Dependencies:
  - sklearn already installed (used for PCA)
  - Existing embedding visualization infrastructure

- Risks:
  - K-means may produce poor clusters on small datasets (<20 points) - mitigate: skip clustering if n < 20
  - Label generation may be uninformative - mitigate: fall back to "Cluster N" if no clear pattern
