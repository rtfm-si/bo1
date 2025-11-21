"""Event collector that wraps LangGraph astream_events and publishes to Redis.

Provides:
- EventCollector: Wraps graph execution and publishes all events to Redis PubSub
"""

import logging
from typing import Any

from backend.api.event_publisher import EventPublisher
from bo1.models.problem import SubProblem

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

    def __init__(self, publisher: EventPublisher) -> None:
        """Initialize EventCollector.

        Args:
            publisher: EventPublisher instance for publishing to Redis
        """
        self.publisher = publisher

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
        final_state = None

        try:
            # Stream events from LangGraph execution
            async for event in graph.astream_events(initial_state, config=config, version="v2"):
                event_type = event.get("event")
                event_name = event.get("name", "")

                # Process node completions (on_chain_end has output data)
                if event_type == "on_chain_end" and "data" in event:
                    output = event.get("data", {}).get("output", {})

                    # Map node names to event handlers
                    if event_name == "decompose" and isinstance(output, dict):
                        await self._handle_decomposition(session_id, output)

                    elif event_name == "select_personas" and isinstance(output, dict):
                        await self._handle_persona_selection(session_id, output)

                    elif event_name == "initial_round" and isinstance(output, dict):
                        await self._handle_initial_round(session_id, output)

                    elif event_name == "facilitator_decide" and isinstance(output, dict):
                        await self._handle_facilitator_decision(session_id, output)

                    elif event_name == "persona_contribute" and isinstance(output, dict):
                        await self._handle_contribution(session_id, output)

                    elif event_name == "moderator_intervene" and isinstance(output, dict):
                        await self._handle_moderator(session_id, output)

                    elif event_name == "check_convergence" and isinstance(output, dict):
                        await self._handle_convergence(session_id, output)

                    elif event_name == "vote" and isinstance(output, dict):
                        await self._handle_voting(session_id, output)

                    elif event_name == "synthesize" and isinstance(output, dict):
                        await self._handle_synthesis(session_id, output)

                    elif event_name == "next_subproblem" and isinstance(output, dict):
                        await self._handle_subproblem_complete(session_id, output)

                    elif event_name == "meta_synthesize" and isinstance(output, dict):
                        await self._handle_meta_synthesis(session_id, output)

                    # Capture final state
                    if isinstance(output, dict):
                        final_state = output

            # Publish completion event
            if final_state:
                await self._handle_completion(session_id, final_state)

        except Exception as e:
            logger.error(f"Error in event collection for session {session_id}: {e}")
            # Publish error event
            self.publisher.publish_event(
                session_id,
                "error",
                {
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
            )
            raise

        return final_state

    async def _handle_decomposition(self, session_id: str, output: dict) -> None:
        """Handle decompose node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        # Publish decomposition started event
        self.publisher.publish_event(session_id, "decomposition_started", {})

        # Extract sub-problems from problem
        problem = output.get("problem")
        if problem and hasattr(problem, "sub_problems"):
            sub_problems = problem.sub_problems

            # Convert SubProblem objects to dicts for JSON serialization
            sub_problems_dicts = []
            for sp in sub_problems:
                if isinstance(sp, SubProblem):
                    sub_problems_dicts.append(
                        {
                            "id": sp.id,
                            "goal": sp.goal,
                            "rationale": getattr(sp, "rationale", ""),
                            "complexity_score": sp.complexity_score,
                            "dependencies": sp.dependencies,
                        }
                    )
                elif isinstance(sp, dict):
                    sub_problems_dicts.append(sp)

            # Publish decomposition complete event
            self.publisher.publish_event(
                session_id,
                "decomposition_complete",
                {
                    "sub_problems": sub_problems_dicts,
                    "count": len(sub_problems_dicts),
                },
            )

    async def _handle_persona_selection(self, session_id: str, output: dict) -> None:
        """Handle select_personas node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        # Publish persona selection started event
        self.publisher.publish_event(session_id, "persona_selection_started", {})

        # Extract personas and recommendations
        personas = output.get("personas", [])
        persona_recommendations = output.get("persona_recommendations", [])

        # Publish individual persona selected events
        for i, persona in enumerate(personas):
            persona_dict = {
                "code": persona.code if hasattr(persona, "code") else persona.get("code"),
                "name": persona.name if hasattr(persona, "name") else persona.get("name"),
                "display_name": (
                    persona.display_name
                    if hasattr(persona, "display_name")
                    else persona.get("display_name", "")
                ),
                "domain_expertise": (
                    persona.domain_expertise
                    if hasattr(persona, "domain_expertise")
                    else persona.get("domain_expertise", [])
                ),
            }

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
                },
            )

        # Publish persona selection complete event
        persona_codes = [p.code if hasattr(p, "code") else p.get("code") for p in personas]
        self.publisher.publish_event(
            session_id,
            "persona_selection_complete",
            {"personas": persona_codes, "count": len(persona_codes)},
        )

        # Check if this is a multi-sub-problem scenario and publish sub-problem context
        sub_problem_index = output.get("sub_problem_index", 0)
        current_sub_problem = output.get("current_sub_problem")
        problem = output.get("problem")

        if problem and hasattr(problem, "sub_problems") and len(problem.sub_problems) > 1:
            if current_sub_problem:
                self.publisher.publish_event(
                    session_id,
                    "subproblem_started",
                    {
                        "sub_problem_index": sub_problem_index,
                        "sub_problem_id": (
                            current_sub_problem.id
                            if hasattr(current_sub_problem, "id")
                            else current_sub_problem.get("id", "")
                        ),
                        "goal": (
                            current_sub_problem.goal
                            if hasattr(current_sub_problem, "goal")
                            else current_sub_problem.get("goal", "")
                        ),
                        "total_sub_problems": len(problem.sub_problems),
                    },
                )

    async def _handle_initial_round(self, session_id: str, output: dict) -> None:
        """Handle initial_round node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        personas = output.get("personas", [])
        persona_codes = [p.code if hasattr(p, "code") else p.get("code") for p in personas]

        # Publish initial round started event
        self.publisher.publish_event(
            session_id,
            "initial_round_started",
            {"experts": persona_codes},
        )

        # Publish individual contributions
        contributions = output.get("contributions", [])
        for contrib in contributions:
            await self._publish_contribution(session_id, contrib, round_number=1)

    async def _handle_facilitator_decision(self, session_id: str, output: dict) -> None:
        """Handle facilitator_decide node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        decision = output.get("facilitator_decision")
        round_number = output.get("round_number", 1)

        if decision:
            # Extract decision fields
            action = decision.get("action", "")
            reasoning = decision.get("reasoning", "")
            next_speaker = decision.get("next_speaker")
            moderator_type = decision.get("moderator_type")
            research_query = decision.get("research_query")

            # Publish facilitator decision event
            data = {
                "action": action,
                "reasoning": reasoning[:200] if len(reasoning) > 200 else reasoning,
                "round": round_number,
            }

            if next_speaker:
                data["next_speaker"] = next_speaker
            if moderator_type:
                data["moderator_type"] = moderator_type
            if research_query:
                data["research_query"] = research_query

            self.publisher.publish_event(session_id, "facilitator_decision", data)

    async def _handle_contribution(self, session_id: str, output: dict) -> None:
        """Handle persona_contribute node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        contributions = output.get("contributions", [])
        round_number = output.get("round_number", 1)

        # Publish the newest contribution (last in list)
        if contributions:
            await self._publish_contribution(session_id, contributions[-1], round_number)

    async def _handle_moderator(self, session_id: str, output: dict) -> None:
        """Handle moderator_intervene node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        contributions = output.get("contributions", [])
        round_number = output.get("round_number", 1)

        # Last contribution is the moderator intervention
        if contributions:
            contrib = contributions[-1]
            moderator_type = contrib.get("persona_code", "moderator")
            content = contrib.get("content", "")

            self.publisher.publish_event(
                session_id,
                "moderator_intervention",
                {
                    "moderator_type": moderator_type,
                    "content": content,
                    "trigger_reason": "Facilitator requested intervention",
                    "round": round_number,
                },
            )

    async def _handle_convergence(self, session_id: str, output: dict) -> None:
        """Handle check_convergence node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        should_stop = output.get("should_stop", False)
        stop_reason = output.get("stop_reason")
        round_number = output.get("round_number", 1)
        max_rounds = output.get("max_rounds", 10)

        # Get convergence score from metrics
        metrics = output.get("metrics", {})
        if hasattr(metrics, "convergence_score"):
            convergence_score = metrics.convergence_score or 0.0
        else:
            convergence_score = (
                metrics.get("convergence_score", 0.0) if isinstance(metrics, dict) else 0.0
            )

        self.publisher.publish_event(
            session_id,
            "convergence",
            {
                "converged": should_stop,
                "score": convergence_score,
                "threshold": 0.85,
                "should_stop": should_stop,
                "stop_reason": stop_reason,
                "round": round_number,
                "max_rounds": max_rounds,
            },
        )

    async def _handle_voting(self, session_id: str, output: dict) -> None:
        """Handle vote node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        personas = output.get("personas", [])
        persona_codes = [p.code if hasattr(p, "code") else p.get("code") for p in personas]

        # Publish voting started event
        self.publisher.publish_event(
            session_id,
            "voting_started",
            {"experts": persona_codes},
        )

        # Publish individual votes/recommendations
        votes = output.get("votes", [])
        for vote in votes:
            # Extract vote fields (using recommendation system)
            persona_code = vote.get("persona_code", "")
            persona_name = vote.get("persona_name", "")
            recommendation = vote.get("recommendation", "")
            confidence = vote.get("confidence", 0.0)
            reasoning = vote.get("reasoning", "")
            conditions = vote.get("conditions", [])

            self.publisher.publish_event(
                session_id,
                "persona_vote",
                {
                    "persona_code": persona_code,
                    "persona_name": persona_name,
                    "recommendation": recommendation,
                    "confidence": confidence,
                    "reasoning": reasoning[:150] if len(reasoning) > 150 else reasoning,
                    "conditions": conditions,
                },
            )

        # Publish voting complete event
        # Determine consensus level based on confidence scores
        if votes:
            avg_confidence = sum(v.get("confidence", 0.0) for v in votes) / len(votes)
            if avg_confidence >= 0.8:
                consensus_level = "strong"
            elif avg_confidence >= 0.6:
                consensus_level = "moderate"
            else:
                consensus_level = "weak"
        else:
            consensus_level = "unknown"

        self.publisher.publish_event(
            session_id,
            "voting_complete",
            {
                "votes_count": len(votes),
                "consensus_level": consensus_level,
            },
        )

    async def _handle_synthesis(self, session_id: str, output: dict) -> None:
        """Handle synthesize node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        # Publish synthesis started event
        self.publisher.publish_event(session_id, "synthesis_started", {})

        # Extract synthesis
        synthesis = output.get("synthesis", "")
        word_count = len(synthesis.split()) if synthesis else 0

        # Publish synthesis complete event
        self.publisher.publish_event(
            session_id,
            "synthesis_complete",
            {
                "synthesis": synthesis,
                "word_count": word_count,
            },
        )

    async def _handle_subproblem_complete(self, session_id: str, output: dict) -> None:
        """Handle next_subproblem node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        # Extract sub-problem result info
        sub_problem_index = output.get("sub_problem_index", 0)
        current_sub_problem = output.get("current_sub_problem")

        if current_sub_problem:
            # Get metrics for cost and duration
            metrics = output.get("metrics", {})
            if hasattr(metrics, "total_cost"):
                total_cost = metrics.total_cost
            else:
                total_cost = metrics.get("total_cost", 0.0) if isinstance(metrics, dict) else 0.0

            # Extract persona codes
            personas = output.get("personas", [])
            persona_codes = [p.code if hasattr(p, "code") else p.get("code") for p in personas]

            # Count contributions
            contributions = output.get("contributions", [])
            contribution_count = len(contributions)

            # Extract sub-problem details
            sp_id = (
                current_sub_problem.id
                if hasattr(current_sub_problem, "id")
                else current_sub_problem.get("id", "")
            )
            sp_goal = (
                current_sub_problem.goal
                if hasattr(current_sub_problem, "goal")
                else current_sub_problem.get("goal", "")
            )

            self.publisher.publish_event(
                session_id,
                "subproblem_complete",
                {
                    "sub_problem_index": sub_problem_index,
                    "sub_problem_id": sp_id,
                    "goal": sp_goal,
                    "cost": total_cost,
                    "duration_seconds": 0.0,  # TODO: Track duration
                    "expert_panel": persona_codes,
                    "contribution_count": contribution_count,
                },
            )

    async def _handle_meta_synthesis(self, session_id: str, output: dict) -> None:
        """Handle meta_synthesize node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        # Extract sub-problem results
        sub_problem_results = output.get("sub_problem_results", [])
        contributions = output.get("contributions", [])

        # Get metrics for cost
        metrics = output.get("metrics", {})
        if hasattr(metrics, "total_cost"):
            total_cost = metrics.total_cost
        else:
            total_cost = metrics.get("total_cost", 0.0) if isinstance(metrics, dict) else 0.0

        # Publish meta-synthesis started event
        self.publisher.publish_event(
            session_id,
            "meta_synthesis_started",
            {
                "sub_problem_count": len(sub_problem_results),
                "total_contributions": len(contributions),
                "total_cost": total_cost,
            },
        )

        # Extract synthesis
        synthesis = output.get("synthesis", "")
        word_count = len(synthesis.split()) if synthesis else 0

        # Publish meta-synthesis complete event
        self.publisher.publish_event(
            session_id,
            "meta_synthesis_complete",
            {
                "synthesis": synthesis,
                "word_count": word_count,
            },
        )

    async def _handle_completion(self, session_id: str, final_state: dict) -> None:
        """Handle deliberation completion.

        Args:
            session_id: Session identifier
            final_state: Final graph state
        """
        # Extract phase costs
        phase_costs = final_state.get("phase_costs", {})

        # Get metrics
        metrics = final_state.get("metrics", {})
        if hasattr(metrics, "total_cost"):
            total_cost = metrics.total_cost
            total_tokens = metrics.total_tokens
        else:
            total_cost = metrics.get("total_cost", 0.0) if isinstance(metrics, dict) else 0.0
            total_tokens = metrics.get("total_tokens", 0) if isinstance(metrics, dict) else 0

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

        # Publish completion event
        round_number = final_state.get("round_number", 0)
        stop_reason = final_state.get("stop_reason", "completed")
        contributions = final_state.get("contributions", [])
        synthesis = final_state.get("synthesis", "")

        self.publisher.publish_event(
            session_id,
            "complete",
            {
                "session_id": session_id,
                "final_output": synthesis or "Deliberation complete",
                "total_cost": total_cost,
                "total_rounds": round_number,
                "total_contributions": len(contributions),
                "total_tokens": total_tokens,
                "duration_seconds": 0.0,  # TODO: Track duration
                "stop_reason": stop_reason,
            },
        )

    async def _publish_contribution(
        self,
        session_id: str,
        contrib: dict,
        round_number: int,
    ) -> None:
        """Publish a contribution event.

        Args:
            session_id: Session identifier
            contrib: Contribution dict/object
            round_number: Current round number
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

        self.publisher.publish_event(
            session_id,
            "contribution",
            {
                "persona_code": persona_code,
                "persona_name": persona_name,
                "content": content,
                "round": round_number,
                "contribution_type": "initial" if round_number == 1 else "sequential",
            },
        )
