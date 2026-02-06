"""Quality checks and validation for deliberation contributions.

Contains challenge phase validation, semantic deduplication,
and contribution quality checking.
"""

import logging
from typing import Any

from bo1.constants import SimilarityCacheThresholds
from bo1.graph.state import (
    DeliberationGraphState,
    get_participant_state,
)
from bo1.graph.utils import track_accumulated_cost
from bo1.prompts.validation import (
    generate_challenge_reprompt,
    validate_challenge_phase_contribution,
)
from bo1.utils.checkpoint_helpers import get_problem_context, get_problem_description

logger = logging.getLogger(__name__)


async def _handle_challenge_validation(
    contribution_msgs: list[Any],
    round_number: int,
    state: DeliberationGraphState,
    engine: Any,
    problem: Any,
    participant_list: str,
    contrib_type: Any,
    contributions: list[Any],
    dependency_context: str | None,
    subproblem_context: str | None,
    research_results: list[Any],
    metrics: Any,
) -> list[Any]:
    """Handle challenge phase validation with optional hard mode retry.

    In soft mode: logs failures and returns original contributions.
    In hard mode: re-prompts failed experts once, accepts with warning if retry fails.

    Args:
        contribution_msgs: List of contributions to validate
        round_number: Current round (3 or 4)
        state: Current deliberation state
        engine: DeliberationEngine instance
        problem: Problem object
        participant_list: Comma-separated participant names
        contrib_type: Contribution type enum
        contributions: Previous contributions for context
        dependency_context: Optional dependency context
        subproblem_context: Optional sub-problem context
        research_results: Research results for context
        metrics: Metrics object for cost tracking

    Returns:
        Updated contribution list (may include retried contributions)
    """
    from backend.api.middleware.metrics import (
        record_challenge_rejection,
        record_challenge_retry,
    )
    from bo1.config import get_settings
    from bo1.graph.nodes.rounds.contribution import _build_retry_memory

    settings = get_settings()

    # Validate and get failures
    failed = _validate_challenge_contributions(contribution_msgs, round_number)

    # Soft mode: just return as-is (validation already logged)
    if settings.challenge_validation_mode == "soft" or not failed:
        return contribution_msgs

    # Hard mode: retry failed contributions
    logger.info(f"Challenge validation hard mode: {len(failed)} contributions need retry")

    # Build mapping of contribution to expert for retry
    # We need to find the expert persona for each failed contribution
    participant_state = get_participant_state(state)
    personas = participant_state.get("personas", [])
    persona_map = {p.code: p for p in personas}

    retry_tasks = []
    failed_contribution_codes = set()

    for contrib, validation_result in failed:
        expert_code = getattr(contrib, "persona_code", None)
        if not expert_code or expert_code not in persona_map:
            logger.warning(f"Cannot retry: expert {expert_code} not found in personas")
            continue

        expert = persona_map[expert_code]
        content = getattr(contrib, "content", "")
        failed_contribution_codes.add(expert_code)

        # Record rejection metric
        record_challenge_rejection(
            round_number=round_number,
            expert_type=getattr(contrib, "persona_type", "persona"),
        )

        # Generate reprompt
        reprompt = generate_challenge_reprompt(
            expert_name=expert.display_name,
            detected_markers=validation_result.detected_markers,
            required_markers=validation_result.threshold,
            original_contribution=content,
        )

        # Build retry memory with reprompt
        retry_memory = _build_retry_memory(
            phase="challenge",
            dependency_context=dependency_context,
            subproblem_context=subproblem_context,
            research_results=research_results,
        )
        retry_memory = f"{reprompt}\n\n{retry_memory}"

        retry_task = engine._call_persona_async(
            persona_profile=expert,
            problem_statement=get_problem_description(problem),
            problem_context=get_problem_context(problem),
            participant_list=participant_list,
            round_number=round_number,
            contribution_type=contrib_type,
            previous_contributions=contributions,
            expert_memory=retry_memory,
        )
        retry_tasks.append((expert, contrib, retry_task))

    if not retry_tasks:
        return contribution_msgs

    # Execute retries
    import asyncio

    logger.info(f"Retrying {len(retry_tasks)} challenge-phase contributions")
    retry_results = await asyncio.gather(*[t[2] for t in retry_tasks])

    # Process retry results
    retried_codes = set()
    new_contributions = []

    for (expert, original_contrib, _), (new_contrib, llm_response) in zip(
        retry_tasks, retry_results, strict=True
    ):
        track_accumulated_cost(metrics, f"round_{round_number}_challenge_retry", llm_response)

        # Re-validate the retry
        passed, result = validate_challenge_phase_contribution(
            content=new_contrib.content,
            round_number=round_number,
            expert_name=expert.display_name,
            min_markers=settings.challenge_min_markers,
        )

        # Record retry success/failure metric
        record_challenge_retry(
            success=passed,
            round_number=round_number,
            expert_type=getattr(original_contrib, "persona_type", "persona"),
        )

        if passed:
            logger.info(
                f"Challenge retry SUCCESS for {expert.display_name}: "
                f"now has {result.marker_count} markers"
            )
            new_contributions.append(new_contrib)
        else:
            logger.warning(
                f"Challenge retry FAILED for {expert.display_name}: "
                f"still only {result.marker_count}/{result.threshold} markers. "
                f"Accepting with warning."
            )
            # Accept the retry contribution anyway (it's likely better than original)
            new_contributions.append(new_contrib)

        retried_codes.add(expert.code)

    # Build final contribution list: keep non-failed + add retried
    final_contributions = []
    for contrib in contribution_msgs:
        code = getattr(contrib, "persona_code", None)
        if code not in failed_contribution_codes:
            final_contributions.append(contrib)

    final_contributions.extend(new_contributions)

    logger.info(
        f"Challenge validation complete: {len(final_contributions)} contributions "
        f"({len(retry_tasks)} retried)"
    )

    return final_contributions


