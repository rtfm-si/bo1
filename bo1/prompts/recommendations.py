"""Recommendation (voting) prompts for expert final recommendations.

This module contains prompts for collecting structured recommendations from experts
at the conclusion of deliberations.
"""

# =============================================================================
# Confidence Level Enumeration
# =============================================================================

# Enforced confidence levels - no "very high", "extremely low", or percentages
CONFIDENCE_ENUM = "HIGH | MEDIUM | LOW"
"""Valid confidence level values for recommendations.

LLM outputs are normalized to these values:
- "very high" / "extremely high" → HIGH
- "moderate" / "somewhat confident" → MEDIUM
- "very low" / "uncertain" → LOW
- Percentages: >=70% → HIGH, 40-69% → MEDIUM, <40% → LOW
"""

# =============================================================================
# Voting Prompt Template
# =============================================================================

# CACHE-OPTIMIZED: Generic voting system prompt (shared across all personas)
# Persona identity moved to user message for cross-persona cache sharing
RECOMMENDATION_SYSTEM_PROMPT = """<instructions>
The deliberation is concluding. Review the full discussion and provide your final recommendation.

<full_discussion>
{discussion_history}
</full_discussion>

IMPORTANT: You MUST respond using the following XML structure. DO NOT use markdown headings or other formats.

Your response will start with <thinking> (which is prefilled for you), and you must continue with the rest of the XML structure:

<thinking>
Reflect on the deliberation:
1. What are the strongest arguments made?
2. What alternatives have been discussed?
3. What evidence supports different approaches?
4. What is your domain-specific recommendation?
5. How confident are you (and why)?
6. What key risks or conditions apply?
</thinking>

<recommendation_block>
<recommendation>
Your specific, actionable recommendation. Be concrete and clear.

For binary questions (e.g., "Should we invest in X?"):
- You can recommend "Approve investment in X" or "Reject X, invest in Y instead"
- You can also recommend alternatives: "Neither - do Z first, then reconsider"
- Or hybrid approaches: "Test with $10K first, then scale if metrics hit targets"

For strategy questions (e.g., "What compensation structure?"):
- Provide a specific strategy: "60% salary, 40% dividends hybrid"
- Or: "Pure salary until profitability, then transition to 50/50"
- Be specific with percentages, timelines, and approaches

Always consider alternatives beyond just yes/no to the stated option.
</recommendation>

<reasoning>
2-3 paragraphs explaining your recommendation from your expert perspective:
- Why this approach is best based on your domain expertise
- What alternatives you considered and why you ruled them out
- Key risks, opportunities, and trade-offs
- How the deliberation shaped your thinking
- Evidence or frameworks supporting your recommendation
</reasoning>

<confidence>HIGH | MEDIUM | LOW</confidence>
(REQUIRED: Use ONLY these exact values. Do not use "very high", percentages, or other variants.)

<confidence_rationale>
Why this confidence level? What would increase or decrease it?
</confidence_rationale>

<conditions>
Critical conditions or caveats (one per line):
- Condition 1
- Condition 2
- Condition 3

If none, write "No conditions."
</conditions>
</recommendation_block>

Remember: Use ONLY the XML tags shown above. Do NOT use markdown headings like ## Recommendation or # Decision.

<recommendation_examples>
Example 1 - STRONG RECOMMENDATION (specific, actionable):

<recommendation>
Approve $300K investment in SEO, but structure as 3 phases: (1) $80K technical SEO audit and fixes in Months 1-2; (2) $120K content production in Months 3-6 (30 articles, 10 guides); (3) $100K link building in Months 7-12. Include kill switch: if organic traffic growth <30% by Month 6, reallocate remaining $100K to paid ads.
</recommendation>

<reasoning>
Maria's financial analysis showed $80 CAC via paid ads vs $15-20 via SEO (long-term). However, Sarah's point about 6-month lag is valid - we can't wait that long with current runway. My phased approach addresses both concerns: front-load technical fixes (fastest impact), then content (medium-term), then links (long-term). The kill switch protects against SEO underperformance - if we're not seeing traction by Month 6, we pivot to paid. This balances Zara's growth urgency with Maria's cost efficiency.
</reasoning>

<confidence>medium</confidence>
<confidence_rationale>High confidence in SEO's long-term ROI, but medium confidence in timeline. 6-month checkpoint provides data-driven decision point.</confidence_rationale>

<conditions>
- Engineering allocates 40 hours/month for technical SEO implementation
- Content quality maintained: hire experienced writer, not junior contractor
- Organic traffic monitored weekly; alert if <10% growth by Month 3
</conditions>

---

Example 2 - WEAK RECOMMENDATION (vague, not actionable):

<recommendation>
We should probably invest in SEO because it's good long-term. Maybe start with some content and see what happens.
</recommendation>

<reasoning>
SEO is generally a good strategy for growth. Other companies have had success with it. We should try it and adjust as we go.
</reasoning>

<confidence>medium</confidence>
<confidence_rationale>It seems reasonable.</confidence_rationale>

<conditions>
No conditions.
</conditions>

PROBLEMS WITH WEAK EXAMPLE:
- No specific dollar amounts or timelines
- "Some content" is not actionable (how much? what type?)
- "See what happens" has no success metrics
- Reasoning doesn't reference other experts' concerns
- Confidence rationale is vague ("seems reasonable")

---

Example 3 - ADDRESSING DISAGREEMENTS:

<recommendation>
Reject pure SEO strategy. Recommend 60/40 split: $200K paid ads (immediate pipeline) + $130K SEO (future moat). Prioritize paid ads in Q1-Q2 for revenue targets, then shift to 40/60 in Q3-Q4 once SEO momentum builds.
</recommendation>

<reasoning>
I disagree with Zara's 70/30 SEO-heavy split. Maria's cash flow concerns (6-month ROI lag) are valid - we can't starve the pipeline for 2 quarters. However, I also disagree with Sarah's 50/50 split as too conservative on SEO. My 60/40 (paid/SEO) addresses Maria's runway anxiety while still making meaningful SEO investment. The Q3 rebalance to 40/60 recognizes Zara's point that SEO compounds - by Q3, organic traffic should be ramping, allowing us to reduce paid spend.
</reasoning>

<confidence>high</confidence>
<confidence_rationale>High confidence based on 8 years of marketing experience across 15 companies. The phased rebalancing approach mitigates both short-term (cash flow) and long-term (CAC) risks.</confidence_rationale>

<conditions>
- Marketing bandwidth: 20 hours/week minimum for SEO execution
- Paid ads performance monitored weekly; pause if CAC exceeds $100
- SEO metrics reviewed monthly; accelerate Q3 transition if traffic growth exceeds 40%
</conditions>
</recommendation_examples>
</instructions>"""

# User message template for recommendations (includes persona identity - NOT cached)
RECOMMENDATION_USER_MESSAGE = """You are {persona_name} preparing your final recommendation.

Please provide your recommendation using the XML structure specified in the instructions above."""
