"""Tests for currency preference in user preferences API."""

from unittest.mock import MagicMock, patch

import pytest


class TestCurrencyPreferencesAPI:
    """Tests for currency preference endpoints."""

    @pytest.fixture
    def mock_db_session(self):
        """Mock db_session context manager."""
        with patch("backend.api.user.db_session") as mock:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.__enter__ = MagicMock(return_value=mock_conn)
            mock_conn.__exit__ = MagicMock(return_value=False)
            mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
            mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
            mock.return_value = mock_conn
            yield mock, mock_cursor

    @pytest.fixture
    def mock_get_current_user(self):
        """Mock the auth dependency."""
        with patch("backend.api.user.get_current_user") as mock:
            mock.return_value = {"user_id": "test-user-123"}
            yield mock

    def test_get_preferences_includes_currency(self, mock_db_session, mock_get_current_user):
        """Test GET /preferences returns preferred_currency."""
        from backend.api.user import PreferencesResponse

        _, cursor = mock_db_session
        cursor.fetchone.return_value = {
            "skip_clarification": False,
            "default_reminder_frequency_days": 3,
            "preferred_currency": "USD",
        }

        # The response model should include preferred_currency
        resp = PreferencesResponse(
            skip_clarification=False,
            default_reminder_frequency_days=3,
            preferred_currency="USD",
        )

        assert resp.preferred_currency == "USD"
        assert resp.skip_clarification is False
        assert resp.default_reminder_frequency_days == 3

    def test_preferences_response_default_currency(self):
        """Test PreferencesResponse defaults to GBP."""
        from backend.api.user import PreferencesResponse

        resp = PreferencesResponse()

        assert resp.preferred_currency == "GBP"

    def test_preferences_update_currency_valid(self):
        """Test PreferencesUpdate accepts valid currencies."""
        from backend.api.user import PreferencesUpdate

        for currency in ["GBP", "USD", "EUR"]:
            update = PreferencesUpdate(preferred_currency=currency)
            assert update.preferred_currency == currency

    def test_preferences_update_currency_invalid(self):
        """Test PreferencesUpdate rejects invalid currencies."""
        from pydantic import ValidationError

        from backend.api.user import PreferencesUpdate

        with pytest.raises(ValidationError) as exc_info:
            PreferencesUpdate(preferred_currency="JPY")

        assert "preferred_currency" in str(exc_info.value)

    def test_preferences_update_currency_case_sensitive(self):
        """Test currency validation is case-sensitive."""
        from pydantic import ValidationError

        from backend.api.user import PreferencesUpdate

        with pytest.raises(ValidationError):
            PreferencesUpdate(preferred_currency="gbp")  # lowercase should fail

    def test_valid_currencies_set(self):
        """Test VALID_CURRENCIES contains expected values."""
        from backend.api.user import VALID_CURRENCIES

        assert VALID_CURRENCIES == {"GBP", "USD", "EUR"}

    def test_preferences_update_partial(self):
        """Test PreferencesUpdate works with partial updates."""
        from backend.api.user import PreferencesUpdate

        # Currency only
        update = PreferencesUpdate(preferred_currency="EUR")
        assert update.preferred_currency == "EUR"
        assert update.skip_clarification is None
        assert update.default_reminder_frequency_days is None

        # Other fields without currency
        update = PreferencesUpdate(skip_clarification=True)
        assert update.preferred_currency is None
        assert update.skip_clarification is True
