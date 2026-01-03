"""Challenge phase validation for deliberation contributions.

Validates that round 3-4 contributions contain sufficient critical engagement
markers (counterarguments, challenges, risk identification, etc.).
"""

import logging
import re
from dataclasses import dataclass

logger = logging.getLogger(__name__)

# Challenge markers - patterns indicating critical engagement
# These indicate the expert is stress-testing ideas rather than just agreeing
CHALLENGE_MARKERS: list[tuple[str, re.Pattern[str]]] = [
    # Contrasting/counterargument markers
    ("however", re.compile(r"\bhowever\b", re.IGNORECASE)),
    ("but", re.compile(r"\bbut\b", re.IGNORECASE)),
    ("on_the_other_hand", re.compile(r"\bon the other hand\b", re.IGNORECASE)),
    ("counterargument", re.compile(r"\bcounter-?argument\b", re.IGNORECASE)),
    ("alternatively", re.compile(r"\balternatively\b", re.IGNORECASE)),
    ("conversely", re.compile(r"\bconversely\b", re.IGNORECASE)),
    # Risk/limitation markers
    ("risk", re.compile(r"\brisk(?:s|y)?\b", re.IGNORECASE)),
    ("limitation", re.compile(r"\blimitation(?:s)?\b", re.IGNORECASE)),
    ("weakness", re.compile(r"\bweakness(?:es)?\b", re.IGNORECASE)),
    ("flaw", re.compile(r"\bflaw(?:s|ed)?\b", re.IGNORECASE)),
    ("problem_with", re.compile(r"\bproblem(?:s)? with\b", re.IGNORECASE)),
    ("drawback", re.compile(r"\bdrawback(?:s)?\b", re.IGNORECASE)),
    ("concern", re.compile(r"\bconcern(?:s|ed)?\b", re.IGNORECASE)),
    ("issue_with", re.compile(r"\bissue(?:s)? with\b", re.IGNORECASE)),
    # Challenge/disagreement markers
    ("challenge", re.compile(r"\bchallenge(?:s|d)?\b", re.IGNORECASE)),
    ("disagree", re.compile(r"\bdisagree(?:s|d|ment)?\b", re.IGNORECASE)),
    ("push_back", re.compile(r"\bpush(?:ing)? back\b", re.IGNORECASE)),
    ("alternative_view", re.compile(r"\balternative view\b", re.IGNORECASE)),
    ("different_perspective", re.compile(r"\bdifferent perspective\b", re.IGNORECASE)),
    ("question_whether", re.compile(r"\bquestion(?:s|ing)? whether\b", re.IGNORECASE)),
    # Missing consideration markers
    ("overlooked", re.compile(r"\boverlooked\b", re.IGNORECASE)),
    ("missing", re.compile(r"\bmissing\b", re.IGNORECASE)),
    ("neglected", re.compile(r"\bneglected\b", re.IGNORECASE)),
    ("what_if", re.compile(r"\bwhat if\b", re.IGNORECASE)),
    ("fails_to", re.compile(r"\bfails? to\b", re.IGNORECASE)),
    ("doesnt_account", re.compile(r"\bdoesn'?t account\b", re.IGNORECASE)),
    # Critical analysis markers
    ("critique", re.compile(r"\bcritique(?:s|d)?\b", re.IGNORECASE)),
    ("skeptic", re.compile(r"\bskeptic(?:al|ism)?\b", re.IGNORECASE)),
    ("devil_advocate", re.compile(r"\bdevil'?s advocate\b", re.IGNORECASE)),
    ("assumptions", re.compile(r"\bassumption(?:s)?\b", re.IGNORECASE)),
    ("reconsider", re.compile(r"\breconsider\b", re.IGNORECASE)),
]


@dataclass
class ChallengeValidationResult:
    """Result of challenge marker validation."""

    detected_markers: list[str]
    marker_count: int
    passes_threshold: bool
    threshold: int


