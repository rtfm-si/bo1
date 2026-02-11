"""Unit tests for improvement plan generator service."""

from unittest.mock import MagicMock, patch

import pytest

from backend.services.action_failure_detector import FailurePatternSummary
from backend.services.improvement_plan_generator import (
    PLAN_CACHE_PREFIX,
    ImprovementPlan,
    ImprovementPlanGenerator,
    PatternInputs,
    Suggestion,
    get_improvement_plan_generator,
)
from backend.services.topic_detector import RepeatedTopic


@pytest.fixture
def mock_redis():
    """Create a mock Redis manager."""
    redis = MagicMock()
    redis.client = MagicMock()
    redis.client.get.return_value = None
    redis.client.setex = MagicMock()
    return redis


@pytest.fixture
def mock_topic_detector():
    """Create a mock topic detector."""
    detector = MagicMock()
    detector.detect_repeated_topics.return_value = []
    return detector


@pytest.fixture
def mock_failure_detector():
    """Create a mock failure detector."""
    detector = MagicMock()
    detector.detect_failure_patterns.return_value = FailurePatternSummary(
        patterns=[],
        failure_rate=0.0,
        total_actions=0,
        failed_actions=0,
        period_days=30,
        by_project={},
        by_category={},
    )
    return detector


@pytest.fixture
def generator(mock_redis, mock_topic_detector, mock_failure_detector):
    """Create generator with mocked dependencies."""
    return ImprovementPlanGenerator(
        redis_manager=mock_redis,
        topic_detector=mock_topic_detector,
        failure_detector=mock_failure_detector,
    )


class TestImprovementPlanGenerator:
    """Tests for ImprovementPlanGenerator class."""

    def test_cache_key(self, generator):
        """Test cache key generation."""
        key = generator._cache_key("user-123")
        assert key == f"{PLAN_CACHE_PREFIX}:user-123"

    def test_get_cached_plan_none(self, generator, mock_redis):
        """Test cache miss returns None."""
        mock_redis.client.get.return_value = None
        result = generator._get_cached_plan("user-123")
        assert result is None

    def test_get_cached_plan_valid(self, generator, mock_redis):
        """Test cache hit returns plan."""
        import json

        cached_data = {
            "suggestions": [
                {
                    "category": "execution",
                    "title": "Test suggestion",
                    "description": "Test description",
                    "action_steps": ["Step 1"],
                    "priority": "high",
                }
            ],
            "generated_at": "2024-01-01T00:00:00",
            "inputs_summary": {"days_analyzed": 30},
            "confidence": 0.5,
        }
        mock_redis.client.get.return_value = json.dumps(cached_data)

        result = generator._get_cached_plan("user-123")

        assert result is not None
        assert len(result.suggestions) == 1
        assert result.suggestions[0].title == "Test suggestion"
        assert result.confidence == 0.5

    def test_get_cached_plan_invalid_json(self, generator, mock_redis):
        """Test cache with invalid JSON returns None."""
        mock_redis.client.get.return_value = "invalid json"
        result = generator._get_cached_plan("user-123")
        assert result is None

    def test_cache_plan(self, generator, mock_redis):
        """Test caching a plan."""
        plan = ImprovementPlan(
            suggestions=[
                Suggestion(
                    category="planning",
                    title="Test",
                    description="Desc",
                    action_steps=["Step"],
                    priority="medium",
                )
            ],
            generated_at="2024-01-01T00:00:00",
            inputs_summary={"days_analyzed": 30},
            confidence=0.6,
        )

        generator._cache_plan("user-123", plan)

        mock_redis.client.setex.assert_called_once()
        args = mock_redis.client.setex.call_args[0]
        assert args[0] == f"{PLAN_CACHE_PREFIX}:user-123"
        assert args[1] == 3600  # 1 hour TTL

    def test_calculate_confidence_no_inputs(self, generator):
        """Test confidence is 0 with no inputs."""
        inputs = PatternInputs(days=30)
        confidence = generator._calculate_confidence(inputs)
        assert confidence == 0.0

    def test_calculate_confidence_with_topics(self, generator):
        """Test confidence increases with topics."""
        inputs = PatternInputs(
            repeated_topics=[
                RepeatedTopic(
                    topic_summary="Topic 1",
                    count=3,
                    first_asked="2024-01-01",
                    last_asked="2024-01-15",
                    conversation_ids=["c1"],
                    representative_messages=["msg1"],
                    similarity_score=0.9,
                ),
                RepeatedTopic(
                    topic_summary="Topic 2",
                    count=2,
                    first_asked="2024-01-02",
                    last_asked="2024-01-16",
                    conversation_ids=["c2"],
                    representative_messages=["msg2"],
                    similarity_score=0.85,
                ),
            ],
            days=30,
        )
        confidence = generator._calculate_confidence(inputs)
        assert confidence >= 0.3  # Minimum threshold

    def test_calculate_confidence_with_failures(self, generator):
        """Test confidence increases with failures."""
        inputs = PatternInputs(
            failure_summary=FailurePatternSummary(
                patterns=[],
                failure_rate=0.4,
                total_actions=10,
                failed_actions=4,
                period_days=30,
                by_project={},
                by_category={},
            ),
            days=30,
        )
        confidence = generator._calculate_confidence(inputs)
        assert confidence >= 0.3

    def test_build_inputs_summary(self, generator):
        """Test building inputs summary."""
        inputs = PatternInputs(
            repeated_topics=[
                RepeatedTopic(
                    topic_summary="Test",
                    count=3,
                    first_asked="",
                    last_asked="",
                    conversation_ids=[],
                    representative_messages=[],
                    similarity_score=0.9,
                )
            ],
            failure_summary=FailurePatternSummary(
                patterns=[],
                failure_rate=0.25,
                total_actions=20,
                failed_actions=5,
                period_days=30,
                by_project={},
                by_category={},
            ),
            days=30,
        )

        summary = generator._build_inputs_summary(inputs)

        assert summary["days_analyzed"] == 30
        assert summary["topics_detected"] == 1
        assert summary["failure_rate"] == 0.25
        assert summary["total_actions"] == 20
        assert summary["failed_actions"] == 5


