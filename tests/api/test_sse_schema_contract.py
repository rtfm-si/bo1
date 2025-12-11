"""Tests for SSE event schema contracts.

Validates that:
1. All event types have corresponding Pydantic schemas
2. JSON Schema exports are valid
3. Base event required fields are present
"""

import pytest

from bo1.events.schemas import (
    EVENT_SCHEMA_REGISTRY,
    BaseEvent,
    get_event_json_schemas,
    get_schema_for_event,
)


class TestSchemaRegistry:
    """Test the event schema registry."""

    def test_registry_not_empty(self) -> None:
        """Registry should contain event types."""
        assert len(EVENT_SCHEMA_REGISTRY) > 0

    def test_all_registry_values_are_base_event_subclasses(self) -> None:
        """All registered schemas should inherit from BaseEvent."""
        for event_type, model in EVENT_SCHEMA_REGISTRY.items():
            assert issubclass(model, BaseEvent), (
                f"{event_type} schema {model} is not a BaseEvent subclass"
            )

    def test_registry_keys_match_model_event_type(self) -> None:
        """Registry keys should match the model's event_type field default."""
        for event_type, model in EVENT_SCHEMA_REGISTRY.items():
            # Get the default value of event_type field
            field_info = model.model_fields.get("event_type")
            if field_info and field_info.default is not None:
                assert field_info.default == event_type, (
                    f"Registry key '{event_type}' doesn't match "
                    f"model default '{field_info.default}'"
                )


class TestJsonSchemaExport:
    """Test JSON Schema export functionality."""

    def test_get_event_json_schemas_returns_dict(self) -> None:
        """Should return a dictionary."""
        schemas = get_event_json_schemas()
        assert isinstance(schemas, dict)

    def test_get_event_json_schemas_matches_registry(self) -> None:
        """Should have same keys as registry."""
        schemas = get_event_json_schemas()
        assert set(schemas.keys()) == set(EVENT_SCHEMA_REGISTRY.keys())

    def test_each_schema_has_properties(self) -> None:
        """Each schema should have a properties section."""
        schemas = get_event_json_schemas()
        for event_type, schema in schemas.items():
            assert "properties" in schema, f"{event_type} schema missing 'properties'"

    def test_each_schema_has_required_fields(self) -> None:
        """Each schema should define required fields."""
        schemas = get_event_json_schemas()
        for event_type, schema in schemas.items():
            # Pydantic includes 'required' if there are required fields
            props = schema.get("properties", {})
            # At minimum, event_type and session_id should be present
            assert "event_type" in props, f"{event_type} schema missing event_type property"
            assert "session_id" in props, f"{event_type} schema missing session_id property"

    def test_contribution_schema_has_expected_fields(self) -> None:
        """Contribution event should have persona and content fields."""
        schemas = get_event_json_schemas()
        contrib_schema = schemas.get("contribution", {})
        props = contrib_schema.get("properties", {})

        assert "persona_code" in props
        assert "persona_name" in props
        assert "content" in props
        assert "round" in props


class TestGetSchemaForEvent:
    """Test schema lookup by event type."""

    def test_returns_model_for_valid_event_type(self) -> None:
        """Should return model class for registered event types."""
        model = get_schema_for_event("contribution")
        assert model is not None
        assert issubclass(model, BaseEvent)

    def test_returns_none_for_unknown_event_type(self) -> None:
        """Should return None for unregistered event types."""
        model = get_schema_for_event("unknown_event_xyz")
        assert model is None


class TestBaseEventFields:
    """Test that base event fields are consistent."""

    def test_base_event_has_required_envelope_fields(self) -> None:
        """BaseEvent should define the envelope fields."""
        fields = BaseEvent.model_fields

        assert "event_type" in fields
        assert "session_id" in fields
        assert "timestamp" in fields

    def test_all_events_inherit_envelope_fields(self) -> None:
        """All registered events should have envelope fields."""
        envelope_fields = {"event_type", "session_id", "timestamp"}

        for event_type, model in EVENT_SCHEMA_REGISTRY.items():
            model_fields = set(model.model_fields.keys())
            missing = envelope_fields - model_fields
            assert not missing, f"{event_type} missing envelope fields: {missing}"


class TestKnownEventTypes:
    """Test that critical event types are registered."""

    @pytest.mark.parametrize(
        "event_type",
        [
            "session_started",
            "decomposition_complete",
            "persona_selected",
            "persona_selection_complete",
            "subproblem_started",
            "subproblem_complete",
            "round_started",
            "contribution",
            "convergence",
            "voting_started",
            "voting_complete",
            "synthesis_complete",
            "meta_synthesis_complete",
            "error",
        ],
    )
    def test_critical_event_type_registered(self, event_type: str) -> None:
        """Critical event types should be in the registry."""
        assert event_type in EVENT_SCHEMA_REGISTRY, (
            f"Critical event type '{event_type}' not in registry"
        )