def detect_challenge_markers(text: str) -> list[str]:
    """Detect challenge engagement markers in text.

    Args:
        text: Contribution content to analyze

    Returns:
        List of marker names found in the text
    """
    if not text:
        return []

    detected: list[str] = []

    for marker_name, pattern in CHALLENGE_MARKERS:
        if pattern.search(text):
            detected.append(marker_name)

    return detected


def has_sufficient_challenge_engagement(
    text: str,
    min_markers: int = 2,
) -> ChallengeValidationResult:
    """Check if text has sufficient challenge engagement markers.

    Args:
        text: Contribution content to validate
        min_markers: Minimum number of distinct markers required (default: 2)

    Returns:
        ChallengeValidationResult with validation details
    """
    markers = detect_challenge_markers(text)
    marker_count = len(markers)

    return ChallengeValidationResult(
        detected_markers=markers,
        marker_count=marker_count,
        passes_threshold=marker_count >= min_markers,
        threshold=min_markers,
    )


def generate_challenge_reprompt(
    expert_name: str,
    detected_markers: list[str],
    required_markers: int,
    original_contribution: str,
) -> str:
    """Generate a reprompt message for contributions lacking challenge engagement.

    Args:
        expert_name: Name of the expert for context
        detected_markers: Markers found in original contribution
        required_markers: Minimum markers required
        original_contribution: Original contribution (truncated for context)

    Returns:
        Reprompt message instructing expert to engage more critically
    """
    detected_str = ", ".join(detected_markers) if detected_markers else "none"

    # Truncate original contribution for context (first 200 chars)
    snippet = original_contribution[:200].replace("\n", " ")
    if len(original_contribution) > 200:
        snippet += "..."

    return f"""Your previous response lacked sufficient critical engagement for the challenge phase.

**What we detected**: {len(detected_markers)} marker(s) - {detected_str}
**Required**: At least {required_markers} distinct challenge markers

Challenge phase (rounds 3-4) requires stress-testing ideas through:
- Counterarguments: "however", "but", "alternatively", "conversely"
- Risk identification: "risk", "limitation", "weakness", "drawback", "concern"
- Disagreement: "challenge", "disagree", "push back", "question whether"
- Missing considerations: "overlooked", "missing", "what if", "fails to"
- Critical analysis: "critique", "skeptical", "assumptions", "reconsider"

**Your previous response began**: "{snippet}"

Please provide a revised response that actively challenges, questions assumptions, identifies risks, or offers counterarguments to the ideas discussed. DO NOT simply agree or summarize - engage critically."""


def validate_challenge_phase_contribution(
    content: str,
    round_number: int,
    expert_name: str,
    expert_type: str = "persona",
    min_markers: int = 2,
) -> tuple[bool, ChallengeValidationResult]:
    """Validate a contribution for challenge phase engagement.

    Only validates contributions in rounds 3-4 (challenge phase).
    Returns (True, result) for non-challenge rounds.

    Args:
        content: Contribution content to validate
        round_number: Current deliberation round (1-indexed)
        expert_name: Name of the expert for logging
        expert_type: Type of expert for metrics
        min_markers: Minimum challenge markers required

    Returns:
        Tuple of (is_valid, validation_result)
    """
    # Only validate challenge phase (rounds 3-4)
    if round_number not in (3, 4):
        # Return a passing result for non-challenge rounds
        return True, ChallengeValidationResult(
            detected_markers=[],
            marker_count=0,
            passes_threshold=True,
            threshold=min_markers,
        )

    result = has_sufficient_challenge_engagement(content, min_markers)

    if not result.passes_threshold:
        # Log warning with snippet
        snippet = content[:100].replace("\n", " ") + "..." if len(content) > 100 else content
        logger.warning(
            f"Challenge phase validation failed for {expert_name} in round {round_number}: "
            f"found {result.marker_count}/{result.threshold} markers. "
            f"Detected: {result.detected_markers}. "
            f"Snippet: '{snippet}'"
        )
    else:
        logger.debug(
            f"Challenge phase validation passed for {expert_name}: "
            f"{result.marker_count} markers ({result.detected_markers[:3]}...)"
        )

    return result.passes_threshold, result
