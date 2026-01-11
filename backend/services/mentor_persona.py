"""Mentor persona selection service.

Auto-selects appropriate mentor persona based on question content.
Uses keyword heuristics for fast classification.
"""

import re
from typing import Literal

# Type alias for persona names
PersonaType = Literal["general", "action_coach", "data_analyst", "researcher"]

# Keywords that suggest action_coach persona
ACTION_KEYWORDS = {
    # Task management
    "task",
    "tasks",
    "action",
    "actions",
    "todo",
    "to-do",
    "to do",
    "priority",
    "priorities",
    "prioritize",
    "prioritise",
    # Execution
    "execute",
    "execution",
    "implement",
    "implementation",
    "deliver",
    "deliverable",
    "deadline",
    "deadlines",
    "due",
    "overdue",
    # Progress
    "progress",
    "stuck",
    "blocked",
    "blocker",
    "blockers",
    "unblock",
    # Planning
    "plan",
    "plans",
    "planning",
    "schedule",
    "scheduling",
    "timeline",
    "timelines",
    "roadmap",
    # Focus
    "focus",
    "focusing",
    "focused",
    "next step",
    "next steps",
    "what should i do",
    "what to do",
    "how do i start",
    "where to start",
    # Delegation
    "delegate",
    "delegation",
    "assign",
    "assigned",
}

# Keywords that suggest data_analyst persona
DATA_KEYWORDS = {
    # Data terms
    "data",
    "dataset",
    "datasets",
    "database",
    "spreadsheet",
    "csv",
    "excel",
    # Analysis
    "analysis",
    "analyze",
    "analyse",
    "analytics",
    "insights",
    "insight",
    "pattern",
    "patterns",
    "trend",
    "trends",
    # Metrics
    "metric",
    "metrics",
    "kpi",
    "kpis",
    "measurement",
    "measure",
    "track",
    "tracking",
    # Statistics
    "average",
    "mean",
    "median",
    "percentage",
    "percent",
    "growth rate",
    "conversion",
    "conversion rate",
    # Charts/Visualization
    "chart",
    "charts",
    "graph",
    "graphs",
    "visualize",
    "visualise",
    "visualization",
    "dashboard",
    # Specific analysis
    "compare",
    "comparison",
    "correlation",
    "segment",
    "segments",
    "breakdown",
    "distribution",
    # Business metrics
    "revenue",
    "sales",
    "churn",
    "retention",
    "ltv",
    "cac",
    "arpu",
    "mrr",
    "arr",
}

# Keywords that suggest researcher persona
RESEARCH_KEYWORDS = {
    # Research terms
    "research",
    "investigate",
    "investigation",
    "explore",
    "exploration",
    "study",
    "studies",
    "find out",
    "look into",
    "dig into",
    # Market research
    "market",
    "market research",
    "market size",
    "market analysis",
    "competitor",
    "competitors",
    "competition",
    "competitive",
    # Industry
    "industry",
    "sector",
    "landscape",
    "benchmark",
    "benchmarks",
    "benchmarking",
    # Information gathering
    "what is",
    "who is",
    "how does",
    "why do",
    "when did",
    "where is",
    "latest",
    "recent",
    "current",
    "state of",
    # Trends
    "emerging",
    "trend",
    "trends",
    "forecast",
    "prediction",
    "outlook",
}


def _normalize_text(text: str) -> str:
    """Normalize text for keyword matching.

    Args:
        text: Input text

    Returns:
        Lowercased text with extra whitespace removed
    """
    return re.sub(r"\s+", " ", text.lower().strip())


def _count_keyword_matches(text: str, keywords: set[str]) -> int:
    """Count how many keywords appear in text.

    Args:
        text: Normalized text to search
        keywords: Set of keywords to match

    Returns:
        Number of unique keyword matches
    """
    matches = 0
    for keyword in keywords:
        # Use word boundary matching for single words
        if " " not in keyword:
            pattern = rf"\b{re.escape(keyword)}\b"
            if re.search(pattern, text):
                matches += 1
        else:
            # Multi-word phrases: simple substring match
            if keyword in text:
                matches += 1
    return matches


