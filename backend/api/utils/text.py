"""Text manipulation utilities for Board of One API."""


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to maximum length with ellipsis.

    Args:
        text: Text to truncate
        max_length: Maximum length (default: 100)

    Returns:
        Truncated text with "..." if longer than max_length

    Examples:
        >>> truncate_text("Short text", 100)
        'Short text'
        >>> truncate_text("Very long text that exceeds the limit", 20)
        'Very long text th...'
    """
    if len(text) <= max_length:
        return text
    return text[: max_length - 3] + "..."
