"""Event collector that wraps LangGraph astream_events and publishes to Redis.

Provides:
- EventCollector: Wraps graph execution and publishes all events to Redis PubSub
"""

import asyncio
import logging
from typing import Any

from anthropic import AsyncAnthropic

from backend.api.dependencies import get_redis_manager
from backend.api.event_extractors import get_event_registry
from backend.api.event_publisher import EventPublisher
from bo1.config import get_settings, resolve_model_alias
from bo1.llm.context import get_cost_context
from bo1.llm.cost_tracker import CostTracker
from bo1.state.postgres_manager import (
    save_session_synthesis,
    update_session_phase,
    update_session_status,
)
from bo1.utils.json_parsing import parse_json_with_fallback

logger = logging.getLogger(__name__)


class EventCollector:
    """Collects LangGraph events and publishes them to Redis for SSE streaming.

    This class wraps LangGraph's astream_events() iterator and maps node
    completions to specific event types, publishing them to Redis PubSub
    for real-time streaming to web clients.

    Examples:
        >>> from backend.api.dependencies import get_event_publisher
        >>> from bo1.graph.config import create_deliberation_graph
        >>> collector = EventCollector(get_event_publisher())
        >>> final_state = await collector.collect_and_publish(
        ...     session_id="bo1_abc123",
        ...     graph=graph,
        ...     initial_state=state,
        ...     config=config
        ... )
    """

    # Node handler registry: maps node names to handler method names
    NODE_HANDLERS: dict[str, str] = {
        "decompose": "_handle_decomposition",
        "identify_gaps": "_handle_identify_gaps",
        "select_personas": "_handle_persona_selection",
        "initial_round": "_handle_initial_round",
        "facilitator_decide": "_handle_facilitator_decision",
        "parallel_round": "_handle_parallel_round",
        "moderator_intervene": "_handle_moderator",
        "check_convergence": "_handle_convergence",
        "vote": "_handle_voting",
        "synthesize": "_handle_synthesis",
        "next_subproblem": "_handle_subproblem_complete",
        "meta_synthesis": "_handle_meta_synthesis",
        "meta_synthesize": "_handle_meta_synthesis",  # Support both node names
        "research": "_handle_research",  # P2-006: Research results
    }

    def __init__(self, publisher: EventPublisher) -> None:
        """Initialize EventCollector.

        Args:
            publisher: EventPublisher instance for publishing to Redis
        """
        self.publisher = publisher
        # Initialize Anthropic client for AI summarization
        settings = get_settings()
        self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    def _emit_working_status(
        self,
        session_id: str,
        phase: str,
        estimated_duration: str,
        sub_problem_index: int = 0,
    ) -> None:
        """Emit a working_status event to indicate ongoing processing.

        Helper method to eliminate duplication of working status event emission.
        Used before long-running operations (voting, synthesis, rounds) to provide
        user feedback that the system is actively processing.

        Args:
            session_id: Session identifier
            phase: Human-readable description of current phase (e.g., "Experts finalizing recommendations...")
            estimated_duration: Estimated time for this phase (e.g., "10-15 seconds")
            sub_problem_index: Sub-problem index for tab filtering (default: 0)
        """
        self.publisher.publish_event(
            session_id,
            "working_status",
            {
                "phase": phase,
                "estimated_duration": estimated_duration,
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

    def _extract_persona_dict(self, persona: Any) -> dict[str, Any]:
        """Extract persona fields into a dictionary.

        Helper method to eliminate duplication of persona attribute extraction.
        Handles both Pydantic models (via hasattr/getattr) and dicts (via .get()).

        Args:
            persona: Persona object (Pydantic model or dict)

        Returns:
            Dictionary with persona fields (code, name, archetype, display_name, domain_expertise)
        """
        from backend.api.event_extractors import get_field_safe

        return {
            "code": get_field_safe(persona, "code"),
            "name": get_field_safe(persona, "name"),
            "archetype": get_field_safe(persona, "archetype", ""),
            "display_name": get_field_safe(persona, "display_name", ""),
            "domain_expertise": get_field_safe(persona, "domain_expertise", []),
        }

    def _mark_session_failed(self, session_id: str, error: Exception) -> None:
        """Mark session as failed with error handling.

        Consolidates duplicate error handling pattern for session failures.
        Publishes error event and updates session status in PostgreSQL.

        Args:
            session_id: Session identifier
            error: The exception that caused the failure
        """
        # Publish error event to SSE stream
        self.publisher.publish_event(
            session_id,
            "error",
            {
                "error": str(error),
                "error_type": type(error).__name__,
            },
        )

        # Update session status to 'failed' in PostgreSQL
        try:
            update_session_status(session_id=session_id, status="failed")
        except Exception as db_error:
            logger.error(f"Failed to update session {session_id} status to failed: {db_error}")

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
                sub_problem_index = output.get("sub_problem_index", 0)
                data["sub_problem_index"] = sub_problem_index

                logger.info(
                    f"[EVENT DEBUG] Publishing {event_type} | sub_problem_index={sub_problem_index} | data keys: {list(data.keys())}"
                )
                self.publisher.publish_event(session_id, event_type, data)
            else:
                # Issue #3 fix: Publish error event when extractor fails
                error_msg = f"Event extraction failed for {event_type}"
                logger.error(
                    f"[EVENT ERROR] {error_msg} (registry_key={registry_key}). Output keys: {list(output.keys())}"
                )
                # Publish error event so UI knows something went wrong
                self.publisher.publish_event(
                    session_id,
                    "error",
                    {
                        "error": error_msg,
                        "error_type": "EventExtractionError",
                        "event_type_attempted": event_type,
                        "sub_problem_index": output.get("sub_problem_index", 0),
                    },
                )
        except Exception as e:
            # Issue #3 fix: Publish error event instead of swallowing the error
            logger.error(
                f"Failed to publish {event_type} for session {session_id}: {e}",
                exc_info=True,
            )
            # Publish error event so frontend can display the failure
            self.publisher.publish_event(
                session_id,
                "error",
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "event_type_attempted": event_type,
                    "sub_problem_index": output.get("sub_problem_index", 0),
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

        Returns:
            Final deliberation state

        Raises:
            Exception: Re-raises any exception from graph execution
        """
        from bo1.feature_flags import USE_SUBGRAPH_DELIBERATION

        if USE_SUBGRAPH_DELIBERATION:
            return await self._collect_with_custom_events(session_id, graph, initial_state, config)
        else:
            return await self._collect_with_astream_events(session_id, graph, initial_state, config)

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
        """
        final_state = None

        try:
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

                # Handle custom events from get_stream_writer()
                if mode == "custom" and isinstance(data, dict) and "event_type" in data:
                    event_type = data.pop("event_type")
                    logger.info(
                        f"[CUSTOM EVENT] {event_type} | sub_problem_index={data.get('sub_problem_index')}"
                    )
                    self.publisher.publish_event(session_id, event_type, data)

                # Handle state updates from nodes
                elif mode == "updates" and node_name:
                    # Dispatch to appropriate handler via registry
                    await self._dispatch_node_handler(node_name, session_id, node_data)

                    # Update final state with the node data
                    final_state = node_data

            # Publish completion event
            if final_state:
                await self._handle_completion(session_id, final_state)

        except Exception as e:
            logger.error(f"Error in custom event collection for session {session_id}: {e}")
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
        """
        final_state = None

        try:
            # Stream events from LangGraph execution
            async for event in graph.astream_events(initial_state, config=config, version="v2"):
                event_type = event.get("event")
                event_name = event.get("name", "")

                # Process node completions (on_chain_end has output data)
                if event_type == "on_chain_end" and "data" in event:
                    output = event.get("data", {}).get("output", {})

                    # Dispatch to appropriate handler via registry
                    if isinstance(output, dict):
                        await self._dispatch_node_handler(event_name, session_id, output)
                        # Capture final state
                        final_state = output

            # Publish completion event
            if final_state:
                await self._handle_completion(session_id, final_state)

        except Exception as e:
            logger.error(f"Error in event collection for session {session_id}: {e}")
            self._mark_session_failed(session_id, e)
            raise

        return final_state

    async def _handle_decomposition(self, session_id: str, output: dict) -> None:
        """Handle decompose node completion."""
        # Update phase in database for dashboard display
        update_session_phase(session_id, "decomposition")

        # P1-004 FIX: Emit working status at START of decomposition
        self._emit_working_status(
            session_id,
            phase="Breaking down your decision into key areas...",
            estimated_duration="5-10 seconds",
            sub_problem_index=output.get("sub_problem_index", 0),
        )

        # ISSUE FIX: Add status message for problem analysis phase
        self._emit_quality_status(
            session_id,
            status="analyzing",
            message="Analyzing problem structure...",
            round_number=0,
            sub_problem_index=output.get("sub_problem_index", 0),
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
            update_session_status(
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
        update_session_phase(session_id, "selection")

        personas = output.get("personas", [])
        persona_recommendations = output.get("persona_recommendations", [])
        sub_problem_index = output.get("sub_problem_index", 0)

        # P1-004 FIX: Emit working status at START of persona selection
        self._emit_working_status(
            session_id,
            phase="Assembling the right experts for your question...",
            estimated_duration="3-5 seconds",
            sub_problem_index=sub_problem_index,
        )

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
            persona_dict = self._extract_persona_dict(persona)

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
        update_session_phase(session_id, "exploration")

        # Extract sub_problem_index for tab filtering
        sub_problem_index = output.get("sub_problem_index", 0)

        # Get personas for archetype/domain_expertise lookup
        personas = output.get("personas", [])

        # P1-004 FIX (MAJOR GAP): Emit working status at START of initial round
        # This is the longest phase (15-30s) and was previously missing status updates
        self._emit_working_status(
            session_id,
            phase="Experts are sharing their initial perspectives...",
            estimated_duration="15-30 seconds",
            sub_problem_index=sub_problem_index,
        )

        # ISSUE FIX: Emit initial discussion quality status at START of round 1
        # This provides early UX feedback that quality tracking has begun
        self._emit_quality_status(
            session_id,
            status="analyzing",
            message="Gathering expert perspectives...",
            round_number=1,
            sub_problem_index=sub_problem_index,
        )

        # Publish individual contributions
        contributions = output.get("contributions", [])
        for contrib in contributions:
            await self._publish_contribution(
                session_id,
                contrib,
                round_number=1,
                sub_problem_index=sub_problem_index,
                personas=personas,
            )

    async def _handle_facilitator_decision(self, session_id: str, output: dict) -> None:
        """Handle facilitator_decide node completion."""
        # P1-004 FIX: Emit working status for facilitator decision
        self._emit_working_status(
            session_id,
            phase="Guiding the discussion deeper...",
            estimated_duration="2-4 seconds",
            sub_problem_index=output.get("sub_problem_index", 0),
        )
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
        sub_problem_index = output.get("sub_problem_index", 0)

        # Update phase in database for dashboard display
        update_session_phase(session_id, current_phase)
        personas = output.get("personas", [])

        # Extract experts for the just-completed round
        # round_number has already been incremented, so we look at -1
        completed_round = round_number - 1
        experts_this_round = experts_per_round[-1] if experts_per_round else []

        # AUDIT FIX (Issue #4): Emit working status BEFORE round starts
        self._emit_working_status(
            session_id,
            phase=f"Experts are discussing (round {completed_round})...",
            estimated_duration="8-12 seconds",
            sub_problem_index=sub_problem_index,
        )

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

        # Emit contribution events for each contribution in this round
        for contribution in contributions:
            contrib_round = (
                contribution.round_number
                if hasattr(contribution, "round_number")
                else contribution.get("round_number", 0)
            )

            # Only publish contributions from the just-completed round
            if contrib_round == completed_round:
                await self._publish_contribution(
                    session_id, contribution, completed_round, sub_problem_index, personas
                )

    async def _handle_moderator(self, session_id: str, output: dict) -> None:
        """Handle moderator_intervene node completion."""
        # P1-004 FIX: Emit working status for moderator intervention
        self._emit_working_status(
            session_id,
            phase="Ensuring balanced perspectives...",
            estimated_duration="2-4 seconds",
            sub_problem_index=output.get("sub_problem_index", 0),
        )
        await self._publish_node_event(session_id, output, "moderator_intervention")

    async def _handle_convergence(self, session_id: str, output: dict) -> None:
        """Handle check_convergence node completion."""
        # P1-004 FIX: Emit working status for convergence check
        self._emit_working_status(
            session_id,
            phase="Checking for emerging agreement...",
            estimated_duration="2-3 seconds",
            sub_problem_index=output.get("sub_problem_index", 0),
        )
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
                    "sub_problem_index": output.get("sub_problem_index", 0),
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
        update_session_phase(session_id, "voting")

        # AUDIT FIX (Issue #4): Emit working status BEFORE voting starts
        self._emit_working_status(
            session_id,
            phase="Experts are finalizing their recommendations...",
            estimated_duration="10-15 seconds",
            sub_problem_index=output.get("sub_problem_index", 0),
        )
        await self._publish_node_event(session_id, output, "voting_complete", registry_key="voting")

    async def _handle_synthesis(self, session_id: str, output: dict) -> None:
        """Handle synthesize node completion."""
        # Update phase in database for dashboard display
        update_session_phase(session_id, "synthesis")

        # AUDIT FIX (Issue #4): Emit working status BEFORE synthesis starts
        self._emit_working_status(
            session_id,
            phase="Bringing together the key insights...",
            estimated_duration="5-8 seconds",
            sub_problem_index=output.get("sub_problem_index", 0),
        )
        # Publish event
        await self._publish_node_event(session_id, output, "synthesis_complete")

        # P2-004: Emit expert summaries event if expert_summaries are available
        expert_summaries = output.get("expert_summaries", {})
        if expert_summaries:
            current_sub_problem = output.get("current_sub_problem")
            expert_summaries_event = {
                "expert_summaries": expert_summaries,
                "sub_problem_index": output.get("sub_problem_index", 0),
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
                save_session_synthesis(session_id, synthesis_text)
                logger.info(f"Saved synthesis to PostgreSQL for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to save synthesis to PostgreSQL for {session_id}: {e}")

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
        # AUDIT FIX (Issue #4): Emit working status BEFORE meta-synthesis starts
        self._emit_working_status(
            session_id,
            phase="Crafting your final recommendation...",
            estimated_duration="8-12 seconds",
        )
        # Publish event
        await self._publish_node_event(session_id, output, "meta_synthesis_complete")

        # Save meta-synthesis to PostgreSQL for long-term storage
        synthesis_text = output.get("meta_synthesis")
        if synthesis_text:
            try:
                save_session_synthesis(session_id, synthesis_text)
                logger.info(f"Saved meta-synthesis to PostgreSQL for session {session_id}")
            except Exception as e:
                logger.error(f"Failed to save meta-synthesis to PostgreSQL for {session_id}: {e}")

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
            # Still verify event persistence
            await self._verify_event_persistence(session_id)
            return

        # Publish cost breakdown
        self._publish_cost_breakdown(session_id, final_state)

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

        # Additional safety: check current phase in PostgreSQL to prevent race conditions
        # This guards against: graph completes with different stop_reason but phase was set
        # to clarification_needed by _handle_identify_gaps earlier
        try:
            from bo1.state.postgres_manager import get_session

            current_session = get_session(session_id)
            if current_session:
                current_phase = current_session.get("phase")
                if current_phase in ("clarification_needed", "context_insufficient"):
                    logger.warning(
                        f"Session {session_id} has phase='{current_phase}' in DB - "
                        f"not overwriting with completed status (stop_reason={stop_reason})"
                    )
                    return
        except Exception as e:
            logger.warning(f"Failed to check current session phase for {session_id}: {e}")

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
                update_session_status(
                    session_id=session_id,
                    status="completed",
                    phase=phase,
                    total_cost=total_cost,
                    round_number=round_number,
                    synthesis_text=synthesis_text,
                    final_recommendation=final_recommendation,
                )
                status_update_success = True
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
                    logger.error(
                        f"CRITICAL: Failed to update session status after 3 attempts for "
                        f"{session_id}: {e}\n"
                        f"Session completed but status may be inconsistent!"
                    )

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
                logger.error(f"Failed to emit status error event: {emit_error}")

    async def _verify_event_persistence(self, session_id: str) -> None:
        """Verify that events were persisted to PostgreSQL by comparing counts with Redis.

        Compares Redis event count (temporary) with PostgreSQL event count (permanent)
        to detect persistence failures. Emits warning events if discrepancies are found.

        Args:
            session_id: Session identifier
        """
        try:
            from bo1.state.postgres_manager import get_session_events

            redis_event_count = self.publisher.redis.llen(f"events_history:{session_id}")
            pg_events = get_session_events(session_id)
            pg_event_count = len(pg_events)

            if pg_event_count < redis_event_count:
                logger.error(
                    f"EVENT PERSISTENCE VERIFICATION FAILED for {session_id}:\n"
                    f"  Redis: {redis_event_count} events\n"
                    f"  PostgreSQL: {pg_event_count} events\n"
                    f"  MISSING: {redis_event_count - pg_event_count} events\n"
                    f"This session will have incomplete history after Redis expires!"
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
            logger.error(f"Failed to verify event persistence for {session_id}: {verify_error}")

    async def _summarize_contribution(self, content: str, persona_name: str) -> dict | None:
        """Summarize expert contribution into structured insights using Haiku 4.5.

        Uses Claude Haiku 4.5 for cost-effective summarization (~$0.001 per contribution).

        Args:
            content: Full expert contribution (200-500 words)
            persona_name: Expert name for context

        Returns:
            Dict with looking_for, value_added, concerns, questions, or None if summarization fails
        """
        from bo1.prompts.contribution_summary_prompts import compose_contribution_summary_request

        try:
            prompt = compose_contribution_summary_request(content, persona_name)

            ctx = get_cost_context()
            model = resolve_model_alias("haiku")

            with CostTracker.track_call(
                provider="anthropic",
                operation_type="completion",
                model_name=model,
                session_id=ctx.get("session_id"),
                user_id=ctx.get("user_id"),
                node_name="contribution_summarizer",
                phase=ctx.get("phase"),
                persona_name=persona_name,
                round_number=ctx.get("round_number"),
                sub_problem_index=ctx.get("sub_problem_index"),
            ) as cost_record:
                response = await self.anthropic_client.messages.create(
                    model=model,
                    max_tokens=500,
                    messages=[
                        {"role": "user", "content": prompt},
                        {"role": "assistant", "content": "{"},  # Prefill to force JSON
                    ],
                )

                # Track token usage
                cost_record.input_tokens = response.usage.input_tokens
                cost_record.output_tokens = response.usage.output_tokens

            # Extract JSON from response - prepend opening brace from prefill
            response_text = response.content[0].text

            # Strategy 1: Try parse_json_with_fallback with prefill
            summary, parse_errors = parse_json_with_fallback(
                content=response_text,
                prefill="{",
                context=f"contribution summary for {persona_name}",
                logger=logger,
            )

            if summary is not None:
                return self._validate_summary_schema(summary)

            # Strategy 2: Extract first complete JSON object using brace counting
            # This handles cases where LLM returns multiple JSON objects or trailing text
            summary = self._extract_first_json_object("{" + response_text)
            if summary is not None:
                logger.debug(f"Extracted summary via brace counting for {persona_name}")
                return self._validate_summary_schema(summary)

            # Strategy 3: Return fallback summary
            logger.warning(
                f"Failed to parse summary for {persona_name}: {parse_errors}. Using fallback."
            )
            return self._create_fallback_summary(persona_name, content)

        except Exception as e:
            logger.error(f"Failed to summarize contribution for {persona_name}: {e}")
            return self._create_fallback_summary(persona_name, content)

    def _extract_first_json_object(self, text: str) -> dict | None:
        """Extract first complete JSON object using brace counting.

        Handles cases where LLM returns multiple JSON objects or trailing text
        by counting opening/closing braces to find the first complete object.

        Args:
            text: Text potentially containing JSON object(s)

        Returns:
            Parsed dict if found, None otherwise
        """
        import json

        try:
            start = text.find("{")
            if start == -1:
                return None

            brace_count = 0
            in_string = False
            escape_next = False

            for i, char in enumerate(text[start:], start):
                if escape_next:
                    escape_next = False
                    continue
                if char == "\\":
                    escape_next = True
                    continue
                if char == '"' and not escape_next:
                    in_string = not in_string
                    continue
                if in_string:
                    continue
                if char == "{":
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0:
                        json_str = text[start : i + 1]
                        return json.loads(json_str)

            return None
        except json.JSONDecodeError:
            return None

    def _validate_summary_schema(self, summary: dict) -> dict:
        """Validate summary has required fields, fill in defaults.

        Args:
            summary: Parsed summary dict

        Returns:
            Summary with all required fields (with defaults if missing)
        """
        summary.setdefault("concise", "")
        summary.setdefault("looking_for", "")
        summary.setdefault("value_added", "")
        summary.setdefault("concerns", [])
        summary.setdefault("questions", [])

        # Ensure arrays are actually arrays
        if not isinstance(summary.get("concerns"), list):
            summary["concerns"] = []
        if not isinstance(summary.get("questions"), list):
            summary["questions"] = []

        return summary

    def _create_fallback_summary(self, persona_name: str, content: str) -> dict:
        """Create a basic fallback summary when parsing fails.

        Args:
            persona_name: Expert name
            content: Original contribution content

        Returns:
            Basic summary dict with minimal information
        """
        # Extract first sentence as a simple summary
        first_sentence = content.split(".")[0][:100] if content else ""
        return {
            "concise": f"{first_sentence}..." if first_sentence else f"Analysis by {persona_name}",
            "looking_for": "Evaluating the situation",
            "value_added": "Expert perspective",
            "concerns": [],
            "questions": [],
            "parse_error": True,
        }

    async def _publish_contribution(
        self,
        session_id: str,
        contrib: dict,
        round_number: int,
        sub_problem_index: int = 0,
        personas: list = None,
    ) -> None:
        """Publish a contribution event with AI summary.

        Args:
            session_id: Session identifier
            contrib: Contribution dict/object
            round_number: Current round number
            sub_problem_index: Sub-problem index for tab filtering
            personas: List of personas for looking up domain expertise
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

        # Generate AI summary for better UX
        summary = await self._summarize_contribution(content, persona_name)

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
