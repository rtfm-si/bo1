"""Synthesis prompts for creating final deliberation reports.

This module contains templates for synthesizing expert deliberations into
actionable recommendations and comprehensive reports.
"""

import re
from typing import Any, NamedTuple

from bo1.prompts.protocols import PLAIN_LANGUAGE_STYLE
from bo1.prompts.sanitizer import sanitize_user_input
from bo1.prompts.style_adapter import get_style_instruction

SYNTHESIS_TOKEN_WARNING_THRESHOLD = 0.9  # Warn at 90% usage

# =============================================================================
# Overflow-Safe Instructions (per overflow.md patterns)
# =============================================================================
# These instructions ensure graceful handling when output approaches token limits

OVERFLOW_SAFE_INSTRUCTIONS = """
<overflow_handling>
CRITICAL: If you are at risk of running out of tokens:
- Do NOT rush or truncate sections
- Stop cleanly at a section boundary
- End your message with EXACTLY: <<<CONTINUE_FROM:{{section_name}}>>>
- Also include: NEXT: <what you will write next, in 10 words or fewer>

Never output partial JSON, tables, or mid-sentence content.
If you cannot complete a section, stop BEFORE starting it.
</overflow_handling>
"""

# Continuation prompt for truncated synthesis
SYNTHESIS_CONTINUATION_PROMPT = """Continue the synthesis from where you left off.

RULES:
- Do NOT repeat any completed sections
- Start with the next unfinished section
- If the previous output ended with <<<CONTINUE_FROM:{{cursor}}>>>, resume from that section
- Preserve the exact same formatting and structure

Previous output (ends with marker or truncation):
{previous_output}

Continue now. Start directly with the next section content."""

# =============================================================================
# Synthesis Prompt Template
# =============================================================================

SYNTHESIS_PROMPT_TEMPLATE = (
    """<system_role>
You are the Facilitator synthesizing the deliberation's conclusion.
</system_role>

<instructions>
Generate a comprehensive synthesis report for the user.

<problem_statement>
{problem_statement}
</problem_statement>

<full_deliberation>
{all_contributions_and_recommendations}
</full_deliberation>

<thinking>
Analyze the deliberation:
1. What consensus emerged across personas?
2. What disagreements remain and why?
3. What evidence was most compelling?
4. What risks were identified by domain experts?
5. What conditions affect the recommendation?
6. How confident is the board overall?
</thinking>

"""
    + PLAIN_LANGUAGE_STYLE
    + """

<synthesis_report>
<executive_summary>
One paragraph: problem, recommendation, key rationale (2-3 sentences).
Use SIMPLE, CLEAR language - avoid technical jargon and complex terminology.
Write as if explaining to a smart friend who isn't an expert. Be direct and concise.
If you catch yourself using abstract nouns, replace them with plain-language equivalents.
</executive_summary>

<recommendation>
Clear, actionable statement of recommended course of action.
Use everyday language - no business jargon.
</recommendation>

<rationale>
3-5 paragraphs covering:
- Key arguments supporting the recommendation (in plain language)
- Evidence and real-world examples cited by experts
- How different perspectives aligned or disagreed
- Main risks and how to handle them
- Key assumptions that need to be true for this to work
</rationale>

<vote_breakdown>
Summary of each expert's recommendation with their confidence level (use "very high", "high", "medium", or "low" - NOT numerical percentages).
For each expert, present their actual recommendation text and reasoning, not just their role description.

Format:
- [Expert Name]: [Their specific recommendation] with [confidence level]
  Key reasoning: [Their main argument in 1-2 sentences]
</vote_breakdown>

<dissenting_views>
Perspectives that disagreed and their reasoning (if any)
</dissenting_views>

<implementation_considerations>
Practical next steps and conditions for success identified by the board
</implementation_considerations>

<confidence_assessment>
Overall confidence level with justification. Express confidence using descriptive terms:
- "Very high confidence" (near certainty, strong evidence)
- "High confidence" (strong conviction, good evidence)
- "Medium confidence" (reasonable certainty, moderate evidence)
- "Low confidence" (significant uncertainty, limited evidence)

Base your assessment on:
- Strength of consensus
- Quality of evidence
- Known unknowns
- Complexity of implementation

DO NOT use numerical percentages or scores. Use natural language to describe confidence.
</confidence_assessment>

<open_questions>
What remains uncertain or requires further investigation?
</open_questions>
</synthesis_report>
</instructions>"""
)


