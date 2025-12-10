"""Dataset profiling tool for Claude agents.

Provides tool definition and handler for data_profile_dataset tool.
"""

import logging
from typing import Any

from backend.services.profiler import ProfileError, profile_dataset, save_profile
from backend.services.summary_generator import generate_dataset_summary
from bo1.state.repositories.dataset_repository import DatasetRepository

logger = logging.getLogger(__name__)


# Tool definition for Claude API
DATA_PROFILE_TOOL = {
    "name": "data_profile_dataset",
    "description": (
        "Profile a dataset to get column types, statistics, and a summary. "
        "Use this to understand the structure and quality of a dataset before analysis."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "dataset_id": {
                "type": "string",
                "description": "UUID of the dataset to profile",
            },
        },
        "required": ["dataset_id"],
    },
}


async def handle_data_profile_tool(
    dataset_id: str,
    user_id: str,
    repository: DatasetRepository | None = None,
) -> dict[str, Any]:
    """Handle data_profile_dataset tool invocation.

    Args:
        dataset_id: Dataset UUID to profile
        user_id: User ID for authorization
        repository: Optional repository instance

    Returns:
        Dict with profile data, summary, and metadata
    """
    repo = repository or DatasetRepository()

    # Get dataset info
    dataset = repo.get_by_id(dataset_id, user_id)
    if not dataset:
        return {
            "error": f"Dataset {dataset_id} not found",
            "success": False,
        }

    # Check if profile exists
    existing_profiles = repo.get_profiles(dataset_id)
    if existing_profiles and dataset.get("summary"):
        # Return cached profile
        return {
            "success": True,
            "dataset_id": dataset_id,
            "dataset_name": dataset["name"],
            "row_count": dataset.get("row_count"),
            "column_count": dataset.get("column_count"),
            "columns": [
                {
                    "name": p["column_name"],
                    "type": p["data_type"],
                    "null_count": p.get("null_count"),
                    "unique_count": p.get("unique_count"),
                    "min_value": p.get("min_value"),
                    "max_value": p.get("max_value"),
                    "mean_value": p.get("mean_value"),
                }
                for p in existing_profiles
            ],
            "summary": dataset.get("summary"),
            "cached": True,
        }

    # Generate new profile
    try:
        profile = profile_dataset(dataset_id, user_id, repo)
        save_profile(profile, repo)
    except ProfileError as e:
        return {
            "error": str(e),
            "success": False,
        }

    # Generate summary
    try:
        summary = await generate_dataset_summary(
            profile.to_dict(),
            dataset_name=dataset["name"],
        )
        repo.update_summary(dataset_id, user_id, summary)
    except Exception as e:
        logger.warning(f"Failed to generate summary: {e}")
        summary = None

    return {
        "success": True,
        "dataset_id": dataset_id,
        "dataset_name": dataset["name"],
        "row_count": profile.row_count,
        "column_count": profile.column_count,
        "columns": [
            {
                "name": col.name,
                "type": col.inferred_type.value,
                "null_count": col.stats.null_count,
                "unique_count": col.stats.unique_count,
                "min_value": col.stats.min_value,
                "max_value": col.stats.max_value,
                "mean_value": col.stats.mean_value,
            }
            for col in profile.columns
        ],
        "summary": summary,
        "cached": False,
    }


# Registry of all data tools
DATA_TOOLS = [DATA_PROFILE_TOOL]
