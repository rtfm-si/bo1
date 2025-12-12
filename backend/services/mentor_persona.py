"""Mentor persona selection service.

Auto-selects appropriate mentor persona based on question content.
Uses keyword heuristics for fast classification.
"""

import re
from typing import Literal

# Type alias for persona names
PersonaType = Literal["general", "action_coach", "data_analyst"]

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
        Persona name: 'general', 'action_coach', or 'data_analyst'
    """
    normalized = _normalize_text(message)

    # Count matches for each persona
    action_matches = _count_keyword_matches(normalized, ACTION_KEYWORDS)
    data_matches = _count_keyword_matches(normalized, DATA_KEYWORDS)

    # Select persona with most matches (minimum 2 to override general)
    if data_matches >= 2 and data_matches > action_matches:
        return "data_analyst"
    if action_matches >= 2 and action_matches > data_matches:
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
    if persona in ("general", "action_coach", "data_analyst"):
        return persona  # type: ignore
    return "general"
