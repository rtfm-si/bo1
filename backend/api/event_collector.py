"""Event collector that wraps LangGraph astream_events and publishes to Redis.

Provides:
- EventCollector: Wraps graph execution and publishes all events to Redis PubSub
"""

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any, Literal

from backend.api.constants import (
    GRAPH_HARD_TIMEOUT_SECONDS,
    GRAPH_LIVENESS_TIMEOUT_SECONDS,
    MEANINGFUL_PROGRESS_EVENTS,
)
from backend.api.dependencies import get_redis_manager, get_session_metadata_cache
from backend.api.event_extractors import extract_persona_dict, get_event_registry
from backend.api.event_publisher import EventPublisher, flush_session_events
from backend.api.middleware.metrics import record_graph_execution_timeout
from backend.services.event_batcher import flush_batcher, wait_for_all_flushes
from bo1.context import set_request_id
from bo1.llm.cost_tracker import CostTracker
from bo1.logging.errors import ErrorCode, log_error
from bo1.state.circuit_breaker_wrappers import is_redis_circuit_open
from bo1.state.repositories.session_repository import extract_session_metadata
from bo1.utils.async_context import create_task_with_context

if TYPE_CHECKING:
    from backend.api.contribution_summarizer import ContributionSummarizer
    from backend.api.protocols import SessionRepositoryProtocol

logger = logging.getLogger(__name__)


def _get_sub_problem_index_safe(output: dict[str, Any], context: str) -> int:
    """Get sub_problem_index with warning if missing.

    Logs a warning when sub_problem_index is missing from node output to help
    identify upstream nodes that don't propagate the index correctly.

    Args:
        output: Node output dictionary
        context: Description of where this is called from (for debugging)

    Returns:
        sub_problem_index value, defaulting to 0 if missing
    """
    if "sub_problem_index" not in output:
        logger.warning(
            "[EVENT WARN] sub_problem_index missing in %s. Defaulting to 0. Keys: %s",
            context,
            list(output.keys())[:10],
        )
        return 0
    return output["sub_problem_index"]


# Type-safe node name literal for graph nodes
NodeName = Literal[
    "decompose",
    "identify_gaps",
    "select_personas",
    "initial_round",
    "facilitator_decide",
    "parallel_round",
    "moderator_intervene",
    "check_convergence",
    "vote",
    "synthesize",
    "next_subproblem",
    "meta_synthesis",
    "meta_synthesize",
    "research",
    "context_collection",
    "analyze_dependencies",
    "data_analysis",
    "cost_guard",
    "clarification",
    "parallel_subproblems",
]


