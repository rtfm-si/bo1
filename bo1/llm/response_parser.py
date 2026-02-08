"""Response parsing utilities for LLM responses.

Consolidates parsing logic for structured responses from different agents.
"""

import json
import logging
import re
from typing import Any

from bo1.constants import TokenLimits
from bo1.graph.state import DeliberationGraphState
from bo1.models.recommendations import Recommendation
from bo1.utils.confidence_parser import (
    extract_confidence_from_text,
    parse_conditions,
    parse_confidence_level,
)
from bo1.utils.extraction import ResponseExtractor
from bo1.utils.xml_parsing import extract_xml_tag

logger = logging.getLogger(__name__)

# Valid facilitator actions (duplicated here to avoid circular import)
# Canonical definition is in bo1.agents.facilitator.VALID_FACILITATOR_ACTIONS
VALID_FACILITATOR_ACTIONS: set[str] = {
    "continue",
    "vote",
    "research",
    "moderator",
    "clarify",
    "analyze_data",
}

# Metrics tracking for facilitator action parsing
_facilitator_parse_stats = {"success": 0, "fallback": 0, "invalid_action": 0}


class XMLValidationError(Exception):
    """Raised when XML structure is malformed."""

    def __init__(  # noqa: D107
        self, message: str, tag: str | None = None, details: str | None = None
    ) -> None:
        self.tag = tag
        self.details = details
        super().__init__(message)


# =============================================================================
# CHALLENGE PHASE VALIDATION PATTERNS
# =============================================================================

# Patterns indicating generic agreement (passive/sycophantic responses)
GENERIC_AGREEMENT_PATTERNS = [
    r"\bi\s+(?:fully\s+)?agree\s+with\s+\w+",  # "I agree with Henrik"
    r"\bbuilding\s+on\s+\w+'?s?\s+(?:point|insight|analysis)",  # "building on X's point"
    r"\bto\s+add\s+to\s+\w+'?s?\s+(?:excellent\s+)?(?:point|analysis)",  # "to add to X's point"
    r"\b(?:great|excellent|fantastic|wonderful)\s+point\s+(?:by\s+)?\w+",  # "great point, X"
    r"\b\w+\s+(?:is\s+)?(?:exactly|absolutely)\s+right",  # "X is exactly right"
    r"\bi\s+(?:strongly\s+)?support\s+\w+'?s?\s+(?:view|position|recommendation)",  # "I support X's view"
    r"\b(?:echoing|reinforcing)\s+what\s+\w+\s+said",  # "echoing what X said"
    r"\b(?:as\s+)?\w+\s+(?:correctly|rightly)\s+(?:pointed\s+out|noted|observed)",  # "as X correctly noted"
    r"\bwell\s+said,?\s+\w+",  # "well said, Henrik"
    r"\b\w+\s+makes?\s+(?:an?\s+)?(?:excellent|great|valid)\s+point",  # "X makes an excellent point"
]

# Patterns indicating active challenge/critique (substantive engagement)
CHALLENGE_INDICATOR_PATTERNS = [
    r"\bi\s+disagree",  # "I disagree"
    r"\bhowever,?\s+(?:i\s+)?(?:would\s+)?(?:argue|suggest|contend)",  # "however, I would argue"
    r"\bthe\s+(?:flaw|problem|issue|weakness)\s+(?:in|with)",  # "the flaw in"
    r"\bwhat\s+about\s+(?:the\s+)?(?:risk|case|scenario)",  # "what about the risk"
    r"\bthis\s+(?:overlooks?|ignores?|misses?|neglects?)",  # "this overlooks"
    r"\b(?:but|yet)\s+we?\s+(?:haven't|have\s+not)\s+(?:considered|addressed)",  # "but we haven't considered"
    r"\b(?:i\s+)?(?:would\s+)?challenge\s+(?:the\s+)?(?:assumption|premise)",  # "I challenge the assumption"
    r"\bcontrary\s+to\s+\w+'?s?\s+(?:view|position|assertion)",  # "contrary to X's view"
    r"\b(?:playing\s+)?devil'?s?\s+advocate",  # "playing devil's advocate"
    r"\b(?:a\s+)?(?:critical|key)\s+(?:risk|concern|gap|blind\s+spot)",  # "a critical risk"
    r"\bwhat\s+if\s+(?:the\s+)?(?:assumption|premise|hypothesis)",  # "what if the assumption"
    r"\b(?:i'm|i\s+am)\s+(?:not\s+)?(?:convinced|persuaded)",  # "I'm not convinced"
    r"\b(?:an?\s+)?(?:alternative|opposing)\s+(?:view|perspective)",  # "an alternative view"
    r"\b(?:the\s+)?(?:counterargument|counter-argument)",  # "the counterargument"
    r"\bunintended\s+consequences?",  # "unintended consequences"
]


