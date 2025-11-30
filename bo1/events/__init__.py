"""Event schemas and utilities for Board of One.

Provides typed Pydantic models for all SSE events, ensuring consistent
event structure between backend and frontend.
"""

from bo1.events.schemas import (
    BaseEvent,
    ContributionEvent,
    ContributionSummary,
    ConvergenceEvent,
    DecompositionCompleteEvent,
    ErrorEvent,
    MetaSynthesisCompleteEvent,
    PersonaSchema,
    PersonaSelectedEvent,
    PersonaSelectionCompleteEvent,
    RoundStartedEvent,
    SessionStartedEvent,
    SubProblemCompleteEvent,
    SubProblemStartedEvent,
    SynthesisCompleteEvent,
    VotingCompleteEvent,
    VotingStartedEvent,
)

__all__ = [
    "BaseEvent",
    "SessionStartedEvent",
    "DecompositionCompleteEvent",
    "PersonaSchema",
    "PersonaSelectedEvent",
    "PersonaSelectionCompleteEvent",
    "SubProblemStartedEvent",
    "RoundStartedEvent",
    "ContributionEvent",
    "ContributionSummary",
    "ConvergenceEvent",
    "VotingStartedEvent",
    "VotingCompleteEvent",
    "SynthesisCompleteEvent",
    "SubProblemCompleteEvent",
    "MetaSynthesisCompleteEvent",
    "ErrorEvent",
]
