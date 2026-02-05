"""Session management for BFF (Backend-for-Frontend) OAuth pattern.

Handles:
- OAuth flow state (PKCE verifiers, redirect URIs)
- User sessions (tokens, user data)
- Session storage in Redis with TTL
- Session CRUD operations

Security:
- Tokens never exposed to frontend (stored only in Redis)
- httpOnly cookies prevent XSS attacks
- Short-lived OAuth state (10 min TTL)
- Session auto-expiry (1 hour TTL)
"""

import json
import logging
import secrets
from datetime import UTC, datetime
from typing import Any

from bo1.logging.errors import ErrorCode, log_error
from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)

# TTL constants
OAUTH_STATE_TTL = 600  # 10 minutes (just for OAuth flow)
SESSION_TTL = 3600  # 1 hour (user session)


class SessionManager:
    """Manages OAuth state and user sessions in Redis.

    Examples:
        >>> manager = SessionManager()
        >>>
        >>> # OAuth flow
        >>> state_id = manager.create_oauth_state("code_verifier_xyz", "http://app/callback")
        >>> state = manager.get_oauth_state(state_id)
        >>> manager.delete_oauth_state(state_id)
        >>>
        >>> # User session
        >>> session_id = manager.create_session("user_123", "user@example.com", tokens)
        >>> session = manager.get_session(session_id)
        >>> manager.delete_session(session_id)
    """

    def __init__(self, redis_manager: RedisManager | None = None) -> None:
        """Initialize session manager.

        Args:
            redis_manager: Optional RedisManager instance. If None, creates new one.
        """
        self.redis = redis_manager or RedisManager()
        if not self.redis.is_available:
            log_error(
                logger,
                ErrorCode.REDIS_CONNECTION_ERROR,
                "Redis not available - session management will fail!",
            )

    # Generic key-value methods for OAuth state

    def set(self, key: str, value: dict[str, Any], expiry: int = OAUTH_STATE_TTL) -> None:
        """Store a value in Redis with TTL.

        Args:
            key: Redis key
            value: Dict to store (will be JSON encoded)
            expiry: TTL in seconds (default 600)
        """
        if not self.redis.redis:
            log_error(logger, ErrorCode.REDIS_CONNECTION_ERROR, "Redis client not available")
            return

        try:
            self.redis.redis.setex(key, expiry, json.dumps(value))
            logger.debug(f"Set key: {key[:20]}... (TTL: {expiry}s)")
        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_WRITE_ERROR,
                f"Failed to set key {key}: {e}",
                exc_info=True,
            )
            raise

    def get(self, key: str) -> dict[str, Any] | None:
        """Retrieve a value from Redis.

        Args:
            key: Redis key

        Returns:
            Stored dict or None if not found
        """
        if not self.redis.redis:
            log_error(logger, ErrorCode.REDIS_CONNECTION_ERROR, "Redis client not available")
            return None

        try:
            data = self.redis.redis.get(key)
            if not data:
                return None
            result: dict[str, Any] = json.loads(str(data))
            return result
        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_READ_ERROR,
                f"Failed to get key {key}: {e}",
                exc_info=True,
            )
            return None

    def delete(self, key: str) -> bool:
        """Delete a key from Redis.

        Args:
            key: Redis key

        Returns:
            True if deleted
        """
        if not self.redis.redis:
            log_error(logger, ErrorCode.REDIS_CONNECTION_ERROR, "Redis client not available")
            return False

        try:
            return bool(self.redis.redis.delete(key))
        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_WRITE_ERROR,
                f"Failed to delete key {key}: {e}",
                exc_info=True,
            )
            return False

    # OAuth Flow State Management

    def create_oauth_state(
        self,
        code_verifier: str,
        redirect_uri: str | None = None,
    ) -> str:
        """Create OAuth flow state and store in Redis.

        Args:
            code_verifier: PKCE code verifier (random string)
            redirect_uri: Optional redirect URI after OAuth completes

        Returns:
            state_id: Random state parameter for CSRF protection

        Examples:
            >>> manager = SessionManager()
            >>> state_id = manager.create_oauth_state("verifier_123", "/dashboard")
        """
        # Generate random state ID
        state_id = secrets.token_urlsafe(32)

        # Create state data
        state_data = {
            "code_verifier": code_verifier,
            "redirect_uri": redirect_uri,
            "created_at": datetime.now(UTC).isoformat(),
        }

        # Save to Redis with short TTL
        key = f"oauth_state:{state_id}"
        if not self.redis.redis:
            log_error(logger, ErrorCode.REDIS_CONNECTION_ERROR, "Redis client not available")
            return state_id

        try:
            self.redis.redis.setex(
                key,
                OAUTH_STATE_TTL,
                json.dumps(state_data),
            )
            logger.info(f"Created OAuth state: {state_id[:8]}... (TTL: {OAUTH_STATE_TTL}s)")
            return state_id

        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_WRITE_ERROR,
                f"Failed to create OAuth state: {e}",
                exc_info=True,
            )
            raise

    def get_oauth_state(self, state_id: str) -> dict[str, Any] | None:
        """Retrieve OAuth flow state from Redis.

        Args:
            state_id: State parameter from OAuth callback

        Returns:
            State data dict with code_verifier, redirect_uri, created_at
            None if not found or expired

        Examples:
            >>> manager = SessionManager()
            >>> state = manager.get_oauth_state("abc123...")
            >>> if state:
            ...     verifier = state["code_verifier"]
        """
        key = f"oauth_state:{state_id}"
        if not self.redis.redis:
            log_error(logger, ErrorCode.REDIS_CONNECTION_ERROR, "Redis client not available")
            return None

        try:
            state_json = self.redis.redis.get(key)

            if not state_json:
                logger.warning(f"OAuth state not found: {state_id[:8]}...")
                return None

            state_data: dict[str, Any] = json.loads(str(state_json))
            logger.debug(f"Retrieved OAuth state: {state_id[:8]}...")
            return state_data

        except Exception as e:
            log_error(
                logger, ErrorCode.REDIS_READ_ERROR, f"Failed to get OAuth state: {e}", exc_info=True
            )
            return None

    def delete_oauth_state(self, state_id: str) -> bool:
        """Delete OAuth flow state from Redis (one-time use).

        Args:
            state_id: State parameter to delete

        Returns:
            True if deleted, False otherwise

        Examples:
            >>> manager = SessionManager()
            >>> manager.delete_oauth_state("abc123...")
        """
        key = f"oauth_state:{state_id}"
        if not self.redis.redis:
            log_error(logger, ErrorCode.REDIS_CONNECTION_ERROR, "Redis client not available")
            return False

        try:
            deleted = self.redis.redis.delete(key)
            if deleted:
                logger.debug(f"Deleted OAuth state: {state_id[:8]}...")
            return bool(deleted)

        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_WRITE_ERROR,
                f"Failed to delete OAuth state: {e}",
                exc_info=True,
            )
            return False

    # User Session Management

    def create_session(
        self,
        user_id: str,
        email: str,
        tokens: dict[str, Any],
    ) -> str:
        """Create user session and store in Redis.

        Args:
            user_id: User ID (UUID from Supabase)
            email: User email
            tokens: Dict with access_token, refresh_token, expires_in

        Returns:
            session_id: Random session identifier

        Examples:
            >>> manager = SessionManager()
            >>> tokens = {"access_token": "jwt...", "refresh_token": "jwt...", "expires_in": 3600}
            >>> session_id = manager.create_session("user_123", "user@example.com", tokens)
        """
        # Generate random session ID
        session_id = secrets.token_urlsafe(32)

        # Calculate token expiry timestamp
        now = datetime.now(UTC)
        expires_in = tokens.get("expires_in", SESSION_TTL)
        expires_at = now.timestamp() + expires_in

        # Create session data
        session_data = {
            "user_id": user_id,
            "email": email,
            "access_token": tokens.get("access_token", ""),
            "refresh_token": tokens.get("refresh_token", ""),
            "expires_at": expires_at,
            "created_at": now.isoformat(),
        }

        # Save to Redis with TTL
        key = f"session:{session_id}"
        if not self.redis.redis:
            log_error(
                logger,
                ErrorCode.REDIS_CONNECTION_ERROR,
                "Redis client not available",
                user_id=user_id,
            )
            return session_id

        try:
            self.redis.redis.setex(
                key,
                SESSION_TTL,
                json.dumps(session_data),
            )
            logger.info(f"Created session for {email}: {session_id[:8]}... (TTL: {SESSION_TTL}s)")
            return session_id

        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_WRITE_ERROR,
                f"Failed to create session: {e}",
                exc_info=True,
                user_id=user_id,
                email=email,
            )
            raise

    def get_session(self, session_id: str) -> dict[str, Any] | None:
        """Retrieve user session from Redis.

        Args:
            session_id: Session identifier from cookie

        Returns:
            Session data dict with user_id, email, access_token, etc.
            None if not found or expired

        Examples:
            >>> manager = SessionManager()
            >>> session = manager.get_session("xyz789...")
            >>> if session:
            ...     user_id = session["user_id"]
            ...     access_token = session["access_token"]
        """
        key = f"session:{session_id}"
        if not self.redis.redis:
            log_error(
                logger,
                ErrorCode.REDIS_CONNECTION_ERROR,
                "Redis client not available",
                session_id=session_id,
            )
            return None

        try:
            session_json = self.redis.redis.get(key)

            if not session_json:
                logger.debug(f"Session not found: {session_id[:8]}...")
                return None

            session_data: dict[str, Any] = json.loads(str(session_json))
            logger.debug(
                f"Retrieved session: {session_id[:8]}... (user: {session_data.get('email')})"
            )
            return session_data

        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_READ_ERROR,
                f"Failed to get session: {e}",
                exc_info=True,
                session_id=session_id,
            )
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete user session from Redis (logout).

        Args:
            session_id: Session identifier to delete

        Returns:
            True if deleted, False otherwise

        Examples:
            >>> manager = SessionManager()
            >>> manager.delete_session("xyz789...")
        """
        key = f"session:{session_id}"
        if not self.redis.redis:
            log_error(
                logger,
                ErrorCode.REDIS_CONNECTION_ERROR,
                "Redis client not available",
                session_id=session_id,
            )
            return False

        try:
            deleted = self.redis.redis.delete(key)
            if deleted:
                logger.info(f"Deleted session: {session_id[:8]}...")
            return bool(deleted)

        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_WRITE_ERROR,
                f"Failed to delete session: {e}",
                exc_info=True,
                session_id=session_id,
            )
            return False

    def refresh_session(self, session_id: str, new_tokens: dict[str, Any]) -> bool:
        """Update session with refreshed tokens.

        Args:
            session_id: Session identifier
            new_tokens: Dict with new access_token, refresh_token, expires_in

        Returns:
            True if updated, False otherwise

        Examples:
            >>> manager = SessionManager()
            >>> new_tokens = {"access_token": "new_jwt...", "refresh_token": "new_jwt...", "expires_in": 3600}
            >>> manager.refresh_session("xyz789...", new_tokens)
        """
        # Get existing session
        session = self.get_session(session_id)
        if not session:
            logger.warning(f"Cannot refresh - session not found: {session_id[:8]}...")
            return False

        # Update token fields
        now = datetime.now(UTC)
        expires_in = new_tokens.get("expires_in", SESSION_TTL)
        session["access_token"] = new_tokens.get("access_token", "")
        session["refresh_token"] = new_tokens.get("refresh_token", "")
        session["expires_at"] = now.timestamp() + expires_in

        # Save updated session
        key = f"session:{session_id}"
        if not self.redis.redis:
            log_error(
                logger,
                ErrorCode.REDIS_CONNECTION_ERROR,
                "Redis client not available",
                session_id=session_id,
            )
            return False

        try:
            self.redis.redis.setex(
                key,
                SESSION_TTL,
                json.dumps(session),
            )
            logger.info(f"Refreshed session: {session_id[:8]}... (user: {session.get('email')})")
            return True

        except Exception as e:
            log_error(
                logger,
                ErrorCode.REDIS_WRITE_ERROR,
                f"Failed to refresh session: {e}",
                exc_info=True,
                session_id=session_id,
            )
            return False
