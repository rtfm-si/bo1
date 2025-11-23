"""Event collector that wraps LangGraph astream_events and publishes to Redis.

Provides:
- EventCollector: Wraps graph execution and publishes all events to Redis PubSub
"""

import json
import logging
from collections.abc import Callable
from typing import Any

from anthropic import AsyncAnthropic

from backend.api.event_publisher import EventPublisher
from bo1.config import get_settings
from bo1.models.problem import SubProblem

logger = logging.getLogger(__name__)


# ==============================================================================
# Extractor Functions - Module-level functions for extracting event data
# ==============================================================================


def _extract_decomposition_data(output: dict[str, Any]) -> dict[str, Any]:
    """Extract decomposition event data from node output.

    Args:
        output: Node output state

    Returns:
        Dict with sub_problems and count fields
    """
    problem = output.get("problem")
    sub_problems_dicts = []

    if problem and hasattr(problem, "sub_problems"):
        sub_problems = problem.sub_problems

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

    return {
        "sub_problems": sub_problems_dicts,
        "count": len(sub_problems_dicts),
    }


def _extract_persona_selection_data(output: dict[str, Any]) -> dict[str, Any]:
    """Extract persona selection event data from node output.

    Args:
        output: Node output state

    Returns:
        Dict with personas, count, and sub_problem_index fields
    """
    personas = output.get("personas", [])
    sub_problem_index = output.get("sub_problem_index", 0)
    persona_codes = [p.code if hasattr(p, "code") else p.get("code") for p in personas]

    return {
        "personas": persona_codes,
        "count": len(persona_codes),
        "sub_problem_index": sub_problem_index,
    }


def _extract_facilitator_decision_data(output: dict[str, Any]) -> dict[str, Any]:
    """Extract facilitator decision event data from node output.

    Args:
        output: Node output state

    Returns:
        Dict with action, reasoning, round, and optional fields
    """
    decision = output.get("facilitator_decision")
    round_number = output.get("round_number", 1)
    sub_problem_index = output.get("sub_problem_index", 0)

    if not decision:
        return {}

    data = {
        "action": decision.get("action", ""),
        "reasoning": decision.get("reasoning", ""),
        "round": round_number,
        "sub_problem_index": sub_problem_index,
    }

    # Add optional fields if present
    if next_speaker := decision.get("next_speaker"):
        data["next_speaker"] = next_speaker
    if moderator_type := decision.get("moderator_type"):
        data["moderator_type"] = moderator_type
    if research_query := decision.get("research_query"):
        data["research_query"] = research_query

    return data


def _extract_moderator_intervention_data(output: dict[str, Any]) -> dict[str, Any]:
    """Extract moderator intervention event data from node output.

    Args:
        output: Node output state

    Returns:
        Dict with moderator_type, content, trigger_reason, and round fields
    """
    contributions = output.get("contributions", [])
    round_number = output.get("round_number", 1)
    sub_problem_index = output.get("sub_problem_index", 0)

    if not contributions:
        return {}

    contrib = contributions[-1]
    moderator_type = contrib.get("persona_code", "moderator")
    content = contrib.get("content", "")

    return {
        "moderator_type": moderator_type,
        "content": content,
        "trigger_reason": "Facilitator requested intervention",
        "round": round_number,
        "sub_problem_index": sub_problem_index,
    }


def _extract_convergence_data(output: dict[str, Any]) -> dict[str, Any]:
    """Extract convergence event data from node output.

    Args:
        output: Node output state

    Returns:
        Dict with convergence metrics and decision fields
    """
    should_stop = output.get("should_stop", False)
    stop_reason = output.get("stop_reason")
    round_number = output.get("round_number", 1)
    max_rounds = output.get("max_rounds", 10)
    sub_problem_index = output.get("sub_problem_index", 0)

    # Get convergence score from metrics
    metrics = output.get("metrics", {})
    if hasattr(metrics, "convergence_score"):
        convergence_score = metrics.convergence_score or 0.0
    else:
        convergence_score = (
            metrics.get("convergence_score", 0.0) if isinstance(metrics, dict) else 0.0
        )

    return {
        "converged": should_stop,
        "score": convergence_score,
        "threshold": 0.85,
        "should_stop": should_stop,
        "stop_reason": stop_reason,
        "round": round_number,
        "max_rounds": max_rounds,
        "sub_problem_index": sub_problem_index,
    }


