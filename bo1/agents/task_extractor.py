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
    description: str = Field(description="Clear, actionable task description")
    category: str = Field(description="Category: implementation, research, decision, communication")
    priority: str = Field(description="high, medium, low")
    suggested_completion_date: str | None = Field(
        default=None, description="ISO date or relative (e.g., 'Week 1')"
    )
    dependencies: list[str] = Field(
        default_factory=list, description="IDs of tasks this depends on"
    )
    source_section: str = Field(description="Which synthesis section this came from")
    confidence: float = Field(description="AI confidence in task extraction (0-1)", ge=0.0, le=1.0)


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
3. **Prioritized** - Assign priority based on impact and urgency mentioned in synthesis
4. **Dated** - Extract or infer completion dates from timeline section
5. **Categorized** - Label as: implementation, research, decision, or communication
6. **Dependencies** - Identify if task depends on other tasks

**Output format (JSON):**
```json
{{
  "tasks": [
    {{
      "id": "task_1",
      "description": "Conduct customer interviews to determine pricing sensitivity for enterprise tier",
      "category": "research",
      "priority": "high",
      "suggested_completion_date": "Week 1",
      "dependencies": [],
      "source_section": "implementation_considerations",
      "confidence": 0.9
    }},
    {{
      "id": "task_2",
      "description": "Build financial model comparing subscription vs usage-based revenue over 24 months",
      "category": "implementation",
      "priority": "high",
      "suggested_completion_date": "Week 2",
      "dependencies": ["task_1"],
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
- Extract from: Implementation Considerations, Timeline, Resources Required, Open Questions
- Ignore vague recommendations like "consider user feedback" (too abstract)
- Tasks should be specific enough to assign to someone
- If timeline section mentions phases (Week 1, Month 1), use those for suggested_completion_date
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
