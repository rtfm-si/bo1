"""Task extraction from synthesis recommendations.

Parses synthesis XML to identify discrete, actionable tasks.
"""

import json

from anthropic import Anthropic
from pydantic import BaseModel, Field

from bo1.config import get_model_for_role
from bo1.llm.context import get_cost_context
from bo1.llm.cost_tracker import CostTracker
from bo1.prompts.task_extractor_prompts import (
    TASK_EXTRACTOR_PREFILL,
    TASK_EXTRACTOR_SYSTEM_PROMPT,
    TASK_EXTRACTOR_USER_TEMPLATE,
)


class ExtractedTask(BaseModel):
    """Represents a discrete, actionable task from synthesis."""

    id: str = Field(description="Unique task ID")
    title: str = Field(description="Short, clear title for the task (5-10 words)")
    description: str = Field(description="Clear, actionable task description (the 'what')")
    what_and_how: list[str] = Field(
        default_factory=list,
        description="What needs to be done and how to achieve it (max 3 bullets)",
    )
    success_criteria: list[str] = Field(
        default_factory=list,
        description="What success looks like (max 2 bullets)",
    )
    kill_criteria: list[str] = Field(
        default_factory=list,
        description="Conditions under which this action should be killed/replanned",
    )
    dependencies: list[str] = Field(
        default_factory=list, description="Prerequisites or things that need to happen first"
    )
    timeline: str = Field(description="How long this will take (e.g., '2 weeks', '1 month')")
    priority: str = Field(description="high, medium, low")
    category: str = Field(description="Category: implementation, research, decision, communication")
    source_section: str = Field(description="Which synthesis section this came from")
    confidence: float = Field(description="AI confidence in task extraction (0-1)", ge=0.0, le=1.0)
    sub_problem_index: int | None = Field(
        default=None,
        description="Which sub-problem this action belongs to (None = applies to all)",
    )
    estimated_duration_days: int | None = Field(
        default=None,
        description="Parsed timeline in business days (auto-calculated from timeline)",
    )
    # Legacy field for backwards compatibility
    suggested_completion_date: str | None = Field(
        default=None, description="ISO date or relative (e.g., 'Week 1') - use timeline instead"
    )


class TaskExtractionResult(BaseModel):
    """Result of task extraction from synthesis."""

    tasks: list[ExtractedTask]
    total_tasks: int
    extraction_confidence: float = Field(ge=0.0, le=1.0)
    synthesis_sections_analyzed: list[str]


async def extract_tasks_from_synthesis(
    synthesis: str,
    session_id: str,
    anthropic_api_key: str,
    sub_problem_index: int | None = None,
    total_sub_problems: int = 1,
    other_sub_problem_goals: list[str] | None = None,
) -> TaskExtractionResult:
    """Extract actionable tasks from synthesis using Claude.

    Args:
        synthesis: XML-formatted synthesis report
        session_id: Session ID for tracking
        anthropic_api_key: Anthropic API key
        sub_problem_index: Index of this sub-problem (for cross-sp dependencies)
        total_sub_problems: Total number of sub-problems in session
        other_sub_problem_goals: Goals of other sub-problems for context

    Returns:
        TaskExtractionResult with extracted tasks

    Raises:
        ValueError: If synthesis is empty or invalid
        json.JSONDecodeError: If AI response is not valid JSON
    """
    if not synthesis or not synthesis.strip():
        raise ValueError("Synthesis cannot be empty")

    from anthropic import AsyncAnthropic

    client = AsyncAnthropic(api_key=anthropic_api_key)

    # Format sub-problem context for cross-sub-problem dependencies
    sp_index_str = (
        str(sub_problem_index) if sub_problem_index is not None else "N/A (meta-synthesis)"
    )
    other_goals_str = ", ".join(other_sub_problem_goals) if other_sub_problem_goals else "N/A"

    user_message = TASK_EXTRACTOR_USER_TEMPLATE.format(
        synthesis=synthesis,
        sub_problem_index=sp_index_str,
        total_sub_problems=total_sub_problems,
        other_sub_problem_goals=other_goals_str,
    )

    # Use haiku for fast, cheap structured extraction (like summarizer)
    model = get_model_for_role("SUMMARIZER")

    ctx = get_cost_context()

    with CostTracker.track_call(
        provider="anthropic",
        operation_type="completion",
        model_name=model,
        session_id=ctx.get("session_id") or session_id,
        user_id=ctx.get("user_id"),
        node_name="task_extractor",
        phase="synthesis",
        prompt_type="task_extraction",
    ) as cost_record:
        response = await client.messages.create(
            model=model,
            max_tokens=4000,
            system=TASK_EXTRACTOR_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": TASK_EXTRACTOR_PREFILL},
            ],
            temperature=0.0,  # Deterministic extraction
        )

        # Track token usage
        cost_record.input_tokens = response.usage.input_tokens
        cost_record.output_tokens = response.usage.output_tokens

    # Parse JSON response (prepend the prefill we used)
    first_block = response.content[0]
    if not hasattr(first_block, "text"):
        raise ValueError(f"Unexpected response type: {type(first_block)}")
    content = TASK_EXTRACTOR_PREFILL + first_block.text

    # Extract JSON from markdown code blocks if present (fallback)
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content and not content.startswith("{"):
        content = content.split("```")[1].split("```")[0].strip()

    data = json.loads(content)

    # Parse timeline to estimated_duration_days for each task
    from bo1.utils.timeline_parser import parse_timeline

    for task_data in data.get("tasks", []):
        timeline = task_data.get("timeline", "")
        if timeline:
            duration_days = parse_timeline(timeline)
            task_data["estimated_duration_days"] = duration_days

    return TaskExtractionResult(**data)


