"""Context collection and clarification nodes.

This module contains nodes for collecting and managing context:
- context_collection_node: Collects business context before deliberation
- identify_gaps_node: Identifies critical information gaps after decomposition
- clarification_node: Handles clarification questions during deliberation
"""

import json
import logging
from datetime import UTC, datetime
from typing import Any

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


def build_cognitive_context_block(profile: dict[str, Any]) -> str:
    """Build cognitive context block for prompt injection.

    Includes:
    - Resonance guidance (how to frame advice)
    - Blindspot compensation (what to actively counter)

    Args:
        profile: Cognitive profile dict from cognition_repository

    Returns:
        Formatted string for injection into problem.context
    """
    if not profile:
        return ""

    lines = ["\n\n## User Cognitive Profile"]

    # Style summary
    if profile.get("cognitive_style_summary"):
        lines.append(f"**Decision Style:** {profile['cognitive_style_summary']}")

    lines.append("\n### Communication Guidance")

    # Time horizon framing
    th = profile.get("gravity_time_horizon")
    if th is not None:
        if th < 0.3:
            lines.append("- Frame recommendations with immediate actionability and quick wins")
        elif th > 0.7:
            lines.append("- Frame recommendations with long-term strategic implications")

    # Information density
    info = profile.get("gravity_information_density")
    if info is not None:
        if info < 0.3:
            lines.append("- Keep analysis high-level, lead with conclusions")
        elif info > 0.7:
            lines.append("- Provide detailed supporting data and nuanced analysis")

    # Risk sensitivity
    risk = profile.get("friction_risk_sensitivity")
    if risk is not None:
        if risk > 0.7:
            lines.append("- Emphasize risk mitigation strategies and downside protection")
        elif risk < 0.3:
            lines.append("- User is comfortable with calculated risks; focus on upside potential")

    # Ambiguity tolerance
    ambig = profile.get("friction_ambiguity_tolerance")
    if ambig is not None:
        if ambig > 0.7:
            lines.append("- Provide clear, bounded options; avoid open-ended recommendations")

    # Control style
    control = profile.get("gravity_control_style")
    if control is not None:
        if control > 0.7:
            lines.append("- Include detailed execution steps; user prefers hands-on involvement")
        elif control < 0.3:
            lines.append("- Focus on outcomes and delegation options")

    # Blindspot Compensation
    blindspots = profile.get("primary_blindspots", [])
    if blindspots:
        lines.append("\n### Blindspot Awareness (Actively Counter These)")
        for bs in blindspots[:3]:
            if isinstance(bs, dict):
                label = bs.get("label", "Unknown")
                compensation = bs.get("compensation", "")
                lines.append(f"- **{label}**: {compensation}")

    return "\n".join(lines)


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