# AUDIT FIX (Priority 3, Task 3.1): Hierarchical Synthesis Template
# This template uses round summaries for old rounds and full detail for final round only
# Expected impact: 60-70% token reduction (3500 avg → 1200 avg)
SYNTHESIS_HIERARCHICAL_TEMPLATE = (
    """<system_role>
You are the Facilitator synthesizing the deliberation's conclusion.
</system_role>

{limited_context_section}

"""
    + OVERFLOW_SAFE_INSTRUCTIONS
    + """

<instructions>
Generate a comprehensive synthesis report for the user.

<problem_statement>
{problem_statement}
</problem_statement>

{constraints_section}

<evolution_of_thinking>
This section shows how the deliberation evolved across rounds (summarized):

{round_summaries}
</evolution_of_thinking>

<final_round_detail>
Full detail from the final round of discussion:

{final_round_contributions}
</final_round_detail>

<expert_recommendations>
{recommendations}
</expert_recommendations>

<thinking>
Analyze the deliberation:
1. What consensus emerged across personas?
2. What disagreements remain and why?
3. What evidence was most compelling?
4. What risks were identified by domain experts?
5. What conditions affect the recommendation?
6. How confident is the board overall?
</thinking>

"""
    + PLAIN_LANGUAGE_STYLE
    + """

<synthesis_report>
<executive_summary>
One paragraph: problem, recommendation, key rationale (2-3 sentences).
Use SIMPLE, CLEAR language - avoid technical jargon and complex terminology.
Write as if explaining to a smart friend who isn't an expert. Be direct and concise.
If you catch yourself using abstract nouns, replace them with plain-language equivalents.
</executive_summary>

<recommendation>
Clear, actionable statement of recommended course of action.
Use everyday language - no business jargon.
</recommendation>

<rationale>
3-5 paragraphs covering:
- Key arguments supporting the recommendation (in plain language)
- Evidence and real-world examples cited by experts
- How different perspectives aligned or disagreed
- Main risks and how to handle them
- Key assumptions that need to be true for this to work
</rationale>

<vote_breakdown>
Summary of each expert's recommendation with their confidence level (use "very high", "high", "medium", or "low" - NOT numerical percentages).
For each expert, present their actual recommendation text and reasoning, not just their role description.

Format:
- [Expert Name]: [Their specific recommendation] with [confidence level]
  Key reasoning: [Their main argument in 1-2 sentences]
</vote_breakdown>

<dissenting_views>
Perspectives that disagreed and their reasoning (if any)
</dissenting_views>

<implementation_considerations>
Practical next steps and conditions for success identified by the board
</implementation_considerations>

<constraint_analysis>
If constraints were provided, evaluate the recommendation against EACH constraint:
- For each constraint: PASS / TENSION / VIOLATION with a brief explanation
- If no constraints were provided, write "No constraints specified."
Skip this section entirely if no constraints are present.
</constraint_analysis>

<confidence_assessment>
Overall confidence level with justification. Express confidence using descriptive terms:
- "Very high confidence" (near certainty, strong evidence)
- "High confidence" (strong conviction, good evidence)
- "Medium confidence" (reasonable certainty, moderate evidence)
- "Low confidence" (significant uncertainty, limited evidence)

Base your assessment on:
- Strength of consensus
- Quality of evidence
- Known unknowns
- Complexity of implementation

DO NOT use numerical percentages or scores. Use natural language to describe confidence.
</confidence_assessment>

<open_questions>
What remains uncertain or requires further investigation?
</open_questions>

{limited_context_output_section}
</synthesis_report>

<synthesis_examples>
Example 1 - HIGH-QUALITY SYNTHESIS:

<executive_summary>
The board recommends a phased SEO investment: $80K upfront for technical fixes (Months 1-2), then $220K for content and links (Months 3-12). This balances Maria's cash flow concerns with Zara's long-term growth vision. Kill switch at Month 6 protects against underperformance.
</executive_summary>

<recommendation>
Invest $300K in SEO using a 3-phase approach with a Month 6 performance checkpoint. If organic traffic growth is <30% by Month 6, reallocate remaining budget to paid ads.
</recommendation>

<rationale>
The financial analysis (Maria) showed clear long-term ROI advantage: SEO achieves $15-20 CAC vs $80 for paid ads. However, the 6-month lag creates pipeline risk given our 9-month runway. The phased approach addresses this by front-loading quick wins (technical SEO fixes typically show impact in 2-3 months) while building long-term assets (content, links).

Key tension: Zara prioritized long-term moat (70% SEO budget), while Maria emphasized cash flow protection. The board resolved this via the kill switch mechanism - we commit to SEO but validate traction at Month 6 before full investment.

Sarah's concern about execution capacity was addressed: the phased timeline spreads work across 12 months, requiring only 40 hours/month from engineering (feasible with current team size of 5).
</rationale>

<vote_breakdown>
- Zara Morales (Growth): "Invest 70% in SEO for long-term moat" with high confidence
  Key reasoning: $15-20 CAC via SEO vs $80 via paid ads creates compounding advantage
- Maria Santos (Finance): "Test SEO with $100K pilot, then scale based on results" with medium confidence
  Key reasoning: 6-month lag creates cash flow risk; pilot reduces exposure
- Sarah Kim (Marketing): "60/40 split (paid/SEO) balances short and long-term" with high confidence
  Key reasoning: Paid ads maintain pipeline while SEO ramps; rebalance in Q3
</vote_breakdown>

<dissenting_views>
Maria dissented from the full $300K investment upfront, recommending a smaller pilot. The board addressed this by including the Month 6 checkpoint, which provides a data-driven decision point similar to her pilot concept.
</dissenting_views>

<implementation_considerations>
Critical success factors:
1. Engineering allocation: 40 hours/month committed for technical SEO (non-negotiable)
2. Content quality: Hire experienced B2B SaaS writer ($80/hour), not junior contractor
3. Weekly monitoring: Track organic traffic, alert if <10% growth by Month 3
4. Month 6 checkpoint: Kill switch decision requires formal review of metrics
</implementation_considerations>

<confidence_assessment>
High confidence in the phased approach and kill switch mechanism. Medium confidence in timeline - SEO results can vary by 2-3 months depending on competition and content quality. The Month 6 checkpoint mitigates timeline risk.
</confidence_assessment>

<open_questions>
- Who owns SEO execution? Need dedicated owner for technical fixes and content calendar.
- Contractor vs hire? If we hire, need to account for 2-month ramp time.
- What if competitors launch SEO offensive during our ramp? How do we stay differentiated?
</open_questions>

---

Example 2 - LOW-QUALITY SYNTHESIS (AVOID THIS):

<executive_summary>
The board discussed SEO vs paid ads. Most people think SEO is good long-term but there are concerns about timeline. We should probably invest in SEO with some paid ads too.
</executive_summary>

<recommendation>
Invest in SEO and paid ads.
</recommendation>

<rationale>
SEO is generally good for growth. Some people raised concerns about timing and cash flow. Paid ads are faster. We should probably do both.
</rationale>

<vote_breakdown>
- Zara: Recommended SEO
- Maria: Had concerns about costs
- Sarah: Suggested a balanced approach
</vote_breakdown>

<dissenting_views>
Some disagreements existed.
</dissenting_views>

<implementation_considerations>
We need to execute the plan carefully.
</implementation_considerations>

<confidence_assessment>
Medium confidence overall.
</confidence_assessment>

<open_questions>
More research might be needed.
</open_questions>

PROBLEMS WITH LOW-QUALITY EXAMPLE:
- No specific dollar amounts or timelines
- Doesn't cite experts by name or reference their arguments
- "Most people think" - which people? What's the vote breakdown?
- "Probably" suggests uncertainty; synthesis should be confident
- No dissenting views mentioned (just "some disagreements")
- No implementation details
- No specific open questions identified
- Vague language throughout ("generally good", "some concerns")
</synthesis_examples>
</instructions>"""
)


