"""Improvement plan generator for proactive mentoring.

Generates LLM-powered improvement plans from detected patterns:
- Repeated topics from mentor conversations
- Action failure patterns
"""

import json
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from backend.services.action_failure_detector import (
    ActionFailureDetector,
    FailurePatternSummary,
    get_action_failure_detector,
)
from backend.services.mentor_conversation_repo import get_mentor_conversation_repo
from backend.services.topic_detector import (
    RepeatedTopic,
    TopicDetector,
    get_topic_detector,
)
from bo1.llm.client import ClaudeClient
from bo1.prompts.improvement_plan import (
    build_improvement_plan_prompt,
    get_improvement_plan_system_prompt,
)
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# Redis cache config
PLAN_CACHE_PREFIX = "improvement_plan"
PLAN_CACHE_TTL = 3600  # 1 hour


@dataclass
class Suggestion:
    """A single improvement suggestion."""

    category: str  # execution, planning, knowledge, process
    title: str
    description: str
    action_steps: list[str]
    priority: str  # high, medium, low


@dataclass
class ImprovementPlan:
    """Generated improvement plan with suggestions."""

    suggestions: list[Suggestion]
    generated_at: str
    inputs_summary: dict[str, Any]
    confidence: float = 0.0  # 0.0-1.0, based on input quality


@dataclass
class PatternInputs:
    """Collected pattern inputs for plan generation."""

    repeated_topics: list[RepeatedTopic] = field(default_factory=list)
    failure_summary: FailurePatternSummary | None = None
    days: int = 30


