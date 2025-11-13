"""Unit tests for FacilitatorAgent sub-methods."""

import pytest

from bo1.agents.facilitator import FacilitatorAgent, FacilitatorDecision
from bo1.models.persona import PersonaProfile
from bo1.models.problem import Problem
from bo1.models.state import ContributionMessage, DeliberationState


@pytest.fixture
def sample_state():
    """Create a sample deliberation state for testing."""
    # Create minimal PersonaProfile objects for testing
    personas = [
        PersonaProfile(
            id="1",
            code="MARIA",
            name="Maria Chen",
            archetype="Tech Entrepreneur",
            category="tech",
            description="Serial startup founder",
            emoji="👩‍💻",
            color_hex="#FF5733",
            traits={
                "creative": 0.8,
                "analytical": 0.7,
                "optimistic": 0.9,
                "risk_averse": 0.3,
                "detail_oriented": 0.6,
            },
            default_weight=1.0,
            temperature=0.7,
            system_prompt="You are Maria, a tech entrepreneur.",
            response_style="analytical",
            display_name="Maria",
            domain_expertise=["startups", "technology"],
        ),
        PersonaProfile(
            id="2",
            code="ZARA",
            name="Zara Okafor",
            archetype="Financial Analyst",
            category="finance",
            description="Investment banking expert",
            emoji="💼",
            color_hex="#3357FF",
            traits={
                "creative": 0.5,
                "analytical": 0.9,
                "optimistic": 0.6,
                "risk_averse": 0.7,
                "detail_oriented": 0.9,
            },
            default_weight=1.0,
            temperature=0.7,
            system_prompt="You are Zara, a financial analyst.",
            response_style="analytical",
            display_name="Zara",
            domain_expertise=["finance", "investing"],
        ),
        PersonaProfile(
            id="3",
            code="TARIQ",
            name="Tariq Hassan",
            archetype="Operations Expert",
            category="ops",
            description="Scaling operations specialist",
            emoji="⚙️",
            color_hex="#33FF57",
            traits={
                "creative": 0.6,
                "analytical": 0.8,
                "optimistic": 0.7,
                "risk_averse": 0.5,
                "detail_oriented": 0.8,
            },
            default_weight=1.0,
            temperature=0.7,
            system_prompt="You are Tariq, an operations expert.",
            response_style="analytical",
            display_name="Tariq",
            domain_expertise=["operations", "scaling"],
        ),
    ]

    problem = Problem(
        title="European Expansion Decision",
        description="Evaluating investment in European market expansion",
        statement="Should we invest $500k in expanding to Europe?",
        context="SaaS startup",
        constraints=[],
        sub_problems=[],
    )

    return DeliberationState(
        session_id="test-session",
        problem=problem,
        selected_personas=personas,
        contributions=[
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria Chen",
                content="Initial thoughts on market expansion",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara Okafor",
                content="Financial analysis of the opportunity",
                round_number=1,
            ),
        ],
    )


