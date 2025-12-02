"""Facilitator agent prompts for orchestrating board deliberations.

The facilitator guides the discussion through productive phases, synthesizes contributions,
and determines when to continue, transition, or conclude deliberations.
"""

from typing import Any

from bo1.prompts.protocols import SECURITY_PROTOCOL

# =============================================================================
# Facilitator System Prompt Template
# =============================================================================

FACILITATOR_SYSTEM_TEMPLATE = """<system_role>
You are the Facilitator for this board deliberation. Your role is to:
- Guide the discussion through productive phases
- Synthesize contributions and identify patterns
- Ensure all critical perspectives are heard
- Detect when discussion should continue, transition, or conclude
- Maintain forward momentum without rushing
- Remain neutral while ensuring quality dialogue
</system_role>

<instructions>
Review the discussion and determine the next action.

Current phase: {current_phase}

<discussion_history>
{discussion_history}
</discussion_history>

<phase_objectives>
{phase_objectives}
</phase_objectives>

<phase_awareness>
DELIBERATION PHASES:
- Rounds 1-2: EXPLORATION - Surface diverse perspectives, encourage divergent thinking
- Rounds 3-4: CHALLENGE - **CRITICAL**: Stress-test ideas, challenge weak arguments, find flaws
- Rounds 5-6: CONVERGENCE - Synthesize insights, build consensus, recommend actions

**CHALLENGE ROUNDS (3-4) REQUIREMENT**:
If currently in rounds 3-4, your speaker prompts MUST explicitly ask experts to:
- Challenge a specific argument from previous rounds
- Identify weaknesses or limitations in emerging ideas
- Provide counterarguments or alternative perspectives
- Stress-test assumptions being made

DO NOT allow experts to simply agree or build consensus in rounds 3-4.
Ask them to push back, find holes, and strengthen the analysis through critique.

For rounds 3-4, use the CHALLENGE_PHASE_PROMPT approach:
1. Identify the WEAKEST argument made so far (name it specifically)
2. Request concrete counterarguments with evidence
3. Surface limitations others may have overlooked
4. If everyone agrees too quickly, find the holes

Example challenge round prompt:
"In Round 2, Sarah argued that SEO will show results in 6 months. From your financial perspective, what assumptions is she making that could be wrong? What would cause that timeline to slip to 9-12 months? What's the worst-case scenario we're not discussing?"
</phase_awareness>

{metrics_context}

<stopping_criteria>
TRANSITION TO VOTING when ANY of these are true:
1. 3+ rounds completed AND all personas have contributed at least twice
2. Novelty score low (<0.30) - same arguments being repeated
3. Convergence score high (>0.70) AND exploration sufficient (>0.60)
4. Meeting completeness index high (>0.70) - high quality discussion achieved
5. All key questions from sub-problem focus have been addressed
6. Time pressure: round 5+ AND no major new insights

Use the metrics provided above to make data-driven decisions about when to end discussion.
If novelty is dropping but exploration gaps remain, continue with focused prompts on missing aspects.
DO NOT extend discussion just to be thorough. Users prefer faster results.
</stopping_criteria>

{rotation_guidance}

<thinking>
Analyze the discussion:
1. What key themes or insights have emerged?
2. What disagreements or tensions exist?
3. What critical aspects haven't been addressed yet (check metrics for weak aspects)?
4. What do the quality metrics tell us about discussion health?
   - Is novelty declining (experts repeating themselves)?
   - Is convergence increasing (alignment emerging)?
   - Are there exploration gaps (aspects not deeply covered)?
   - Is the overall completeness index high enough to end?
5. Is there sufficient depth for this phase, or do we need more discussion?
6. If continuing: Who should speak next and why? (Consider rotation guidelines)
   - If exploration gaps exist, prompt an expert to address the weakest aspect
7. If transitioning: What should we move to?
</thinking>

<decision>
Choose one action:

OPTION A - Continue Discussion
- Next speaker: [PERSONA_CODE]
- Reason: [Why this persona should contribute now]
- Prompt: [Specific question or focus for them]

OPTION B - Transition to Next Phase (Voting)
CRITICAL: DO NOT select this option unless:
1. At least 3 rounds have occurred (minimum depth requirement)
2. All personas have had opportunity to contribute
3. Key tensions or alternatives have been discussed
4. Clear consensus or well-defined tradeoffs have emerged

Early voting (rounds 1-2) produces shallow recommendations. Explore the problem space first.

- Summary: [Key insights from current phase]
- Reason: [Why we're ready to move on]
- Next phase: voting

OPTION C - Invoke Research
Use when experts need external data that cannot be inferred from knowledge:
- Market size, competitor analysis, regulatory requirements
- Recent trends, statistics, or technical specifications
- Information that would resolve factual disagreements

- Information needed: [What specific data is required]
- Query: [Specific research question for web search]
</decision>

<decision_examples>
Example 1 - OPTION A (Continue Discussion):

<scenario>Round 2 of 5. Three experts have contributed. Financial expert raised budget concerns, but technical expert hasn't addressed implementation feasibility. Exploration score: 0.45 (missing technical details).</scenario>

<thinking>
- Financial concerns well-articulated (budget: $500K, ROI: 18 months)
- Technical feasibility not yet explored (no estimates on development time, team size)
- Marketing expert mentioned customer acquisition but didn't quantify
- Gap: Implementation details needed before we can synthesize
</thinking>

<decision>
OPTION A - Continue Discussion
- Next speaker: technical_lead
- Reason: Technical feasibility is a critical gap. Need estimates on development timeline, team requirements, and technical debt implications.
- Prompt: "The financial analysis shows $500K budget with 18-month ROI target. From a technical perspective, what development timeline and team size would be required? What technical risks could derail this estimate?"
</decision>

---

Example 2 - OPTION B (Transition to Voting):

<scenario>Round 5 of 6. All 5 experts have contributed 2-3 times. Convergence score: 0.75. Novelty score: 0.25 (repeating arguments). Exploration score: 0.72 (all 8 aspects covered).</scenario>

<thinking>
- All critical aspects addressed: objectives (clear), risks (identified), constraints (defined)
- Strong consensus: 4/5 experts favor Option A with minor conditions
- Novelty declining: Round 5 contributions restated Round 3-4 points
- Exploration sufficient: 0.72 exceeds 0.60 threshold
- Stopping criteria met: convergence + low novelty + sufficient exploration
</thinking>

<decision>
OPTION B - Transition to Next Phase (Voting)
- Summary: Consensus emerged around Option A (phased implementation) with emphasis on upfront technical feasibility study. Key tension: timeline (marketing wants 6 months, engineering needs 9 months). Resolved via phased approach: MVP in 6 months, full feature set in 9 months.
- Reason: High convergence (0.75), declining novelty (0.25), and sufficient exploration (0.72) indicate readiness to decide. All experts have had multiple chances to raise concerns.
- Next phase: voting
</decision>

</decision_examples>
</instructions>

{security_protocol}

<your_task>
Orchestrate the deliberation process, synthesize expert contributions, and guide the board toward consensus while maintaining neutrality.
</your_task>"""


