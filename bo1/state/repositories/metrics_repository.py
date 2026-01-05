"""Metrics repository for business metrics (Layer 3 context).

Handles:
- Metric templates (predefined SaaS metrics)
- User metrics (values and custom metrics)
- Metric CRUD operations
"""

import logging
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class MetricsRepository(BaseRepository):
    """Repository for business metrics data."""

    # =========================================================================
    # Metric Templates
    # =========================================================================

    def get_templates(self, business_model: str | None = None) -> list[dict[str, Any]]:
        """Get metric templates, optionally filtered by business model.

        Args:
            business_model: Filter to templates applicable to this model
                           (saas, ecommerce, marketplace, d2c) or None for all

        Returns:
            List of metric template dictionaries ordered by priority then display_order
        """
        if business_model:
            # Filter by business model (includes 'all' templates)
            return self._execute_query(
                """
                SELECT metric_key, name, definition, importance, category,
                       value_unit, display_order, applies_to, priority
                FROM metric_templates
                WHERE applies_to @> %s OR applies_to @> '["all"]'
                ORDER BY priority ASC, display_order ASC, metric_key
                """,
                (f'["{business_model}"]',),
            )
        else:
            return self._execute_query(
                """
                SELECT metric_key, name, definition, importance, category,
                       value_unit, display_order, applies_to, priority
                FROM metric_templates
                ORDER BY priority ASC, display_order ASC, metric_key
                """
            )

    def get_template(self, metric_key: str) -> dict[str, Any] | None:
        """Get a single metric template by key.

        Args:
            metric_key: The metric key (e.g., 'mrr', 'cac')

        Returns:
            Metric template dict or None
        """
        return self._execute_one(
            """
            SELECT metric_key, name, definition, importance, category,
                   value_unit, display_order, applies_to, priority
            FROM metric_templates
            WHERE metric_key = %s
            """,
            (metric_key,),
        )

    # =========================================================================
    # User Metrics
    # =========================================================================

    def get_business_metrics(
        self, user_id: str, include_irrelevant: bool = False
    ) -> list[dict[str, Any]]:
        """Get all metrics for a user.

        Args:
            user_id: User identifier
            include_irrelevant: If True, include metrics marked as not relevant

        Returns:
            List of user metric dictionaries
        """
        if include_irrelevant:
            return self._execute_query(
                """
                SELECT id, user_id, metric_key, name, definition, importance,
                       category, value, value_unit, captured_at, source,
                       is_predefined, display_order, is_relevant, created_at, updated_at
                FROM business_metrics
                WHERE user_id = %s
                ORDER BY display_order, metric_key
                """,
                (user_id,),
                user_id=user_id,
            )
        return self._execute_query(
            """
            SELECT id, user_id, metric_key, name, definition, importance,
                   category, value, value_unit, captured_at, source,
                   is_predefined, display_order, is_relevant, created_at, updated_at
            FROM business_metrics
            WHERE user_id = %s AND is_relevant = TRUE
            ORDER BY display_order, metric_key
            """,
            (user_id,),
            user_id=user_id,
        )

    def get_user_metric(self, user_id: str, metric_key: str) -> dict[str, Any] | None:
        """Get a single user metric by key.

        Args:
            user_id: User identifier
            metric_key: The metric key

        Returns:
            User metric dict or None
        """
        return self._execute_one(
            """
            SELECT id, user_id, metric_key, name, definition, importance,
                   category, value, value_unit, captured_at, source,
                   is_predefined, display_order, is_relevant, created_at, updated_at
            FROM business_metrics
            WHERE user_id = %s AND metric_key = %s
            """,
            (user_id, metric_key),
            user_id=user_id,
        )

    def get_metrics_with_templates(
        self, user_id: str, business_model: str | None = None, include_irrelevant: bool = False
    ) -> dict[str, Any]:
        """Get user metrics merged with applicable templates.

        Returns:
        - User's saved metrics (relevant only by default)
        - Template definitions for metrics not yet saved
        - Hidden metrics (when include_irrelevant=True)

        Args:
            user_id: User identifier
            business_model: Filter templates by business model
            include_irrelevant: If True, also return hidden metrics separately

        Returns:
            Dict with 'metrics' (user's saved), 'templates' (unfilled),
            and optionally 'hidden_metrics'
        """
        # Get user's saved metrics (relevant only)
        business_metrics = self.get_business_metrics(user_id, include_irrelevant=False)

        # Get applicable templates
        templates = self.get_templates(business_model)

        # Filter templates to those not already saved (check all metrics including hidden)
        all_user_metrics = (
            self.get_business_metrics(user_id, include_irrelevant=True)
            if include_irrelevant
            else business_metrics
        )
        all_saved_keys = {m["metric_key"] for m in all_user_metrics}
        unfilled_templates = [t for t in templates if t["metric_key"] not in all_saved_keys]

        result = {
            "metrics": business_metrics,
            "templates": unfilled_templates,
        }

        # Get hidden metrics if requested
        if include_irrelevant:
            hidden_metrics = [m for m in all_user_metrics if not m.get("is_relevant", True)]
            result["hidden_metrics"] = hidden_metrics

        return result

    def save_metric(
        self,
        user_id: str,
        metric_key: str,
        value: Decimal | float | int | None,
        name: str | None = None,
        definition: str | None = None,
        importance: str | None = None,
        category: str | None = None,
        value_unit: str | None = None,
        source: str = "manual",
        is_predefined: bool = False,
        display_order: int = 0,
    ) -> dict[str, Any]:
        """Save or update a user metric.

        If the metric exists, updates the value. Otherwise creates it.
        For predefined metrics, looks up template for defaults.

        Args:
            user_id: User identifier
            metric_key: Metric key (e.g., 'mrr', 'custom_xyz')
            value: The metric value
            name: Display name (required for custom, optional for predefined)
            definition: What it measures
            importance: Why it matters
            category: financial, growth, retention, efficiency, custom
            value_unit: $, %, months, ratio
            source: manual, clarification, integration
            is_predefined: True if based on template
            display_order: Sort order

        Returns:
            The saved metric record
        """
        # For predefined metrics, get defaults from template
        if is_predefined and not all([name, definition, category, value_unit]):
            template = self.get_template(metric_key)
            if template:
                name = name or template["name"]
                definition = definition or template["definition"]
                importance = importance or template["importance"]
                category = category or template["category"]
                value_unit = value_unit or template["value_unit"]
                display_order = display_order or template["display_order"]

        if not name:
            raise ValueError(f"name is required for metric {metric_key}")

        captured_at = datetime.now(UTC) if value is not None else None

        return self._execute_returning(
            """
            INSERT INTO business_metrics (
                user_id, metric_key, name, definition, importance, category,
                value, value_unit, captured_at, source, is_predefined, display_order
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (user_id, metric_key) DO UPDATE SET
                name = EXCLUDED.name,
                definition = COALESCE(EXCLUDED.definition, business_metrics.definition),
                importance = COALESCE(EXCLUDED.importance, business_metrics.importance),
                category = COALESCE(EXCLUDED.category, business_metrics.category),
                value = EXCLUDED.value,
                value_unit = COALESCE(EXCLUDED.value_unit, business_metrics.value_unit),
                captured_at = EXCLUDED.captured_at,
                source = EXCLUDED.source,
                updated_at = NOW()
            RETURNING id, user_id, metric_key, name, definition, importance,
                      category, value, value_unit, captured_at, source,
                      is_predefined, display_order, is_relevant, created_at, updated_at
            """,
            (
                user_id,
                metric_key,
                name,
                definition,
                importance,
                category,
                value,
                value_unit,
                captured_at,
                source,
                is_predefined,
                display_order,
            ),
            user_id=user_id,
        )

    def update_metric_value(
        self,
        user_id: str,
        metric_key: str,
        value: Decimal | float | int | None,
        source: str = "manual",
    ) -> dict[str, Any] | None:
        """Update just the value of an existing metric.

        Args:
            user_id: User identifier
            metric_key: The metric key
            value: New value
            source: Source of update

        Returns:
            Updated metric or None if not found
        """
        captured_at = datetime.now(UTC) if value is not None else None

        result = self._execute_one(
            """
            UPDATE business_metrics
            SET value = %s,
                captured_at = %s,
                source = %s,
                updated_at = NOW()
            WHERE user_id = %s AND metric_key = %s
            RETURNING id, user_id, metric_key, name, definition, importance,
                      category, value, value_unit, captured_at, source,
                      is_predefined, display_order, is_relevant, created_at, updated_at
            """,
            (value, captured_at, source, user_id, metric_key),
            user_id=user_id,
        )
        return result

    def delete_metric(self, user_id: str, metric_key: str) -> bool:
        """Delete a custom metric (cannot delete predefined).

        Args:
            user_id: User identifier
            metric_key: The metric key

        Returns:
            True if deleted, False if not found or predefined
        """
        # First check if it's predefined
        existing = self.get_user_metric(user_id, metric_key)
        if not existing:
            return False
        if existing.get("is_predefined"):
            logger.warning(f"Cannot delete predefined metric {metric_key} for user {user_id}")
            return False

        count = self._execute_count(
            """
            DELETE FROM business_metrics
            WHERE user_id = %s AND metric_key = %s AND is_predefined = false
            """,
            (user_id, metric_key),
            user_id=user_id,
        )
        return count > 0

    def set_metric_relevance(
        self, user_id: str, metric_key: str, is_relevant: bool
    ) -> dict[str, Any] | None:
        """Set the relevance flag for a predefined metric.

        Only works for predefined metrics. Custom metrics should use delete.

        Args:
            user_id: User identifier
            metric_key: The metric key
            is_relevant: True to show, False to hide

        Returns:
            Updated metric or None if not found/not predefined
        """
        existing = self.get_user_metric(user_id, metric_key)
        if not existing:
            return None
        if not existing.get("is_predefined"):
            logger.warning(f"Cannot set relevance on custom metric {metric_key} for user {user_id}")
            return None

        return self._execute_one(
            """
            UPDATE business_metrics
            SET is_relevant = %s,
                updated_at = NOW()
            WHERE user_id = %s AND metric_key = %s
            RETURNING id, user_id, metric_key, name, definition, importance,
                      category, value, value_unit, captured_at, source,
                      is_predefined, display_order, is_relevant, created_at, updated_at
            """,
            (is_relevant, user_id, metric_key),
            user_id=user_id,
        )

    def initialize_predefined_metrics(
        self, user_id: str, business_model: str | None = None
    ) -> list[dict[str, Any]]:
        """Initialize predefined metrics for a user from templates.

        Creates metric entries with NULL values for all applicable templates.
        Skips metrics that already exist.

        Args:
            user_id: User identifier
            business_model: Filter templates by business model

        Returns:
            List of created/existing metrics
        """
        templates = self.get_templates(business_model)
        created = []

        for template in templates:
            try:
                metric = self.save_metric(
                    user_id=user_id,
                    metric_key=template["metric_key"],
                    value=None,  # Initialize without value
                    name=template["name"],
                    definition=template["definition"],
                    importance=template["importance"],
                    category=template["category"],
                    value_unit=template["value_unit"],
                    is_predefined=True,
                    display_order=template["display_order"],
                )
                created.append(metric)
            except Exception as e:
                logger.warning(f"Failed to initialize metric {template['metric_key']}: {e}")

        return created


# Singleton instance
metrics_repository = MetricsRepository()