class TestShouldTriggerModerator:
    """Tests for _should_trigger_moderator method."""

    def test_no_trigger_with_few_contributions(self, sample_state):
        """Should not trigger moderator with fewer than 4 contributions."""
        facilitator = FacilitatorAgent()
        sample_state.contributions = sample_state.contributions[:2]
        result = facilitator._should_trigger_moderator(sample_state, round_number=1)
        assert result is None

    def test_premature_consensus_in_early_rounds(self, sample_state):
        """Should trigger contrarian moderator for premature consensus in early rounds."""
        facilitator = FacilitatorAgent()
        # Add contributions with heavy agreement
        sample_state.contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="I agree completely yes this is exactly correct aligned",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara",
                content="Yes indeed I agree exactly the same conclusion",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="TARIQ",
                persona_name="Tariq",
                content="Correct yes I agree completely aligned thinking",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="Indeed yes exactly aligned with everyone",
                round_number=2,
            ),
        ]

        result = facilitator._should_trigger_moderator(sample_state, round_number=3)
        assert result is not None
        assert result["type"] == "contrarian"
        assert "premature" in result["reason"].lower() or "early" in result["reason"].lower()

    def test_unverified_claims_in_middle_rounds(self, sample_state):
        """Should trigger skeptic moderator for unverified claims in middle rounds."""
        facilitator = FacilitatorAgent()
        sample_state.contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content=(
                    "We must do this immediately. This will definitely work. "
                    "It should be our priority and will certainly succeed"
                ),
                round_number=5,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara",
                content="This will always generate returns and never fail",
                round_number=5,
            ),
            ContributionMessage(
                persona_code="TARIQ",
                persona_name="Tariq",
                content="General comment",
                round_number=5,
            ),
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="Another comment",
                round_number=6,
            ),
        ]

        result = facilitator._should_trigger_moderator(sample_state, round_number=6)
        assert result is not None
        assert result["type"] == "skeptic"
        assert "claim" in result["reason"].lower() or "evidence" in result["reason"].lower()

    def test_negativity_spiral_in_late_rounds(self, sample_state):
        """Should trigger optimist moderator for negativity spiral in late rounds."""
        facilitator = FacilitatorAgent()
        sample_state.contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content=(
                    "This won't work it's impossible and can't succeed. "
                    "Too risky with problems that will fail"
                ),
                round_number=8,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara",
                content="Multiple issues that can't be resolved will fail",
                round_number=8,
            ),
            ContributionMessage(
                persona_code="TARIQ",
                persona_name="Tariq",
                content="Too many problems and issues here",
                round_number=8,
            ),
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="More problems that won't work",
                round_number=9,
            ),
        ]

        result = facilitator._should_trigger_moderator(sample_state, round_number=9)
        assert result is not None
        assert result["type"] == "optimist"
        assert (
            "negative" in result["reason"].lower()
            or "problem" in result["reason"].lower()
            or "solution" in result["reason"].lower()
        )

    def test_circular_arguments_any_round(self, sample_state):
        """Should trigger contrarian moderator for circular arguments in any round."""
        facilitator = FacilitatorAgent()
        sample_state.contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="market analysis shows market trends indicate market opportunity",
                round_number=5,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara",
                content="market analysis reveals market patterns suggest market growth",
                round_number=5,
            ),
            ContributionMessage(
                persona_code="TARIQ",
                persona_name="Tariq",
                content="market trends show market analysis indicates market potential",
                round_number=5,
            ),
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="market opportunity shows market analysis suggests market trends",
                round_number=6,
            ),
        ]

        result = facilitator._should_trigger_moderator(sample_state, round_number=6)
        assert result is not None
        assert result["type"] == "contrarian"
        assert "circular" in result["reason"].lower() or "repeat" in result["reason"].lower()


class TestCheckResearchNeeded:
    """Tests for _check_research_needed method."""

    def test_no_research_needed_clear_discussion(self, sample_state):
        """Should return None when discussion is clear."""
        facilitator = FacilitatorAgent()
        sample_state.contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="Based on available evidence we can proceed",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara",
                content="The data supports this conclusion",
                round_number=1,
            ),
        ]

        result = facilitator._check_research_needed(sample_state)
        assert result is None

    def test_detects_information_gaps(self, sample_state):
        """Should detect when information gaps exist."""
        facilitator = FacilitatorAgent()
        sample_state.contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria",
                content="What is the current market size for this product?",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara",
                content="General discussion",
                round_number=1,
            ),
        ]

        result = facilitator._check_research_needed(sample_state)
        assert result is not None
        assert "query" in result
        assert "reason" in result


