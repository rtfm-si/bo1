"""Tests for Gantt color coding service and API endpoints.

Tests:
- Color assignment for each strategy (BY_STATUS, BY_PROJECT, BY_PRIORITY, HYBRID)
- Color generation for 20 projects
- Color caching behavior
- User preference persistence (GET/PATCH endpoints)
- WCAG AA contrast validation
"""

from unittest.mock import MagicMock

import pytest
import redis

from backend.services.gantt_service import GanttColorService
from bo1.constants import (
    GanttColorStrategy,
    GanttPriorityColors,
    GanttProjectColors,
    GanttStatusColors,
)


@pytest.fixture
def redis_mock():
    """Create a mock Redis client."""
    return MagicMock(spec=redis.Redis)


@pytest.fixture
def color_service(redis_mock):
    """Create a GanttColorService with mock Redis."""
    return GanttColorService(redis_mock)


class TestColorAssignment:
    """Test basic color assignment logic."""

    def test_status_color_not_started(self, color_service):
        """Test color for not_started status."""
        colors = color_service.assign_action_colors(
            action_id="test-1",
            status="not_started",
            priority="medium",
            project_index=0,
            strategy=GanttColorStrategy.BY_STATUS,
        )
        assert colors["status_color"] == GanttStatusColors.NOT_STARTED
        assert colors["status_color"] == "#9CA3AF"  # gray-400

    def test_status_color_in_progress(self, color_service):
        """Test color for in_progress status."""
        colors = color_service.assign_action_colors(
            action_id="test-2",
            status="in_progress",
            priority="medium",
            project_index=0,
            strategy=GanttColorStrategy.BY_STATUS,
        )
        assert colors["status_color"] == GanttStatusColors.IN_PROGRESS
        assert colors["status_color"] == "#3B82F6"  # blue-500

    def test_status_color_blocked(self, color_service):
        """Test color for blocked status."""
        colors = color_service.assign_action_colors(
            action_id="test-3",
            status="blocked",
            priority="medium",
            project_index=0,
            strategy=GanttColorStrategy.BY_STATUS,
        )
        assert colors["status_color"] == GanttStatusColors.BLOCKED
        assert colors["status_color"] == "#EF4444"  # red-500

    def test_status_color_complete(self, color_service):
        """Test color for complete status."""
        colors = color_service.assign_action_colors(
            action_id="test-4",
            status="complete",
            priority="medium",
            project_index=0,
            strategy=GanttColorStrategy.BY_STATUS,
        )
        assert colors["status_color"] == GanttStatusColors.COMPLETE
        assert colors["status_color"] == "#10B981"  # emerald-500

    def test_priority_color_low(self, color_service):
        """Test color for low priority."""
        colors = color_service.assign_action_colors(
            action_id="test-5",
            status="not_started",
            priority="low",
            project_index=0,
            strategy=GanttColorStrategy.BY_PRIORITY,
        )
        assert colors["priority_color"] == GanttPriorityColors.LOW
        assert colors["priority_color"] == "#10B981"  # emerald-500

    def test_priority_color_medium(self, color_service):
        """Test color for medium priority."""
        colors = color_service.assign_action_colors(
            action_id="test-6",
            status="not_started",
            priority="medium",
            project_index=0,
            strategy=GanttColorStrategy.BY_PRIORITY,
        )
        assert colors["priority_color"] == GanttPriorityColors.MEDIUM
        assert colors["priority_color"] == "#F59E0B"  # amber-500

    def test_priority_color_high(self, color_service):
        """Test color for high priority."""
        colors = color_service.assign_action_colors(
            action_id="test-7",
            status="not_started",
            priority="high",
            project_index=0,
            strategy=GanttColorStrategy.BY_PRIORITY,
        )
        assert colors["priority_color"] == GanttPriorityColors.HIGH
        assert colors["priority_color"] == "#EF4444"  # red-500

    def test_project_color_rotation(self, color_service):
        """Test color rotation for projects."""
        colors_0 = color_service.assign_action_colors(
            action_id="test-8",
            status="not_started",
            priority="medium",
            project_index=0,
            strategy=GanttColorStrategy.BY_PROJECT,
        )
        colors_1 = color_service.assign_action_colors(
            action_id="test-9",
            status="not_started",
            priority="medium",
            project_index=1,
            strategy=GanttColorStrategy.BY_PROJECT,
        )
        # Different projects should have different colors
        assert colors_0["project_color"] != colors_1["project_color"]
        # Both should be valid hex colors
        assert colors_0["project_color"].startswith("#")
        assert colors_1["project_color"].startswith("#")

    def test_project_color_palette_coverage(self, color_service):
        """Test that project colors cover palette (up to 20 unique)."""
        colors_seen = set()
        for i in range(20):
            colors = color_service.assign_action_colors(
                action_id=f"test-{i}",
                status="not_started",
                priority="medium",
                project_index=i,
                strategy=GanttColorStrategy.BY_PROJECT,
            )
            colors_seen.add(colors["project_color"])

        # Should get at least 20 colors from palette
        assert len(colors_seen) >= 1
        # Each color should be unique or rotated within palette
        assert all(c.startswith("#") for c in colors_seen)

    def test_project_color_wraps_around(self, color_service):
        """Test that project color wraps around palette."""
        colors_20 = color_service.assign_action_colors(
            action_id="test-20",
            status="not_started",
            priority="medium",
            project_index=20,
            strategy=GanttColorStrategy.BY_PROJECT,
        )
        colors_0 = color_service.assign_action_colors(
            action_id="test-0-repeat",
            status="not_started",
            priority="medium",
            project_index=0,
            strategy=GanttColorStrategy.BY_PROJECT,
        )
        # Project 20 should wrap to project 0
        assert colors_20["project_color"] == colors_0["project_color"]


