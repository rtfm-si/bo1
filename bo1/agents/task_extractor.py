"""Task extraction from synthesis recommendations.

Parses synthesis XML to identify discrete, actionable tasks.
"""

import json

from anthropic import Anthropic
from pydantic import BaseModel, Field

from bo1.config import get_model_for_role


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


TASK_EXTRACTION_PROMPT = """You are analyzing a synthesis report from a multi-expert deliberation.

Your task is to extract discrete, actionable tasks from the synthesis sections.

<synthesis>
{synthesis}
</synthesis>

Extract tasks following these rules:
1. **Discrete** - Each task should be a single, completable action
2. **Actionable** - Must be something the user can actually do (not abstract)
3. **Well-structured** - Each task MUST include title, what_and_how, success criteria, kill criteria
4. **Prioritized** - Assign priority based on impact and urgency mentioned in synthesis
5. **Timed** - Include realistic timeline (e.g., "2 weeks", "1 month")
6. **Dependencies** - Identify what needs to happen before this task can start

**Output format (JSON):**
```json
{{
  "tasks": [
    {{
      "id": "task_1",
      "title": "Conduct enterprise pricing research",
      "description": "Determine pricing sensitivity for enterprise tier through customer interviews",
      "what_and_how": [
        "Schedule 10-15 interviews with current enterprise prospects",
        "Use Van Westendorp pricing model for survey questions",
        "Analyze competitive pricing in similar B2B SaaS markets"
      ],
      "success_criteria": [
        "Clear price range identified with >80% confidence",
        "3+ pricing tiers defined with feature differentiation"
      ],
      "kill_criteria": [
        "If <5 interviews completed after 2 weeks, pivot to survey approach",
        "If pricing variance exceeds 3x between segments, split into separate initiatives"
      ],
      "dependencies": ["Access to customer contact list", "Sales team availability for intros"],
      "timeline": "2 weeks",
      "priority": "high",
      "category": "research",
      "source_section": "implementation_considerations",
      "confidence": 0.9
    }},
    {{
      "id": "task_2",
      "title": "Build revenue comparison model",
      "description": "Create financial model comparing subscription vs usage-based revenue",
      "what_and_how": [
        "Model 24-month projections for both pricing approaches",
        "Include customer churn assumptions from industry benchmarks",
        "Run sensitivity analysis on key variables"
      ],
      "success_criteria": [
        "Clear recommendation supported by financial projections",
        "Break-even point identified for each pricing model"
      ],
      "kill_criteria": [
        "If data quality insufficient, use industry proxies with documented assumptions",
        "Abandon if pricing research (task_1) doesn't complete"
      ],
      "dependencies": ["Pricing research complete (task_1)", "Finance team review"],
      "timeline": "1 week",
      "priority": "high",
      "category": "implementation",
      "source_section": "implementation_considerations",
      "confidence": 0.85
    }}
  ],
  "total_tasks": 2,
  "extraction_confidence": 0.88,
  "synthesis_sections_analyzed": ["implementation_considerations", "timeline", "resources_required"]
}}
```

**Important:**
- Focus on **concrete tasks**, not general advice
- Extract from: Implementation Considerations, Timeline, Resources Required, Open Questions, Unified Action Plan
- Ignore vague recommendations like "consider user feedback" (too abstract)
- Tasks should be specific enough to assign to someone
- **title** should be 5-10 words, distinct from description
- **what_and_how** must have 1-3 specific action bullets (not a repeat of the title)
- **success_criteria** must have 1-2 measurable outcomes
- **kill_criteria** must have 1-2 conditions for when to stop/replan
- **dependencies** should list prerequisites (can reference other task IDs or external requirements)
- **timeline** should be realistic (e.g., "3 days", "2 weeks", "1 month")
- Set confidence based on how explicit the task is in the synthesis

Extract tasks now. Output ONLY valid JSON, no additional commentary."""


async def extract_tasks_from_synthesis(
    synthesis: str,
    session_id: str,
    anthropic_api_key: str,
) -> TaskExtractionResult:
    """Extract actionable tasks from synthesis using Claude.

    Args:
        synthesis: XML-formatted synthesis report
        session_id: Session ID for tracking
        anthropic_api_key: Anthropic API key

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

    prompt = TASK_EXTRACTION_PROMPT.format(synthesis=synthesis)

    # Use haiku for fast, cheap structured extraction (like summarizer)
    model = get_model_for_role("SUMMARIZER")

    response = await client.messages.create(
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,  # Deterministic extraction
    )

    # Parse JSON response
    first_block = response.content[0]
    if not hasattr(first_block, "text"):
        raise ValueError(f"Unexpected response type: {type(first_block)}")
    content = first_block.text

    # Extract JSON from markdown code blocks if present
    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    data = json.loads(content)

    return TaskExtractionResult(**data)


def sync_extract_tasks_from_synthesis(
    synthesis: str,
    session_id: str,
    anthropic_api_key: str,
) -> TaskExtractionResult:
    """Synchronous version of extract_tasks_from_synthesis.

    Used in contexts where async is not available.
    """
    if not synthesis or not synthesis.strip():
        raise ValueError("Synthesis cannot be empty")

    client = Anthropic(api_key=anthropic_api_key)

    prompt = TASK_EXTRACTION_PROMPT.format(synthesis=synthesis)

    # Use haiku for fast, cheap structured extraction (like summarizer)
    model = get_model_for_role("SUMMARIZER")

    response = client.messages.create(
        model=model,
        max_tokens=4000,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
    )

    first_block = response.content[0]
    if not hasattr(first_block, "text"):
        raise ValueError(f"Unexpected response type: {type(first_block)}")
    content = first_block.text

    if "```json" in content:
        content = content.split("```json")[1].split("```")[0].strip()
    elif "```" in content:
        content = content.split("```")[1].split("```")[0].strip()

    data = json.loads(content)

    return TaskExtractionResult(**data)
