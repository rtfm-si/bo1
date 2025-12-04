"""Timeline parsing utilities for action management.

Provides functions to:
- Parse human-readable timeline strings to business days
- Add business days to dates (excluding weekends)
- Handle common timeline formats (weeks, months, days)
"""

import re
from datetime import date, timedelta


def parse_timeline(timeline: str) -> int | None:
    """Parse human-readable timeline to business days.

    Supports formats like:
    - "2 weeks" -> 10 days
    - "1 month" -> 20 days
    - "3 days" -> 3 days
    - "1 wk" -> 5 days
    - "2 months" -> 40 days

    Args:
        timeline: Human-readable timeline string

    Returns:
        Number of business days, or None if unable to parse

    Examples:
        >>> parse_timeline("2 weeks")
        10
        >>> parse_timeline("1 month")
        20
        >>> parse_timeline("3 days")
        3
        >>> parse_timeline("invalid")
        None
    """
    if not timeline or not isinstance(timeline, str):
        return None

    timeline = timeline.strip().lower()

    # Pattern: number + optional space + unit
    # Units: week(s), wk(s), month(s), mo(s), day(s), d
    patterns = [
        # Weeks (5 business days per week)
        (r"(\d+)\s*(?:week|wk)s?", 5),
        # Months (20 business days per month - standard work month)
        (r"(\d+)\s*(?:month|mo)s?", 20),
        # Days (1:1 - we assume business days)
        (r"(\d+)\s*(?:day|d)s?", 1),
    ]

    for pattern, multiplier in patterns:
        match = re.search(pattern, timeline, re.IGNORECASE)
        if match:
            number = int(match.group(1))
            return number * multiplier

    return None


def add_business_days(start: date, days: int) -> date:
    """Add business days to a date, skipping weekends.

    Args:
        start: Starting date
        days: Number of business days to add (can be negative)

    Returns:
        End date after adding business days

    Examples:
        >>> add_business_days(date(2025, 12, 2), 5)  # Monday + 5 days
        date(2025, 12, 9)  # Next Monday
        >>> add_business_days(date(2025, 12, 6), 1)  # Friday + 1 day
        date(2025, 12, 9)  # Monday
    """
    if days == 0:
        return start

    # Determine direction
    step = 1 if days > 0 else -1
    days_to_add = abs(days)

    current = start
    business_days_added = 0

    while business_days_added < days_to_add:
        current += timedelta(days=step)
        # Skip weekends (Monday = 0, Sunday = 6)
        if current.weekday() < 5:  # Monday-Friday
            business_days_added += 1

    return current


def format_timeline(days: int | None) -> str:
    """Format business days as human-readable timeline.

    Args:
        days: Number of business days

    Returns:
        Human-readable string (e.g., "2 weeks", "1 month")

    Examples:
        >>> format_timeline(10)
        '2 weeks'
        >>> format_timeline(20)
        '1 month'
        >>> format_timeline(3)
        '3 days'
        >>> format_timeline(None)
        ''
    """
    if days is None or days <= 0:
        return ""

    # Convert to weeks if evenly divisible by 5
    if days % 5 == 0 and days >= 5:
        weeks = days // 5
        return f"{weeks} week" if weeks == 1 else f"{weeks} weeks"

    # Convert to months if evenly divisible by 20
    if days % 20 == 0 and days >= 20:
        months = days // 20
        return f"{months} month" if months == 1 else f"{months} months"

    # Otherwise, use days
    return f"{days} day" if days == 1 else f"{days} days"
