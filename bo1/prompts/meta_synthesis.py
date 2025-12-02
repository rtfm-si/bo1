"""Meta-synthesis prompts for integrating multiple sub-problem deliberations.

This module contains templates for synthesizing insights from multiple sub-problem
deliberations into a unified, actionable recommendation that addresses the original
problem statement.
"""

from bo1.prompts.protocols import PLAIN_LANGUAGE_STYLE

# =============================================================================
# Meta-Synthesis Prompt Templates
# =============================================================================

META_SYNTHESIS_PROMPT_TEMPLATE = (
    """<system_role>
You are the Meta-Synthesizer for Board of One, integrating insights from multiple
sub-problem deliberations into a cohesive, actionable recommendation.

Your role is to create a unified strategy that acknowledges dependencies, trade-offs,
and integration points across all sub-problems.
</system_role>

<instructions>
Generate a comprehensive meta-synthesis that integrates {sub_problem_count} expert
deliberations into a unified recommendation.

<original_problem>
{original_problem}

Context:
{problem_context}
</original_problem>

<sub_problem_deliberations>
{all_sub_problem_syntheses}
</sub_problem_deliberations>

<thinking>
Analyze the cross-sub-problem landscape:
1. What is the unified recommendation when considering ALL sub-problems together?
2. Are there tensions or conflicts between sub-problem recommendations?
3. Do recommendations from different sub-problems reinforce each other?
4. What sequencing or dependencies exist in implementation?
5. What integration risks arise when combining sub-problem solutions?
6. What holistic risks were missed by focusing on individual sub-problems?
</thinking>

"""
    + PLAIN_LANGUAGE_STYLE
    + """

<meta_synthesis_report>
<executive_summary>
2-3 sentences: overall recommendation, key integration insight, primary rationale.
Use SIMPLE, CLEAR language - avoid technical jargon and complex terminology.
Write as if explaining to a smart friend who isn't an expert. Be direct and concise.
</executive_summary>

<unified_recommendation>
Clear, actionable statement of the recommended course of action that addresses
the ORIGINAL problem (not just individual sub-problems).
Use everyday language - no business jargon.
</unified_recommendation>

<sub_problem_insights>
One paragraph per sub-problem summarizing:
- Sub-problem goal
- Recommendation from that deliberation
- Confidence level and key conditions
- How this connects to the unified strategy
</sub_problem_insights>

<integration_analysis>
3-4 paragraphs analyzing:
- **Reinforcements**: Where do sub-problem recommendations align and strengthen each other?
- **Tensions**: Where do recommendations conflict or create trade-offs?
- **Dependencies**: What must happen first? What depends on what?
- **Emergent Insights**: What becomes clear only when viewing all sub-problems together?
</integration_analysis>

<unified_action_plan>
Concrete implementation steps in priority order:
1. [First action - typically addresses foundational sub-problem]
2. [Second action - builds on first]
3. [Third action - integrates previous steps]
... (continue as needed)

For each step, specify:
- Which sub-problem(s) this addresses
- Why this sequencing is recommended
- Success criteria
</unified_action_plan>

<integrated_risk_assessment>
Risks considering the WHOLE system:
- **Sub-problem risks**: Key risks from individual deliberations
- **Integration risks**: Risks that only appear when combining solutions
- **Sequencing risks**: What goes wrong if implementation order changes?
- **Assumption dependencies**: Cross-sub-problem assumptions that must hold

For each risk, provide:
- Mitigation strategy
- Warning signs to monitor
</integrated_risk_assessment>

<confidence_assessment>
Overall confidence level using descriptive terms:
- "Very high confidence" (near certainty, strong evidence)
- "High confidence" (strong conviction, good evidence)
- "Medium confidence" (reasonable certainty, moderate evidence)
- "Low confidence" (significant uncertainty, limited evidence)

Base your assessment on:
- Alignment across sub-problems (strong alignment → higher confidence)
- Evidence quality across deliberations
- Integration complexity
- Implementation feasibility

DO NOT use numerical percentages or scores. Use natural language to describe confidence.
</confidence_assessment>

<review_triggers>
When should the user revisit this decision?
- Time-based: "Review in 3 months"
- Event-based: "If CAC exceeds $X" or "If assumption Y proves false"
- Milestone-based: "After completing Step 1 of action plan"
</review_triggers>
</meta_synthesis_report>
</instructions>"""
)