def _extract_voting_data(output: dict[str, Any]) -> dict[str, Any]:
    """Extract voting event data from node output.

    Args:
        output: Node output state

    Returns:
        Dict with votes, consensus_level, and confidence metrics
    """
    votes = output.get("votes", [])
    sub_problem_index = output.get("sub_problem_index", 0)

    # Format votes for compact display
    formatted_votes = []
    for vote in votes:
        formatted_votes.append(
            {
                "persona_code": vote.get("persona_code", ""),
                "persona_name": vote.get("persona_name", ""),
                "recommendation": vote.get("recommendation", ""),
                "confidence": vote.get("confidence", 0.0),
                "reasoning": vote.get("reasoning", ""),
                "conditions": vote.get("conditions", []),
            }
        )

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
        avg_confidence = 0.0

    return {
        "votes": formatted_votes,
        "votes_count": len(votes),
        "consensus_level": consensus_level,
        "avg_confidence": avg_confidence,
        "sub_problem_index": sub_problem_index,
    }


def _extract_synthesis_data(output: dict[str, Any]) -> dict[str, Any]:
    """Extract synthesis event data from node output.

    Args:
        output: Node output state

    Returns:
        Dict with synthesis text, word_count, and sub_problem_index
    """
    synthesis = output.get("synthesis", "")
    word_count = len(synthesis.split()) if synthesis else 0
    sub_problem_index = output.get("sub_problem_index", 0)

    return {
        "synthesis": synthesis,
        "word_count": word_count,
        "sub_problem_index": sub_problem_index,
    }


def _extract_meta_synthesis_data(output: dict[str, Any]) -> dict[str, Any]:
    """Extract meta-synthesis event data from node output.

    Args:
        output: Node output state

    Returns:
        Dict with synthesis text and word_count
    """
    synthesis = output.get("synthesis", "")
    word_count = len(synthesis.split()) if synthesis else 0

    return {
        "synthesis": synthesis,
        "word_count": word_count,
    }


def _extract_subproblem_started_data(output: dict[str, Any]) -> dict[str, Any]:
    """Extract subproblem started event data from node output.

    Args:
        output: Node output state

    Returns:
        Dict with sub_problem info, or empty dict if not a multi-subproblem scenario
    """
    sub_problem_index = output.get("sub_problem_index", 0)
    current_sub_problem = output.get("current_sub_problem")
    problem = output.get("problem")

    # Only publish if this is a multi-sub-problem scenario
    if not (problem and hasattr(problem, "sub_problems") and len(problem.sub_problems) > 1):
        return {}

    if not current_sub_problem:
        return {}

    return {
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
    }


def _extract_subproblem_complete_data(output: dict[str, Any], redis_client: Any) -> dict[str, Any]:
    """Extract subproblem complete event data from node output.

    Args:
        output: Node output state
        redis_client: Redis client for duration calculation

    Returns:
        Dict with completed sub-problem metrics, or empty dict if no results
    """
    sub_problem_results = output.get("sub_problem_results", [])

    if not sub_problem_results:
        return {}

    # Get the most recently completed sub-problem result
    result = sub_problem_results[-1]

    # Extract result data
    if hasattr(result, "sub_problem_id"):
        sp_id = result.sub_problem_id
        sp_goal = result.sub_problem_goal
        cost = result.cost
        duration_seconds = result.duration_seconds
        expert_panel = result.expert_panel
        contribution_count = result.contribution_count
    else:
        sp_id = result.get("sub_problem_id", "")
        sp_goal = result.get("sub_problem_goal", "")
        cost = result.get("cost", 0.0)
        duration_seconds = result.get("duration_seconds", 0.0)
        expert_panel = result.get("expert_panel", [])
        contribution_count = result.get("contribution_count", 0)

    completed_index = len(sub_problem_results) - 1

    return {
        "sub_problem_index": completed_index,
        "sub_problem_id": sp_id,
        "goal": sp_goal,
        "cost": cost,
        "duration_seconds": duration_seconds,
        "expert_panel": expert_panel,
        "contribution_count": contribution_count,
    }


