"""Template repository for meeting template management.

Handles:
- Template CRUD operations
- Public template listing for users
- Admin template management
- Template versioning for safe updates
"""

import logging
from typing import Any
from uuid import UUID

from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class TemplateRepository(BaseRepository):
    """Repository for meeting template operations."""

    # =========================================================================
    # Public Operations (no auth required for reads)
    # =========================================================================

    def list_active(self, category: str | None = None) -> list[dict[str, Any]]:
        """List all active templates for public gallery.

        Args:
            category: Optional category filter

        Returns:
            List of active template records
        """
        if category:
            return self._execute_query(
                """
                SELECT id, name, slug, description, category, problem_statement_template,
                       context_hints, suggested_persona_traits, is_builtin, version,
                       created_at, updated_at
                FROM meeting_templates
                WHERE is_active = true AND category = %s
                ORDER BY is_builtin DESC, name
                """,
                (category,),
            )
        return self._execute_query(
            """
            SELECT id, name, slug, description, category, problem_statement_template,
                   context_hints, suggested_persona_traits, is_builtin, version,
                   created_at, updated_at
            FROM meeting_templates
            WHERE is_active = true
            ORDER BY is_builtin DESC, name
            """
        )

    def get_by_slug(self, slug: str) -> dict[str, Any] | None:
        """Get a template by slug for public access.

        Args:
            slug: Template slug

        Returns:
            Template record or None if not found/inactive
        """
        return self._execute_one(
            """
            SELECT id, name, slug, description, category, problem_statement_template,
                   context_hints, suggested_persona_traits, is_builtin, version,
                   created_at, updated_at
            FROM meeting_templates
            WHERE slug = %s AND is_active = true
            """,
            (slug,),
        )

    def get_by_id(self, template_id: str | UUID) -> dict[str, Any] | None:
        """Get a template by ID.

        Args:
            template_id: Template UUID

        Returns:
            Template record or None if not found
        """
        return self._execute_one(
            """
            SELECT id, name, slug, description, category, problem_statement_template,
                   context_hints, suggested_persona_traits, is_builtin, is_active, version,
                   created_at, updated_at
            FROM meeting_templates
            WHERE id = %s
            """,
            (str(template_id),),
        )

    def get_categories(self) -> list[str]:
        """Get all distinct categories from active templates.

        Returns:
            List of category strings
        """
        rows = self._execute_query(
            """
            SELECT DISTINCT category
            FROM meeting_templates
            WHERE is_active = true
            ORDER BY category
            """
        )
        return [row["category"] for row in rows]

    # =========================================================================
    # Admin Operations
    # =========================================================================

    def list_all(self, include_inactive: bool = True) -> list[dict[str, Any]]:
        """List all templates for admin management.

        Args:
            include_inactive: Include deactivated templates

        Returns:
            List of all template records
        """
        if include_inactive:
            return self._execute_query(
                """
                SELECT id, name, slug, description, category, problem_statement_template,
                       context_hints, suggested_persona_traits, is_builtin, is_active, version,
                       created_at, updated_at
                FROM meeting_templates
                ORDER BY is_active DESC, is_builtin DESC, name
                """
            )
        return self.list_active()

    def create(
        self,
        name: str,
        slug: str,
        description: str,
        category: str,
        problem_statement_template: str,
        context_hints: list[str] | None = None,
        suggested_persona_traits: list[str] | None = None,
    ) -> dict[str, Any]:
        """Create a new template (admin only).

        Args:
            name: Display name
            slug: URL-friendly identifier
            description: Gallery description
            category: Template category
            problem_statement_template: Pre-filled problem statement
            context_hints: Suggested context fields
            suggested_persona_traits: Persona trait hints

        Returns:
            Created template record

        Raises:
            ValueError: If slug already exists
        """
        return self._execute_returning(
            """
            INSERT INTO meeting_templates (
                name, slug, description, category, problem_statement_template,
                context_hints, suggested_persona_traits
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            RETURNING id, name, slug, description, category, problem_statement_template,
                      context_hints, suggested_persona_traits, is_builtin, is_active, version,
                      created_at, updated_at
            """,
            (
                name.strip(),
                slug.strip().lower(),
                description.strip(),
                category,
                problem_statement_template.strip(),
                self._to_json(context_hints or []),
                self._to_json(suggested_persona_traits or []),
            ),
        )

    def update(
        self,
        template_id: str | UUID,
        name: str | None = None,
        description: str | None = None,
        category: str | None = None,
        problem_statement_template: str | None = None,
        context_hints: list[str] | None = None,
        suggested_persona_traits: list[str] | None = None,
        is_active: bool | None = None,
    ) -> dict[str, Any] | None:
        """Update a template (admin only).

        Increments version on each update for change tracking.

        Args:
            template_id: Template UUID
            name: Updated name
            description: Updated description
            category: Updated category
            problem_statement_template: Updated problem statement
            context_hints: Updated context hints
            suggested_persona_traits: Updated traits
            is_active: Activate/deactivate

        Returns:
            Updated template record or None if not found
        """
        updates = []
        params: list[Any] = []

        if name is not None:
            updates.append("name = %s")
            params.append(name.strip())
        if description is not None:
            updates.append("description = %s")
            params.append(description.strip())
        if category is not None:
            updates.append("category = %s")
            params.append(category)
        if problem_statement_template is not None:
            updates.append("problem_statement_template = %s")
            params.append(problem_statement_template.strip())
        if context_hints is not None:
            updates.append("context_hints = %s")
            params.append(self._to_json(context_hints))
        if suggested_persona_traits is not None:
            updates.append("suggested_persona_traits = %s")
            params.append(self._to_json(suggested_persona_traits))
        if is_active is not None:
            updates.append("is_active = %s")
            params.append(is_active)

        if not updates:
            return self.get_by_id(template_id)

        # Always update timestamp and increment version
        updates.append("updated_at = NOW()")
        updates.append("version = version + 1")
        params.append(str(template_id))

        return self._execute_one(
            f"""
            UPDATE meeting_templates
            SET {", ".join(updates)}
            WHERE id = %s
            RETURNING id, name, slug, description, category, problem_statement_template,
                      context_hints, suggested_persona_traits, is_builtin, is_active, version,
                      created_at, updated_at
            """,
            tuple(params),
        )

    def delete(self, template_id: str | UUID) -> bool:
        """Hard delete a template (admin only).

        Only allows deletion of non-builtin templates.

        Args:
            template_id: Template UUID

        Returns:
            True if deleted, False if not found or is builtin
        """
        count = self._execute_count(
            """
            DELETE FROM meeting_templates
            WHERE id = %s AND is_builtin = false
            """,
            (str(template_id),),
        )
        return count > 0

    def deactivate(self, template_id: str | UUID) -> dict[str, Any] | None:
        """Soft delete (deactivate) a template.

        Args:
            template_id: Template UUID

        Returns:
            Updated template or None if not found
        """
        return self.update(template_id, is_active=False)

    def activate(self, template_id: str | UUID) -> dict[str, Any] | None:
        """Reactivate a template.

        Args:
            template_id: Template UUID

        Returns:
            Updated template or None if not found
        """
        return self.update(template_id, is_active=True)

    def slug_exists(self, slug: str, exclude_id: str | UUID | None = None) -> bool:
        """Check if a slug already exists.

        Args:
            slug: Slug to check
            exclude_id: Exclude this template ID from check (for updates)

        Returns:
            True if slug exists
        """
        if exclude_id:
            row = self._execute_one(
                """
                SELECT 1 FROM meeting_templates
                WHERE slug = %s AND id != %s
                """,
                (slug.strip().lower(), str(exclude_id)),
            )
        else:
            row = self._execute_one(
                """
                SELECT 1 FROM meeting_templates
                WHERE slug = %s
                """,
                (slug.strip().lower(),),
            )
        return row is not None

    # =========================================================================
    # Analytics / Stats
    # =========================================================================

    def get_usage_stats(self) -> list[dict[str, Any]]:
        """Get template usage statistics.

        Returns:
            List of templates with usage count
        """
        return self._execute_query(
            """
            SELECT t.id, t.name, t.slug, t.category,
                   COUNT(s.id) as usage_count,
                   MAX(s.created_at) as last_used_at
            FROM meeting_templates t
            LEFT JOIN sessions s ON s.template_id = t.id
            GROUP BY t.id
            ORDER BY usage_count DESC, t.name
            """
        )


# Singleton instance
template_repository = TemplateRepository()
