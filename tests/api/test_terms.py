"""Unit tests for Terms & Conditions API endpoints.

Tests:
- GET /api/v1/terms/current - public endpoint, returns active T&C
- GET /api/v1/user/terms-consent - authenticated, returns consent status
- POST /api/v1/user/terms-consent - authenticated, records consent
"""

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from backend.api.terms import (
    ConsentRecordResponse,
    ConsentRequest,
    ConsentStatusResponse,
    TermsVersionResponse,
)


class TestTermsVersionResponse:
    """Tests for TermsVersionResponse model."""

    def test_valid_response(self):
        """Valid response data should pass validation."""
        response = TermsVersionResponse(
            id=str(uuid4()),
            version="1.0",
            content="# Terms\n\nSample content.",
            published_at="2025-12-26T00:00:00Z",
            is_active=True,
        )
        assert response.version == "1.0"
        assert response.is_active is True


class TestConsentStatusResponse:
    """Tests for ConsentStatusResponse model."""

    def test_consented_user(self):
        """Response for user who has consented."""
        response = ConsentStatusResponse(
            has_consented=True,
            current_version="1.0",
            consented_version="1.0",
            consented_at="2025-12-26T10:00:00Z",
        )
        assert response.has_consented is True
        assert response.consented_version == "1.0"

    def test_non_consented_user(self):
        """Response for user who has not consented."""
        response = ConsentStatusResponse(
            has_consented=False,
            current_version="1.0",
            consented_version=None,
            consented_at=None,
        )
        assert response.has_consented is False
        assert response.consented_version is None


class TestConsentRequest:
    """Tests for ConsentRequest model."""

    def test_valid_request(self):
        """Valid request data should pass validation."""
        version_id = str(uuid4())
        request = ConsentRequest(terms_version_id=version_id)
        assert request.terms_version_id == version_id


class TestConsentRecordResponse:
    """Tests for ConsentRecordResponse model."""

    def test_valid_response(self):
        """Valid response data should pass validation."""
        response = ConsentRecordResponse(
            id=str(uuid4()),
            terms_version_id=str(uuid4()),
            consented_at="2025-12-26T10:00:00Z",
            message="Consent recorded successfully",
        )
        assert response.message == "Consent recorded successfully"


