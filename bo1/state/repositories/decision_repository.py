"""Decision repository for published decision CRUD operations.

Handles:
- Published decision CRUD
- Status management (draft/published)
- Slug generation and validation
- Category-based queries
- Related decisions linking
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING, Any
from uuid import UUID, uuid4

if TYPE_CHECKING:
    pass

from bo1.state.database import db_session
from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


def calculate_reading_time(text: str | None) -> int | None:
    """Calculate reading time in minutes (200 wpm average).

    Returns None if no text provided.
    """
    if not text:
        return None
    words = len(text.split())
    return max(1, words // 200)


def generate_slug(title: str, existing_slugs: list[str] | None = None) -> str:
    """Generate URL-friendly slug from title.

    Args:
        title: Decision title
        existing_slugs: Optional list of existing slugs to avoid conflicts

    Returns:
        Unique slug string
    """
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower())
    slug = slug.strip("-")
    slug = slug[:100]

    if not existing_slugs:
        return slug

    base_slug = slug
    counter = 1
    while slug in existing_slugs:
        slug = f"{base_slug}-{counter}"
        counter += 1

    return slug


# Valid decision categories
DECISION_CATEGORIES = [
    "hiring",
    "pricing",
    "fundraising",
    "marketing",
    "strategy",
    "product",
    "operations",
    "growth",
]


class DecisionRepository(BaseRepository):
    """Repository for published decision operations."""

    def create(
        self,
        title: str,
        category: str,
        founder_context: dict[str, Any],
        slug: str | None = None,
        session_id: str | UUID | None = None,
        meta_description: str | None = None,
        expert_perspectives: list[dict[str, Any]] | None = None,
        synthesis: str | None = None,
        faqs: list[dict[str, Any]] | None = None,
        status: str = "draft",
        featured_image_url: str | None = None,
        seo_keywords: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new published decision.

        Args:
            title: Decision title (becomes H1)
            category: Decision category (hiring, pricing, etc.)
            founder_context: Context dict with stage, constraints, situation
            slug: URL slug (auto-generated if not provided)
            session_id: Source session ID (optional)
            meta_description: SEO description
            expert_perspectives: List of expert viewpoints
            synthesis: Board synthesis/recommendation
            faqs: FAQ pairs for schema
            status: draft or published
            featured_image_url: URL for og:image and schema image
            seo_keywords: List of SEO keywords for meta tag

        Returns:
            Created decision record
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                if not slug:
                    cur.execute("SELECT slug FROM published_decisions")
                    existing = [row["slug"] for row in cur.fetchall()]
                    slug = generate_slug(title, existing)

                decision_id = str(uuid4())

                reading_time = calculate_reading_time(synthesis)

                cur.execute(
                    """
                    INSERT INTO published_decisions (
                        id, session_id, category, slug, title, meta_description,
                        founder_context, expert_perspectives, synthesis, faqs, status,
                        featured_image_url, seo_keywords, reading_time_minutes
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id, session_id, category, slug, title, meta_description,
                              founder_context, expert_perspectives, synthesis, faqs,
                              related_decision_ids, status, published_at,
                              created_at, updated_at, view_count, click_through_count,
                              featured_image_url, seo_keywords, reading_time_minutes
                    """,
                    (
                        decision_id,
                        str(session_id) if session_id else None,
                        category,
                        slug,
                        title,
                        meta_description,
                        self._to_json(founder_context),
                        self._to_json(expert_perspectives),
                        synthesis,
                        self._to_json(faqs),
                        status,
                        featured_image_url,
                        seo_keywords,
                        reading_time,
                    ),
                )
                result = cur.fetchone()
                logger.info(f"Created decision: {title} (slug: {slug})")
                return dict(result) if result else {}

    def get_by_id(self, decision_id: str | UUID) -> dict[str, Any] | None:
        """Get decision by ID."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, session_id, category, slug, title, meta_description,
                           founder_context, expert_perspectives, synthesis, faqs,
                           related_decision_ids, status, published_at,
                           created_at, updated_at, view_count, click_through_count,
                           homepage_featured, homepage_order,
                           featured_image_url, seo_keywords, reading_time_minutes
                    FROM published_decisions
                    WHERE id = %s
                    """,
                    (str(decision_id),),
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def get_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Get decision by slug."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, session_id, category, slug, title, meta_description,
                           founder_context, expert_perspectives, synthesis, faqs,
                           related_decision_ids, status, published_at,
                           created_at, updated_at, view_count, click_through_count,
                           featured_image_url, seo_keywords, reading_time_minutes
                    FROM published_decisions
                    WHERE slug = %s
                    """,
                    (slug,),
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def get_by_category_slug(self, category: str, slug: str) -> dict[str, Any] | None:
        """Get published decision by category and slug (public route)."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, session_id, category, slug, title, meta_description,
                           founder_context, expert_perspectives, synthesis, faqs,
                           related_decision_ids, status, published_at,
                           created_at, updated_at, view_count, click_through_count,
                           featured_image_url, seo_keywords, reading_time_minutes
                    FROM published_decisions
                    WHERE category = %s AND slug = %s AND status = 'published'
                    """,
                    (category, slug),
                )
                result = cur.fetchone()
                return dict(result) if result else None

    def list_decisions(
        self,
        status: str | None = None,
        category: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """List decisions with optional filters."""
        with db_session() as conn:
            with conn.cursor() as cur:
                conditions = []
                params: list[Any] = []

                if status:
                    conditions.append("status = %s")
                    params.append(status)
                if category:
                    conditions.append("category = %s")
                    params.append(category)

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
                params.extend([limit, offset])

                cur.execute(
                    f"""
                    SELECT id, session_id, category, slug, title, meta_description,
                           status, published_at, created_at, updated_at,
                           view_count, click_through_count,
                           homepage_featured, homepage_order
                    FROM published_decisions
                    {where_clause}
                    ORDER BY
                        CASE WHEN status = 'published' THEN published_at END DESC,
                        updated_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    params,
                )
                return [dict(row) for row in cur.fetchall()]

    def list_published_by_category(self, category: str) -> list[dict[str, Any]]:
        """List published decisions in a category (public)."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, category, slug, title, meta_description,
                           founder_context, published_at
                    FROM published_decisions
                    WHERE status = 'published' AND category = %s
                    ORDER BY published_at DESC
                    """,
                    (category,),
                )
                return [dict(row) for row in cur.fetchall()]

    def list_all_published(self) -> list[dict[str, Any]]:
        """List all published decisions (for sitemap/index)."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, category, slug, title, meta_description,
                           founder_context, published_at, updated_at
                    FROM published_decisions
                    WHERE status = 'published'
                    ORDER BY published_at DESC
                    """
                )
                return [dict(row) for row in cur.fetchall()]

    def get_categories_with_counts(self) -> list[dict[str, Any]]:
        """Get categories with published decision counts."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT category, COUNT(*) as count
                    FROM published_decisions
                    WHERE status = 'published'
                    GROUP BY category
                    ORDER BY count DESC
                    """
                )
                return [dict(row) for row in cur.fetchall()]

    def update(
        self,
        decision_id: str | UUID,
        title: str | None = None,
        category: str | None = None,
        slug: str | None = None,
        meta_description: str | None = None,
        founder_context: dict[str, Any] | None = None,
        expert_perspectives: list[dict[str, Any]] | None = None,
        synthesis: str | None = None,
        faqs: list[dict[str, Any]] | None = None,
        related_decision_ids: list[str] | None = None,
        status: str | None = None,
        featured_image_url: str | None = None,
        seo_keywords: list[str] | None = None,
    ) -> dict[str, Any] | None:
        """Update decision fields."""
        updates: list[str] = []
        params: list[Any] = []

        if title is not None:
            updates.append("title = %s")
            params.append(title)
        if category is not None:
            updates.append("category = %s")
            params.append(category)
        if slug is not None:
            updates.append("slug = %s")
            params.append(slug)
        if meta_description is not None:
            updates.append("meta_description = %s")
            params.append(meta_description)
        if founder_context is not None:
            updates.append("founder_context = %s")
            params.append(self._to_json(founder_context))
        if expert_perspectives is not None:
            updates.append("expert_perspectives = %s")
            params.append(self._to_json(expert_perspectives))
        if synthesis is not None:
            updates.append("synthesis = %s")
            params.append(synthesis)
            # Recalculate reading time when synthesis changes
            reading_time = calculate_reading_time(synthesis)
            updates.append("reading_time_minutes = %s")
            params.append(reading_time)
        if faqs is not None:
            updates.append("faqs = %s")
            params.append(self._to_json(faqs))
        if related_decision_ids is not None:
            updates.append("related_decision_ids = %s")
            params.append(related_decision_ids)
        if status is not None:
            updates.append("status = %s")
            params.append(status)
        if featured_image_url is not None:
            updates.append("featured_image_url = %s")
            params.append(featured_image_url)
        if seo_keywords is not None:
            updates.append("seo_keywords = %s")
            params.append(seo_keywords)

        if not updates:
            return self.get_by_id(decision_id)

        updates.append("updated_at = NOW()")
        params.append(str(decision_id))

        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    UPDATE published_decisions
                    SET {", ".join(updates)}
                    WHERE id = %s
                    RETURNING id, session_id, category, slug, title, meta_description,
                              founder_context, expert_perspectives, synthesis, faqs,
                              related_decision_ids, status, published_at,
                              created_at, updated_at, view_count, click_through_count,
                              featured_image_url, seo_keywords, reading_time_minutes
                    """,
                    params,
                )
                result = cur.fetchone()
                if result:
                    logger.info(f"Updated decision {decision_id}")
                return dict(result) if result else None

    def delete(self, decision_id: str | UUID) -> bool:
        """Delete decision (hard delete)."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM published_decisions WHERE id = %s RETURNING id",
                    (str(decision_id),),
                )
                result = cur.fetchone()
                if result:
                    logger.info(f"Deleted decision {decision_id}")
                    return True
                return False

    def publish(self, decision_id: str | UUID) -> dict[str, Any] | None:
        """Publish a decision immediately."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE published_decisions
                    SET status = 'published',
                        published_at = COALESCE(published_at, NOW()),
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, session_id, category, slug, title, meta_description,
                              founder_context, expert_perspectives, synthesis, faqs,
                              related_decision_ids, status, published_at,
                              created_at, updated_at, view_count, click_through_count
                    """,
                    (str(decision_id),),
                )
                result = cur.fetchone()
                if result:
                    logger.info(f"Published decision {decision_id}")
                return dict(result) if result else None

    def unpublish(self, decision_id: str | UUID) -> dict[str, Any] | None:
        """Revert decision to draft."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE published_decisions
                    SET status = 'draft',
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, session_id, category, slug, title, meta_description,
                              founder_context, expert_perspectives, synthesis, faqs,
                              related_decision_ids, status, published_at,
                              created_at, updated_at, view_count, click_through_count
                    """,
                    (str(decision_id),),
                )
                result = cur.fetchone()
                if result:
                    logger.info(f"Unpublished decision {decision_id}")
                return dict(result) if result else None

    def count(self, status: str | None = None, category: str | None = None) -> int:
        """Count decisions with optional filters."""
        with db_session() as conn:
            with conn.cursor() as cur:
                conditions = []
                params: list[Any] = []

                if status:
                    conditions.append("status = %s")
                    params.append(status)
                if category:
                    conditions.append("category = %s")
                    params.append(category)

                where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

                cur.execute(
                    f"SELECT COUNT(*) FROM published_decisions {where_clause}",
                    params,
                )
                result = cur.fetchone()
                return result["count"] if result else 0

    def increment_view(self, slug: str) -> bool:
        """Increment view count for a published decision."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE published_decisions
                    SET view_count = view_count + 1
                    WHERE slug = %s AND status = 'published'
                    RETURNING id
                    """,
                    (slug,),
                )
                result = cur.fetchone()
                return result is not None

    def increment_click(self, slug: str) -> bool:
        """Increment CTA click count for a published decision."""
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE published_decisions
                    SET click_through_count = click_through_count + 1
                    WHERE slug = %s AND status = 'published'
                    RETURNING id
                    """,
                    (slug,),
                )
                result = cur.fetchone()
                return result is not None

    def list_featured_for_homepage(self, limit: int = 6) -> list[dict[str, Any]]:
        """List featured decisions for homepage display.

        Returns published decisions marked as homepage_featured,
        ordered by homepage_order.
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, category, slug, title, meta_description,
                           founder_context, synthesis, homepage_order
                    FROM published_decisions
                    WHERE status = 'published' AND homepage_featured = true
                    ORDER BY homepage_order NULLS LAST, published_at DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return [dict(row) for row in cur.fetchall()]

    def set_homepage_featured(
        self,
        decision_id: str | UUID,
        featured: bool,
        order: int | None = None,
    ) -> dict[str, Any] | None:
        """Set or unset a decision as homepage featured.

        Args:
            decision_id: Decision ID
            featured: Whether to feature on homepage
            order: Sort order (lower = first), None clears order

        Returns:
            Updated decision record
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE published_decisions
                    SET homepage_featured = %s,
                        homepage_order = %s,
                        updated_at = NOW()
                    WHERE id = %s
                    RETURNING id, session_id, category, slug, title, meta_description,
                              founder_context, expert_perspectives, synthesis, faqs,
                              related_decision_ids, status, published_at,
                              created_at, updated_at, view_count, click_through_count,
                              homepage_featured, homepage_order
                    """,
                    (featured, order if featured else None, str(decision_id)),
                )
                result = cur.fetchone()
                if result:
                    action = "Featured" if featured else "Unfeatured"
                    logger.info(f"{action} decision {decision_id} on homepage")
                return dict(result) if result else None

    def update_homepage_order(self, ordered_ids: list[str]) -> bool:
        """Bulk update homepage_order for featured decisions.

        Args:
            ordered_ids: List of decision IDs in desired order

        Returns:
            True if successful
        """
        with db_session() as conn:
            with conn.cursor() as cur:
                for order, decision_id in enumerate(ordered_ids):
                    cur.execute(
                        """
                        UPDATE published_decisions
                        SET homepage_order = %s, updated_at = NOW()
                        WHERE id = %s AND homepage_featured = true
                        """,
                        (order, decision_id),
                    )
                logger.info(f"Reordered {len(ordered_ids)} homepage featured decisions")
                return True

    def get_related(self, decision_id: str | UUID, limit: int = 5) -> list[dict[str, Any]]:
        """Get related published decisions."""
        decision = self.get_by_id(decision_id)
        if not decision:
            return []

        related_ids = decision.get("related_decision_ids") or []

        with db_session() as conn:
            with conn.cursor() as cur:
                if related_ids:
                    # Get explicitly related decisions
                    cur.execute(
                        """
                        SELECT id, category, slug, title, meta_description
                        FROM published_decisions
                        WHERE id = ANY(%s) AND status = 'published'
                        LIMIT %s
                        """,
                        (related_ids, limit),
                    )
                    results = [dict(row) for row in cur.fetchall()]
                    if len(results) >= limit:
                        return results
                    remaining = limit - len(results)
                else:
                    results = []
                    remaining = limit

                # Fill with same-category decisions
                exclude_ids = [str(decision_id)] + related_ids
                cur.execute(
                    """
                    SELECT id, category, slug, title, meta_description
                    FROM published_decisions
                    WHERE category = %s AND status = 'published'
                      AND id != ALL(%s)
                    ORDER BY published_at DESC
                    LIMIT %s
                    """,
                    (decision["category"], exclude_ids, remaining),
                )
                results.extend([dict(row) for row in cur.fetchall()])

                return results


# Singleton instance
decision_repository = DecisionRepository()
