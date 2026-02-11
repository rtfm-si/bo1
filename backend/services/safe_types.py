"""Shared type-conversion helpers used across service modules."""

from __future__ import annotations

from typing import Any

import numpy as np


def safe_str(value: Any, max_len: int) -> str | None:
    """Safely convert value to string with length limit."""
    if value is None:
        return None
    return str(value)[:max_len] if value else None


def safe_list(value: Any, max_items: int, item_max_len: int = 300) -> list[str]:
    """Safely convert value to list of strings."""
    if not value or not isinstance(value, list):
        return []
    return [str(item)[:item_max_len] for item in value[:max_items] if item]


def safe_float(val: Any) -> float | None:
    """Safely convert to float, handling NaN and infinity."""
    if val is None:
        return None
    try:
        f = float(val)
        if np.isnan(f) or np.isinf(f):
            return None
        return round(f, 4)
    except (TypeError, ValueError):
        return None