class TestExtractNextSpeaker:
    """Tests for _extract_next_speaker method."""

    def test_extracts_valid_persona_code(self, sample_state):
        """Should extract valid persona code from content."""
        facilitator = FacilitatorAgent()
        content = "Let's hear from MARIA next about the technical considerations."

        result = facilitator._extract_next_speaker(content, sample_state)
        assert result == "MARIA"

    def test_extracts_persona_with_underscores(self, sample_state):
        """Should handle persona codes with underscores."""
        facilitator = FacilitatorAgent()
        # Add persona with underscore
        sample_state.selected_personas.append(
            PersonaProfile(
                id="4",
                code="JOHN_DOE",
                name="John Doe",
                archetype="Expert",
                category="strategy",
                description="Test expert",
                emoji="🎯",
                color_hex="#FF33AA",
                traits={
                    "creative": 0.7,
                    "analytical": 0.8,
                    "optimistic": 0.7,
                    "risk_averse": 0.5,
                    "detail_oriented": 0.7,
                },
                default_weight=1.0,
                temperature=0.7,
                system_prompt="You are John, an expert.",
                response_style="analytical",
                display_name="John Doe",
                domain_expertise=["strategy"],
            )
        )
        content = "john doe should speak next about the analysis"

        result = facilitator._extract_next_speaker(content, sample_state)
        assert result == "JOHN_DOE"

    def test_defaults_to_first_persona_if_unclear(self, sample_state):
        """Should default to first persona if no clear match."""
        facilitator = FacilitatorAgent()
        content = "Let's continue the discussion with someone else."

        result = facilitator._extract_next_speaker(content, sample_state)
        assert result == sample_state.selected_personas[0].code

    def test_handles_empty_persona_list(self, sample_state):
        """Should handle empty persona list gracefully."""
        facilitator = FacilitatorAgent()
        sample_state.selected_personas = []
        content = "Continue discussion"

        result = facilitator._extract_next_speaker(content, sample_state)
        assert result is None


class TestExtractSpeakerPrompt:
    """Tests for _extract_speaker_prompt method."""

    def test_extracts_prompt_after_marker(self):
        """Should extract text after 'Prompt:' marker."""
        facilitator = FacilitatorAgent()
        content = "Next steps:\n\nPrompt: What are your thoughts on the financial implications?"

        result = facilitator._extract_speaker_prompt(content)
        assert result is not None
        assert "financial implications" in result.lower()

    def test_extracts_focus_after_marker(self):
        """Should extract text after 'Focus:' marker."""
        facilitator = FacilitatorAgent()
        content = "Focus: Consider the operational challenges"

        result = facilitator._extract_speaker_prompt(content)
        assert result is not None
        assert "operational" in result.lower()

    def test_extracts_question_after_marker(self):
        """Should extract text after 'Question:' marker."""
        facilitator = FacilitatorAgent()
        content = "Question: How will this impact our existing infrastructure?"

        result = facilitator._extract_speaker_prompt(content)
        assert result is not None
        assert "infrastructure" in result.lower()

    def test_returns_none_without_markers(self):
        """Should return None when no markers found."""
        facilitator = FacilitatorAgent()
        content = "Continue the discussion about various topics"

        result = facilitator._extract_speaker_prompt(content)
        assert result is None

    def test_limits_extraction_length(self):
        """Should limit extraction to reasonable length."""
        facilitator = FacilitatorAgent()
        long_text = "x" * 500
        content = f"Prompt: {long_text}"

        result = facilitator._extract_speaker_prompt(content)
        assert result is not None
        assert len(result) < 350  # Should be truncated at newline or around 300 chars


