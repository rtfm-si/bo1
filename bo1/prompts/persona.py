"""Persona agent prompts for expert contributions during deliberations.

This module contains functions and templates for composing prompts for individual
expert personas contributing to board deliberations.
"""

from bo1.prompts.protocols import (
    DELIBERATION_CONTEXT_TEMPLATE,
    _build_prompt_protocols,
    _get_security_task,
)

# =============================================================================
# Challenge Phase Protocol (Rounds 3-4)
# =============================================================================

CHALLENGE_PHASE_PROMPT = """<challenge_mode>
## MANDATORY CHALLENGE MODE (Rounds 3-4)

Your primary role in this round is to STRESS-TEST ideas, not build consensus.

You MUST:
1. **Identify the WEAKEST argument** made so far (name it specifically)
2. **Provide a concrete counterargument** with evidence or reasoning
3. **Surface limitations** that others may have overlooked
4. **Challenge emerging consensus** - if everyone agrees too quickly, find the holes

DO NOT:
- Simply agree or build on ideas without critique
- Provide generic support ("I think this is great...")
- Default to comfortable consensus

**If you find yourself agreeing with everything, you are NOT doing your job.**

The best outcomes come from rigorous challenge. Your role is to make the final recommendation MORE robust by finding its weaknesses NOW, not after implementation.
</challenge_mode>"""

# =============================================================================
# Enhanced Persona Contribution Prompt (Issue #4 - Deeper Discussion)
# =============================================================================


def compose_persona_contribution_prompt(
    persona_name: str,
    persona_description: str,
    persona_expertise: str,
    persona_communication_style: str,
    problem_statement: str,
    previous_contributions: list[dict[str, str]],
    speaker_prompt: str,
    round_number: int,
) -> tuple[str, str]:
    """Compose prompt for persona contribution with critical thinking emphasis.

    Args:
        persona_name: Name of the persona
        persona_description: Short description of the persona
        persona_expertise: Areas of expertise
        persona_communication_style: How they communicate
        problem_statement: The problem being discussed
        previous_contributions: List of dicts with 'persona_code' and 'content' keys
        speaker_prompt: Specific focus for this contribution
        round_number: Current round number (1-indexed)

    Returns:
        Tuple of (system_prompt, user_message) for the LLM
    """
    # Determine debate phase based on round number
    if round_number <= 2:
        phase_instruction = """
        <debate_phase>EARLY - DIVERGENT THINKING</debate_phase>
        <phase_goals>
        - Explore multiple perspectives
        - Challenge initial assumptions
        - Raise concerns and risks
        - Identify gaps in analysis
        - DON'T seek consensus yet - surface disagreements
        </phase_goals>
        """
    elif round_number <= 4:
        # Rounds 3-4: MANDATORY CHALLENGE MODE
        phase_instruction = f"""
        <debate_phase>MIDDLE - CRITICAL CHALLENGE PHASE</debate_phase>
        <phase_goals>
        - CHALLENGE weak arguments with evidence
        - STRESS-TEST emerging ideas for hidden flaws
        - SURFACE counterarguments and limitations
        - IDENTIFY tradeoffs others are overlooking
        - PUSH BACK on comfortable consensus
        </phase_goals>

        {CHALLENGE_PHASE_PROMPT}
        """
    else:
        phase_instruction = """
        <debate_phase>LATE - CONVERGENT THINKING</debate_phase>
        <phase_goals>
        - Synthesize key insights
        - Recommend specific actions
        - Acknowledge remaining uncertainties
        - Build consensus on critical points
        - Propose next steps
        </phase_goals>
        """

    # Format previous contributions for context (last 5 only)
    discussion_history = "\n\n".join(
        [
            f"[{c.get('persona_code', 'Unknown')}]: {c.get('content', '')}"
            for c in previous_contributions[-5:]  # Last 5 contributions
        ]
    )

    system_prompt = f"""You are {persona_name}, {persona_description}.

<expertise>
{persona_expertise}
</expertise>

<communication_style>
{persona_communication_style}
</communication_style>

{phase_instruction}

<critical_thinking_protocol>
You MUST engage critically with the discussion:

1. **Challenge Assumptions**: If someone makes an assumption, question it
2. **Demand Evidence**: If a claim lacks support, ask for evidence
3. **Identify Gaps**: Point out what's missing from the analysis
4. **Build or Refute**: Explicitly agree/disagree with previous speakers
5. **Recommend Actions**: End with specific, actionable recommendations

**Format your response with explicit structure:**
- Start with: "Based on [previous speaker's] point about X..."
- Include: "I disagree/agree with [persona] because..."
- End with: "My recommendation is to [specific action]..."
</critical_thinking_protocol>

<forbidden_patterns>
NEVER do any of the following:
- Generic agreement ("I agree with the previous speakers...")
- Vague observations without conclusions
- Listing facts without analysis
- Ending without a recommendation or question
- Meta-discussion about your role or how to respond (e.g., "Should I respond as X?")
- Asking about communication protocol or format expectations
- Analyzing the discussion framework instead of the problem itself
- Breaking character to discuss the conversation structure
</forbidden_patterns>

<critical_instruction>
IMPORTANT: You ARE the expert named above. You are already in character. Do NOT:
- Ask questions about how you should respond or what role you should play
- Discuss or analyze the communication framework
- Question the context of the discussion
- Reference "protocols" or "interaction formats"

Instead, IMMEDIATELY engage with the problem statement and provide substantive analysis based on your expertise. The problem you must address is in <problem_context> above.
</critical_instruction>

<problem_context>
{problem_statement}
</problem_context>

<previous_discussion>
{discussion_history}
</previous_discussion>

<your_focus>
{speaker_prompt}
</your_focus>

{_build_prompt_protocols(include_communication=False)}
"""

    user_message = f"""Provide your contribution following this structure:

<thinking>
(Private reasoning - not shown to other experts)
- Which previous points relate to my expertise?
- What do I disagree with or find concerning?
- What evidence supports my position?
- What am I uncertain about?
</thinking>

<contribution>
(Public statement to the group - 2-4 paragraphs)

[Start by referencing a specific previous contribution]
[Provide your analysis with clear reasoning]
[Challenge weak points or build on strong ones]
[End with specific recommendations or questions]
</contribution>

Remember: This is round {round_number}. Focus on {phase_instruction.split("</debate_phase>")[0].split(">")[-1]} thinking.
"""

    return system_prompt, user_message


