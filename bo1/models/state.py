"""State management models for Board of One.

Defines the deliberation state and contribution tracking.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .persona import PersonaProfile
from .problem import Problem, SubProblem


class DeliberationPhase(str, Enum):
    """Current phase of the deliberation process."""

    INTAKE = "intake"  # Problem intake and clarification
    DECOMPOSITION = "decomposition"  # Breaking down the problem
    SELECTION = "selection"  # Selecting expert personas
    INITIAL_ROUND = "initial_round"  # First round of contributions
    DISCUSSION = "discussion"  # Multi-round debate
    VOTING = "voting"  # Voting phase
    SYNTHESIS = "synthesis"  # Final synthesis
    COMPLETE = "complete"  # Deliberation finished


class ContributionType(str, Enum):
    """Type of contribution in the deliberation."""

    INITIAL = "initial"  # Initial contribution (first round)
    RESPONSE = "response"  # Response to previous contributions
    MODERATOR = "moderator"  # Moderator intervention
    FACILITATOR = "facilitator"  # Facilitator guidance
    RESEARCH = "research"  # Research findings
    VOTE = "vote"  # Vote contribution


class ContributionMessage(BaseModel):
    """A single contribution from a persona in the deliberation."""

    persona_code: str = Field(..., description="Code of the persona making this contribution")
    persona_name: str = Field(..., description="Display name of the persona")
    content: str = Field(..., description="The contribution content (markdown)")
    thinking: str | None = Field(
        None, description="Internal thinking process (from <thinking> tag)"
    )
    contribution_type: ContributionType = Field(
        default=ContributionType.INITIAL, description="Type of contribution"
    )
    round_number: int = Field(..., ge=0, description="Round number (0 = initial)")
    timestamp: datetime = Field(default_factory=datetime.now, description="When this was created")
    token_count: int | None = Field(None, description="Token count for this contribution")
    cost: float | None = Field(None, description="Cost in USD for generating this contribution")

    @property
    def tokens_used(self) -> int:
        """Alias for token_count for backward compatibility."""
        return self.token_count or 0

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "persona_code": "growth_hacker",
                    "persona_name": "Zara",
                    "content": "I recommend focusing on product-led growth...",
                    "thinking": "Let me analyze the growth channels...",
                    "contribution_type": "initial",
                    "round_number": 0,
                    "timestamp": "2024-01-15T10:30:00",
                    "token_count": 250,
                    "cost": 0.0015,
                }
            ]
        }
    )


class DeliberationMetrics(BaseModel):
    """Metrics tracking for the deliberation."""

    total_cost: float = Field(default=0.0, description="Total cost in USD")
    total_tokens: int = Field(default=0, description="Total tokens used")
    cache_hits: int = Field(default=0, description="Number of cache hits")
    cache_creation_tokens: int = Field(default=0, description="Tokens used to create cache")
    cache_read_tokens: int = Field(default=0, description="Tokens read from cache")
    phase_costs: dict[str, float] = Field(
        default_factory=dict,
        description="Cost breakdown by phase (e.g., problem_decomposition, persona_selection)",
    )
    convergence_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Semantic convergence score (0-1)"
    )
    novelty_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Average novelty of recent contributions (0-1)"
    )
    conflict_score: float | None = Field(
        default=None, ge=0.0, le=1.0, description="Level of disagreement (0-1)"
    )
    drift_events: int = Field(default=0, description="Number of problem drift events detected")


class DeliberationState(BaseModel):
    """Complete state of a deliberation session."""

    session_id: str = Field(..., description="Unique session identifier (UUID)")
    problem: Problem = Field(..., description="The problem being deliberated")
    current_sub_problem: SubProblem | None = Field(
        None, description="The current sub-problem being discussed"
    )
    selected_personas: list[PersonaProfile] = Field(
        default_factory=list, description="Personas selected for this deliberation"
    )
    contributions: list[ContributionMessage] = Field(
        default_factory=list, description="All contributions in chronological order"
    )
    round_summaries: list[str] = Field(
        default_factory=list,
        description="Summaries of previous rounds (for hierarchical context)",
    )
    phase: DeliberationPhase = Field(default=DeliberationPhase.INTAKE, description="Current phase")
    current_round: int = Field(default=0, ge=0, description="Current round number")
    max_rounds: int = Field(default=10, ge=1, le=15, description="Maximum rounds allowed")
    metrics: DeliberationMetrics = Field(
        default_factory=lambda: DeliberationMetrics(), description="Deliberation metrics"
    )
    votes: list[Any] = Field(default_factory=list, description="Votes from personas (Vote objects)")
    synthesis: str | None = Field(default=None, description="Final synthesis report")
    created_at: datetime = Field(default_factory=datetime.now, description="When session started")
    updated_at: datetime = Field(default_factory=datetime.now, description="Last update time")
    completed_at: datetime | None = Field(default=None, description="When session completed")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata (user_id, tags, etc.)"
    )

    # Context fields (Day 14)
    business_context: dict[str, Any] | None = Field(
        default=None, description="Business context collected from user"
    )
    internal_context: dict[str, str] | None = Field(
        default=None, description="Answers to internal information gap questions"
    )
    research_context: list[dict[str, Any]] | None = Field(
        default=None, description="External research results"
    )

    @property
    def sub_problem(self) -> SubProblem | None:
        """Alias for current_sub_problem for backward compatibility."""
        return self.current_sub_problem

    @property
    def total_cost(self) -> float:
        """Total cost from metrics."""
        return self.metrics.total_cost

    @property
    def total_tokens(self) -> int:
        """Total tokens from metrics."""
        return self.metrics.total_tokens

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "session_id": "550e8400-e29b-41d4-a716-446655440000",
                    "problem": {
                        "title": "Pricing Strategy",
                        "description": "Determine optimal pricing",
                        "context": "SaaS startup",
                        "constraints": [],
                        "sub_problems": [],
                    },
                    "current_sub_problem": None,
                    "selected_personas": [],
                    "contributions": [],
                    "round_summaries": [],
                    "phase": "intake",
                    "current_round": 0,
                    "max_rounds": 10,
                    "metrics": {
                        "total_cost": 0.0,
                        "total_tokens": 0,
                        "cache_hits": 0,
                        "cache_creation_tokens": 0,
                        "cache_read_tokens": 0,
                        "convergence_score": None,
                        "novelty_score": None,
                        "conflict_score": None,
                        "drift_events": 0,
                    },
                    "votes": [],
                    "synthesis": None,
                    "created_at": "2024-01-15T10:00:00",
                    "updated_at": "2024-01-15T10:00:00",
                    "metadata": {},
                }
            ]
        }
    )

    def get_contributions_for_round(self, round_number: int) -> list[ContributionMessage]:
        """Get all contributions for a specific round.

        Args:
            round_number: The round number to filter by

        Returns:
            List of contributions from that round
        """
        return [c for c in self.contributions if c.round_number == round_number]

    def get_latest_contributions(self, count: int = 5) -> list[ContributionMessage]:
        """Get the N most recent contributions.

        Args:
            count: Number of contributions to retrieve

        Returns:
            List of most recent contributions
        """
        return self.contributions[-count:]

    def add_contribution(self, contribution: ContributionMessage) -> None:
        """Add a contribution and update timestamp.

        Args:
            contribution: The contribution to add
        """
        self.contributions.append(contribution)
        self.updated_at = datetime.now()

    def advance_round(self) -> None:
        """Advance to the next round."""
        self.current_round += 1
        self.updated_at = datetime.now()

    def update_metrics(
        self,
        cost: float | None = None,
        tokens: int | None = None,
        cache_hit: bool = False,
        cache_creation: int | None = None,
        cache_read: int | None = None,
    ) -> None:
        """Update deliberation metrics.

        Args:
            cost: Cost to add (USD)
            tokens: Tokens to add
            cache_hit: Whether this was a cache hit
            cache_creation: Cache creation tokens
            cache_read: Cache read tokens
        """
        if cost is not None:
            self.metrics.total_cost += cost
        if tokens is not None:
            self.metrics.total_tokens += tokens
        if cache_hit:
            self.metrics.cache_hits += 1
        if cache_creation is not None:
            self.metrics.cache_creation_tokens += cache_creation
        if cache_read is not None:
            self.metrics.cache_read_tokens += cache_read
        self.updated_at = datetime.now()

    def format_discussion_history(
        self,
        include_round_numbers: bool = True,
        include_thinking: bool = False,
        max_contributions: int | None = None,
        separator: str = "---",
    ) -> str:
        r"""Format discussion history for prompt inclusion.

        Args:
            include_round_numbers: Include round number in header
            include_thinking: Include <thinking> tags in output
            max_contributions: Limit to last N contributions (None = all)
            separator: Separator line between contributions

        Returns:
            Formatted discussion history string

        Examples:
            >>> state.format_discussion_history()
            "--- Maria (Round 1) ---\nI think we should...\n\n--- ..."

            >>> state.format_discussion_history(max_contributions=5)
            # Only last 5 contributions
        """
        import re

        contributions = self.contributions
        if max_contributions:
            contributions = contributions[-max_contributions:]

        lines = []
        for msg in contributions:
            # Header
            if include_round_numbers:
                header = f"{separator} {msg.persona_name} (Round {msg.round_number}) {separator}"
            else:
                header = f"{separator} {msg.persona_name} {separator}"
            lines.append(header)

            # Content
            content = msg.content
            if not include_thinking and msg.thinking:
                # Strip <thinking> tags if requested
                content = re.sub(
                    r"<thinking>.*?</thinking>", "", content, flags=re.DOTALL | re.IGNORECASE
                )
                content = content.strip()

            lines.append(content)
            lines.append("")  # Blank line between contributions

        return "\n".join(lines)

    @property
    def participant_list(self) -> str:
        """Comma-separated list of participant names.

        Returns:
            String like "Maria, Zara, Tariq"

        Examples:
            >>> state.participant_list
            'Maria, Zara, Tariq'
        """
        return ", ".join([p.display_name for p in self.selected_personas])
