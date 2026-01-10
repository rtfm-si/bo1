"""LLM-powered dataset report generation.

Generates structured reports from favourited insights and charts.
"""

import json
import logging
from typing import Any

from bo1.llm.client import ClaudeClient

logger = logging.getLogger(__name__)

REPORT_SYSTEM_PROMPT = """You are a senior data analyst creating an executive report. Your job is to
transform a collection of data insights and charts into a cohesive narrative
that tells the story of what the data reveals.

REPORT STRUCTURE (Pyramid Principle):
1. Lead with the answer - what's the most important takeaway?
2. Group supporting points by theme, not chronology
3. Each section should flow logically to the next
4. Charts should support claims, not just decorate

QUALITY RULES:
- Every claim must reference specific data
- Avoid weasel words ("significant", "notable") - use numbers
- Recommendations must be actionable and specific
- Acknowledge data limitations honestly
- Write for a busy executive who wants the bottom line first

You output ONLY valid JSON. No markdown, no explanation."""

REPORT_USER_PROMPT = """Create an executive report from these favourited insights and charts.

DATASET: {dataset_name}
DESCRIPTION: {dataset_description}
ROW COUNT: {row_count:,}

FAVOURITED ITEMS:
{favourites_json}

Generate a report with this JSON structure:

{{
  "title": "Clear, specific report title",
  "executive_summary": "2-3 sentences summarizing the key finding and recommendation",
  "sections": [
    {{
      "section_type": "key_findings",
      "title": "Key Findings",
      "content": "Markdown content summarizing main findings. Reference charts by their favourite_id.",
      "chart_refs": ["favourite_id_1", "favourite_id_2"]
    }},
    {{
      "section_type": "analysis",
      "title": "Analysis section title",
      "content": "Deeper analysis with specific numbers. Group by theme.",
      "chart_refs": []
    }},
    {{
      "section_type": "recommendations",
      "title": "Recommendations",
      "content": "3-5 concrete, actionable recommendations based on the data.",
      "chart_refs": []
    }},
    {{
      "section_type": "data_notes",
      "title": "Data Notes",
      "content": "Any caveats, limitations, or quality issues to be aware of.",
      "chart_refs": []
    }}
  ]
}}

GUIDELINES:
- The executive_summary should be the "so what" - what should the reader do?
- Key findings should lead with the most important insight
- Analysis sections can be split by theme (e.g., "Revenue Trends", "Customer Segments")
- Reference charts using their favourite IDs so they can be embedded
- Be specific with numbers, not vague ("$127K" not "significant revenue")
- Recommendations should be actionable ("Investigate Q2 spike" not "Monitor trends")
- Data notes should honestly acknowledge any limitations"""


