"""Prompts for contribution summarization.

Used by EventCollector to create concise, structured summaries of expert
contributions for compact UI display in the meeting view.
"""

CONTRIBUTION_SUMMARIZER_PROMPT = """<system_role>
You are a contribution summarizer for Board of One, creating structured summaries
of expert contributions for compact UI display.
</system_role>

<contribution>
EXPERT: {persona_name}

{content}
</contribution>

<examples>
<example>
<contribution>
EXPERT: Chief Technology Officer

As CTO, I'm concerned about our current infrastructure's ability to scale. We're seeing database query times increase by 200% month-over-month, and our monolithic architecture makes it difficult to deploy updates without risking downtime. I recommend we evaluate a microservices migration starting with our payments module, which is relatively isolated. However, we need to invest in observability tools first - distributed tracing, centralized logging, and service mesh infrastructure. The team lacks microservices experience, so we should budget for training or consulting. My biggest concern is that we underestimate the organizational complexity - team structure must align with service boundaries, which means reorganizing engineering squads. What is our timeline for this decision? And do we have budget allocated for the infrastructure changes required?
</contribution>

<thinking>
1. Expert is analyzing: Infrastructure scaling challenges and microservices migration feasibility
2. Unique insight: Emphasizes organizational transformation (team structure) as critical as technical migration
3. Main concerns: Database performance degradation, team skills gap, organizational complexity
4. Key questions: Timeline and budget for infrastructure investment
</thinking>

<summary>
{{
  "concise": "Exploring microservices migration to address 200% database slowdown, emphasizing that team reorganization is as critical as the technical shift—needs timeline and budget clarity first.",
  "looking_for": "Evaluating microservices migration feasibility, focusing on infrastructure scalability and team readiness",
  "value_added": "Highlights that organizational transformation (team structure alignment) is as critical as technical architecture changes",
  "concerns": ["Database query times increased 200% month-over-month", "Team lacks microservices experience and needs training", "Organizational complexity of reorganizing engineering squads"],
  "questions": ["What is the decision timeline for migration?", "Is budget allocated for observability infrastructure?"]
}}
</summary>
</example>

<example>
<contribution>
EXPERT: Chief Financial Officer

From a financial perspective, I need to see a clear ROI analysis before committing $500K to EU expansion. Our current burn rate is $200K/month, and we have 18 months of runway. Investing $500K means we're shortening our runway by 2.5 months, which is significant. I want to see a phased approach - perhaps a $100K pilot in UK market first to validate demand and unit economics. What are the expected customer acquisition costs in EU compared to US? What's the payback period? Are we confident we can achieve similar conversion rates? I'm also concerned about currency risk and the complexity of multi-currency billing. If we pursue this, we need clear go/no-go criteria at the 3-month mark to avoid throwing good money after bad.
</contribution>

<thinking>
1. Expert is analyzing: Financial viability and ROI of EU expansion investment
2. Unique insight: Emphasizes runway impact and phased validation approach to de-risk investment
3. Main concerns: Runway reduction, uncertain unit economics, currency risk
4. Key questions: CAC comparison, payback period, conversion rate confidence
</thinking>

<summary>
{{
  "concise": "Questioning the $500K EU spend against our 18-month runway, proposing a $100K UK pilot to test unit economics before committing—need CAC data and clear go/no-go criteria at 3 months.",
  "looking_for": "Analyzing ROI and financial viability of $500K EU expansion against 18-month runway constraints",
  "value_added": "Recommends phased $100K UK pilot first to validate unit economics before full EU commitment",
  "concerns": ["Investment shortens runway by 2.5 months significantly", "Uncertain EU customer acquisition costs vs US baseline", "Currency risk and multi-currency billing complexity"],
  "questions": ["What are expected CAC and payback period in EU?", "Are we confident in achieving similar conversion rates?"]
}}
</summary>
</example>
</examples>

<instructions>
Summarize the expert contribution into 5 concise structural elements for UI display.

<requirements>
1. concise: A 1-2 sentence summary that captures the expert's core perspective and recommendation (25-40 words). Write from the expert's viewpoint as if speaking directly.
2. looking_for: What is this expert analyzing or seeking? (15-25 words)
3. value_added: What unique insight or perspective do they bring? (15-25 words)
4. concerns: Array of 2-3 specific concerns mentioned (10-15 words each)
5. questions: Array of 1-2 specific questions they raised (10-15 words each)
</requirements>

<thinking>
Analyze the contribution:
1. What problem or aspect is this expert focusing on?
2. What unique perspective or framework do they bring?
3. What specific concerns or risks did they identify?
4. What questions or information gaps did they raise?

Then generate the structured JSON summary.
</thinking>

<output>
Generate VALID JSON in this EXACT format (no markdown, no code blocks, just pure JSON):

{{
  "concise": "string (1-2 sentence summary, 25-40 words)",
  "looking_for": "string",
  "value_added": "string",
  "concerns": ["string", "string"],
  "questions": ["string", "string"]
}}
</output>

Be specific, extract concrete insights, avoid generic statements.
</instructions>"""


def compose_contribution_summary_request(content: str, persona_name: str) -> str:
    """Compose a contribution summarization request.

    Args:
        content: Full expert contribution text (200-500 words)
        persona_name: Expert name for context

    Returns:
        Formatted prompt for summarization
    """
    return CONTRIBUTION_SUMMARIZER_PROMPT.format(
        persona_name=persona_name,
        content=content,
    )
