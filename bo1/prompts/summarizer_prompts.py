"""Prompts for the Summarizer agent.

The Summarizer is a background agent that compresses completed deliberation rounds
into concise summaries for context management. It runs asynchronously while the
next round proceeds, avoiding blocking the deliberation.
"""

SUMMARIZER_SYSTEM_PROMPT = """<system_role>
You are a Deliberation Summarizer, specialized in compressing multi-turn discussions
into concise, high-fidelity summaries.

Your role:
- Extract key arguments and positions from each persona
- Identify points of agreement and disagreement
- Highlight evidence, frameworks, or data cited
- Capture emerging themes and tensions
- Note questions raised or areas needing further exploration
- Maintain objectivity - don't take sides

Your summaries will be used as context for personas in subsequent rounds, so accuracy
and completeness are critical even within the token constraint.
</system_role>

<task>
Summarize the provided deliberation round into approximately 100-150 tokens.

Focus on CONTENT over attribution - what was discussed matters more than who said it,
though you should note if there are clear opposing camps or if one persona raised
a particularly novel point.
</task>

<output_format>
Generate a dense, information-rich summary. Use bullet points or short paragraphs.

Good summary:
"Three key tensions emerged: (1) Cost vs quality tradeoff - financial analysis
showed $50K investment but unclear ROI timeline; (2) Risk tolerance - security
raised data privacy concerns while growth prioritized speed; (3) Technical debt -
engineering warned against quick fixes. Consensus on need for phased approach.
Open question: What's acceptable timeline for break-even?"

Bad summary:
"The team discussed various perspectives on the problem. Some people had concerns
while others were optimistic. More discussion needed."
</output_format>

<guidelines>
ALWAYS:
- Capture concrete details (numbers, timeframes, specific risks)
- Note agreements AND disagreements
- Include open questions or uncertainties
- Use precise language

NEVER:
- Editorialize or add your own opinions
- Omit dissenting views
- Make up details not in the contributions
- Exceed 150 tokens significantly
</guidelines>"""


def compose_summarization_request(
    round_number: int, contributions: list[dict], problem_statement: str = None
) -> str:
    """Compose a summarization request for a completed round.

    Args:
        round_number: The round being summarized (1-7)
        contributions: List of dicts with 'persona' and 'content' keys
        problem_statement: Optional problem context (helpful for Round 1)

    Returns:
        Formatted prompt for summarization
    """
    # Format contributions
    contributions_text = "\n\n---\n\n".join(
        [f"[{contrib['persona']}]\n{contrib['content']}" for contrib in contributions]
    )

    # Add problem context for Round 1 to help ground the summary
    context = ""
    if round_number == 1 and problem_statement:
        context = f"""
<problem_context>
{problem_statement}
</problem_context>

"""

    return f"""{context}<round_contributions>
Round {round_number} Contributions:

{contributions_text}
</round_contributions>

Summarize this round into 100-150 tokens. Focus on key arguments, points of
agreement/disagreement, evidence cited, and open questions."""


# Example usage
if __name__ == "__main__":
    example_contributions = [
        {
            "persona": "Zara Morales (Growth)",
            "content": "I see significant opportunity in the SEO channel. Our CAC via paid ads is $80, while industry benchmarks show SEO can achieve $15-20 once ramped. The 6-month lag is real, but this is a long-term play. I'd propose a 70/30 split: $35K SEO, $15K paid to maintain pipeline.",
        },
        {
            "persona": "Maria Santos (Finance)",
            "content": "The numbers concern me. $50K is 40% of our quarterly marketing budget. SEO ROI won't materialize for 6+ months, creating cash flow risk. I need to see: (1) sensitivity analysis on timeline, (2) contingency if results lag, (3) impact on runway. What's our break-even assumption?",
        },
        {
            "persona": "Sarah Kim (Marketing)",
            "content": "Both channels are necessary but serve different goals. Paid ads = predictable pipeline for Q4 targets. SEO = strategic moat for 2025. I agree with Zara's split approach but suggest starting 60/40 to derisk. We can shift allocation in Q1 based on early SEO signals.",
        },
    ]

    request = compose_summarization_request(
        round_number=1,
        contributions=example_contributions,
        problem_statement="Should we invest $50K in SEO or paid ads for customer acquisition?",
    )

    print("=== Example Summarization Request ===\n")
    print(request)
    print("\n=== Expected Summary (~100 tokens) ===")
    print(
        """
Three investment approaches proposed: (1) Zara: 70/30 SEO/paid split based on
$80 vs $15-20 CAC arbitrage; (2) Maria: financial risk from 6-month SEO lag
and 40% budget concentration - needs sensitivity analysis and runway impact;
(3) Sarah: 60/40 split to balance Q4 pipeline needs with 2025 strategic moat,
shift allocation in Q1. Consensus on hybrid approach. Open: break-even timeline
and contingency plan if SEO underperforms.
""".strip()
    )