# =============================================================================
# Helper Functions
# =============================================================================


def compose_persona_prompt(
    persona_system_role: str,
    problem_statement: str,
    participant_list: str,
    current_phase: str = "discussion",
    expert_memory: str | None = None,
) -> str:
    """Compose a complete framework-aligned persona system prompt.

    DEPRECATED: Use compose_persona_prompt_cached() for better cache optimization.

    This function takes the BESPOKE persona content (system_role) and combines it
    with GENERIC protocols and DYNAMIC context to create the full prompt.

    Args:
        persona_system_role: The <system_role> section from persona's system_prompt
        problem_statement: The problem being deliberated
        participant_list: Names of other personas in deliberation
        current_phase: Current deliberation phase (e.g., "initial", "discussion", "voting")
        expert_memory: Optional cross-sub-problem memory (summary from previous sub-problems)

    Returns:
        Complete system prompt following PROMPT_ENGINEERING_FRAMEWORK.md

    Example:
        >>> from bo1.data import get_persona_by_code
        >>> persona = get_persona_by_code("growth_hacker")
        >>> full_prompt = compose_persona_prompt(
        ...     persona_system_role=persona["system_prompt"],
        ...     problem_statement="Should we invest in SEO or paid ads?",
        ...     participant_list="Zara, Maria, Sarah",
        ...     current_phase="discussion"
        ... )
    """
    # Build parts list for composition
    parts = [persona_system_role]

    # Inject expert memory if available (cross-sub-problem memory)
    if expert_memory:
        parts.append(f"""

<your_previous_analysis>
You previously contributed to an earlier sub-problem in this deliberation.
Here's a summary of your position from that analysis:

{expert_memory}

You should build on this earlier analysis, maintaining consistency with your
previous recommendations unless new information changes your view. If you
change your position, explain why.
</your_previous_analysis>
""")

    # Build deliberation context
    context = DELIBERATION_CONTEXT_TEMPLATE.format(
        problem_statement=problem_statement,
        participant_list=participant_list,
        current_phase=current_phase,
    )

    parts.append(f"\n{context}\n")
    parts.append(
        f"\n{_build_prompt_protocols(include_communication=True, include_security=False)}\n"
    )

    # Build security addendum
    parts.append(f"\n{_get_security_task()}")

    return "".join(parts)


