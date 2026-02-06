"""State serialization/deserialization for checkpoint storage.

Extracted from state.py for maintainability.
Converts between Pydantic models and dicts for Redis/JSON checkpoint storage.
"""

import logging
from typing import Any

from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem, SubProblem
from bo1.models.state import (
    ContributionMessage,
    DeliberationMetrics,
    SubProblemResult,
)

logger = logging.getLogger(__name__)


def serialize_state_for_checkpoint(state: dict[str, Any]) -> dict[str, Any]:
    """Serialize state for checkpoint storage.

    Converts Pydantic models to dicts to ensure proper serialization
    by LangGraph's AsyncRedisSaver. This fixes the bug where nested models
    (like Problem.sub_problems) are lost on checkpoint resume.

    Serialized fields (Pydantic → dict):
        - problem: Problem model with nested SubProblem list
        - current_sub_problem: SubProblem model
        - personas: list[PersonaProfile]
        - contributions: list[ContributionMessage]
        - metrics: DeliberationMetrics
        - sub_problem_results: list[SubProblemResult]

    Pass-through fields (already JSON-serializable):
        - All primitive types (str, int, float, bool)
        - All dict[str, Any] fields (facilitator_decision, business_context, etc.)
        - All list[str] or list[dict] fields (round_summaries, votes, etc.)

    Edge cases:
        - Empty lists: Preserved as [] (not converted to None)
        - None values: Preserved as None (not omitted)
        - Mixed Pydantic/dict in lists: Handles both via hasattr check
        - Missing keys: Absent keys remain absent (TypedDict partial)

    Version compatibility:
        - Forward-compat: New fields added to state are ignored in older code
        - Backward-compat: Old checkpoints missing new fields load without error
          (TypedDict total=False allows missing keys)

    Args:
        state: The graph state to serialize

    Returns:
        Dictionary with all Pydantic models converted to dicts
    """
    result = dict(state)

    # Single-value Pydantic fields
    for key in ("problem", "current_sub_problem", "metrics"):
        if key in result and result[key] is not None and hasattr(result[key], "model_dump"):
            result[key] = result[key].model_dump()

    # List-of-Pydantic fields
    for key in ("personas", "contributions", "sub_problem_results"):
        items = result.get(key)
        if items:
            result[key] = [
                item.model_dump() if hasattr(item, "model_dump") else item for item in items
            ]

    return result


def deserialize_state_from_checkpoint(data: dict[str, Any]) -> dict[str, Any]:
    """Deserialize state from checkpoint storage.

    Converts dicts back to Pydantic models where appropriate.
    This is the inverse of serialize_state_for_checkpoint.

    Deserialized fields (dict → Pydantic):
        - problem: dict → Problem (with nested SubProblem list)
        - current_sub_problem: dict → SubProblem
        - personas: list[dict] → list[PersonaProfile]
        - contributions: list[dict] → list[ContributionMessage]
        - metrics: dict → DeliberationMetrics
        - sub_problem_results: list[dict] → list[SubProblemResult]

    Edge cases:
        - Missing keys: Silently skipped (no KeyError)
        - Extra keys: Preserved as-is (forward-compat for new fields)
        - None values: Preserved as None (not converted)
        - Mixed dict/Pydantic in lists: Only dicts are converted
        - Empty lists: Preserved as [] (not converted)

    Validation:
        - Uses model_validate() which raises ValidationError on schema mismatch
        - Caller should handle ValidationError for corrupted checkpoints

    Args:
        data: Dictionary loaded from checkpoint

    Returns:
        Dictionary with Pydantic models reconstructed
    """
    from bo1.utils.checkpoint_helpers import is_corrupted_type_annotation

    result = dict(data)

    # Deserialize Problem
    if "problem" in result and isinstance(result["problem"], dict):
        result["problem"] = Problem.model_validate(result["problem"])

    # Deserialize current_sub_problem with corruption detection
    # Check for corrupted id BEFORE model_validate (which would reject it)
    if "current_sub_problem" in result and isinstance(result["current_sub_problem"], dict):
        current_sp_dict = result["current_sub_problem"]
        sp_id = current_sp_dict.get("id")

        if is_corrupted_type_annotation(sp_id):
            # Corrupted checkpoint - id is a type annotation path like
            # ['bo1', 'models', 'problem', 'SubProblem']
            logger.warning(
                f"Corrupted current_sub_problem.id detected: {sp_id} - "
                "attempting repair from problem.sub_problems"
            )

            # Attempt repair: get from problem.sub_problems by index
            problem = result.get("problem")
            sub_problem_index = result.get("sub_problem_index", 0)
            repaired = False

            if problem is not None:
                sub_problems = (
                    getattr(problem, "sub_problems", [])
                    if hasattr(problem, "sub_problems")
                    else problem.get("sub_problems", [])
                    if isinstance(problem, dict)
                    else []
                )
                if 0 <= sub_problem_index < len(sub_problems):
                    repaired_sp = sub_problems[sub_problem_index]
                    if isinstance(repaired_sp, dict):
                        result["current_sub_problem"] = SubProblem.model_validate(repaired_sp)
                    else:
                        result["current_sub_problem"] = repaired_sp
                    logger.info(f"Repaired current_sub_problem from index {sub_problem_index}")
                    repaired = True
                else:
                    logger.error(
                        f"Cannot repair current_sub_problem: index {sub_problem_index} "
                        f"out of bounds for {len(sub_problems)} sub_problems"
                    )

            if not repaired:
                # Cannot repair - remove corrupted data to avoid validation error
                logger.error("Removing corrupted current_sub_problem (repair failed)")
                result["current_sub_problem"] = None
        else:
            # Normal case - validate as usual
            result["current_sub_problem"] = SubProblem.model_validate(current_sp_dict)

    # Deserialize personas list
    if "personas" in result and result["personas"]:
        result["personas"] = [
            PersonaProfile.model_validate(p) if isinstance(p, dict) else p
            for p in result["personas"]
        ]

    # Deserialize contributions list
    if "contributions" in result and result["contributions"]:
        result["contributions"] = [
            ContributionMessage.model_validate(c) if isinstance(c, dict) else c
            for c in result["contributions"]
        ]

    # Deserialize metrics
    if "metrics" in result and isinstance(result["metrics"], dict):
        result["metrics"] = DeliberationMetrics.model_validate(result["metrics"])

    # Deserialize sub_problem_results list
    if "sub_problem_results" in result and result["sub_problem_results"]:
        result["sub_problem_results"] = [
            SubProblemResult.model_validate(spr) if isinstance(spr, dict) else spr
            for spr in result["sub_problem_results"]
        ]

    return result
