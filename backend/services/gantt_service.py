"""Gantt chart color assignment service.

Provides color coding for actions based on strategy (by status, project, priority, or hybrid).
Includes caching to avoid recomputation on each request.
"""

import json
import logging

import redis

from bo1.constants import (
    GanttColorCache,
    GanttColorStrategy,
    GanttPriorityColors,
    GanttProjectColors,
    GanttStatusColors,
)

logger = logging.getLogger(__name__)


class GanttColorService:
    """Service for assigning colors to actions based on strategy."""

    def __init__(self, redis_client: redis.Redis) -> None:  # type: ignore[type-arg]
        """Initialize the Gantt color service.

        Args:
            redis_client: Redis client for caching colors
        """
        self.redis = redis_client

    def assign_action_colors(
        self,
        action_id: str,
        status: str,
        priority: str,
        project_index: int,
        strategy: str = GanttColorStrategy.BY_STATUS,
    ) -> dict[str, str | None]:
        """Assign colors to an action based on the strategy.

        Returns a dict with status_color, priority_color, project_color.
        The relevant color depends on the strategy:
        - BY_STATUS: use status_color for the main bar
        - BY_PROJECT: use project_color for the main bar
        - BY_PRIORITY: use priority_color for the main bar
        - HYBRID: use status_color as primary + project_color as accent

        Args:
            action_id: Action UUID
            status: Action status (e.g., "in_progress")
            priority: Action priority (e.g., "high")
            project_index: Project index for rotating through project colors
            strategy: Color strategy to apply

        Returns:
            Dictionary with keys: status_color, priority_color, project_color
        """
        # Check cache first
        cache_key = self._build_cache_key(action_id, strategy)
        cached = self._get_cached_colors(cache_key)
        if cached is not None:
            return cached

        # Compute colors
        colors = {
            "status_color": self._get_status_color(status),
            "priority_color": self._get_priority_color(priority),
            "project_color": self._get_project_color(project_index),
        }

        # Cache for 10 minutes
        self._cache_colors(cache_key, colors)

        return colors

    def _get_status_color(self, status: str) -> str | None:
        """Get color for a given status.

        Args:
            status: Status string (e.g., "in_progress")

        Returns:
            Hex color string or None if status not recognized
        """
        normalized = status.lower().strip() if status else None
        if not normalized:
            return GanttStatusColors.NOT_STARTED

        return GanttStatusColors.MAP.get(normalized, GanttStatusColors.NOT_STARTED)

    def _get_priority_color(self, priority: str) -> str | None:
        """Get color for a given priority.

        Args:
            priority: Priority string (e.g., "high")

        Returns:
            Hex color string or None if priority not recognized
        """
        normalized = priority.lower().strip() if priority else None
        if not normalized:
            return None

        return GanttPriorityColors.MAP.get(normalized)

    def _get_project_color(self, project_index: int) -> str | None:
        """Get color for a project by index.

        Args:
            project_index: 0-based project index

        Returns:
            Hex color string
        """
        if project_index < 0:
            return None

        return GanttProjectColors.get_color_for_project(project_index)

    def _build_cache_key(self, action_id: str, strategy: str) -> str:
        """Build Redis cache key.

        Args:
            action_id: Action UUID
            strategy: Color strategy

        Returns:
            Redis cache key
        """
        return f"{GanttColorCache.KEY_PREFIX}{action_id}:{strategy}"

    def _get_cached_colors(self, cache_key: str) -> dict[str, str | None] | None:
        """Get cached colors from Redis.

        Args:
            cache_key: Redis cache key

        Returns:
            Cached color dict or None if not found
        """
        try:
            cached_json = self.redis.get(cache_key)
            if cached_json:
                return json.loads(cached_json)
        except Exception as e:
            logger.warning(f"Failed to retrieve cached colors: {e}")

        return None

    def _cache_colors(self, cache_key: str, colors: dict[str, str | None]) -> None:
        """Cache colors in Redis.

        Args:
            cache_key: Redis cache key
            colors: Colors dict to cache
        """
        try:
            self.redis.setex(
                cache_key,
                GanttColorCache.TTL_SECONDS,
                json.dumps(colors),
            )
        except Exception as e:
            logger.warning(f"Failed to cache colors: {e}")

    def invalidate_color_cache(self, action_id: str) -> None:
        """Invalidate all cached colors for an action.

        Called when action is updated (status, priority, project).

        Args:
            action_id: Action UUID to invalidate
        """
        try:
            for strategy in GanttColorStrategy.ALL:
                cache_key = self._build_cache_key(action_id, strategy)
                self.redis.delete(cache_key)
        except Exception as e:
            logger.warning(f"Failed to invalidate color cache: {e}")

    def validate_strategy(self, strategy: str) -> bool:
        """Validate that strategy is one of the allowed values.

        Args:
            strategy: Strategy string to validate

        Returns:
            True if valid, False otherwise
        """
        return strategy in GanttColorStrategy.ALL