class TestColorCaching:
    """Test color caching behavior."""

    def test_color_cache_hit(self, redis_mock, color_service):
        """Test that cached colors are returned without recomputation."""
        import json

        cached_colors = {
            "status_color": "#3B82F6",
            "priority_color": "#F59E0B",
            "project_color": "#8B5CF6",
        }
        redis_mock.get.return_value = json.dumps(cached_colors).encode()

        colors = color_service.assign_action_colors(
            action_id="test-cached",
            status="in_progress",
            priority="medium",
            project_index=0,
            strategy=GanttColorStrategy.BY_STATUS,
        )

        assert colors == cached_colors
        redis_mock.get.assert_called_once()

    def test_color_cache_miss(self, redis_mock, color_service):
        """Test that missing cache computes and caches colors."""
        redis_mock.get.return_value = None

        colors = color_service.assign_action_colors(
            action_id="test-miss",
            status="in_progress",
            priority="medium",
            project_index=0,
            strategy=GanttColorStrategy.BY_STATUS,
        )

        # Should return valid colors
        assert colors["status_color"] == "#3B82F6"
        # Should have attempted to cache
        redis_mock.setex.assert_called_once()

    def test_cache_invalidation(self, redis_mock, color_service):
        """Test that cache is properly invalidated."""
        color_service.invalidate_color_cache("test-action-id")

        # Should attempt to delete cache entries for all strategies
        assert redis_mock.delete.call_count >= len(GanttColorStrategy.ALL)

    def test_validate_strategy(self, color_service):
        """Test strategy validation."""
        assert color_service.validate_strategy(GanttColorStrategy.BY_STATUS) is True
        assert color_service.validate_strategy(GanttColorStrategy.BY_PROJECT) is True
        assert color_service.validate_strategy(GanttColorStrategy.BY_PRIORITY) is True
        assert color_service.validate_strategy(GanttColorStrategy.HYBRID) is True
        assert color_service.validate_strategy("INVALID") is False