class ValidationConfig:
    """Configuration for LLM response validation with re-prompt behavior.

    Attributes:
        required_tags: List of XML tags that must be present
        max_retries: Maximum retry attempts on validation failure (default: 1)
        strict: If True, raise exception after retries exhausted (default: False)
    """

    def __init__(
        self,
        required_tags: list[str],
        max_retries: int = 1,
        strict: bool = False,
    ) -> None:
        """Initialize validation config.

        Args:
            required_tags: XML tags required in response
            max_retries: Max validation retries (default: 1)
            strict: Raise on exhausted retries (default: False)
        """
        self.required_tags = required_tags
        self.max_retries = max_retries
        self.strict = strict


class XMLValidator:
    """Validates XML structure in LLM responses.

    Detects:
    - Unclosed tags: <thinking>content without </thinking>
    - Invalid nesting: <a><b></a></b>
    - Missing required elements
    """

    # Common XML tags used in responses
    KNOWN_TAGS = {
        "thinking",
        "contribution",
        "recommendation",
        "reasoning",
        "confidence",
        "conditions",
        "action",
        "decision",
        "summary",
        "question",
        "reason",
        "next_speaker",
    }

    @staticmethod
    def find_unclosed_tags(text: str) -> list[str]:
        """Find XML tags that are opened but not closed.

        Args:
            text: Content to validate

        Returns:
            List of unclosed tag names
        """
        unclosed = []
        # Find all opening tags
        open_pattern = r"<(\w+)(?:\s[^>]*)?>(?!.*</\1>)"
        for match in re.finditer(open_pattern, text, re.DOTALL | re.IGNORECASE):
            tag = match.group(1).lower()
            if tag in XMLValidator.KNOWN_TAGS:
                # Verify it's actually unclosed (not just regex limitation)
                close_pattern = rf"</{tag}>"
                if not re.search(close_pattern, text, re.IGNORECASE):
                    unclosed.append(tag)
        return unclosed

    @staticmethod
    def find_invalid_nesting(text: str) -> list[tuple[str, str]]:
        """Find XML tags with invalid nesting order.

        Args:
            text: Content to validate

        Returns:
            List of (outer_tag, inner_tag) pairs that are incorrectly nested
        """
        invalid_pairs = []
        # Track tag positions
        tag_stack: list[tuple[str, int]] = []

        # Find all tags (opening and closing)
        tag_pattern = r"<(/?)(\w+)(?:\s[^>]*)?>"
        for match in re.finditer(tag_pattern, text, re.IGNORECASE):
            is_close = match.group(1) == "/"
            tag = match.group(2).lower()

            if tag not in XMLValidator.KNOWN_TAGS:
                continue

            if is_close:
                # Find matching open tag
                found = False
                for i in range(len(tag_stack) - 1, -1, -1):
                    if tag_stack[i][0] == tag:
                        # Check if there are unclosed tags between
                        if i < len(tag_stack) - 1:
                            for j in range(i + 1, len(tag_stack)):
                                invalid_pairs.append((tag_stack[j][0], tag))
                        tag_stack = tag_stack[:i]
                        found = True
                        break
                if not found and tag_stack:
                    # Closing tag without matching open
                    pass  # Handled by find_unclosed_tags
            else:
                tag_stack.append((tag, match.start()))

        return invalid_pairs

    @staticmethod
    def validate(text: str, required_tags: list[str] | None = None) -> tuple[bool, list[str]]:
        """Validate XML structure in text.

        Args:
            text: Content to validate
            required_tags: Optional list of tags that must be present

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []

        # Check for unclosed tags
        unclosed = XMLValidator.find_unclosed_tags(text)
        if unclosed:
            errors.append(f"Unclosed tags: {', '.join(unclosed)}")

        # Check for invalid nesting
        invalid_nesting = XMLValidator.find_invalid_nesting(text)
        if invalid_nesting:
            pairs = [f"<{outer}>...<{inner}>" for outer, inner in invalid_nesting]
            errors.append(f"Invalid tag nesting: {', '.join(pairs)}")

        # Check required tags
        if required_tags:
            for tag in required_tags:
                if not extract_xml_tag(text, tag):
                    errors.append(f"Missing required tag: <{tag}>")

        return len(errors) == 0, errors

    @staticmethod
    def get_validation_feedback(errors: list[str]) -> str:
        """Generate feedback message for re-response request.

        Args:
            errors: List of validation errors

        Returns:
            Formatted feedback for LLM
        """
        return (
            "Your response had XML formatting issues:\n"
            + "\n".join(f"- {e}" for e in errors)
            + "\n\nPlease provide your response again with properly closed and nested XML tags."
        )


class ResponseParser:
    """Utilities for parsing structured data from LLM responses.

    Consolidates common parsing patterns used across facilitator, voting,
    and deliberation agents.
    """

    # Patterns that indicate a persona is confused/meta-discussing instead of engaging
    META_DISCUSSION_PATTERNS = [
        r"should i respond as",
        r"what is the specific context",
        r"interaction protocol",
        r"communication expectations",
        r"what role should i",
        r"how should i respond",
        r"framework for this communication",
        r"should i follow a different",
        r"what is the context",
        r"seeking clear direction",
        r"potential misunderstanding",
        r"need for precise guidance",
        r"understanding the specific communication",
    ]

    # Patterns indicating expert is struggling with insufficient context
    # (broader than META_DISCUSSION_PATTERNS - catches experts discussing LACK of information)
    INSUFFICIENT_CONTEXT_PATTERNS = [
        r"without (?:more|additional|further) (?:context|information|details)",
        r"(?:need|require) more (?:context|information|specifics)",
        r"unclear what (?:the|you) (?:want|need|expect)",
        r"(?:missing|lack(?:ing)?|insufficient) (?:key |critical )?(?:details|information|context)",
        r"to provide (?:a |more )?(?:specific|meaningful|actionable) (?:advice|recommendation)",
        r"(?:hard|difficult|impossible) to (?:assess|evaluate|analyze) without",
        r"what (?:exactly|specifically) (?:are|is) (?:the|your)",
        r"(?:could|would) you (?:clarify|elaborate|provide)",
        r"i(?:'m| am) not (?:clear|sure) (?:on|about) what",
        r"the problem (?:statement |context )?(?:is |doesn't |lacks )",
        r"i(?:'m| am) not seeing (?:a |the )?(?:problem|context|discussion)",
        r"(?:problem|context|discussion) (?:appears? to be |seems? )?missing",
        r"before (?:i can |we )(?:proceed|provide|offer)",
        r"cannot (?:offer|provide|give) (?:specific|concrete|meaningful)",
    ]

    @staticmethod
    def is_meta_discussion(content: str) -> bool:
        """Check if the content appears to be meta-discussion rather than substantive analysis.

        Args:
            content: The contribution text to check

        Returns:
            True if the content appears to be meta-discussion about the task itself
            rather than engaging with the problem.

        Example:
            >>> ResponseParser.is_meta_discussion("Should I respond as Henrik?")
            True
            >>> ResponseParser.is_meta_discussion("Based on the market analysis, I recommend...")
            False
        """
        content_lower = content.lower()
        for pattern in ResponseParser.META_DISCUSSION_PATTERNS:
            if re.search(pattern, content_lower):
                logger.warning(f"Meta-discussion pattern detected: {pattern}")
                return True
        return False

    @staticmethod
    def is_context_insufficient_discussion(content: str) -> bool:
        """Check if contribution indicates expert is struggling with insufficient context.

        This is broader than is_meta_discussion() - it catches when experts are
        discussing the LACK of information rather than engaging with the problem itself.

        Args:
            content: The contribution text to check

        Returns:
            True if the content indicates expert needs more context to engage properly

        Example:
            >>> ResponseParser.is_context_insufficient_discussion(
            ...     "Without more context about the business model, I cannot provide specific advice."
            ... )
            True
            >>> ResponseParser.is_context_insufficient_discussion(
            ...     "Based on typical startup patterns, I recommend focusing on unit economics."
            ... )
            False
        """
        content_lower = content.lower()

        # First check existing meta-discussion patterns
        if ResponseParser.is_meta_discussion(content):
            return True

        # Then check insufficient context patterns
        for pattern in ResponseParser.INSUFFICIENT_CONTEXT_PATTERNS:
            if re.search(pattern, content_lower):
                logger.warning(f"Insufficient context pattern detected: {pattern}")
                return True

        return False

    @staticmethod
    def parse_persona_response(content: str) -> tuple[str | None, str, str | None]:
        """Parse persona response to extract <thinking>, <contribution>, and <summary>.

        Args:
            content: Raw response content

        Returns:
            Tuple of (thinking, contribution, inline_summary)
        """
        # Use extract_xml_tag utility instead of manual parsing
        thinking = extract_xml_tag(content, "thinking")

        # Extract <summary> before contribution to strip it from content
        inline_summary = extract_xml_tag(content, "summary")

        # Extract <contribution> if present
        contribution = extract_xml_tag(content, "contribution")
        if not contribution:
            # If no explicit <contribution> tag, use the part after </thinking>
            if "</thinking>" in content:
                contribution = content.split("</thinking>", 1)[1].strip()
            else:
                # No tags at all - use full content
                contribution = content

        # Strip leaked <summary> tags from contribution text
        if inline_summary and contribution:
            contribution = re.sub(
                r"<summary>[\s\S]*?</summary>", "", contribution, flags=re.IGNORECASE
            ).strip()

        return thinking, contribution, inline_summary

    @staticmethod
    def parse_recommendation_from_response(response_content: str, persona: Any) -> Recommendation:
        """Parse recommendation from LLM response.

        No keyword matching - just extracts structured fields.
        Trusts the LLM to provide the recommendation.

        Args:
            response_content: Raw LLM response
            persona: Persona object with 'code' and 'name' attributes

        Returns:
            Parsed Recommendation object

        Example:
            >>> content = '''<recommendation>60% salary, 40% dividends hybrid</recommendation>
            ... <reasoning>This balances tax efficiency...</reasoning>
            ... <confidence>high</confidence>
            ... <conditions>Review quarterly</conditions>'''
            >>> persona = type('P', (), {'code': 'test', 'name': 'Test Persona'})()
            >>> rec = ResponseParser.parse_recommendation_from_response(content, persona)
            >>> rec.recommendation
            '60% salary, 40% dividends hybrid'
        """
        # Extract recommendation text directly (no keyword matching!)
        recommendation = extract_xml_tag(response_content, "recommendation")
        if not recommendation:
            logger.error(
                f"⚠️ FALLBACK: Could not extract <recommendation> tag from {persona.name} response. "
                f"Response preview: {response_content[:200]}..."
            )
            recommendation = "[No recommendation provided]"

        # Extract reasoning
        reasoning = extract_xml_tag(response_content, "reasoning")
        if not reasoning:
            logger.warning(
                f"⚠️ FALLBACK: Could not extract <reasoning> tag from {persona.name} recommendation. "
                f"Using fallback text."
            )
            reasoning = "[Reasoning not provided in structured format]"

        # Extract and parse confidence
        confidence_str = extract_xml_tag(response_content, "confidence")
        if not confidence_str:
            # Try fallback pattern matching from full text
            confidence_str = extract_confidence_from_text(response_content)
            if confidence_str:
                logger.info(
                    f"⚠️ FALLBACK: Extracted confidence '{confidence_str}' from {persona.name} "
                    f"using fallback pattern matching (no <confidence> tag)."
                )
            else:
                logger.warning(
                    f"⚠️ FALLBACK: Could not extract confidence from {persona.name} recommendation. "
                    f"Defaulting to 0.6 (medium)."
                )
        confidence = parse_confidence_level(confidence_str)

        # Extract and parse conditions
        conditions_str = extract_xml_tag(response_content, "conditions")
        conditions = parse_conditions(conditions_str)

        return Recommendation(
            persona_code=persona.code,
            persona_name=persona.name,
            recommendation=recommendation,  # Store as-is, no parsing!
            reasoning=reasoning,
            confidence=confidence,
            conditions=conditions,
            weight=1.0,  # Default weight
        )

    @staticmethod
    def parse_facilitator_decision(content: str, state: DeliberationGraphState) -> dict[str, Any]:
        """Parse facilitator decision from response content.

        This extracts the decision action and associated parameters.
        Uses a two-step approach:
        1. Try extracting from <action> or <decision> XML tags (more reliable)
        2. Fall back to keyword matching if no valid XML tag found

        Args:
            content: LLM response content
            state: Deliberation state for persona lookups

        Returns:
            Dictionary with parsed decision details:
            - action: str ("continue", "vote", "research", "moderator", "clarify")
            - reasoning: str
            - next_speaker: str | None (for "continue")
            - speaker_prompt: str | None (for "continue")
            - moderator_type: str | None (for "moderator")
            - moderator_focus: str | None (for "moderator")
            - research_query: str | None (for "research")
            - phase_summary: str | None (for "vote")
            - clarification_question: str | None (for "clarify")
            - clarification_reason: str | None (for "clarify")
        """
        action: str | None = None
        extracted_value: str | None = None

        # Step 1: Try XML tag extraction
        for tag_name in ["action", "decision"]:
            extracted = extract_xml_tag(content, tag_name)
            if extracted:
                extracted_value = extracted.lower().strip()
                if extracted_value in VALID_FACILITATOR_ACTIONS:
                    action = extracted_value
                break  # Found a tag (valid or not), stop searching

        # Step 2: Validate action - raise XMLValidationError if missing or invalid
        session_id = state.get("session_id", "unknown")

        # Case A: No <action> or <decision> tag found at all
        if extracted_value is None:
            _facilitator_parse_stats["invalid_action"] += 1
            logger.warning(
                f"[LLM_RELIABILITY] Facilitator missing action tag. "
                f"session_id={session_id}, "
                f"content_preview={content[:150]!r}..."
            )
            raise XMLValidationError(
                "Missing required <action> tag in facilitator response",
                tag="action",
                details=f"Content preview: {content[:100]}...",
            )

        # Case B: Tag found but value is not valid
        if action is None:
            _facilitator_parse_stats["invalid_action"] += 1
            logger.warning(
                f"[LLM_RELIABILITY] Facilitator invalid action value. "
                f"session_id={session_id}, "
                f"invalid_value={extracted_value!r}, "
                f"valid_actions={sorted(VALID_FACILITATOR_ACTIONS)}, "
                f"content_preview={content[:150]!r}..."
            )
            raise XMLValidationError(
                f"Invalid action value '{extracted_value}' - must be one of {sorted(VALID_FACILITATOR_ACTIONS)}",
                tag="action",
                details=f"Received: {extracted_value}",
            )

        _facilitator_parse_stats["success"] += 1

        # Extract reasoning
        reasoning = extract_xml_tag(content, "thinking") or content[:500]

        # Parse based on action type
        result = {
            "action": action,
            "reasoning": reasoning,
            "next_speaker": None,
            "speaker_prompt": None,
            "moderator_type": None,
            "moderator_focus": None,
            "research_query": None,
            "phase_summary": None,
            "clarification_question": None,
            "clarification_reason": None,
        }

        personas = state.get("personas", [])
        if action == "continue":
            next_speaker = ResponseExtractor.extract_persona_code(content, personas, logger=logger)
            # Fallback: If extraction failed, pick first available persona
            if not next_speaker:
                if personas:
                    next_speaker = personas[0].code
                    logger.warning(
                        f"Failed to extract next_speaker from facilitator response, "
                        f"defaulting to {next_speaker}"
                    )
                else:
                    logger.error(
                        "CRITICAL: Cannot determine next_speaker - no personas available in state"
                    )
                    raise ValueError(
                        "Cannot determine next_speaker for 'continue' action: no personas in state"
                    )
            result["next_speaker"] = next_speaker
            result["speaker_prompt"] = ResponseExtractor.extract_after_marker(
                content, ["prompt:", "focus:", "question:"]
            )
        elif action == "moderator":
            result["moderator_type"] = ResponseExtractor.extract_enum_from_keywords(
                content,
                {"contrarian": "contrarian", "skeptic": "skeptic", "optimist": "optimist"},
                default="contrarian",
            )
            result["moderator_focus"] = ResponseExtractor.extract_after_marker(
                content, ["focus:", "address:", "challenge:"]
            )
        elif action == "research":
            result["research_query"] = ResponseExtractor.extract_after_marker(
                content, ["query:", "question:", "information needed:"]
            )
        elif action == "vote":
            result["phase_summary"] = extract_xml_tag(
                content, "summary"
            ) or ResponseExtractor.extract_after_marker(content, ["summary:"], max_length=500)
        elif action == "clarify":
            result["clarification_question"] = extract_xml_tag(
                content, "question"
            ) or ResponseExtractor.extract_after_marker(
                content, ["question:", "clarify:", "ask:"], max_length=500
            )
            result["clarification_reason"] = extract_xml_tag(
                content, "reason"
            ) or ResponseExtractor.extract_after_marker(
                content, ["reason:", "because:", "why:"], max_length=300
            )

        return result

    @staticmethod
    def validate_contribution_content(content: str, persona_name: str = "") -> tuple[bool, str]:
        """Validate that a contribution is substantive expert analysis, not meta-commentary.

        Detects malformed responses where the LLM responds about the prompt structure
        rather than providing actual expert analysis.

        Args:
            content: The contribution content to validate
            persona_name: Name of the persona (for logging)

        Returns:
            Tuple of (is_valid: bool, reason: str)
            - is_valid: True if content is valid expert contribution
            - reason: Description of why content is invalid (empty if valid)

        Example:
            >>> is_valid, reason = ResponseParser.validate_contribution_content(
            ...     "I apologize, but the guidance doesn't align with the framework..."
            ... )
            >>> is_valid
            False
            >>> reason
            'Meta-response: apology about framework'
        """
        content_lower = content.lower()

        # Pattern 1: Apologies about framework/guidance/instructions
        meta_apology_patterns = [
            r"i\s+apologize.*(?:guidance|framework|instruction|prompt|system)",
            r"(?:sorry|apologies).*(?:doesn't|does not|can't|cannot)\s+align",
            r"(?:this|the)\s+(?:guidance|framework).*doesn't\s+(?:align|match)",
            r"the\s+(?:prompt|instruction).*(?:confus|unclear|doesn't)",
        ]

        for pattern in meta_apology_patterns:
            if re.search(pattern, content_lower):
                logger.warning(
                    f"Malformed response from {persona_name}: Meta-response detected (apology pattern)"
                )
                return False, "Meta-response: apology about framework"

        # Pattern 2: Meta-commentary about the deliberation process
        meta_process_patterns = [
            r"multi[- ]?persona\s+deliberation",
            r"structured\s+response\s+(?:using|with|format)",
            r"<thinking>\s*and\s*<contribution>\s*tags",
            r"existing\s+discussion\s+protocol",
            r"contribution\s+summarization",
            r"response\s+(?:protocol|format|structure)",
        ]

        for pattern in meta_process_patterns:
            if re.search(pattern, content_lower):
                logger.warning(
                    f"Malformed response from {persona_name}: Meta-commentary about process"
                )
                return False, "Meta-response: commentary about deliberation process"

        # Pattern 3: Questions about how to respond (instead of actual response)
        meta_question_patterns = [
            r"should\s+(?:i|a)\s+(?:full|rigorous)\s+response\s+be\s+provided",
            r"would\s+you\s+like\s+me\s+to\s+(?:provide|give|respond)",
            r"how\s+(?:to|should\s+i)\s+(?:ensure|provide|format)",
            r"(?:shall|should)\s+i\s+(?:proceed|continue|respond)",
        ]

        for pattern in meta_question_patterns:
            if re.search(pattern, content_lower):
                logger.warning(
                    f"Malformed response from {persona_name}: Asking how to respond instead of responding"
                )
                return False, "Meta-response: asking how to respond"

        # Pattern 4: Insufficient substance (too short to be meaningful)
        word_count = len(content.split())
        if word_count < TokenLimits.MIN_CONTRIBUTION_WORDS:
            logger.warning(
                f"Malformed response from {persona_name}: Too short ({word_count} words)"
            )
            return False, f"Insufficient substance: only {word_count} words"

        # Pattern 4b: Overlength contribution (exceeds word limit)
        if word_count > TokenLimits.MAX_CONTRIBUTION_WORDS:
            logger.warning(
                f"Overlength response from {persona_name}: {word_count} words "
                f"(max {TokenLimits.MAX_CONTRIBUTION_WORDS})"
            )
            return (
                False,
                f"Overlength: {word_count} words, max {TokenLimits.MAX_CONTRIBUTION_WORDS}",
            )

        # Pattern 5: Starting with defensive language
        defensive_starts = [
            "i apologize",
            "i'm sorry",
            "sorry, but",
            "i cannot",
            "i can't",
            "unfortunately, i",
        ]

        for start in defensive_starts:
            if content_lower.strip().startswith(start):
                logger.warning(
                    f"Malformed response from {persona_name}: Starts with defensive language"
                )
                return False, "Meta-response: starts with defensive language"

        # All checks passed
        return True, ""

    @staticmethod
    def validate_challenge_phase_contribution(
        content: str, round_number: int, persona_name: str = ""
    ) -> tuple[bool, str]:
        """Validate that challenge phase contributions contain substantive critique.

        In rounds 3-4 (1-indexed), contributions should actively challenge ideas
        rather than passively agreeing. This prevents echo-chamber dynamics.

        Args:
            content: The contribution content to validate
            round_number: Current round number (1-indexed)
            persona_name: Name of the persona (for logging)

        Returns:
            Tuple of (is_valid: bool, rejection_reason: str)
            - is_valid: True if contribution has substantive challenge content
            - rejection_reason: Description of why rejected (empty if valid)

        Example:
            >>> is_valid, reason = ResponseParser.validate_challenge_phase_contribution(
            ...     "I agree with Henrik's excellent analysis.", 3
            ... )
            >>> is_valid
            False
            >>> reason
            'Challenge phase requires substantive critique'
        """
        from bo1.constants import ChallengePhaseConfig

        # Only validate in challenge phase rounds
        if round_number not in ChallengePhaseConfig.ROUNDS:
            return True, ""

        content_lower = content.lower()

        # Count agreement patterns
        agreement_matches = 0
        for pattern in GENERIC_AGREEMENT_PATTERNS:
            if re.search(pattern, content_lower):
                agreement_matches += 1

        # Count challenge indicators
        challenge_matches = 0
        for pattern in CHALLENGE_INDICATOR_PATTERNS:
            if re.search(pattern, content_lower):
                challenge_matches += 1

        # If content has challenge indicators, it's valid regardless of agreement
        if challenge_matches > 0:
            logger.debug(
                f"Challenge phase validation passed for {persona_name}: "
                f"{challenge_matches} challenge indicator(s) found"
            )
            return True, ""

        # If no challenge indicators but has agreement patterns, reject
        if agreement_matches > 0:
            logger.warning(
                f"[CHALLENGE_PHASE] Contribution from {persona_name} in round {round_number} "
                f"rejected: {agreement_matches} agreement pattern(s), 0 challenge indicators. "
                f"Content preview: {content[:100]}..."
            )
            return False, "Challenge phase requires substantive critique"

        # No agreement patterns and no challenge indicators - allow
        # (could be neutral technical contribution)
        logger.debug(
            f"Challenge phase validation passed for {persona_name}: no agreement patterns detected"
        )
        return True, ""

    @staticmethod
    def truncate_contribution(
        content: str, max_words: int = TokenLimits.MAX_CONTRIBUTION_WORDS
    ) -> str:
        """Truncate contribution to max word count, preferring sentence boundaries.

        Args:
            content: The contribution content to truncate
            max_words: Maximum allowed words (default: TokenLimits.MAX_CONTRIBUTION_WORDS)

        Returns:
            Truncated content with [truncated] marker if shortened

        Example:
            >>> long_text = "Word " * 400
            >>> result = ResponseParser.truncate_contribution(long_text, max_words=300)
            >>> len(result.split()) <= 301  # 300 words + [truncated] marker
            True
        """
        words = content.split()
        if len(words) <= max_words:
            return content

        # Take first max_words
        truncated_words = words[:max_words]
        truncated_text = " ".join(truncated_words)

        # Try to find last sentence boundary within truncated text
        sentence_endings = [". ", "! ", "? ", ".\n", "!\n", "?\n"]
        last_boundary = -1
        for ending in sentence_endings:
            pos = truncated_text.rfind(ending)
            if pos > last_boundary:
                last_boundary = pos + len(ending) - 1  # Include the punctuation

        # Use sentence boundary if it preserves at least 50% of content
        min_preserve = max_words // 2
        if last_boundary > 0:
            boundary_text = truncated_text[: last_boundary + 1].strip()
            if len(boundary_text.split()) >= min_preserve:
                return f"{boundary_text} [truncated]"

        # Fall back to word boundary
        return f"{truncated_text} [truncated]"


def extract_json_from_response(text: str) -> dict[str, Any]:
    r"""Extract JSON from LLM response, stripping markdown/XML wrappers if present.

    Handles common LLM output patterns (in order of preference):
    1. Raw JSON: {"key": "value"}
    2. XML wrapped: <json_output>{"key": "value"}</json_output>
    3. Markdown wrapped: ```json\n{"key": "value"}\n```

    This is the FALLBACK parser. Prefer using prefill="{" in PromptRequest
    to prevent markdown wrapping in the first place.

    Args:
        text: Raw LLM response text

    Returns:
        Parsed JSON as dict

    Raises:
        json.JSONDecodeError: If JSON parsing fails after all extraction attempts
    """
    text = text.strip()

    # Try raw JSON first (most common with prefill)
    if text.startswith("{"):
        try:
            result: dict[str, Any] = json.loads(text)
            return result
        except json.JSONDecodeError:
            pass  # Fall through to other patterns

    # Pattern 1: XML tags <json_output>...</json_output>
    xml_pattern = r"<json_output>\s*(.*?)\s*</json_output>"
    match = re.search(xml_pattern, text, re.DOTALL)
    if match:
        result = json.loads(match.group(1).strip())
        return result

    # Pattern 2: Markdown code blocks ```json ... ``` or ``` ... ```
    code_block_pattern = r"^```(?:json)?\s*\n?(.*?)\n?```$"
    match = re.match(code_block_pattern, text, re.DOTALL)
    if match:
        result = json.loads(match.group(1).strip())
        return result

    # Pattern 3: Malformed markdown (leading ``` without proper closing)
    if text.startswith("```"):
        lines = text.split("\n")
        if lines[-1].strip() == "```":
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        result = json.loads("\n".join(lines).strip())
        return result

    # Last resort: try parsing as-is
    result = json.loads(text)
    return result


# Citation validation results
class CitationValidationResult:
    """Result of citation validation."""

    def __init__(  # noqa: D107
        self,
        citation_count: int,
        min_required: int,
        is_valid: bool,
        warning: str | None = None,
    ) -> None:
        self.citation_count = citation_count
        self.min_required = min_required
        self.is_valid = is_valid
        self.warning = warning


def validate_citations(
    content: str,
    min_citations: int = 3,
    persona_type: str = "researcher",
) -> CitationValidationResult:
    """Validate citation presence in masked persona responses.

    Detects <source> blocks or URL patterns in response content.
    Returns warning (not hard fail) if citation count below threshold.

    Args:
        content: Response content to validate
        min_citations: Minimum required citations (default 3 for researcher)
        persona_type: Type of persona ("researcher" or "moderator")

    Returns:
        CitationValidationResult with validation status and warning if applicable

    Example:
        >>> content = '''<sources><source><url>https://example.com</url></source></sources>'''
        >>> result = validate_citations(content, min_citations=3)
        >>> result.is_valid
        False
        >>> result.warning
        'researcher response has 1 citation(s), minimum 3 required'
    """
    citation_count = 0

    # Pattern 1: Count <source> blocks (preferred structured format)
    source_pattern = r"<source>.*?</source>"
    source_matches = re.findall(source_pattern, content, re.DOTALL | re.IGNORECASE)
    citation_count += len(source_matches)

    # Pattern 2: Count standalone URLs with https:// (fallback for unstructured citations)
    # Only count if no structured sources found
    if citation_count == 0:
        url_pattern = r"https?://[^\s<>\"'\)]+(?:\.[^\s<>\"'\)]+)+"
        url_matches = re.findall(url_pattern, content)
        # Deduplicate URLs
        unique_urls = set(url_matches)
        citation_count = len(unique_urls)

    # Determine validation result
    is_valid = citation_count >= min_citations
    warning = None

    if not is_valid:
        warning = f"{persona_type} response has {citation_count} citation(s), minimum {min_citations} required"
        logger.warning(f"[CITATION_COMPLIANCE] {warning}")

    return CitationValidationResult(
        citation_count=citation_count,
        min_required=min_citations,
        is_valid=is_valid,
        warning=warning,
    )


def get_facilitator_parse_stats() -> dict[str, int]:
    """Get current facilitator action parse statistics.

    Returns:
        Dictionary with keys: success, fallback, invalid_action
        - success: Actions extracted from XML tags
        - fallback: Actions extracted via keyword matching
        - invalid_action: Actions forced to 'continue' due to invalid value
    """
    return _facilitator_parse_stats.copy()


def reset_facilitator_parse_stats() -> None:
    """Reset facilitator parse statistics (for testing)."""
    global _facilitator_parse_stats
    _facilitator_parse_stats = {"success": 0, "fallback": 0, "invalid_action": 0}
