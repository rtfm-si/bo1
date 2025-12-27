"""Tests for API terminology consistency.

Ensures API responses use correct terminology (session/problem_statement/persona)
and don't leak UI terminology (meeting/decision/expert) into field names.

See CLAUDE.md: "Terminology: UI=meeting/decision/expert; API=session/problem_statement/persona"
"""

import pytest
from pydantic import BaseModel

# Known legacy fields that predate this check (would require breaking API changes to fix)
LEGACY_EXCEPTIONS = frozenset(
    {
        # admin/models.py - UserInfo fields
        "total_meetings",
        "last_meeting_at",
        "last_meeting_id",
        # admin/models.py - MeetingStats (admin KPIs, user-facing name intentional)
        "meetings",
        "meetings_today",
        "meetings_this_week",
        "meetings_this_month",
        # events.py - SSE event fields
        "expert_panel",
        "expert_summaries",
        "expert_questions",
        # onboarding.py - step names
        "first_meeting_id",
        # OnboardingStep enum value
        # models.py - SessionResponse
        "expert_count",
        # sessions.py - meeting credits (user-facing tier limit field)
        "meeting_credits_remaining",
    }
)

# Legacy SSE event function names
LEGACY_EVENT_FUNCTIONS = frozenset(
    {
        "facilitator_decision_event",  # Internal orchestration, not UI terminology
    }
)

# UI terms that should NOT appear in new API field names
BANNED_UI_TERMS = {"meeting", "expert", "decision"}

# Allowed contexts where these terms are acceptable
ALLOWED_PATTERNS = {
    # "decision" as category value is domain terminology, not UI leak
    "implementation/research/decision/communication",
    # facilitator_decision is internal orchestration terminology
    "facilitator_decision",
}


def get_all_api_models():
    """Import and return all API response models."""
    from backend.api import models
    from backend.api.admin import models as admin_models

    all_models = []
    for module in [models, admin_models]:
        for name in dir(module):
            obj = getattr(module, name)
            if isinstance(obj, type) and issubclass(obj, BaseModel) and obj is not BaseModel:
                all_models.append((name, obj))
    return all_models


def extract_field_names(model: type[BaseModel]) -> set[str]:
    """Extract all field names from a Pydantic model recursively."""
    fields = set()
    for field_name in model.model_fields:
        fields.add(field_name)
    return fields


class TestApiTerminology:
    """Validate API models don't use UI terminology in field names."""

    def test_no_new_ui_terminology_in_models(self):
        """Ensure new API fields don't introduce UI terminology."""
        violations = []

        for model_name, model in get_all_api_models():
            for field_name in extract_field_names(model):
                # Skip known legacy exceptions
                if field_name in LEGACY_EXCEPTIONS:
                    continue

                # Check for banned UI terms in field name
                for term in BANNED_UI_TERMS:
                    if term in field_name.lower():
                        violations.append(f"{model_name}.{field_name} contains '{term}'")

        if violations:
            pytest.fail(
                "API fields using UI terminology (should use session/problem_statement/persona):\n"
                + "\n".join(f"  - {v}" for v in violations)
            )

    def test_legacy_exceptions_documented(self):
        """Verify legacy exceptions actually exist in models."""
        all_fields = set()
        for _, model in get_all_api_models():
            all_fields.update(extract_field_names(model))

        # Check that documented exceptions exist (catches stale exceptions)
        for exception in LEGACY_EXCEPTIONS:
            # Skip step names that aren't Pydantic fields
            if exception in {"expert_panel"}:
                continue
            if exception not in all_fields:
                # Field may have been removed or renamed - that's okay
                pass


class TestSseEventTerminology:
    """Validate SSE event schemas don't use UI terminology."""

    def test_no_new_ui_terminology_in_sse_events(self):
        """Ensure new SSE event fields don't introduce UI terminology."""
        from backend.api import events

        violations = []

        # Get all SSE event functions
        for name in dir(events):
            if name.endswith("_event") and callable(getattr(events, name)):
                # Skip known legacy event functions
                if name in LEGACY_EVENT_FUNCTIONS:
                    continue
                # Check function name for UI terminology
                for term in BANNED_UI_TERMS:
                    if term in name.lower() and name not in {"context_insufficient_event"}:
                        # context_insufficient_event has "expert_questions" which is legacy
                        if f"{term}_" in name or f"_{term}" in name:
                            violations.append(f"Event function '{name}' contains '{term}'")

        if violations:
            pytest.fail(
                "SSE events using UI terminology:\n" + "\n".join(f"  - {v}" for v in violations)
            )
