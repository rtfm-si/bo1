"""Redis-based state management for deliberation sessions.

Handles:
- Session persistence with TTL
- State serialization/deserialization
- Connection pooling
- Error handling and fallback
"""

import json
import logging
import uuid
from typing import Any

import redis

from bo1.config import get_settings
from bo1.models.state import DeliberationState

logger = logging.getLogger(__name__)


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
        ttl_seconds: int = 86400,  # 24 hours
    ) -> None:
        """Initialize Redis manager.

        Args:
            host: Redis host (defaults to config)
            port: Redis port (defaults to config)
            db: Redis database number (defaults to config)
            ttl_seconds: Session TTL in seconds (default: 24 hours)
        """
        settings = get_settings()

        self.host = host or settings.redis_host
        self.port = port or settings.redis_port
        self.db = db or settings.redis_db
        self.ttl_seconds = ttl_seconds

        # Initialize connection pool
        try:
            self.pool = redis.ConnectionPool(
                host=self.host,
                port=self.port,
                db=self.db,
                decode_responses=True,  # Auto-decode bytes to str
                max_connections=10,
            )
            self.redis: redis.Redis | None = redis.Redis(connection_pool=self.pool)  # type: ignore[type-arg]

            # Test connection
            assert self.redis is not None  # Type guard: checked by is_available
            self.redis.ping()
            logger.info(f"✅ Connected to Redis at {self.host}:{self.port}/{self.db}")
            self._available = True

        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.warning(f"⚠️  Redis unavailable: {e}. Continuing without persistence.")
            self._available = False
            self.redis = None

    @property
    def is_available(self) -> bool:
        """Check if Redis is available."""
        return self._available

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

    def _get_key(self, session_id: str) -> str:
        """Get Redis key for a session.

        Args:
            session_id: Session identifier

        Returns:
            Redis key string
        """
        return f"session:{session_id}"

    def save_state(self, session_id: str, state: DeliberationState) -> bool:
        """Save deliberation state to Redis.

        Args:
            session_id: Session identifier
            state: Deliberation state to save

        Returns:
            True if saved successfully, False otherwise

        Examples:
            >>> manager = RedisManager()
            >>> state = DeliberationState(...)
            >>> success = manager.save_state("bo1_abc123", state)
        """
        if not self.is_available:
            logger.debug("Redis unavailable, skipping save")
            return False

        try:
            # Serialize state to JSON
            state_json = state.model_dump_json()

            # Save to Redis with TTL
            key = self._get_key(session_id)
            assert self.redis is not None  # Type guard: checked by is_available
            self.redis.setex(key, self.ttl_seconds, state_json)

            logger.debug(f"💾 Saved state to Redis: {session_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to save state to Redis: {e}")
            return False

    def load_state(self, session_id: str) -> DeliberationState | None:
        """Load deliberation state from Redis.

        Args:
            session_id: Session identifier

        Returns:
            Deliberation state if found, None otherwise

        Examples:
            >>> manager = RedisManager()
            >>> state = manager.load_state("bo1_abc123")
            >>> if state:
            ...     print(f"Loaded session with {len(state.contributions)} contributions")
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

            # Deserialize from JSON
            state = DeliberationState.model_validate_json(str(state_json))
            logger.debug(f"📂 Loaded state from Redis: {session_id}")
            return state

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
            # Scan for all session keys
            assert self.redis is not None  # Type guard: checked by is_available
            keys_result = self.redis.keys("session:bo1_*")
            # Extract session IDs (keys are already strings with decode_responses=True)
            keys = list(keys_result) if keys_result else []
            session_ids = [str(key).replace("session:", "") for key in keys]
            return session_ids

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
            ttl = self.redis.ttl(key)
            return int(ttl)

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
            current_ttl = int(self.redis.ttl(key))

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

    def load_metadata(self, session_id: str) -> dict[str, Any] | None:
        """Load session metadata.

        Args:
            session_id: Session identifier

        Returns:
            Metadata dictionary if found, None otherwise

        Examples:
            >>> manager = RedisManager()
            >>> metadata = manager.load_metadata("bo1_abc123")
            >>> if metadata:
            ...     print(f"Session created: {metadata['created_at']}")
        """
        if not self.is_available:
            return None

        try:
            key = f"metadata:{session_id}"
            assert self.redis is not None  # Type guard: checked by is_available
            metadata_json = self.redis.get(key)

            if not metadata_json:
                return None

            metadata: dict[str, Any] = json.loads(str(metadata_json))
            return metadata

        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return None

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