def sync_extract_tasks_from_synthesis(
    synthesis: str,
    session_id: str,
    anthropic_api_key: str,
    sub_problem_index: int | None = None,
    total_sub_problems: int = 1,
    other_sub_problem_goals: list[str] | None = None,
) -> TaskExtractionResult:
    """Synchronous version of extract_tasks_from_synthesis.

    Used in contexts where async is not available.

    Args:
        synthesis: XML-formatted synthesis report
        session_id: Session ID for tracking
        anthropic_api_key: Anthropic API key
        sub_problem_index: Index of this sub-problem (for cross-sp dependencies)
        total_sub_problems: Total number of sub-problems in session
        other_sub_problem_goals: Goals of other sub-problems for context

    Returns:
        TaskExtractionResult with extracted tasks
    """
    if not synthesis or not synthesis.strip():
        raise ValueError("Synthesis cannot be empty")

    client = Anthropic(api_key=anthropic_api_key)

    # Format sub-problem context for cross-sub-problem dependencies
    sp_index_str = (
        str(sub_problem_index) if sub_problem_index is not None else "N/A (meta-synthesis)"
    )
    other_goals_str = ", ".join(other_sub_problem_goals) if other_sub_problem_goals else "N/A"

    user_message = TASK_EXTRACTOR_USER_TEMPLATE.format(
        synthesis=synthesis,
        sub_problem_index=sp_index_str,
        total_sub_problems=total_sub_problems,
        other_sub_problem_goals=other_goals_str,
    )

    # Use haiku for fast, cheap structured extraction (like summarizer)
    model = get_model_for_role("SUMMARIZER")

    ctx = get_cost_context()

    with CostTracker.track_call(
        provider="anthropic",
        operation_type="completion",
        model_name=model,
        session_id=ctx.get("session_id") or session_id,
        user_id=ctx.get("user_id"),
        node_name="task_extractor",
        phase="synthesis",
        prompt_type="task_extraction",
    ) as cost_record:
        response = client.messages.create(
            model=model,
            max_tokens=4000,
            system=TASK_EXTRACTOR_SYSTEM_PROMPT,
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": TASK_EXTRACTOR_PREFILL},
            ],
            temperature=0.0,
        )

        # Track token usage
        cost_record.input_tokens = response.usage.input_tokens
        cost_record.output_tokens = response.usage.output_tokens

    # Parse JSON response (prepend the prefill we used)
    first_block = response.content[0]
    if not hasattr(first_block, "text"):
        raise ValueError(f"Unexpected response type: {type(first_block)}")
    content = TASK_EXTRACTOR_PREFILL + first_block.text

    # Extract JSON from markdown code blocks if present (fallback)
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content and not content.startswith("{"):
        content = content.split("```")[1].split("```")[0].strip()

    data = json.loads(content)

    # Parse timeline to estimated_duration_days for each task
    from bo1.utils.timeline_parser import parse_timeline

    for task_data in data.get("tasks", []):
        timeline = task_data.get("timeline", "")
        if timeline:
            duration_days = parse_timeline(timeline)
            task_data["estimated_duration_days"] = duration_days

    return TaskExtractionResult(**data)
