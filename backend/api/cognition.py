"""Cognition API endpoints.

Provides cognitive profiling endpoints:
- GET /api/v1/cognition - Get current cognitive profile
- POST /api/v1/cognition/lite - Submit lite assessment (onboarding)
- POST /api/v1/cognition/assess - Submit tier 2 assessment
- GET /api/v1/cognition/insights - Get blindspot insights
"""

import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, ValidationInfo, field_validator

from backend.api.middleware.auth import get_current_user
from backend.api.utils.auth_helpers import extract_user_id
from backend.api.utils.errors import handle_api_errors, http_error
from bo1.logging.errors import ErrorCode
from bo1.state.repositories.cognition_repository import (
    TIER2_UNLOCK_THRESHOLD,
    cognition_repository,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/cognition", tags=["cognition"])


# =============================================================================
# Request/Response Models
# =============================================================================


class GravityProfile(BaseModel):
    """Cognitive Gravity Map profile."""

    time_horizon: float | None = Field(None, ge=0, le=1, description="0=immediate, 1=long-term")
    information_density: float | None = Field(None, ge=0, le=1, description="0=summary, 1=detail")
    control_style: float | None = Field(None, ge=0, le=1, description="0=delegate, 1=hands-on")
    assessed_at: str | None = None


class FrictionProfile(BaseModel):
    """Decision Friction Profile."""

    risk_sensitivity: float | None = Field(None, ge=0, le=1, description="0=tolerant, 1=averse")
    cognitive_load: float | None = Field(None, ge=0, le=1, description="0=complex, 1=simple")
    ambiguity_tolerance: float | None = Field(
        None, ge=0, le=1, description="0=tolerant, 1=needs clarity"
    )
    assessed_at: str | None = None


class UncertaintyProfile(BaseModel):
    """Uncertainty Posture Matrix profile."""

    threat_lens: float | None = Field(None, ge=0, le=1, description="0=opportunity, 1=threat")
    control_need: float | None = Field(None, ge=0, le=1, description="0=flow, 1=control")
    exploration_drive: float | None = Field(None, ge=0, le=1, description="0=cautious, 1=explorer")
    assessed_at: str | None = None


class LeverageProfile(BaseModel):
    """Leverage Instinct Index profile (Tier 2)."""

    structural: float | None = Field(None, ge=0, le=1, description="Systems/processes preference")
    informational: float | None = Field(None, ge=0, le=1, description="Data/research preference")
    relational: float | None = Field(None, ge=0, le=1, description="People/networks preference")
    temporal: float | None = Field(None, ge=0, le=1, description="Timing/patience preference")
    assessed_at: str | None = None


class TensionProfile(BaseModel):
    """Value Tension Scan profile (Tier 2)."""

    autonomy_security: float | None = Field(
        None, ge=-1, le=1, description="-1=autonomy, +1=security"
    )
    mastery_speed: float | None = Field(None, ge=-1, le=1, description="-1=mastery, +1=speed")
    growth_stability: float | None = Field(None, ge=-1, le=1, description="-1=growth, +1=stability")
    assessed_at: str | None = None


class TimeBiasProfile(BaseModel):
    """Strategic Time Bias profile (Tier 2)."""

    score: float | None = Field(None, ge=0, le=1, description="0=short-term, 1=long-term")
    assessed_at: str | None = None


class Blindspot(BaseModel):
    """Identified blindspot."""

    id: str
    label: str
    compensation: str


class UnlockPrompt(BaseModel):
    """Tier 2 unlock prompt info."""

    show: bool = False
    message: str = ""
    meetings_remaining: int = 0


class CognitionProfileResponse(BaseModel):
    """Full cognitive profile response."""

    exists: bool = Field(False, description="Whether profile exists")

    # Tier 1 instruments
    gravity: GravityProfile | None = None
    friction: FrictionProfile | None = None
    uncertainty: UncertaintyProfile | None = None

    # Tier 2 status
    tier2_unlocked: bool = False
    tier2_unlocked_at: str | None = None

    # Tier 2 instruments (null if not unlocked/assessed)
    leverage: LeverageProfile | None = None
    tension: TensionProfile | None = None
    time_bias: TimeBiasProfile | None = None

    # Computed insights
    primary_blindspots: list[Blindspot] = Field(default_factory=list)
    cognitive_style_summary: str | None = None

    # Progress tracking
    completed_meetings_count: int = 0
    unlock_prompt: UnlockPrompt | None = None


class LiteAssessmentRequest(BaseModel):
    """Lite assessment (onboarding) request."""

    # Gravity dimensions
    gravity_time_horizon: float = Field(..., ge=0, le=1)
    gravity_information_density: float = Field(..., ge=0, le=1)
    gravity_control_style: float = Field(..., ge=0, le=1)

    # Friction dimensions
    friction_risk_sensitivity: float = Field(..., ge=0, le=1)
    friction_cognitive_load: float = Field(..., ge=0, le=1)
    friction_ambiguity_tolerance: float = Field(..., ge=0, le=1)

    # Uncertainty dimensions
    uncertainty_threat_lens: float = Field(..., ge=0, le=1)
    uncertainty_control_need: float = Field(..., ge=0, le=1)
    uncertainty_exploration_drive: float = Field(..., ge=0, le=1)


class LiteAssessmentResponse(BaseModel):
    """Lite assessment response."""

    success: bool = True
    profile_summary: str = Field(..., description="One-liner cognitive style summary")
    primary_blindspots: list[Blindspot] = Field(default_factory=list)


class Tier2AssessmentRequest(BaseModel):
    """Tier 2 assessment request."""

    instrument: Literal["leverage", "tension", "time_bias"]
    responses: dict[str, float]

    @field_validator("responses")
    @classmethod
    def validate_responses(cls, v: dict[str, float], info: ValidationInfo) -> dict[str, float]:
        """Validate response values are in valid range."""
        for key, value in v.items():
            if "tension" in info.data.get("instrument", ""):
                # Tension values are -1 to 1
                if not -1 <= value <= 1:
                    raise ValueError(f"{key} must be between -1 and 1")
            else:
                # Other values are 0 to 1
                if not 0 <= value <= 1:
                    raise ValueError(f"{key} must be between 0 and 1")
        return v


class InsightItem(BaseModel):
    """Single insight item."""

    key: str
    title: str
    description: str
    recommendation: str


class CognitionInsightsResponse(BaseModel):
    """Cognitive insights response."""

    insights: list[InsightItem] = Field(default_factory=list)
    blindspots: list[Blindspot] = Field(default_factory=list)


# =============================================================================
# Helper Functions
# =============================================================================


def _build_profile_response(profile: dict[str, Any] | None) -> CognitionProfileResponse:
    """Build CognitionProfileResponse from database profile."""
    if not profile:
        return CognitionProfileResponse(exists=False)

    # Build Tier 1 profiles
    gravity = GravityProfile(
        time_horizon=profile.get("gravity_time_horizon"),
        information_density=profile.get("gravity_information_density"),
        control_style=profile.get("gravity_control_style"),
        assessed_at=profile.get("gravity_assessed_at"),
    )

    friction = FrictionProfile(
        risk_sensitivity=profile.get("friction_risk_sensitivity"),
        cognitive_load=profile.get("friction_cognitive_load"),
        ambiguity_tolerance=profile.get("friction_ambiguity_tolerance"),
        assessed_at=profile.get("friction_assessed_at"),
    )

    uncertainty = UncertaintyProfile(
        threat_lens=profile.get("uncertainty_threat_lens"),
        control_need=profile.get("uncertainty_control_need"),
        exploration_drive=profile.get("uncertainty_exploration_drive"),
        assessed_at=profile.get("uncertainty_assessed_at"),
    )

    # Build Tier 2 profiles if unlocked
    tier2_unlocked = profile.get("tier2_unlocked", False)
    leverage = None
    tension = None
    time_bias = None

    if tier2_unlocked:
        leverage = LeverageProfile(
            structural=profile.get("leverage_structural"),
            informational=profile.get("leverage_informational"),
            relational=profile.get("leverage_relational"),
            temporal=profile.get("leverage_temporal"),
            assessed_at=profile.get("leverage_assessed_at"),
        )
        tension = TensionProfile(
            autonomy_security=profile.get("tension_autonomy_security"),
            mastery_speed=profile.get("tension_mastery_speed"),
            growth_stability=profile.get("tension_growth_stability"),
            assessed_at=profile.get("tension_assessed_at"),
        )
        time_bias = TimeBiasProfile(
            score=profile.get("time_bias_score"),
            assessed_at=profile.get("time_bias_assessed_at"),
        )

    # Build blindspots
    raw_blindspots = profile.get("primary_blindspots", [])
    blindspots = [Blindspot(**bs) for bs in raw_blindspots if isinstance(bs, dict)]

    # Build unlock prompt
    meetings_count = profile.get("completed_meetings_count", 0)
    meetings_remaining = max(0, TIER2_UNLOCK_THRESHOLD - meetings_count)
    unlock_prompt = None

    if not tier2_unlocked and meetings_remaining <= 2 and meetings_remaining > 0:
        unlock_prompt = UnlockPrompt(
            show=True,
            message=f"Complete {meetings_remaining} more meeting{'s' if meetings_remaining > 1 else ''} to unlock advanced cognitive profiling",
            meetings_remaining=meetings_remaining,
        )
    elif tier2_unlocked and not profile.get("leverage_assessed_at"):
        unlock_prompt = UnlockPrompt(
            show=True,
            message="Advanced profiling unlocked! Complete your full cognitive profile for better recommendations.",
            meetings_remaining=0,
        )

    return CognitionProfileResponse(
        exists=True,
        gravity=gravity,
        friction=friction,
        uncertainty=uncertainty,
        tier2_unlocked=tier2_unlocked,
        tier2_unlocked_at=profile.get("tier2_unlocked_at"),
        leverage=leverage,
        tension=tension,
        time_bias=time_bias,
        primary_blindspots=blindspots,
        cognitive_style_summary=profile.get("cognitive_style_summary"),
        completed_meetings_count=meetings_count,
        unlock_prompt=unlock_prompt,
    )


# =============================================================================
# Endpoints
# =============================================================================


@router.get("", response_model=CognitionProfileResponse)
@handle_api_errors("get cognitive profile")
async def get_cognition_profile(
    current_user: dict = Depends(get_current_user),
) -> CognitionProfileResponse:
    """Get user's cognitive profile.

    Returns the full cognitive profile including:
    - Tier 1 instruments (Gravity, Friction, Uncertainty)
    - Tier 2 instruments if unlocked (Leverage, Tension, Time Bias)
    - Identified blindspots
    - Style summary
    - Unlock progress
    """
    user_id = extract_user_id(current_user)
    profile = cognition_repository.get_profile(user_id)
    return _build_profile_response(profile)


@router.post("/lite", response_model=LiteAssessmentResponse)
@handle_api_errors("submit lite assessment")
async def submit_lite_assessment(
    request: LiteAssessmentRequest,
    current_user: dict = Depends(get_current_user),
) -> LiteAssessmentResponse:
    """Submit lite (onboarding) cognitive assessment.

    Saves Tier 1 dimensions (9 questions):
    - Cognitive Gravity Map (3 dimensions)
    - Decision Friction Profile (3 dimensions)
    - Uncertainty Posture Matrix (3 dimensions)

    Returns profile summary and identified blindspots.
    """
    user_id = extract_user_id(current_user)

    # Convert request to dict for repository
    responses = {
        "gravity_time_horizon": request.gravity_time_horizon,
        "gravity_information_density": request.gravity_information_density,
        "gravity_control_style": request.gravity_control_style,
        "friction_risk_sensitivity": request.friction_risk_sensitivity,
        "friction_cognitive_load": request.friction_cognitive_load,
        "friction_ambiguity_tolerance": request.friction_ambiguity_tolerance,
        "uncertainty_threat_lens": request.uncertainty_threat_lens,
        "uncertainty_control_need": request.uncertainty_control_need,
        "uncertainty_exploration_drive": request.uncertainty_exploration_drive,
    }

    profile = cognition_repository.save_lite_assessment(user_id, responses)

    # Build blindspots response
    raw_blindspots = profile.get("primary_blindspots", [])
    blindspots = [Blindspot(**bs) for bs in raw_blindspots if isinstance(bs, dict)]

    return LiteAssessmentResponse(
        success=True,
        profile_summary=profile.get("cognitive_style_summary", "Profile saved"),
        primary_blindspots=blindspots,
    )


@router.post("/assess", response_model=CognitionProfileResponse)
@handle_api_errors("submit tier 2 assessment")
async def submit_tier2_assessment(
    request: Tier2AssessmentRequest,
    current_user: dict = Depends(get_current_user),
) -> CognitionProfileResponse:
    """Submit Tier 2 cognitive assessment.

    Requires Tier 2 to be unlocked (3+ completed meetings).

    Instruments:
    - leverage: Leverage Instinct Index
    - tension: Value Tension Scan
    - time_bias: Strategic Time Bias

    Returns updated full profile.
    """
    user_id = extract_user_id(current_user)

    try:
        profile = cognition_repository.save_tier2_assessment(
            user_id,
            request.instrument,
            request.responses,
        )
        return _build_profile_response(profile)
    except ValueError as e:
        raise http_error(ErrorCode.VALIDATION_ERROR, str(e), 400) from e


@router.get("/insights", response_model=CognitionInsightsResponse)
@handle_api_errors("get cognitive insights")
async def get_cognition_insights(
    current_user: dict = Depends(get_current_user),
) -> CognitionInsightsResponse:
    """Get personalized cognitive insights.

    Returns insights based on profile analysis and blindspot recommendations.
    """
    user_id = extract_user_id(current_user)
    profile = cognition_repository.get_profile(user_id)

    if not profile or not profile.get("gravity_assessed_at"):
        return CognitionInsightsResponse(insights=[], blindspots=[])

    # Build insights based on profile
    insights = []

    # Time horizon insight
    th = profile.get("gravity_time_horizon")
    if th is not None:
        if th < 0.35:
            insights.append(
                InsightItem(
                    key="time_horizon",
                    title="Action-Oriented",
                    description="You naturally focus on immediate results and quick wins.",
                    recommendation="Balance with periodic strategic reviews to ensure short-term actions align with long-term goals.",
                )
            )
        elif th > 0.65:
            insights.append(
                InsightItem(
                    key="time_horizon",
                    title="Strategic Planner",
                    description="You excel at long-term thinking and seeing the big picture.",
                    recommendation="Set concrete milestones to ensure steady progress toward your vision.",
                )
            )

    # Risk sensitivity insight
    risk = profile.get("friction_risk_sensitivity")
    if risk is not None:
        if risk < 0.35:
            insights.append(
                InsightItem(
                    key="risk_tolerance",
                    title="Risk Comfortable",
                    description="You're comfortable taking calculated risks.",
                    recommendation="Ensure you have adequate fallback plans for high-stakes decisions.",
                )
            )
        elif risk > 0.65:
            insights.append(
                InsightItem(
                    key="risk_tolerance",
                    title="Risk Aware",
                    description="You carefully evaluate risks before committing.",
                    recommendation="Watch for analysis paralysis; sometimes good enough beats perfect.",
                )
            )

    # Build blindspots
    raw_blindspots = profile.get("primary_blindspots", [])
    blindspots = [Blindspot(**bs) for bs in raw_blindspots if isinstance(bs, dict)]

    return CognitionInsightsResponse(
        insights=insights,
        blindspots=blindspots,
    )


# =============================================================================
# CALIBRATION ENDPOINTS
# =============================================================================


class CalibrationOption(BaseModel):
    """Single calibration option."""

    value: float
    label: str


class CalibrationPromptResponse(BaseModel):
    """Calibration prompt for user feedback."""

    show_prompt: bool = False
    question: str | None = None
    options: list[CalibrationOption] = []
    dimension: str | None = None


class CalibrationSubmitRequest(BaseModel):
    """Request to submit calibration response."""

    dimension: str
    value: float = Field(ge=0, le=1)


@router.get("/calibration", response_model=CalibrationPromptResponse)
@handle_api_errors("get calibration prompt")
async def get_calibration_prompt(
    current_user: dict = Depends(get_current_user),
) -> CalibrationPromptResponse:
    """Get a calibration prompt if one is due.

    Calibration prompts are shown periodically to refine inferred dimensions.
    Returns show_prompt=false if no calibration is needed.
    """
    user_id = extract_user_id(current_user)

    if not cognition_repository.should_show_calibration(user_id):
        return CalibrationPromptResponse(show_prompt=False)

    prompt = cognition_repository.get_calibration_prompt(user_id)
    if not prompt:
        return CalibrationPromptResponse(show_prompt=False)

    return CalibrationPromptResponse(
        show_prompt=True,
        question=prompt["question"],
        options=[CalibrationOption(**opt) for opt in prompt["options"]],
        dimension=prompt["dimension"],
    )


@router.post("/calibration", response_model=CognitionProfileResponse)
@handle_api_errors("submit calibration response")
async def submit_calibration(
    request: CalibrationSubmitRequest,
    current_user: dict = Depends(get_current_user),
) -> CognitionProfileResponse:
    """Submit a calibration response.

    Updates the inferred dimension with the user's explicit feedback.
    """
    user_id = extract_user_id(current_user)

    # Validate dimension is a valid inferred dimension
    valid_dimensions = {
        "inferred_planning_depth",
        "inferred_iteration_style",
        "inferred_deadline_response",
        "inferred_accountability_pref",
        "inferred_challenge_appetite",
        "inferred_format_preference",
        "inferred_example_preference",
    }

    if request.dimension not in valid_dimensions:
        raise http_error(
            ErrorCode.VALIDATION_ERROR,
            f"Invalid dimension: {request.dimension}",
            400,
        )

    cognition_repository.save_calibration_response(user_id, request.dimension, request.value)

    profile = cognition_repository.get_profile(user_id)
    return _build_profile_response(profile)
