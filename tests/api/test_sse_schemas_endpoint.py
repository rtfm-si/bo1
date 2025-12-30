"""Tests for SSE schemas endpoint and OpenAPI integration."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    """Create test app with SSE schemas endpoint."""
    from backend.api.main import app as main_app

    return main_app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestSSESchemasEndpoint:
    """Test /api/v1/sse/schemas endpoint."""

    def test_sse_schemas_returns_200(self, client):
        """Test endpoint returns 200 OK."""
        response = client.get("/api/v1/sse/schemas")
        assert response.status_code == 200

    def test_sse_schemas_returns_all_events(self, client):
        """Test endpoint returns all expected event types."""
        response = client.get("/api/v1/sse/schemas")
        data = response.json()

        expected_events = {
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
        }

        assert set(data["event_types"]) == expected_events
        assert data["count"] == 14

    def test_sse_schemas_has_schema_dict(self, client):
        """Test endpoint returns schemas dict with JSON Schema for each event."""
        response = client.get("/api/v1/sse/schemas")
        data = response.json()

        schemas = data["schemas"]
        assert isinstance(schemas, dict)
        assert len(schemas) == 14

        # Each schema should be a valid JSON Schema
        for _event_type, schema in schemas.items():
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema

    def test_sse_schemas_has_lifecycle_order(self, client):
        """Test endpoint returns correct lifecycle order."""
        response = client.get("/api/v1/sse/schemas")
        data = response.json()

        lifecycle = data["lifecycle"]
        assert lifecycle[0] == "session_started"
        assert lifecycle[-1] == "error"
        assert "contribution" in lifecycle
        assert "meta_synthesis_complete" in lifecycle

    def test_sse_schemas_no_auth_required(self, client):
        """Test endpoint is public (no auth required)."""
        # Should work without any auth headers/cookies
        response = client.get("/api/v1/sse/schemas")
        assert response.status_code == 200


class TestOpenAPISSESchemas:
    """Test SSE schemas in OpenAPI spec."""

    def test_openapi_includes_sse_event_schemas(self, app):
        """Test OpenAPI spec includes SSEEvent_* schemas."""
        # Reset cached schema to ensure fresh generation
        app.openapi_schema = None

        schema = app.openapi()
        components = schema.get("components", {})
        schemas = components.get("schemas", {})

        # Check SSE event schemas are present with prefix
        sse_schemas = [k for k in schemas.keys() if k.startswith("SSEEvent_")]
        assert len(sse_schemas) == 14

        expected_sse_schemas = {
            "SSEEvent_session_started",
            "SSEEvent_decomposition_complete",
            "SSEEvent_persona_selected",
            "SSEEvent_persona_selection_complete",
            "SSEEvent_subproblem_started",
            "SSEEvent_subproblem_complete",
            "SSEEvent_round_started",
            "SSEEvent_contribution",
            "SSEEvent_convergence",
            "SSEEvent_voting_started",
            "SSEEvent_voting_complete",
            "SSEEvent_synthesis_complete",
            "SSEEvent_meta_synthesis_complete",
            "SSEEvent_error",
        }
        assert set(sse_schemas) == expected_sse_schemas

    def test_openapi_sse_schemas_are_valid(self, app):
        """Test SSE schemas in OpenAPI are valid JSON Schema."""
        app.openapi_schema = None

        schema = app.openapi()
        schemas = schema["components"]["schemas"]

        for name, sse_schema in schemas.items():
            if not name.startswith("SSEEvent_"):
                continue

            assert "type" in sse_schema
            assert sse_schema["type"] == "object"
            # Should have properties
            assert "properties" in sse_schema

    def test_openapi_contribution_schema_has_fields(self, app):
        """Test SSEEvent_contribution has expected fields."""
        app.openapi_schema = None

        schema = app.openapi()
        contrib = schema["components"]["schemas"]["SSEEvent_contribution"]

        props = contrib.get("properties", {})
        assert "persona_code" in props
        assert "persona_name" in props
        assert "content" in props
        assert "round" in props
        assert "contribution_type" in props