async def generate_dataset_report(
    dataset: dict[str, Any],
    favourites: list[dict[str, Any]],
    title: str | None = None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Generate a report from favourited items.

    Args:
        dataset: Dataset metadata
        favourites: List of favourited items
        title: Optional custom title

    Returns:
        Tuple of (report_data, metadata)
    """
    # Format favourites for prompt
    favourites_for_prompt = []
    for f in favourites:
        item = {
            "favourite_id": f["id"],
            "type": f["favourite_type"],
            "title": f.get("title") or "Untitled",
        }
        if f.get("content"):
            item["content"] = f["content"][:500]  # Truncate for prompt
        if f.get("insight_data"):
            item["insight"] = f["insight_data"]
        if f.get("chart_spec"):
            item["chart_type"] = f["chart_spec"].get("chart_type", "chart")
            item["chart_fields"] = {
                "x": f["chart_spec"].get("x_field"),
                "y": f["chart_spec"].get("y_field"),
                "group": f["chart_spec"].get("group_field"),
            }
        if f.get("user_note"):
            item["user_note"] = f["user_note"]
        favourites_for_prompt.append(item)

    prompt = REPORT_USER_PROMPT.format(
        dataset_name=dataset.get("name", "Unknown"),
        dataset_description=dataset.get("description")
        or dataset.get("summary")
        or "No description",
        row_count=dataset.get("row_count", 0),
        favourites_json=json.dumps(favourites_for_prompt, indent=2),
    )

    # Call LLM
    client = ClaudeClient()
    response = await client.generate(
        system_prompt=REPORT_SYSTEM_PROMPT,
        user_prompt=prompt,
        max_tokens=4000,
        temperature=0.3,
        model="claude-sonnet-4-20250514",
    )

    # Parse response
    try:
        # Extract JSON from response
        content = response.content
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            content = content.split("```")[1].split("```")[0]

        report_data = json.loads(content.strip())

        # Apply custom title if provided
        if title:
            report_data["title"] = title

        # Ensure required fields
        if "sections" not in report_data:
            report_data["sections"] = []
        if "executive_summary" not in report_data:
            report_data["executive_summary"] = ""

        metadata = {
            "model": "claude-sonnet-4-20250514",
            "tokens": response.usage.input_tokens + response.usage.output_tokens
            if response.usage
            else 0,
        }

        return report_data, metadata

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse report JSON: {e}")
        # Return fallback structure
        fallback = {
            "title": title or f"Report: {dataset.get('name', 'Dataset')}",
            "executive_summary": "Report generation encountered an error. Please try again.",
            "sections": [
                {
                    "section_type": "key_findings",
                    "title": "Key Findings",
                    "content": "Unable to generate report content. The favourited items are available for manual review.",
                    "chart_refs": [f["id"] for f in favourites if f.get("chart_spec")],
                }
            ],
        }
        return fallback, {"model": "claude-sonnet-4-20250514", "tokens": 0, "error": str(e)}


SUMMARY_REGENERATION_PROMPT = """Based on the following data analysis report, regenerate the executive summary.
The summary should be 2-3 sentences that capture:
1. The most important finding (lead with the answer)
2. The key implication or recommendation (so what?)
3. Any critical caveats if needed

Report Title: {title}

Report Sections:
{sections_text}

Output ONLY the executive summary text. No JSON, no markdown, just the summary text."""


async def regenerate_executive_summary(
    report: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Regenerate the executive summary for an existing report.

    Args:
        report: Report data with title and sections

    Returns:
        Tuple of (summary_text, metadata)
    """
    # Format sections for prompt
    sections_text = ""
    for section in report.get("report_content", {}).get("sections", []):
        sections_text += f"\n## {section.get('title', 'Section')}\n"
        sections_text += section.get("content", "")[:1000]  # Truncate
        sections_text += "\n"

    prompt = SUMMARY_REGENERATION_PROMPT.format(
        title=report.get("title", "Untitled Report"),
        sections_text=sections_text or "No sections available",
    )

    client = ClaudeClient()
    response = await client.generate(
        system_prompt="You are a senior data analyst writing executive summaries. Be concise and actionable.",
        user_prompt=prompt,
        max_tokens=500,
        temperature=0.3,
        model="claude-sonnet-4-20250514",
    )

    summary = response.content.strip()
    metadata = {
        "model": "claude-sonnet-4-20250514",
        "tokens": response.usage.input_tokens + response.usage.output_tokens
        if response.usage
        else 0,
    }

    return summary, metadata


def export_report_to_markdown(
    report: dict[str, Any],
    dataset_name: str,
    favourites: list[dict[str, Any]] | None = None,
) -> str:
    """Export a report to markdown format.

    Args:
        report: Report data with sections and executive summary
        dataset_name: Name of the dataset
        favourites: Optional list of favourites for chart references

    Returns:
        Markdown string
    """
    from datetime import datetime

    lines = []

    # Header
    lines.append(f"# {report.get('title', 'Data Analysis Report')}")
    lines.append("")
    lines.append(f"**Dataset:** {dataset_name}")
    lines.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("")
    lines.append("---")
    lines.append("")

    # Executive Summary
    if report.get("executive_summary"):
        lines.append("## Executive Summary")
        lines.append("")
        lines.append(report["executive_summary"])
        lines.append("")

    # Sections
    report_content = report.get("report_content", {})
    sections = report_content.get("sections", [])

    for section in sections:
        section_title = section.get("title", "Section")
        lines.append(f"## {section_title}")
        lines.append("")

        content = section.get("content", "")
        lines.append(content)
        lines.append("")

        # Note chart references
        chart_refs = section.get("chart_refs", [])
        if chart_refs and favourites:
            for ref in chart_refs:
                fav = next((f for f in favourites if f["id"] == ref), None)
                if fav and fav.get("title"):
                    lines.append(f"> *See chart: {fav['title']}*")
            lines.append("")

    # Footer
    lines.append("---")
    lines.append("")
    lines.append("*Generated by Board of One Data Analysis*")

    return "\n".join(lines)
