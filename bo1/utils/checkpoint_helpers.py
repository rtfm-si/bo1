"""Checkpoint deserialization helpers.

After LangGraph checkpoint restoration, Pydantic objects may be deserialized as dicts.
These helpers provide safe access to attributes on objects that may be dicts.
"""

from typing import Any


def get_attr_safe(obj: Any, attr: str, default: Any = None) -> Any:
    """Safely get attribute from an object that may be a dict.

    After checkpoint restoration, Pydantic objects may be deserialized as dicts.
    This helper handles both cases.

    Args:
        obj: Object to get attribute from (may be dict or Pydantic model)
        attr: Attribute name to get
        default: Default value if attribute not found

    Returns:
        Attribute value or default

    Example:
        >>> get_attr_safe(sub_problem, "goal", "")  # Works with dict or SubProblem
        "Should we expand?"
    """
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(attr, default)
    return getattr(obj, attr, default)


def get_sub_problem_goal(sp: Any) -> str:
    """Get goal from sub-problem (handles dict or SubProblem)."""
    result: str = get_attr_safe(sp, "goal", "")
    return result


def get_sub_problem_context(sp: Any) -> str:
    """Get context from sub-problem (handles dict or SubProblem)."""
    result: str = get_attr_safe(sp, "context", "") or ""
    return result


def get_sub_problem_id(sp: Any) -> str:
    """Get id from sub-problem (handles dict or SubProblem)."""
    result: str = get_attr_safe(sp, "id", "")
    return result


def get_sub_problem_id_safe(sp: Any, logger: Any = None) -> str:
    """Get id from sub-problem with corruption detection and repair.

    After LangGraph checkpoint restore, the sub_problem.id field may become
    corrupted to a type annotation path list like:
    ['bo1', 'models', 'problem', 'SubProblem']

    This helper detects and handles that corruption.

    Args:
        sp: SubProblem object or dict
        logger: Optional logger for warning on corruption

    Returns:
        Valid string ID, or empty string if corrupted/missing
    """
    if sp is None:
        return ""

    raw_id = get_attr_safe(sp, "id", "")

    # Handle corrupted list case (type annotation path)
    if isinstance(raw_id, list):
        if logger:
            logger.warning(
                f"Corrupted sub_problem.id detected: {raw_id} - "
                "this is a type annotation path, not a valid ID"
            )
        return ""

    # Validate it's actually a string
    if not isinstance(raw_id, str):
        if logger:
            logger.warning(f"Invalid sub_problem.id type: {type(raw_id).__name__}")
        return ""

    return raw_id


def get_sub_problem_goal_safe(sp: Any, logger: Any = None) -> str:
    """Get goal from sub-problem with corruption detection.

    Args:
        sp: SubProblem object or dict
        logger: Optional logger for warning on corruption

    Returns:
        Valid string goal, or empty string if corrupted/missing
    """
    if sp is None:
        return ""

    raw_goal = get_attr_safe(sp, "goal", "")

    # Handle corrupted list case
    if isinstance(raw_goal, list):
        if logger:
            logger.warning(f"Corrupted sub_problem.goal detected: {raw_goal}")
        return ""

    if not isinstance(raw_goal, str):
        if logger:
            logger.warning(f"Invalid sub_problem.goal type: {type(raw_goal).__name__}")
        return ""

    return raw_goal


def get_problem_description(problem: Any) -> str:
    """Get description from problem (handles dict or Problem)."""
    result: str = get_attr_safe(problem, "description", "")
    return result


def get_problem_context(problem: Any) -> str:
    """Get context from problem (handles dict or Problem)."""
    result: str = get_attr_safe(problem, "context", "") or ""
    return result


def get_problem_sub_problems(problem: Any) -> list[Any]:
    """Get sub_problems list from problem (handles dict or Problem)."""
    result: list[Any] = get_attr_safe(problem, "sub_problems", []) or []
    return result
