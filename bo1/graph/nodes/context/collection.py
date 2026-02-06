"""Context collection node - loads business context and cognitive profile."""

import logging
from datetime import UTC, datetime
from typing import Any

from bo1.graph.nodes.context.cognitive import build_cognitive_context_block
from bo1.graph.nodes.utils import log_with_session
from bo1.graph.state import (
    DeliberationGraphState,
    get_core_state,
    get_problem_state,
)
from bo1.graph.utils import ensure_metrics, track_phase_cost
from bo1.prompts.sanitizer import sanitize_user_input
from bo1.state.repositories import user_repository
from bo1.state.repositories.cognition_repository import cognition_repository

logger = logging.getLogger(__name__)


async def context_collection_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Collect business context and information gaps before deliberation.

    This node:
    1. Loads saved business context (if user_id exists)
    2. Injects context into problem.context dictionary
    3. Tracks cost in metrics.phase_costs["context_collection"] (data loading = $0)

    Note: Full context collection (prompts, information gaps, research) will be
    implemented in future iterations. Currently just loads saved context.

    Args:
        state: Current graph state (must have problem)

    Returns:
        Dictionary with state updates (problem with enriched context)
    """
    # Use nested state accessors for grouped field access
    core_state = get_core_state(state)
    problem_state = get_problem_state(state)

    session_id = core_state.get("session_id")
    request_id = core_state.get("request_id")
    log_with_session(
        logger,
        logging.INFO,
        session_id,
        "context_collection_node: Starting context collection",
        request_id=request_id,
    )

    problem = problem_state.get("problem")
    if not problem:
        raise ValueError("context_collection_node called without problem")

    # Get user_id from state (optional)
    user_id = core_state.get("user_id")

    # Initialize metrics
    metrics = ensure_metrics(state)

    # Step 1: Load saved business context
    business_context = None
    if user_id:
        logger.info(f"Loading saved business context for user_id: {user_id}")
        try:
            saved_context = user_repository.get_context(user_id)
            if saved_context:
                logger.info("Found saved business context")
                business_context = saved_context

                # Inject business context into problem.context (append to string)
                # Format business context as a readable addition
                context_lines = [
                    "\n\n## Business Context",
                ]
                # Sanitize user-provided business context fields (P1 security)
                if saved_context.get("business_model"):
                    context_lines.append(
                        f"- Business Model: {sanitize_user_input(saved_context['business_model'], context='business_context')}"
                    )
                if saved_context.get("target_market"):
                    context_lines.append(
                        f"- Target Market: {sanitize_user_input(saved_context['target_market'], context='business_context')}"
                    )
                if saved_context.get("revenue"):
                    context_lines.append(
                        f"- Revenue: {sanitize_user_input(str(saved_context['revenue']), context='business_context')}"
                    )
                if saved_context.get("customers"):
                    context_lines.append(
                        f"- Customers: {sanitize_user_input(str(saved_context['customers']), context='business_context')}"
                    )
                if saved_context.get("growth_rate"):
                    context_lines.append(
                        f"- Growth Rate: {sanitize_user_input(str(saved_context['growth_rate']), context='business_context')}"
                    )

                # Strategic objectives (user-defined supporting goals)
                strategic_objectives = saved_context.get("strategic_objectives")
                if strategic_objectives and isinstance(strategic_objectives, list):
                    context_lines.append("\n## Strategic Objectives")
                    for obj in strategic_objectives[:5]:  # Max 5
                        # Sanitize each strategic objective (P1 security)
                        context_lines.append(
                            f"- {sanitize_user_input(str(obj), context='strategic_objective')}"
                        )
                    logger.info(
                        f"Injected {len(strategic_objectives[:5])} strategic objectives into context"
                    )

                # ISSUE #4 FIX: Include saved clarifications from previous meetings
                # with freshness indicators for expert awareness
                # Enhanced: Include structured category/metric info from Haiku parsing
                clarifications = saved_context.get("clarifications", {})
                if clarifications:
                    context_lines.append("\n### User Insights (from previous meetings)")
                    now = datetime.now(UTC)

                    # Group by category for organized context
                    categorized: dict[str, list[tuple[str, dict[str, Any]]]] = {}
                    for question, answer_data in clarifications.items():
                        if isinstance(answer_data, dict):
                            category = answer_data.get("category", "uncategorized")
                        else:
                            category = "uncategorized"
                        if category not in categorized:
                            categorized[category] = []
                        categorized[category].append((question, answer_data))

                    # Output by category (prioritize revenue/customers/growth)
                    priority_order = [
                        "revenue",
                        "customers",
                        "growth",
                        "team",
                        "product",
                        "market",
                        "competition",
                        "funding",
                        "costs",
                        "operations",
                        "uncategorized",
                    ]
                    for category in priority_order:
                        if category not in categorized:
                            continue
                        items = categorized[category]
                        if not items:
                            continue

                        category_label = category.replace("_", " ").title()
                        context_lines.append(f"\n**{category_label}:**")

                        for question, answer_data in items:
                            if isinstance(answer_data, dict):
                                answer = answer_data.get("answer", "N/A")
                                updated_str = answer_data.get("updated_at") or answer_data.get(
                                    "answered_at"
                                )
                                metric = answer_data.get("metric")
                            else:
                                answer = str(answer_data)
                                updated_str = None
                                metric = None

                            # Add freshness indicator
                            freshness = ""
                            if updated_str:
                                try:
                                    updated_at = datetime.fromisoformat(
                                        updated_str.replace("Z", "+00:00")
                                    )
                                    days_ago = (now - updated_at).days
                                    if days_ago == 0:
                                        freshness = " [today]"
                                    elif days_ago == 1:
                                        freshness = " [yesterday]"
                                    elif days_ago < 7:
                                        freshness = f" [{days_ago} days ago]"
                                    elif days_ago < 30:
                                        weeks = days_ago // 7
                                        freshness = f" [{weeks} week{'s' if weeks > 1 else ''} ago]"
                                    elif days_ago > 30:
                                        months = days_ago // 30
                                        freshness = f" [⚠️ {months} month{'s' if months > 1 else ''} ago - may be outdated]"
                                except (ValueError, AttributeError):
                                    freshness = " [date unknown]"
                            else:
                                freshness = " [date unknown]"

                            # Format metric if available
                            metric_str = ""
                            if metric and metric.get("value") is not None:
                                val = metric["value"]
                                unit = metric.get("unit", "")
                                if unit == "USD":
                                    if val >= 1_000_000:
                                        metric_str = f" (${val / 1_000_000:.1f}M)"
                                    elif val >= 1_000:
                                        metric_str = f" (${val / 1_000:.0f}K)"
                                    else:
                                        metric_str = f" (${val:,.0f})"
                                elif unit == "%":
                                    metric_str = f" ({val}%)"
                                elif unit == "count":
                                    metric_str = f" ({val:,.0f})"

                            # Sanitize saved clarification question and answer (P1 security)
                            context_lines.append(
                                f"- Q: {sanitize_user_input(str(question), context='saved_clarification')}{freshness}"
                            )
                            context_lines.append(
                                f"  A: {sanitize_user_input(str(answer), context='saved_clarification')}{metric_str}"
                            )
                    logger.info(
                        f"Injected {len(clarifications)} previous clarifications (with freshness) into context"
                    )

                # Append to existing context
                problem.context = problem.context + "\n".join(context_lines)
                logger.info("Injected business context into problem.context")
        except Exception as e:
            logger.warning(f"Failed to load business context: {e}")

    # Step 1b: Load cognitive profile for prompt shaping
    if user_id:
        try:
            cognitive_profile = cognition_repository.get_profile_for_prompt(user_id)
            if cognitive_profile:
                cognitive_block = build_cognitive_context_block(cognitive_profile)
                if cognitive_block:
                    problem.context = problem.context + cognitive_block
                    logger.info(
                        f"Injected cognitive profile into context for user {user_id[:8]}..."
                    )
        except Exception as e:
            logger.warning(f"Failed to load cognitive profile: {e}")

    # Step 2: Load user-selected context (meetings, actions, datasets)
    context_ids = state.get("context_ids")
    if context_ids:
        selected_context_lines: list[str] = []

        # Load past meetings
        meeting_ids = context_ids.get("meetings", [])
        if meeting_ids:
            from bo1.state.repositories import session_repository as sess_repo

            selected_context_lines.append("\n\n## Referenced Past Meetings")
            for mid in meeting_ids[:5]:  # Limit to 5
                try:
                    meeting = sess_repo.get(mid)
                    if meeting:
                        stmt = meeting.get("problem_statement", "")[:500]
                        synth = meeting.get("synthesis_text", "")
                        final_rec = meeting.get("final_recommendation", "")

                        selected_context_lines.append(f"\n### Meeting: {stmt[:100]}...")
                        if synth:
                            selected_context_lines.append(f"**Outcome:** {synth[:800]}")
                        if final_rec:
                            selected_context_lines.append(f"**Recommendation:** {final_rec[:500]}")
                except Exception as e:
                    logger.warning(f"Failed to load meeting {mid}: {e}")
            logger.info(f"Injected {len(meeting_ids)} past meetings into context")

        # Load actions
        action_ids = context_ids.get("actions", [])
        if action_ids:
            from bo1.state.repositories.action_repository import ActionRepository

            action_repo = ActionRepository()
            selected_context_lines.append("\n\n## Referenced Actions")
            for aid in action_ids[:10]:  # Limit to 10
                try:
                    action = action_repo.get(aid)
                    if action:
                        title = action.get("title", "")
                        status = action.get("status", "")
                        desc = action.get("description", "")[:300]
                        selected_context_lines.append(f"- **{title}** ({status}): {desc}")
                except Exception as e:
                    logger.warning(f"Failed to load action {aid}: {e}")
            logger.info(f"Injected {len(action_ids)} actions into context")

        # Load datasets (profile info only, not raw data)
        dataset_ids = context_ids.get("datasets", [])
        if dataset_ids:
            from bo1.state.repositories.dataset_repository import DatasetRepository

            ds_repo = DatasetRepository()
            selected_context_lines.append("\n\n## Referenced Datasets")
            for did in dataset_ids[:3]:  # Limit to 3
                try:
                    ds = ds_repo.get_by_id(did, user_id) if user_id else None
                    if ds:
                        name = ds.get("name", "")
                        rows = ds.get("row_count", 0)
                        cols = ds.get("column_count", 0)
                        desc = ds.get("description", "")[:200]
                        selected_context_lines.append(
                            f"- **{name}** ({rows:,} rows, {cols} columns)"
                        )
                        if desc:
                            selected_context_lines.append(f"  {desc}")
                except Exception as e:
                    logger.warning(f"Failed to load dataset {did}: {e}")
            logger.info(f"Injected {len(dataset_ids)} datasets into context")

        # Append selected context to problem.context
        if selected_context_lines:
            problem.context = problem.context + "\n".join(selected_context_lines)
            logger.info("Injected user-selected context into problem.context")

    # Track cost in metrics (data loading = $0, no LLM calls)
    track_phase_cost(metrics, "context_collection", None)

    log_with_session(logger, logging.INFO, session_id, "context_collection_node: Complete")

    return {
        "problem": problem,
        "business_context": business_context,
        "metrics": metrics,
        "current_node": "context_collection",
    }
