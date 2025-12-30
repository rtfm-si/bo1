"""Tests for OpenAPI security scheme documentation.

Verifies that security requirements appear correctly in the generated OpenAPI spec:
- Protected routes have sessionAuth requirement
- Mutating routes have both sessionAuth and csrfToken requirements
- Public routes have no security requirement
"""

import json
from pathlib import Path

import pytest


@pytest.fixture(scope="module")
def openapi_spec():
    """Load the generated OpenAPI spec from the repo root."""
    spec_path = Path(__file__).parent.parent.parent / "openapi.json"
    if not spec_path.exists():
        pytest.skip("openapi.json not found - run 'make openapi-export' first")
    with open(spec_path) as f:
        return json.load(f)


class TestSecuritySchemes:
    """Test security scheme definitions in OpenAPI spec."""

    def test_session_auth_scheme_defined(self, openapi_spec):
        """Verify sessionAuth security scheme is defined."""
        schemes = openapi_spec.get("components", {}).get("securitySchemes", {})
        assert "sessionAuth" in schemes
        assert schemes["sessionAuth"]["type"] == "apiKey"
        assert schemes["sessionAuth"]["in"] == "cookie"
        assert schemes["sessionAuth"]["name"] == "sAccessToken"

    def test_csrf_token_scheme_defined(self, openapi_spec):
        """Verify csrfToken security scheme is defined."""
        schemes = openapi_spec.get("components", {}).get("securitySchemes", {})
        assert "csrfToken" in schemes
        assert schemes["csrfToken"]["type"] == "apiKey"
        assert schemes["csrfToken"]["in"] == "header"
        assert schemes["csrfToken"]["name"] == "X-CSRF-Token"


class TestSessionEndpointsSecurity:
    """Test security requirements on session endpoints."""

    def test_post_sessions_requires_auth_and_csrf(self, openapi_spec):
        """POST /sessions requires sessionAuth + csrfToken."""
        security = (
            openapi_spec["paths"].get("/api/v1/sessions", {}).get("post", {}).get("security", [])
        )
        scheme_names = [list(s.keys())[0] for s in security]
        assert "sessionAuth" in scheme_names
        assert "csrfToken" in scheme_names

    def test_get_sessions_requires_auth_only(self, openapi_spec):
        """GET /sessions requires sessionAuth only."""
        security = (
            openapi_spec["paths"].get("/api/v1/sessions", {}).get("get", {}).get("security", [])
        )
        scheme_names = [list(s.keys())[0] for s in security]
        assert "sessionAuth" in scheme_names
        # GET endpoints should not require CSRF
        assert "csrfToken" not in scheme_names


class TestActionsEndpointsSecurity:
    """Test security requirements on action endpoints."""

    def test_get_actions_requires_auth_only(self, openapi_spec):
        """GET /actions requires sessionAuth only."""
        security = (
            openapi_spec["paths"].get("/api/v1/actions", {}).get("get", {}).get("security", [])
        )
        scheme_names = [list(s.keys())[0] for s in security]
        assert "sessionAuth" in scheme_names
        assert "csrfToken" not in scheme_names

    def test_post_action_start_requires_auth_and_csrf(self, openapi_spec):
        """POST /actions/{id}/start requires sessionAuth + csrfToken."""
        security = (
            openapi_spec["paths"]
            .get("/api/v1/actions/{action_id}/start", {})
            .get("post", {})
            .get("security", [])
        )
        scheme_names = [list(s.keys())[0] for s in security]
        assert "sessionAuth" in scheme_names
        assert "csrfToken" in scheme_names

    def test_delete_action_requires_auth_and_csrf(self, openapi_spec):
        """DELETE /actions/{id} requires sessionAuth + csrfToken."""
        security = (
            openapi_spec["paths"]
            .get("/api/v1/actions/{action_id}", {})
            .get("delete", {})
            .get("security", [])
        )
        scheme_names = [list(s.keys())[0] for s in security]
        assert "sessionAuth" in scheme_names
        assert "csrfToken" in scheme_names


class TestProjectsEndpointsSecurity:
    """Test security requirements on project endpoints."""

    def test_get_projects_requires_auth_only(self, openapi_spec):
        """GET /projects requires sessionAuth only."""
        security = (
            openapi_spec["paths"].get("/api/v1/projects", {}).get("get", {}).get("security", [])
        )
        scheme_names = [list(s.keys())[0] for s in security]
        assert "sessionAuth" in scheme_names
        assert "csrfToken" not in scheme_names

    def test_post_projects_requires_auth_and_csrf(self, openapi_spec):
        """POST /projects requires sessionAuth + csrfToken."""
        security = (
            openapi_spec["paths"].get("/api/v1/projects", {}).get("post", {}).get("security", [])
        )
        scheme_names = [list(s.keys())[0] for s in security]
        assert "sessionAuth" in scheme_names
        assert "csrfToken" in scheme_names

    def test_patch_project_requires_auth_and_csrf(self, openapi_spec):
        """PATCH /projects/{id} requires sessionAuth + csrfToken."""
        security = (
            openapi_spec["paths"]
            .get("/api/v1/projects/{project_id}", {})
            .get("patch", {})
            .get("security", [])
        )
        scheme_names = [list(s.keys())[0] for s in security]
        assert "sessionAuth" in scheme_names
        assert "csrfToken" in scheme_names

    def test_delete_project_requires_auth_and_csrf(self, openapi_spec):
        """DELETE /projects/{id} requires sessionAuth + csrfToken."""
        security = (
            openapi_spec["paths"]
            .get("/api/v1/projects/{project_id}", {})
            .get("delete", {})
            .get("security", [])
        )
        scheme_names = [list(s.keys())[0] for s in security]
        assert "sessionAuth" in scheme_names
        assert "csrfToken" in scheme_names


class TestStreamingEndpointsSecurity:
    """Test security requirements on streaming endpoints."""

    def test_get_stream_requires_auth(self, openapi_spec):
        """GET /sessions/{id}/stream requires sessionAuth."""
        security = (
            openapi_spec["paths"]
            .get("/api/v1/sessions/{session_id}/stream", {})
            .get("get", {})
            .get("security", [])
        )
        scheme_names = [list(s.keys())[0] for s in security]
        assert "sessionAuth" in scheme_names

    def test_get_events_requires_auth(self, openapi_spec):
        """GET /sessions/{id}/events requires sessionAuth."""
        security = (
            openapi_spec["paths"]
            .get("/api/v1/sessions/{session_id}/events", {})
            .get("get", {})
            .get("security", [])
        )
        scheme_names = [list(s.keys())[0] for s in security]
        assert "sessionAuth" in scheme_names