def _extract_completion_data(output: dict[str, Any]) -> dict[str, Any]:
    """Extract completion event data from final state.

    Args:
        output: Final graph state

    Returns:
        Dict with session summary and metrics
    """
    # Get metrics
    metrics = output.get("metrics", {})
    if hasattr(metrics, "total_cost"):
        total_cost = metrics.total_cost
        total_tokens = metrics.total_tokens
    else:
        total_cost = metrics.get("total_cost", 0.0) if isinstance(metrics, dict) else 0.0
        total_tokens = metrics.get("total_tokens", 0) if isinstance(metrics, dict) else 0

    round_number = output.get("round_number", 0)
    stop_reason = output.get("stop_reason", "completed")
    contributions = output.get("contributions", [])
    synthesis = output.get("synthesis", "")
    session_id = output.get("session_id", "")

    return {
        "session_id": session_id,
        "final_output": synthesis or "Deliberation complete",
        "total_cost": total_cost,
        "total_rounds": round_number,
        "total_contributions": len(contributions),
        "total_tokens": total_tokens,
        "duration_seconds": 0.0,  # TODO: Track duration
        "stop_reason": stop_reason,
    }


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
        # Initialize Anthropic client for AI summarization
        settings = get_settings()
        self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def _publish_node_event(
        self,
        session_id: str,
        output: dict[str, Any],
        event_type: str,
        extractor: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        """Generic event publisher with custom extraction logic.

        Args:
            session_id: Session identifier
            output: Raw node output dictionary
            event_type: Event type for SSE
            extractor: Function to extract event data from output
        """
        try:
            data = extractor(output)
            if data:  # Only publish if extractor returned data
                self.publisher.publish_event(session_id, event_type, data)
        except Exception as e:
            logger.error(f"Failed to publish {event_type} for session {session_id}: {e}")

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
        """Handle decompose node completion."""
        await self._publish_node_event(
            session_id, output, "decomposition_complete", _extract_decomposition_data
        )

    async def _handle_persona_selection(self, session_id: str, output: dict) -> None:
        """Handle select_personas node completion - publishes multiple events."""
        personas = output.get("personas", [])
        persona_recommendations = output.get("persona_recommendations", [])
        sub_problem_index = output.get("sub_problem_index", 0)

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
                    "sub_problem_index": sub_problem_index,
                },
            )

        # Publish persona selection complete event
        await self._publish_node_event(
            session_id, output, "persona_selection_complete", _extract_persona_selection_data
        )

        # Store start timestamp and publish subproblem_started if multi-subproblem scenario
        subproblem_data = _extract_subproblem_started_data(output)
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
        # Extract sub_problem_index for tab filtering
        sub_problem_index = output.get("sub_problem_index", 0)

        # Publish individual contributions
        contributions = output.get("contributions", [])
        for contrib in contributions:
            await self._publish_contribution(
                session_id, contrib, round_number=1, sub_problem_index=sub_problem_index
            )

    async def _handle_facilitator_decision(self, session_id: str, output: dict) -> None:
        """Handle facilitator_decide node completion."""
        await self._publish_node_event(
            session_id, output, "facilitator_decision", _extract_facilitator_decision_data
        )

    async def _handle_contribution(self, session_id: str, output: dict) -> None:
        """Handle persona_contribute node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        contributions = output.get("contributions", [])
        round_number = output.get("round_number", 1)
        sub_problem_index = output.get("sub_problem_index", 0)

        # Publish the newest contribution (last in list)
        if contributions:
            await self._publish_contribution(
                session_id, contributions[-1], round_number, sub_problem_index
            )

    async def _handle_moderator(self, session_id: str, output: dict) -> None:
        """Handle moderator_intervene node completion."""
        await self._publish_node_event(
            session_id, output, "moderator_intervention", _extract_moderator_intervention_data
        )

    async def _handle_convergence(self, session_id: str, output: dict) -> None:
        """Handle check_convergence node completion."""
        await self._publish_node_event(session_id, output, "convergence", _extract_convergence_data)

    async def _handle_voting(self, session_id: str, output: dict) -> None:
        """Handle vote node completion."""
        await self._publish_node_event(session_id, output, "voting_complete", _extract_voting_data)

    async def _handle_synthesis(self, session_id: str, output: dict) -> None:
        """Handle synthesize node completion."""
        await self._publish_node_event(
            session_id, output, "synthesis_complete", _extract_synthesis_data
        )

    async def _handle_subproblem_complete(self, session_id: str, output: dict) -> None:
        """Handle next_subproblem node completion - includes duration calculation."""
        sub_problem_results = output.get("sub_problem_results", [])

        if not sub_problem_results:
            return

        # Extract data using extractor
        data = _extract_subproblem_complete_data(output, self.publisher.redis)

        # Calculate actual duration if we have start time
        completed_index = data["sub_problem_index"]
        subproblem_key = f"subproblem:{session_id}:{completed_index}:start_time"
        start_time_str = self.publisher.redis.get(subproblem_key)

        if start_time_str and data["duration_seconds"] == 0.0:
            # Calculate duration from stored start time
            from datetime import UTC, datetime

            start_time = datetime.fromisoformat(start_time_str)
            end_time = datetime.now(UTC)
            data["duration_seconds"] = (end_time - start_time).total_seconds()

            # Clean up the start time key
            self.publisher.redis.delete(subproblem_key)

        self.publisher.publish_event(session_id, "subproblem_complete", data)

    async def _handle_meta_synthesis(self, session_id: str, output: dict) -> None:
        """Handle meta_synthesize node completion."""
        await self._publish_node_event(
            session_id, output, "meta_synthesis_complete", _extract_meta_synthesis_data
        )

    async def _handle_completion(self, session_id: str, final_state: dict) -> None:
        """Handle deliberation completion - publishes cost breakdown and completion events."""
        # Extract phase costs and metrics
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

        # Publish completion event
        completion_data = _extract_completion_data(final_state)
        completion_data["session_id"] = session_id  # Ensure session_id is present
        self.publisher.publish_event(session_id, "complete", completion_data)

    async def _summarize_contribution(self, content: str, persona_name: str) -> dict | None:
        """Summarize expert contribution into structured insights using Haiku 4.5.

        Uses Claude Haiku 4.5 for cost-effective summarization (~$0.001 per contribution).

        Args:
            content: Full expert contribution (200-500 words)
            persona_name: Expert name for context

        Returns:
            Dict with looking_for, value_added, concerns, questions, or None if summarization fails
        """
        try:
            prompt = f"""<system_role>