def _validate_challenge_contributions(
    contributions: list[Any],
    round_number: int,
    min_markers: int | None = None,
) -> list[tuple[Any, Any]]:
    """Validate challenge phase contributions for critical engagement markers.

    Supports both soft enforcement (log only) and hard enforcement (return failures).
    In hard mode, returns list of (contribution, validation_result) for failures.

    Args:
        contributions: List of ContributionMessage objects
        round_number: Current round number (should be 3 or 4)
        min_markers: Minimum markers required (uses config default if None)

    Returns:
        List of (contribution, validation_result) tuples for failed validations
    """
    from backend.api.middleware.metrics import record_challenge_validation
    from bo1.config import get_settings

    settings = get_settings()
    effective_min_markers = min_markers or settings.challenge_min_markers
    failed_contributions: list[tuple[Any, Any]] = []

    for contribution in contributions:
        expert_name = getattr(contribution, "persona_name", "unknown")
        expert_type = getattr(contribution, "persona_type", "persona")
        content = getattr(contribution, "content", "")

        passed, result = validate_challenge_phase_contribution(
            content=content,
            round_number=round_number,
            expert_name=expert_name,
            expert_type=expert_type,
            min_markers=effective_min_markers,
        )

        # Record metric for monitoring
        record_challenge_validation(
            passed=passed,
            round_number=round_number,
            expert_type=expert_type,
        )

        if not passed:
            logger.info(
                f"Challenge validation: {expert_name} found {result.marker_count}/{result.threshold} markers. "
                f"Detected: {result.detected_markers}"
            )
            failed_contributions.append((contribution, result))

    return failed_contributions


async def _apply_semantic_deduplication(
    contributions: list[Any],
) -> list[Any]:
    """Apply semantic deduplication to filter repetitive contributions.

    Uses embedding similarity to identify and filter duplicate contributions,
    ensuring at least one contribution survives for progress.

    Args:
        contributions: List of ContributionMessage objects

    Returns:
        Filtered list of contributions with duplicates removed
    """
    from bo1.graph.quality.semantic_dedup import filter_duplicate_contributions

    if not contributions:
        return []

    filtered = await filter_duplicate_contributions(
        contributions=contributions,
        threshold=SimilarityCacheThresholds.DUPLICATE_CONTRIBUTION,
    )

    filtered_count = len(contributions) - len(filtered)
    if filtered_count > 0:
        logger.info(
            f"Filtered {filtered_count} duplicate contributions "
            f"({filtered_count / len(contributions):.0%})"
        )

    # FAILSAFE: Ensure at least 1 contribution per round
    if not filtered and contributions:
        logger.warning(
            f"All {len(contributions)} contributions filtered as duplicates. "
            f"Keeping most novel contribution to ensure progress."
        )
        filtered = [contributions[0]]
        logger.info(f"Failsafe: Kept contribution from {contributions[0].persona_name}")

    return filtered


async def _check_contribution_quality(
    contributions: list[Any],
    problem_context: str,
    round_number: int,
    metrics: Any,
    facilitator_guidance: dict[str, Any],
    quality_cache: Any | None = None,
) -> tuple[list[Any], dict[str, Any]]:
    """Check quality of contributions and update facilitator guidance.

    Runs lightweight quality checks on contributions and adds guidance
    for the next round if shallow contributions are detected.

    Args:
        contributions: List of ContributionMessage objects
        problem_context: Problem description for context
        round_number: Current round number
        metrics: Metrics object for cost tracking
        facilitator_guidance: Existing facilitator guidance dict
        quality_cache: Optional QualityCheckCache for caching results

    Returns:
        Tuple of (quality_results, updated_facilitator_guidance)
    """
    from bo1.graph.quality.contribution_check import check_contributions_quality

    if not contributions:
        return [], facilitator_guidance

    try:
        quality_results, quality_responses = await check_contributions_quality(
            contributions=contributions,
            problem_context=problem_context,
            cache=quality_cache,
            round_number=round_number,
        )

        # Track cost for quality checks
        for response in quality_responses:
            if response:  # Skip None responses (heuristic fallbacks)
                track_accumulated_cost(metrics, f"round_{round_number}_quality_check", response)

        # Track quality metrics
        shallow_count = sum(1 for r in quality_results if r.is_shallow)
        avg_quality = sum(r.quality_score for r in quality_results) / len(quality_results)

        logger.info(
            f"Quality check: {shallow_count}/{len(quality_results)} shallow, "
            f"avg score: {avg_quality:.2f}"
        )

        # If any contributions are shallow, add guidance for next round
        if shallow_count > 0:
            shallow_feedback = [
                f"{contributions[i].persona_name}: {quality_results[i].feedback}"
                for i in range(len(quality_results))
                if quality_results[i].is_shallow
            ]

            if "quality_issues" not in facilitator_guidance:
                facilitator_guidance["quality_issues"] = []

            facilitator_guidance["quality_issues"].append(
                {
                    "round": round_number,
                    "shallow_count": shallow_count,
                    "total_count": len(quality_results),
                    "feedback": shallow_feedback,
                    "guidance": (
                        f"Round {round_number} had {shallow_count} shallow contributions. "
                        f"Next round: emphasize concrete details, evidence, and actionable steps."
                    ),
                }
            )

            logger.info(
                f"Added quality guidance for next round: {shallow_count} shallow contributions"
            )

        return quality_results, facilitator_guidance

    except Exception as e:
        logger.warning(f"Quality check failed: {e}. Continuing without quality feedback.")
        return [], facilitator_guidance
