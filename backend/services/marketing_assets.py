"""Marketing Assets Service.

Handles storage and retrieval of marketing collateral (images, animations,
concepts, templates) for AI content generation.

Key features:
- Upload to DO Spaces with CDN URLs
- Tag-based search for asset suggestions
- Keyword matching for article integration
- Tier-gated storage limits
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime

from backend.services.spaces import SpacesClient, SpacesError, get_spaces_client
from bo1.state.database import db_session

logger = logging.getLogger(__name__)

# Allowed file types with size limits
ALLOWED_MIME_TYPES = {
    "image/png": 10 * 1024 * 1024,  # 10MB
    "image/jpeg": 10 * 1024 * 1024,
    "image/gif": 10 * 1024 * 1024,
    "image/webp": 10 * 1024 * 1024,
    "image/svg+xml": 2 * 1024 * 1024,  # 2MB for SVG
    "video/mp4": 50 * 1024 * 1024,  # 50MB for video
    "video/webm": 50 * 1024 * 1024,
}

VALID_ASSET_TYPES = {"image", "animation", "concept", "template"}


class AssetValidationError(Exception):
    """Validation error for asset operations."""

    pass


class AssetStorageError(Exception):
    """Storage error for asset operations."""

    pass


@dataclass
class AssetRecord:
    """Database record for a marketing asset."""

    id: int
    user_id: str
    workspace_id: str | None
    filename: str
    storage_key: str
    cdn_url: str
    asset_type: str
    title: str
    description: str | None
    tags: list[str]
    metadata: dict | None
    file_size: int
    mime_type: str
    created_at: datetime
    updated_at: datetime


def validate_file(
    filename: str,
    mime_type: str,
    file_size: int,
) -> None:
    """Validate file before upload.

    Args:
        filename: Original filename
        mime_type: MIME type
        file_size: Size in bytes

    Raises:
        AssetValidationError: If validation fails
    """
    if mime_type not in ALLOWED_MIME_TYPES:
        allowed = ", ".join(sorted(ALLOWED_MIME_TYPES.keys()))
        raise AssetValidationError(f"File type '{mime_type}' not allowed. Allowed: {allowed}")

    max_size = ALLOWED_MIME_TYPES[mime_type]
    if file_size > max_size:
        max_mb = max_size // (1024 * 1024)
        raise AssetValidationError(f"File too large. Maximum size for {mime_type}: {max_mb}MB")

    if not filename or len(filename) > 255:
        raise AssetValidationError("Invalid filename")


def validate_asset_type(asset_type: str) -> None:
    """Validate asset type.

    Args:
        asset_type: Asset type string

    Raises:
        AssetValidationError: If invalid
    """
    if asset_type not in VALID_ASSET_TYPES:
        valid = ", ".join(sorted(VALID_ASSET_TYPES))
        raise AssetValidationError(f"Invalid asset type '{asset_type}'. Valid: {valid}")


def upload_asset(
    user_id: str,
    workspace_id: str | None,
    filename: str,
    file_data: bytes,
    mime_type: str,
    title: str,
    asset_type: str,
    description: str | None = None,
    tags: list[str] | None = None,
    metadata: dict | None = None,
    spaces_client: SpacesClient | None = None,
) -> AssetRecord:
    """Upload an asset to storage and create database record.

    Args:
        user_id: Owner user ID
        workspace_id: Optional workspace ID
        filename: Original filename
        file_data: File content as bytes
        mime_type: MIME type
        title: User-friendly title
        asset_type: Type (image, animation, concept, template)
        description: Optional description
        tags: Optional list of tags
        metadata: Optional metadata dict
        spaces_client: Optional SpacesClient (for testing)

    Returns:
        AssetRecord with CDN URL

    Raises:
        AssetValidationError: If validation fails
        AssetStorageError: If upload fails
    """
    file_size = len(file_data)

    # Validate inputs
    validate_file(filename, mime_type, file_size)
    validate_asset_type(asset_type)

    if not title or len(title) > 255:
        raise AssetValidationError("Title required, max 255 characters")

    tags = tags or []
    if len(tags) > 20:
        raise AssetValidationError("Maximum 20 tags allowed")

    # Generate unique storage key
    file_ext = filename.rsplit(".", 1)[-1] if "." in filename else ""
    unique_id = uuid.uuid4().hex[:12]
    storage_key = (
        f"marketing/{user_id[:8]}/{unique_id}.{file_ext}"
        if file_ext
        else f"marketing/{user_id[:8]}/{unique_id}"
    )

    # Upload to Spaces
    client = spaces_client or get_spaces_client()
    try:
        cdn_url = client.upload_file(
            key=storage_key,
            data=file_data,
            content_type=mime_type,
            metadata={"user_id": user_id, "asset_type": asset_type},
        )
    except SpacesError as e:
        logger.error(f"Failed to upload asset for user {user_id[:8]}...: {e}")
        raise AssetStorageError(f"Upload failed: {e}") from e

    # Create database record
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO marketing_assets
                (user_id, workspace_id, filename, storage_key, cdn_url, asset_type,
                 title, description, tags, metadata, file_size, mime_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id, created_at, updated_at
                """,
                (
                    user_id,
                    workspace_id,
                    filename,
                    storage_key,
                    cdn_url,
                    asset_type,
                    title,
                    description,
                    tags,
                    metadata,
                    file_size,
                    mime_type,
                ),
            )
            row = cur.fetchone()

            logger.info(
                f"Uploaded asset id={row['id']} for user {user_id[:8]}..., key={storage_key}"
            )

            return AssetRecord(
                id=row["id"],
                user_id=user_id,
                workspace_id=workspace_id,
                filename=filename,
                storage_key=storage_key,
                cdn_url=cdn_url,
                asset_type=asset_type,
                title=title,
                description=description,
                tags=tags,
                metadata=metadata,
                file_size=file_size,
                mime_type=mime_type,
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )


def list_assets(
    user_id: str,
    asset_type: str | None = None,
    tags: list[str] | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[AssetRecord], int]:
    """List user's assets with optional filtering.

    Args:
        user_id: Owner user ID
        asset_type: Filter by type
        tags: Filter by tags (OR matching)
        search: Search in title/description
        limit: Max results
        offset: Pagination offset

    Returns:
        Tuple of (assets, total_count)
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Build WHERE clause with positional params
            conditions = ["user_id = %s"]
            params: list = [user_id]

            if asset_type:
                conditions.append("asset_type = %s")
                params.append(asset_type)

            if tags:
                conditions.append("tags && %s")  # Array overlap
                params.append(tags)

            if search:
                conditions.append("(title ILIKE %s OR description ILIKE %s)")
                search_pattern = f"%{search}%"
                params.extend([search_pattern, search_pattern])

            where_clause = " AND ".join(conditions)

            # Get total count
            cur.execute(
                f"SELECT COUNT(*) FROM marketing_assets WHERE {where_clause}",
                params,
            )
            total = cur.fetchone()["count"]

            # Get paginated results
            cur.execute(
                f"""
                SELECT id, user_id, workspace_id, filename, storage_key, cdn_url,
                       asset_type, title, description, tags, metadata, file_size,
                       mime_type, created_at, updated_at
                FROM marketing_assets
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                [*params, limit, offset],
            )

            assets = []
            for row in cur.fetchall():
                assets.append(
                    AssetRecord(
                        id=row["id"],
                        user_id=row["user_id"],
                        workspace_id=row["workspace_id"],
                        filename=row["filename"],
                        storage_key=row["storage_key"],
                        cdn_url=row["cdn_url"],
                        asset_type=row["asset_type"],
                        title=row["title"],
                        description=row["description"],
                        tags=row["tags"] or [],
                        metadata=row["metadata"],
                        file_size=row["file_size"],
                        mime_type=row["mime_type"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )

            return assets, total


def get_asset(user_id: str, asset_id: int) -> AssetRecord | None:
    """Get a single asset by ID.

    Args:
        user_id: Owner user ID
        asset_id: Asset ID

    Returns:
        AssetRecord or None if not found
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, workspace_id, filename, storage_key, cdn_url,
                       asset_type, title, description, tags, metadata, file_size,
                       mime_type, created_at, updated_at
                FROM marketing_assets
                WHERE id = %s AND user_id = %s
                """,
                (asset_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                return None

            return AssetRecord(
                id=row["id"],
                user_id=row["user_id"],
                workspace_id=row["workspace_id"],
                filename=row["filename"],
                storage_key=row["storage_key"],
                cdn_url=row["cdn_url"],
                asset_type=row["asset_type"],
                title=row["title"],
                description=row["description"],
                tags=row["tags"] or [],
                metadata=row["metadata"],
                file_size=row["file_size"],
                mime_type=row["mime_type"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )


def update_asset(
    user_id: str,
    asset_id: int,
    title: str | None = None,
    description: str | None = None,
    tags: list[str] | None = None,
) -> AssetRecord | None:
    """Update asset metadata.

    Args:
        user_id: Owner user ID
        asset_id: Asset ID
        title: New title
        description: New description
        tags: New tags

    Returns:
        Updated AssetRecord or None if not found
    """
    if tags is not None and len(tags) > 20:
        raise AssetValidationError("Maximum 20 tags allowed")

    with db_session() as conn:
        with conn.cursor() as cur:
            # Check exists
            cur.execute(
                "SELECT id FROM marketing_assets WHERE id = %s AND user_id = %s",
                (asset_id, user_id),
            )
            if not cur.fetchone():
                return None

            # Build update with positional params
            updates = ["updated_at = now()"]
            params: list = []

            if title is not None:
                updates.append("title = %s")
                params.append(title)

            if description is not None:
                updates.append("description = %s")
                params.append(description)

            if tags is not None:
                updates.append("tags = %s")
                params.append(tags)

            # Add WHERE params at end
            params.extend([asset_id, user_id])

            cur.execute(
                f"""
                UPDATE marketing_assets
                SET {", ".join(updates)}
                WHERE id = %s AND user_id = %s
                RETURNING id, user_id, workspace_id, filename, storage_key, cdn_url,
                          asset_type, title, description, tags, metadata, file_size,
                          mime_type, created_at, updated_at
                """,
                params,
            )
            row = cur.fetchone()

            return AssetRecord(
                id=row["id"],
                user_id=row["user_id"],
                workspace_id=row["workspace_id"],
                filename=row["filename"],
                storage_key=row["storage_key"],
                cdn_url=row["cdn_url"],
                asset_type=row["asset_type"],
                title=row["title"],
                description=row["description"],
                tags=row["tags"] or [],
                metadata=row["metadata"],
                file_size=row["file_size"],
                mime_type=row["mime_type"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )


def delete_asset(
    user_id: str,
    asset_id: int,
    spaces_client: SpacesClient | None = None,
) -> bool:
    """Delete an asset from storage and database.

    Args:
        user_id: Owner user ID
        asset_id: Asset ID
        spaces_client: Optional SpacesClient (for testing)

    Returns:
        True if deleted, False if not found
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            # Get storage key first
            cur.execute(
                """
                SELECT storage_key FROM marketing_assets
                WHERE id = %s AND user_id = %s
                """,
                (asset_id, user_id),
            )
            row = cur.fetchone()
            if not row:
                return False

            storage_key = row["storage_key"]

            # Delete from database
            cur.execute(
                "DELETE FROM marketing_assets WHERE id = %s AND user_id = %s",
                (asset_id, user_id),
            )

    # Delete from Spaces (after DB commit)
    client = spaces_client or get_spaces_client()
    try:
        client.delete_file(storage_key)
    except SpacesError as e:
        # Log but don't fail - DB record is already deleted
        logger.warning(f"Failed to delete asset file {storage_key}: {e}")

    logger.info(f"Deleted asset id={asset_id} for user {user_id[:8]}...")
    return True


def search_by_tags(
    user_id: str,
    keywords: list[str],
    limit: int = 10,
) -> list[AssetRecord]:
    """Find assets matching keyword tags.

    Uses array overlap to find assets with matching tags.

    Args:
        user_id: Owner user ID
        keywords: Keywords to match against tags
        limit: Max results

    Returns:
        List of matching AssetRecords
    """
    if not keywords:
        return []

    # Normalize keywords for tag matching
    normalized = [k.lower().strip() for k in keywords if k.strip()]
    if not normalized:
        return []

    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, workspace_id, filename, storage_key, cdn_url,
                       asset_type, title, description, tags, metadata, file_size,
                       mime_type, created_at, updated_at,
                       (SELECT COUNT(*) FROM unnest(tags) t WHERE lower(t) = ANY(%s)) as match_count
                FROM marketing_assets
                WHERE user_id = %s
                  AND tags && %s
                ORDER BY match_count DESC, created_at DESC
                LIMIT %s
                """,
                (normalized, user_id, normalized, limit),
            )

            assets = []
            for row in cur.fetchall():
                assets.append(
                    AssetRecord(
                        id=row["id"],
                        user_id=row["user_id"],
                        workspace_id=row["workspace_id"],
                        filename=row["filename"],
                        storage_key=row["storage_key"],
                        cdn_url=row["cdn_url"],
                        asset_type=row["asset_type"],
                        title=row["title"],
                        description=row["description"],
                        tags=row["tags"] or [],
                        metadata=row["metadata"],
                        file_size=row["file_size"],
                        mime_type=row["mime_type"],
                        created_at=row["created_at"],
                        updated_at=row["updated_at"],
                    )
                )

            return assets


@dataclass
class AssetSuggestionResult:
    """Result of asset suggestion matching."""

    asset: AssetRecord
    relevance_score: float
    matching_tags: list[str]


def suggest_for_article(
    user_id: str,
    article_keywords: list[str],
    limit: int = 5,
) -> list[AssetSuggestionResult]:
    """Suggest assets that match article keywords.

    Calculates relevance score based on tag overlap.

    Args:
        user_id: Owner user ID
        article_keywords: Keywords from article (title, content)
        limit: Max suggestions

    Returns:
        List of AssetSuggestionResult sorted by relevance
    """
    if not article_keywords:
        return []

    # Normalize keywords
    normalized = [k.lower().strip() for k in article_keywords if k.strip()]
    if not normalized:
        return []

    # Get matching assets
    assets = search_by_tags(user_id, normalized, limit=limit * 2)

    # Calculate relevance scores
    results = []
    for asset in assets:
        asset_tags_lower = [t.lower() for t in asset.tags]
        matching = [k for k in normalized if k in asset_tags_lower]

        if matching:
            # Score = matching tags / total keywords (capped at 1.0)
            score = min(len(matching) / len(normalized), 1.0)
            results.append(
                AssetSuggestionResult(
                    asset=asset,
                    relevance_score=round(score, 2),
                    matching_tags=matching,
                )
            )

    # Sort by relevance and limit
    results.sort(key=lambda x: x.relevance_score, reverse=True)
    return results[:limit]


def get_asset_count(user_id: str) -> int:
    """Get total asset count for user.

    Args:
        user_id: Owner user ID

    Returns:
        Number of assets
    """
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM marketing_assets WHERE user_id = %s",
                (user_id,),
            )
            return cur.fetchone()["count"] or 0
