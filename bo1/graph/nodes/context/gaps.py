"""Information gap identification node."""

import json
import logging
from typing import Any

from bo1.graph.nodes.utils import log_with_session
from bo1.graph.state import DeliberationGraphState
from bo1.graph.utils import ensure_metrics, track_phase_cost
from bo1.utils.checkpoint_helpers import get_attr_safe

logger = logging.getLogger(__name__)


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
    sub_problems = get_attr_safe(problem, "sub_problems", []) or []
    if not sub_problems:
        logger.info("identify_gaps_node: No sub-problems, skipping gap analysis")
        return {"current_node": "identify_gaps"}

    # Get business context
    business_context = state.get("business_context") or {}

    # BUG FIX (P1 #3): Include problem_context in business_context
    # This ensures the information gap analysis considers context already provided by the user
    problem_context = get_attr_safe(problem, "context", "") or ""

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
