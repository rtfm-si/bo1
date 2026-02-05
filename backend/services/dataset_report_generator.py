"""LLM-powered dataset report generation.

Generates structured reports from favourited insights and charts.
"""

import json
import logging
from typing import Any

from bo1.analysis.charts import generate_chart_from_insight
from bo1.llm.broker import PromptBroker, PromptRequest
from bo1.utils.json_parsing import parse_json_with_fallback

logger = logging.getLogger(__name__)


def generate_chart_for_insight(
    insight_data: dict[str, Any],
    title: str = "Chart",
) -> dict[str, Any] | None:
    """Generate a chart for an insight that doesn't have one.

    Args:
        insight_data: The insight data dict with supporting_data and visualization
        title: Chart title

    Returns:
        Plotly figure_json or None
    """
    if not insight_data:
        return None

    # Get visualization config
    viz = insight_data.get("visualization", {})
    if not viz:
        # Default to bar chart
        viz = {"type": "bar"}

    # Get supporting data
    supporting_data = insight_data.get("supporting_data", {})

    return generate_chart_from_insight(
        visualization_config=viz,
        supporting_data=supporting_data,
        title=title,
    )


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
    # Format favourites for prompt and generate missing charts
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

            # Auto-generate chart if insight doesn't have one
            if not f.get("figure_json") and not f.get("chart_spec"):
                generated_chart = generate_chart_for_insight(
                    insight_data=f["insight_data"],
                    title=f.get("title") or "Insight Chart",
                )
                if generated_chart:
                    f["figure_json"] = generated_chart
                    item["has_chart"] = True

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

    # Call LLM via broker (handles retries, fallback, model resolution)
    broker = PromptBroker()
    try:
        request = PromptRequest(
            system=REPORT_SYSTEM_PROMPT,
            user_message=prompt,
            model="core",  # Uses configured sonnet-level model
            max_tokens=4000,
            temperature=0.3,
            agent_type="ReportGenerator",
            phase="report_generation",
        )
        response = await broker.call(request)
    except Exception as e:
        logger.error(f"LLM call failed for report generation: {e}")
        # Return fallback report on LLM failure
        fallback = {
            "title": title or f"Report: {dataset.get('name', 'Dataset')}",
            "executive_summary": "Report generation is temporarily unavailable. Please try again later.",
            "sections": [
                {
                    "section_type": "key_findings",
                    "title": "Key Findings",
                    "content": "Unable to generate report content due to a temporary service issue. Your favourited items are available for manual review.",
                    "chart_refs": [f["id"] for f in favourites if f.get("chart_spec")],
                }
            ],
        }
        return fallback, {"model": "core", "tokens": 0, "error": str(e)}

    # Parse response
    try:
        report_data, errors = parse_json_with_fallback(
            response.content, context="dataset_report_generator"
        )
        if report_data is None:
            logger.warning(f"Failed to parse report response: {errors}")
            return fallback, {"model": "core", "tokens": 0, "error": str(errors)}

        # Apply custom title if provided
        if title:
            report_data["title"] = title

        # Ensure required fields
        if "sections" not in report_data:
            report_data["sections"] = []
        if "executive_summary" not in report_data:
            report_data["executive_summary"] = ""

        metadata = {
            "model": response.model,
            "tokens": response.total_tokens,
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
        return fallback, {"model": "core", "tokens": 0, "error": str(e)}


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

    broker = PromptBroker()
    request = PromptRequest(
        system="You are a senior data analyst writing executive summaries. Be concise and actionable.",
        user_message=prompt,
        model="core",  # Uses configured sonnet-level model
        max_tokens=500,
        temperature=0.3,
        agent_type="ReportGenerator",
        phase="summary_regeneration",
    )
    response = await broker.call(request)

    summary = response.content.strip()
    metadata = {
        "model": response.model,
        "tokens": response.total_tokens,
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