async def identify_gaps_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Identify critical information gaps after decomposition.

    This node runs AFTER decomposition and BEFORE deliberation to:
    1. Analyze the problem and sub-problems for missing critical information
    2. Categorize gaps as INTERNAL (user must provide) or EXTERNAL (can research)
    3. If CRITICAL internal gaps exist, pause session for user Q&A
    4. External gaps can be researched automatically during deliberation

    This prevents entire sub-problems by getting key info upfront, leading to
    better, faster, cheaper deliberations.

    If the user has enabled "skip_clarification" preference, this node skips
    the gap analysis and continues directly to deliberation.

    Args:
        state: Current graph state (must have problem with sub_problems)

    Returns:
        Dictionary with state updates:
        - If critical gaps: should_stop=True, pending_clarification with questions
        - If no critical gaps: continues to next node
        - If skip_clarification: continues to next node without analysis
    """
    session_id = state.get("session_id")
    log_with_session(
        logger, logging.INFO, session_id, "identify_gaps_node: Analyzing information gaps"
    )

    # Check if user has enabled skip_clarification preference
    skip_clarification = state.get("skip_clarification", False)
    if skip_clarification:
        log_with_session(
            logger,
            logging.INFO,
            session_id,
            "identify_gaps_node: User preference skip_clarification=True, skipping gap analysis",
        )
        return {"current_node": "identify_gaps"}

    problem = state.get("problem")
    if not problem:
        raise ValueError("identify_gaps_node called without problem")

    # Check if we already have clarification answers waiting to be processed
    clarification_answers = state.get("clarification_answers")
    pending_clarification = state.get("pending_clarification")

    # Debug logging to trace the clarification flow
    logger.info(
        f"identify_gaps_node: clarification_answers={clarification_answers is not None}, "
        f"pending_clarification={pending_clarification is not None}"
    )

    if clarification_answers and isinstance(clarification_answers, dict):
        answer_count = len(clarification_answers)
        logger.info(f"identify_gaps_node: Processing {answer_count} clarification answers")

        # Check if there are unanswered questions from pending_clarification
        if pending_clarification and pending_clarification.get("questions"):
            original_questions = pending_clarification.get("questions", [])
            answered_questions = set(clarification_answers.keys())

            # Find unanswered questions
            unanswered_questions = [
                q for q in original_questions if q.get("question") not in answered_questions
            ]

            if unanswered_questions:
                logger.info(
                    f"identify_gaps_node: {len(unanswered_questions)} questions remain unanswered, "
                    f"re-pausing for user input"
                )

                # Re-pause with remaining questions
                return {
                    "current_node": "identify_gaps",
                    "should_stop": True,
                    "stop_reason": "clarification_needed",
                    "pending_clarification": {
                        "questions": unanswered_questions,
                        "phase": "pre_deliberation",
                        "reason": "Additional information needed to proceed",
                    },
                    # Keep the answers we have, don't clear them
                    "clarification_answers": clarification_answers,
                }

        # All questions answered (or no original questions) - continue to next node
        logger.info("identify_gaps_node: All clarification questions answered, continuing")

        # Check for partial/incomplete answers and set limited_context_mode
        limited_context_mode = False
        partial_answer_reasons = []

        if clarification_answers:
            for question, answer in clarification_answers.items():
                answer_str = str(answer).strip() if answer else ""

                # Check for empty or very short answers (< 10 chars is likely unhelpful)
                if not answer_str:
                    partial_answer_reasons.append(f"Empty answer for: {question[:50]}...")
                    limited_context_mode = True
                elif len(answer_str) < 10:
                    partial_answer_reasons.append(
                        f"Very short answer ({len(answer_str)} chars) for: {question[:50]}..."
                    )
                    limited_context_mode = True

            if limited_context_mode:
                logger.warning(
                    f"identify_gaps_node: Partial/incomplete answers detected - "
                    f"enabling limited_context_mode. Reasons: {partial_answer_reasons}"
                )
            else:
                logger.info(
                    f"identify_gaps_node: All {len(clarification_answers)} answers appear complete"
                )

        # Inject answers into problem context for use by downstream nodes
        # This ensures experts have access to the user's clarification responses
        if clarification_answers:
            # Format answers as context addition
            answer_context = "\n\n## User Clarifications\n"
            for question, answer in clarification_answers.items():
                answer_context += f"- **Q:** {question}\n  **A:** {answer}\n"

            # Get current context and append answers
            current_context = ""
            if isinstance(problem, dict):
                current_context = problem.get("context", "") or ""
                problem["context"] = current_context + answer_context
            else:
                current_context = problem.context or ""
                problem.context = current_context + answer_context

            logger.info(
                f"identify_gaps_node: Injected {len(clarification_answers)} clarification "
                f"answer(s) into problem context ({len(answer_context)} chars added)"
            )

        return {
            "current_node": "identify_gaps",
            "pending_clarification": None,
            "problem": problem,  # Updated with clarification context
            "clarification_answers": None,  # Clear after processing
            "limited_context_mode": limited_context_mode,  # NEW: Flag for partial answers
            "context_insufficient_emitted": False,  # Reset for fresh detection
        }

    # Get sub-problems from problem (handle both dict and object)
    if isinstance(problem, dict):
        sub_problems = problem.get("sub_problems", []) or []
    else:
        sub_problems = problem.sub_problems or []
    if not sub_problems:
        logger.info("identify_gaps_node: No sub-problems, skipping gap analysis")
        return {"current_node": "identify_gaps"}

    # Get business context
    business_context = state.get("business_context") or {}

    # BUG FIX (P1 #3): Include problem_context in business_context
    # This ensures the information gap analysis considers context already provided by the user
    problem_context = ""
    if isinstance(problem, dict):
        problem_context = problem.get("context", "") or ""
    else:
        problem_context = problem.context or ""

    # Merge problem_context into business_context for the LLM
    merged_context = dict(business_context) if isinstance(business_context, dict) else {}
    if problem_context:
        # Parse problem_context if it's JSON
        try:
            parsed_context = json.loads(problem_context)
            if isinstance(parsed_context, dict):
                merged_context.update(parsed_context)
            else:
                merged_context["provided_context"] = problem_context
        except (json.JSONDecodeError, TypeError):
            # If not JSON, store as string
            merged_context["provided_context"] = problem_context

    logger.info(
        f"identify_gaps_node: Merged context has {len(merged_context)} keys "
        f"(problem_context length: {len(problem_context)} chars)"
    )

    # Call decomposer's identify_information_gaps method
    from bo1.agents.decomposer import DecomposerAgent

    decomposer = DecomposerAgent()

    # Handle sub_problems as either objects or dicts
    sub_problems_dicts = []
    for sp in sub_problems:
        if isinstance(sp, dict):
            sub_problems_dicts.append(
                {
                    "id": sp.get("id", ""),
                    "goal": sp.get("goal", ""),
                    "context": sp.get("context", ""),
                    "complexity_score": sp.get("complexity_score", 5),
                }
            )
        else:
            sub_problems_dicts.append(
                {
                    "id": sp.id,
                    "goal": sp.goal,
                    "context": sp.context,
                    "complexity_score": sp.complexity_score,
                }
            )

    # Get problem description (handle dict or object)
    problem_description = (
        problem.get("description", "") if isinstance(problem, dict) else problem.description
    )

    response = await decomposer.identify_information_gaps(
        problem_description=problem_description,
        sub_problems=sub_problems_dicts,
        business_context=merged_context if merged_context else None,  # BUG FIX: Use merged context
    )

    # Parse gaps
    try:
        gaps = json.loads(response.content)
    except json.JSONDecodeError:
        logger.warning("identify_gaps_node: Failed to parse gaps JSON, continuing without Q&A")
        gaps = {"internal_gaps": [], "external_gaps": []}

    internal_gaps = gaps.get("internal_gaps", [])
    external_gaps = gaps.get("external_gaps", [])

    # Filter to CRITICAL internal gaps only
    critical_internal_gaps = [gap for gap in internal_gaps if gap.get("priority") == "CRITICAL"]

    logger.info(
        f"identify_gaps_node: Found {len(internal_gaps)} internal gaps "
        f"({len(critical_internal_gaps)} critical), {len(external_gaps)} external gaps"
    )

    # Track cost
    metrics = ensure_metrics(state)
    track_phase_cost(metrics, "identify_gaps", response)

    # Store external gaps for potential research during deliberation
    state_updates: dict[str, Any] = {
        "metrics": metrics,
        "current_node": "identify_gaps",
        "external_research_gaps": external_gaps,  # Can be researched later
    }

    if critical_internal_gaps:
        # Format questions for user
        questions = [
            {
                "question": gap["question"],
                "reason": gap.get(
                    "reason", "This information is critical for high-quality recommendations"
                ),
                "priority": "CRITICAL",
            }
            for gap in critical_internal_gaps
        ]

        logger.info(
            f"identify_gaps_node: Pausing for {len(questions)} critical clarifying questions"
        )

        # Pause session for user to answer
        state_updates.update(
            {
                "should_stop": True,
                "stop_reason": "clarification_needed",
                "pending_clarification": {
                    "questions": questions,
                    "phase": "pre_deliberation",
                    "reason": "Critical information needed before starting expert deliberation",
                },
            }
        )
    else:
        logger.info("identify_gaps_node: No critical gaps, proceeding to deliberation")

    return state_updates


async def clarification_node(state: DeliberationGraphState) -> dict[str, Any]:
    """Handle clarification questions from facilitator during deliberation.

    This node:
    1. In API mode (headless): Auto-pause and wait for user to answer via API
    2. In CLI mode: Interactive prompt for answer/pause/skip

    Args:
        state: Current graph state (must have pending_clarification)

    Returns:
        Dictionary with state updates (context with answer, or paused state)
    """
    logger.info("clarification_node: Handling clarification request")

    pending_clarification = state.get("pending_clarification")

    if not pending_clarification:
        logger.warning("clarification_node called without pending_clarification")
        return {
            "current_node": "clarification",
        }

    question = pending_clarification.get("question", "Unknown question")
    reason = pending_clarification.get("reason", "")

    # Check if we're running in headless mode (no stdin available)
    # In API/server mode, stdin is not connected, so we auto-pause
    import os
    import sys

    is_headless = not sys.stdin.isatty() or os.environ.get("BO1_HEADLESS", "").lower() in (
        "1",
        "true",
    )

    if is_headless:
        # API mode: Auto-pause session, user answers via API
        logger.info(
            f"clarification_node: Headless mode detected, pausing for API-based answer. "
            f"Question: {question[:50]}..."
        )
        return {
            "should_stop": True,
            "stop_reason": "clarification_needed",
            "pending_clarification": pending_clarification,
            "current_node": "clarification",
        }

    # CLI mode: Interactive prompt
    from bo1.ui.console import Console

    console = Console()

    console.print("\n[bold yellow]Clarification Needed[/bold yellow]")
    console.print(f"Question: {question}")
    if reason:
        console.print(f"Reason: {reason}")

    console.print("\nOptions:")
    console.print("1. Answer now")
    console.print("2. Pause session (resume later)")
    console.print("3. Skip question")

    try:
        choice = console.input("\nYour choice (1-3): ").strip()
    except EOFError:
        # Fallback: If stdin fails, pause the session
        logger.warning("clarification_node: EOFError on input, pausing session")
        return {
            "should_stop": True,
            "stop_reason": "clarification_needed",
            "pending_clarification": pending_clarification,
            "current_node": "clarification",
        }

    if choice == "1":
        # Collect answer
        try:
            answer = console.input("\nYour answer: ").strip()
        except EOFError:
            logger.warning("clarification_node: EOFError on answer input, pausing session")
            return {
                "should_stop": True,
                "stop_reason": "clarification_needed",
                "pending_clarification": pending_clarification,
                "current_node": "clarification",
            }

        # Store answer in pending_clarification for later injection
        answered_clarification = pending_clarification.copy()
        answered_clarification["answer"] = answer
        answered_clarification["answered"] = True

        logger.info(f"Clarification answered: {question[:50]}...")

        # Update business_context with clarification (with timestamp per TODO.md)
        # Only store if the response contains meaningful content
        from backend.services.insight_parser import is_valid_insight_response

        if is_valid_insight_response(answer):
            business_context = state.get("business_context") or {}
            if not isinstance(business_context, dict):
                business_context = {}
            clarifications = business_context.get("clarifications", {})
            # Store with validated structure
            from backend.api.context.services import normalize_clarification_for_storage

            clarification_entry = {
                "answer": answer,
                "answered_at": datetime.now(UTC).isoformat(),
                "session_id": state.get("session_id"),
                "source": "meeting",
            }
            clarifications[question] = normalize_clarification_for_storage(clarification_entry)
            business_context["clarifications"] = clarifications
        else:
            logger.debug(
                f"Skipping storage of invalid insight response: {answer[:50] if answer else 'None'}..."
            )
            business_context = state.get("business_context") or {}

        return {
            "business_context": business_context,
            "pending_clarification": None,
            "current_node": "clarification",
        }

    elif choice == "2":
        # Pause session
        logger.info("User requested session pause for clarification")

        return {
            "should_stop": True,
            "stop_reason": "clarification_needed",
            "pending_clarification": pending_clarification,
            "current_node": "clarification",
        }

    else:
        # Skip question
        logger.info(f"User skipped clarification: {question[:50]}...")

        return {
            "pending_clarification": None,
            "current_node": "clarification",
        }
