"""Tests for TermsRepository.

Validates:
- get_active_version() returns active T&C version
- get_version_by_id() returns specific version
- create_consent() records user consent
- get_user_latest_consent() returns most recent consent
- has_user_consented_to_current() checks consent status
"""

from datetime import UTC, datetime
from unittest.mock import patch
from uuid import uuid4

import pytest


class TestTermsRepository:
    """Test terms repository operations."""

    @pytest.fixture
    def sample_terms_version(self):
        """Sample T&C version data."""
        return {
            "id": str(uuid4()),
            "version": "1.0",
            "content": "# Terms\n\nSample terms content.",
            "published_at": datetime.now(UTC),
            "is_active": True,
            "created_at": datetime.now(UTC),
        }

    @pytest.fixture
    def sample_consent(self):
        """Sample consent record."""
        return {
            "id": str(uuid4()),
            "user_id": "user_123",
            "terms_version_id": str(uuid4()),
            "consented_at": datetime.now(UTC),
            "ip_address": "192.168.1.1",
            "terms_version": "1.0",
            "terms_published_at": datetime.now(UTC),
        }

    def test_get_active_version_returns_active(self, sample_terms_version):
        """Verify get_active_version returns the active T&C version."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with patch.object(repo, "_execute_one", return_value=sample_terms_version):
            version = repo.get_active_version()

        assert version is not None
        assert version["version"] == "1.0"
        assert version["is_active"] is True

    def test_get_active_version_returns_none_when_none_active(self):
        """Verify get_active_version returns None when no active version."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with patch.object(repo, "_execute_one", return_value=None):
            version = repo.get_active_version()

        assert version is None

    def test_get_version_by_id_returns_correct_version(self, sample_terms_version):
        """Verify get_version_by_id returns the matching version."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        version_id = sample_terms_version["id"]

        with patch.object(repo, "_execute_one", return_value=sample_terms_version) as mock_query:
            version = repo.get_version_by_id(version_id)

        assert version["id"] == version_id
        mock_query.assert_called_once()

    def test_get_version_by_id_returns_none_for_missing(self):
        """Verify get_version_by_id returns None for non-existent ID."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with patch.object(repo, "_execute_one", return_value=None):
            version = repo.get_version_by_id("nonexistent-id")

        assert version is None

    def test_create_consent_records_consent(self, sample_consent):
        """Verify create_consent inserts consent record."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with patch.object(repo, "_execute_returning", return_value=sample_consent) as mock_query:
            consent = repo.create_consent(
                user_id="user_123",
                version_id=sample_consent["terms_version_id"],
                ip_address="192.168.1.1",
            )

        assert consent["user_id"] == "user_123"
        assert consent["ip_address"] == "192.168.1.1"
        mock_query.assert_called_once()

    def test_create_consent_without_ip_address(self, sample_consent):
        """Verify create_consent works without IP address."""
        from bo1.state.repositories.terms_repository import TermsRepository

        consent_no_ip = {**sample_consent, "ip_address": None}

        repo = TermsRepository()
        with patch.object(repo, "_execute_returning", return_value=consent_no_ip):
            consent = repo.create_consent(
                user_id="user_123",
                version_id=sample_consent["terms_version_id"],
            )

        assert consent["ip_address"] is None

    def test_get_user_latest_consent_returns_most_recent(self, sample_consent):
        """Verify get_user_latest_consent returns most recent consent."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with patch.object(repo, "_execute_one", return_value=sample_consent):
            consent = repo.get_user_latest_consent("user_123")

        assert consent is not None
        assert consent["terms_version"] == "1.0"

    def test_get_user_latest_consent_returns_none_when_no_consent(self):
        """Verify get_user_latest_consent returns None when no consent exists."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with patch.object(repo, "_execute_one", return_value=None):
            consent = repo.get_user_latest_consent("user_with_no_consent")

        assert consent is None

    def test_has_user_consented_to_current_returns_true(self):
        """Verify has_user_consented_to_current returns True when consented."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with patch.object(repo, "_execute_one", return_value={"has_consented": True}):
            result = repo.has_user_consented_to_current("user_123")

        assert result is True

    def test_has_user_consented_to_current_returns_false(self):
        """Verify has_user_consented_to_current returns False when not consented."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with patch.object(repo, "_execute_one", return_value={"has_consented": False}):
            result = repo.has_user_consented_to_current("user_456")

        assert result is False

    def test_has_user_consented_to_current_handles_none(self):
        """Verify has_user_consented_to_current handles None response."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with patch.object(repo, "_execute_one", return_value=None):
            result = repo.has_user_consented_to_current("user_789")

        assert result is False

    def test_get_user_consents_returns_all_consents(self, sample_consent):
        """Verify get_user_consents returns all consent records for user."""
        from bo1.state.repositories.terms_repository import TermsRepository

        consents = [sample_consent, {**sample_consent, "terms_version": "2.0"}]

        repo = TermsRepository()
        with patch.object(repo, "_execute_query", return_value=consents):
            result = repo.get_user_consents("user_123")

        assert len(result) == 2
        assert result[0]["terms_version"] == "1.0"
        assert result[1]["terms_version"] == "2.0"

    def test_get_user_consents_returns_empty_list(self):
        """Verify get_user_consents returns empty list when no consents."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with patch.object(repo, "_execute_query", return_value=[]):
            result = repo.get_user_consents("user_with_no_consents")

        assert result == []

    def test_get_all_consents_returns_paginated_results(self, sample_consent):
        """Verify get_all_consents returns paginated records with total count."""
        from bo1.state.repositories.terms_repository import TermsRepository

        consents = [
            {**sample_consent, "email": "user1@example.com"},
            {**sample_consent, "email": "user2@example.com"},
        ]

        repo = TermsRepository()
        with (
            patch.object(repo, "_execute_one", return_value={"count": 100}),
            patch.object(repo, "_execute_query", return_value=consents),
        ):
            records, total = repo.get_all_consents(limit=50, offset=0)

        assert total == 100
        assert len(records) == 2
        assert records[0]["email"] == "user1@example.com"

    def test_get_all_consents_with_time_filter(self, sample_consent):
        """Verify get_all_consents applies time filter."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        time_filter = "tc.consented_at >= (CURRENT_TIMESTAMP AT TIME ZONE 'UTC') - INTERVAL '1 day'"

        with (
            patch.object(repo, "_execute_one", return_value={"count": 10}) as mock_count,
            patch.object(repo, "_execute_query", return_value=[sample_consent]) as mock_query,
        ):
            records, total = repo.get_all_consents(limit=20, offset=0, time_filter_sql=time_filter)

        # Verify time filter was passed to queries
        assert time_filter in mock_count.call_args[0][0]
        assert time_filter in mock_query.call_args[0][0]
        assert total == 10

    def test_get_all_consents_empty_results(self):
        """Verify get_all_consents handles empty results."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with (
            patch.object(repo, "_execute_one", return_value={"count": 0}),
            patch.object(repo, "_execute_query", return_value=[]),
        ):
            records, total = repo.get_all_consents(limit=50, offset=0)

        assert total == 0
        assert records == []

    def test_get_all_consents_pagination(self, sample_consent):
        """Verify get_all_consents respects limit and offset."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with (
            patch.object(repo, "_execute_one", return_value={"count": 100}),
            patch.object(repo, "_execute_query", return_value=[sample_consent]) as mock_query,
        ):
            repo.get_all_consents(limit=20, offset=40)

        # Verify limit and offset were passed
        call_args = mock_query.call_args[0]
        assert call_args[1] == (20, 40)  # (limit, offset)

    # =========================================================================
    # Version Management Tests
    # =========================================================================

    def test_get_all_versions_returns_paginated_results(self, sample_terms_version):
        """Verify get_all_versions returns paginated version records."""
        from bo1.state.repositories.terms_repository import TermsRepository

        versions = [sample_terms_version, {**sample_terms_version, "version": "1.1"}]

        repo = TermsRepository()
        with (
            patch.object(repo, "_execute_one", return_value={"count": 10}),
            patch.object(repo, "_execute_query", return_value=versions),
        ):
            records, total = repo.get_all_versions(limit=50, offset=0)

        assert total == 10
        assert len(records) == 2

    def test_get_all_versions_respects_pagination(self, sample_terms_version):
        """Verify get_all_versions passes limit and offset correctly."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with (
            patch.object(repo, "_execute_one", return_value={"count": 100}),
            patch.object(repo, "_execute_query", return_value=[sample_terms_version]) as mock_query,
        ):
            repo.get_all_versions(limit=20, offset=40)

        call_args = mock_query.call_args[0]
        assert call_args[1] == (20, 40)  # (limit, offset)

    def test_create_version_creates_draft(self, sample_terms_version):
        """Verify create_version creates a draft version."""
        from bo1.state.repositories.terms_repository import TermsRepository

        draft = {**sample_terms_version, "is_active": False, "published_at": None}

        repo = TermsRepository()
        with patch.object(repo, "_execute_returning", return_value=draft) as mock_exec:
            result = repo.create_version(version="1.1", content="New content")

        assert result["is_active"] is False
        assert result["published_at"] is None
        mock_exec.assert_called_once()

    def test_create_version_with_active_flag(self, sample_terms_version):
        """Verify create_version can create active version."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with patch.object(repo, "_execute_returning", return_value=sample_terms_version):
            result = repo.create_version(version="1.0", content="Content", is_active=True)

        assert result["is_active"] is True

    def test_update_version_updates_draft(self, sample_terms_version):
        """Verify update_version updates draft content."""
        from bo1.state.repositories.terms_repository import TermsRepository

        draft = {**sample_terms_version, "is_active": False, "content": "Updated"}

        repo = TermsRepository()
        with patch.object(repo, "_execute_returning", return_value=draft):
            result = repo.update_version(version_id=draft["id"], content="Updated")

        assert result["content"] == "Updated"

    def test_update_version_returns_none_for_active(self):
        """Verify update_version returns None for active versions."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with patch.object(repo, "_execute_returning", return_value=None):
            result = repo.update_version(version_id="some-id", content="Updated")

        assert result is None

    def test_publish_version_activates_version(self, sample_terms_version):
        """Verify publish_version sets is_active=True."""
        from bo1.state.repositories.terms_repository import TermsRepository

        published = {**sample_terms_version, "is_active": True}

        repo = TermsRepository()
        with patch.object(repo, "_execute_returning", return_value=published):
            result = repo.publish_version(version_id=sample_terms_version["id"])

        assert result["is_active"] is True

    def test_publish_version_returns_none_for_missing(self):
        """Verify publish_version returns None for non-existent version."""
        from bo1.state.repositories.terms_repository import TermsRepository

        repo = TermsRepository()
        with patch.object(repo, "_execute_returning", return_value=None):
            result = repo.publish_version(version_id="nonexistent")

        assert result is None