You are a contribution summarizer for Board of One, creating structured summaries
of expert contributions for compact UI display.
</system_role>

<contribution>
EXPERT: {persona_name}

{content}
</contribution>

<examples>
<example>
<contribution>
EXPERT: Chief Technology Officer

As CTO, I'm concerned about our current infrastructure's ability to scale. We're seeing database query times increase by 200% month-over-month, and our monolithic architecture makes it difficult to deploy updates without risking downtime. I recommend we evaluate a microservices migration starting with our payments module, which is relatively isolated. However, we need to invest in observability tools first - distributed tracing, centralized logging, and service mesh infrastructure. The team lacks microservices experience, so we should budget for training or consulting. My biggest concern is that we underestimate the organizational complexity - team structure must align with service boundaries, which means reorganizing engineering squads. What is our timeline for this decision? And do we have budget allocated for the infrastructure changes required?
</contribution>

<thinking>
1. Expert is analyzing: Infrastructure scaling challenges and microservices migration feasibility
2. Unique insight: Emphasizes organizational transformation (team structure) as critical as technical migration
3. Main concerns: Database performance degradation, team skills gap, organizational complexity
4. Key questions: Timeline and budget for infrastructure investment
</thinking>

<summary>
{{
  "looking_for": "Evaluating microservices migration feasibility, focusing on infrastructure scalability and team readiness",
  "value_added": "Highlights that organizational transformation (team structure alignment) is as critical as technical architecture changes",
  "concerns": ["Database query times increased 200% month-over-month", "Team lacks microservices experience and needs training", "Organizational complexity of reorganizing engineering squads"],
  "questions": ["What is the decision timeline for migration?", "Is budget allocated for observability infrastructure?"]
}}
</summary>
</example>

