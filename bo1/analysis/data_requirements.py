"""Data requirements generation module.

Generates data requirements guides for analyzing specific objectives,
helping users understand what data they need to collect.
"""

import logging
from typing import Any

from bo1.analysis.prompts.data_requirements import (
    DATA_REQUIREMENTS_SYSTEM_PROMPT,
    build_data_requirements_prompt,
    parse_data_requirements_response,
)
from bo1.llm.client import ClaudeClient
from bo1.models.dataset_objective_analysis import (
    DataPriority,
    DataRequirements,
    DataSource,
    EssentialData,
    ValuableAddition,
)

logger = logging.getLogger(__name__)


async def generate_data_requirements(
    objective_name: str,
    objective_description: str | None = None,
    target_value: str | None = None,
    current_value: str | None = None,
    industry: str | None = None,
    business_model: str | None = None,
) -> DataRequirements:
    """Generate data requirements for analyzing a specific objective.

    Uses the data_requirements prompt to help users understand what data
    they need to collect for meaningful analysis of an objective.

    Args:
        objective_name: Name of the objective (e.g., "Reduce customer churn to < 5%")
        objective_description: Optional detailed description
        target_value: Target to achieve (e.g., "5%")
        current_value: Current state (e.g., "8%")
        industry: Business industry for context-specific suggestions
        business_model: Type of business model (SaaS, e-commerce, etc.)

    Returns:
        DataRequirements with essential data, valuable additions, and sources
    """
    # Build the prompt
    user_prompt = build_data_requirements_prompt(
        objective_name=objective_name,
        objective_description=objective_description,
        target_value=target_value,
        current_value=current_value,
        industry=industry,
        business_model=business_model,
    )

    # Call LLM
    client = ClaudeClient()
    try:
        response_text, usage = await client.call(
            model="sonnet",
            system=DATA_REQUIREMENTS_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
            cache_system=True,
            temperature=0.3,  # Lower temp for consistent requirements
            prefill="{",
        )

        # Parse response
        raw_result = parse_data_requirements_response(response_text)

        # Convert to typed model
        return _parse_requirements(raw_result)

    except Exception as e:
        logger.error(f"Error generating data requirements: {e}")
        # Return a generic fallback
        return _create_generic_requirements(objective_name)


def _parse_requirements(raw: dict[str, Any]) -> DataRequirements:
    """Parse raw LLM response into typed DataRequirements model.

    Args:
        raw: Parsed JSON from LLM response

    Returns:
        DataRequirements model
    """
    # Parse essential data
    essential_data = []
    for item in raw.get("essential_data", []):
        essential_data.append(
            EssentialData(
                name=item.get("name", ""),
                description=item.get("description", ""),
                example_columns=item.get("example_columns", []),
                why_essential=item.get("why_essential", ""),
                questions_answered=item.get("questions_answered", []),
            )
        )

    # Parse valuable additions
    valuable_additions = []
    for item in raw.get("valuable_additions", []):
        # Parse priority
        try:
            priority_str = item.get("priority", "medium").lower()
            priority = DataPriority(priority_str)
        except ValueError:
            priority = DataPriority.MEDIUM

        valuable_additions.append(
            ValuableAddition(
                name=item.get("name", ""),
                description=item.get("description", ""),
                insight_unlocked=item.get("insight_unlocked", ""),
                priority=priority,
            )
        )

    # Parse data sources
    data_sources = []
    for item in raw.get("data_sources", []):
        data_sources.append(
            DataSource(
                source_type=item.get("source_type", ""),
                example_tools=item.get("example_tools", []),
                typical_export_name=item.get("typical_export_name", ""),
                columns_typically_included=item.get("columns_typically_included", []),
            )
        )

    return DataRequirements(
        objective_summary=raw.get("objective_summary", ""),
        essential_data=essential_data,
        valuable_additions=valuable_additions,
        data_sources=data_sources,
        analysis_preview=raw.get("analysis_preview", ""),
    )


def _create_generic_requirements(objective_name: str) -> DataRequirements:
    """Create generic data requirements when LLM call fails.

    Args:
        objective_name: Name of the objective

    Returns:
        Generic DataRequirements
    """
    return DataRequirements(
        objective_summary=f"Analyzing: {objective_name}",
        essential_data=[
            EssentialData(
                name="Relevant metrics",
                description="Quantitative data that measures progress toward your objective",
                example_columns=["value", "metric", "amount"],
                why_essential="Without measurable data, we cannot track progress",
                questions_answered=["How are we performing?", "Are we improving?"],
            ),
            EssentialData(
                name="Time dimension",
                description="Dates or timestamps to track changes over time",
                example_columns=["date", "created_at", "timestamp"],
                why_essential="Required for trend analysis and progress tracking",
                questions_answered=["When did changes occur?", "What's the trend?"],
            ),
        ],
        valuable_additions=[
            ValuableAddition(
                name="Segmentation dimensions",
                description="Categories or groups to break down the analysis",
                insight_unlocked="Understand which segments perform best or worst",
                priority=DataPriority.HIGH,
            ),
        ],
        data_sources=[
            DataSource(
                source_type="Analytics",
                example_tools=["Google Analytics", "Mixpanel", "Amplitude"],
                typical_export_name="Analytics Export",
                columns_typically_included=["date", "metric", "value"],
            ),
        ],
        analysis_preview="With the right data, we can track your progress, identify trends, and surface actionable insights.",
    )


async def generate_requirements_for_objectives(
    objectives: list[dict[str, Any]],
    industry: str | None = None,
    business_model: str | None = None,
) -> dict[str, DataRequirements]:
    """Generate data requirements for multiple objectives.

    Args:
        objectives: List of objective dicts with id, name, description, target, current
        industry: Business industry
        business_model: Type of business model

    Returns:
        Dict mapping objective_id to DataRequirements
    """
    results = {}

    for obj in objectives:
        obj_id = obj.get("id", obj.get("name", "unknown"))
        try:
            requirements = await generate_data_requirements(
                objective_name=obj.get("name", ""),
                objective_description=obj.get("description"),
                target_value=obj.get("target"),
                current_value=obj.get("current"),
                industry=industry,
                business_model=business_model,
            )
            results[obj_id] = requirements
        except Exception as e:
            logger.error(f"Error generating requirements for objective {obj_id}: {e}")
            results[obj_id] = _create_generic_requirements(obj.get("name", "Unknown"))

    return results
