"""Response parsing utilities for LLM responses.

Consolidates parsing logic for structured responses from different agents.
"""

import logging
import re
from typing import Any

from bo1.graph.state import DeliberationGraphState
from bo1.models.recommendations import Recommendation
from bo1.utils.confidence_parser import (
    parse_conditions,
    parse_confidence_level,
)
from bo1.utils.extraction import ResponseExtractor
from bo1.utils.xml_parsing import extract_xml_tag

logger = logging.getLogger(__name__)


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
    def parse_persona_response(content: str) -> tuple[str | None, str]:
        """Parse persona response to extract <thinking> and <contribution>.

        Args:
            content: Raw response content

        Returns:
            Tuple of (thinking, contribution)

        Example:
            >>> content = "<thinking>Analysis...</thinking><contribution>My view is...</contribution>"
            >>> thinking, contribution = ResponseParser.parse_persona_response(content)
            >>> thinking
            'Analysis...'
            >>> contribution
            'My view is...'
        """
        # Use extract_xml_tag utility instead of manual parsing
        thinking = extract_xml_tag(content, "thinking")

        # Extract <contribution> if present
        contribution = extract_xml_tag(content, "contribution")
        if not contribution:
            # If no explicit <contribution> tag, use the part after </thinking>
            if "</thinking>" in content:
                contribution = content.split("</thinking>", 1)[1].strip()
            else:
                # No tags at all - use full content
                contribution = content

        return thinking, contribution

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
            logger.warning(
                f"⚠️ FALLBACK: Could not extract <confidence> tag from {persona.name} recommendation. "
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
        content_lower = content.lower()

        # Detect action type
        if "option a" in content_lower or "continue discussion" in content_lower:
            action = "continue"
        elif (
            "option b" in content_lower or "transition" in content_lower or "vote" in content_lower
        ):
            action = "vote"
        elif "option c" in content_lower or "research" in content_lower:
            action = "research"
        elif "option d" in content_lower or "moderator" in content_lower:
            action = "moderator"
        elif "option e" in content_lower or "clarif" in content_lower:
            action = "clarify"
        else:
            # Default to continue if unclear
            logger.warning("Could not parse facilitator action clearly, defaulting to 'continue'")
            action = "continue"

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
        if word_count < 20:
            logger.warning(
                f"Malformed response from {persona_name}: Too short ({word_count} words)"
            )
            return False, f"Insufficient substance: only {word_count} words"

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
