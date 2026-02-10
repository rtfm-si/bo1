"""Decision patterns API endpoint (Pattern Detection Dashboard).

Provides:
- GET /api/v1/users/me/decision-patterns - Aggregated pattern analysis
"""

import logging
from collections import defaultdict
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request

from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rate_limit import CONTROL_RATE_LIMIT, limiter
from backend.api.models import (
    BiasFlag,
    ConfidenceCalibration,
    ConstraintAccuracy,
    DecisionPatternsResponse,
    MonthlyTrend,
)
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors
from bo1.state.repositories.user_decision_repository import user_decision_repository

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/users/me/decision-patterns", tags=["decision-patterns"])

MIN_DECISIONS_FOR_PATTERNS = 3


def _compute_bias_flags(
    *,
    avg_confidence: float | None,
    success_rate: float | None,
    matrix_usage_pct: float | None,
    total_decisions: int,
    avg_surprise: float | None,
    outcomes_with_status: int,
    decisions_without_outcome: int,
) -> list[BiasFlag]:
    """Compute bias heuristics from aggregate stats."""
    flags: list[BiasFlag] = []

    # Overconfidence: high confidence but low success
    if (
        avg_confidence is not None
        and success_rate is not None
        and avg_confidence > 0.8
        and success_rate < 0.5
        and outcomes_with_status >= 3
    ):
        flags.append(
            BiasFlag(
                bias_type="overconfidence",
                description="High average confidence but low success rate — calibrate expectations.",
                severity="high",
            )
        )

    # Matrix aversion: rarely uses decision matrix
    if matrix_usage_pct is not None and matrix_usage_pct < 10 and total_decisions > 5:
        flags.append(
            BiasFlag(
                bias_type="matrix_aversion",
                description="Decision matrix used in fewer than 10% of decisions.",
                severity="low",
            )
        )

    # Surprise blindness: outcomes often surprising
    if avg_surprise is not None and avg_surprise > 3.5 and outcomes_with_status >= 3:
        flags.append(
            BiasFlag(
                bias_type="surprise_blindness",
                description="Outcomes are frequently surprising — consider additional risk analysis.",
                severity="medium",
            )
        )

    # Outcome avoidance: > 50% decisions without outcomes after 30d
    if (
        total_decisions > 3
        and decisions_without_outcome > 0
        and (decisions_without_outcome / total_decisions) > 0.5
    ):
        flags.append(
            BiasFlag(
                bias_type="outcome_avoidance",
                description="Most decisions lack recorded outcomes — close the feedback loop.",
                severity="low",
            )
        )

    return flags


