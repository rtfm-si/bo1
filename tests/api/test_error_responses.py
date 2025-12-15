"""Tests for error response documentation.

Verifies:
- ErrorResponse model exists with required fields
- 401/404 responses are in endpoint decorator
"""


class TestErrorResponseModel:
    """Test ErrorResponse model structure."""

    def test_error_response_model_exists(self):
        """ErrorResponse model should exist."""
        from backend.api.models import ErrorResponse

        assert ErrorResponse is not None

    def test_error_response_has_detail_field(self):
        """ErrorResponse should have detail field."""
        from backend.api.models import ErrorResponse

        # Create instance to verify structure
        error = ErrorResponse(detail="Test error")
        assert error.detail == "Test error"

    def test_error_response_optional_fields(self):
        """ErrorResponse should support optional fields."""
        from backend.api.models import ErrorResponse

        error = ErrorResponse(
            detail="Test error",
            error_code="TEST_ERROR",
            session_id="bo1_abc123",
        )
        assert error.error_code == "TEST_ERROR"
        assert error.session_id == "bo1_abc123"


class TestActionsEndpointResponses:
    """Test actions endpoint has error responses in decorator."""

    def test_actions_list_has_401_response(self):
        """Actions list endpoint should have 401 in responses."""
        from backend.api.actions import router

        # Find the route
        for route in router.routes:
            if hasattr(route, "path") and route.path == "" and "GET" in route.methods:
                responses = getattr(route, "responses", {})
                assert 401 in responses or "401" in responses, "401 should be documented"
                break

    def test_action_detail_has_404_response(self):
        """Action detail endpoint should have 404 in responses."""
        from backend.api.actions import router

        for route in router.routes:
            if hasattr(route, "path") and route.path == "/{action_id}" and "GET" in route.methods:
                responses = getattr(route, "responses", {})
                assert 404 in responses or "404" in responses, "404 should be documented"
                break
