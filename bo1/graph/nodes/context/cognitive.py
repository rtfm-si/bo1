"""Cognitive profile helpers for building personalization context blocks."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


def _get_profile_value(profile: dict[str, Any], key: str, default: float = 0.5) -> float:
    """Safely get a numeric profile value."""
    val = profile.get(key)
    if val is None:
        return default
    try:
        return float(val)
    except (TypeError, ValueError):
        return default


def _build_communication_style(profile: dict[str, Any]) -> list[str]:
    """Build communication style guidance based on cognitive profile."""
    lines = []

    # Information density (0=summary, 1=detail)
    info = _get_profile_value(profile, "gravity_information_density")
    if info < 0.3:
        lines.append("- Lead with conclusions, then support; avoid burying insights in detail")
        lines.append("- Use bullet points over paragraphs; one key insight per point")
    elif info > 0.7:
        lines.append("- Provide detailed analysis with supporting data and edge cases")
        lines.append("- Show your reasoning chain; user values thoroughness over brevity")
    else:
        lines.append("- Balance summary with key supporting details")

    # Cognitive load tolerance (0=thrives on complexity, 1=needs simplicity)
    load = _get_profile_value(profile, "friction_cognitive_load")
    if load > 0.7:
        lines.append("- Limit options to 2-3 clear choices; avoid overwhelming with possibilities")
        lines.append("- Use simple language; avoid jargon unless domain-specific")
    elif load < 0.3:
        lines.append("- User handles complexity well; include nuanced trade-offs and conditionals")

    # Ambiguity tolerance (0=tolerant, 1=needs clarity)
    ambig = _get_profile_value(profile, "friction_ambiguity_tolerance")
    if ambig > 0.7:
        lines.append("- Be definitive; avoid hedging language like 'it depends' or 'possibly'")
        lines.append("- Provide specific numbers, dates, thresholds over ranges")
    elif ambig < 0.3:
        lines.append("- Comfortable with uncertainty; can present probabilistic outcomes")

    return lines


def _build_decision_framing(profile: dict[str, Any]) -> list[str]:
    """Build decision framing guidance based on cognitive profile."""
    lines = []

    # Time horizon (0=immediate, 1=long-term)
    th = _get_profile_value(profile, "gravity_time_horizon")
    if th < 0.3:
        lines.append("- Frame with immediate impact: 'This week you can...' or 'Quick win:'")
        lines.append("- Emphasize speed-to-value over long-term optimization")
    elif th > 0.7:
        lines.append("- Frame with strategic horizon: '6-12 month impact' or 'Foundation for...'")
        lines.append("- Connect tactical actions to long-term positioning")
    else:
        lines.append("- Balance immediate actions with medium-term outcomes (1-3 months)")

    # Risk sensitivity (0=tolerant, 1=averse)
    risk = _get_profile_value(profile, "friction_risk_sensitivity")
    if risk > 0.7:
        lines.append("- Lead with risk mitigation; present downside scenarios first")
        lines.append("- Emphasize reversibility: 'You can always...' or 'Low-commitment test:'")
    elif risk < 0.3:
        lines.append("- Lead with opportunity and upside potential")
        lines.append("- User accepts calculated risks; don't over-hedge recommendations")
    else:
        lines.append("- Present balanced risk/reward; user weighs both")

    # Threat lens (0=sees opportunity, 1=sees threat)
    threat = _get_profile_value(profile, "uncertainty_threat_lens")
    if threat > 0.7:
        lines.append("- Acknowledge risks explicitly before presenting opportunities")
        lines.append("- Frame change as 'protecting against' rather than 'gaining'")
    elif threat < 0.3:
        lines.append("- Frame uncertainty as opportunity space to explore")
        lines.append("- User energized by possibility; lean into 'what if' scenarios")

    return lines


def _build_recommendation_style(profile: dict[str, Any]) -> list[str]:
    """Build recommendation style guidance based on Tier 2 profile."""
    lines = []

    # Exploration drive (0=cautious/proven, 1=explorer/novel)
    explore = _get_profile_value(profile, "uncertainty_exploration_drive")
    if explore > 0.7:
        lines.append("- Include innovative/unconventional options; user values novelty")
        lines.append("- 'Have you considered...' approaches welcome")
    elif explore < 0.3:
        lines.append("- Favor proven, established approaches over experimental")
        lines.append("- Reference industry standards, case studies, precedents")

    # Leverage preferences (Tier 2) - favor recommendations that match natural style
    lev_structural = _get_profile_value(profile, "leverage_structural", 0.0)
    lev_info = _get_profile_value(profile, "leverage_informational", 0.0)
    lev_relational = _get_profile_value(profile, "leverage_relational", 0.0)
    lev_temporal = _get_profile_value(profile, "leverage_temporal", 0.0)

    # Only include if Tier 2 assessed (values > 0)
    if lev_structural > 0.1 or lev_info > 0.1 or lev_relational > 0.1 or lev_temporal > 0.1:
        leverage_prefs = []
        if lev_structural > 0.6:
            leverage_prefs.append("systems/processes")
        if lev_info > 0.6:
            leverage_prefs.append("data/research")
        if lev_relational > 0.6:
            leverage_prefs.append("people/delegation")
        if lev_temporal > 0.6:
            leverage_prefs.append("timing/patience")

        if leverage_prefs:
            lines.append(f"- User creates leverage through: {', '.join(leverage_prefs)}")
            lines.append("- Frame recommendations using these natural strengths")

        # Counter-balance: suggest building weaker areas
        weak_areas = []
        if lev_structural < 0.4 and lev_structural > 0:
            weak_areas.append("systematizing")
        if lev_relational < 0.4 and lev_relational > 0:
            weak_areas.append("delegation")
        if weak_areas:
            lines.append(f"- Gently suggest: consider {', '.join(weak_areas)} where appropriate")

    # Value tensions (Tier 2) - acknowledge trade-offs user struggles with
    t_auto_sec = profile.get("tension_autonomy_security")
    t_mast_speed = profile.get("tension_mastery_speed")
    t_grow_stab = profile.get("tension_growth_stability")

    if t_auto_sec is not None or t_mast_speed is not None or t_grow_stab is not None:
        tensions = []
        if t_auto_sec is not None:
            t = float(t_auto_sec)
            if t < -0.3:
                tensions.append("prioritizes autonomy over security")
            elif t > 0.3:
                tensions.append("prioritizes security over autonomy")
        if t_mast_speed is not None:
            t = float(t_mast_speed)
            if t < -0.3:
                tensions.append("prioritizes mastery/quality over speed")
            elif t > 0.3:
                tensions.append("prioritizes speed over perfection")
        if t_grow_stab is not None:
            t = float(t_grow_stab)
            if t < -0.3:
                tensions.append("growth-oriented, accepts volatility")
            elif t > 0.3:
                tensions.append("stability-oriented, risk-averse to growth")

        if tensions:
            lines.append(f"- User's value priorities: {'; '.join(tensions)}")

    # Time bias (Tier 2)
    time_bias = profile.get("time_bias_score")
    if time_bias is not None:
        tb = float(time_bias)
        if tb < 0.3:
            lines.append("- Short-term optimizer: emphasize immediate ROI, quick payback")
        elif tb > 0.7:
            lines.append(
                "- Long-term investor: comfortable deferring gratification for bigger wins"
            )

    return lines


def _build_action_structure(profile: dict[str, Any]) -> list[str]:
    """Build action item structure guidance."""
    lines = []

    # Control style (0=delegate, 1=hands-on)
    control = _get_profile_value(profile, "gravity_control_style")
    if control > 0.7:
        lines.append("- Provide detailed step-by-step execution plans")
        lines.append("- User wants to do it themselves; include 'how' not just 'what'")
    elif control < 0.3:
        lines.append("- Focus on outcomes and success criteria, not execution details")
        lines.append("- Include delegation suggestions: 'Have someone...' or 'Outsource to...'")
    else:
        lines.append("- Balance outcomes with key execution milestones")

    # Control need (0=comfortable with flow, 1=needs control)
    control_need = _get_profile_value(profile, "uncertainty_control_need")
    if control_need > 0.7:
        lines.append("- Include checkpoints and progress markers")
        lines.append("- Suggest tracking mechanisms and status updates")
    elif control_need < 0.3:
        lines.append("- User comfortable with ambiguous progress; focus on end state")

    return lines


def _build_behavioral_calibration(profile: dict[str, Any]) -> list[str]:
    """Build calibration based on observed behavioral patterns."""
    lines: list[str] = []
    observations = profile.get("behavioral_observations", {})

    if not observations:
        return lines

    # Meeting duration patterns
    avg_duration = observations.get("avg_meeting_duration_seconds")
    if avg_duration:
        if avg_duration < 300:  # < 5 min
            lines.append("- User prefers quick sessions; be concise and actionable")
        elif avg_duration > 900:  # > 15 min
            lines.append("- User engages deeply; thoroughness valued over speed")

    # Clarification skip rate
    skip_rate = observations.get("clarification_skip_rate")
    if skip_rate is not None:
        if skip_rate > 0.5:
            lines.append("- User often skips clarifications; make reasonable assumptions")
        elif skip_rate < 0.2:
            lines.append("- User values thoroughness; ask clarifying questions when uncertain")

    # Action completion rate
    completion_rate = observations.get("action_completion_rate")
    if completion_rate is not None:
        if completion_rate < 0.3:
            lines.append("- Low action completion; suggest fewer, smaller, more specific actions")
            lines.append("- Consider: 'Just do this ONE thing this week'")
        elif completion_rate > 0.7:
            lines.append("- High follow-through; can suggest ambitious action plans")

    # Deliberation depth (rounds)
    avg_rounds = observations.get("avg_rounds")
    if avg_rounds:
        if avg_rounds < 2:
            lines.append("- User decides quickly; lead with strongest recommendation")
        elif avg_rounds > 4:
            lines.append("- User values deliberation; present multiple perspectives")

    return lines


def _build_inferred_dimensions(profile: dict[str, Any]) -> list[str]:
    """Build guidance from inferred cognitive dimensions."""
    lines = []
    confidence = profile.get("inference_confidence", {})

    # Only include dimensions with reasonable confidence
    min_confidence = 0.3

    # Planning depth
    planning = profile.get("inferred_planning_depth")
    if planning is not None and confidence.get("inferred_planning_depth", 0) >= min_confidence:
        if planning < 0.35:
            lines.append("- User prefers minimal planning; keep action plans lean")
        elif planning > 0.65:
            lines.append("- User values thorough planning; include dependencies and sequencing")

    # Iteration style
    iteration = profile.get("inferred_iteration_style")
    if iteration is not None and confidence.get("inferred_iteration_style", 0) >= min_confidence:
        if iteration < 0.35:
            lines.append("- Ship-fast mentality; suggest MVPs and iterations over perfection")
        elif iteration > 0.65:
            lines.append(
                "- Quality-first approach; emphasize getting it right over getting it fast"
            )

    # Deadline response
    deadline = profile.get("inferred_deadline_response")
    if deadline is not None and confidence.get("inferred_deadline_response", 0) >= min_confidence:
        if deadline < 0.35:
            lines.append("- Energized by deadlines; can use time pressure as motivator")
        elif deadline > 0.65:
            lines.append("- Stressed by deadlines; suggest buffer time and realistic timelines")

    # Accountability preference
    accountability = profile.get("inferred_accountability_pref")
    if (
        accountability is not None
        and confidence.get("inferred_accountability_pref", 0) >= min_confidence
    ):
        if accountability > 0.65:
            lines.append("- Benefits from external accountability; suggest check-ins or partners")

    # Challenge appetite
    challenge = profile.get("inferred_challenge_appetite")
    if challenge is not None and confidence.get("inferred_challenge_appetite", 0) >= min_confidence:
        if challenge < 0.35:
            lines.append("- Prefers comfortable wins; suggest incremental improvements")
        elif challenge > 0.65:
            lines.append("- Enjoys stretch goals; can suggest ambitious targets")

    # Format preference
    format_pref = profile.get("inferred_format_preference")
    if (
        format_pref is not None
        and confidence.get("inferred_format_preference", 0) >= min_confidence
    ):
        if format_pref < 0.35:
            lines.append("- Prefers narrative style; use flowing prose over rigid structure")
        elif format_pref > 0.65:
            lines.append("- Prefers structured output; use clear bullets, headers, tables")

    # Example preference
    example_pref = profile.get("inferred_example_preference")
    if (
        example_pref is not None
        and confidence.get("inferred_example_preference", 0) >= min_confidence
    ):
        if example_pref < 0.35:
            lines.append("- Grasps abstract principles; lead with concepts")
        elif example_pref > 0.65:
            lines.append("- Learns from examples; include concrete cases and analogies")

    return lines


def build_cognitive_context_block(profile: dict[str, Any]) -> str:
    """Build cognitive context block for prompt injection.

    Comprehensive personalization based on:
    1. Communication Style - How to present information
    2. Decision Framing - How to frame choices and trade-offs
    3. Recommendation Style - What kind of solutions to favor
    4. Action Structure - How to format action items
    5. Blindspot Compensation - What to actively counter
    6. Behavioral Calibration - Adjustments from observed patterns

    Args:
        profile: Cognitive profile dict from cognition_repository

    Returns:
        Formatted string for injection into problem.context
    """
    if not profile:
        return ""

    lines = ["\n\n## User Cognitive Profile (Personalization Guide)"]

    # Style summary
    if profile.get("cognitive_style_summary"):
        lines.append(f"**Decision Style:** {profile['cognitive_style_summary']}")

    # 1. Communication Style
    comm_lines = _build_communication_style(profile)
    if comm_lines:
        lines.append("\n### Communication Style")
        lines.extend(comm_lines)

    # 2. Decision Framing
    framing_lines = _build_decision_framing(profile)
    if framing_lines:
        lines.append("\n### Decision Framing")
        lines.extend(framing_lines)

    # 3. Recommendation Style (includes Tier 2)
    rec_lines = _build_recommendation_style(profile)
    if rec_lines:
        lines.append("\n### Recommendation Style")
        lines.extend(rec_lines)

    # 4. Action Structure
    action_lines = _build_action_structure(profile)
    if action_lines:
        lines.append("\n### Action Items")
        lines.extend(action_lines)

    # 5. Blindspot Compensation (highest priority)
    blindspots = profile.get("primary_blindspots", [])
    if blindspots:
        lines.append("\n### ⚠️ Blindspot Compensation (ACTIVELY COUNTER)")
        for bs in blindspots[:3]:
            if isinstance(bs, dict):
                label = bs.get("label", "Unknown")
                compensation = bs.get("compensation", "")
                lines.append(f"- **{label}**: {compensation}")

    # 6. Behavioral Calibration
    behav_lines = _build_behavioral_calibration(profile)
    if behav_lines:
        lines.append("\n### Behavioral Patterns (Observed)")
        lines.extend(behav_lines)

    # 7. Inferred Dimensions (from behavior + stated preferences)
    inferred_lines = _build_inferred_dimensions(profile)
    if inferred_lines:
        lines.append("\n### Inferred Preferences")
        lines.extend(inferred_lines)

    return "\n".join(lines)