# =============================================================================
# Lean Synthesis Template (McKinsey-style, ~800-1000 tokens output)
# =============================================================================
# This template produces complete, premium output within 1500 token budget.
# Uses Pyramid Principle (answer first), Rule of Three, and "So What?" framework.

SYNTHESIS_LEAN_TEMPLATE = (
    """<system_role>
You are a senior consultant synthesizing expert deliberation into an executive brief.
Your output should feel premium, considered, and trustworthy - like a McKinsey deliverable.
</system_role>

"""
    + OVERFLOW_SAFE_INSTRUCTIONS
    + """

<principles>
PYRAMID PRINCIPLE: Lead with the answer. The reader should know your recommendation in the first sentence.
RULE OF THREE: Three supporting points. Three next steps. No more.
"SO WHAT?": Every point must answer why it matters to the decision-maker.
SPECIFICITY: Concrete actions beat vague advice. "Talk to 3 customers this week" not "gather feedback."
CONFIDENCE: State recommendations clearly. Acknowledge uncertainty honestly, but don't hedge everything.
</principles>

{limited_context_section}

<problem>
{problem_statement}
</problem>

<deliberation_summary>
How the expert discussion evolved:
{round_summaries}
</deliberation_summary>

<final_positions>
{final_round_contributions}
</final_positions>

<expert_recommendations>
{recommendations}
</expert_recommendations>

<output_format>
Generate a synthesis using EXACTLY this structure. Be concise but complete.

## The Bottom Line

[One to two sentences. What should the reader do? Lead with the answer, not the analysis. This is the most important part - if they read nothing else, this tells them the decision.]

## Why This Matters

[Three bullet points maximum. Each bullet should be ONE key insight that supports your recommendation. Each must pass the "so what?" test - why does this matter to the decision?]

- **[Key insight 1]**: [Why it matters - the "so what"]
- **[Key insight 2]**: [Why it matters]
- **[Key insight 3]**: [Why it matters]

## What To Do Next

[Three concrete, specific actions. Not vague advice. Each should be something the reader could start this week.]

1. **[Specific action]**: [Brief detail on how/why]
2. **[Specific action]**: [Brief detail]
3. **[Specific action]**: [Brief detail]

## Key Risks

[Two to three risks to watch. Be honest but constructive - acknowledge what could go wrong without undermining the recommendation.]

- **[Risk]**: [Mitigation or how to watch for it]
- **[Risk]**: [Mitigation]

## Board Confidence

[One paragraph. State the overall confidence level (High/Medium/Low) and why. Note where experts agreed strongly vs. where uncertainty remains. Be honest about what you don't know.]

{limited_context_output_section}
</output_format>

<quality_checklist>
Before outputting, verify:
- [ ] Bottom line is actionable and specific (not "consider your options")
- [ ] Each "Why This Matters" point has a clear "so what"
- [ ] Next steps are concrete enough to start this week
- [ ] Risks are real but include mitigation
- [ ] Confidence assessment is honest about uncertainty
- [ ] No business jargon ("leverage", "synergize", "optimize")
- [ ] Total output is ~400-600 words (every sentence must earn its place)
</quality_checklist>"""
)