class TestGetCurrentTermsEndpoint:
    """Tests for GET /api/v1/terms/current endpoint."""

    @pytest.fixture
    def mock_terms_version(self):
        """Sample T&C version."""
        return {
            "id": uuid4(),
            "version": "1.0",
            "content": "# Terms\n\nSample terms content.",
            "published_at": datetime.now(UTC),
            "is_active": True,
            "created_at": datetime.now(UTC),
        }

    @pytest.mark.asyncio
    async def test_returns_active_version(self, mock_terms_version):
        """Endpoint should return active T&C version."""
        from backend.api.terms import get_current_terms

        with patch(
            "backend.api.terms.terms_repository.get_active_version",
            return_value=mock_terms_version,
        ):
            response = await get_current_terms()

        assert response.version == "1.0"
        assert response.is_active is True

    @pytest.mark.asyncio
    async def test_returns_404_when_no_active_version(self):
        """Endpoint should return 404 when no active T&C version."""
        from fastapi import HTTPException

        from backend.api.terms import get_current_terms

        with patch(
            "backend.api.terms.terms_repository.get_active_version",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_terms()

            assert exc_info.value.status_code == 404


class TestGetConsentStatusEndpoint:
    """Tests for GET /api/v1/user/terms-consent endpoint."""

    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        return {"user_id": "user_123", "email": "test@example.com"}

    @pytest.fixture
    def mock_active_version(self):
        """Mock active T&C version."""
        return {
            "id": uuid4(),
            "version": "1.0",
            "content": "Terms...",
            "published_at": datetime.now(UTC),
            "is_active": True,
        }

    @pytest.fixture
    def mock_consent(self):
        """Mock consent record."""
        return {
            "id": uuid4(),
            "user_id": "user_123",
            "terms_version_id": uuid4(),
            "consented_at": datetime.now(UTC),
            "ip_address": "192.168.1.1",
            "terms_version": "1.0",
            "terms_published_at": datetime.now(UTC),
        }

    @pytest.mark.asyncio
    async def test_returns_consent_status_when_consented(
        self, mock_user, mock_active_version, mock_consent
    ):
        """Endpoint should return consent status for consented user."""
        from backend.api.terms import get_consent_status

        with (
            patch(
                "backend.api.terms.terms_repository.get_active_version",
                return_value=mock_active_version,
            ),
            patch(
                "backend.api.terms.terms_repository.has_user_consented_to_current",
                return_value=True,
            ),
            patch(
                "backend.api.terms.terms_repository.get_user_latest_consent",
                return_value=mock_consent,
            ),
        ):
            response = await get_consent_status(user=mock_user)

        assert response.has_consented is True
        assert response.current_version == "1.0"

    @pytest.mark.asyncio
    async def test_returns_not_consented_status(self, mock_user, mock_active_version):
        """Endpoint should return not consented status for new user."""
        from backend.api.terms import get_consent_status

        with (
            patch(
                "backend.api.terms.terms_repository.get_active_version",
                return_value=mock_active_version,
            ),
            patch(
                "backend.api.terms.terms_repository.has_user_consented_to_current",
                return_value=False,
            ),
            patch(
                "backend.api.terms.terms_repository.get_user_latest_consent",
                return_value=None,
            ),
        ):
            response = await get_consent_status(user=mock_user)

        assert response.has_consented is False

    @pytest.mark.asyncio
    async def test_returns_consented_when_no_active_version(self, mock_user):
        """Endpoint should return consented=True when no active T&C."""
        from backend.api.terms import get_consent_status

        with patch(
            "backend.api.terms.terms_repository.get_active_version",
            return_value=None,
        ):
            response = await get_consent_status(user=mock_user)

        # No T&C to consent to, so consider consented
        assert response.has_consented is True
        assert response.current_version is None


class TestRecordConsentEndpoint:
    """Tests for POST /api/v1/user/terms-consent endpoint."""

    @pytest.fixture
    def mock_user(self):
        """Mock authenticated user."""
        return {"user_id": "user_123", "email": "test@example.com"}

    @pytest.fixture
    def mock_request(self):
        """Mock FastAPI request."""
        request = MagicMock()
        request.headers.get.return_value = "192.168.1.1"
        request.client.host = "192.168.1.1"
        return request

    @pytest.fixture
    def mock_version(self):
        """Mock T&C version."""
        return {
            "id": uuid4(),
            "version": "1.0",
            "content": "Terms...",
            "published_at": datetime.now(UTC),
            "is_active": True,
        }

    @pytest.fixture
    def mock_consent_record(self, mock_version):
        """Mock consent record returned by repository."""
        return {
            "id": uuid4(),
            "user_id": "user_123",
            "terms_version_id": mock_version["id"],
            "consented_at": datetime.now(UTC),
            "ip_address": "192.168.1.1",
        }

    @pytest.mark.asyncio
    async def test_records_consent_successfully(
        self, mock_user, mock_request, mock_version, mock_consent_record
    ):
        """Endpoint should record consent and return success."""
        from backend.api.terms import record_consent

        body = ConsentRequest(terms_version_id=str(mock_version["id"]))

        with (
            patch(
                "backend.api.terms.terms_repository.get_version_by_id",
                return_value=mock_version,
            ),
            patch(
                "backend.api.terms.terms_repository.create_consent",
                return_value=mock_consent_record,
            ),
        ):
            response = await record_consent(request=mock_request, body=body, user=mock_user)

        assert response.message == "Consent recorded successfully"

    @pytest.mark.asyncio
    async def test_returns_404_for_invalid_version(self, mock_user, mock_request):
        """Endpoint should return 404 for non-existent T&C version."""
        from fastapi import HTTPException

        from backend.api.terms import record_consent

        body = ConsentRequest(terms_version_id=str(uuid4()))

        with patch(
            "backend.api.terms.terms_repository.get_version_by_id",
            return_value=None,
        ):
            with pytest.raises(HTTPException) as exc_info:
                await record_consent(request=mock_request, body=body, user=mock_user)

            assert exc_info.value.status_code == 404


class TestAdminConsentAuditEndpoint:
    """Tests for GET /admin/terms/consents endpoint."""

    @pytest.fixture
    def mock_consent_records(self):
        """Mock consent records for admin audit."""
        return [
            {
                "user_id": "user_1",
                "email": "user1@example.com",
                "terms_version": "1.0",
                "consented_at": datetime.now(UTC),
                "ip_address": "192.168.1.1",
            },
            {
                "user_id": "user_2",
                "email": "user2@example.com",
                "terms_version": "1.0",
                "consented_at": datetime.now(UTC),
                "ip_address": "10.0.0.1",
            },
        ]

    @pytest.fixture
    def client(self):
        """Create test client with admin auth override and disabled rate limiter."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from backend.api.admin.terms import limiter, router
        from backend.api.middleware.admin import require_admin_any

        def mock_admin():
            return "admin_user"

        original_enabled = limiter.enabled
        limiter.enabled = False

        test_app = FastAPI()
        test_app.dependency_overrides[require_admin_any] = mock_admin
        # Router has prefix="/terms", endpoint is "/consents", so full path is /terms/consents
        test_app.include_router(router)

        yield TestClient(test_app, raise_server_exceptions=False)

        limiter.enabled = original_enabled

    def test_returns_consent_audit_records(self, client, mock_consent_records):
        """Endpoint returns paginated consent records."""
        with patch(
            "backend.api.admin.terms.terms_repository.get_all_consents",
            return_value=(mock_consent_records, 2),
        ):
            response = client.get("/terms/consents?period=all&limit=50&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["email"] == "user1@example.com"
        assert data["period"] == "all"

    def test_applies_time_period_filter(self, client, mock_consent_records):
        """Endpoint applies time period filter correctly."""
        with patch(
            "backend.api.admin.terms.terms_repository.get_all_consents",
            return_value=(mock_consent_records, 2),
        ) as mock_get:
            response = client.get("/terms/consents?period=day")

        assert response.status_code == 200
        # Verify time filter was applied
        call_kwargs = mock_get.call_args[1]
        assert "1 day" in call_kwargs["time_filter_sql"]

    def test_respects_pagination(self, client, mock_consent_records):
        """Endpoint respects limit and offset parameters."""
        with patch(
            "backend.api.admin.terms.terms_repository.get_all_consents",
            return_value=(mock_consent_records, 100),
        ) as mock_get:
            response = client.get("/terms/consents?limit=20&offset=40")

        assert response.status_code == 200
        data = response.json()
        # Verify pagination params passed to repository
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs["limit"] == 20
        assert call_kwargs["offset"] == 40
        assert data["has_more"] is True  # 40 + 20 < 100

    def test_handles_empty_results(self, client):
        """Endpoint handles empty results gracefully."""
        with patch(
            "backend.api.admin.terms.terms_repository.get_all_consents",
            return_value=([], 0),
        ):
            response = client.get("/terms/consents?period=hour")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 0
        assert len(data["items"]) == 0
        assert data["has_more"] is False


class TestAdminTermsVersionsEndpoints:
    """Tests for admin T&C version management endpoints."""

    @pytest.fixture
    def mock_version(self):
        """Mock T&C version."""
        return {
            "id": uuid4(),
            "version": "1.0",
            "content": "# Terms\n\nSample content.",
            "published_at": datetime.now(UTC),
            "is_active": True,
            "created_at": datetime.now(UTC),
        }

    @pytest.fixture
    def mock_draft_version(self):
        """Mock draft T&C version."""
        return {
            "id": uuid4(),
            "version": "1.1",
            "content": "# Draft Terms\n\nNew content.",
            "published_at": None,
            "is_active": False,
            "created_at": datetime.now(UTC),
        }

    @pytest.fixture
    def client(self):
        """Create test client with admin auth override and disabled rate limiter."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from backend.api.admin.terms import limiter, router
        from backend.api.middleware.admin import require_admin_any

        def mock_admin():
            return "admin_user"

        original_enabled = limiter.enabled
        limiter.enabled = False

        test_app = FastAPI()
        test_app.dependency_overrides[require_admin_any] = mock_admin
        test_app.include_router(router)

        yield TestClient(test_app, raise_server_exceptions=False)

        limiter.enabled = original_enabled

    def test_list_versions_returns_paginated(self, client, mock_version, mock_draft_version):
        """GET /terms/versions returns paginated version list."""
        versions = [mock_version, mock_draft_version]
        with patch(
            "backend.api.admin.terms.terms_repository.get_all_versions",
            return_value=(versions, 2),
        ):
            response = client.get("/terms/versions?limit=50&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 2
        assert data["items"][0]["version"] == "1.0"
        assert data["items"][1]["version"] == "1.1"

    def test_create_version_success(self, client, mock_draft_version):
        """POST /terms/versions creates new draft."""
        with patch(
            "backend.api.admin.terms.terms_repository.create_version",
            return_value=mock_draft_version,
        ):
            response = client.post(
                "/terms/versions",
                json={"version": "1.1", "content": "# Draft Terms\n\nNew content."},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["version"] == "1.1"
        assert data["is_active"] is False

    def test_create_version_duplicate_returns_409(self, client):
        """POST /terms/versions with duplicate version returns 409."""
        with patch(
            "backend.api.admin.terms.terms_repository.create_version",
            side_effect=Exception("unique constraint violation"),
        ):
            response = client.post(
                "/terms/versions",
                json={"version": "1.0", "content": "Content"},
            )

        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_update_version_success(self, client, mock_draft_version):
        """PUT /terms/versions/{id} updates draft content."""
        updated = {**mock_draft_version, "content": "Updated content"}
        with patch(
            "backend.api.admin.terms.terms_repository.update_version",
            return_value=updated,
        ):
            response = client.put(
                f"/terms/versions/{mock_draft_version['id']}",
                json={"content": "Updated content"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated content"

    def test_update_version_not_found_returns_404(self, client):
        """PUT /terms/versions/{id} returns 404 for missing/active version."""
        with patch(
            "backend.api.admin.terms.terms_repository.update_version",
            return_value=None,
        ):
            response = client.put(
                "/terms/versions/nonexistent-id",
                json={"content": "Updated"},
            )

        assert response.status_code == 404

    def test_publish_version_success(self, client, mock_draft_version):
        """POST /terms/versions/{id}/publish activates version."""
        published = {**mock_draft_version, "is_active": True, "published_at": datetime.now(UTC)}
        with patch(
            "backend.api.admin.terms.terms_repository.publish_version",
            return_value=published,
        ):
            response = client.post(f"/terms/versions/{mock_draft_version['id']}/publish")

        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
        assert data["published_at"] is not None

    def test_publish_version_not_found_returns_404(self, client):
        """POST /terms/versions/{id}/publish returns 404 for missing version."""
        with patch(
            "backend.api.admin.terms.terms_repository.publish_version",
            return_value=None,
        ):
            response = client.post("/terms/versions/nonexistent-id/publish")

        assert response.status_code == 404
