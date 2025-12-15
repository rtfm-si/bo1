"""Blog repository for blog post CRUD operations.

Handles:
- Blog post CRUD
- Status management (draft/scheduled/published)
- Slug generation and validation
- Scheduled post queries
"""

from __future__ import annotations

import builtins
import logging
import re
from datetime import datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

if TYPE_CHECKING:
    pass

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


def generate_slug(title: str, existing_slugs: list[str] | None = None) -> str:
    """Generate URL-friendly slug from title.

    Args:
        title: Blog post title
        existing_slugs: Optional list of existing slugs to avoid conflicts

    Returns:
        Unique slug string
    """
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    # Remove leading/trailing hyphens
    slug = slug.strip("-")
    # Limit length
    slug = slug[:200]

    if not existing_slugs:
        return slug

    # Ensure uniqueness by appending number if needed
    base_slug = slug
    counter = 1
    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


class BlogRepository(BaseRepository):
    """Repository for blog post operations."""

    # =========================================================================
    # Blog Post CRUD
    # =========================================================================

    def create(
        self,
        title: str,
        content: str,
        slug: str | None = None,
        excerpt: str | None = None,
        status: str = "draft",
        published_at: datetime | None = None,
        seo_keywords: list[str] | None = None,
        generated_by_topic: str | None = None,
        meta_title: str | None = None,
        meta_description: str | None = None,
        author_id: str | UUID | None = None,
    ) -> dict[str, Any]:
        """Create a new blog post.

        Args:
            title: Post title
            content: Markdown content
            slug: URL slug (auto-generated if not provided)
            excerpt: Short excerpt for previews
            status: draft, scheduled, or published
            published_at: Publication datetime (required for scheduled)
            seo_keywords: Target keywords
            generated_by_topic: Topic that triggered generation
            meta_title: Custom SEO title
            meta_description: Custom SEO description
            author_id: User who created the post

        Returns:
            Created blog post record
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                # Generate slug if not provided
                if not slug:
                    # Get existing slugs to avoid conflicts
                    cur.execute("SELECT slug FROM blog_posts")
                    existing = [row["slug"] for row in cur.fetchall()]
                    slug = generate_slug(title, existing)

                cur.execute(
                    """
                    INSERT INTO blog_posts (
                        title, slug, content, excerpt, status, published_at,
                        seo_keywords, generated_by_topic, meta_title, meta_description,
                        author_id
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, title, slug, content, excerpt, status, published_at,
                              seo_keywords, generated_by_topic, meta_title, meta_description,
                              author_id, created_at, updated_at
                    """,
                    (
                        title,
                        slug,
                        content,
                        excerpt,
                        status,
                        published_at,
                        seo_keywords,
                        generated_by_topic,
                        meta_title,
                        meta_description,
                        str(author_id) if author_id else None,
                    ),
                )
                result = cur.fetchone()
                logger.info(f"Created blog post: {title} (slug: {slug})")
                return dict(result) if result else {}

    def get_by_id(self, post_id: str | UUID) -> dict[str, Any] | None:
        """Get blog post by ID.

        Args:
            post_id: Post UUID

        Returns:
            Blog post record or None
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, slug, content, excerpt, status, published_at,
                           seo_keywords, generated_by_topic, meta_title, meta_description,
                           author_id, created_at, updated_at
                    FROM blog_posts
                    WHERE id = %s
                    """,
                    (str(post_id),),
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def get_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Get blog post by slug.

        Args:
            slug: URL slug

        Returns:
            Blog post record or None
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, slug, content, excerpt, status, published_at,
                           seo_keywords, generated_by_topic, meta_title, meta_description,
                           author_id, created_at, updated_at
                    FROM blog_posts
                    WHERE slug = %s
                    """,
                    (slug,),
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def list(
        self,
        status: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List blog posts with optional status filter.

        Args:
            status: Filter by status (draft, scheduled, published)
            limit: Max results
            offset: Pagination offset

        Returns:
            List of blog post records
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                if status:
                    cur.execute(
                        """
                        SELECT id, title, slug, excerpt, status, published_at,
                               seo_keywords, generated_by_topic, created_at, updated_at
                        FROM blog_posts
                        WHERE status = %s
                        ORDER BY
                            CASE WHEN status = 'scheduled' THEN published_at END ASC,
                            updated_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (status, limit, offset),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, title, slug, excerpt, status, published_at,
                               seo_keywords, generated_by_topic, created_at, updated_at
                        FROM blog_posts
                        ORDER BY
                            CASE WHEN status = 'scheduled' THEN published_at END ASC,
                            updated_at DESC
                        LIMIT %s OFFSET %s
                        """,
                        (limit, offset),
                    )
                return [dict(row) for row in cur.fetchall()]

    def update(
        self,
        post_id: str | UUID,
        title: str | None = None,
        content: str | None = None,
        slug: str | None = None,
        excerpt: str | None = None,
        status: str | None = None,
        published_at: datetime | None = None,
        seo_keywords: builtins.list[str] | None = None,
        meta_title: str | None = None,
        meta_description: str | None = None,
    ) -> dict[str, Any] | None:
        """Update blog post fields.

        Args:
            post_id: Post UUID
            title: New title (optional)
            content: New content (optional)
            slug: New slug (optional)
            excerpt: New excerpt (optional)
            status: New status (optional)
            published_at: New publish date (optional)
            seo_keywords: New SEO keywords (optional)
            meta_title: New meta title (optional)
            meta_description: New meta description (optional)

        Returns:
            Updated blog post record or None if not found
        """
        updates: dict[str, Any] = {}
        params = []

        if title is not None:
            updates["title"] = title
        if content is not None:
            updates["content"] = content
        if slug is not None:
            updates["slug"] = slug
        if excerpt is not None:
            updates["excerpt"] = excerpt
        if status is not None:
            updates["status"] = status
        if published_at is not None:
            updates["published_at"] = published_at
        if seo_keywords is not None:
            updates["seo_keywords"] = seo_keywords
        if meta_title is not None:
            updates["meta_title"] = meta_title
        if meta_description is not None:
            updates["meta_description"] = meta_description

        if not updates:
            return self.get_by_id(post_id)

        # Build SET clause
        set_parts = [f"{k} = %s" for k in updates]
        set_parts.append("updated_at = NOW()")
        params = list(updates.values())
        params.append(str(post_id))

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE blog_posts
                    SET {", ".join(set_parts)}
                    WHERE id = %s
                    RETURNING id, title, slug, content, excerpt, status, published_at,
                              seo_keywords, generated_by_topic, meta_title, meta_description,
                              author_id, created_at, updated_at
                    """,
                    params,
                )
                result = cur.fetchone()
                if result:
                    logger.info(f"Updated blog post {post_id}")
                return dict(result) if result else None

    def delete(self, post_id: str | UUID) -> bool:
        """Delete blog post (hard delete).

        Args:
            post_id: Post UUID

        Returns:
            True if deleted, False if not found
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM blog_posts WHERE id = %s RETURNING id",
                    (str(post_id),),
                )
                result = cur.fetchone()
                if result:
                    logger.info(f"Deleted blog post {post_id}")
                    return True
                return False

    # =========================================================================
    # Publishing Operations
    # =========================================================================

    def get_scheduled_for_publish(self) -> builtins.list[dict[str, Any]]:
        """Get scheduled posts ready for publishing.

        Returns posts with status='scheduled' and published_at <= now.

        Returns:
            List of posts ready to publish
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, title, slug, content, excerpt, status, published_at,
                           seo_keywords, generated_by_topic, meta_title, meta_description,
                           author_id, created_at, updated_at
                    FROM blog_posts
                    WHERE status = 'scheduled'
                      AND published_at <= NOW()
                    ORDER BY published_at ASC
                    """,
                )
                return [dict(row) for row in cur.fetchall()]

    def publish(self, post_id: str | UUID) -> dict[str, Any] | None:
        """Publish a blog post immediately.

        Sets status='published' and published_at=NOW() if not already set.

        Args:
            post_id: Post UUID

        Returns:
            Updated blog post record or None
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE blog_posts
                    SET status = 'published',
                        published_at = COALESCE(published_at, NOW()),
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, title, slug, content, excerpt, status, published_at,
                              seo_keywords, generated_by_topic, meta_title, meta_description,
                              author_id, created_at, updated_at
                    """,
                    (str(post_id),),
                )
                result = cur.fetchone()
                if result:
                    logger.info(f"Published blog post {post_id}")
                return dict(result) if result else None

    def schedule(
        self,
        post_id: str | UUID,
        publish_at: datetime,
    ) -> dict[str, Any] | None:
        """Schedule a blog post for future publication.

        Args:
            post_id: Post UUID
            publish_at: Scheduled publication datetime

        Returns:
            Updated blog post record or None
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE blog_posts
                    SET status = 'scheduled',
                        published_at = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, title, slug, content, excerpt, status, published_at,
                              seo_keywords, generated_by_topic, meta_title, meta_description,
                              author_id, created_at, updated_at
                    """,
                    (publish_at, str(post_id)),
                )
                result = cur.fetchone()
                if result:
                    logger.info(f"Scheduled blog post {post_id} for {publish_at}")
                return dict(result) if result else None

    def count(self, status: str | None = None) -> int:
        """Count blog posts with optional status filter.

        Args:
            status: Filter by status

        Returns:
            Post count
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                if status:
                    cur.execute(
                        "SELECT COUNT(*) FROM blog_posts WHERE status = %s",
                        (status,),
                    )
                else:
                    cur.execute("SELECT COUNT(*) FROM blog_posts")
                result = cur.fetchone()
                return result["count"] if result else 0


# Singleton instance
blog_repository = BlogRepository()