# =============================================================================
# Limited Context Mode Sections (Option D+E Hybrid)
# =============================================================================

LIMITED_CONTEXT_PROMPT_SECTION = """<limited_context_notice>
IMPORTANT: This deliberation was conducted with LIMITED CONTEXT.

The user acknowledged that complete information was not available. The experts have made
their best effort to provide analysis based on available information, but this synthesis
MUST include:

1. An explicit "Assumptions & Limitations" section
2. Clear marking of any recommendations that depend on unverified assumptions
3. Reduced confidence level where context gaps exist
4. Specific questions that would need to be answered for higher confidence

Be transparent about what the board COULD NOT fully assess due to missing context.
</limited_context_notice>
"""

LIMITED_CONTEXT_OUTPUT_SECTION = """
## Assumptions & Limitations

IMPORTANT: This analysis was conducted with incomplete context. The following assumptions were made:

[List 3-5 key assumptions that the experts made in lieu of complete information. Be specific about what was assumed and what could change the recommendation if the assumption is wrong.]

1. **[Assumption 1]**: [Why it was assumed and what would change if wrong]
2. **[Assumption 2]**: [Why it was assumed and what would change if wrong]
3. **[Assumption 3]**: [Why it was assumed and what would change if wrong]

### Information That Would Increase Confidence

[List 2-3 specific pieces of information that, if provided, would significantly improve the quality of this recommendation.]

- **[Missing info 1]**: [Why it matters]
- **[Missing info 2]**: [Why it matters]
"""


def get_limited_context_sections(limited_context_mode: bool) -> tuple[str, str]:
    """Get the limited context sections for synthesis prompts.

    Args:
        limited_context_mode: Whether the deliberation was conducted with limited context

    Returns:
        Tuple of (prompt_section, output_section) to insert into templates
    """
    if limited_context_mode:
        return LIMITED_CONTEXT_PROMPT_SECTION, LIMITED_CONTEXT_OUTPUT_SECTION
    return "", ""


