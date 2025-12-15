"""Tests for PersonaSelectorAgent adaptive model selection."""

from unittest.mock import patch

from bo1.agents.selector import PersonaSelectorAgent, bo1_persona_selector_model_total
from bo1.config import MODEL_BY_ROLE
from bo1.constants import ComplexityScores


class TestPersonaSelectorModelSelection:
    """Test adaptive model selection based on complexity."""

    def test_default_model_without_complexity_uses_sonnet(self):
        """Without complexity set, should use Sonnet (default)."""
        agent = PersonaSelectorAgent()
        assert agent.get_default_model() == MODEL_BY_ROLE["selector"]
        assert "sonnet" in MODEL_BY_ROLE["selector"]

    def test_simple_complexity_uses_haiku(self):
        """Complexity 1-3 (simple) should use Haiku."""
        agent = PersonaSelectorAgent()
        for complexity in [1, 2, 3]:
            agent.set_complexity(complexity)
            assert agent.get_default_model() == MODEL_BY_ROLE["selector_haiku"]
            assert "haiku" in MODEL_BY_ROLE["selector_haiku"]

    def test_moderate_complexity_uses_haiku(self):
        """Complexity 4-6 (moderate) should use Haiku."""
        agent = PersonaSelectorAgent()
        for complexity in [4, 5, 6]:
            agent.set_complexity(complexity)
            assert agent.get_default_model() == MODEL_BY_ROLE["selector_haiku"]

    def test_complex_problems_use_sonnet(self):
        """Complexity 7-10 (complex) should use Sonnet."""
        agent = PersonaSelectorAgent()
        for complexity in [7, 8, 9, 10]:
            agent.set_complexity(complexity)
            assert agent.get_default_model() == MODEL_BY_ROLE["selector"]
            assert "sonnet" in MODEL_BY_ROLE["selector"]

    def test_boundary_complexity_6_uses_haiku(self):
        """Complexity 6 (boundary) should use Haiku."""
        agent = PersonaSelectorAgent()
        agent.set_complexity(6)
        assert agent.get_default_model() == MODEL_BY_ROLE["selector_haiku"]

    def test_boundary_complexity_7_uses_sonnet(self):
        """Complexity 7 (boundary) should use Sonnet."""
        agent = PersonaSelectorAgent()
        agent.set_complexity(7)
        assert agent.get_default_model() == MODEL_BY_ROLE["selector"]

    def test_feature_flag_disabled_uses_sonnet_always(self):
        """When feature flag disabled, should always use Sonnet."""
        with patch("bo1.agents.selector.USE_HAIKU_FOR_SIMPLE_PERSONAS", False):
            agent = PersonaSelectorAgent()
            # Even with simple complexity
            agent.set_complexity(3)
            assert agent.get_default_model() == MODEL_BY_ROLE["selector"]

    def test_threshold_constant_value(self):
        """Verify threshold constant matches plan (6)."""
        assert ComplexityScores.HAIKU_SELECTOR_THRESHOLD == 6


class TestPersonaSelectorMetrics:
    """Test Prometheus metrics for model selection."""

    def test_metric_exists(self):
        """Verify metric is defined."""
        assert bo1_persona_selector_model_total is not None
        # Check it's a Counter with correct labels
        assert hasattr(bo1_persona_selector_model_total, "labels")

    def test_metric_labels(self):
        """Verify metric has correct labels."""
        # This will raise if labels don't match
        labeled = bo1_persona_selector_model_total.labels(
            model="haiku",
            complexity_bucket="simple",
        )
        assert labeled is not None