class EventCollector:
    """Collects LangGraph events and publishes them to Redis for SSE streaming.

    This class wraps LangGraph's astream_events() iterator and maps node
    completions to specific event types, publishing them to Redis PubSub
    for real-time streaming to web clients.

    Examples:
        >>> from backend.api.dependencies import get_contribution_summarizer, get_event_publisher
        >>> from bo1.graph.config import create_deliberation_graph
        >>> collector = EventCollector(get_event_publisher(), get_contribution_summarizer())
        >>> final_state = await collector.collect_and_publish(
        ...     session_id="bo1_abc123",
        ...     graph=graph,
        ...     initial_state=state,
        ...     config=config
        ... )
    """

    # Node handler registry: maps node names to handler method names
    # Type-safe: keys must be valid NodeName values
    NODE_HANDLERS: dict[NodeName, str] = {
        "decompose": "_handle_decomposition",
        "identify_gaps": "_handle_identify_gaps",
        "select_personas": "_handle_persona_selection",
        "select_personas_sp_node": "_handle_persona_selection",  # Sub-problem persona selection
        "initial_round": "_handle_initial_round",
        "facilitator_decide": "_handle_facilitator_decision",
        "parallel_round": "_handle_parallel_round",
        "parallel_round_sp_node": "_handle_parallel_round",  # Sub-problem parallel round
        "moderator_intervene": "_handle_moderator",
        "check_convergence": "_handle_convergence",
        "check_convergence_sp_node": "_handle_convergence",  # Sub-problem convergence
        "vote": "_handle_voting",
        "vote_sp_node": "_handle_voting",  # Sub-problem voting
        "synthesize": "_handle_synthesis",
        "synthesize_sp_node": "_handle_synthesis",  # Sub-problem synthesis
        "next_subproblem": "_handle_subproblem_complete",
        "meta_synthesis": "_handle_meta_synthesis",
        "meta_synthesize": "_handle_meta_synthesis",  # Support both node names
        "research": "_handle_research",  # P2-006: Research results
        "context_collection": "_handle_context_collection",  # P1: UI feedback
        "analyze_dependencies": "_handle_dependency_analysis",  # P1: UI feedback
        "data_analysis": "_handle_data_analysis",  # EPIC 4: Dataset analysis
        "cost_guard": "_handle_cost_guard",  # Cost limit enforcement
        "clarification": "_handle_clarification",  # User clarification requests
        "parallel_subproblems": "_handle_parallel_subproblems",  # Parallel sub-problem execution
    }

    # Mapping of node names to working_status messages emitted at START
    NODE_START_STATUS: dict[str, str] = {
        "decompose": "Breaking down your decision into key areas...",
        "select_personas": "Assembling the right experts for your question...",
        "initial_round": "Experts are sharing their initial perspectives...",
        "facilitator_decide": "Guiding the discussion deeper...",
        "parallel_round": "Experts are discussing...",
        "moderator_intervene": "Ensuring balanced perspectives...",
        "check_convergence": "Checking for emerging agreement...",
        "vote": "Experts are finalizing their recommendations...",
        "synthesize": "Bringing together the key insights...",
        "meta_synthesis": "Crafting your final recommendation...",
        "meta_synthesize": "Crafting your final recommendation...",
    }

    def __init__(
        self,
        publisher: EventPublisher,
        summarizer: "ContributionSummarizer",
        session_repo: "SessionRepositoryProtocol",
    ) -> None:
        """Initialize EventCollector.

        Args:
            publisher: EventPublisher instance for publishing to Redis
            summarizer: ContributionSummarizer for AI-powered summaries
            session_repo: Session repository for state persistence
        """
        self.publisher = publisher
        self.summarizer = summarizer
        self.session_repo = session_repo
        self._previous_node: str | None = None
        self._redis_fallback_emitted: bool = False  # Track if fallback event already sent

    def _save_metadata_fallback(
        self,
        session_id: str,
        state: dict[str, Any],
    ) -> None:
        """Save session metadata to PostgreSQL when Redis circuit breaker is open.

        Called after each node completion when Redis is unavailable. Extracts
        persistable fields from graph state and writes to sessions table.

        Args:
            session_id: Session identifier
            state: Current graph state dict
        """
        if not is_redis_circuit_open():
            return  # Redis is available, no fallback needed

        try:
            # Extract metadata from state
            metadata = extract_session_metadata(state)

            if not metadata:
                return  # No metadata to persist

            # Save to PostgreSQL
            success = self.session_repo.save_metadata(session_id, metadata)

            if success:
                logger.info(
                    f"[REDIS_FALLBACK] Persisted metadata to PostgreSQL for {session_id}: "
                    f"phase={metadata.get('phase')}, round={metadata.get('round_number')}"
                )

                # Emit redis_fallback_activated event (once per session)
                if not self._redis_fallback_emitted:
                    self._redis_fallback_emitted = True
                    try:
                        # Direct PostgreSQL event persistence (Redis unavailable)
                        from bo1.state.repositories import session_repository

                        session_repository.save_event(
                            session_id=session_id,
                            event_type="redis_fallback_activated",
                            sequence=0,  # Special sequence for system events
                            data={
                                "message": "Redis unavailable - using PostgreSQL fallback",
                                "fields_persisted": list(metadata.keys()),
                            },
                        )
                    except Exception as event_err:
                        logger.warning(f"Failed to save fallback event: {event_err}")
            else:
                logger.warning(f"[REDIS_FALLBACK] Failed to persist metadata for {session_id}")

        except Exception as e:
            log_error(
                logger,
                ErrorCode.DB_WRITE_ERROR,
                f"[REDIS_FALLBACK] Error persisting metadata for {session_id}: {e}",
                session_id=session_id,
            )

    def _emit_working_status(
        self,
        session_id: str,
        phase: str,
        sub_problem_index: int = 0,
    ) -> None:
        """Emit a working_status event to indicate ongoing processing.

        Helper method to eliminate duplication of working status event emission.
        Used before long-running operations (voting, synthesis, rounds) to provide
        user feedback that the system is actively processing.

        Args:
            session_id: Session identifier
            phase: Human-readable description of current phase (e.g., "Experts finalizing recommendations...")
            sub_problem_index: Sub-problem index for tab filtering (default: 0)
        """
        self.publisher.publish_event(
            session_id,
            "working_status",
            {
                "phase": phase,
                "sub_problem_index": sub_problem_index,
            },
        )

    def _emit_quality_status(
        self,
        session_id: str,
        status: str,
        message: str,
        round_number: int,
        sub_problem_index: int = 0,
    ) -> None:
        """Emit a discussion_quality_status event for quality tracking.

        Helper method to eliminate duplication of quality status event emission.
        Used to indicate quality analysis phases (analyzing, selecting, gathering).

        Args:
            session_id: Session identifier
            status: Status type (e.g., "analyzing", "selecting", "gathering")
            message: Human-readable status message
            round_number: Current round number
            sub_problem_index: Sub-problem index for tab filtering (default: 0)
        """
        self.publisher.publish_event(
            session_id,
            "discussion_quality_status",
            {
                "status": status,
                "message": message,
                "round": round_number,
                "sub_problem_index": sub_problem_index,
            },
        )

    def _emit_state_transition(
        self,
        session_id: str,
        to_node: str,
        sub_problem_index: int = 0,
    ) -> None:
        """Emit a state_transition event for progress visualization.

        Tracks transitions between graph nodes for client-side progress UI.
        Emits from_node (previous node, None for first) and to_node.

        Args:
            session_id: Session identifier
            to_node: Name of the node transitioning to
            sub_problem_index: Sub-problem index for tab filtering (default: 0)
        """
        self.publisher.publish_event(
            session_id,
            "state_transition",
            {
                "from_node": self._previous_node,
                "to_node": to_node,
                "sub_problem_index": sub_problem_index,
            },
        )
        self._previous_node = to_node

    def _map_error_type_to_code(
        self,
        error: Exception,
        error_type: str,
        timeout_exceeded: bool,
    ) -> str:
        """Map exception type to ErrorCode for frontend-specific messaging.

        Args:
            error: The exception instance
            error_type: The exception class name (e.g., "APIError", "RateLimitError")
            timeout_exceeded: Whether this was a timeout failure

        Returns:
            ErrorCode value string for frontend consumption
        """
        if timeout_exceeded:
            return ErrorCode.LLM_TIMEOUT.value

        # Map common error types to ErrorCode values
        error_message = str(error).lower()
        error_type_lower = error_type.lower()

        # LLM-specific errors
        if "rate" in error_message or "ratelimit" in error_type_lower:
            return ErrorCode.LLM_RATE_LIMIT.value
        if "circuit" in error_message or "circuit" in error_type_lower:
            return ErrorCode.LLM_CIRCUIT_OPEN.value
        if "retry" in error_message and "exhaust" in error_message:
            return ErrorCode.LLM_RETRIES_EXHAUSTED.value
        if "timeout" in error_message or "timeout" in error_type_lower:
            return ErrorCode.LLM_TIMEOUT.value
        if "embedding" in error_message:
            return ErrorCode.LLM_EMBEDDING_FAILED.value
        if "parse" in error_message or "json" in error_message:
            return ErrorCode.LLM_PARSE_FAILED.value
        if any(x in error_type_lower for x in ["llm", "anthropic", "openai", "api"]):
            return ErrorCode.LLM_API_ERROR.value

        # Database errors
        if "database" in error_message or "postgres" in error_message or "sql" in error_message:
            return ErrorCode.DB_QUERY_ERROR.value

        # Redis errors
        if "redis" in error_message:
            return ErrorCode.REDIS_CONNECTION_ERROR.value

        # Service errors
        if "service" in error_message and "unavailable" in error_message:
            return ErrorCode.SERVICE_UNAVAILABLE.value

        # Default to generic service execution error
        return ErrorCode.SERVICE_EXECUTION_ERROR.value

    def _mark_session_failed(
        self,
        session_id: str,
        error: Exception,
        timeout_exceeded: bool = False,
        elapsed_seconds: float | None = None,
    ) -> None:
        """Mark session as failed with error handling.

        Consolidates duplicate error handling pattern for session failures.
        Publishes error event, updates session status, and sends notification email.

        Args:
            session_id: Session identifier
            error: The exception that caused the failure
            timeout_exceeded: Whether failure was due to wall-clock timeout
            elapsed_seconds: Time elapsed before timeout (only set if timeout_exceeded=True)
        """
        # Flush any pending cost records before marking failed
        try:
            CostTracker.flush(session_id)
        except Exception as flush_error:
            logger.warning(f"Failed to flush cost buffer on session failure: {flush_error}")

        error_type = type(error).__name__

        # For timeout failures, emit specific timeout event first
        if timeout_exceeded:
            self.publisher.publish_event(
                session_id,
                "session_timeout",
                {
                    "elapsed_seconds": elapsed_seconds or 0,
                    "timeout_threshold_seconds": GRAPH_HARD_TIMEOUT_SECONDS,
                    "reason": "Wall-clock timeout exceeded - session took too long",
                },
            )
            # Record timeout metric
            session_data = self.session_repo.get(session_id)
            session_type = (
                session_data.get("session_type", "standard") if session_data else "standard"
            )
            record_graph_execution_timeout(session_type)
            logger.warning(
                f"Session {session_id} timed out after {elapsed_seconds:.1f}s "
                f"(threshold: {GRAPH_HARD_TIMEOUT_SECONDS}s)"
            )

        # Publish error event to SSE stream
        # Map error type to ErrorCode for frontend-specific messaging
        error_code = self._map_error_type_to_code(error, error_type, timeout_exceeded)
        error_data: dict[str, Any] = {
            "error": str(error),
            "error_type": error_type,
            "error_code": error_code,
        }
        if timeout_exceeded:
            error_data["timeout_exceeded"] = True
            error_data["elapsed_seconds"] = elapsed_seconds
        self.publisher.publish_event(session_id, "error", error_data)

        # Update session status to 'failed' in PostgreSQL
        # Note: timeout metadata is already included in the error event above
        try:
            self.session_repo.update_status(
                session_id=session_id,
                status="failed",
            )
            # Invalidate cached metadata on status change
            get_session_metadata_cache().invalidate(session_id)
        except Exception as db_error:
            log_error(
                logger,
                ErrorCode.DB_WRITE_ERROR,
                f"Failed to update session {session_id} status to failed: {db_error}",
                session_id=session_id,
            )

        # Send failure notification email (non-blocking)
        try:
            session_data = self.session_repo.get(session_id)
            if session_data:
                from backend.services.email import send_meeting_failed_email

                send_meeting_failed_email(
                    user_id=session_data.get("user_id", ""),
                    session_id=session_id,
                    problem_statement=session_data.get("problem_statement", ""),
                    error_type="timeout" if timeout_exceeded else error_type,
                )
        except Exception as email_error:
            logger.warning(f"Failed to send meeting failed email: {email_error}")

    async def _publish_node_event(
        self,
        session_id: str,
        output: dict[str, Any],
        event_type: str,
        registry_key: str | None = None,
    ) -> None:
        """Generic event publisher using event extractor registry.

        Args:
            session_id: Session identifier
            output: Raw node output dictionary
            event_type: Event type for SSE (e.g., 'decomposition_complete')
            registry_key: Key to look up in event registry (defaults to event_type with suffixes removed)

        Note:
            This method uses the EventExtractorRegistry to look up the appropriate
            extractor configuration. If registry_key is not provided, it derives the
            key from event_type by removing common suffixes (_complete, _started, etc.)
        """
        try:
            # Derive registry key from event_type if not provided
            if registry_key is None:
                # Strip common suffixes to get base event type
                registry_key = event_type.replace("_complete", "").replace("_started", "")

            # Get registry and extract data
            registry = get_event_registry()
            data = registry.extract(registry_key, output)

            if data:  # Only publish if extractor returned data
                # Add sub_problem_index from state to event data
                # This is CRITICAL for frontend tab filtering (meeting page line 872)
                # Without this field, events don't appear in sub-problem tabs
                sub_problem_index = _get_sub_problem_index_safe(
                    output, f"_publish_via_registry:{event_type}"
                )
                data["sub_problem_index"] = sub_problem_index

                logger.info(
                    f"[EVENT DEBUG] Publishing {event_type} | sub_problem_index={sub_problem_index} | data keys: {list(data.keys())}"
                )
                self.publisher.publish_event(session_id, event_type, data)
            else:
                # Issue #3 fix: Publish error event when extractor fails
                error_msg = f"Event extraction failed for {event_type}"
                log_error(
                    logger,
                    ErrorCode.GRAPH_EXECUTION_ERROR,
                    f"[EVENT ERROR] {error_msg} (registry_key={registry_key}). Output keys: {list(output.keys())}",
                    session_id=session_id,
                    event_type=event_type,
                    registry_key=registry_key,
                )
                # Publish error event so UI knows something went wrong
                self.publisher.publish_event(
                    session_id,
                    "error",
                    {
                        "error": error_msg,
                        "error_type": "EventExtractionError",
                        "event_type_attempted": event_type,
                        "sub_problem_index": _get_sub_problem_index_safe(
                            output, f"_publish_via_registry:error:{event_type}"
                        ),
                    },
                )
        except Exception as e:
            # Issue #3 fix: Publish error event instead of swallowing the error
            log_error(
                logger,
                ErrorCode.API_SSE_ERROR,
                f"Failed to publish {event_type} for session {session_id}: {e}",
                exc_info=True,
                session_id=session_id,
                event_type=event_type,
            )
            # Publish error event so frontend can display the failure
            self.publisher.publish_event(
                session_id,
                "error",
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "event_type_attempted": event_type,
                    "sub_problem_index": _get_sub_problem_index_safe(
                        output, f"_publish_via_registry:exception:{event_type}"
                    ),
                },
            )

    async def _dispatch_node_handler(
        self,
        node_name: str,
        session_id: str,
        node_data: dict[str, Any],
    ) -> bool:
        """Dispatch node completion to the appropriate handler method.

        Args:
            node_name: Name of the completed node
            session_id: Session identifier
            node_data: Node output data

        Returns:
            True if handler was found and called, False if no handler exists

        Note:
            This method looks up the handler in NODE_HANDLERS registry and
            calls it via getattr. If no handler exists for the node, it logs
            and returns False gracefully (not all nodes need handlers).
        """
        handler_name = self.NODE_HANDLERS.get(node_name)

        # DEBUG: Log dispatch attempts
        logger.info(f"[DISPATCH DEBUG] node_name={node_name} | handler_name={handler_name}")

        if handler_name:
            # Get the handler method from this instance
            handler = getattr(self, handler_name, None)
            if handler and callable(handler):
                await handler(session_id, node_data)
                return True
            else:
                logger.warning(
                    f"Handler '{handler_name}' not found for node '{node_name}' "
                    f"(registered but method missing)"
                )
                return False
        else:
            # Not all nodes need handlers - this is expected
            logger.debug(f"No handler registered for node '{node_name}' (skipping)")
            return False

    async def collect_and_publish(
        self,
        session_id: str,
        graph: Any,  # CompiledStateGraph
        initial_state: Any,  # DeliberationGraphState | None
        config: dict[str, Any],
        request_id: str | None = None,
    ) -> Any:  # Final DeliberationGraphState
        """Execute graph and publish all events to Redis.

        This method wraps LangGraph's astream_events() and intercepts
        node completions to publish events to Redis PubSub.

        When USE_SUBGRAPH_DELIBERATION is enabled, uses astream() with
        stream_mode=["updates", "custom"] to capture custom events from
        get_stream_writer() in subgraph nodes.

        Args:
            session_id: Session identifier
            graph: Compiled LangGraph instance
            initial_state: Initial graph state (or None to resume from checkpoint)
            config: Graph execution config (includes thread_id, recursion_limit)
            request_id: Correlation ID for request tracing (optional)

        Returns:
            Final deliberation state

        Raises:
            Exception: Re-raises any exception from graph execution
        """
        from bo1.feature_flags import USE_SUBGRAPH_DELIBERATION

        # Reset tracking for new session
        self._previous_node = None
        self._redis_fallback_emitted = False

        # Set request_id in context for propagation through graph execution
        token = set_request_id(request_id) if request_id else None

        try:
            if USE_SUBGRAPH_DELIBERATION:
                return await self._collect_with_custom_events(
                    session_id, graph, initial_state, config
                )
            else:
                return await self._collect_with_astream_events(
                    session_id, graph, initial_state, config
                )
        finally:
            # Reset context if we set it
            if token:
                from bo1.context import reset_request_id

                reset_request_id(token)

    async def _collect_with_custom_events(
        self,
        session_id: str,
        graph: Any,
        initial_state: Any,
        config: dict[str, Any],
    ) -> Any:
        """Execute graph with custom event streaming for subgraph support.

        Uses astream(stream_mode=["updates", "custom"]) to capture:
        - State updates from nodes (updates)
        - Custom events from get_stream_writer() (custom)

        This enables real-time per-expert streaming from subgraph nodes.

        Timeout architecture:
        - Hard ceiling (30 min): Absolute maximum meeting duration
        - Liveness timeout (10 min): Max time between meaningful events
        - If meaningful events keep flowing, meeting can run up to hard ceiling
        - If no meaningful events for liveness timeout, meeting is killed as stuck
        """
        final_state = None
        start_time = time.monotonic()
        last_meaningful_event_time = start_time

        try:
            async with asyncio.timeout(GRAPH_HARD_TIMEOUT_SECONDS):
                async for chunk in graph.astream(
                    initial_state,
                    config=config,
                    stream_mode=["updates", "custom"],
                    subgraphs=True,
                ):
                    # LangGraph 1.x with subgraphs=True returns (namespace, mode, data)
                    # namespace: tuple of node path (empty for main graph)
                    # mode: "updates" or "custom"
                    # data: dict with node_name as key for updates, or custom event data
                    namespace, mode, data = chunk

                    # For "updates" mode, data is {node_name: state_update}
                    # For "custom" mode, data is the custom event dict directly
                    if mode == "updates" and isinstance(data, dict):
                        # Get the node name from the data keys
                        node_names = list(data.keys())
                        node_name = node_names[0] if node_names else None
                        node_data = data.get(node_name, {}) if node_name else {}
                    else:
                        node_name = None
                        node_data = data

                    logger.debug(f"[STREAM] namespace={namespace}, mode={mode}, node={node_name}")

                    # Track event type for liveness check
                    event_type_for_liveness: str | None = None

                    # Handle custom events from get_stream_writer()
                    if mode == "custom" and isinstance(data, dict) and "event_type" in data:
                        event_type = data.pop("event_type")
                        event_type_for_liveness = event_type
                        logger.info(
                            f"[CUSTOM EVENT] {event_type} | sub_problem_index={data.get('sub_problem_index')}"
                        )
                        self.publisher.publish_event(session_id, event_type, data)

                    # Handle state updates from nodes
                    elif mode == "updates" and node_name:
                        # Emit state transition event for progress visualization
                        sub_problem_index = _get_sub_problem_index_safe(
                            node_data, f"state_updates:{node_name}"
                        )
                        self._emit_state_transition(session_id, node_name, sub_problem_index)

                        # Dispatch to appropriate handler via registry
                        await self._dispatch_node_handler(node_name, session_id, node_data)

                        # Update final state with the node data
                        final_state = node_data

                        # Redis fallback: persist metadata to PostgreSQL if Redis unavailable
                        self._save_metadata_fallback(session_id, node_data)

                    # Liveness check: update timer if meaningful event, or check for stuck
                    now = time.monotonic()
                    if (
                        event_type_for_liveness
                        and event_type_for_liveness in MEANINGFUL_PROGRESS_EVENTS
                    ):
                        last_meaningful_event_time = now
                        logger.debug(
                            f"[LIVENESS] Meaningful event '{event_type_for_liveness}' - timer reset"
                        )

                    # Check if we've exceeded liveness timeout
                    time_since_meaningful = now - last_meaningful_event_time
                    if time_since_meaningful > GRAPH_LIVENESS_TIMEOUT_SECONDS:
                        elapsed = now - start_time
                        raise TimeoutError(
                            f"No meaningful progress for {time_since_meaningful:.1f}s "
                            f"(liveness limit: {GRAPH_LIVENESS_TIMEOUT_SECONDS}s, "
                            f"total elapsed: {elapsed:.1f}s)"
                        )

            # Publish completion event
            if final_state:
                await self._handle_completion(session_id, final_state)

        except TimeoutError as te:
            elapsed = time.monotonic() - start_time
            # Determine if this was a hard timeout or liveness timeout
            is_liveness_timeout = "liveness" in str(te) or "meaningful" in str(te)
            timeout_type = "liveness" if is_liveness_timeout else "hard ceiling"
            timeout_error = TimeoutError(
                f"Graph execution timed out after {elapsed:.1f}s "
                f"({timeout_type}, limit: {GRAPH_HARD_TIMEOUT_SECONDS}s hard / "
                f"{GRAPH_LIVENESS_TIMEOUT_SECONDS}s liveness)"
            )
            log_error(
                logger,
                ErrorCode.GRAPH_EXECUTION_ERROR,
                f"Timeout in custom event collection for session {session_id}: {te}",
                session_id=session_id,
                elapsed_seconds=elapsed,
                timeout_type=timeout_type,
            )
            self._mark_session_failed(
                session_id, timeout_error, timeout_exceeded=True, elapsed_seconds=elapsed
            )
            raise timeout_error from te
        except Exception as e:
            log_error(
                logger,
                ErrorCode.GRAPH_EXECUTION_ERROR,
                f"Error in custom event collection for session {session_id}: {e}",
                session_id=session_id,
            )
            self._mark_session_failed(session_id, e)
            raise

        return final_state

    async def _collect_with_astream_events(
        self,
        session_id: str,
        graph: Any,
        initial_state: Any,
        config: dict[str, Any],
    ) -> Any:
        """Execute graph using legacy astream_events() method.

        This is the original implementation using astream_events(version="v2").

        Timeout architecture (same as custom events):
        - Hard ceiling (30 min): Absolute maximum meeting duration
        - Liveness timeout (10 min): Max time between node completions
        - If nodes keep completing, meeting can run up to hard ceiling
        - If no node completions for liveness timeout, meeting is killed as stuck
        """
        final_state = None
        start_time = time.monotonic()
        last_node_completion_time = start_time

        try:
            async with asyncio.timeout(GRAPH_HARD_TIMEOUT_SECONDS):
                # Stream events from LangGraph execution
                async for event in graph.astream_events(initial_state, config=config, version="v2"):
                    event_type = event.get("event")
                    event_name = event.get("name", "")

                    # Emit working_status BEFORE node starts processing
                    if event_type == "on_chain_start":
                        status_message = self.NODE_START_STATUS.get(event_name)
                        if status_message:
                            self._emit_working_status(
                                session_id, phase=status_message, sub_problem_index=0
                            )

                    # Process node completions (on_chain_end has output data)
                    elif event_type == "on_chain_end" and "data" in event:
                        output = event.get("data", {}).get("output", {})

                        # Dispatch to appropriate handler via registry
                        if isinstance(output, dict):
                            # Emit state transition event for progress visualization
                            sub_problem_index = _get_sub_problem_index_safe(
                                output, f"on_chain_end:{event_name}"
                            )
                            self._emit_state_transition(session_id, event_name, sub_problem_index)

                            await self._dispatch_node_handler(event_name, session_id, output)
                            # Capture final state
                            final_state = output

                            # Redis fallback: persist metadata to PostgreSQL if Redis unavailable
                            self._save_metadata_fallback(session_id, output)

                            # Liveness: any node completion counts as progress
                            last_node_completion_time = time.monotonic()

                    # Check liveness timeout (no node completions for too long)
                    now = time.monotonic()
                    time_since_completion = now - last_node_completion_time
                    if time_since_completion > GRAPH_LIVENESS_TIMEOUT_SECONDS:
                        elapsed = now - start_time
                        raise TimeoutError(
                            f"No node completions for {time_since_completion:.1f}s "
                            f"(liveness limit: {GRAPH_LIVENESS_TIMEOUT_SECONDS}s, "
                            f"total elapsed: {elapsed:.1f}s)"
                        )

            # Publish completion event
            if final_state:
                await self._handle_completion(session_id, final_state)

        except TimeoutError as te:
            elapsed = time.monotonic() - start_time
            is_liveness_timeout = "liveness" in str(te) or "completions" in str(te)
            timeout_type = "liveness" if is_liveness_timeout else "hard ceiling"
            timeout_error = TimeoutError(
                f"Graph execution timed out after {elapsed:.1f}s "
                f"({timeout_type}, limit: {GRAPH_HARD_TIMEOUT_SECONDS}s hard / "
                f"{GRAPH_LIVENESS_TIMEOUT_SECONDS}s liveness)"
            )
            log_error(
                logger,
                ErrorCode.GRAPH_EXECUTION_ERROR,
                f"Timeout in event collection for session {session_id}: {te}",
                session_id=session_id,
                elapsed_seconds=elapsed,
                timeout_type=timeout_type,
            )
            self._mark_session_failed(
                session_id, timeout_error, timeout_exceeded=True, elapsed_seconds=elapsed
            )
            raise timeout_error from te
        except Exception as e:
            log_error(
                logger,
                ErrorCode.GRAPH_EXECUTION_ERROR,
                f"Error in event collection for session {session_id}: {e}",
                session_id=session_id,
            )
            self._mark_session_failed(session_id, e)
            raise

        return final_state

    async def _handle_decomposition(self, session_id: str, output: dict) -> None:
        """Handle decompose node completion."""
        # Update phase in database for dashboard display
        self.session_repo.update_phase(session_id, "decomposition")

        # ISSUE FIX: Add status message for problem analysis phase
        self._emit_quality_status(
            session_id,
            status="analyzing",
            message="Analyzing problem structure...",
            round_number=0,
            sub_problem_index=_get_sub_problem_index_safe(output, "_handle_decompose"),
        )
        await self._publish_node_event(session_id, output, "decomposition_complete")

        # Emit comparison_detected event if a "X vs Y" comparison was identified
        if output.get("comparison_detected"):
            comparison_event = {
                "comparison_type": output.get("comparison_type", ""),
                "options": output.get("comparison_options", []),
                "research_queries_count": len(output.get("pending_research_queries", [])),
            }
            self.publisher.publish_event(
                session_id,
                "comparison_detected",
                comparison_event,
            )
            logger.info(
                f"Comparison detected: {comparison_event['comparison_type']} - "
                f"{comparison_event['options']} ({comparison_event['research_queries_count']} queries)"
            )

    async def _handle_identify_gaps(self, session_id: str, output: dict) -> None:
        """Handle identify_gaps node completion.

        Emits clarification_required event if critical information gaps were found.
        """
        pending_clarification = output.get("pending_clarification")

        if pending_clarification:
            questions = pending_clarification.get("questions", [])
            phase = pending_clarification.get("phase", "pre_deliberation")
            reason = pending_clarification.get("reason", "")

            logger.info(
                f"identify_gaps: Found {len(questions)} critical questions, pausing for user input"
            )

            # Emit clarification_required event
            self.publisher.publish_event(
                session_id,
                "clarification_required",
                {
                    "questions": questions,
                    "phase": phase,
                    "reason": reason,
                    "question_count": len(questions),
                },
            )

            # Update session status to paused and phase to clarification_needed
            # Update PostgreSQL
            self.session_repo.update_status(
                session_id=session_id,
                status="paused",
                phase="clarification_needed",
            )

            # Also update Redis metadata so API returns correct status
            try:
                redis_manager = get_redis_manager()
                metadata = redis_manager.load_metadata(session_id)
                if metadata:
                    metadata["status"] = "paused"
                    metadata["phase"] = "clarification_needed"
                    redis_manager.save_metadata(session_id, metadata)
                    logger.info(
                        f"Updated Redis metadata for {session_id}: status=paused, phase=clarification_needed"
                    )
                # ISS-001 FIX: Invalidate session metadata cache to prevent stale reads
                get_session_metadata_cache().invalidate(session_id)
            except Exception as e:
                logger.warning(f"Failed to update Redis metadata for {session_id}: {e}")
        else:
            # No critical gaps, just emit a status update
            external_gaps = output.get("external_research_gaps", [])
            if external_gaps:
                logger.info(
                    f"identify_gaps: No critical gaps, but {len(external_gaps)} "
                    f"external research opportunities identified"
                )

    async def _handle_persona_selection(self, session_id: str, output: dict) -> None:
        """Handle select_personas node completion - publishes multiple events."""
        # Update phase in database for dashboard display
        self.session_repo.update_phase(session_id, "selection")

        personas = output.get("personas", [])
        persona_recommendations = output.get("persona_recommendations", [])
        sub_problem_index = _get_sub_problem_index_safe(output, "_handle_select_personas")

        # ISSUE FIX: Add status message for expert selection phase
        self._emit_quality_status(
            session_id,
            status="selecting",
            message="Selecting expert panel...",
            round_number=0,
            sub_problem_index=sub_problem_index,
        )

        # Publish individual persona selected events
        for i, persona in enumerate(personas):
            persona_dict = extract_persona_dict(persona)

            # Find matching rationale from persona_recommendations
            rationale = ""
            if i < len(persona_recommendations):
                rec = persona_recommendations[i]
                if isinstance(rec, dict):
                    rationale = rec.get("rationale", "")
                elif hasattr(rec, "rationale"):
                    rationale = rec.rationale

            self.publisher.publish_event(
                session_id,
                "persona_selected",
                {
                    "persona": persona_dict,
                    "rationale": rationale,
                    "order": i + 1,
                    "sub_problem_index": sub_problem_index,
                },
            )

        # Publish persona selection complete event
        await self._publish_node_event(session_id, output, "persona_selection_complete")

        # Store start timestamp and publish subproblem_started if multi-subproblem scenario
        registry = get_event_registry()
        subproblem_data = registry.extract("subproblem_started", output)
        if subproblem_data:
            from datetime import UTC, datetime

            subproblem_key = f"subproblem:{session_id}:{sub_problem_index}:start_time"
            start_timestamp = datetime.now(UTC).isoformat()
            self.publisher.redis.setex(subproblem_key, 86400, start_timestamp)  # 24-hour TTL

            self.publisher.publish_event(session_id, "subproblem_started", subproblem_data)

    async def _handle_initial_round(self, session_id: str, output: dict) -> None:
        """Handle initial_round node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        # Update phase in database for dashboard display
        self.session_repo.update_phase(session_id, "exploration")

        # Extract sub_problem_index for tab filtering
        sub_problem_index = _get_sub_problem_index_safe(output, "_handle_initial_round")

        # Get personas for archetype/domain_expertise lookup
        personas = output.get("personas", [])

        # ISSUE FIX: Emit initial discussion quality status at START of round 1
        # This provides early UX feedback that quality tracking has begun
        self._emit_quality_status(
            session_id,
            status="analyzing",
            message="Gathering expert perspectives...",
            round_number=1,
            sub_problem_index=sub_problem_index,
        )

        # PERF: Batch summarize all contributions in parallel
        contributions = output.get("contributions", [])
        if contributions:
            # Extract (content, persona_name) for batch summarization
            items = []
            for contrib in contributions:
                if hasattr(contrib, "content"):
                    items.append((contrib.content, contrib.persona_name))
                else:
                    items.append((contrib.get("content", ""), contrib.get("persona_name", "")))

            summaries = await self.summarizer.batch_summarize(items)

            # Publish contributions with pre-computed summaries
            for contrib, summary in zip(contributions, summaries, strict=True):
                await self._publish_contribution(
                    session_id,
                    contrib,
                    round_number=1,
                    sub_problem_index=sub_problem_index,
                    personas=personas,
                    summary=summary,
                )

    async def _handle_facilitator_decision(self, session_id: str, output: dict) -> None:
        """Handle facilitator_decide node completion."""
        await self._publish_node_event(session_id, output, "facilitator_decision")

    async def _handle_parallel_round(self, session_id: str, output: dict) -> None:
        """Handle parallel_round node completion events.

        Publishes events for:
        - Working status (before round starts)
        - Round start (phase, experts selected)
        - Each contribution generated in this round
        - Round summary

        Args:
            session_id: Session identifier
            output: Node output state
        """
        contributions = output.get("contributions", [])
        round_number = output.get("round_number", 1)
        current_phase = output.get("current_phase", "exploration")
        experts_per_round = output.get("experts_per_round", [])
        sub_problem_index = _get_sub_problem_index_safe(output, "_handle_parallel_round")

        # DEBUG: Log handler invocation
        logger.info(
            f"[PARALLEL_ROUND DEBUG] Handler called | "
            f"session={session_id} | "
            f"round_number={round_number} | "
            f"contributions_count={len(contributions)} | "
            f"sub_problem_index={sub_problem_index}"
        )

        # Update phase in database for dashboard display
        self.session_repo.update_phase(session_id, current_phase)
        personas = output.get("personas", [])

        # Extract experts for the just-completed round
        # round_number has already been incremented, so we look at -1
        completed_round = round_number - 1
        experts_this_round = experts_per_round[-1] if experts_per_round else []

        # Emit parallel round start event
        self.publisher.publish_event(
            session_id,
            "parallel_round_start",
            {
                "round": completed_round,
                "phase": current_phase,
                "experts_selected": experts_this_round,
                "expert_count": len(experts_this_round),
                "sub_problem_index": sub_problem_index,
            },
        )

        # PERF: Filter contributions for this round, then batch summarize in parallel
        round_contributions = []
        for contribution in contributions:
            contrib_round = (
                contribution.round_number
                if hasattr(contribution, "round_number")
                else contribution.get("round_number", 0)
            )
            if contrib_round == completed_round:
                round_contributions.append(contribution)

        if round_contributions:
            # Extract (content, persona_name) for batch summarization
            items = []
            for contrib in round_contributions:
                if hasattr(contrib, "content"):
                    items.append((contrib.content, contrib.persona_name))
                else:
                    items.append((contrib.get("content", ""), contrib.get("persona_name", "")))

            summaries = await self.summarizer.batch_summarize(items)

            # Publish contributions with pre-computed summaries
            for contrib, summary in zip(round_contributions, summaries, strict=True):
                await self._publish_contribution(
                    session_id, contrib, completed_round, sub_problem_index, personas, summary
                )

    async def _handle_moderator(self, session_id: str, output: dict) -> None:
        """Handle moderator_intervene node completion."""
        await self._publish_node_event(session_id, output, "moderator_intervention")

    async def _handle_convergence(self, session_id: str, output: dict) -> None:
        """Handle check_convergence node completion."""
        logger.info(
            f"[CONVERGENCE DEBUG] Handler called for session {session_id} | "
            f"round={output.get('round_number')} | "
            f"should_stop={output.get('should_stop')} | "
            f"metrics={output.get('metrics')}"
        )

        # NEW: Check for context insufficiency (Option D+E Hybrid)
        stop_reason = output.get("stop_reason")
        if stop_reason == "context_insufficient":
            context_info = output.get("context_insufficiency_info", {})
            logger.warning(
                f"[CONTEXT INSUFFICIENT] Emitting context_insufficient event for {session_id} | "
                f"meta_ratio={context_info.get('meta_ratio', 0):.0%} | "
                f"questions={context_info.get('expert_questions', [])}"
            )
            # Emit context_insufficient event to pause and ask user for choice
            self.publisher.publish_event(
                session_id,
                "context_insufficient",
                {
                    "meta_ratio": context_info.get("meta_ratio", 0),
                    "expert_questions": context_info.get("expert_questions", []),
                    "reason": (
                        f"{context_info.get('meta_count', 0)} of "
                        f"{context_info.get('total_count', 0)} contributions "
                        f"indicate experts need more context to provide meaningful analysis."
                    ),
                    "round_number": output.get("round_number", 1),
                    "sub_problem_index": _get_sub_problem_index_safe(
                        output, "_handle_convergence:context_request"
                    ),
                    "choices": [
                        {
                            "id": "provide_more",
                            "label": "Provide Additional Details",
                            "description": "Answer the questions our experts have raised",
                        },
                        {
                            "id": "continue",
                            "label": "Continue with Available Information",
                            "description": "Proceed with best-effort analysis",
                        },
                        {
                            "id": "end",
                            "label": "End Meeting",
                            "description": "Generate summary with current insights",
                        },
                    ],
                    "timeout_seconds": 120,
                },
            )
            return  # Don't emit convergence event when context is insufficient

        await self._publish_node_event(session_id, output, "convergence")

    async def _handle_voting(self, session_id: str, output: dict) -> None:
        """Handle vote node completion."""
        # Update phase in database for dashboard display
        self.session_repo.update_phase(session_id, "voting")
        await self._publish_node_event(session_id, output, "voting_complete", registry_key="voting")

    async def _handle_synthesis(self, session_id: str, output: dict) -> None:
        """Handle synthesize node completion."""
        # Update phase in database for dashboard display
        self.session_repo.update_phase(session_id, "synthesis")
        # Publish event
        await self._publish_node_event(session_id, output, "synthesis_complete")

        # P2-004: Emit expert summaries event if expert_summaries are available
        expert_summaries = output.get("expert_summaries", {})
        if expert_summaries:
            current_sub_problem = output.get("current_sub_problem")
            expert_summaries_event = {
                "expert_summaries": expert_summaries,
                "sub_problem_index": _get_sub_problem_index_safe(
                    output, "_handle_convergence:expert_summaries"
                ),
                "sub_problem_goal": (
                    current_sub_problem.goal
                    if current_sub_problem and hasattr(current_sub_problem, "goal")
                    else ""
                ),
            }
            self.publisher.publish_event(
                session_id,
                "expert_summaries",
                expert_summaries_event,
            )
            logger.info(
                f"Published expert_summaries event for session {session_id}, "
                f"sub_problem_index={output.get('sub_problem_index', 0)}, "
                f"summaries_count={len(expert_summaries)}"
            )

        # Save synthesis to PostgreSQL for long-term storage
        synthesis_text = output.get("synthesis")
        if synthesis_text:
            try:
                self.session_repo.save_synthesis(session_id, synthesis_text)
                logger.info(f"Saved synthesis to PostgreSQL for session {session_id}")
            except Exception as e:
                log_error(
                    logger,
                    ErrorCode.DB_WRITE_ERROR,
                    f"Failed to save synthesis to PostgreSQL for {session_id}: {e}",
                    session_id=session_id,
                )

    async def _handle_subproblem_complete(self, session_id: str, output: dict) -> None:
        """Handle next_subproblem node completion - NO-OP to avoid duplicate events.

        AUDIT FIX (Issue #2): The subproblem_complete event is already published by
        the parallel_subproblems_node itself. Publishing here creates duplicate
        "Sub-Problem X Complete" messages in the UI.

        This handler is kept as a no-op for clarity and to maintain the handler
        structure in case we need to add future logic here.
        """
        # NO-OP: Event already published by parallel_subproblems_node
        # See: bo1/graph/nodes/subproblems.py (event publishing in node)
        pass

    async def _handle_meta_synthesis(self, session_id: str, output: dict) -> None:
        """Handle meta_synthesize node completion."""
        # Publish event
        await self._publish_node_event(session_id, output, "meta_synthesis_complete")

        # Save meta-synthesis to PostgreSQL for long-term storage
        synthesis_text = output.get("meta_synthesis")
        if synthesis_text:
            try:
                self.session_repo.save_synthesis(session_id, synthesis_text)
                logger.info(f"Saved meta-synthesis to PostgreSQL for session {session_id}")
            except Exception as e:
                log_error(
                    logger,
                    ErrorCode.DB_WRITE_ERROR,
                    f"Failed to save meta-synthesis to PostgreSQL for {session_id}: {e}",
                    session_id=session_id,
                )

    async def _handle_research(self, session_id: str, output: dict) -> None:
        """Handle research node completion (P2-006).

        Emits research_results event with query, summary, sources, and metadata.
        """
        research_results = output.get("research_results", [])
        if research_results:
            logger.info(
                f"[RESEARCH] Publishing {len(research_results)} research results for session {session_id}"
            )
            await self._publish_node_event(session_id, output, "research_results")
        else:
            logger.debug(f"[RESEARCH] No research results to publish for session {session_id}")

    async def _handle_context_collection(self, session_id: str, output: dict) -> None:
        """Handle context_collection node completion (P1: UI feedback gap).

        Emits context_collection_complete event with business context summary.
        """
        business_context = output.get("business_context", {})
        metrics = output.get("metrics", {})

        # Truncate context for event payload if too long
        context_summary = ""
        if isinstance(business_context, dict):
            context_summary = business_context.get("summary", "")[:500]
        elif isinstance(business_context, str):
            context_summary = business_context[:500]

        event_data = {
            "context_loaded": bool(business_context),
            "context_summary": context_summary,
            "metrics_count": len(metrics) if isinstance(metrics, dict) else 0,
        }

        self.publisher.publish_event(session_id, "context_collection_complete", event_data)
        logger.info(
            f"[CONTEXT] Published context_collection_complete for session {session_id}: "
            f"context_loaded={event_data['context_loaded']}, metrics_count={event_data['metrics_count']}"
        )

    async def _handle_dependency_analysis(self, session_id: str, output: dict) -> None:
        """Handle analyze_dependencies node completion (P1: UI feedback gap).

        Emits dependency_analysis_complete event with execution batch info.
        """
        execution_batches = output.get("execution_batches", [])
        parallel_mode = output.get("parallel_mode", False)

        # Extract batch summary
        batch_info = []
        for i, batch in enumerate(execution_batches):
            if isinstance(batch, list):
                # Batch is list of sub-problem indices or objects
                sp_ids = []
                for sp in batch:
                    if isinstance(sp, dict):
                        sp_ids.append(sp.get("id", str(sp)))
                    elif hasattr(sp, "id"):
                        sp_ids.append(sp.id)
                    else:
                        sp_ids.append(str(sp))
                batch_info.append({"batch_index": i, "sub_problem_ids": sp_ids})

        event_data = {
            "batch_count": len(execution_batches),
            "parallel_mode": parallel_mode,
            "batches": batch_info,
        }

        self.publisher.publish_event(session_id, "dependency_analysis_complete", event_data)
        logger.info(
            f"[DEPS] Published dependency_analysis_complete for session {session_id}: "
            f"batch_count={event_data['batch_count']}, parallel_mode={parallel_mode}"
        )

    async def _handle_data_analysis(self, session_id: str, output: dict) -> None:
        """Handle data_analysis node completion (EPIC 4: Dataset analysis).

        Stub handler that logs completion. The data_analysis node handles its own
        event emission for analysis results; this handler provides visibility into
        node completion for debugging and future enhancements.
        """
        data_analysis_results = output.get("data_analysis_results", [])
        logger.info(
            f"[DATA_ANALYSIS] Node completed for session {session_id}: "
            f"results_count={len(data_analysis_results)}"
        )

    async def _handle_cost_guard(self, session_id: str, output: dict) -> None:
        """Handle cost_guard node completion (cost limit enforcement).

        Stub handler that logs cost check results. The cost_guard node enforces
        per-session cost limits; this handler provides visibility into node
        completion without emitting SSE events (cost data is sensitive).
        """
        metrics = output.get("metrics", {})
        total_cost = (
            metrics.total_cost if hasattr(metrics, "total_cost") else metrics.get("total_cost", 0.0)
        )
        should_stop = output.get("should_stop", False)
        stop_reason = output.get("stop_reason", "")

        logger.info(
            f"[COST_GUARD] Node completed for session {session_id}: "
            f"total_cost=${total_cost:.4f}, should_stop={should_stop}, stop_reason={stop_reason}"
        )

    async def _handle_clarification(self, session_id: str, output: dict) -> None:
        """Handle clarification node completion (user clarification requests).

        Stub handler that logs clarification processing. Clarification events are
        emitted by _handle_identify_gaps; this handler provides visibility into
        node completion for sessions that process clarification responses.
        """
        clarification_answers = output.get("clarification_answers")
        has_answers = bool(clarification_answers)
        logger.info(
            f"[CLARIFICATION] Node completed for session {session_id}: "
            f"has_answers={has_answers}, answer_count={len(clarification_answers) if has_answers else 0}"
        )

    async def _handle_parallel_subproblems(self, session_id: str, output: dict) -> None:
        """Handle parallel_subproblems node completion (parallel sub-problem execution).

        Stub handler that logs parallel batch execution. The subproblem_complete event
        is already emitted by the node itself; this handler provides visibility into
        batch completion for debugging and monitoring.
        """
        execution_batches = output.get("execution_batches", [])
        sub_problem_index = _get_sub_problem_index_safe(output, "_handle_parallel_subproblems")
        logger.info(
            f"[PARALLEL_SUBPROBLEMS] Node completed for session {session_id}: "
            f"batch_count={len(execution_batches)}, current_sub_problem_index={sub_problem_index}"
        )

    def _check_and_publish_subproblem_failures(
        self,
        session_id: str,
        final_state: dict[str, Any],
    ) -> bool:
        """Check for incomplete sub-problem results and publish meeting_failed event.

        This method detects when a multi-sub-problem session terminates with
        incomplete results (e.g., due to LLM errors, timeouts, or other failures).

        ARCH P3: This logic was moved from route_after_next_subproblem to here
        to eliminate cross-layer coupling (graph router importing API dependencies).

        Detection criteria:
        - current_sub_problem is None (indicates loop termination)
        - sub_problem_results count < total sub_problems (incomplete)
        - Only applies to multi-sub-problem sessions (total > 1)

        Args:
            session_id: Session identifier
            final_state: Final deliberation state

        Returns:
            True if failure detected and event published, False otherwise
        """
        # Extract problem and sub-problem data
        problem = final_state.get("problem")
        if not problem:
            return False

        # Get sub-problems list
        if hasattr(problem, "sub_problems"):
            sub_problems = problem.sub_problems
        elif isinstance(problem, dict):
            sub_problems = problem.get("sub_problems", [])
        else:
            sub_problems = []

        total_sub_problems = len(sub_problems)

        # Skip for single sub-problem sessions (atomic problems)
        if total_sub_problems <= 1:
            return False

        # Check if we're in a failure state:
        # - current_sub_problem is None (loop terminated)
        # - sub_problem_results count < total (incomplete)
        current_sub_problem = final_state.get("current_sub_problem")
        sub_problem_results = final_state.get("sub_problem_results", [])

        if current_sub_problem is not None:
            # Still processing - not a failure case
            return False

        if len(sub_problem_results) >= total_sub_problems:
            # All results present - success, not failure
            return False

        # Sub-problem failure detected - calculate details
        failed_count = total_sub_problems - len(sub_problem_results)

        # Build set of completed sub-problem IDs
        completed_ids: set[str] = set()
        for r in sub_problem_results:
            if isinstance(r, dict):
                sp_id = r.get("sub_problem_id")
            elif hasattr(r, "sub_problem_id"):
                sp_id = r.sub_problem_id
            else:
                sp_id = None
            if sp_id:
                completed_ids.add(sp_id)

        # Get expected IDs and find failed ones
        failed_ids: list[str] = []
        failed_goals: list[str] = []
        for sp in sub_problems:
            if isinstance(sp, dict):
                sp_id = sp.get("id")
                sp_goal = sp.get("goal", "")
            elif hasattr(sp, "id"):
                sp_id = sp.id
                sp_goal = getattr(sp, "goal", "")
            else:
                sp_id = None
                sp_goal = ""

            if sp_id and sp_id not in completed_ids:
                failed_ids.append(sp_id)
                failed_goals.append(sp_goal)

        # Log the failure
        log_error(
            logger,
            ErrorCode.GRAPH_EXECUTION_ERROR,
            f"[SUBPROBLEM_FAILURE] Session {session_id}: {failed_count} sub-problem(s) failed. "
            f"Failed IDs: {failed_ids}. "
            f"Expected {total_sub_problems} results, got {len(sub_problem_results)}.",
        )

        # Publish meeting_failed event to UI
        self.publisher.publish_event(
            session_id,
            "meeting_failed",
            {
                "reason": f"{failed_count} sub-problem(s) failed to complete",
                "failed_count": failed_count,
                "failed_ids": failed_ids,
                "failed_goals": failed_goals,
                "completed_count": len(sub_problem_results),
                "total_count": total_sub_problems,
            },
        )

        # Update session status to 'failed'
        try:
            self.session_repo.update_status(
                session_id=session_id,
                status="failed",
            )
            # Invalidate cached metadata on status change
            get_session_metadata_cache().invalidate(session_id)
        except Exception as db_error:
            log_error(
                logger,
                ErrorCode.DB_WRITE_ERROR,
                f"Failed to update session {session_id} status to failed: {db_error}",
                session_id=session_id,
            )

        return True

    async def _handle_completion(self, session_id: str, final_state: dict) -> None:
        """Handle deliberation completion - orchestrates cost breakdown, completion event, status update, and verification.

        Args:
            session_id: Session identifier
            final_state: Final deliberation state containing synthesis, costs, and metrics
        """
        # Check if session paused for clarification - don't treat as completion
        stop_reason = final_state.get("stop_reason")
        if stop_reason == "clarification_needed":
            logger.info(
                f"Session {session_id} paused for clarification - "
                f"skipping completion handling (clarification_required event already sent)"
            )

            # BUG FIX (P1 #4): Persist partial costs even when pausing for clarification
            # This ensures cost tracking is accurate even for interrupted sessions
            await self._persist_partial_costs(session_id, final_state)

            # Still verify event persistence
            await self._verify_event_persistence(session_id)
            return

        # Check for sub-problem failures (ARCH P3: moved from router to EventCollector)
        # This keeps graph routers as pure functions without API layer dependencies
        if self._check_and_publish_subproblem_failures(session_id, final_state):
            # Sub-problem failure detected and event published
            # Mark session as failed and return (don't proceed with normal completion)
            await self._persist_partial_costs(session_id, final_state)
            await self._verify_event_persistence(session_id)
            return

        # Flush any pending batch events before completion
        # First flush the EventBatcher (priority-based batching)
        await flush_batcher()
        # Then flush any remaining events in the publisher's batch
        await flush_session_events(session_id)

        # Flush cost tracker buffer to ensure all costs are in DB before breakdown
        try:
            CostTracker.flush(session_id)
        except Exception as flush_error:
            logger.warning(f"Failed to flush cost buffer on completion: {flush_error}")

        # Publish cost breakdown
        self._publish_cost_breakdown(session_id, final_state)

        # Check for cost anomaly (>$1.00 threshold)
        self._check_cost_anomaly(session_id)

        # Publish completion event
        self._publish_completion_event(session_id, final_state)

        # Update session status with retry logic
        await self._update_session_status_with_retry(session_id, final_state)

        # Verify event persistence
        await self._verify_event_persistence(session_id)

    def _publish_cost_breakdown(self, session_id: str, final_state: dict) -> None:
        """Publish phase cost breakdown event if costs are available.

        Args:
            session_id: Session identifier
            final_state: Final deliberation state containing phase costs and metrics
        """
        phase_costs = final_state.get("phase_costs", {})
        metrics = final_state.get("metrics", {})

        if hasattr(metrics, "total_cost"):
            total_cost = metrics.total_cost
        else:
            total_cost = metrics.get("total_cost", 0.0) if isinstance(metrics, dict) else 0.0

        # Publish phase cost breakdown
        if phase_costs:
            self.publisher.publish_event(
                session_id,
                "phase_cost_breakdown",
                {
                    "phase_costs": phase_costs,
                    "total_cost": total_cost,
                },
            )

    def _check_cost_anomaly(self, session_id: str, threshold: float = 1.00) -> None:
        """Check if session cost exceeds threshold and log warning.

        Args:
            session_id: Session identifier
            threshold: Cost threshold in USD (default $1.00)
        """
        try:
            costs = CostTracker.get_session_costs(session_id)
            total_cost = costs.get("total_cost", 0.0)

            if total_cost > threshold:
                logger.warning(
                    f"[COST ANOMALY] Session {session_id} exceeded ${threshold:.2f} threshold: "
                    f"total=${total_cost:.4f}, by_provider={costs.get('by_provider', {})}, "
                    f"total_calls={costs.get('total_calls', 0)}"
                )
                # Emit cost_anomaly event for dashboard visibility
                self.publisher.publish_event(
                    session_id,
                    "cost_anomaly",
                    {
                        "total_cost": total_cost,
                        "threshold": threshold,
                        "by_provider": costs.get("by_provider", {}),
                        "total_calls": costs.get("total_calls", 0),
                    },
                )
        except Exception as e:
            log_error(
                logger,
                ErrorCode.COST_FLUSH_ERROR,
                f"Failed to check cost anomaly for session {session_id}: {e}",
                session_id=session_id,
            )

    def _publish_completion_event(self, session_id: str, final_state: dict) -> None:
        """Publish completion event with extracted data from final state.

        Args:
            session_id: Session identifier
            final_state: Final deliberation state
        """
        registry = get_event_registry()
        completion_data = registry.extract("completion", final_state)
        completion_data["session_id"] = session_id  # Ensure session_id is present
        self.publisher.publish_event(session_id, "complete", completion_data)

    async def _update_session_status_with_retry(self, session_id: str, final_state: dict) -> None:
        """Update session status in PostgreSQL with exponential backoff retry logic.

        CRITICAL: This must succeed to maintain consistency between Redis and PostgreSQL.
        Uses 3 retry attempts with exponential backoff (0.1s, 0.2s).

        Args:
            session_id: Session identifier
            final_state: Final deliberation state containing synthesis, metrics, and phase info
        """
        # Check if session paused for clarification - don't set to completed
        stop_reason = final_state.get("stop_reason")
        non_completion_reasons = {"clarification_needed", "context_insufficient"}
        if stop_reason in non_completion_reasons:
            logger.info(
                f"Session {session_id} has stop_reason={stop_reason} - "
                f"not updating status to completed"
            )
            return

        # Note: We previously had a check here that blocked updating status to 'completed'
        # if the DB phase was 'clarification_needed'. This was incorrect because sessions
        # that went through clarification Q&A and then completed should be marked as completed.
        # The stop_reason check above (lines 1583-1590) already handles the case where the
        # graph stops FOR clarification (stop_reason='clarification_needed'). When the graph
        # resumes and completes normally, stop_reason will be None or 'completed', so we
        # should proceed with the status update.

        # Extract data for status update
        synthesis_text = final_state.get("synthesis") or final_state.get("meta_synthesis")
        final_recommendation = None  # Could extract from synthesis if needed
        round_number = final_state.get("round_number", 0)
        phase = final_state.get("current_phase")

        # Extract total cost
        metrics = final_state.get("metrics", {})
        if hasattr(metrics, "total_cost"):
            total_cost = metrics.total_cost
        else:
            total_cost = metrics.get("total_cost", 0.0) if isinstance(metrics, dict) else 0.0

        status_update_success = False
        last_error = None

        # Retry loop with exponential backoff
        for attempt in range(3):  # 3 attempts with exponential backoff
            try:
                self.session_repo.update_status(
                    session_id=session_id,
                    status="completed",
                    phase=phase,
                    total_cost=total_cost,
                    round_number=round_number,
                    synthesis_text=synthesis_text,
                    final_recommendation=final_recommendation,
                )
                status_update_success = True
                # Invalidate cached metadata on status change
                get_session_metadata_cache().invalidate(session_id)
                if attempt > 0:
                    logger.info(
                        f"Session status update succeeded on attempt {attempt + 1} for {session_id}"
                    )
                else:
                    logger.info(f"Updated session {session_id} status to 'completed' in PostgreSQL")
                break
            except Exception as e:
                last_error = e
                if attempt < 2:  # Don't sleep on last attempt
                    wait_time = 0.1 * (2**attempt)  # 0.1s, 0.2s
                    logger.warning(
                        f"Session status update attempt {attempt + 1}/3 failed for "
                        f"{session_id}: {e}. Retrying in {wait_time}s..."
                    )
                    # BUG FIX: Use asyncio.sleep instead of time.sleep in async method
                    await asyncio.sleep(wait_time)
                else:
                    log_error(
                        logger,
                        ErrorCode.DB_WRITE_ERROR,
                        f"CRITICAL: Failed to update session status after 3 attempts for "
                        f"{session_id}: {e}\n"
                        f"Session completed but status may be inconsistent!",
                        session_id=session_id,
                    )

        # Send meeting completion notification (fire-and-forget)
        if status_update_success:
            try:
                from backend.api.ntfy import notify_meeting_completed
                from bo1.state.repositories import contribution_repository

                # Get problem statement for notification
                problem = final_state.get("problem")
                if isinstance(problem, dict):
                    problem_statement = problem.get("statement", "")
                elif hasattr(problem, "statement"):
                    problem_statement = problem.statement
                else:
                    problem_statement = ""

                # Count contributions
                contribution_count = contribution_repository.count_by_session(session_id)

                # Fire-and-forget notification (with context for correlation_id)
                create_task_with_context(
                    notify_meeting_completed(
                        session_id=session_id,
                        problem_statement=problem_statement,
                        contribution_count=contribution_count,
                        total_cost=total_cost,
                    )
                )
            except Exception as notify_error:
                logger.warning(f"Failed to send meeting completion notification: {notify_error}")

            # Fetch session for cost tracking and promo credit consumption
            current_session = self.session_repo.get(session_id)

            # Record cost to user's period aggregate (admin monitoring)
            try:
                from backend.services import user_cost_tracking as uct
                from backend.services.alerts import alert_user_cost_threshold

                user_id = current_session.get("user_id") if current_session else None
                if user_id and total_cost > 0:
                    # Convert USD to cents
                    cost_cents = int(total_cost * 100)
                    _, budget_result = uct.record_session_cost(
                        user_id=user_id,
                        session_id=session_id,
                        cost_cents=cost_cents,
                    )
                    logger.debug(f"Recorded session cost for user {user_id}: {cost_cents} cents")

                    # Send alert if threshold crossed
                    if budget_result and budget_result.should_alert:
                        # Get user email for alert
                        email = None
                        try:
                            from bo1.state.database import db_session as get_db

                            with get_db() as conn:
                                with conn.cursor() as cur:
                                    cur.execute(
                                        "SELECT email FROM users WHERE user_id = %s",
                                        (user_id,),
                                    )
                                    row = cur.fetchone()
                                    if row:
                                        email = row["email"]
                        except Exception as e:
                            logger.debug("Could not fetch user email for alert: %s", e)

                        # Fire-and-forget alert (with context for correlation_id)
                        create_task_with_context(
                            alert_user_cost_threshold(
                                user_id=user_id,
                                email=email,
                                current_cost_cents=budget_result.current_cost_cents,
                                limit_cents=budget_result.limit_cents or 0,
                                status=budget_result.status.value,
                            )
                        )
                        # Mark alert sent
                        uct.mark_alert_sent(user_id)
            except Exception as cost_error:
                logger.warning(f"Failed to record user cost tracking: {cost_error}")

            # Consume promo credit if session was created using one
            try:
                if current_session and current_session.get("used_promo_credit"):
                    from backend.services.promotion_service import consume_promo_deliberation

                    user_id = current_session.get("user_id")
                    if user_id:
                        consumed = consume_promo_deliberation(user_id)
                        if consumed:
                            logger.info(f"Consumed promo credit for completed session {session_id}")
                        else:
                            logger.warning(
                                f"Session {session_id} marked as promo but no credits consumed"
                            )
            except Exception as promo_error:
                logger.warning(f"Failed to consume promo credit: {promo_error}")

        # If status update failed, emit error event to frontend
        if not status_update_success:
            try:
                self.publisher.publish_event(
                    session_id=session_id,
                    event_type="session_status_error",
                    data={
                        "error": str(last_error),
                        "message": "Meeting completed but failed to update database status",
                        "synthesis_available": bool(synthesis_text),
                    },
                )
            except Exception as emit_error:
                log_error(
                    logger,
                    ErrorCode.API_SSE_ERROR,
                    f"Failed to emit status error event: {emit_error}",
                    session_id=session_id,
                )

    async def _persist_partial_costs(self, session_id: str, final_state: dict) -> None:
        """Persist partial costs to PostgreSQL for sessions that pause before completion.

        BUG FIX (P1 #4): Ensures costs are tracked even for sessions that pause for
        clarification or context insufficiency. Without this, sessions that pause
        show $0.0000 in the database.

        Args:
            session_id: Session identifier
            final_state: Current deliberation state with metrics
        """
        try:
            # Extract total cost from metrics
            metrics = final_state.get("metrics", {})
            if hasattr(metrics, "total_cost"):
                total_cost = metrics.total_cost
            else:
                total_cost = metrics.get("total_cost", 0.0) if isinstance(metrics, dict) else 0.0

            # Only update if we have costs to persist
            if total_cost > 0:
                round_number = final_state.get("round_number", 0)
                phase = final_state.get("current_node") or final_state.get("phase")

                self.session_repo.update_status(
                    session_id=session_id,
                    status="paused",  # Keep status as paused
                    phase=phase,
                    total_cost=total_cost,
                    round_number=round_number,
                )

                logger.info(
                    f"Persisted partial costs for paused session {session_id}: "
                    f"${total_cost:.4f} (phase={phase}, round={round_number})"
                )
            else:
                logger.debug(
                    f"No costs to persist for paused session {session_id} (total_cost={total_cost})"
                )

        except Exception as e:
            logger.warning(f"Failed to persist partial costs for {session_id}: {e}")

    async def _verify_event_persistence(self, session_id: str) -> None:
        """Verify that events were persisted to PostgreSQL by comparing counts with Redis.

        Compares Redis event count (temporary) with PostgreSQL event count (permanent)
        to detect persistence failures. Emits warning events if discrepancies are found.

        Note: Uses deterministic flush completion tracking instead of fixed sleep delay.
        Falls back to legacy delay if flush tracking times out. Includes retry logic
        to handle race conditions between final flush and verification.

        Args:
            session_id: Session identifier
        """
        try:
            # First, force-flush any pending events in the batcher
            await flush_batcher()

            # Wait for all pending flushes to complete (deterministic)
            # This replaces the non-deterministic asyncio.sleep() delay
            flush_completed = await wait_for_all_flushes(timeout=5.0)
            if not flush_completed:
                logger.warning(
                    f"[VERIFY] Flush timeout for {session_id}, proceeding with verification "
                    f"(some events may not have persisted yet)"
                )

            redis_event_count = self.publisher.redis.llen(f"events_history:{session_id}")
            pg_events = self.session_repo.get_events(session_id)
            pg_event_count = len(pg_events)

            # If mismatch detected, retry with exponential backoff to handle race condition
            max_retries = 3
            retry_delay = 0.5  # seconds (will double each retry: 0.5, 1.0, 2.0)
            for retry in range(max_retries):
                if pg_event_count >= redis_event_count:
                    break
                current_delay = retry_delay * (2**retry)  # Exponential backoff
                logger.info(
                    f"[VERIFY] Mismatch for {session_id} (attempt {retry + 1}/{max_retries}): "
                    f"Redis={redis_event_count}, PostgreSQL={pg_event_count}, "
                    f"retrying in {current_delay}s..."
                )
                await asyncio.sleep(current_delay)
                pg_events = self.session_repo.get_events(session_id)
                pg_event_count = len(pg_events)

            if pg_event_count < redis_event_count:
                log_error(
                    logger,
                    ErrorCode.DB_WRITE_ERROR,
                    f"EVENT PERSISTENCE VERIFICATION FAILED for {session_id}:\n"
                    f"  Redis: {redis_event_count} events\n"
                    f"  PostgreSQL: {pg_event_count} events\n"
                    f"  MISSING: {redis_event_count - pg_event_count} events\n"
                    f"This session will have incomplete history after Redis expires!",
                    session_id=session_id,
                    redis_events=redis_event_count,
                    postgres_events=pg_event_count,
                )
                # Emit warning event to frontend
                self.publisher.publish_event(
                    session_id=session_id,
                    event_type="persistence_verification_warning",
                    data={
                        "redis_events": redis_event_count,
                        "postgres_events": pg_event_count,
                        "missing_events": redis_event_count - pg_event_count,
                        "message": "Some events may not have persisted to database",
                    },
                )
            elif pg_event_count == 0 and redis_event_count > 0:
                logger.critical(
                    f"CRITICAL: Session {session_id} has {redis_event_count} events in "
                    f"Redis but ZERO in PostgreSQL! All events will be lost!"
                )
            else:
                logger.info(
                    f"Event persistence verified for {session_id}: "
                    f"{pg_event_count} events in PostgreSQL"
                )
        except Exception as verify_error:
            log_error(
                logger,
                ErrorCode.DB_QUERY_ERROR,
                f"Failed to verify event persistence for {session_id}: {verify_error}",
                session_id=session_id,
            )

    async def _publish_contribution(
        self,
        session_id: str,
        contrib: dict,
        round_number: int,
        sub_problem_index: int = 0,
        personas: list = None,
        summary: dict | None = None,
    ) -> None:
        """Publish a contribution event with AI summary.

        Args:
            session_id: Session identifier
            contrib: Contribution dict/object
            round_number: Current round number
            sub_problem_index: Sub-problem index for tab filtering
            personas: List of personas for looking up domain expertise
            summary: Pre-computed summary (skips LLM call if provided)
        """
        # Extract contribution fields
        if hasattr(contrib, "persona_code"):
            persona_code = contrib.persona_code
            persona_name = contrib.persona_name
            content = contrib.content
        else:
            persona_code = contrib.get("persona_code", "")
            persona_name = contrib.get("persona_name", "")
            content = contrib.get("content", "")

        logger.info(
            f"[CONTRIBUTION DEBUG] Processing contribution | "
            f"persona_code={persona_code} | "
            f"personas_provided={'Yes' if personas else 'No'} | "
            f"personas_count={len(personas) if personas else 0}"
        )

        # Find matching persona to get domain_expertise and archetype (role)
        domain_expertise = []
        archetype = ""
        if personas:
            for persona in personas:
                p_code = persona.code if hasattr(persona, "code") else persona.get("code")
                if p_code == persona_code:
                    domain_expertise = (
                        persona.domain_expertise
                        if hasattr(persona, "domain_expertise")
                        else persona.get("domain_expertise", [])
                    )
                    archetype = (
                        persona.archetype
                        if hasattr(persona, "archetype")
                        else persona.get("archetype", "")
                    )
                    logger.info(
                        f"[CONTRIBUTION DEBUG] Found matching persona | "
                        f"persona_code={persona_code} | "
                        f"archetype={archetype} | "
                        f"domain_expertise={domain_expertise}"
                    )
                    break
        else:
            logger.warning(
                f"[CONTRIBUTION DEBUG] No personas list provided for persona_code={persona_code}"
            )

        if not archetype:
            logger.warning(
                f"[CONTRIBUTION DEBUG] No archetype found for persona_code={persona_code} | "
                f"personas_available={[p.code if hasattr(p, 'code') else p.get('code') for p in personas] if personas else []}"
            )

        # Use pre-computed summary or generate one (fallback for direct calls)
        if summary is None:
            summary = await self.summarizer.summarize(content, persona_name)

        logger.info(
            f"[CONTRIBUTION DEBUG] Summary generation result | "
            f"persona_name={persona_name} | "
            f"summary_generated={'Yes' if summary else 'No'} | "
            f"has_concise={bool(summary and summary.get('concise')) if summary else False}"
        )

        self.publisher.publish_event(
            session_id,
            "contribution",
            {
                "persona_code": persona_code,
                "persona_name": persona_name,
                "archetype": archetype,  # NEW: Expert's role/title (e.g., "Angel Investor")
                "domain_expertise": domain_expertise,  # NEW: Expert's areas of expertise
                "content": content,  # Keep full content for reference
                "summary": summary,  # NEW: Structured summary for compact display
                "round": round_number,
                "contribution_type": "initial" if round_number == 1 else "parallel",
                "sub_problem_index": sub_problem_index,  # For tab filtering
            },
        )