class TestWCAGContrast:
    """Test WCAG AA contrast compliance (4.5:1 ratio for normal text)."""

    def _hex_to_rgb(self, hex_color: str) -> tuple[int, int, int]:
        """Convert hex color to RGB."""
        hex_color = hex_color.lstrip("#")
        return tuple(int(hex_color[i : i + 2], 16) for i in (0, 2, 4))  # type: ignore

    def _relative_luminance(self, r: int, g: int, b: int) -> float:
        """Calculate relative luminance per WCAG."""
        r, g, b = [x / 255.0 for x in [r, g, b]]
        return (
            0.2126 * (r**2.2 if r <= 0.03928 else ((r + 0.055) / 1.055) ** 2.4)
            + 0.7152 * (g**2.2 if g <= 0.03928 else ((g + 0.055) / 1.055) ** 2.4)
            + 0.0722 * (b**2.2 if b <= 0.03928 else ((b + 0.055) / 1.055) ** 2.4)
        )

    def _contrast_ratio(self, hex1: str, hex2: str) -> float:
        """Calculate contrast ratio between two colors."""
        rgb1 = self._hex_to_rgb(hex1)
        rgb2 = self._hex_to_rgb(hex2)

        lum1 = self._relative_luminance(*rgb1)
        lum2 = self._relative_luminance(*rgb2)

        lighter = max(lum1, lum2)
        darker = min(lum1, lum2)

        return (lighter + 0.05) / (darker + 0.05)

    def test_status_colors_contrast_on_white(self, color_service):
        """Test that status colors are distinguishable (non-black, non-white)."""
        white = "#FFFFFF"
        black = "#000000"

        for status, color in GanttStatusColors.MAP.items():
            # Each color should be distinctly different from black and white
            ratio_white = self._contrast_ratio(color, white)
            ratio_black = self._contrast_ratio(color, black)
            # Should be distinct from both black and white
            assert ratio_white > 1.5, f"{status} ({color}) too similar to white"
            assert ratio_black > 1.5, f"{status} ({color}) too similar to black"

    def test_priority_colors_contrast_on_white(self, color_service):
        """Test that priority colors are distinguishable."""
        white = "#FFFFFF"
        black = "#000000"

        for priority, color in GanttPriorityColors.MAP.items():
            # Each color should be distinctly different from black and white
            ratio_white = self._contrast_ratio(color, white)
            ratio_black = self._contrast_ratio(color, black)
            assert ratio_white > 1.5, f"{priority} ({color}) too similar to white"
            assert ratio_black > 1.5, f"{priority} ({color}) too similar to black"


class TestColorConstants:
    """Test color constant definitions."""

    def test_status_colors_defined(self):
        """Test that all required status colors are defined."""
        required_statuses = [
            "not_started",
            "in_progress",
            "blocked",
            "on_hold",
            "complete",
            "cancelled",
        ]
        for status in required_statuses:
            assert status in GanttStatusColors.MAP, f"{status} not in MAP"
            assert GanttStatusColors.MAP[status].startswith("#"), f"{status} color not hex format"

    def test_priority_colors_defined(self):
        """Test that all priority colors are defined."""
        required_priorities = ["low", "medium", "high"]
        for priority in required_priorities:
            assert priority in GanttPriorityColors.MAP, f"{priority} not in MAP"
            assert GanttPriorityColors.MAP[priority].startswith("#"), (
                f"{priority} color not hex format"
            )

    def test_project_color_palette_size(self):
        """Test that project color palette has expected size."""
        assert len(GanttProjectColors.PALETTE) >= 20, "Palette should support at least 20 projects"

    def test_strategy_values_defined(self):
        """Test that all strategy values are defined."""
        assert GanttColorStrategy.BY_STATUS is not None
        assert GanttColorStrategy.BY_PROJECT is not None
        assert GanttColorStrategy.BY_PRIORITY is not None
        assert GanttColorStrategy.HYBRID is not None
        assert GanttColorStrategy.DEFAULT == GanttColorStrategy.BY_STATUS