def compose_persona_prompt_cached(
    problem_statement: str,
    participant_list: str,
    current_phase: str = "discussion",
) -> tuple[str, str]:
    """Compose cache-optimized persona prompts for cross-persona cache sharing.

    CACHE OPTIMIZATION: Separates cacheable (problem context, protocols) from
    variable (persona identity) content. This enables all personas to share the
    same cached system prompt, dramatically reducing costs.

    Pattern:
        - System prompt (CACHED): Problem context + protocols (shared by all personas)
        - User message template (NOT CACHED): Persona identity (unique per persona)

    Args:
        problem_statement: The problem being deliberated
        participant_list: Names of other personas in deliberation
        current_phase: Current deliberation phase (e.g., "initial", "discussion", "voting")

    Returns:
        Tuple of (system_prompt, user_message_template) where:
        - system_prompt: Generic cached content (discussion context + protocols)
        - user_message_template: Template string with {persona_system_role} and {persona_name} placeholders

    Example:
        >>> system_prompt, user_template = compose_persona_prompt_cached(
        ...     problem_statement="Should we invest in SEO or paid ads?",
        ...     participant_list="Zara, Maria, Sarah",
        ...     current_phase="discussion"
        ... )
        >>> # System prompt is SAME for all personas (cached!)
        >>> # User message varies per persona:
        >>> user_msg = user_template.format(
        ...     persona_system_role=persona["system_prompt"],
        ...     persona_name=persona["name"]
        ... )
    """
    # Build deliberation context (CACHED - same for all personas)
    context = DELIBERATION_CONTEXT_TEMPLATE.format(
        problem_statement=problem_statement,
        participant_list=participant_list,
        current_phase=current_phase,
    )

    # System prompt: Generic content shared by all personas (CACHED)
    system_prompt = f"""{context}

{_build_prompt_protocols(include_communication=True, include_security=False)}

{_get_security_task()}"""

    # User message template: Persona-specific content (NOT CACHED)
    user_message_template = """{{persona_system_role}}

You are {{persona_name}}, participating in this deliberation. Please provide your contribution based on your expertise."""

    return system_prompt, user_message_template


# =============================================================================
# Hierarchical Context Composition (Week 3 - Day 16-17)
# =============================================================================


def compose_persona_prompt_hierarchical(
    persona_system_role: str,
    problem_statement: str,
    participant_list: str,
    round_summaries: list[str],
    current_round_contributions: list[dict[str, str]],
    round_number: int,
    current_phase: str = "discussion",
) -> str:
    """Compose persona prompt with hierarchical context management.

    This function prevents quadratic token growth by:
    - Including old rounds as summaries (~100 tokens each, cached)
    - Including current round as full detail (~200 tokens per contribution, not cached)

    Design:
    - Rounds 1 to N-2: Summaries only
    - Round N-1: Full contributions (provides immediate context)
    - Total context stays ~1,400 tokens (linear growth, not quadratic)

    Args:
        persona_system_role: Bespoke persona identity from personas.json
        problem_statement: The problem being deliberated
        participant_list: Comma-separated list of participant names
        round_summaries: List of summaries for past rounds (Rounds 1 to N-2)
        current_round_contributions: Full contributions from Round N-1
        round_number: Current round number (N)
        current_phase: Current deliberation phase

    Returns:
        Composed system prompt with hierarchical context

    Example:
        >>> round_summaries = [
        ...     "Round 1: Three key tensions emerged: cost vs quality...",
        ...     "Round 2: Maria provided financial analysis showing..."
        ... ]
        >>> current_round = [
        ...     {"persona": "Maria", "content": "Building on Round 2 analysis..."},
        ...     {"persona": "Zara", "content": "I agree with Maria but..."}
        ... ]
        >>> prompt = compose_persona_prompt_hierarchical(
        ...     persona_system_role=maria_role,
        ...     problem_statement="Should we invest in SEO?",
        ...     participant_list="Maria, Zara, Tariq",
        ...     round_summaries=round_summaries,
        ...     current_round_contributions=current_round,
        ...     round_number=3,
        ...     current_phase="discussion"
        ... )
    """
    from bo1.prompts.utils import get_round_phase_config

    # Build hierarchical context
    context_parts = []

    # Previous rounds (summarized)
    if round_summaries:
        context_parts.append("<previous_rounds_summary>")
        for i, summary in enumerate(round_summaries, start=1):
            context_parts.append(f"Round {i}: {summary}")
        context_parts.append("</previous_rounds_summary>\n")

    # Current round (full detail)
    if current_round_contributions:
        context_parts.append("<current_round_detail>")
        for contrib in current_round_contributions:
            persona_name = contrib.get("persona", "Unknown")
            content = contrib.get("content", "")
            context_parts.append(f"[{persona_name}]\n{content}\n")
        context_parts.append("</current_round_detail>\n")

    discussion_context = "\n".join(context_parts)

    # Get phase config
    # Note: We need to know max_rounds to use adaptive config properly
    # For now, use a heuristic: max_rounds = 10 (typical for complex problems)
    max_rounds = 10
    phase_config = get_round_phase_config(round_number, max_rounds)
    phase_directive = phase_config["directive"]

    # Compose full prompt
    return f"""{persona_system_role}

<problem_statement>
{problem_statement}
</problem_statement>

<participants>
{participant_list}
</participants>

<discussion_history>
{discussion_context}
</discussion_history>

<task>
You are in Round {round_number} of the deliberation.

{phase_directive}

Your contribution should:
- Build on what has been discussed (reference specific points from summaries or recent contributions)
- Add new insights or perspectives
- Address gaps or questions raised by other participants
- Stay focused on the problem statement
</task>

{_build_prompt_protocols(include_communication=True, include_security=False)}

{_get_security_task()}"""