def compose_synthesis_prompt(
    problem_statement: str,
    all_contributions_and_recommendations: str,
    business_context: dict[str, Any] | None = None,
) -> str:
    """Compose final synthesis prompt.

    Args:
        problem_statement: The problem being synthesized
        all_contributions_and_recommendations: Deliberation content
        business_context: Optional business context for style adaptation

    Returns:
        Formatted synthesis prompt
    """
    safe_problem_statement = sanitize_user_input(problem_statement, context="problem_statement")

    # Get style instruction if available
    style_block = get_style_instruction(business_context) if business_context else ""
    if style_block:
        # Prepend style instruction to problem statement
        safe_problem_statement = f"{style_block}\n\n{safe_problem_statement}"

    return SYNTHESIS_PROMPT_TEMPLATE.format(
        problem_statement=safe_problem_statement,
        all_contributions_and_recommendations=all_contributions_and_recommendations,
    )


def get_synthesis_style_instruction(business_context: dict[str, Any] | None) -> str:
    """Get style instruction block for synthesis prompts.

    Wraps the standard style instruction with synthesis-specific guidance.

    Args:
        business_context: Business context dict with brand fields

    Returns:
        Style instruction string or empty string
    """
    style_block = get_style_instruction(business_context) if business_context else ""
    if not style_block:
        return ""

    return f"""{style_block}

<synthesis_style_note>
The final recommendations should be written in a style that matches the user's brand voice.
Maintain the actionable, specific nature of recommendations while adapting vocabulary and tone.
</synthesis_style_note>"""


# =============================================================================
# Overflow Detection and Continuation Utilities
# =============================================================================


class OverflowStatus(NamedTuple):
    """Result of checking for overflow markers or truncation."""

    needs_continuation: bool
    cursor: str | None  # Section to continue from (if marker found)
    next_hint: str | None  # "NEXT:" hint if provided


# Regex pattern to detect continuation markers
CONTINUE_MARKER_PATTERN = re.compile(
    r"<<<CONTINUE_FROM:([^>]+)>>>\s*(?:NEXT:\s*(.+?))?$",
    re.IGNORECASE | re.MULTILINE,
)


def detect_overflow(content: str, is_truncated: bool = False) -> OverflowStatus:
    """Detect if content indicates overflow and needs continuation.

    Checks for:
    1. Explicit <<<CONTINUE_FROM:section>>> markers from the model
    2. API-level truncation (stop_reason=max_tokens)

    Args:
        content: The LLM response content
        is_truncated: True if API returned stop_reason=max_tokens

    Returns:
        OverflowStatus with continuation info
    """
    # Check for explicit continuation marker
    match = CONTINUE_MARKER_PATTERN.search(content)
    if match:
        cursor = match.group(1).strip()
        next_hint = match.group(2).strip() if match.group(2) else None
        return OverflowStatus(
            needs_continuation=True,
            cursor=cursor,
            next_hint=next_hint,
        )

    # Check for API-level truncation
    if is_truncated:
        return OverflowStatus(
            needs_continuation=True,
            cursor=None,  # Unknown section, will need to infer
            next_hint=None,
        )

    return OverflowStatus(needs_continuation=False, cursor=None, next_hint=None)


def compose_continuation_prompt(previous_output: str, cursor: str | None = None) -> str:
    """Compose a continuation prompt for truncated synthesis.

    Args:
        previous_output: The truncated/partial output from previous call
        cursor: Optional section name to continue from

    Returns:
        Formatted continuation prompt
    """
    # Trim to last ~2000 chars to avoid context bloat (per overflow.md recommendation)
    trimmed_output = previous_output[-2000:] if len(previous_output) > 2000 else previous_output

    # Add cursor hint if available
    if cursor:
        cursor_instruction = f"\nResume from section: {cursor}"
    else:
        cursor_instruction = ""

    return (
        SYNTHESIS_CONTINUATION_PROMPT.format(
            previous_output=trimmed_output,
        )
        + cursor_instruction
    )


def strip_continuation_marker(content: str) -> str:
    """Remove continuation markers from content for final output.

    Args:
        content: Content potentially containing markers

    Returns:
        Clean content without markers
    """
    # Remove the <<<CONTINUE_FROM:...>>> marker and NEXT: line
    cleaned = CONTINUE_MARKER_PATTERN.sub("", content)
    return cleaned.rstrip()
