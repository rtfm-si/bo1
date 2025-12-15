"""Prompts for improvement plan generation.

Provides system prompt and prompt builder for generating
actionable improvement plans from detected user patterns.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from backend.services.action_failure_detector import FailurePatternSummary
    from backend.services.topic_detector import RepeatedTopic


IMPROVEMENT_PLAN_SYSTEM = """<role>
You are a productivity coach analyzing user patterns to generate actionable improvement suggestions.
</role>

<task>
Based on the patterns provided, generate 3-5 specific, actionable improvement suggestions.
Focus on practical steps the user can take to address recurring challenges.
</task>

<output_format>
Respond with XML in this exact format:
<suggestions>
  <suggestion>
    <category>execution|planning|knowledge|process</category>
    <title>Brief, actionable title</title>
    <description>2-3 sentence explanation of the issue and why this matters</description>
    <action_steps>
      <step>Specific action 1</step>
      <step>Specific action 2</step>
      <step>Specific action 3</step>
    </action_steps>
    <priority>high|medium|low</priority>
  </suggestion>
</suggestions>

Categories:
- execution: Getting things done, completing actions
- planning: Breaking down work, setting realistic goals
- knowledge: Recurring questions, skill gaps
- process: Workflow improvements, removing blockers
</output_format>

<constraints>
- Be specific and actionable, not generic
- Reference the actual patterns you see
- Prioritize based on impact
- Keep descriptions concise
- Focus on quick wins and high-impact changes
</constraints>"""


def get_improvement_plan_system_prompt() -> str:
    """Get the system prompt for improvement plan generation."""
    return IMPROVEMENT_PLAN_SYSTEM


def build_improvement_plan_prompt(
    repeated_topics: list["RepeatedTopic"],
    failure_summary: "FailurePatternSummary | None",
) -> str:
    """Build the user prompt with detected patterns.

    Args:
        repeated_topics: List of detected repeated topics
        failure_summary: Summary of action failures

    Returns:
        Formatted prompt string
    """
    parts = ["<detected_patterns>"]

    # Add repeated topics
    if repeated_topics:
        parts.append("  <repeated_questions>")
        parts.append("  The user has asked about these topics multiple times:")
        for topic in repeated_topics[:5]:  # Max 5 topics
            parts.append(f'    <topic count="{topic.count}">')
            parts.append(f"      <summary>{topic.topic_summary}</summary>")
            if topic.representative_messages:
                # Include a sample message for context
                sample = topic.representative_messages[0][:150]
                parts.append(f"      <sample>{sample}</sample>")
            parts.append("    </topic>")
        parts.append("  </repeated_questions>")

    # Add failure patterns
    if failure_summary and failure_summary.failed_actions > 0:
        parts.append("  <action_failures>")
        rate_pct = f"{failure_summary.failure_rate:.0%}"
        parts.append(
            f"  Failure rate: {rate_pct} "
            f"({failure_summary.failed_actions}/{failure_summary.total_actions} actions)"
        )

        # Add category breakdown
        if failure_summary.by_category:
            parts.append("    <by_category>")
            for cat, count in sorted(failure_summary.by_category.items(), key=lambda x: -x[1])[:3]:
                parts.append(f'      <category name="{cat}" count="{count}"/>')
            parts.append("    </by_category>")

        # Add project breakdown
        if failure_summary.by_project:
            parts.append("    <by_project>")
            for proj, count in sorted(failure_summary.by_project.items(), key=lambda x: -x[1])[:3]:
                parts.append(f'      <project name="{proj}" failures="{count}"/>')
            parts.append("    </by_project>")

        # Sample failures
        if failure_summary.patterns:
            parts.append("    <sample_failures>")
            for p in failure_summary.patterns[:3]:
                reason = p.failure_reason or "No reason given"
                parts.append(f'      <failure status="{p.status}">')
                parts.append(f"        <title>{p.title}</title>")
                parts.append(f"        <reason>{reason}</reason>")
                parts.append("      </failure>")
            parts.append("    </sample_failures>")

        parts.append("  </action_failures>")

    parts.append("</detected_patterns>")

    # Add instruction
    parts.append("")
    parts.append("Based on these patterns, generate improvement suggestions.")

    return "\n".join(parts)
