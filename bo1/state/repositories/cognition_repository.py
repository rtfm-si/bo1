"""Cognition repository for cognitive profile operations.

Handles:
- Cognitive profile CRUD
- Lite assessment (onboarding)
- Tier 2 assessment
- Meeting count tracking for tier unlock
- Blindspot computation
"""

import logging
from collections.abc import Callable
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any, cast

from psycopg2.extras import Json

from bo1.state.repositories.base import BaseRepository

logger = logging.getLogger(__name__)

# Tier 2 unlock threshold (number of completed meetings)
TIER2_UNLOCK_THRESHOLD = 3

# Blindspot detection rules
# Each rule: condition function, label, compensation advice
BLINDSPOT_RULES = {
    "short_term_bias": {
        "condition": lambda p: _get_decimal(p, "gravity_time_horizon", 0.5) < 0.3,
        "label": "Short-term focus",
        "compensation": "Highlight 6-12 month consequences of each option",
    },
    "long_term_bias": {
        "condition": lambda p: _get_decimal(p, "gravity_time_horizon", 0.5) > 0.8,
        "label": "Over-planning tendency",
        "compensation": "Emphasize immediate actionable steps and quick wins",
    },
    "analysis_paralysis": {
        "condition": lambda p: (
            _get_decimal(p, "gravity_information_density", 0.5) > 0.7
            and _get_decimal(p, "friction_ambiguity_tolerance", 0.5) > 0.6
        ),
        "label": "Analysis paralysis risk",
        "compensation": "Provide 'good enough' thresholds and deadline suggestions",
    },
    "risk_blindness": {
        "condition": lambda p: _get_decimal(p, "friction_risk_sensitivity", 0.5) < 0.25,
        "label": "Risk blindness",
        "compensation": "Present worst-case scenarios explicitly",
    },
    "over_caution": {
        "condition": lambda p: (
            _get_decimal(p, "friction_risk_sensitivity", 0.5) > 0.75
            and _get_decimal(p, "uncertainty_threat_lens", 0.5) > 0.7
        ),
        "label": "Over-caution",
        "compensation": "Highlight opportunity costs of inaction and decision reversibility",
    },
    "delegation_avoidance": {
        "condition": lambda p: _get_decimal(p, "gravity_control_style", 0.5) > 0.8,
        "label": "Delegation avoidance",
        "compensation": "Suggest specific delegation options and trust-building experiments",
    },
    "complexity_seeking": {
        "condition": lambda p: (
            _get_decimal(p, "friction_cognitive_load", 0.5) < 0.3
            and _get_decimal(p, "gravity_information_density", 0.5) > 0.7
        ),
        "label": "Complexity seeking",
        "compensation": "Present simpler alternatives alongside complex solutions",
    },
    "novelty_aversion": {
        "condition": lambda p: _get_decimal(p, "uncertainty_exploration_drive", 0.5) < 0.25,
        "label": "Novelty aversion",
        "compensation": "Frame new approaches as extensions of familiar patterns",
    },
}


def _get_decimal(profile: dict[str, Any], key: str, default: float) -> float:
    """Safely get a decimal value from profile, converting to float."""
    value = profile.get(key)
    if value is None:
        return default
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


