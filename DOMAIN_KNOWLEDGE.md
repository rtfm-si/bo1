# DOMAIN_KNOWLEDGE.md

GOVERNANCE LOCK: Do NOT alter, expand, or reinterpret without explicit user request.
DO NOT LOAD unless task requires domain context.

<meetings>
Meeting = session; Decision = problem_statement; Focus Area = sub_problem
3-6 rounds → synthesis with recommendations
MUST NOT alter meeting flow structure
</meetings>

<personas>
45 experts (bo1/data/personas.json); 3-5 per meeting
Contribute, challenge; Facilitator orchestrates only
MUST NOT modify persona roles without explicit request
</personas>

<constraints>
Rounds: 6 max; Recursion: 20 max; Cost: ~$0.10
Semantic dedup: 0.80; Context insufficiency → user modal
MUST NOT exceed defined limits
</constraints>

<cost_model>
Sonnet (main, cached), Haiku (summarize); 90% cache target
Tier limits prevent runaway
Do NOT expose costs to non-admin end users
MUST NOT bypass cost controls
</cost_model>

<user_flows>
Create → submit → decompose → personas → rounds (SSE) → synthesis
May see context_insufficient modal
MUST NOT add steps without request
</user_flows>
