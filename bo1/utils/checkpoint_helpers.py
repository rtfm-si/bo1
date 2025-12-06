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
