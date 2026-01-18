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
from datetime import UTC
from typing import Any

from bo1.constants import SessionManagerConfig
from bo1.state.redis_manager import RedisManager
from bo1.state.repositories import session_repository
from bo1.state.repositories.cognition_repository import cognition_repository
from bo1.utils.async_context import create_task_with_context

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

    def __init__(
        self,
        redis_manager: RedisManager,
        admin_user_ids: set[str] | None = None,
        max_concurrent_sessions: int | None = None,
    ) -> None:
        """Initialize session manager.

        Args:
            redis_manager: Redis state manager for metadata persistence
            admin_user_ids: Set of user IDs with admin privileges (optional)
            max_concurrent_sessions: Max concurrent sessions (default from config)
        """
        self.redis_manager = redis_manager
        self.admin_user_ids = admin_user_ids or set()
        self.active_executions: dict[str, asyncio.Task[Any]] = {}
        self._session_start_times: dict[str, float] = {}
        self._capacity_lock = asyncio.Lock()
        self.max_concurrent_sessions = (
            max_concurrent_sessions
            if max_concurrent_sessions is not None
            else SessionManagerConfig.MAX_CONCURRENT_SESSIONS
        )
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

    def get_oldest_session(self) -> str | None:
        """Get the oldest active session by start time.

        Returns:
            Session ID of oldest session or None if no active sessions
        """
        if not self._session_start_times:
            return None
        return min(self._session_start_times, key=self._session_start_times.get)  # type: ignore[arg-type]

    def is_at_capacity(self) -> bool:
        """Check if session manager is at capacity.

        Returns:
            True if at or above max_concurrent_sessions
        """
        return len(self.active_executions) >= self.max_concurrent_sessions

    def get_capacity_info(self) -> dict[str, Any]:
        """Get capacity utilization statistics.

        Returns:
            Dict with current_sessions, max_sessions, utilization_pct, at_capacity
        """
        current = len(self.active_executions)
        max_sessions = self.max_concurrent_sessions
        utilization = (current / max_sessions * 100) if max_sessions > 0 else 0
        return {
            "current_sessions": current,
            "max_sessions": max_sessions,
            "utilization_pct": round(utilization, 1),
            "at_capacity": current >= max_sessions,
        }

    async def _evict_oldest_session(self, reason: str = "capacity_eviction") -> str | None:
        """Evict the oldest session to make room for a new one.

        Sends eviction_warning event before hard-kill after grace period.

        Args:
            reason: Reason for eviction

        Returns:
            Evicted session_id or None if no sessions to evict
        """
        oldest_session_id = self.get_oldest_session()
        if not oldest_session_id:
            return None

        task = self.active_executions.get(oldest_session_id)
        if not task:
            # Session in start_times but not in active_executions - clean up
            self._session_start_times.pop(oldest_session_id, None)
            return None

        # Get user_id for the evicted session
        metadata = self._load_session_metadata(oldest_session_id)
        evicted_user_id = metadata.get("user_id") if metadata else None

        # Emit eviction_warning event
        try:
            if self.redis_manager.redis:
                import json

                warning_event = json.dumps(
                    {
                        "event_type": "eviction_warning",
                        "data": {
                            "reason": reason,
                            "grace_period_seconds": SessionManagerConfig.EVICTION_GRACE_PERIOD_SECONDS,
                            "timestamp": time.time(),
                        },
                    }
                )
                self.redis_manager.redis.publish(
                    f"events:{oldest_session_id}", f"data: {warning_event}\n\n"
                )
        except Exception as e:
            logger.warning(f"Failed to publish eviction_warning (non-critical): {e}")

        # Mark session as evicting
        self._update_session_status(oldest_session_id, "evicting", eviction_reason=reason)

        # Wait grace period
        await asyncio.sleep(SessionManagerConfig.EVICTION_GRACE_PERIOD_SECONDS)

        # Now kill the session
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.info(f"[{oldest_session_id}] Evicted session task canceled")
        except Exception as e:
            logger.error(f"[{oldest_session_id}] Error during eviction cancellation: {e}")

        # Clean up
        self.active_executions.pop(oldest_session_id, None)
        self._session_start_times.pop(oldest_session_id, None)

        # Update final status
        self._update_session_status(
            oldest_session_id,
            "evicted",
            eviction_reason=reason,
            evicted_by="system",
        )

        logger.warning(
            f"[{oldest_session_id}] Session evicted (user={evicted_user_id}). Reason: {reason}"
        )

        return oldest_session_id

    async def start_session(self, session_id: str, user_id: str, coro: Any) -> asyncio.Task[Any]:
        """Start a new deliberation session as background task.

        If at capacity, evicts the oldest session (FIFO) before starting.

        Args:
            session_id: Unique session identifier
            user_id: User who owns this session
            coro: Coroutine to execute (graph.ainvoke())

        Returns:
            Background asyncio.Task
        """
        async with self._capacity_lock:
            # Check capacity and evict if needed
            if self.is_at_capacity():
                capacity_info = self.get_capacity_info()
                logger.warning(
                    f"[{session_id}] At capacity ({capacity_info['current_sessions']}/{capacity_info['max_sessions']}), "
                    "evicting oldest session"
                )
                evicted_id = await self._evict_oldest_session(reason="capacity_eviction")
                if evicted_id:
                    logger.info(f"[{session_id}] Evicted session {evicted_id} to make room")

            # Track start time for FIFO ordering
            self._session_start_times[session_id] = time.time()

            # Log capacity metrics
            capacity_info = self.get_capacity_info()
            logger.info(
                f"[{session_id}] Starting session. Capacity: {capacity_info['current_sessions'] + 1}/"
                f"{capacity_info['max_sessions']} ({capacity_info['utilization_pct']}%)"
            )

        # Store ownership metadata with running status
        self._update_session_status(session_id, "running", user_id=user_id)

        # Wrap coroutine with error handling
        async def wrapped_execution() -> Any:
            try:
                logger.info(f"[{session_id}] Starting graph execution...")
                result = await coro
                logger.info(f"[{session_id}] Graph execution completed successfully")

                # Validate graph produced synthesis before marking completed
                state = result if isinstance(result, dict) else {}
                has_synthesis = bool(state.get("synthesis"))
                has_sub_problem_results = bool(state.get("sub_problem_results"))
                pending_clarification = bool(state.get("pending_clarification"))

                if not has_synthesis and not has_sub_problem_results and not pending_clarification:
                    # Graph exited early without producing synthesis
                    logger.error(
                        f"[{session_id}] Graph completed without synthesis - marking as failed. "
                        f"Last node: {state.get('current_node', 'unknown')}"
                    )
                    self._update_session_status(
                        session_id,
                        "failed",
                        error="Meeting completed without generating synthesis. Please retry.",
                    )
                    return result

                # ISS-002 FIX: Don't mark as completed if paused for clarification
                # _handle_identify_gaps already set status=paused, phase=clarification_needed
                stop_reason = state.get("stop_reason")
                if pending_clarification or stop_reason == "clarification_needed":
                    logger.info(
                        f"[{session_id}] Graph paused for clarification - "
                        f"keeping paused status (stop_reason={stop_reason})"
                    )
                    return result  # Early return - don't overwrite paused status

                # Update metadata on successful completion
                self._update_session_status(session_id, "completed")

                # Track meeting completion for cognitive profile
                completed_user_id = state.get("user_id")
                if completed_user_id:
                    try:
                        # Increment meeting count for tier unlock
                        cognition_repository.increment_meeting_count(completed_user_id)
                        logger.info(
                            f"[{session_id}] Incremented meeting count for user {completed_user_id[:8]}..."
                        )

                        # Track behavioral metrics
                        session_data = session_repository.get(session_id)
                        if session_data and session_data.get("created_at"):
                            from datetime import datetime

                            created_at = session_data["created_at"]
                            if isinstance(created_at, str):
                                created_at = datetime.fromisoformat(
                                    created_at.replace("Z", "+00:00")
                                )
                            duration_seconds = int((datetime.now(UTC) - created_at).total_seconds())

                            # Get round count and clarification info from state
                            rounds_count = state.get("round_number", 1)
                            clarification_answers = state.get("clarification_answers") or {}
                            skip_clarification = state.get("skip_clarification", False)

                            # Estimate clarifications: if answers exist, they were asked
                            clarifications_asked = len(clarification_answers)
                            # If skip_clarification was set and no answers, count as skipped
                            clarifications_skipped = (
                                1 if skip_clarification and not clarification_answers else 0
                            )

                            cognition_repository.track_meeting_completion(
                                user_id=completed_user_id,
                                duration_seconds=duration_seconds,
                                rounds_count=rounds_count,
                                clarifications_asked=clarifications_asked,
                                clarifications_skipped=clarifications_skipped,
                            )
                    except Exception as cog_err:
                        logger.warning(
                            f"[{session_id}] Failed to track cognitive metrics: {cog_err}"
                        )

                return result
            except asyncio.CancelledError:
                logger.info(f"[{session_id}] Graph execution was cancelled")
                raise
            except Exception as e:
                error_msg = str(e)
                error_type = type(e).__name__
                logger.error(f"[{session_id}] Graph execution failed: {e}", exc_info=True)

                # Emit error event for UI display and PostgreSQL logging
                try:
                    # Get next sequence number for this session's events
                    # Error events use sequence 9999 as they're terminal and don't need ordering
                    session_repository.save_event(
                        session_id=session_id,
                        event_type="error",
                        sequence=9999,  # Special sequence for terminal error events
                        data={
                            "error": error_msg,
                            "error_type": error_type,
                            "recoverable": False,  # Graph-level failures are not recoverable
                            "timestamp": time.time(),
                        },
                    )
                    logger.info(f"[{session_id}] Saved error event to database")

                    # Also publish to Redis for real-time UI update
                    if self.redis_manager.redis:
                        try:
                            self.redis_manager.redis.publish(
                                f"events:{session_id}",
                                f"data: {{'event_type': 'error', 'data': {{'error': '{error_msg}', 'error_type': '{error_type}', 'recoverable': false}}}}\n\n",
                            )
                        except Exception as redis_err:
                            logger.warning(
                                f"Failed to publish error to Redis (non-critical): {redis_err}"
                            )
                except Exception as event_err:
                    logger.error(
                        f"Failed to save error event (non-critical): {event_err}",
                        exc_info=True,
                    )

                # Update metadata on failure
                self._update_session_status(session_id, "failed", error=error_msg)
                raise
            finally:
                # Remove from active executions and start times
                self.active_executions.pop(session_id, None)
                self._session_start_times.pop(session_id, None)
                logger.info(f"[{session_id}] Removed from active executions")

        # Create background task with context (preserves correlation_id)
        task = create_task_with_context(wrapped_execution())
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
        self._update_session_status(
            session_id,
            "killed",
            killed_by=killed_by,
            kill_reason=reason,
            admin_kill=str(is_admin),
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

    def _update_session_status(self, session_id: str, status: str, **extra_fields: Any) -> None:
        """Update session status with timestamp and optional extra fields.

        Convenience method to update session status with automatic timestamping.
        Consolidates the repeated pattern of updating metadata with status + timestamp.

        When status is terminal (completed, failed, killed), schedules Redis cleanup
        after a grace period to ensure completed meetings are read from Postgres.

        Args:
            session_id: Session identifier
            status: New status (e.g., "running", "completed", "failed", "killed")
            **extra_fields: Additional fields to update (e.g., error="...", killed_by="...")

        Examples:
            >>> self._update_session_status(session_id, "completed")
            >>> self._update_session_status(session_id, "failed", error=str(e))
            >>> self._update_session_status(session_id, "killed", killed_by=user_id, kill_reason=reason)
        """
        # Build metadata dict with status and appropriate timestamp
        metadata: dict[str, Any] = {"status": status}

        # Add timestamp field based on status
        # Special case: "running" status uses "started_at" for backward compatibility
        if status == "running":
            timestamp_field = "started_at"
        else:
            timestamp_field = f"{status}_at"

        metadata[timestamp_field] = str(time.time())

        # Add any extra fields
        metadata.update(extra_fields)

        self._save_session_metadata(session_id, metadata)

        # Sync status to PostgreSQL to prevent Redis/PostgreSQL desync
        # This ensures SSE endpoint sees consistent status regardless of which store it checks
        try:
            session_repository.update_status(session_id=session_id, status=status)
        except Exception as e:
            # Log but don't fail - Redis is primary for live sessions
            logger.warning(f"[{session_id}] Failed to sync status '{status}' to PostgreSQL: {e}")

        # Schedule Redis cleanup for terminal states
        # This ensures completed meetings are read from Postgres after grace period
        terminal_states = {"completed", "failed", "killed"}
        if status in terminal_states:
            user_id = extra_fields.get("user_id")
            # If no user_id in extra_fields, try to get from existing metadata
            if not user_id:
                existing_meta = self._load_session_metadata(session_id)
                user_id = existing_meta.get("user_id") if existing_meta else None
            self.redis_manager.schedule_cleanup(session_id, user_id)

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


def is_safe_resume_boundary(state: dict[str, Any]) -> bool:
    """Check if state is at a safe checkpoint boundary for resume.

    Safe boundaries (resume-safe):
    - At start (no contributions yet)
    - Between sub-problems (synthesis complete, moving to next SP)
    - At synthesis (all rounds complete)

    Unsafe boundaries (mid-execution):
    - Mid-round execution: has in-flight contributions without round completion
    - Partial contributions for current round
    - Pending clarification awaiting user response

    Args:
        state: Checkpoint state dict

    Returns:
        True if safe to resume from this state
    """
    contributions = state.get("contributions", [])
    round_number = state.get("round_number", 0)
    current_node = state.get("current_node", "")
    pending_clarification = state.get("pending_clarification")
    sub_problem_results = state.get("sub_problem_results", [])
    sub_problem_index = state.get("sub_problem_index", 0)

    # Pending clarification - unsafe (waiting for user input)
    # Check this first as it can occur at any point
    if pending_clarification:
        logger.debug(f"Unsafe boundary: pending_clarification={pending_clarification}")
        return False

    # At start (no contributions yet) - safe
    if not contributions and round_number == 0:
        return True

    # Between sub-problems (synthesis complete, moving to next SP) - safe
    # sub_problem_results has completed SPs, sub_problem_index is next SP
    if len(sub_problem_results) > 0 and sub_problem_index == len(sub_problem_results):
        return True

    # At synthesis node - safe
    if current_node in ("synthesis", "final_synthesis"):
        return True

    # Check for partial round contributions
    # Get contribution count for current round
    current_round_contributions = [c for c in contributions if _get_round(c) == round_number]
    personas = state.get("personas", [])

    # If we have some contributions for current round but not all, unsafe
    if current_round_contributions and len(current_round_contributions) < len(personas):
        logger.debug(
            f"Unsafe boundary: partial round ({len(current_round_contributions)}/{len(personas)} contributions)"
        )
        return False

    # At round boundary (all contributions for round received) - safe
    return True


def _get_round(contribution: Any) -> int:
    """Extract round_number from contribution (dict or Pydantic)."""
    if isinstance(contribution, dict):
        return int(contribution.get("round_number", 0))
    return int(getattr(contribution, "round_number", 0))


def _validate_checkpoint_state(state: dict[str, Any], session_id: str) -> list[str]:
    """Validate restored state fields for corruption detection.

    Checks critical fields required for deliberation to continue:
    - problem: must exist with sub_problems list
    - personas: must be a non-empty list
    - contributions: must be a list (can be empty)
    - phase: must be a valid phase value

    Args:
        state: Restored checkpoint state
        session_id: For logging context

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Validate problem
    problem = state.get("problem")
    if not problem:
        errors.append("Missing problem field")
    else:
        if isinstance(problem, dict):
            sub_problems = problem.get("sub_problems", [])
        else:
            sub_problems = getattr(problem, "sub_problems", []) or []
        if not sub_problems:
            errors.append("Problem has no sub_problems")

    # Validate personas
    personas = state.get("personas")
    if personas is None:
        errors.append("Missing personas field")
    elif not isinstance(personas, list):
        errors.append(f"Invalid personas type: {type(personas)}")
    elif len(personas) == 0 and state.get("round_number", 0) > 0:
        # Personas can be empty only before selection (round 0)
        errors.append("Empty personas list after round 0")

    # Validate contributions
    contributions = state.get("contributions")
    if contributions is not None and not isinstance(contributions, list):
        errors.append(f"Invalid contributions type: {type(contributions)}")

    # Validate phase
    phase = state.get("phase")
    if phase is None:
        errors.append("Missing phase field")

    if errors:
        logger.warning(
            f"Checkpoint validation failed for {session_id}: {errors}",
            extra={"session_id": session_id, "errors": errors},
        )

    return errors


async def resume_session_from_checkpoint(
    session_id: str,
    graph: Any,
    config: dict[str, Any],
    db_fallback: bool = True,
) -> tuple[dict[str, Any] | None, bool]:
    """Load and prepare state from checkpoint for resuming a failed session.

    This function loads the last checkpoint for a session and prepares
    the state for resumption by:
    1. Loading state via graph.aget_state() (Redis checkpoint)
    2. On Redis failure: fallback to PostgreSQL event reconstruction
    3. Validating restored state fields
    4. Checking for safe resume boundary
    5. Resetting should_stop and stop_reason flags
    6. Clearing any error state

    Args:
        session_id: Session identifier
        graph: LangGraph graph instance with checkpointer
        config: Graph config with thread_id
        db_fallback: Whether to attempt PostgreSQL fallback on Redis failure

    Returns:
        Tuple of (state dict or None, is_fallback_resume bool)
        - state: Prepared state dict ready for graph resumption, or None if unrecoverable
        - is_fallback_resume: True if state was reconstructed from PostgreSQL
    """
    from bo1.logging.errors import ErrorCode, log_error

    is_fallback = False

    try:
        # Load state from checkpoint
        checkpoint_state = await graph.aget_state(config)

        if not checkpoint_state or not checkpoint_state.values:
            logger.warning(f"No checkpoint found for session {session_id}")
            # Attempt PostgreSQL fallback
            if db_fallback:
                state = await _reconstruct_state_from_postgres(session_id)
                if state:
                    is_fallback = True
                else:
                    return None, False
            else:
                return None, False
        else:
            state = dict(checkpoint_state.values)

    except Exception as e:
        log_error(
            logger,
            ErrorCode.GRAPH_CHECKPOINT_ERROR,
            f"Failed to load checkpoint from Redis for {session_id}: {e}",
            session_id=session_id,
        )

        # Attempt PostgreSQL fallback
        if db_fallback:
            state = await _reconstruct_state_from_postgres(session_id)
            if state:
                is_fallback = True
            else:
                return None, False
        else:
            return None, False

    # Validate state fields
    validation_errors = _validate_checkpoint_state(state, session_id)
    if validation_errors:
        log_error(
            logger,
            ErrorCode.GRAPH_STATE_ERROR,
            f"Corrupted checkpoint for {session_id}: {validation_errors}",
            session_id=session_id,
            validation_errors=validation_errors,
        )
        return None, is_fallback

    # Check for safe resume boundary
    if not is_safe_resume_boundary(state):
        logger.warning(
            f"Checkpoint for {session_id} not at safe resume boundary",
            extra={"session_id": session_id, "current_node": state.get("current_node")},
        )
        # Note: we still allow resume but log warning - caller can decide policy

    # Extract sub_problems count for logging
    problem = state.get("problem")
    if problem:
        if isinstance(problem, dict):
            sub_problems = problem.get("sub_problems", [])
        else:
            sub_problems = getattr(problem, "sub_problems", []) or []
        sub_problems_count = len(sub_problems) if sub_problems else 0
    else:
        sub_problems_count = 0

    logger.info(
        f"Loaded checkpoint for {session_id}: "
        f"problem={bool(problem)}, sub_problems={sub_problems_count}, fallback={is_fallback}"
    )

    # Reset stop flags so graph continues execution
    state["should_stop"] = False
    state["stop_reason"] = None

    # Clear any pending clarification state (we're retrying, not answering)
    state["pending_clarification"] = None

    # Mark if this was a fallback resume
    state["is_fallback_resume"] = is_fallback

    logger.debug(f"Prepared state for resume from checkpoint for session {session_id}")
    return state, is_fallback


async def publish_resume_failed_event(
    session_id: str,
    error_code: str,
    message: str,
) -> None:
    """Publish resume_failed event for frontend notification.

    Called when checkpoint resume fails and recovery is not possible.
    Allows frontend to display user-friendly error and suggest next steps.

    Args:
        session_id: Session identifier
        error_code: Machine-readable error code (e.g., GRAPH_RESUME_FAILED)
        message: User-friendly error message
    """
    try:
        from bo1.state.redis_manager import RedisManager

        redis_mgr = RedisManager()
        if redis_mgr.client is None:
            logger.warning(f"No Redis client available to publish resume_failed for {session_id}")
            return

        from backend.api.event_publisher import EventPublisher

        publisher = EventPublisher(redis_client=redis_mgr.client)
        publisher.publish_event(
            session_id,
            "resume_failed",
            {
                "session_id": session_id,
                "error_code": error_code,
                "message": message,
                "recoverable": False,
            },
        )
        logger.info(f"Published resume_failed event for session {session_id}")
    except Exception as e:
        logger.warning(f"Failed to publish resume_failed event for {session_id}: {e}")


async def _reconstruct_state_from_postgres(session_id: str) -> dict[str, Any] | None:
    """Reconstruct state from PostgreSQL when Redis checkpoint unavailable.

    Loads session metadata and replays events to rebuild state.
    Only reconstructs fields that are persisted in PostgreSQL:
    - Basic metadata (phase, round_number)
    - Contributions (from session_events)
    - Synthesis (if complete)

    Limited reconstruction - some state may be lost:
    - Detailed persona state
    - Research results
    - Semantic scores

    Args:
        session_id: Session identifier

    Returns:
        Reconstructed state dict or None if insufficient data
    """
    from bo1.logging.errors import ErrorCode, log_error
    from bo1.state.repositories.session_repository import SessionRepository

    try:
        repo = SessionRepository()

        # Get session metadata
        session = repo.get(session_id)
        if not session:
            logger.warning(f"No session found in PostgreSQL for {session_id}")
            return None

        # Get events for reconstruction
        events = repo.get_events(session_id)
        if not events:
            logger.warning(f"No events found in PostgreSQL for {session_id}")
            return None

        # Initialize state from session metadata
        state: dict[str, Any] = {
            "session_id": session_id,
            "phase": session.get("phase", "intake"),
            "round_number": session.get("round_number", 0),
            "max_rounds": 6,  # Default parallel architecture
            "should_stop": False,
            "stop_reason": None,
            "contributions": [],
            "personas": [],
            "sub_problem_results": [],
            "sub_problem_index": session.get("problem_context", {}).get("sub_problem_index", 0),
        }

        # Replay events to rebuild contributions
        contributions = []
        for event in events:
            event_type = event.get("event_type")
            data = event.get("data", {})

            if event_type == "contribution":
                contributions.append(data)
            elif event_type == "synthesis_complete":
                state["synthesis"] = data.get("synthesis")
            elif event_type == "persona_selected":
                # Reconstruct basic persona info
                if data.get("personas"):
                    state["personas"] = data["personas"]

        state["contributions"] = contributions

        # Check if we have minimum required data
        if not state.get("personas") and state.get("round_number", 0) > 0:
            logger.warning(
                f"Insufficient data for reconstruction: no personas after round 0 for {session_id}"
            )
            return None

        logger.info(
            f"Reconstructed state from PostgreSQL for {session_id}: "
            f"contributions={len(contributions)}, phase={state.get('phase')}"
        )
        return state

    except Exception as e:
        log_error(
            logger,
            ErrorCode.DB_QUERY_ERROR,
            f"Failed to reconstruct state from PostgreSQL for {session_id}: {e}",
            session_id=session_id,
            exc_info=True,
        )
        return None


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
