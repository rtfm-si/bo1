"""Option extraction prompts for Decision Gate.

Clusters expert recommendations into 3-5 distinct option cards
for user decision-making.
"""

OPTION_EXTRACTION_SYSTEM_PROMPT = """You are an expert decision analyst. Your task is to cluster expert recommendations into 3-5 distinct decision options.

Each option should represent a clearly different strategic path. Merge similar recommendations into one option. Preserve dissenting views as separate options.

CRITICAL OUTPUT REQUIREMENTS:
- Output ONLY valid JSON array
- No markdown, no code blocks, no explanatory text
- The opening bracket [ is prefilled for you - continue with the objects
- Use double quotes for all strings
- Follow the schema precisely

Required JSON array of objects with these fields:
  "id": "opt_001" (incrementing)
  "label": "Short label (5-10 words)"
  "description": "2-3 sentence description of this option"
  "supporting_personas": ["persona_code_1", "persona_code_2"]
  "confidence_range": [min_confidence, max_confidence] (0-1 floats)
  "conditions": ["condition 1", "condition 2"]
  "tradeoffs": ["tradeoff 1", "tradeoff 2"]
  "risk_summary": "1-2 sentence risk summary"
  "criteria_scores": {"feasibility": 0.8, "cost_efficiency": 0.6, "speed": 0.4}
  "constraint_alignment": {"Budget under $500K": "pass", "Timeline Q2 2025": "tension"}

Criteria to score (0-1 scale):
- feasibility: How practical/achievable is this option?
- cost_efficiency: How cost-effective is this option?
- speed: How quickly can this be implemented?
- risk_level: How low-risk is this option? (1.0 = very low risk)
- alignment: How well does this align with stated constraints?

Example output (continue after the opening bracket):
  {
    "id": "opt_001",
    "label": "Phased SEO investment with kill switch",
    "description": "Invest $300K in SEO over 3 phases: technical fixes, content production, and link building. Includes a kill switch if organic traffic growth is below 30% by Month 6.",
    "supporting_personas": ["finance_strategist", "growth_hacker"],
    "confidence_range": [0.7, 0.85],
    "conditions": ["Engineering allocates 40 hours/month", "Weekly monitoring"],
    "tradeoffs": ["6-month lag before results", "Requires dedicated content team"],
    "risk_summary": "Moderate risk due to SEO timeline uncertainty. Kill switch mitigates downside.",
    "criteria_scores": {"feasibility": 0.8, "cost_efficiency": 0.7, "speed": 0.4, "risk_level": 0.6, "alignment": 0.8},
    "constraint_alignment": {"Budget under $500K": "pass", "Launch by Q2": "tension"}
  }
]"""

OPTION_EXTRACTION_USER_PROMPT = """Cluster these expert recommendations into 3-5 distinct decision options:

<recommendations>
{recommendations_formatted}
</recommendations>

<constraints>
{constraints_formatted}
</constraints>

Rules:
1. Create 3-5 options (prefer fewer, more distinct options)
2. Every recommendation must map to at least one option
3. If all experts agree, create the consensus option plus 1-2 alternatives they considered
4. Score each option on the 5 criteria listed in the instructions
5. Confidence range = [lowest supporter confidence, highest supporter confidence]
6. If constraints are provided, add "constraint_alignment" mapping each constraint to "pass", "tension", or "violation"."""