<example>
<contribution>
EXPERT: Chief Financial Officer

From a financial perspective, I need to see a clear ROI analysis before committing $500K to EU expansion. Our current burn rate is $200K/month, and we have 18 months of runway. Investing $500K means we're shortening our runway by 2.5 months, which is significant. I want to see a phased approach - perhaps a $100K pilot in UK market first to validate demand and unit economics. What are the expected customer acquisition costs in EU compared to US? What's the payback period? Are we confident we can achieve similar conversion rates? I'm also concerned about currency risk and the complexity of multi-currency billing. If we pursue this, we need clear go/no-go criteria at the 3-month mark to avoid throwing good money after bad.
</contribution>

<thinking>
1. Expert is analyzing: Financial viability and ROI of EU expansion investment
2. Unique insight: Emphasizes runway impact and phased validation approach to de-risk investment
3. Main concerns: Runway reduction, uncertain unit economics, currency risk
4. Key questions: CAC comparison, payback period, conversion rate confidence
</thinking>

<summary>
{{
  "looking_for": "Analyzing ROI and financial viability of $500K EU expansion against 18-month runway constraints",
  "value_added": "Recommends phased $100K UK pilot first to validate unit economics before full EU commitment",
  "concerns": ["Investment shortens runway by 2.5 months significantly", "Uncertain EU customer acquisition costs vs US baseline", "Currency risk and multi-currency billing complexity"],
  "questions": ["What are expected CAC and payback period in EU?", "Are we confident in achieving similar conversion rates?"]
}}
</summary>
</example>
</examples>

<instructions>
Summarize the expert contribution into 4 concise structural elements for UI display.

<requirements>
1. looking_for: What is this expert analyzing or seeking? (15-25 words)
2. value_added: What unique insight or perspective do they bring? (15-25 words)
3. concerns: Array of 2-3 specific concerns mentioned (10-15 words each)
4. questions: Array of 1-2 specific questions they raised (10-15 words each)
</requirements>

<thinking>
Analyze the contribution:
1. What problem or aspect is this expert focusing on?
2. What unique perspective or framework do they bring?
3. What specific concerns or risks did they identify?
4. What questions or information gaps did they raise?

Then generate the structured JSON summary.
</thinking>

<output>
Generate VALID JSON in this EXACT format (no markdown, no code blocks, just pure JSON):

{{
  "looking_for": "string",
  "value_added": "string",
  "concerns": ["string", "string"],
  "questions": ["string", "string"]
}}
</output>

Be specific, extract concrete insights, avoid generic statements.
</instructions>"""

            response = await self.anthropic_client.messages.create(
                model="claude-3-5-haiku-20241022",
                max_tokens=500,
                messages=[
                    {"role": "user", "content": prompt},
                    {"role": "assistant", "content": "{"},  # Prefill to force JSON
                ],
            )

            # Extract JSON from response - prepend opening brace from prefill
            response_text = "{" + response.content[0].text
            summary = json.loads(response_text)

            logger.debug(f"Summarized contribution for {persona_name}")
            return summary

        except Exception as e:
            logger.error(f"Failed to summarize contribution for {persona_name}: {e}")
            return None

    async def _publish_contribution(
        self,
        session_id: str,
        contrib: dict,
        round_number: int,
        sub_problem_index: int = 0,
    ) -> None:
        """Publish a contribution event with AI summary.

        Args:
            session_id: Session identifier
            contrib: Contribution dict/object
            round_number: Current round number
            sub_problem_index: Sub-problem index for tab filtering
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

        # Generate AI summary for better UX
        summary = await self._summarize_contribution(content, persona_name)

        self.publisher.publish_event(
            session_id,
            "contribution",
            {
                "persona_code": persona_code,
                "persona_name": persona_name,
                "content": content,  # Keep full content for reference
                "summary": summary,  # NEW: Structured summary for compact display
                "round": round_number,
                "contribution_type": "initial" if round_number == 1 else "sequential",
                "sub_problem_index": sub_problem_index,  # For tab filtering
            },
        )
