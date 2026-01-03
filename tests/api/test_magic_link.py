"""Tests for magic link email service and rate limiting."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest


class TestMagicLinkRateLimiting:
    """Tests for magic link rate limiting functionality."""

    def test_rate_limit_check_no_previous_request(self) -> None:
        """Test that first request is not rate limited."""
        from backend.api.supertokens_config import _check_magic_link_rate_limit

        with patch("bo1.state.database.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = None  # No user found
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_db.return_value.__enter__.return_value = mock_conn

            is_limited, remaining = _check_magic_link_rate_limit("test@example.com")

            assert is_limited is False
            assert remaining == 0

    def test_rate_limit_check_null_timestamp(self) -> None:
        """Test that user with null timestamp is not rate limited."""
        from backend.api.supertokens_config import _check_magic_link_rate_limit

        with patch("bo1.state.database.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchone.return_value = (None,)  # User exists but no timestamp
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_db.return_value.__enter__.return_value = mock_conn

            is_limited, remaining = _check_magic_link_rate_limit("test@example.com")

            assert is_limited is False
            assert remaining == 0

    def test_rate_limit_check_recent_request_blocked(self) -> None:
        """Test that request within cooldown is rate limited."""
        from backend.api.supertokens_config import (
            MAGIC_LINK_RATE_LIMIT_SECONDS,
            _check_magic_link_rate_limit,
        )

        with patch("bo1.state.database.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            # Last request was 30 seconds ago
            recent_time = datetime.now(UTC) - timedelta(seconds=30)
            mock_cursor.fetchone.return_value = (recent_time,)
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_db.return_value.__enter__.return_value = mock_conn

            is_limited, remaining = _check_magic_link_rate_limit("test@example.com")

            assert is_limited is True
            assert remaining > 0
            assert remaining <= MAGIC_LINK_RATE_LIMIT_SECONDS - 30

    def test_rate_limit_check_old_request_allowed(self) -> None:
        """Test that request after cooldown is allowed."""
        from backend.api.supertokens_config import (
            MAGIC_LINK_RATE_LIMIT_SECONDS,
            _check_magic_link_rate_limit,
        )

        with patch("bo1.state.database.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            # Last request was 90 seconds ago (after 60s cooldown)
            old_time = datetime.now(UTC) - timedelta(seconds=MAGIC_LINK_RATE_LIMIT_SECONDS + 30)
            mock_cursor.fetchone.return_value = (old_time,)
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_db.return_value.__enter__.return_value = mock_conn

            is_limited, remaining = _check_magic_link_rate_limit("test@example.com")

            assert is_limited is False
            assert remaining == 0

    def test_rate_limit_check_db_error_allows_request(self) -> None:
        """Test that database error allows request (fail open)."""
        from backend.api.supertokens_config import _check_magic_link_rate_limit

        with patch("bo1.state.database.db_session") as mock_db:
            mock_db.return_value.__enter__.side_effect = Exception("DB error")

            is_limited, remaining = _check_magic_link_rate_limit("test@example.com")

            # Should allow request on error
            assert is_limited is False
            assert remaining == 0

    def test_rate_limit_check_naive_datetime_handled(self) -> None:
        """Test that naive datetime from DB is handled correctly."""
        from backend.api.supertokens_config import _check_magic_link_rate_limit

        with patch("bo1.state.database.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            # Naive datetime (no timezone) - 30 seconds ago
            naive_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=30)
            mock_cursor.fetchone.return_value = (naive_time,)
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_db.return_value.__enter__.return_value = mock_conn

            is_limited, remaining = _check_magic_link_rate_limit("test@example.com")

            assert is_limited is True
            assert remaining > 0


class TestMagicLinkEmailService:
    """Tests for MagicLinkEmailService.send_email()."""

    @pytest.mark.asyncio
    async def test_send_email_success(self) -> None:
        """Test successful magic link email send."""
        from backend.api.supertokens_config import MagicLinkEmailService

        service = MagicLinkEmailService()

        mock_template_vars = MagicMock()
        mock_template_vars.email = "test@example.com"
        mock_template_vars.url_with_link_code = "https://example.com/auth/verify?code=abc123"
        mock_template_vars.code_life_time = 900000  # 15 minutes in ms

        with (
            patch("backend.api.supertokens_config._check_magic_link_rate_limit") as mock_rate_limit,
            patch("backend.api.supertokens_config.send_email") as mock_send,
            patch("backend.api.supertokens_config._update_magic_link_timestamp") as mock_update,
            patch("backend.api.supertokens_config.render_magic_link_email") as mock_render,
        ):
            mock_rate_limit.return_value = (False, 0)  # Not rate limited
            mock_render.return_value = ("<html>...</html>", "text version")

            await service.send_email(mock_template_vars, {})

            mock_rate_limit.assert_called_once_with("test@example.com")
            mock_send.assert_called_once()
            mock_update.assert_called_once_with("test@example.com")

    @pytest.mark.asyncio
    async def test_send_email_rate_limited(self) -> None:
        """Test that rate limited request raises ValueError."""
        from backend.api.supertokens_config import MagicLinkEmailService

        service = MagicLinkEmailService()

        mock_template_vars = MagicMock()
        mock_template_vars.email = "test@example.com"
        mock_template_vars.url_with_link_code = "https://example.com/auth/verify?code=abc123"
        mock_template_vars.code_life_time = 900000

        with patch(
            "backend.api.supertokens_config._check_magic_link_rate_limit"
        ) as mock_rate_limit:
            mock_rate_limit.return_value = (True, 45)  # Rate limited, 45s remaining

            with pytest.raises(ValueError) as exc_info:
                await service.send_email(mock_template_vars, {})

            assert "45 seconds" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_email_missing_url_raises(self) -> None:
        """Test that missing magic link URL raises ValueError."""
        from backend.api.supertokens_config import MagicLinkEmailService

        service = MagicLinkEmailService()

        mock_template_vars = MagicMock()
        mock_template_vars.email = "test@example.com"
        mock_template_vars.url_with_link_code = None
        mock_template_vars.code_life_time = 900000

        with pytest.raises(ValueError) as exc_info:
            await service.send_email(mock_template_vars, {})

        assert "Magic link URL is required" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_send_email_failure_re_raises(self) -> None:
        """Test that email send failure is re-raised."""
        mock_template_vars = MagicMock()
        mock_template_vars.email = "test@example.com"
        mock_template_vars.url_with_link_code = "https://example.com/auth/verify?code=abc123"
        mock_template_vars.code_life_time = 900000

        with (
            patch("backend.api.supertokens_config._check_magic_link_rate_limit") as mock_rate_limit,
            patch("backend.api.supertokens_config.send_email") as mock_send,
            patch("backend.api.supertokens_config.render_magic_link_email") as mock_render,
            patch("backend.api.supertokens_config.log_error"),
            patch("backend.api.supertokens_config.ErrorCode"),
        ):
            mock_rate_limit.return_value = (False, 0)
            mock_render.return_value = ("<html>...</html>", "text version")
            mock_send.side_effect = Exception("Resend API error")

            from backend.api.supertokens_config import MagicLinkEmailService

            service = MagicLinkEmailService()

            with pytest.raises(Exception) as exc_info:
                await service.send_email(mock_template_vars, {})

            assert "Resend API error" in str(exc_info.value)


class TestUpdateMagicLinkTimestamp:
    """Tests for _update_magic_link_timestamp helper."""

    def test_update_timestamp_success(self) -> None:
        """Test successful timestamp update."""
        from backend.api.supertokens_config import _update_magic_link_timestamp

        with patch("bo1.state.database.db_session") as mock_db:
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
            mock_db.return_value.__enter__.return_value = mock_conn

            _update_magic_link_timestamp("test@example.com")

            mock_cursor.execute.assert_called_once()
            call_args = mock_cursor.execute.call_args
            assert "UPDATE users" in call_args[0][0]
            assert "last_magic_link_at" in call_args[0][0]

    def test_update_timestamp_db_error_logged(self) -> None:
        """Test that database error is logged but doesn't raise."""
        from backend.api.supertokens_config import _update_magic_link_timestamp

        with (
            patch("bo1.state.database.db_session") as mock_db,
            patch("backend.api.supertokens_config.logger") as mock_logger,
        ):
            mock_db.return_value.__enter__.side_effect = Exception("DB error")

            # Should not raise
            _update_magic_link_timestamp("test@example.com")

            mock_logger.warning.assert_called_once()
            assert "Failed to update magic link timestamp" in str(mock_logger.warning.call_args)