class TestExtractModeratorType:
    """Tests for _extract_moderator_type method."""

    def test_extracts_contrarian(self):
        """Should extract contrarian moderator type."""
        facilitator = FacilitatorAgent()
        content = "We need a contrarian moderator to challenge the consensus"

        result = facilitator._extract_moderator_type(content)
        assert result == "contrarian"

    def test_extracts_skeptic(self):
        """Should extract skeptic moderator type."""
        facilitator = FacilitatorAgent()
        content = "Bring in the skeptic to verify these claims"

        result = facilitator._extract_moderator_type(content)
        assert result == "skeptic"

    def test_extracts_optimist(self):
        """Should extract optimist moderator type."""
        facilitator = FacilitatorAgent()
        content = "Need an optimist moderator to find solutions"

        result = facilitator._extract_moderator_type(content)
        assert result == "optimist"

    def test_defaults_to_contrarian(self):
        """Should default to contrarian if no type found."""
        facilitator = FacilitatorAgent()
        content = "No moderator type mentioned here"

        result = facilitator._extract_moderator_type(content)
        assert result == "contrarian"


class TestExtractModeratorFocus:
    """Tests for _extract_moderator_focus method."""

    def test_extracts_focus_marker(self):
        """Should extract text after 'Focus:' marker."""
        facilitator = FacilitatorAgent()
        content = "Focus: Challenge the assumptions about market size"

        result = facilitator._extract_moderator_focus(content)
        assert result is not None
        assert "assumptions" in result.lower()

    def test_extracts_address_marker(self):
        """Should extract text after 'Address:' marker."""
        facilitator = FacilitatorAgent()
        content = "Address: The unverified claims about ROI"

        result = facilitator._extract_moderator_focus(content)
        assert result is not None
        assert "unverified" in result.lower()

    def test_extracts_challenge_marker(self):
        """Should extract text after 'Challenge:' marker."""
        facilitator = FacilitatorAgent()
        content = "Challenge: The negative thinking patterns"

        result = facilitator._extract_moderator_focus(content)
        assert result is not None
        assert "negative" in result.lower()

    def test_returns_none_without_markers(self):
        """Should return None when no markers found."""
        facilitator = FacilitatorAgent()
        content = "General moderator discussion without specific markers"

        result = facilitator._extract_moderator_focus(content)
        assert result is None


class TestExtractResearchQuery:
    """Tests for _extract_research_query method."""

    def test_extracts_query_marker(self):
        """Should extract text after 'Query:' marker."""
        facilitator = FacilitatorAgent()
        content = "Query: What is the average customer acquisition cost in Europe?"

        result = facilitator._extract_research_query(content)
        assert result is not None
        assert "customer acquisition" in result.lower()

    def test_extracts_question_marker(self):
        """Should extract text after 'Question:' marker."""
        facilitator = FacilitatorAgent()
        content = "Question: What are the regulatory requirements for expansion?"

        result = facilitator._extract_research_query(content)
        assert result is not None
        assert "regulatory" in result.lower()

    def test_returns_none_without_markers(self):
        """Should return None when no markers found."""
        facilitator = FacilitatorAgent()
        content = "Research needed but no specific query provided"

        result = facilitator._extract_research_query(content)
        assert result is None


class TestParseDecision:
    """Tests for _parse_decision method."""

    def test_parses_continue_action(self, sample_state):
        """Should parse 'continue' action correctly."""
        facilitator = FacilitatorAgent()
        content = """
        Option A: Continue Discussion
        <thinking>Discussion is productive and should continue</thinking>
        Next speaker: MARIA
        Prompt: What are your thoughts on the financial risks?
        """

        decision = facilitator._parse_decision(content, sample_state)
        assert decision.action == "continue"
        assert decision.next_speaker == "MARIA"
        assert decision.speaker_prompt is not None
        assert "financial" in decision.speaker_prompt.lower()

    def test_parses_vote_action(self, sample_state):
        """Should parse 'vote' action correctly."""
        facilitator = FacilitatorAgent()
        content = """
        Option B: Transition to Voting
        <thinking>Discussion has reached sufficient depth</thinking>
        """

        decision = facilitator._parse_decision(content, sample_state)
        assert decision.action == "vote"

    def test_parses_research_action(self, sample_state):
        """Should parse 'research' action correctly."""
        facilitator = FacilitatorAgent()
        content = """
        Option C: Research
        <thinking>We need market data</thinking>
        Query: What is the market size for SaaS in Europe?
        """

        decision = facilitator._parse_decision(content, sample_state)
        assert decision.action == "research"
        assert decision.research_query is not None

    def test_parses_moderator_action(self, sample_state):
        """Should parse 'moderator' action correctly."""
        facilitator = FacilitatorAgent()
        content = """
        Option D: Invoke Moderator
        <thinking>Need contrarian perspective</thinking>
        Moderator type: contrarian
        Focus: Challenge the assumptions
        """

        decision = facilitator._parse_decision(content, sample_state)
        assert decision.action == "moderator"
        assert decision.moderator_type == "contrarian"

    def test_defaults_to_continue_if_unclear(self, sample_state):
        """Should default to 'continue' if action unclear."""
        facilitator = FacilitatorAgent()
        content = "Some unclear response without clear action markers"

        decision = facilitator._parse_decision(content, sample_state)
        assert decision.action == "continue"


