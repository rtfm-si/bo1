"""Comparison question detector.

Detects "this vs that" style comparison questions and generates
appropriate research queries for market context.

Examples of comparison questions:
- "Series A now vs wait 6 months"
- "Should I build vs buy?"
- "React vs Svelte for our frontend"
- "Expand to Europe or focus on US market?"
"""

import logging
import re
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class ComparisonResult:
    """Result of comparison detection."""

    is_comparison: bool
    """Whether the problem is a comparison question."""

    options: list[str] = field(default_factory=list)
    """The options being compared (e.g., ["Series A now", "wait 6 months"])."""

    comparison_type: str = ""
    """Type of comparison (timing, build_vs_buy, technology, market, strategy)."""

    research_queries: list[dict[str, str]] = field(default_factory=list)
    """Suggested research queries with priority and reason."""


class ComparisonDetector:
    """Detects comparison-type decision questions.

    Identifies questions that compare two or more options and generates
    proactive research queries to inform the comparison.
    """

    # Patterns for detecting comparisons (ordered from most specific to general)
    COMPARISON_PATTERNS = [
        # Timing patterns (most specific - must come first)
        # "X now vs wait/later/defer"
        (r"(\w+(?:\s+\w+)*?)\s+now\s+(?:vs\.?|or)\s+(wait(?:\s+\d+\s+\w+)?|later|defer)", "timing"),
        # "now vs later/wait"
        (r"(now)\s+(?:vs\.?|or)\s+(wait(?:\s+\d+\s+\w+)?|later|defer)", "timing"),
        # "build vs buy" (specific pattern)
        (r"(build)\s+(?:vs\.?|or)\s+(buy)", "build_vs_buy"),
        # "hire vs outsource"
        (r"(hire)\s+(?:vs\.?|or|versus)\s+(outsource|contract)", "hiring"),
        # "expand to X or Y" (market expansion)
        (r"expand\s+to\s+(\w+)\s+or\s+(\w+)", "market"),
        # "comparing X to Y" / "compare X with Y" (limited capture)
        (r"compar(?:e|ing)\s+(\w+)\s+(?:to|with)\s+(\w+)", "explicit"),
        # "choose between X and Y"
        (r"choose\s+between\s+(\w+)\s+and\s+(\w+)", "explicit"),
        # "better: X or Y"
        (r"better[:\s]+(\w+)\s+or\s+(\w+)", "explicit"),
        # "X vs Y" / "X versus Y" - capture just the adjacent words
        (r"(\w+)\s+(?:vs\.?|versus)\s+(\w+)", "explicit"),
        # "should we X or Y" - limit capture to single words after should
        (r"should\s+(?:I|we)\s+(\w+)\s+or\s+(\w+)", "choice"),
    ]

    # Context keywords that indicate comparison decisions
    COMPARISON_KEYWORDS = [
        "versus",
        " vs ",
        " vs.",
        " or ",
        "which is better",
        "should we choose",
        "alternative",
        "option a",
        "option b",
        "tradeoff",
        "trade-off",
        "compare",
        "comparing",
    ]

    # Research query templates for different comparison types
    RESEARCH_TEMPLATES = {
        "timing": [
            {"template": "current market conditions for {context}", "priority": "HIGH"},
            {"template": "market timing considerations for {option_a}", "priority": "MEDIUM"},
            {"template": "cost of waiting vs acting now for {context}", "priority": "MEDIUM"},
        ],
        "build_vs_buy": [
            {"template": "build vs buy analysis for {context}", "priority": "HIGH"},
            {"template": "total cost of ownership {option_a} vs {option_b}", "priority": "MEDIUM"},
            {"template": "time to market considerations build vs buy", "priority": "MEDIUM"},
        ],
        "market": [
            {"template": "{option_a} market size and growth 2025", "priority": "HIGH"},
            {"template": "{option_b} market size and growth 2025", "priority": "HIGH"},
            {"template": "market entry barriers {option_a} vs {option_b}", "priority": "MEDIUM"},
        ],
        "technology": [
            {"template": "{option_a} vs {option_b} comparison 2025", "priority": "HIGH"},
            {"template": "{option_a} developer ecosystem and community", "priority": "MEDIUM"},
            {"template": "{option_b} developer ecosystem and community", "priority": "MEDIUM"},
        ],
        "hiring": [
            {"template": "hire vs outsource software development 2025", "priority": "HIGH"},
            {"template": "contractor vs employee cost analysis", "priority": "MEDIUM"},
            {"template": "outsourcing risks and benefits", "priority": "MEDIUM"},
        ],
        "explicit": [
            {"template": "{option_a} vs {option_b} analysis", "priority": "HIGH"},
            {"template": "pros and cons {option_a}", "priority": "MEDIUM"},
            {"template": "pros and cons {option_b}", "priority": "MEDIUM"},
        ],
        "choice": [
            {"template": "{option_a} vs {option_b} decision framework", "priority": "HIGH"},
            {"template": "risks and benefits {option_a}", "priority": "MEDIUM"},
            {"template": "risks and benefits {option_b}", "priority": "MEDIUM"},
        ],
    }

    @classmethod
    def detect(cls, problem_statement: str, context: str | None = None) -> ComparisonResult:
        """Detect if problem is a comparison question.

        Args:
            problem_statement: The decision/problem to analyze
            context: Optional additional context

        Returns:
            ComparisonResult with detection results and suggested queries
        """
        full_text = problem_statement.lower()
        if context:
            full_text += " " + context.lower()

        # Quick check for comparison keywords
        has_comparison_keyword = any(kw in full_text for kw in cls.COMPARISON_KEYWORDS)

        if not has_comparison_keyword:
            return ComparisonResult(is_comparison=False)

        # Try each pattern
        for pattern, comparison_type in cls.COMPARISON_PATTERNS:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                options = [match.group(1).strip(), match.group(2).strip()]
                # Clean up options
                options = [cls._clean_option(opt) for opt in options]

                logger.info(
                    f"ComparisonDetector: Detected '{comparison_type}' comparison "
                    f"with options: {options}"
                )

                # Generate research queries
                queries = cls.generate_research_queries(
                    options=options,
                    comparison_type=comparison_type,
                    context=problem_statement,
                )

                return ComparisonResult(
                    is_comparison=True,
                    options=options,
                    comparison_type=comparison_type,
                    research_queries=queries,
                )

        # Has keywords but no specific pattern matched
        # Try to extract implicit comparison
        if " or " in full_text:
            # Try to find "X or Y" without the full pattern
            simple_match = re.search(r"(\w+)\s+or\s+(\w+)", full_text)
            if simple_match:
                options = [simple_match.group(1), simple_match.group(2)]
                return ComparisonResult(
                    is_comparison=True,
                    options=options,
                    comparison_type="choice",
                    research_queries=cls.generate_research_queries(
                        options=options,
                        comparison_type="choice",
                        context=problem_statement,
                    ),
                )

        return ComparisonResult(is_comparison=False)

    @classmethod
    def _clean_option(cls, option: str) -> str:
        """Clean up an extracted option string."""
        # Remove common filler words
        filler_words = ["the", "a", "an", "to", "for", "with", "in", "on"]
        words = option.split()
        words = [w for w in words if w.lower() not in filler_words or len(words) == 1]
        return " ".join(words).strip()

    @classmethod
    def generate_research_queries(
        cls,
        options: list[str],
        comparison_type: str,
        context: str,
    ) -> list[dict[str, str]]:
        """Generate research queries for the comparison.

        Args:
            options: The options being compared
            comparison_type: Type of comparison detected
            context: Original problem context

        Returns:
            List of research query dicts with question, priority, and reason
        """
        templates = cls.RESEARCH_TEMPLATES.get(comparison_type, cls.RESEARCH_TEMPLATES["explicit"])
        queries = []

        # Extract relevant context keywords
        context_words = context[:100] if len(context) > 100 else context

        for template_info in templates:
            template = template_info["template"]
            priority = template_info["priority"]

            # Format template with options
            formatted_query = template.format(
                option_a=options[0] if options else "option A",
                option_b=options[1] if len(options) > 1 else "option B",
                context=context_words,
            )

            queries.append(
                {
                    "question": formatted_query,
                    "priority": priority,
                    "reason": f"Comparison research: {options[0]} vs {options[1] if len(options) > 1 else 'alternative'}",
                }
            )

        return queries