class ImprovementPlanGenerator:
    """Generates improvement plans from user patterns.

    Uses TopicDetector + ActionFailureDetector to gather patterns,
    then LLM to generate actionable improvement suggestions.
    """

    def __init__(
        self,
        redis_manager: RedisManager | None = None,
        topic_detector: TopicDetector | None = None,
        failure_detector: ActionFailureDetector | None = None,
    ) -> None:
        """Initialize the generator.

        Args:
            redis_manager: Optional Redis manager for caching
            topic_detector: Optional topic detector instance
            failure_detector: Optional failure detector instance
        """
        self._redis = redis_manager or RedisManager()
        self._topic_detector = topic_detector or get_topic_detector()
        self._failure_detector = failure_detector or get_action_failure_detector()

    def _cache_key(self, user_id: str) -> str:
        """Generate cache key for a user's plan."""
        return f"{PLAN_CACHE_PREFIX}:{user_id}"

    def _get_cached_plan(self, user_id: str) -> ImprovementPlan | None:
        """Get cached plan if available."""
        key = self._cache_key(user_id)
        data = self._redis.client.get(key)
        if not data:
            return None

        try:
            parsed = json.loads(data)
            return ImprovementPlan(
                suggestions=[Suggestion(**s) for s in parsed.get("suggestions", [])],
                generated_at=parsed.get("generated_at", ""),
                inputs_summary=parsed.get("inputs_summary", {}),
                confidence=parsed.get("confidence", 0.0),
            )
        except Exception as e:
            logger.warning(f"Failed to parse cached plan: {e}")
            return None

    def _cache_plan(self, user_id: str, plan: ImprovementPlan) -> None:
        """Cache a generated plan."""
        key = self._cache_key(user_id)
        data = {
            "suggestions": [
                {
                    "category": s.category,
                    "title": s.title,
                    "description": s.description,
                    "action_steps": s.action_steps,
                    "priority": s.priority,
                }
                for s in plan.suggestions
            ],
            "generated_at": plan.generated_at,
            "inputs_summary": plan.inputs_summary,
            "confidence": plan.confidence,
        }
        self._redis.client.setex(key, PLAN_CACHE_TTL, json.dumps(data))

    def _gather_inputs(self, user_id: str, days: int) -> PatternInputs:
        """Gather pattern inputs from detectors.

        Args:
            user_id: User to analyze
            days: Days to look back

        Returns:
            PatternInputs with topics and failures
        """
        inputs = PatternInputs(days=days)

        # Get repeated topics
        try:
            conv_repo = get_mentor_conversation_repo()
            messages = conv_repo.get_all_user_messages(user_id, days=days)
            inputs.repeated_topics = self._topic_detector.detect_repeated_topics(
                user_id=user_id,
                messages=messages,
                threshold=0.85,
                min_occurrences=2,  # Lower threshold for plan generation
            )
        except Exception as e:
            logger.warning(f"Failed to get repeated topics: {e}")

        # Get failure patterns
        try:
            inputs.failure_summary = self._failure_detector.detect_failure_patterns(
                user_id=user_id,
                days=days,
                min_failures=2,  # Lower threshold for plan generation
            )
        except Exception as e:
            logger.warning(f"Failed to get failure patterns: {e}")

        return inputs

    def _calculate_confidence(self, inputs: PatternInputs) -> float:
        """Calculate confidence score based on input quality."""
        score = 0.0

        # Topics contribute up to 0.4
        if inputs.repeated_topics:
            topic_score = min(len(inputs.repeated_topics) / 5, 1.0) * 0.4
            score += topic_score

        # Failures contribute up to 0.4
        if inputs.failure_summary and inputs.failure_summary.failed_actions >= 3:
            failure_score = min(inputs.failure_summary.failed_actions / 10, 1.0) * 0.4
            score += failure_score

        # Baseline confidence if we have any data
        if score > 0:
            score = max(score, 0.3)  # Minimum 30% if we have data

        return round(score, 2)

    def _build_inputs_summary(self, inputs: PatternInputs) -> dict[str, Any]:
        """Build a summary of inputs used for the plan."""
        summary: dict[str, Any] = {
            "days_analyzed": inputs.days,
            "topics_detected": len(inputs.repeated_topics),
        }

        if inputs.failure_summary:
            summary["failure_rate"] = round(inputs.failure_summary.failure_rate, 2)
            summary["total_actions"] = inputs.failure_summary.total_actions
            summary["failed_actions"] = inputs.failure_summary.failed_actions

        return summary

    async def generate_plan(
        self,
        user_id: str,
        days: int = 30,
        force_refresh: bool = False,
    ) -> ImprovementPlan:
        """Generate an improvement plan for a user.

        Args:
            user_id: User to generate plan for
            days: Days to look back (7-90)
            force_refresh: Bypass cache and regenerate

        Returns:
            ImprovementPlan with suggestions and metadata
        """
        # Check cache first
        if not force_refresh:
            cached = self._get_cached_plan(user_id)
            if cached:
                return cached

        # Gather inputs
        inputs = self._gather_inputs(user_id, days)

        # Check if we have enough data
        if not inputs.repeated_topics and (
            not inputs.failure_summary or inputs.failure_summary.failed_actions == 0
        ):
            # Return empty plan with "on track" message
            return ImprovementPlan(
                suggestions=[
                    Suggestion(
                        category="status",
                        title="You're on track!",
                        description="No significant patterns detected that require attention. "
                        "Keep up the good work!",
                        action_steps=["Continue current practices", "Check back in a few weeks"],
                        priority="low",
                    )
                ],
                generated_at=datetime.now(UTC).isoformat(),
                inputs_summary=self._build_inputs_summary(inputs),
                confidence=0.0,
            )

        # Build prompt and call LLM
        try:
            suggestions = await self._generate_suggestions(inputs)
            confidence = self._calculate_confidence(inputs)

            plan = ImprovementPlan(
                suggestions=suggestions,
                generated_at=datetime.now(UTC).isoformat(),
                inputs_summary=self._build_inputs_summary(inputs),
                confidence=confidence,
            )

            # Cache the result
            self._cache_plan(user_id, plan)
            return plan

        except Exception as e:
            logger.error(f"Failed to generate improvement plan: {e}")
            # Return fallback plan
            return ImprovementPlan(
                suggestions=[
                    Suggestion(
                        category="error",
                        title="Unable to generate plan",
                        description="We encountered an issue analyzing your patterns. "
                        "Please try again later.",
                        action_steps=["Try again in a few minutes"],
                        priority="medium",
                    )
                ],
                generated_at=datetime.now(UTC).isoformat(),
                inputs_summary=self._build_inputs_summary(inputs),
                confidence=0.0,
            )

    async def _generate_suggestions(self, inputs: PatternInputs) -> list[Suggestion]:
        """Generate suggestions via LLM.

        Args:
            inputs: Pattern inputs to analyze

        Returns:
            List of Suggestion objects
        """
        # Build prompt
        prompt = build_improvement_plan_prompt(
            repeated_topics=inputs.repeated_topics,
            failure_summary=inputs.failure_summary,
        )

        system_prompt = get_improvement_plan_system_prompt()

        # Call LLM
        client = ClaudeClient()
        response, _usage = await client.call(
            model="haiku",  # Use Haiku for cost efficiency
            system=system_prompt,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.3,  # Lower temp for structured output
        )

        # Parse response
        return self._parse_suggestions(response)

    def _parse_suggestions(self, response: str) -> list[Suggestion]:
        """Parse LLM response into Suggestion objects.

        Expected format:
        <suggestions>
          <suggestion>
            <category>execution</category>
            <title>...</title>
            <description>...</description>
            <action_steps>
              <step>...</step>
            </action_steps>
            <priority>high</priority>
          </suggestion>
        </suggestions>
        """
        import re

        suggestions: list[Suggestion] = []

        # Find all suggestion blocks
        suggestion_pattern = r"<suggestion>(.*?)</suggestion>"
        matches = re.findall(suggestion_pattern, response, re.DOTALL)

        for match in matches:
            try:
                # Extract fields
                category = self._extract_tag(match, "category") or "general"
                title = self._extract_tag(match, "title") or "Untitled"
                description = self._extract_tag(match, "description") or ""
                priority = self._extract_tag(match, "priority") or "medium"

                # Extract action steps
                steps_match = re.search(r"<action_steps>(.*?)</action_steps>", match, re.DOTALL)
                action_steps = []
                if steps_match:
                    step_pattern = r"<step>(.*?)</step>"
                    action_steps = re.findall(step_pattern, steps_match.group(1), re.DOTALL)
                    action_steps = [s.strip() for s in action_steps if s.strip()]

                # Validate category and priority
                valid_categories = {
                    "execution",
                    "planning",
                    "knowledge",
                    "process",
                    "status",
                    "error",
                }
                if category not in valid_categories:
                    category = "general"

                valid_priorities = {"high", "medium", "low"}
                if priority not in valid_priorities:
                    priority = "medium"

                suggestions.append(
                    Suggestion(
                        category=category,
                        title=title.strip(),
                        description=description.strip(),
                        action_steps=action_steps[:5],  # Max 5 steps
                        priority=priority,
                    )
                )

            except Exception as e:
                logger.warning(f"Failed to parse suggestion: {e}")
                continue

        # Limit to 5 suggestions
        return suggestions[:5]

    def _extract_tag(self, text: str, tag: str) -> str | None:
        """Extract content from an XML tag."""
        import re

        pattern = rf"<{tag}>(.*?)</{tag}>"
        match = re.search(pattern, text, re.DOTALL)
        return match.group(1).strip() if match else None


# Module-level singleton


@lru_cache(maxsize=1)
def get_improvement_plan_generator() -> ImprovementPlanGenerator:
    """Get or create the improvement plan generator singleton."""
    return ImprovementPlanGenerator()
