"""Runtime configuration service with Redis-backed overrides.

Provides runtime config overrides that take precedence over env vars,
enabling emergency toggles without server restart.

Pattern: runtime:config:{key}

Security: Only whitelisted config keys can be overridden.
"""

import logging
from typing import Any

import redis

from bo1.config import get_settings

logger = logging.getLogger(__name__)

# Whitelist of config keys that can be overridden at runtime
# Each key maps to its expected type for validation
ALLOWED_OVERRIDES: dict[str, type] = {
    # Security toggles
    "prompt_injection_block_suspicious": bool,
    # LLM/Caching toggles
    "enable_llm_response_cache": bool,
    "enable_prompt_cache": bool,
    # Feature toggles
    "enable_sse_streaming": bool,
    "auto_generate_projects": bool,
    "enable_context_collection": bool,
}

# Redis key prefix for runtime config overrides
REDIS_KEY_PREFIX = "runtime:config:"


def _get_redis_client() -> redis.Redis | None:
    """Get Redis client for config operations.

    Returns:
        Redis client or None if unavailable
    """
    settings = get_settings()
    try:
        pool_kwargs: dict[str, Any] = {
            "host": settings.redis_host,
            "port": settings.redis_port,
            "db": settings.redis_db,
            "decode_responses": True,
        }
        if settings.redis_password:
            pool_kwargs["password"] = settings.redis_password

        client = redis.Redis(**pool_kwargs)
        client.ping()
        return client
    except Exception as e:
        logger.warning("Redis unavailable for runtime config: %s", e)
        return None


def get_override(key: str) -> Any | None:
    """Get runtime override value for a config key.

    Args:
        key: Config key name (must be in ALLOWED_OVERRIDES whitelist)

    Returns:
        Override value if set, None if not set or Redis unavailable

    Example:
        >>> value = get_override("prompt_injection_block_suspicious")
        >>> if value is not None:
        ...     use_value = value
        ... else:
        ...     use_value = settings.prompt_injection_block_suspicious
    """
    if key not in ALLOWED_OVERRIDES:
        logger.warning("Attempted to get override for non-whitelisted key: %s", key)
        return None

    client = _get_redis_client()
    if not client:
        return None

    try:
        redis_key = f"{REDIS_KEY_PREFIX}{key}"
        value = client.get(redis_key)

        if value is None:
            return None

        # Parse based on expected type
        expected_type = ALLOWED_OVERRIDES[key]
        if expected_type is bool:
            return value.lower() == "true"
        return value
    except Exception as e:
        logger.error("Failed to get runtime override for %s: %s", key, e)
        return None


def set_override(key: str, value: Any) -> bool:
    """Set runtime override value for a config key.

    Args:
        key: Config key name (must be in ALLOWED_OVERRIDES whitelist)
        value: Value to set (must match expected type)

    Returns:
        True if set successfully, False otherwise
    """
    if key not in ALLOWED_OVERRIDES:
        logger.warning("Attempted to set override for non-whitelisted key: %s", key)
        return False

    # Validate type
    expected_type = ALLOWED_OVERRIDES[key]
    if not isinstance(value, expected_type):
        logger.warning(
            "Type mismatch for %s: expected %s, got %s",
            key,
            expected_type.__name__,
            type(value).__name__,
        )
        return False

    client = _get_redis_client()
    if not client:
        return False

    try:
        redis_key = f"{REDIS_KEY_PREFIX}{key}"
        # Serialize based on type
        if expected_type is bool:
            str_value = "true" if value else "false"
        else:
            str_value = str(value)

        # Set with no TTL (persistent until cleared)
        client.set(redis_key, str_value)
        logger.info("Runtime override set: %s = %s", key, value)
        return True
    except Exception as e:
        logger.error("Failed to set runtime override for %s: %s", key, e)
        return False


def clear_override(key: str) -> bool:
    """Clear runtime override for a config key.

    Args:
        key: Config key name

    Returns:
        True if cleared (or didn't exist), False on error
    """
    if key not in ALLOWED_OVERRIDES:
        logger.warning("Attempted to clear override for non-whitelisted key: %s", key)
        return False

    client = _get_redis_client()
    if not client:
        return False

    try:
        redis_key = f"{REDIS_KEY_PREFIX}{key}"
        client.delete(redis_key)
        logger.info("Runtime override cleared: %s", key)
        return True
    except Exception as e:
        logger.error("Failed to clear runtime override for %s: %s", key, e)
        return False


def get_all_overrides() -> dict[str, dict[str, Any]]:
    """Get all runtime config overrides with their status.

    Returns dict with each whitelisted key and:
    - key: config key name
    - override_value: current override (None if not set)
    - default_value: value from settings/env
    - effective_value: value that will be used (override > default)
    - is_overridden: True if override is active
    """
    settings = get_settings()
    result: dict[str, dict[str, Any]] = {}

    for key in ALLOWED_OVERRIDES:
        override = get_override(key)
        default = getattr(settings, key, None)

        result[key] = {
            "key": key,
            "override_value": override,
            "default_value": default,
            "effective_value": override if override is not None else default,
            "is_overridden": override is not None,
        }

    return result


def get_effective_value(key: str) -> Any:
    """Get the effective value for a config key (override > default).

    Args:
        key: Config key name

    Returns:
        Effective value (override if set, else default from settings)
    """
    override = get_override(key)
    if override is not None:
        return override

    settings = get_settings()
    return getattr(settings, key, None)