class TestGeneratePlan:
    """Tests for generate_plan method."""

    @pytest.mark.asyncio
    async def test_returns_cached_plan(self, generator, mock_redis):
        """Test returns cached plan when available."""
        import json

        cached = {
            "suggestions": [
                {
                    "category": "execution",
                    "title": "Cached",
                    "description": "From cache",
                    "action_steps": [],
                    "priority": "low",
                }
            ],
            "generated_at": "2024-01-01T00:00:00",
            "inputs_summary": {},
            "confidence": 0.5,
        }
        mock_redis.client.get.return_value = json.dumps(cached)

        result = await generator.generate_plan("user-123")

        assert result.suggestions[0].title == "Cached"

    @pytest.mark.asyncio
    async def test_bypasses_cache_with_force_refresh(self, generator, mock_redis):
        """Test force_refresh bypasses cache."""
        import json

        cached = {
            "suggestions": [],
            "generated_at": "2024-01-01T00:00:00",
            "inputs_summary": {},
            "confidence": 0.0,
        }
        mock_redis.client.get.return_value = json.dumps(cached)

        # With no inputs, should return "on track" message
        result = await generator.generate_plan("user-123", force_refresh=True)

        # Should not use cached empty plan, should generate new one
        assert len(result.suggestions) == 1
        assert "on track" in result.suggestions[0].title.lower()

    @pytest.mark.asyncio
    async def test_returns_on_track_when_no_patterns(self, generator):
        """Test returns 'on track' message when no patterns detected."""
        result = await generator.generate_plan("user-123")

        assert len(result.suggestions) == 1
        assert result.suggestions[0].category == "status"
        assert "on track" in result.suggestions[0].title.lower()
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    @patch("backend.services.improvement_plan_generator.get_mentor_conversation_repo")
    async def test_gathers_inputs_from_detectors(
        self, mock_conv_repo, generator, mock_topic_detector, mock_failure_detector
    ):
        """Test gathers inputs from both detectors."""
        mock_conv_repo.return_value.get_all_user_messages.return_value = []

        await generator.generate_plan("user-123", days=60)

        mock_topic_detector.detect_repeated_topics.assert_called_once()
        mock_failure_detector.detect_failure_patterns.assert_called_once()

        # Check days parameter was passed
        failure_call_kwargs = mock_failure_detector.detect_failure_patterns.call_args[1]
        assert failure_call_kwargs["days"] == 60