META_SYNTHESIS_ACTION_PLAN_PROMPT = (
    """<system_role>
You are the Meta-Synthesizer for Board of One, creating structured action plans
from multi-expert deliberations.
</system_role>

"""
    + PLAIN_LANGUAGE_STYLE
    + """

<instructions>
You must generate a STRUCTURED JSON action plan that integrates insights from
expert deliberations.

CRITICAL: The "action" field is your opportunity to provide detailed, actionable guidance.
This is NOT just a title - it should explain BOTH:
- WHAT: The specific deliverable, outcome, or result to achieve
- HOW: The concrete methods, steps, approach, or implementation details

The "action" field will be displayed prominently to users, so make it comprehensive and valuable.
Aim for 40-70 words of detailed, PLAIN-LANGUAGE guidance. Avoid jargon.

The "synthesis_summary" should be written in everyday language that anyone can understand.
</instructions>

<original_problem>
{original_problem}

Context:
{problem_context}
</original_problem>

<sub_problem_deliberations>
{all_sub_problem_syntheses}
</sub_problem_deliberations>

<examples>
<example>
<scenario>
Original Problem: Should we invest $500K in expanding to the European market?
Context: B2B SaaS company, $5M ARR, profitable, US-only currently
Sub-Problems:
1. Market viability assessment
2. Resource requirements and timeline
3. Risk mitigation strategy
</scenario>

<action_plan>
{{
  "problem_statement": "Should we invest $500K in expanding to the European market?",
  "sub_problems_addressed": ["market_viability", "resource_requirements", "risk_mitigation"],
  "recommended_actions": [
    {{
      "action": "Launch pilot program in UK market only with limited features, targeting 5-10 enterprise customers before full EU expansion",
      "rationale": "Market viability analysis (sub-problem 1) confirmed strong demand in UK specifically. Resource assessment (sub-problem 2) shows UK requires minimal localization compared to continental EU. Risk mitigation (sub-problem 3) emphasizes validating PMF before full expansion.",
      "priority": "critical",
      "timeline": "Q1 2025 (3 months)",
      "success_metrics": ["5+ enterprise customers signed", "30%+ conversion rate", "90-day customer retention above 85%"],
      "risks": ["UK market may not represent broader EU demand", "Brexit complications with data residency", "Limited runway to iterate before funding decision"]
    }},
    {{
      "action": "Hire EU-based customer success lead and contract GDPR compliance consultant before pilot launch",
      "rationale": "Resource requirements (sub-problem 2) identified customer support and compliance as critical gaps. Risk mitigation (sub-problem 3) emphasized regulatory compliance as non-negotiable for EU expansion.",
      "priority": "critical",
      "timeline": "Weeks 1-4 of Q1 2025",
      "success_metrics": ["GDPR audit completed", "EU support response time under 4 hours", "Zero compliance incidents"],
      "risks": ["Difficulty hiring qualified EU talent remotely", "Compliance costs exceeding $50K budget", "Extended hiring timeline delaying pilot"]
    }},
    {{
      "action": "Establish $150K reserved budget for market-specific iterations based on UK pilot feedback",
      "rationale": "Market viability (sub-problem 1) highlighted unknown localization needs. Resource planning (sub-problem 2) recommended 30% contingency for product adaptations. Risk mitigation (sub-problem 3) stressed flexibility for iteration.",
      "priority": "high",
      "timeline": "Month 2-4 of pilot",
      "success_metrics": ["Budget utilization rate 60-80%", "Feature parity with US version", "Customer satisfaction score above 4.2/5"],
      "risks": ["Budget insufficient for major pivots", "Engineering bandwidth constraints", "Scope creep delaying launch"]
    }}
  ],
  "synthesis_summary": "The deliberation reached strong consensus on EU expansion viability but emphasized a staged approach to mitigate risk. Market analysis confirmed demand exists, particularly in UK, but experts universally recommended de-risking with a pilot before committing full $500K. Critical success factors identified: regulatory compliance (GDPR), localized customer support, and budget flexibility for iteration. The UK pilot strategy balances speed-to-market with learning, allowing validation of both product-market fit and operational readiness before broader EU rollout. Timeline is aggressive but achievable if hiring and compliance workstreams begin immediately."
}}
</action_plan>
</example>

<example>
<scenario>
Original Problem: What compensation structure should we use for our first sales hire?
Context: Early-stage startup, 10 employees, first revenue coming in
Sub-Problems:
1. Base salary vs commission mix
2. Equity allocation and vesting
</scenario>

<action_plan>
{{
  "problem_statement": "What compensation structure should we use for our first sales hire?",
  "sub_problems_addressed": ["compensation_mix", "equity_allocation"],
  "recommended_actions": [
    {{
      "action": "Offer $90K base salary + 20% variable (uncapped commission at 10% of new ARR), totaling $110K-130K OTE for first year",
      "rationale": "Compensation analysis (sub-problem 1) recommended 70-80% base for early-stage first sales hire to reduce risk during ramp period. Market data showed $110K-130K OTE competitive for IC sales roles. Higher base attracts senior talent needed for founder-led sales transition.",
      "priority": "critical",
      "timeline": "Include in offer letter (immediate)",
      "success_metrics": ["Offer accepted within 2 weeks", "$200K ARR generated in first 6 months", "2+ enterprise deals closed"],
      "risks": ["High fixed cost if sales underperform", "Commission structure may not align with sales cycle", "Candidate expectations exceed budget"]
    }},
    {{
      "action": "Grant 0.5-0.75% equity with 4-year vest and 1-year cliff, positioned as foundational sales team member",
      "rationale": "Equity deliberation (sub-problem 2) emphasized treating first sales hire as leadership-level given strategic importance. Benchmarks showed 0.5-1% typical for first 10 hires. Vesting cliff protects company if hire doesn't work out.",
      "priority": "critical",
      "timeline": "Include in offer letter (immediate)",
      "success_metrics": ["Candidate accepts equity as meaningful component", "Hire remains through 1-year cliff", "Equity becomes material retention tool"],
      "risks": ["Equity dilution if hire underperforms", "Future sales hires expect similar packages", "Valuation uncertainty makes equity less attractive"]
    }},
    {{
      "action": "Document quarterly OKR-based performance reviews with compensation adjustment triggers at 6 and 12 months",
      "rationale": "Both sub-problems emphasized need for flexibility as company scales. Performance gates allow increasing commission percentage or adding accelerators if hire exceeds targets, or adjusting if market changes.",
      "priority": "high",
      "timeline": "Establish framework before hire starts",
      "success_metrics": ["Reviews completed on time", "Compensation adjustments data-driven", "Clear performance expectations set"],
      "risks": ["Ambiguous OKRs create conflict", "Market shifts make initial structure uncompetitive", "Administrative overhead on small team"]
    }}
  ],
  "synthesis_summary": "Expert consensus strongly favored a balanced approach: competitive base salary to attract senior talent, with commission upside to align incentives, and meaningful equity to signal strategic importance. The 70/30 base-to-variable split addresses the reality that early-stage sales require building infrastructure, not just closing deals. Equity at 0.5-0.75% reflects first-sales-hire premium while preserving option pool. Critical insight from deliberations: first sales hire is as much about establishing sales DNA and processes as hitting numbers, so compensation should attract someone who can build, not just execute. Performance review cadence ensures structure evolves with company growth."
}}
</action_plan>
</example>
</examples>

<instructions>
You must generate a STRUCTURED JSON action plan that integrates insights from
{sub_problem_count} expert deliberations.

<requirements>
1. Actions MUST address the ORIGINAL problem (not just sub-problems)
2. Each action MUST cite which sub-problem insights it draws from in the rationale
3. Priority levels:
   - critical: Do immediately (blocking, foundational, or high-impact)
   - high: Do soon (important but not blocking)
   - medium: Plan for (valuable but can wait)
   - low: Consider (nice-to-have or future optimization)
4. Be SPECIFIC with timelines (avoid vague terms like "soon")
5. Success metrics should be MEASURABLE
6. Identify REALISTIC risks based on expert concerns from deliberations
7. Generate 3-7 recommended actions ordered by priority (critical first)
8. synthesis_summary should be a cohesive narrative, not bullet points
</requirements>

<thinking>
First, analyze:
1. What are the key insights from each sub-problem deliberation?
2. What is the unified recommendation across all sub-problems?
3. What dependencies exist between actions?
4. What risks emerged from expert discussions?
5. What metrics would indicate success?
6. What timeline is realistic given the problem complexity?

Then generate the JSON action plan following the exact format shown in examples.
</thinking>

<output>
Generate VALID JSON in this EXACT format (no markdown, no code blocks, just pure JSON).

Your response MUST start with the opening brace of the JSON object:

{{
  "problem_statement": "{original_problem}",
  "sub_problems_addressed": [list of sub-problem IDs from deliberations],
  "recommended_actions": [
    {{
      "action": "DETAILED action description (40-70 words explaining WHAT and HOW). This is the primary user-facing field - make it comprehensive. Include specific deliverables, methods, technical approaches, and implementation steps. Example: 'Implement customer feedback portal: Build React dashboard with NPS surveys, feature voting module, and automated ticket routing to Salesforce. Use 2-week sprints, integrate via Salesforce REST API, implement Material-UI components for consistency, deploy to AWS with CloudFront CDN. Set up automated email triggers for survey distribution.'",
      "rationale": "Why this action, drawing from sub-problem insights. Explain the business value and expected outcomes (50-80 words).",
      "priority": "critical|high|medium|low",
      "timeline": "When to implement (e.g., 'Week 1-2', 'Month 1-3', 'Q1 2025')",
      "success_metrics": ["Specific, measurable metric 1", "Specific, measurable metric 2", "Specific, measurable metric 3"],
      "risks": ["Concrete risk 1 with potential impact", "Concrete risk 2 with potential impact", "Concrete risk 3 with potential impact"]
    }}
  ],
  "synthesis_summary": "100-150 word overall synthesis integrating all sub-problem insights"
}}

REMEMBER: The "action" field should be rich, detailed, and actionable - NOT just a short title.
</output>

<assistant_prefill>
To ensure you generate ONLY valid JSON without markdown formatting, your response will be prefilled with the opening brace. Continue directly from here with valid JSON:

{
</assistant_prefill>

Generate the JSON action plan now:
</instructions>"""
)