def auto_select_persona(message: str) -> PersonaType:
    """Auto-select mentor persona based on message content.

    Uses keyword heuristics to classify the question type.

    Args:
        message: User's question/message

    Returns:
        Persona name: 'general', 'action_coach', 'data_analyst', or 'researcher'
    """
    normalized = _normalize_text(message)

    # Count matches for each persona
    action_matches = _count_keyword_matches(normalized, ACTION_KEYWORDS)
    data_matches = _count_keyword_matches(normalized, DATA_KEYWORDS)
    research_matches = _count_keyword_matches(normalized, RESEARCH_KEYWORDS)

    # Select persona with most matches (minimum 2 to override general)
    max_matches = max(action_matches, data_matches, research_matches)
    if max_matches >= 2:
        if research_matches == max_matches:
            return "researcher"
        if data_matches == max_matches:
            return "data_analyst"
        if action_matches == max_matches:
            return "action_coach"

    # Default to general for ambiguous or general questions
    return "general"


def validate_persona(persona: str | None) -> PersonaType:
    """Validate and normalize a persona name.

    Args:
        persona: Persona name to validate

    Returns:
        Valid persona name, defaults to 'general'
    """
    if persona in ("general", "action_coach", "data_analyst", "researcher"):
        return persona  # type: ignore
    return "general"


# =============================================================================
# Persona Definitions
# =============================================================================

PERSONA_DEFINITIONS: dict[PersonaType, dict[str, str | list[str]]] = {
    "general": {
        "id": "general",
        "name": "General Business Advisor",
        "description": "Broad business guidance covering strategy, operations, and decision-making.",
        "expertise": ["strategy", "operations", "leadership", "problem-solving"],
        "icon": "briefcase",
    },
    "action_coach": {
        "id": "action_coach",
        "name": "Action & Execution Coach",
        "description": "Focused guidance on task management, prioritization, and getting things done.",
        "expertise": [
            "task management",
            "prioritization",
            "execution",
            "time management",
            "delegation",
        ],
        "icon": "check-circle",
    },
    "data_analyst": {
        "id": "data_analyst",
        "name": "Data & Analytics Advisor",
        "description": "Expert in data interpretation, metrics analysis, and data-driven decisions.",
        "expertise": ["data analysis", "metrics", "KPIs", "visualization", "business intelligence"],
        "icon": "chart-bar",
    },
    "researcher": {
        "id": "researcher",
        "name": "Research",
        "description": "Investigates market trends, competitors, and industry insights to inform your decisions.",
        "expertise": ["market research", "competitive analysis", "industry trends", "benchmarking"],
        "icon": "search",
    },
}


class MentorPersona:
    """Mentor persona with metadata."""

    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        expertise: list[str],
        icon: str = "user",
    ) -> None:
        """Initialize mentor persona with metadata."""
        self.id = id
        self.name = name
        self.description = description
        self.expertise = expertise
        self.icon = icon

    def to_dict(self) -> dict[str, str | list[str]]:
        """Convert to dict representation."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "expertise": self.expertise,
            "icon": self.icon,
        }


def list_all_personas() -> list[MentorPersona]:
    """List all available mentor personas.

    Returns:
        List of MentorPersona objects with id, name, description, expertise, icon
    """
    return [
        MentorPersona(
            id=str(defn["id"]),
            name=str(defn["name"]),
            description=str(defn["description"]),
            expertise=list(defn["expertise"]) if isinstance(defn["expertise"], list) else [],
            icon=str(defn.get("icon", "user")),
        )
        for defn in PERSONA_DEFINITIONS.values()
    ]


def get_persona_by_id(persona_id: str) -> MentorPersona | None:
    """Get a persona by its ID.

    Args:
        persona_id: Persona identifier

    Returns:
        MentorPersona or None if not found
    """
    defn = PERSONA_DEFINITIONS.get(persona_id)  # type: ignore
    if not defn:
        return None
    return MentorPersona(
        id=str(defn["id"]),
        name=str(defn["name"]),
        description=str(defn["description"]),
        expertise=list(defn["expertise"]) if isinstance(defn["expertise"], list) else [],
        icon=str(defn.get("icon", "user")),
    )
