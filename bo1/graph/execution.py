"""Session execution and management for LangGraph deliberations.

This module provides:
- SessionManager: Manages active deliberation sessions
- Kill switches: User and admin session termination
- Graceful shutdown: Signal handlers for deployment
"""

import asyncio
import logging
import signal
import time
from typing import Any

from bo1.state.redis_manager import RedisManager

logger = logging.getLogger(__name__)


class PermissionError(Exception):
    """Raised when user attempts unauthorized action."""

    pass


class SessionManager:
    """Manages active deliberation sessions with kill switch capabilities.

    Features:
    - Track active background tasks
    - User kill switch (ownership enforced)
    - Admin kill switch (any session)
    - Emergency kill all (admin only)
    - Graceful shutdown on SIGTERM/SIGINT
    """

    def __init__(self, redis_manager: RedisManager, admin_user_ids: set[str] | None = None) -> None:
        """Initialize session manager.

        Args:
            redis_manager: Redis state manager for metadata persistence
            admin_user_ids: Set of user IDs with admin privileges (optional)
        """
        self.redis_manager = redis_manager
        self.admin_user_ids = admin_user_ids or set()
        self.active_executions: dict[str, asyncio.Task[Any]] = {}
        self._shutdown_event = asyncio.Event()
        self._setup_signal_handlers()

    def is_admin(self, user_id: str) -> bool:
        """Check if user has admin privileges.

        Args:
            user_id: User ID to check

        Returns:
            True if user is admin, False otherwise
        """
        return user_id in self.admin_user_ids

    async def start_session(self, session_id: str, user_id: str, coro: Any) -> asyncio.Task[Any]:
        """Start a new deliberation session as background task.

        Args:
            session_id: Unique session identifier
            user_id: User who owns this session
            coro: Coroutine to execute (graph.ainvoke())

        Returns:
            Background asyncio.Task
        """
        # Store ownership metadata
        self._save_session_metadata(
            session_id,
            {
                "user_id": user_id,
                "status": "running",
                "started_at": str(time.time()),
            },
        )

        # Create background task
        task = asyncio.create_task(coro)
        self.active_executions[session_id] = task

        logger.info(f"Started session {session_id} for user {user_id}")
        return task

    async def kill_session(
        self, session_id: str, user_id: str, reason: str = "User requested"
    ) -> bool:
        """Kill a session (user can only kill own sessions).

        Args:
            session_id: Session to kill
            user_id: User requesting kill
            reason: Reason for termination

        Returns:
            True if killed successfully, False if session not found

        Raises:
            PermissionError: If user doesn't own the session
        """
        # Check ownership
        metadata = self._load_session_metadata(session_id)
        if not metadata:
            logger.warning(f"Kill failed: Session {session_id} not found")
            return False

        if metadata.get("user_id") != user_id:
            raise PermissionError(
                f"User {user_id} cannot kill session {session_id} owned by {metadata.get('user_id')}"
            )

        # Kill the session
        return await self._kill_session_internal(session_id, user_id, reason)

    async def admin_kill_session(
        self, session_id: str, admin_user_id: str, reason: str = "Admin terminated"
    ) -> bool:
        """Kill any session (admin only, no ownership check).

        Args:
            session_id: Session to kill
            admin_user_id: Admin user requesting kill
            reason: Reason for termination

        Returns:
            True if killed successfully, False if session not found

        Raises:
            PermissionError: If user is not admin
        """
        if not self.is_admin(admin_user_id):
            raise PermissionError(f"User {admin_user_id} is not an admin")

        return await self._kill_session_internal(session_id, admin_user_id, reason, is_admin=True)

    async def admin_kill_all_sessions(
        self, admin_user_id: str, reason: str = "System maintenance"
    ) -> int:
        """Emergency kill all active sessions (admin only).

        Args:
            admin_user_id: Admin user requesting kill
            reason: Reason for mass termination

        Returns:
            Number of sessions killed

        Raises:
            PermissionError: If user is not admin
        """
        if not self.is_admin(admin_user_id):
            raise PermissionError(f"User {admin_user_id} is not an admin")

        logger.warning(
            f"ADMIN KILL ALL: User {admin_user_id} killing all sessions. Reason: {reason}"
        )

        # Get all active session IDs
        session_ids = list(self.active_executions.keys())

        # Kill each session
        killed_count = 0
        for session_id in session_ids:
            try:
                await self._kill_session_internal(session_id, admin_user_id, reason, is_admin=True)
                killed_count += 1
            except Exception as e:
                logger.error(f"Failed to kill session {session_id}: {e}")

        logger.warning(f"ADMIN KILL ALL: Terminated {killed_count} sessions")
        return killed_count

    async def _kill_session_internal(
        self, session_id: str, killed_by: str, reason: str, is_admin: bool = False
    ) -> bool:
        """Internal method to kill a session.

        Args:
            session_id: Session to kill
            killed_by: User ID who killed the session
            reason: Reason for termination
            is_admin: Whether this is an admin kill

        Returns:
            True if killed successfully, False if session not found
        """
        # Check if session is running
        task = self.active_executions.get(session_id)
        if not task:
            logger.warning(f"Kill failed: Session {session_id} not in active executions")
            return False

        # Cancel the task
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"Session {session_id} task canceled successfully")
        except Exception as e:
            logger.error(f"Error during session {session_id} cancellation: {e}")

        # Remove from active executions
        self.active_executions.pop(session_id, None)

        # Update metadata
        self._save_session_metadata(
            session_id,
            {
                "status": "killed",
                "killed_at": str(time.time()),
                "killed_by": killed_by,
                "kill_reason": reason,
                "admin_kill": str(is_admin),
            },
        )

        # Log termination (audit trail)
        log_msg = f"Session {session_id} killed by {killed_by}"
        if is_admin:
            log_msg += " (ADMIN)"
        log_msg += f". Reason: {reason}"
        logger.warning(log_msg)

        return True

    def _save_session_metadata(self, session_id: str, metadata: dict[str, Any]) -> None:
        """Save session metadata to Redis.

        Args:
            session_id: Session identifier
            metadata: Metadata to save
        """
        # Get existing metadata
        existing = self._load_session_metadata(session_id) or {}

        # Merge with new metadata
        existing.update(metadata)

        # Save to Redis using the manager's metadata methods
        self.redis_manager.save_metadata(session_id, existing)

    def _load_session_metadata(self, session_id: str) -> dict[str, Any] | None:
        """Load session metadata from Redis.

        Args:
            session_id: Session identifier

        Returns:
            Metadata dict or None if not found
        """
        return self.redis_manager.load_metadata(session_id)

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        # Note: signal.signal only works in main thread
        # For async apps, we'll handle this in shutdown() method
        pass

    async def shutdown(self, grace_period: float = 5.0) -> None:
        """Gracefully shutdown all active sessions.

        Args:
            grace_period: Seconds to wait for tasks to finish
        """
        logger.warning(
            f"Shutting down SessionManager. {len(self.active_executions)} active sessions"
        )

        if not self.active_executions:
            return

        # Cancel all tasks
        for session_id, task in self.active_executions.items():
            logger.info(f"Canceling session {session_id}")
            task.cancel()

        # Wait for tasks to finish (with timeout)
        tasks = list(self.active_executions.values())
        try:
            await asyncio.wait_for(
                asyncio.gather(*tasks, return_exceptions=True), timeout=grace_period
            )
        except TimeoutError:
            logger.warning(f"Graceful shutdown timed out after {grace_period}s")

        # Update metadata for all sessions
        for session_id in list(self.active_executions.keys()):
            self._save_session_metadata(
                session_id,
                {
                    "status": "shutdown",
                    "shutdown_at": str(time.time()),
                    "shutdown_reason": "System shutdown",
                },
            )

        self.active_executions.clear()
        logger.warning("SessionManager shutdown complete")


# Global signal handler setup for applications
def setup_shutdown_handlers(session_manager: SessionManager) -> None:
    """Setup SIGTERM and SIGINT handlers for graceful shutdown.

    This should be called from the main thread of your application.

    Args:
        session_manager: SessionManager instance to shutdown
    """

    def handle_shutdown(signum: int, frame: Any) -> None:
        """Signal handler for graceful shutdown."""
        logger.warning(f"Received signal {signum}, initiating graceful shutdown")

        # Get the event loop
        try:
            loop = asyncio.get_event_loop()
            loop.create_task(session_manager.shutdown())
        except RuntimeError:
            # No event loop running, shutdown synchronously
            logger.error("No event loop running, cannot gracefully shutdown")

    # Register signal handlers
    signal.signal(signal.SIGTERM, handle_shutdown)
    signal.signal(signal.SIGINT, handle_shutdown)

    logger.info("Shutdown signal handlers registered (SIGTERM, SIGINT)")
