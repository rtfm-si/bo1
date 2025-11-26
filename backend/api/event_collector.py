"""Event collector that wraps LangGraph astream_events and publishes to Redis.

Provides:
- EventCollector: Wraps graph execution and publishes all events to Redis PubSub
"""

import json
import logging
from typing import Any

from anthropic import AsyncAnthropic

from backend.api.event_extractors import get_event_registry
from backend.api.event_publisher import EventPublisher
from bo1.config import get_settings

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
        # Initialize Anthropic client for AI summarization
        settings = get_settings()
        self.anthropic_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

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

                    elif event_name == "parallel_round" and isinstance(output, dict):
                        await self._handle_parallel_round(session_id, output)

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
        await self._publish_node_event(session_id, output, "decomposition_complete")

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
                "archetype": (
                    persona.archetype
                    if hasattr(persona, "archetype")
                    else persona.get("archetype", "")
                ),
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
        await self._publish_node_event(session_id, output, "facilitator_decision")

    async def _handle_contribution(self, session_id: str, output: dict) -> None:
        """Handle persona_contribute node completion.

        Args:
            session_id: Session identifier
            output: Node output state
        """
        contributions = output.get("contributions", [])
        round_number = output.get("round_number", 1)
        sub_problem_index = output.get("sub_problem_index", 0)
        personas = output.get("personas", [])

        # Publish the newest contribution (last in list)
        if contributions:
            await self._publish_contribution(
                session_id, contributions[-1], round_number, sub_problem_index, personas
            )

    async def _handle_parallel_round(self, session_id: str, output: dict) -> None:
        """Handle parallel_round node completion events.

        Publishes events for:
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
        await self._publish_node_event(session_id, output, "moderator_intervention")

    async def _handle_convergence(self, session_id: str, output: dict) -> None:
        """Handle check_convergence node completion."""
        logger.info(
            f"[CONVERGENCE DEBUG] Handler called for session {session_id} | "
            f"round={output.get('round_number')} | "
            f"should_stop={output.get('should_stop')} | "
            f"metrics={output.get('metrics')}"
        )
        await self._publish_node_event(session_id, output, "convergence")

    async def _handle_voting(self, session_id: str, output: dict) -> None:
        """Handle vote node completion."""
        await self._publish_node_event(session_id, output, "voting_complete", registry_key="voting")

    async def _handle_synthesis(self, session_id: str, output: dict) -> None:
        """Handle synthesize node completion."""
        await self._publish_node_event(session_id, output, "synthesis_complete")

    async def _handle_subproblem_complete(self, session_id: str, output: dict) -> None:
        """Handle next_subproblem node completion - includes duration calculation."""
        sub_problem_results = output.get("sub_problem_results", [])

        if not sub_problem_results:
            return

        # Extract data using registry
        registry = get_event_registry()
        data = registry.extract("subproblem_complete", output)

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
        await self._publish_node_event(session_id, output, "meta_synthesis_complete")

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
        registry = get_event_registry()
        completion_data = registry.extract("completion", final_state)
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
  "concise": "Exploring microservices migration to address 200% database slowdown, emphasizing that team reorganization is as critical as the technical shift—needs timeline and budget clarity first.",
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
  "concise": "Questioning the $500K EU spend against our 18-month runway, proposing a $100K UK pilot to test unit economics before committing—need CAC data and clear go/no-go criteria at 3 months.",
  "looking_for": "Analyzing ROI and financial viability of $500K EU expansion against 18-month runway constraints",
  "value_added": "Recommends phased $100K UK pilot first to validate unit economics before full EU commitment",
  "concerns": ["Investment shortens runway by 2.5 months significantly", "Uncertain EU customer acquisition costs vs US baseline", "Currency risk and multi-currency billing complexity"],
  "questions": ["What are expected CAC and payback period in EU?", "Are we confident in achieving similar conversion rates?"]
}}
</summary>
</example>
</examples>

<instructions>
Summarize the expert contribution into 5 concise structural elements for UI display.

<requirements>
1. concise: A 1-2 sentence summary that captures the expert's core perspective and recommendation (25-40 words). Write from the expert's viewpoint as if speaking directly.
2. looking_for: What is this expert analyzing or seeking? (15-25 words)
3. value_added: What unique insight or perspective do they bring? (15-25 words)
4. concerns: Array of 2-3 specific concerns mentioned (10-15 words each)
5. questions: Array of 1-2 specific questions they raised (10-15 words each)
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
  "concise": "string (1-2 sentence summary, 25-40 words)",
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
                    break

        # Generate AI summary for better UX
        summary = await self._summarize_contribution(content, persona_name)

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
                "contribution_type": "initial" if round_number == 1 else "sequential",
                "sub_problem_index": sub_problem_index,  # For tab filtering
            },
        )