class TestFormatDiscussionHistory:
    """Tests for _format_discussion_history method."""

    def test_formats_empty_history(self, sample_state):
        """Should handle empty contribution list."""
        facilitator = FacilitatorAgent()
        sample_state.contributions = []

        result = facilitator._format_discussion_history(sample_state)
        assert "no contributions" in result.lower() or "initial" in result.lower()

    def test_formats_with_contributions(self, sample_state):
        """Should format contributions into readable history."""
        facilitator = FacilitatorAgent()
        sample_state.contributions = [
            ContributionMessage(
                persona_code="MARIA",
                persona_name="Maria Chen",
                content="First contribution about tech",
                round_number=1,
            ),
            ContributionMessage(
                persona_code="ZARA",
                persona_name="Zara Okafor",
                content="Second contribution about finance",
                round_number=1,
            ),
        ]

        result = facilitator._format_discussion_history(sample_state)
        assert "Maria" in result or "MARIA" in result
        assert len(result) > 0


class TestGetPhaseObjectives:
    """Tests for _get_phase_objectives method."""

    def test_initial_phase_objectives(self):
        """Should return objectives for initial phase."""
        facilitator = FacilitatorAgent()
        result = facilitator._get_phase_objectives("initial", round_number=1, max_rounds=10)
        assert "initial" in result.lower()
        assert len(result) > 0

    def test_discussion_phase_objectives(self):
        """Should return objectives for discussion phase."""
        facilitator = FacilitatorAgent()
        result = facilitator._get_phase_objectives("discussion", round_number=5, max_rounds=10)
        assert "discussion" in result.lower()
        assert "5" in result  # Should mention current round
        assert "10" in result  # Should mention max rounds

    def test_handles_unknown_phase(self):
        """Should handle unknown phase gracefully."""
        facilitator = FacilitatorAgent()
        result = facilitator._get_phase_objectives("unknown_phase", round_number=1, max_rounds=10)
        assert len(result) > 0  # Should return something


class TestLogDecisionDetails:
    """Tests for _log_decision_details method."""

    def test_logs_without_error(self, sample_state):
        """Should log decision details without raising errors."""
        facilitator = FacilitatorAgent()
        decision = FacilitatorDecision(
            action="continue",
            reasoning="Discussion is productive",
            next_speaker="MARIA",
            speaker_prompt="What are your thoughts?",
        )

        # Should not raise any exceptions
        facilitator._log_decision_details(decision, sample_state)

    def test_logs_moderator_decision(self, sample_state):
        """Should log moderator decision details."""
        facilitator = FacilitatorAgent()
        decision = FacilitatorDecision(
            action="moderator",
            reasoning="Need fresh perspective",
            moderator_type="contrarian",
            moderator_focus="Challenge assumptions",
        )

        # Should not raise any exceptions
        facilitator._log_decision_details(decision, sample_state)