class TestParseSuggestions:
    """Tests for _parse_suggestions method."""

    def test_parse_valid_suggestions(self, generator):
        """Test parsing valid XML suggestions."""
        response = """
        <suggestions>
          <suggestion>
            <category>execution</category>
            <title>Break down large tasks</title>
            <description>You tend to cancel large tasks. Break them into smaller pieces.</description>
            <action_steps>
              <step>Review task size before starting</step>
              <step>Split tasks over 4 hours</step>
            </action_steps>
            <priority>high</priority>
          </suggestion>
        </suggestions>
        """

        result = generator._parse_suggestions(response)

        assert len(result) == 1
        assert result[0].category == "execution"
        assert result[0].title == "Break down large tasks"
        assert len(result[0].action_steps) == 2
        assert result[0].priority == "high"

    def test_parse_multiple_suggestions(self, generator):
        """Test parsing multiple suggestions."""
        response = """
        <suggestions>
          <suggestion>
            <category>planning</category>
            <title>First suggestion</title>
            <description>First desc</description>
            <action_steps><step>Step 1</step></action_steps>
            <priority>high</priority>
          </suggestion>
          <suggestion>
            <category>knowledge</category>
            <title>Second suggestion</title>
            <description>Second desc</description>
            <action_steps><step>Step A</step></action_steps>
            <priority>medium</priority>
          </suggestion>
        </suggestions>
        """

        result = generator._parse_suggestions(response)

        assert len(result) == 2
        assert result[0].category == "planning"
        assert result[1].category == "knowledge"

    def test_parse_invalid_category_defaults_to_general(self, generator):
        """Test invalid category defaults to 'general'."""
        response = """
        <suggestions>
          <suggestion>
            <category>invalid_category</category>
            <title>Test</title>
            <description>Desc</description>
            <action_steps></action_steps>
            <priority>high</priority>
          </suggestion>
        </suggestions>
        """

        result = generator._parse_suggestions(response)

        assert result[0].category == "general"

    def test_parse_invalid_priority_defaults_to_medium(self, generator):
        """Test invalid priority defaults to 'medium'."""
        response = """
        <suggestions>
          <suggestion>
            <category>execution</category>
            <title>Test</title>
            <description>Desc</description>
            <action_steps></action_steps>
            <priority>urgent</priority>
          </suggestion>
        </suggestions>
        """

        result = generator._parse_suggestions(response)

        assert result[0].priority == "medium"

    def test_parse_limits_to_5_suggestions(self, generator):
        """Test limits output to 5 suggestions."""
        suggestions = "\n".join(
            [
                f"""
                <suggestion>
                  <category>execution</category>
                  <title>Suggestion {i}</title>
                  <description>Desc {i}</description>
                  <action_steps></action_steps>
                  <priority>medium</priority>
                </suggestion>
                """
                for i in range(10)
            ]
        )
        response = f"<suggestions>{suggestions}</suggestions>"

        result = generator._parse_suggestions(response)

        assert len(result) == 5

    def test_parse_limits_action_steps_to_5(self, generator):
        """Test limits action steps to 5."""
        steps = "\n".join([f"<step>Step {i}</step>" for i in range(10)])
        response = f"""
        <suggestions>
          <suggestion>
            <category>process</category>
            <title>Test</title>
            <description>Desc</description>
            <action_steps>{steps}</action_steps>
            <priority>low</priority>
          </suggestion>
        </suggestions>
        """

        result = generator._parse_suggestions(response)

        assert len(result[0].action_steps) == 5

    def test_parse_empty_response(self, generator):
        """Test parsing empty response."""
        result = generator._parse_suggestions("")
        assert len(result) == 0

    def test_parse_malformed_xml(self, generator):
        """Test gracefully handles malformed XML."""
        response = "<suggestions><suggestion>malformed</suggestion></suggestions>"
        result = generator._parse_suggestions(response)
        # Should return empty or partial results, not crash
        assert isinstance(result, list)


class TestExtractTag:
    """Tests for _extract_tag helper."""

    def test_extract_existing_tag(self, generator):
        """Test extracting an existing tag."""
        text = "<title>My Title</title>"
        result = generator._extract_tag(text, "title")
        assert result == "My Title"

    def test_extract_missing_tag(self, generator):
        """Test extracting a missing tag returns None."""
        text = "<other>value</other>"
        result = generator._extract_tag(text, "title")
        assert result is None

    def test_extract_multiline_content(self, generator):
        """Test extracting multiline content."""
        text = """<description>
        Line 1
        Line 2
        </description>"""
        result = generator._extract_tag(text, "description")
        assert "Line 1" in result
        assert "Line 2" in result


class TestSingleton:
    """Tests for singleton pattern."""

    def test_get_improvement_plan_generator_returns_same_instance(self):
        """Test singleton returns same instance."""
        # Reset singleton
        get_improvement_plan_generator.cache_clear()

        gen1 = get_improvement_plan_generator()
        gen2 = get_improvement_plan_generator()

        assert gen1 is gen2

        # Reset for other tests
        get_improvement_plan_generator.cache_clear()
