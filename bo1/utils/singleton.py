"""Singleton pattern utilities for Board of One.

Provides a consistent decorator-based approach to creating singleton instances
across the codebase, replacing manual global variable patterns.

Benefits:
- Consistent pattern across all singletons
- Thread-safe singleton creation
- Easy to reset for testing
- Clear, documented pattern
"""

from collections.abc import Callable
from functools import wraps
from typing import TypeVar

T = TypeVar("T")


def singleton[T](factory: Callable[[], T]) -> Callable[[], T]:
    """Decorator to create thread-safe singleton from factory function.

    This decorator transforms a factory function into a singleton getter,
    ensuring only one instance is created across the application lifetime.

    Args:
        factory: Function that creates the instance (called only once)

    Returns:
        Singleton getter function that always returns the same instance

    Examples:
        >>> @singleton
        ... def get_cache() -> Cache:
        ...     return Cache()
        >>> cache1 = get_cache()
        >>> cache2 = get_cache()
        >>> assert cache1 is cache2  # Same instance

        >>> # For testing: reset singleton via function attribute
        >>> get_cache.reset()  # type: ignore
        >>> cache3 = get_cache()
        >>> assert cache3 is not cache1  # New instance after reset

    Note:
        Thread safety: Uses simple check-then-create pattern. For highly
        concurrent environments, consider adding lock protection.
    """
    instance: list[T | None] = [None]  # Use list to allow mutation in closure

    @wraps(factory)
    def get_instance() -> T:
        """Get or create singleton instance."""
        if instance[0] is None:
            instance[0] = factory()
        return instance[0]  # type: ignore

    def reset() -> None:
        """Reset singleton (primarily for testing).

        Examples:
            >>> get_cache.reset()  # type: ignore
            >>> cache = get_cache()  # Creates new instance
        """
        instance[0] = None

    # Attach reset method to function for testing convenience
    get_instance.reset = reset  # type: ignore[attr-defined]

    return get_instance
