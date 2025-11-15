"""Response parsing utilities for LLM responses.

Consolidates parsing logic for structured responses from different agents.
"""

import logging
from typing import Any

from bo1.models.recommendations import Recommendation
from bo1.models.state import DeliberationState
from bo1.utils.extraction import ResponseExtractor
from bo1.utils.vote_parsing import (
    parse_conditions,
    parse_confidence_level,
)
from bo1.utils.xml_parsing import extract_xml_tag

logger = logging.getLogger(__name__)


class ResponseParser:
    """Utilities for parsing structured data from LLM responses.

    Consolidates common parsing patterns used across facilitator, voting,
    and deliberation agents.
    """

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
        thinking = None
        contribution = content

        # Extract <thinking> if present
        if "<thinking>" in content and "</thinking>" in content:
            thinking_start = content.index("<thinking>") + len("<thinking>")
            thinking_end = content.index("</thinking>")
            thinking = content[thinking_start:thinking_end].strip()

        # Extract <contribution> if present
        if "<contribution>" in content and "</contribution>" in content:
            contrib_start = content.index("<contribution>") + len("<contribution>")
            contrib_end = content.index("</contribution>")
            contribution = content[contrib_start:contrib_end].strip()
        else:
            # If no explicit <contribution> tag, use the part after </thinking>
            if "</thinking>" in content:
                contribution = content.split("</thinking>", 1)[1].strip()

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
    def parse_facilitator_decision(content: str, state: DeliberationState) -> dict[str, Any]:
        """Parse facilitator decision from response content.

        This extracts the decision action and associated parameters.

        Args:
            content: LLM response content
            state: Deliberation state for persona lookups

        Returns:
            Dictionary with parsed decision details:
            - action: str ("continue", "vote", "research", "moderator")
            - reasoning: str
            - next_speaker: str | None (for "continue")
            - speaker_prompt: str | None (for "continue")
            - moderator_type: str | None (for "moderator")
            - moderator_focus: str | None (for "moderator")
            - research_query: str | None (for "research")
            - phase_summary: str | None (for "vote")
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
        }

        if action == "continue":
            next_speaker = ResponseExtractor.extract_persona_code(
                content, state.selected_personas, logger=logger
            )
            # Fallback: If extraction failed, pick first available persona
            if not next_speaker and state.selected_personas:
                next_speaker = state.selected_personas[0].code
                logger.warning(
                    f"Failed to extract next_speaker from facilitator response, "
                    f"defaulting to {next_speaker}"
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

        return result
