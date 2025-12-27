"""Tests for research sharing consent service."""

import pytest

from bo1.state.database import db_session


@pytest.fixture
def clean_consent_table():
    """Clean research_sharing_consent table before/after tests."""
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM research_sharing_consent WHERE user_id LIKE 'test_%'")
            conn.commit()
    yield
    with db_session() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM research_sharing_consent WHERE user_id LIKE 'test_%'")
            conn.commit()


class TestResearchSharingConsent:
    """Tests for research sharing consent management."""

    def test_get_consent_status_no_consent(self, clean_consent_table):
        """User without consent record returns False."""
        from backend.services.research_sharing import get_consent_status

        status = get_consent_status("test_user_no_consent")
        assert status.consented is False
        assert status.consented_at is None
        assert status.revoked_at is None

    def test_give_consent(self, clean_consent_table):
        """User can opt in to research sharing."""
        from backend.services.research_sharing import get_consent_status, give_consent

        user_id = "test_user_give_consent"
        status = give_consent(user_id)

        assert status.consented is True
        assert status.consented_at is not None
        assert status.revoked_at is None

        # Verify persistence
        status2 = get_consent_status(user_id)
        assert status2.consented is True

    def test_revoke_consent(self, clean_consent_table):
        """User can opt out of research sharing."""
        from backend.services.research_sharing import (
            get_consent_status,
            give_consent,
            revoke_consent,
        )

        user_id = "test_user_revoke"
        give_consent(user_id)

        status = revoke_consent(user_id)

        assert status.consented is False
        assert status.consented_at is not None
        assert status.revoked_at is not None

        # Verify persistence
        status2 = get_consent_status(user_id)
        assert status2.consented is False

    def test_re_consent_after_revoke(self, clean_consent_table):
        """User can re-consent after revoking."""
        from backend.services.research_sharing import (
            give_consent,
            revoke_consent,
        )

        user_id = "test_user_reconsent"
        give_consent(user_id)
        revoke_consent(user_id)
        status = give_consent(user_id)

        assert status.consented is True
        assert status.revoked_at is None

    def test_is_consented_helper(self, clean_consent_table):
        """is_consented returns correct boolean."""
        from backend.services.research_sharing import give_consent, is_consented, revoke_consent

        user_id = "test_user_is_consented"

        assert is_consented(user_id) is False
        give_consent(user_id)
        assert is_consented(user_id) is True
        revoke_consent(user_id)
        assert is_consented(user_id) is False
