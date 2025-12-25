"""Pagination utilities for list response models."""


def make_pagination_fields(total: int, limit: int, offset: int) -> dict:
    """Calculate pagination helper fields.

    Args:
        total: Total number of items in the collection
        limit: Page size (number of items per page)
        offset: Current offset (number of items to skip)

    Returns:
        Dict with pagination fields:
        - total: Total number of items
        - limit: Page size
        - offset: Current offset
        - has_more: Whether more items exist beyond current page
        - next_offset: Offset for next page (None if no more pages)
    """
    has_more = offset + limit < total
    next_offset = offset + limit if has_more else None
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": has_more,
        "next_offset": next_offset,
    }


def make_page_pagination_fields(total: int, page: int, per_page: int) -> dict:
    """Calculate pagination helper fields for page-based pagination.

    Converts page/per_page to offset-based pagination fields.

    Args:
        total: Total number of items in the collection
        page: Current page number (1-indexed)
        per_page: Items per page

    Returns:
        Dict with pagination fields (same as make_pagination_fields)
    """
    offset = (page - 1) * per_page
    return make_pagination_fields(total=total, limit=per_page, offset=offset)