@router.get(
    "",
    response_model=DecisionPatternsResponse,
    summary="Get decision-making patterns",
)
@limiter.limit(CONTROL_RATE_LIMIT)
@handle_api_errors("get decision patterns")
async def get_decision_patterns(
    request: Request,
    current_user: dict = Depends(get_current_user),
) -> DecisionPatternsResponse:
    """Compute aggregated decision-making patterns for the current user."""
    user_id = extract_user_id(current_user)

    rows = user_decision_repository.list_with_outcomes(user_id, limit=100)
    total = len(rows)

    if total < MIN_DECISIONS_FOR_PATTERNS:
        return DecisionPatternsResponse(
            has_enough_data=False,
            total_decisions=total,
            confidence_calibration=ConfidenceCalibration(),
        )

    # Aggregate stats
    matrix_count = sum(1 for r in rows if r.get("decision_source") == "matrix")
    matrix_usage_pct = (matrix_count / total * 100) if total > 0 else None

    # Outcome breakdown
    outcome_breakdown: dict[str, int] = {}
    surprise_factors: list[int] = []
    confidence_values: list[float] = []
    successful_count = 0
    outcomes_with_status = 0
    now = datetime.now(UTC)
    decisions_without_outcome_over_30d = 0

    for r in rows:
        # Extract confidence from rationale JSONB (0-100 scale → 0-1)
        rationale = r.get("rationale")
        if isinstance(rationale, dict):
            raw_conf = rationale.get("confidence")
            if raw_conf is not None:
                try:
                    confidence_values.append(float(raw_conf) / 100.0)
                except (TypeError, ValueError):
                    pass
        status = r.get("outcome_status")
        if status:
            outcome_breakdown[status] = outcome_breakdown.get(status, 0) + 1
            outcomes_with_status += 1
            if status == "successful":
                successful_count += 1
            sf = r.get("surprise_factor")
            if sf is not None:
                surprise_factors.append(sf)
        else:
            # Check if decision is older than 30 days
            created = r.get("created_at")
            if created and isinstance(created, datetime):
                if not created.tzinfo:
                    created = created.replace(tzinfo=UTC)
                age = (now - created).days
                if age > 30:
                    decisions_without_outcome_over_30d += 1

    success_rate = (successful_count / outcomes_with_status) if outcomes_with_status > 0 else None
    avg_surprise = (sum(surprise_factors) / len(surprise_factors)) if surprise_factors else None

    avg_confidence = (
        (sum(confidence_values) / len(confidence_values)) if confidence_values else None
    )

    calibration = ConfidenceCalibration(
        avg_confidence=avg_confidence,
        success_rate=success_rate,
        total_with_outcomes=outcomes_with_status,
    )

    # Constraint accuracy aggregation
    violations_chosen = 0
    violations_successful = 0
    tensions_chosen = 0
    tensions_successful = 0
    total_with_constraints = 0
    for r in rows:
        rationale = r.get("rationale")
        if not isinstance(rationale, dict):
            continue
        ca = rationale.get("constraint_alignment")
        if not isinstance(ca, dict) or not ca:
            continue
        total_with_constraints += 1
        status = r.get("outcome_status")
        is_success = status == "successful"
        for _desc, alignment in ca.items():
            if alignment == "violation":
                violations_chosen += 1
                if is_success:
                    violations_successful += 1
            elif alignment == "tension":
                tensions_chosen += 1
                if is_success:
                    tensions_successful += 1

    constraint_accuracy = (
        ConstraintAccuracy(
            total_with_constraints=total_with_constraints,
            violations_chosen=violations_chosen,
            violations_successful=violations_successful,
            tensions_chosen=tensions_chosen,
            tensions_successful=tensions_successful,
        )
        if total_with_constraints > 0
        else None
    )

    # Monthly trend bucketing
    month_buckets: dict[str, dict] = defaultdict(
        lambda: {"total": 0, "outcomes": 0, "successes": 0, "confidences": []}
    )
    for r in rows:
        created = r.get("created_at")
        if not isinstance(created, datetime):
            continue
        month_key = created.strftime("%Y-%m")
        bucket = month_buckets[month_key]
        bucket["total"] += 1
        status = r.get("outcome_status")
        if status:
            bucket["outcomes"] += 1
            if status == "successful":
                bucket["successes"] += 1
        rat = r.get("rationale")
        if isinstance(rat, dict):
            raw_c = rat.get("confidence")
            if raw_c is not None:
                try:
                    bucket["confidences"].append(float(raw_c) / 100.0)
                except (TypeError, ValueError):
                    pass

    monthly_trends = []
    for month_key in sorted(month_buckets):
        b = month_buckets[month_key]
        sr = (b["successes"] / b["outcomes"]) if b["outcomes"] > 0 else None
        ac = (sum(b["confidences"]) / len(b["confidences"])) if b["confidences"] else None
        monthly_trends.append(
            MonthlyTrend(
                month=month_key,
                total_decisions=b["total"],
                outcomes_recorded=b["outcomes"],
                success_rate=sr,
                avg_confidence=ac,
            )
        )

    bias_flags = _compute_bias_flags(
        avg_confidence=calibration.avg_confidence,
        success_rate=success_rate,
        matrix_usage_pct=matrix_usage_pct,
        total_decisions=total,
        avg_surprise=avg_surprise,
        outcomes_with_status=outcomes_with_status,
        decisions_without_outcome=decisions_without_outcome_over_30d,
    )

    return DecisionPatternsResponse(
        has_enough_data=True,
        total_decisions=total,
        confidence_calibration=calibration,
        outcome_breakdown=outcome_breakdown,
        matrix_usage_pct=matrix_usage_pct,
        avg_surprise_factor=avg_surprise,
        bias_flags=bias_flags,
        constraint_accuracy=constraint_accuracy,
        monthly_trends=monthly_trends,
    )
