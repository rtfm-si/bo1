"""Metric label utilities for Prometheus cardinality control.

Prevents metric explosion from high-cardinality labels like session_id and user_id.
"""

from bo1.constants import MetricLabelConfig


def truncate_label(value: str | None, length: int | None = None) -> str:
    """Truncate a label value to reduce Prometheus metric cardinality.

    Args:
        value: Label value to truncate (e.g., UUID session_id)
        length: Max length (default: LABEL_TRUNCATE_LENGTH)

    Returns:
        Truncated string, or "unknown" if value is None/empty

    Examples:
        >>> truncate_label("3f2504e0-4f89-11d3-9a0c-0305e82c3301")
        '3f2504e0'
        >>> truncate_label("short")
        'short'
        >>> truncate_label(None)
        'unknown'
    """
    if not value:
        return "unknown"

    max_len = length if length is not None else MetricLabelConfig.LABEL_TRUNCATE_LENGTH
    return value[:max_len] if len(value) > max_len else value