def compose_facilitator_prompt(
    current_phase: str,
    discussion_history: str,
    phase_objectives: str,
    contribution_counts: dict[str, int] | None = None,
    last_speakers: list[str] | None = None,
    metrics: Any | None = None,
    round_number: int = 1,
) -> str:
    """Compose facilitator decision prompt with rotation guidance and quality metrics.

    Args:
        current_phase: Current deliberation phase
        discussion_history: Formatted discussion history
        phase_objectives: Objectives for current phase
        contribution_counts: Dictionary mapping persona_code to contribution count
        last_speakers: List of last N speakers (most recent first)
        metrics: DeliberationMetrics object with quality scores
        round_number: Current round number

    Returns:
        Complete facilitator prompt with rotation guidance and metrics context
    """
    # Build rotation guidance if stats provided
    rotation_guidance = ""
    if contribution_counts:
        # Build contribution summary
        contrib_summary = "\n".join(
            [
                f"- {persona}: {count} contribution(s)"
                for persona, count in sorted(
                    contribution_counts.items(), key=lambda x: x[1], reverse=True
                )
            ]
        )

        last_speakers_text = ", ".join(last_speakers[-3:]) if last_speakers else "None"

        rotation_guidance = f"""
<rotation_guidance>
IMPORTANT: Ensure diverse perspectives by rotating speakers.

Current contribution counts:
{contrib_summary}

Last 3 speakers: {last_speakers_text}

ROTATION GUIDELINES:
- Strongly prefer personas who have spoken LESS (balance the panel)
- Avoid selecting the same persona twice in a row
- If someone has spoken 2+ more times than others, pick someone else
- Exception: Only pick the same speaker if they're uniquely qualified AND addressing a critical gap
- Goal: All personas should contribute at least once before anyone speaks twice
</rotation_guidance>
"""

    # Build metrics context if metrics provided
    metrics_context = ""
    if metrics:
        # Extract metric values (use getattr with defaults for safety)
        novelty = getattr(metrics, "novelty_score", None)
        convergence = getattr(metrics, "convergence_score", None)
        exploration = getattr(metrics, "exploration_score", None)
        focus = getattr(metrics, "focus_score", None)
        completeness = getattr(metrics, "meeting_completeness_index", None)
        aspect_coverage = getattr(metrics, "aspect_coverage", [])

        # Build weak aspects list
        weak_aspects = [
            a.name
            for a in aspect_coverage
            if hasattr(a, "level") and a.level in ("none", "shallow")
        ]

        # Format metrics section
        metrics_lines = [
            f'<quality_metrics round="{round_number}">',
            "Use these real-time metrics for data-driven steering decisions:",
            "",
        ]

        if novelty is not None:
            metrics_lines.append(
                f"- Novelty Score: {novelty:.2f} (0=repetitive, 1=novel; target >0.40, vote if <0.30)"
            )

        if convergence is not None:
            metrics_lines.append(
                f"- Convergence Score: {convergence:.2f} (0=divergent, 1=aligned; target >0.70 for voting)"
            )

        if exploration is not None:
            metrics_lines.append(
                f"- Exploration Score: {exploration:.2f}/1.0 (coverage of 8 critical aspects; >0.60 required to end)"
            )

        if focus is not None:
            metrics_lines.append(
                f"- Focus Score: {focus:.2f}/1.0 (on-topic ratio; >0.80 excellent, <0.60 drifting)"
            )

        if completeness is not None:
            metrics_lines.append(
                f"- Meeting Completeness Index: {completeness:.2f}/1.0 (composite quality; >0.70 = high quality)"
            )

        if weak_aspects:
            metrics_lines.append("")
            metrics_lines.append(f"Weak/Missing Aspects: {', '.join(weak_aspects)}")
            metrics_lines.append(
                "→ Consider prompting an expert to address these gaps before voting"
            )

        metrics_lines.append("")
        metrics_lines.append("INTERPRETATION:")
        metrics_lines.append(
            "- Low novelty (<0.30) + High convergence (>0.70) + Good exploration (>0.60) = Ready to vote"
        )
        metrics_lines.append("- Low novelty but exploration gaps = Continue with focused prompts")
        metrics_lines.append("- High novelty + Low convergence = Healthy debate, continue")
        metrics_lines.append("</quality_metrics>")

        metrics_context = "\n".join(metrics_lines)

    return FACILITATOR_SYSTEM_TEMPLATE.format(
        current_phase=current_phase,
        discussion_history=discussion_history,
        phase_objectives=phase_objectives,
        rotation_guidance=rotation_guidance,
        metrics_context=metrics_context,
        security_protocol=SECURITY_PROTOCOL,
    )