class CognitionRepository(BaseRepository):
    """Repository for cognitive profile data."""

    # =========================================================================
    # Profile CRUD
    # =========================================================================

    def get_profile(self, user_id: str) -> dict[str, Any] | None:
        """Get user's cognitive profile.

        Args:
            user_id: User identifier

        Returns:
            Profile dict or None if not exists
        """
        self._validate_id(user_id, "user_id")

        row = self._execute_one(
            """
            SELECT
                id, user_id,
                gravity_time_horizon, gravity_information_density, gravity_control_style,
                gravity_assessed_at,
                friction_risk_sensitivity, friction_cognitive_load, friction_ambiguity_tolerance,
                friction_assessed_at,
                uncertainty_threat_lens, uncertainty_control_need, uncertainty_exploration_drive,
                uncertainty_assessed_at,
                tier2_unlocked, tier2_unlocked_at, completed_meetings_count,
                leverage_structural, leverage_informational, leverage_relational, leverage_temporal,
                leverage_assessed_at,
                tension_autonomy_security, tension_mastery_speed, tension_growth_stability,
                tension_assessed_at,
                time_bias_score, time_bias_assessed_at,
                behavioral_observations, primary_blindspots, cognitive_style_summary,
                created_at, updated_at
            FROM user_cognition
            WHERE user_id = %s
            """,
            (user_id,),
            user_id=user_id,
        )

        if not row:
            return None

        # Convert decimals to floats for JSON serialization
        return self._convert_profile_types(row)

    def _convert_profile_types(self, row: dict[str, Any]) -> dict[str, Any]:
        """Convert database types to JSON-serializable types."""
        result = {}
        for key, value in row.items():
            if isinstance(value, Decimal):
                result[key] = float(value)
            elif hasattr(value, "isoformat"):
                result[key] = value.isoformat()
            else:
                result[key] = value
        return result

    def ensure_profile_exists(self, user_id: str) -> dict[str, Any]:
        """Ensure a cognitive profile exists for user, creating if needed.

        Args:
            user_id: User identifier

        Returns:
            Profile dict (existing or newly created)
        """
        self._validate_id(user_id, "user_id")

        row = self._execute_one(
            """
            INSERT INTO user_cognition (user_id)
            VALUES (%s)
            ON CONFLICT (user_id) DO UPDATE
            SET updated_at = NOW()
            RETURNING *
            """,
            (user_id,),
            user_id=user_id,
        )

        return self._convert_profile_types(row) if row else {}

    # =========================================================================
    # Lite Assessment (Onboarding - Tier 1)
    # =========================================================================

    def save_lite_assessment(
        self,
        user_id: str,
        responses: dict[str, float],
    ) -> dict[str, Any]:
        """Save lite (onboarding) assessment responses.

        Saves Tier 1 dimensions:
        - gravity_time_horizon, gravity_information_density, gravity_control_style
        - friction_risk_sensitivity, friction_cognitive_load, friction_ambiguity_tolerance
        - uncertainty_threat_lens, uncertainty_control_need, uncertainty_exploration_drive

        Args:
            user_id: User identifier
            responses: Dict mapping dimension names to 0-1 values

        Returns:
            Updated profile dict
        """
        self._validate_id(user_id, "user_id")

        now = datetime.now(UTC)

        # Ensure profile exists first
        self.ensure_profile_exists(user_id)

        # Update Tier 1 dimensions
        row = self._execute_returning(
            """
            UPDATE user_cognition
            SET
                gravity_time_horizon = %s,
                gravity_information_density = %s,
                gravity_control_style = %s,
                gravity_assessed_at = %s,
                friction_risk_sensitivity = %s,
                friction_cognitive_load = %s,
                friction_ambiguity_tolerance = %s,
                friction_assessed_at = %s,
                uncertainty_threat_lens = %s,
                uncertainty_control_need = %s,
                uncertainty_exploration_drive = %s,
                uncertainty_assessed_at = %s,
                updated_at = %s
            WHERE user_id = %s
            RETURNING *
            """,
            (
                responses.get("gravity_time_horizon"),
                responses.get("gravity_information_density"),
                responses.get("gravity_control_style"),
                now,
                responses.get("friction_risk_sensitivity"),
                responses.get("friction_cognitive_load"),
                responses.get("friction_ambiguity_tolerance"),
                now,
                responses.get("uncertainty_threat_lens"),
                responses.get("uncertainty_control_need"),
                responses.get("uncertainty_exploration_drive"),
                now,
                now,
                user_id,
            ),
            user_id=user_id,
        )

        profile = self._convert_profile_types(row)

        # Compute and save blindspots
        blindspots = self.compute_blindspots(profile)
        self._update_blindspots(user_id, blindspots)

        # Generate style summary
        summary = self._generate_style_summary(profile)
        self._update_style_summary(user_id, summary)

        profile["primary_blindspots"] = blindspots
        profile["cognitive_style_summary"] = summary

        logger.info(f"Saved lite assessment for user {user_id[:8]}...")
        return profile

    # =========================================================================
    # Tier 2 Assessment
    # =========================================================================

    def save_tier2_assessment(
        self,
        user_id: str,
        instrument: str,
        responses: dict[str, float],
    ) -> dict[str, Any]:
        """Save Tier 2 assessment for specific instrument.

        Args:
            user_id: User identifier
            instrument: One of 'leverage', 'tension', 'time_bias'
            responses: Dict mapping dimension names to values

        Returns:
            Updated profile dict

        Raises:
            ValueError: If instrument is invalid or tier2 not unlocked
        """
        self._validate_id(user_id, "user_id")

        # Verify tier2 is unlocked
        profile = self.get_profile(user_id)
        if not profile or not profile.get("tier2_unlocked"):
            raise ValueError("Tier 2 is not unlocked for this user")

        now = datetime.now(UTC)

        if instrument == "leverage":
            row = self._execute_returning(
                """
                UPDATE user_cognition
                SET
                    leverage_structural = %s,
                    leverage_informational = %s,
                    leverage_relational = %s,
                    leverage_temporal = %s,
                    leverage_assessed_at = %s,
                    updated_at = %s
                WHERE user_id = %s
                RETURNING *
                """,
                (
                    responses.get("leverage_structural"),
                    responses.get("leverage_informational"),
                    responses.get("leverage_relational"),
                    responses.get("leverage_temporal"),
                    now,
                    now,
                    user_id,
                ),
                user_id=user_id,
            )
        elif instrument == "tension":
            row = self._execute_returning(
                """
                UPDATE user_cognition
                SET
                    tension_autonomy_security = %s,
                    tension_mastery_speed = %s,
                    tension_growth_stability = %s,
                    tension_assessed_at = %s,
                    updated_at = %s
                WHERE user_id = %s
                RETURNING *
                """,
                (
                    responses.get("tension_autonomy_security"),
                    responses.get("tension_mastery_speed"),
                    responses.get("tension_growth_stability"),
                    now,
                    now,
                    user_id,
                ),
                user_id=user_id,
            )
        elif instrument == "time_bias":
            row = self._execute_returning(
                """
                UPDATE user_cognition
                SET
                    time_bias_score = %s,
                    time_bias_assessed_at = %s,
                    updated_at = %s
                WHERE user_id = %s
                RETURNING *
                """,
                (
                    responses.get("time_bias_score"),
                    now,
                    now,
                    user_id,
                ),
                user_id=user_id,
            )
        else:
            raise ValueError(f"Invalid instrument: {instrument}")

        profile = self._convert_profile_types(row)

        # Recompute blindspots with new data
        blindspots = self.compute_blindspots(profile)
        self._update_blindspots(user_id, blindspots)
        profile["primary_blindspots"] = blindspots

        logger.info(f"Saved {instrument} assessment for user {user_id[:8]}...")
        return profile

    # =========================================================================
    # Meeting Count & Tier 2 Unlock
    # =========================================================================

    def increment_meeting_count(self, user_id: str) -> int:
        """Increment completed meetings count and check for tier2 unlock.

        Args:
            user_id: User identifier

        Returns:
            New meeting count
        """
        self._validate_id(user_id, "user_id")

        # Ensure profile exists
        self.ensure_profile_exists(user_id)

        # Increment count
        row = self._execute_one(
            """
            UPDATE user_cognition
            SET
                completed_meetings_count = completed_meetings_count + 1,
                updated_at = NOW()
            WHERE user_id = %s
            RETURNING completed_meetings_count, tier2_unlocked
            """,
            (user_id,),
            user_id=user_id,
        )

        count = row["completed_meetings_count"] if row else 0
        tier2_unlocked = row["tier2_unlocked"] if row else False

        # Check for tier2 unlock
        if count >= TIER2_UNLOCK_THRESHOLD and not tier2_unlocked:
            self._unlock_tier2(user_id)
            logger.info(f"User {user_id[:8]}... unlocked Tier 2 after {count} meetings")

        return count

    def _unlock_tier2(self, user_id: str) -> None:
        """Mark tier2 as unlocked for user."""
        self._execute_count(
            """
            UPDATE user_cognition
            SET tier2_unlocked = true, tier2_unlocked_at = NOW(), updated_at = NOW()
            WHERE user_id = %s
            """,
            (user_id,),
            user_id=user_id,
        )

    # =========================================================================
    # Blindspot Computation
    # =========================================================================

    def compute_blindspots(self, profile: dict[str, Any]) -> list[dict[str, str]]:
        """Compute primary blindspots from profile dimensions.

        Args:
            profile: Cognitive profile dict

        Returns:
            List of blindspot dicts with label and compensation
        """
        blindspots = []

        for rule_id, rule in BLINDSPOT_RULES.items():
            try:
                condition = cast(Callable[[dict[str, Any]], bool], rule["condition"])
                if condition(profile):
                    blindspots.append(
                        {
                            "id": rule_id,
                            "label": str(rule["label"]),
                            "compensation": str(rule["compensation"]),
                        }
                    )
            except Exception as e:
                logger.warning(f"Error evaluating blindspot rule {rule_id}: {e}")

        # Limit to top 3 blindspots
        return blindspots[:3]

    def _update_blindspots(self, user_id: str, blindspots: list[dict[str, str]]) -> None:
        """Update primary_blindspots for user."""
        self._execute_count(
            """
            UPDATE user_cognition
            SET primary_blindspots = %s, updated_at = NOW()
            WHERE user_id = %s
            """,
            (Json(blindspots), user_id),
            user_id=user_id,
        )

    # =========================================================================
    # Style Summary Generation
    # =========================================================================

    def _generate_style_summary(self, profile: dict[str, Any]) -> str:
        """Generate a one-liner cognitive style summary.

        Args:
            profile: Cognitive profile dict

        Returns:
            Human-readable style summary
        """
        parts = []

        # Time horizon
        th = _get_decimal(profile, "gravity_time_horizon", 0.5)
        if th < 0.35:
            parts.append("action-oriented")
        elif th > 0.65:
            parts.append("strategic")
        else:
            parts.append("balanced")

        # Information style
        info = _get_decimal(profile, "gravity_information_density", 0.5)
        if info < 0.35:
            parts.append("big-picture thinker")
        elif info > 0.65:
            parts.append("detail-focused")

        # Risk style
        risk = _get_decimal(profile, "friction_risk_sensitivity", 0.5)
        if risk < 0.35:
            parts.append("who embraces calculated risks")
        elif risk > 0.65:
            parts.append("who values careful analysis")

        # Exploration
        explore = _get_decimal(profile, "uncertainty_exploration_drive", 0.5)
        if explore > 0.65:
            parts.append("and thrives on new challenges")
        elif explore < 0.35:
            parts.append("and prefers proven approaches")

        if len(parts) >= 2:
            return f"A {parts[0]}, {parts[1]}" + (
                " " + " ".join(parts[2:]) if len(parts) > 2 else ""
            )
        return "Cognitive profile in progress"

    def _update_style_summary(self, user_id: str, summary: str) -> None:
        """Update cognitive_style_summary for user."""
        self._execute_count(
            """
            UPDATE user_cognition
            SET cognitive_style_summary = %s, updated_at = NOW()
            WHERE user_id = %s
            """,
            (summary, user_id),
            user_id=user_id,
        )

    # =========================================================================
    # Behavioral Observations
    # =========================================================================

    def update_behavioral_observation(
        self,
        user_id: str,
        metric: str,
        value: float | int,
    ) -> None:
        """Update a behavioral observation metric.

        Uses JSONB merge to update single metric without overwriting others.

        Args:
            user_id: User identifier
            metric: Metric name (e.g., 'decision_speed_avg_ms')
            value: Metric value
        """
        self._validate_id(user_id, "user_id")

        # Ensure profile exists
        self.ensure_profile_exists(user_id)

        # Update single metric in JSONB
        self._execute_count(
            """
            UPDATE user_cognition
            SET
                behavioral_observations = behavioral_observations || %s::jsonb,
                updated_at = NOW()
            WHERE user_id = %s
            """,
            (Json({metric: value, "last_observation_at": datetime.now(UTC).isoformat()}), user_id),
            user_id=user_id,
        )

    def track_meeting_completion(
        self,
        user_id: str,
        duration_seconds: int,
        rounds_count: int,
        clarifications_asked: int,
        clarifications_skipped: int,
    ) -> None:
        """Track behavioral metrics from a completed meeting.

        Updates rolling averages for:
        - avg_meeting_duration_seconds
        - avg_rounds_per_meeting
        - clarification_skip_rate (skipped / total asked)

        Args:
            user_id: User identifier
            duration_seconds: Time from session start to completion
            rounds_count: Number of deliberation rounds
            clarifications_asked: Total clarification questions presented
            clarifications_skipped: Number of clarifications user skipped
        """
        self._validate_id(user_id, "user_id")

        # Ensure profile exists
        profile = self.get_profile(user_id)
        if not profile:
            self.ensure_profile_exists(user_id)
            profile = self.get_profile(user_id) or {}

        # Get existing observations
        obs = profile.get("behavioral_observations", {})
        meeting_count = profile.get("completed_meetings_count", 1)

        # Calculate rolling averages
        # For first meeting, just use the value; for subsequent, compute weighted average
        prev_avg_duration = obs.get("avg_meeting_duration_seconds", duration_seconds)
        prev_avg_rounds = obs.get("avg_rounds_per_meeting", rounds_count)

        if meeting_count <= 1:
            new_avg_duration = duration_seconds
            new_avg_rounds = rounds_count
        else:
            # Weighted rolling average (give more weight to recent)
            weight = 0.3  # 30% weight to new value
            new_avg_duration = int(prev_avg_duration * (1 - weight) + duration_seconds * weight)
            new_avg_rounds = round(prev_avg_rounds * (1 - weight) + rounds_count * weight, 1)

        # Calculate clarification skip rate (lifetime)
        total_asked = obs.get("total_clarifications_asked", 0) + clarifications_asked
        total_skipped = obs.get("total_clarifications_skipped", 0) + clarifications_skipped
        skip_rate = round(total_skipped / total_asked, 2) if total_asked > 0 else 0.0

        # Update observations
        updates = {
            "avg_meeting_duration_seconds": new_avg_duration,
            "avg_rounds_per_meeting": new_avg_rounds,
            "total_clarifications_asked": total_asked,
            "total_clarifications_skipped": total_skipped,
            "clarification_skip_rate": skip_rate,
            "last_meeting_duration_seconds": duration_seconds,
            "last_meeting_rounds": rounds_count,
            "last_observation_at": datetime.now(UTC).isoformat(),
        }

        self._execute_count(
            """
            UPDATE user_cognition
            SET
                behavioral_observations = behavioral_observations || %s::jsonb,
                updated_at = NOW()
            WHERE user_id = %s
            """,
            (Json(updates), user_id),
            user_id=user_id,
        )
        logger.info(
            f"Tracked meeting behavior for user {user_id[:8]}...: "
            f"duration={duration_seconds}s, rounds={rounds_count}, skip_rate={skip_rate}"
        )

    def update_action_completion_rate(self, user_id: str, completion_rate: float) -> None:
        """Update the action completion rate metric.

        Args:
            user_id: User identifier
            completion_rate: Ratio of completed actions (0.0 to 1.0)
        """
        self._validate_id(user_id, "user_id")
        self.ensure_profile_exists(user_id)

        self._execute_count(
            """
            UPDATE user_cognition
            SET
                behavioral_observations = behavioral_observations || %s::jsonb,
                updated_at = NOW()
            WHERE user_id = %s
            """,
            (
                Json(
                    {
                        "action_completion_rate": round(completion_rate, 2),
                        "action_rate_updated_at": datetime.now(UTC).isoformat(),
                    }
                ),
                user_id,
            ),
            user_id=user_id,
        )

    # =========================================================================
    # Profile for Prompt Injection
    # =========================================================================

    def get_profile_for_prompt(self, user_id: str) -> dict[str, Any] | None:
        """Get cognitive profile optimized for prompt injection.

        Returns only the fields needed for prompt context building.

        Args:
            user_id: User identifier

        Returns:
            Simplified profile dict or None
        """
        profile = self.get_profile(user_id)
        if not profile:
            return None

        # Check if tier1 is assessed (at least gravity)
        if not profile.get("gravity_assessed_at"):
            return None

        return {
            "gravity_time_horizon": profile.get("gravity_time_horizon"),
            "gravity_information_density": profile.get("gravity_information_density"),
            "gravity_control_style": profile.get("gravity_control_style"),
            "friction_risk_sensitivity": profile.get("friction_risk_sensitivity"),
            "friction_cognitive_load": profile.get("friction_cognitive_load"),
            "friction_ambiguity_tolerance": profile.get("friction_ambiguity_tolerance"),
            "uncertainty_threat_lens": profile.get("uncertainty_threat_lens"),
            "uncertainty_control_need": profile.get("uncertainty_control_need"),
            "uncertainty_exploration_drive": profile.get("uncertainty_exploration_drive"),
            "primary_blindspots": profile.get("primary_blindspots", []),
            "cognitive_style_summary": profile.get("cognitive_style_summary"),
        }


# Singleton instance
cognition_repository = CognitionRepository()
