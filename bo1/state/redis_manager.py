"""Redis-based state management for deliberation sessions.

Handles:
- Session persistence with TTL
- State serialization/deserialization
- Connection pooling
- Error handling and fallback
- Automatic reconnection with exponential backoff
"""

import asyncio
import json
import logging
import time
import uuid
from enum import Enum
from typing import Any, cast

import redis

from bo1.config import get_settings

logger = logging.getLogger(__name__)


class RedisConnectionState(Enum):
    """Redis connection state for health monitoring."""

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"


class RedisManager:
    """Manages deliberation state persistence in Redis.

    Features:
    - Automatic session ID generation
    - 24-hour TTL for sessions
    - Connection pooling
    - Graceful fallback if Redis unavailable

    Examples:
        >>> manager = RedisManager()
        >>> session_id = manager.create_session()
        >>> manager.save_state(session_id, state)
        >>> loaded_state = manager.load_state(session_id)
    """

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        db: int | None = None,
        password: str | None = None,
        ttl_seconds: int | None = None,
    ) -> None:
        """Initialize Redis manager.

        Args:
            host: Redis host (defaults to config)
            port: Redis port (defaults to config)
            db: Redis database number (defaults to config)
            password: Redis password (defaults to config)
            ttl_seconds: Session TTL in seconds (default: 7 days via DatabaseConfig)
        """
        from bo1.constants import DatabaseConfig, RedisReconnection

        settings = get_settings()

        self.host = host or settings.redis_host
        self.port = port or settings.redis_port
        self.db = db or settings.redis_db
        # Only use password if explicitly provided and non-empty
        self.password = (
            (password or settings.redis_password) if (password or settings.redis_password) else None
        )
        # Use aligned TTL (7 days) to match checkpoint TTL
        self.ttl_seconds = ttl_seconds or DatabaseConfig.REDIS_METADATA_TTL_SECONDS

        # Reconnection state tracking
        self._connection_state = RedisConnectionState.DISCONNECTED
        self._reconnect_attempts = 0
        self._max_reconnect_attempts = RedisReconnection.MAX_ATTEMPTS
        self._last_reconnect_time: float = 0.0

        # Initialize connection pool
        try:
            # Build connection pool args - only include password if set
            pool_kwargs: dict[str, Any] = {
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "decode_responses": True,  # Auto-decode bytes to str
                "max_connections": 10,
            }
            if self.password:  # Only add password if it's not None/empty
                pool_kwargs["password"] = self.password

            self.pool = redis.ConnectionPool(**pool_kwargs)
            # Note: decode_responses=True returns str, but Redis typing is complex
            # Different redis-py versions have different type parameter requirements
            # Using bare redis.Redis for compatibility across versions
            self.redis: redis.Redis | None = redis.Redis(connection_pool=self.pool)  # type: ignore[type-arg,unused-ignore]

            # Test connection
            assert self.redis is not None  # Type guard: checked by is_available
            self.redis.ping()
            auth_status = " (with auth)" if self.password else ""
            logger.info(f"✅ Connected to Redis at {self.host}:{self.port}/{self.db}{auth_status}")
            self._available = True
            self._connection_state = RedisConnectionState.CONNECTED

        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"⚠️  Redis unavailable: {e}. Continuing without persistence.")
            self._available = False
            self._connection_state = RedisConnectionState.DISCONNECTED
            self.redis = None

    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._available

    @property
    def connection_state(self) -> RedisConnectionState:
        """Get current Redis connection state for health monitoring."""
        return self._connection_state

    @property
    def reconnect_attempts(self) -> int:
        """Get number of reconnection attempts since last disconnect."""
        return self._reconnect_attempts

    def _calculate_backoff_delay(self) -> float:
        """Calculate exponential backoff delay in seconds.

        Returns:
            Delay in seconds based on attempt count with exponential backoff
        """
        from bo1.constants import RedisReconnection

        base_delay_s = RedisReconnection.INITIAL_DELAY_MS / 1000.0
        max_delay_s = RedisReconnection.MAX_DELAY_MS / 1000.0

        delay = base_delay_s * (RedisReconnection.BACKOFF_FACTOR**self._reconnect_attempts)
        return min(delay, max_delay_s)

    def _attempt_reconnect(self) -> bool:
        """Attempt to reconnect to Redis with exponential backoff.

        Returns:
            True if reconnection succeeded, False otherwise
        """
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error(
                f"[REDIS_RECONNECT] Max reconnect attempts ({self._max_reconnect_attempts}) "
                "exceeded, giving up"
            )
            return False

        self._connection_state = RedisConnectionState.RECONNECTING
        self._reconnect_attempts += 1

        # Calculate backoff delay
        delay = self._calculate_backoff_delay()
        logger.info(
            f"[REDIS_RECONNECT] Attempt {self._reconnect_attempts}/{self._max_reconnect_attempts} "
            f"after {delay:.1f}s delay"
        )

        # Sleep for backoff delay (synchronous - for async use ensure_connected_async)
        time.sleep(delay)
        self._last_reconnect_time = time.time()

        try:
            # Build connection pool args
            pool_kwargs: dict[str, Any] = {
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "decode_responses": True,
                "max_connections": 10,
            }
            if self.password:
                pool_kwargs["password"] = self.password

            # Create new pool and client
            self.pool = redis.ConnectionPool(**pool_kwargs)
            self.redis = redis.Redis(connection_pool=self.pool)  # type: ignore[type-arg,unused-ignore]

            # Test connection
            self.redis.ping()

            # Success - reset state
            self._available = True
            self._connection_state = RedisConnectionState.CONNECTED
            self._reconnect_attempts = 0

            logger.info(
                f"[REDIS_RECONNECT] Successfully reconnected to Redis "
                f"at {self.host}:{self.port}/{self.db}"
            )

            # Record success in circuit breaker
            try:
                from bo1.state.circuit_breaker_wrappers import record_redis_success

                record_redis_success()
            except ImportError:
                pass  # Circuit breaker not available

            # Emit Prometheus metric
            try:
                from backend.api.metrics import prom_metrics

                prom_metrics.redis_reconnect_total.inc()
            except ImportError:
                pass  # Metrics not available in all contexts

            return True

        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"[REDIS_RECONNECT] Reconnect attempt failed: {e}")
            self._connection_state = RedisConnectionState.DISCONNECTED
            # Record failure in circuit breaker
            try:
                from bo1.state.circuit_breaker_wrappers import record_redis_failure

                record_redis_failure(e)
            except ImportError:
                pass
            return False

    async def _attempt_reconnect_async(self) -> bool:
        """Async version of reconnection with non-blocking sleep.

        Returns:
            True if reconnection succeeded, False otherwise
        """
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            logger.error(
                f"[REDIS_RECONNECT] Max reconnect attempts ({self._max_reconnect_attempts}) "
                "exceeded, giving up"
            )
            return False

        self._connection_state = RedisConnectionState.RECONNECTING
        self._reconnect_attempts += 1

        # Calculate backoff delay
        delay = self._calculate_backoff_delay()
        logger.info(
            f"[REDIS_RECONNECT] Async attempt {self._reconnect_attempts}/{self._max_reconnect_attempts} "
            f"after {delay:.1f}s delay"
        )

        # Non-blocking sleep
        await asyncio.sleep(delay)
        self._last_reconnect_time = time.time()

        try:
            # Build connection pool args
            pool_kwargs: dict[str, Any] = {
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "decode_responses": True,
                "max_connections": 10,
            }
            if self.password:
                pool_kwargs["password"] = self.password

            # Create new pool and client
            self.pool = redis.ConnectionPool(**pool_kwargs)
            self.redis = redis.Redis(connection_pool=self.pool)  # type: ignore[type-arg,unused-ignore]

            # Test connection
            self.redis.ping()

            # Success - reset state
            self._available = True
            self._connection_state = RedisConnectionState.CONNECTED
            self._reconnect_attempts = 0

            logger.info(
                f"[REDIS_RECONNECT] Successfully reconnected to Redis "
                f"at {self.host}:{self.port}/{self.db}"
            )

            # Record success in circuit breaker
            try:
                from bo1.state.circuit_breaker_wrappers import record_redis_success

                record_redis_success()
            except ImportError:
                pass  # Circuit breaker not available

            # Emit Prometheus metric
            try:
                from backend.api.metrics import prom_metrics

                prom_metrics.redis_reconnect_total.inc()
            except ImportError:
                pass  # Metrics not available in all contexts

            return True

        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"[REDIS_RECONNECT] Async reconnect attempt failed: {e}")
            self._connection_state = RedisConnectionState.DISCONNECTED
            # Record failure in circuit breaker
            try:
                from bo1.state.circuit_breaker_wrappers import record_redis_failure

                record_redis_failure(e)
            except ImportError:
                pass
            return False

    def _ensure_connected(self) -> bool:
        """Ensure Redis connection is available, attempting reconnect if needed.

        Called before Redis operations to handle connection drops gracefully.
        Integrates with Redis circuit breaker - if circuit is open, returns False
        immediately without attempting reconnection.

        Returns:
            True if connected (or reconnected), False if unavailable
        """
        # Check circuit breaker first
        try:
            from bo1.state.circuit_breaker_wrappers import is_redis_circuit_open

            if is_redis_circuit_open():
                logger.debug("[REDIS_CIRCUIT] Circuit open, skipping reconnection")
                return False
        except ImportError:
            pass  # Circuit breaker not available

        if self._connection_state == RedisConnectionState.CONNECTED and self._available:
            # Already connected
            return True

        if self._connection_state == RedisConnectionState.RECONNECTING:
            # Reconnection already in progress
            return False

        # Attempt reconnection
        return self._attempt_reconnect()

    async def ensure_connected_async(self) -> bool:
        """Async version of ensure_connected for non-blocking reconnection.

        Returns:
            True if connected (or reconnected), False if unavailable
        """
        if self._connection_state == RedisConnectionState.CONNECTED and self._available:
            return True

        if self._connection_state == RedisConnectionState.RECONNECTING:
            return False

        return await self._attempt_reconnect_async()

    def _handle_connection_error(self, error: Exception) -> None:
        """Handle a connection error by updating state and preparing for reconnect.

        Records failure in Redis circuit breaker for transient errors.

        Args:
            error: The connection error that occurred
        """
        # Record failure in circuit breaker
        try:
            from bo1.state.circuit_breaker_wrappers import record_redis_failure

            record_redis_failure(error)
        except ImportError:
            pass  # Circuit breaker not available

        if self._connection_state != RedisConnectionState.DISCONNECTED:
            logger.warning(f"[REDIS_DISCONNECT] Connection lost: {error}")
            self._available = False
            self._connection_state = RedisConnectionState.DISCONNECTED

            # Send ntfy alert on disconnection
            try:
                import httpx

                from bo1.config import get_settings

                settings = get_settings()
                if settings.ntfy_topic_alerts:
                    httpx.post(
                        f"https://ntfy.sh/{settings.ntfy_topic_alerts}",
                        content=f"Redis disconnected: {error}",
                        headers={
                            "Title": "Redis Connection Lost",
                            "Priority": "high",
                            "Tags": "redis,infrastructure",
                        },
                        timeout=5,
                    )
            except ImportError:
                pass  # httpx not available in all contexts
            except Exception as alert_error:
                logger.debug(f"Failed to send disconnect alert: {alert_error}")

    def create_session(self) -> str:
        """Create a new session ID.

        Returns:
            UUID string for the new session

        Examples:
            >>> manager = RedisManager()
            >>> session_id = manager.create_session()
            >>> print(session_id)  # e.g., "bo1_7f8d9c2a-4b5e-..."
        """
        session_id = f"bo1_{uuid.uuid4()}"
        logger.info(f"📝 Created new session: {session_id}")
        return session_id

    @property
    def client(self) -> redis.Redis | None:  # type: ignore[type-arg,unused-ignore]
        """Backward compatibility: alias for self.redis.

        Returns:
            Redis client instance or None if unavailable
        """
        return self.redis

    def _get_key(self, session_id: str) -> str:
        """Get Redis key for a session.

        Args:
            session_id: Session identifier

        Returns:
            Redis key string
        """
        # Support both "session:id" and "deliberation:id" formats for backward compatibility
        if session_id.startswith("session:") or session_id.startswith("deliberation:"):
            return session_id
        return f"session:{session_id}"

    def save_state(
        self,
        session_id: str,
        state: dict[str, Any],
        ttl: int | None = None,
    ) -> bool:
        """Save deliberation state to Redis.

        Args:
            session_id: Session identifier (can include "session:" or "deliberation:" prefix)
            state: Deliberation state to save (dict)
            ttl: Optional TTL in seconds (overrides default)

        Returns:
            True if saved successfully, False otherwise

        Examples:
            >>> manager = RedisManager()
            >>> success = manager.save_state("bo1_abc123", state_dict)
            >>> # Or with custom TTL
            >>> success = manager.save_state("deliberation:test", state_dict, ttl=3600)
        """
        if not self.is_available:
            logger.debug("Redis unavailable, skipping save")
            return False

        try:
            # Serialize state to JSON
            state_json = json.dumps(state, default=str)

            # Save to Redis with TTL
            key = self._get_key(session_id)
            ttl_seconds = ttl if ttl is not None else self.ttl_seconds
            assert self.redis is not None  # Type guard: checked by is_available
            self.redis.setex(key, ttl_seconds, state_json)

            # Update last_activity_at in metadata
            try:
                from datetime import UTC, datetime

                metadata = self.load_metadata(session_id)
                if metadata:
                    metadata["last_activity_at"] = datetime.now(UTC).isoformat()
                    metadata["updated_at"] = datetime.now(UTC).isoformat()
                    self.save_metadata(session_id, metadata)
            except Exception as e:
                # Don't fail save_state if metadata update fails
                logger.debug(f"Failed to update last_activity_at: {e}")

            logger.debug(f"💾 Saved state to Redis: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save state to Redis: {e}")
            return False

    def load_state(self, session_id: str) -> dict[str, Any] | None:
        """Load deliberation state from Redis.

        Args:
            session_id: Session identifier (can include "session:" or "deliberation:" prefix)

        Returns:
            Deliberation state as dict if found, None otherwise

        Examples:
            >>> manager = RedisManager()
            >>> state = manager.load_state("bo1_abc123")
            >>> if state:
            ...     print(f"Loaded session with {len(state['contributions'])} contributions")
        """
        if not self.is_available:
            logger.debug("Redis unavailable, cannot load")
            return None

        try:
            key = self._get_key(session_id)
            assert self.redis is not None  # Type guard: checked by is_available
            state_json = self.redis.get(key)

            if not state_json:
                logger.debug(f"Session not found: {session_id}")
                return None

            # Deserialize from JSON to dict (for backward compatibility)
            state_dict: dict[str, Any] = json.loads(str(state_json))
            logger.debug(f"📂 Loaded state from Redis: {session_id}")
            return state_dict

        except Exception as e:
            logger.error(f"Failed to load state from Redis: {e}")
            return None

    def delete_state(self, session_id: str) -> bool:
        """Delete a session from Redis.

        Args:
            session_id: Session identifier

        Returns:
            True if deleted, False otherwise

        Examples:
            >>> manager = RedisManager()
            >>> manager.delete_state("bo1_abc123")
        """
        if not self.is_available:
            return False

        try:
            key = self._get_key(session_id)
            assert self.redis is not None  # Type guard: checked by is_available
            deleted = self.redis.delete(key)
            logger.debug(f"🗑️  Deleted session: {session_id}")
            return bool(deleted)

        except Exception as e:
            logger.error(f"Failed to delete state: {e}")
            return False

    def list_sessions(self) -> list[str]:
        """List all active sessions.

        Returns:
            List of session IDs

        Examples:
            >>> manager = RedisManager()
            >>> sessions = manager.list_sessions()
            >>> print(f"Found {len(sessions)} active sessions")
        """
        if not self.is_available:
            return []

        try:
            # Scan for all session keys (both session: and metadata: prefixes)
            assert self.redis is not None  # Type guard: checked by is_available
            session_keys = cast(list[str], self.redis.keys("session:bo1_*"))
            metadata_keys = cast(list[str], self.redis.keys("metadata:bo1_*"))

            # Extract session IDs from both sources
            session_ids_set: set[str] = set()

            if session_keys:
                session_ids_set.update(key.replace("session:", "") for key in session_keys)

            if metadata_keys:
                session_ids_set.update(key.replace("metadata:", "") for key in metadata_keys)

            return list(session_ids_set)

        except Exception as e:
            logger.error(f"Failed to list sessions: {e}")
            return []

    def get_session_ttl(self, session_id: str) -> int:
        """Get remaining TTL for a session in seconds.

        Args:
            session_id: Session identifier

        Returns:
            TTL in seconds, -1 if no expiry, -2 if not found

        Examples:
            >>> manager = RedisManager()
            >>> ttl = manager.get_session_ttl("bo1_abc123")
            >>> print(f"Session expires in {ttl // 3600} hours")
        """
        if not self.is_available:
            return -2

        try:
            key = self._get_key(session_id)
            assert self.redis is not None  # Type guard: checked by is_available
            ttl_value = self.redis.ttl(key)
            # Redis ttl() returns int directly when decode_responses=True
            return int(ttl_value) if isinstance(ttl_value, (int, str)) else -2

        except Exception as e:
            logger.error(f"Failed to get TTL: {e}")
            return -2

    def extend_session(self, session_id: str, additional_seconds: int = 86400) -> bool:
        """Extend the TTL of a session.

        Args:
            session_id: Session identifier
            additional_seconds: Seconds to add to current TTL

        Returns:
            True if extended, False otherwise

        Examples:
            >>> manager = RedisManager()
            >>> manager.extend_session("bo1_abc123", 86400)  # Add 24 hours
        """
        if not self.is_available:
            return False

        try:
            key = self._get_key(session_id)
            assert self.redis is not None  # Type guard: checked by is_available
            ttl_value = self.redis.ttl(key)
            # Redis ttl() returns int directly when decode_responses=True
            current_ttl = int(ttl_value) if isinstance(ttl_value, (int, str)) else -2

            if current_ttl < 0:
                # Session doesn't exist or has no expiry
                return False

            new_ttl = current_ttl + additional_seconds
            assert self.redis is not None  # Type guard: checked by is_available
            self.redis.expire(key, new_ttl)
            logger.debug(f"⏰ Extended session TTL: {session_id} (+{additional_seconds}s)")
            return True

        except Exception as e:
            logger.error(f"Failed to extend session: {e}")
            return False

    def save_metadata(self, session_id: str, metadata: dict[str, Any]) -> bool:
        """Save session metadata separately from state.

        Useful for storing lightweight data like creation time, user info, etc.

        Args:
            session_id: Session identifier
            metadata: Dictionary of metadata to save

        Returns:
            True if saved, False otherwise

        Examples:
            >>> manager = RedisManager()
            >>> manager.save_metadata("bo1_abc123", {
            ...     "created_at": "2025-11-12T10:30:00",
            ...     "user_id": "user_123",
            ...     "problem_title": "Pricing Strategy"
            ... })
        """
        if not self.is_available:
            return False

        try:
            key = f"metadata:{session_id}"
            metadata_json = json.dumps(metadata)
            assert self.redis is not None  # Type guard: checked by is_available
            self.redis.setex(key, self.ttl_seconds, metadata_json)
            return True

        except Exception as e:
            logger.error(f"Failed to save metadata: {e}")
            return False

    def load_metadata(
        self,
        session_id: str,
        recache_ttl_seconds: int = 3600,
    ) -> dict[str, Any] | None:
        """Load session metadata with PostgreSQL fallback.

        Attempts to load from Redis first. If Redis returns None (cache miss
        or TTL expiry), falls back to PostgreSQL via SessionRepository.
        Optionally re-caches metadata in Redis on successful DB fetch.

        Args:
            session_id: Session identifier
            recache_ttl_seconds: TTL for re-cached metadata (default: 3600).
                Set to 0 to disable re-caching on DB hit.

        Returns:
            Metadata dictionary if found, None otherwise

        Examples:
            >>> manager = RedisManager()
            >>> metadata = manager.load_metadata("bo1_abc123")
            >>> if metadata:
            ...     print(f"Session created: {metadata['created_at']}")
        """
        # Try Redis first
        if self.is_available:
            try:
                key = f"metadata:{session_id}"
                assert self.redis is not None  # Type guard: checked by is_available
                metadata_json = self.redis.get(key)

                if metadata_json:
                    metadata: dict[str, Any] = json.loads(str(metadata_json))
                    return metadata

            except Exception as e:
                logger.error(f"Failed to load metadata from Redis: {e}")

        # Fallback to PostgreSQL
        try:
            from bo1.state.repositories import session_repository

            db_metadata = session_repository.get_metadata(session_id)
            if db_metadata:
                logger.info(f"[REDIS_FALLBACK] Loaded metadata from DB for {session_id}")

                # Emit Prometheus metric
                try:
                    from backend.api.metrics import prom_metrics

                    prom_metrics.redis_metadata_fallback_total.labels(result="success").inc()
                except ImportError:
                    pass  # Metrics not available in all contexts

                # Re-cache in Redis if enabled and Redis is available
                if recache_ttl_seconds > 0 and self.is_available:
                    try:
                        key = f"metadata:{session_id}"
                        metadata_json = json.dumps(db_metadata)
                        assert self.redis is not None
                        self.redis.setex(key, recache_ttl_seconds, metadata_json)
                        logger.debug(f"[REDIS_FALLBACK] Re-cached metadata for {session_id}")
                    except Exception as cache_err:
                        logger.warning(f"Failed to re-cache metadata: {cache_err}")

                return db_metadata

            # DB also returned None
            logger.debug(f"[REDIS_FALLBACK] Session not found in DB: {session_id}")
            try:
                from backend.api.metrics import prom_metrics

                prom_metrics.redis_metadata_fallback_total.labels(result="failure").inc()
            except ImportError:
                pass

            return None

        except Exception as e:
            logger.error(f"[REDIS_FALLBACK] Failed to load metadata from DB: {e}")
            try:
                from backend.api.metrics import prom_metrics

                prom_metrics.redis_metadata_fallback_total.labels(result="failure").inc()
            except ImportError:
                pass
            return None

    def add_session_to_user_index(self, user_id: str, session_id: str) -> bool:
        """Add session to user's session index.

        Args:
            user_id: User identifier
            session_id: Session identifier

        Returns:
            True if successful, False otherwise

        Examples:
            >>> manager = RedisManager()
            >>> manager.add_session_to_user_index("user123", "bo1_abc")
            True
        """
        if not self.is_available:
            return False

        try:
            key = f"user_sessions:{user_id}"
            assert self.redis is not None
            self.redis.sadd(key, session_id)
            # Set TTL to match session TTL (24 hours default)
            self.redis.expire(key, self.ttl_seconds)
            return True

        except Exception as e:
            logger.error(f"Failed to add session to user index: {e}")
            return False

    def remove_session_from_user_index(self, user_id: str, session_id: str) -> bool:
        """Remove session from user's session index.

        Args:
            user_id: User identifier
            session_id: Session identifier

        Returns:
            True if successful, False otherwise

        Examples:
            >>> manager = RedisManager()
            >>> manager.remove_session_from_user_index("user123", "bo1_abc")
            True
        """
        if not self.is_available:
            return False

        try:
            key = f"user_sessions:{user_id}"
            assert self.redis is not None
            self.redis.srem(key, session_id)
            return True

        except Exception as e:
            logger.error(f"Failed to remove session from user index: {e}")
            return False

    def list_user_sessions(self, user_id: str) -> list[str]:
        """List all session IDs for a specific user.

        Args:
            user_id: User identifier

        Returns:
            List of session IDs owned by the user

        Examples:
            >>> manager = RedisManager()
            >>> sessions = manager.list_user_sessions("user123")
            >>> print(f"User has {len(sessions)} sessions")
        """
        if not self.is_available:
            return []

        try:
            key = f"user_sessions:{user_id}"
            assert self.redis is not None
            session_ids = cast(set[str], self.redis.smembers(key))

            if not session_ids:
                return []

            # Convert set to list (Redis returns set of strings)
            return list(session_ids)

        except Exception as e:
            logger.error(f"Failed to list user sessions: {e}")
            return []

    def batch_load_metadata(self, session_ids: list[str]) -> dict[str, dict[str, Any]]:
        """Batch load metadata for multiple sessions using Redis pipeline.

        Args:
            session_ids: List of session identifiers

        Returns:
            Dictionary mapping session_id to metadata (only for sessions that exist)

        Examples:
            >>> manager = RedisManager()
            >>> session_ids = ["bo1_abc", "bo1_def"]
            >>> metadata_dict = manager.batch_load_metadata(session_ids)
            >>> print(f"Loaded metadata for {len(metadata_dict)} sessions")
        """
        if not self.is_available or not session_ids:
            return {}

        try:
            assert self.redis is not None

            # Use pipeline to batch all GET requests
            pipe = self.redis.pipeline()
            for session_id in session_ids:
                key = f"metadata:{session_id}"
                pipe.get(key)

            # Execute all requests in one roundtrip
            results = pipe.execute()

            # Parse results
            metadata_dict: dict[str, dict[str, Any]] = {}
            for session_id, metadata_json in zip(session_ids, results, strict=True):
                if metadata_json:
                    try:
                        metadata = json.loads(str(metadata_json))
                        metadata_dict[session_id] = metadata
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse metadata for {session_id}")
                        continue

            return metadata_dict

        except Exception as e:
            logger.error(f"Failed to batch load metadata: {e}")
            return {}

    def cleanup_session(self, session_id: str, user_id: str | None = None) -> dict[str, bool]:
        """Clean up all Redis data for a completed session.

        Removes transient Redis data after a session completes, since the
        authoritative data is now in PostgreSQL. This frees Redis memory
        and ensures completed meetings are read from Postgres.

        Cleans up:
        - session:{session_id} - LangGraph state
        - metadata:{session_id} - Session metadata
        - events_history:{session_id} - Event history
        - user_sessions:{user_id} - Removes from user's index (if user_id provided)

        Note: LangGraph checkpoints (managed by AsyncRedisSaver) use a different
        key pattern and have their own TTL. This cleans up our custom keys.

        Args:
            session_id: Session identifier to clean up
            user_id: Optional user ID to remove session from user index

        Returns:
            Dict showing which keys were cleaned up

        Examples:
            >>> manager = RedisManager()
            >>> result = manager.cleanup_session("bo1_abc123", "user_456")
            >>> print(result)
            {'session': True, 'metadata': True, 'events': True, 'user_index': True}
        """
        result = {
            "session": False,
            "metadata": False,
            "events": False,
            "user_index": False,
        }

        if not self.is_available:
            logger.debug("Redis unavailable, skipping cleanup")
            return result

        assert self.redis is not None

        try:
            # Use pipeline for atomic cleanup
            pipe = self.redis.pipeline()

            # Delete session state
            session_key = self._get_key(session_id)
            pipe.delete(session_key)

            # Delete metadata
            metadata_key = f"metadata:{session_id}"
            pipe.delete(metadata_key)

            # Delete event history
            events_key = f"events_history:{session_id}"
            pipe.delete(events_key)

            # Remove from user index if user_id provided
            if user_id:
                user_key = f"user_sessions:{user_id}"
                pipe.srem(user_key, session_id)

            # Execute all deletes
            results = pipe.execute()

            # Parse results
            result["session"] = bool(results[0])
            result["metadata"] = bool(results[1])
            result["events"] = bool(results[2])
            if user_id:
                result["user_index"] = bool(results[3])

            cleaned = sum(1 for v in result.values() if v)
            logger.info(f"🧹 Cleaned up {cleaned} Redis keys for session {session_id}")

            return result

        except Exception as e:
            logger.error(f"Failed to cleanup session {session_id}: {e}")
            return result

    def schedule_cleanup(
        self, session_id: str, user_id: str | None = None, delay_seconds: int | None = None
    ) -> bool:
        """Schedule session cleanup after a grace period.

        Instead of immediate cleanup, sets short TTL on keys to allow
        for reconnections and final data retrieval.

        Args:
            session_id: Session identifier
            user_id: Optional user ID (unused, but kept for API consistency)
            delay_seconds: Cleanup delay in seconds (default: 1 hour)

        Returns:
            True if TTLs were set successfully
        """
        from bo1.constants import DatabaseConfig

        if not self.is_available:
            return False

        delay = delay_seconds or DatabaseConfig.REDIS_CLEANUP_GRACE_PERIOD_SECONDS

        assert self.redis is not None

        try:
            pipe = self.redis.pipeline()

            # Set TTL on all session keys
            session_key = self._get_key(session_id)
            pipe.expire(session_key, delay)

            metadata_key = f"metadata:{session_id}"
            pipe.expire(metadata_key, delay)

            events_key = f"events_history:{session_id}"
            pipe.expire(events_key, delay)

            pipe.execute()

            logger.info(
                f"⏰ Scheduled cleanup for session {session_id} in {delay}s ({delay // 60} min)"
            )
            return True

        except Exception as e:
            logger.error(f"Failed to schedule cleanup for session {session_id}: {e}")
            return False

    def get_cached_user_id(self, session_id: str) -> str | None:
        """Get user_id from Redis metadata cache with DB fallback.

        Uses load_metadata() which has built-in PostgreSQL fallback when
        Redis cache misses. This provides a single optimized lookup path.

        Args:
            session_id: Session identifier

        Returns:
            user_id if found, None otherwise

        Examples:
            >>> manager = RedisManager()
            >>> user_id = manager.get_cached_user_id("bo1_abc123")
            >>> if user_id:
            ...     print(f"Session owned by: {user_id}")
        """
        # load_metadata has Redis->PostgreSQL fallback with re-caching
        metadata = self.load_metadata(session_id)
        if metadata and metadata.get("user_id"):
            return str(metadata["user_id"])

        logger.debug(f"[REDIS_FALLBACK] No user_id found for {session_id}")
        return None

    def get_pool_health(self) -> dict[str, Any]:
        """Get Redis connection pool health metrics.

        Returns pool statistics including:
        - used_connections: Connections currently in use
        - free_connections: Connections available in pool
        - max_connections: Maximum pool size
        - utilization_pct: Pool utilization percentage (0-100)
        - healthy: Whether pool is in healthy state

        Note: redis-py ConnectionPool uses internal attributes that may vary by version:
        - _in_use_connections: set of connections currently checked out
        - _available_connections: list of connections available

        Returns:
            Dict with pool health metrics

        Examples:
            >>> manager = RedisManager()
            >>> health = manager.get_pool_health()
            >>> print(f"Pool utilization: {health['utilization_pct']:.1f}%")
        """
        if not self.is_available or not self.pool:
            return {
                "healthy": False,
                "used_connections": 0,
                "free_connections": 0,
                "max_connections": 0,
                "utilization_pct": 0.0,
                "error": "Redis pool not available",
            }

        try:
            # Access pool internals (redis-py implementation detail)
            # _in_use_connections is a set of connections currently in use
            # _available_connections is a list of available connections
            in_use: set[object] = getattr(self.pool, "_in_use_connections", set())
            available = getattr(self.pool, "_available_connections", [])
            max_conns = getattr(self.pool, "max_connections", 10)

            used_count = len(in_use) if in_use else 0
            free_count = len(available) if available else 0

            # Calculate utilization (used / max, not used / total_created)
            utilization = (used_count / max_conns * 100) if max_conns > 0 else 0.0

            return {
                "healthy": True,
                "used_connections": used_count,
                "free_connections": free_count,
                "max_connections": max_conns,
                "utilization_pct": round(utilization, 2),
            }

        except Exception as e:
            logger.warning(f"[REDIS_POOL] Failed to get pool health: {e}")
            return {
                "healthy": False,
                "used_connections": 0,
                "free_connections": 0,
                "max_connections": 0,
                "utilization_pct": 0.0,
                "error": str(e),
            }

    def close(self) -> None:
        """Close Redis connection pool.

        Examples:
            >>> manager = RedisManager()
            >>> # ... use manager ...
            >>> manager.close()
        """
        if self.is_available and self.pool:
            self.pool.disconnect()
            logger.info("Closed Redis connection pool")

    # =========================================================================
    # User Context Caching
    # =========================================================================

    def get_cached_context(self, user_id: str) -> dict[str, Any] | None:
        """Get cached user context from Redis.

        Args:
            user_id: User identifier

        Returns:
            Cached context dict if found, None otherwise

        Examples:
            >>> manager = RedisManager()
            >>> context = manager.get_cached_context("user123")
            >>> if context:
            ...     print(f"Cache hit for user {user_id}")
        """
        from bo1.constants import UserContextCache

        if not UserContextCache.is_enabled():
            return None

        if not self.is_available:
            logger.debug("Redis unavailable, skipping context cache lookup")
            return None

        try:
            key = f"{UserContextCache.KEY_PREFIX}{user_id}"
            assert self.redis is not None
            context_json = self.redis.get(key)

            if context_json:
                context: dict[str, Any] = json.loads(str(context_json))
                logger.debug(f"[CONTEXT_CACHE] Hit for user {user_id}")
                return context

            logger.debug(f"[CONTEXT_CACHE] Miss for user {user_id}")
            return None

        except Exception as e:
            logger.warning(f"[CONTEXT_CACHE] Error fetching context for {user_id}: {e}")
            return None

    def cache_context(self, user_id: str, context: dict[str, Any], ttl: int | None = None) -> bool:
        """Cache user context in Redis.

        Args:
            user_id: User identifier
            context: Context dict to cache
            ttl: Optional TTL override (defaults to UserContextCache.TTL_SECONDS)

        Returns:
            True if cached successfully, False otherwise

        Examples:
            >>> manager = RedisManager()
            >>> manager.cache_context("user123", {"company_name": "Acme"})
            True
        """
        from bo1.constants import UserContextCache

        if not UserContextCache.is_enabled():
            return False

        if not self.is_available:
            logger.debug("Redis unavailable, skipping context cache write")
            return False

        try:
            key = f"{UserContextCache.KEY_PREFIX}{user_id}"
            context_json = json.dumps(context, default=str)
            ttl_seconds = ttl if ttl is not None else UserContextCache.TTL_SECONDS

            assert self.redis is not None
            self.redis.setex(key, ttl_seconds, context_json)
            logger.debug(f"[CONTEXT_CACHE] Cached context for user {user_id} (TTL={ttl_seconds}s)")
            return True

        except Exception as e:
            logger.warning(f"[CONTEXT_CACHE] Error caching context for {user_id}: {e}")
            return False

    def invalidate_context(self, user_id: str) -> bool:
        """Invalidate cached user context in Redis.

        Called after context updates to ensure cache consistency.

        Args:
            user_id: User identifier

        Returns:
            True if invalidated (or key didn't exist), False on error

        Examples:
            >>> manager = RedisManager()
            >>> manager.invalidate_context("user123")
            True
        """
        from bo1.constants import UserContextCache

        if not UserContextCache.is_enabled():
            return True  # Nothing to invalidate

        if not self.is_available:
            logger.debug("Redis unavailable, skipping context cache invalidation")
            return True  # Not an error - just no cache to clear

        try:
            key = f"{UserContextCache.KEY_PREFIX}{user_id}"
            assert self.redis is not None
            deleted = self.redis.delete(key)
            if deleted:
                logger.info(f"[CONTEXT_CACHE] Invalidated cache for user {user_id}")
            else:
                logger.debug(f"[CONTEXT_CACHE] No cache to invalidate for user {user_id}")
            return True

        except Exception as e:
            logger.warning(f"[CONTEXT_CACHE] Error invalidating context for {user_id}: {e}")
            return False
