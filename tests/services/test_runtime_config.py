"""Tests for runtime config service."""

from unittest.mock import MagicMock, patch

from backend.services.runtime_config import (
    ALLOWED_OVERRIDES,
    REDIS_KEY_PREFIX,
    clear_override,
    get_all_overrides,
    get_effective_value,
    get_override,
    set_override,
)


class TestAllowedOverrides:
    """Tests for ALLOWED_OVERRIDES whitelist."""

    def test_prompt_injection_in_whitelist(self) -> None:
        """prompt_injection_block_suspicious should be whitelisted."""
        assert "prompt_injection_block_suspicious" in ALLOWED_OVERRIDES

    def test_enable_llm_response_cache_in_whitelist(self) -> None:
        """enable_llm_response_cache should be whitelisted."""
        assert "enable_llm_response_cache" in ALLOWED_OVERRIDES
        assert ALLOWED_OVERRIDES["enable_llm_response_cache"] is bool

    def test_enable_prompt_cache_in_whitelist(self) -> None:
        """enable_prompt_cache should be whitelisted."""
        assert "enable_prompt_cache" in ALLOWED_OVERRIDES
        assert ALLOWED_OVERRIDES["enable_prompt_cache"] is bool

    def test_enable_sse_streaming_in_whitelist(self) -> None:
        """enable_sse_streaming should be whitelisted."""
        assert "enable_sse_streaming" in ALLOWED_OVERRIDES
        assert ALLOWED_OVERRIDES["enable_sse_streaming"] is bool

    def test_auto_generate_projects_in_whitelist(self) -> None:
        """auto_generate_projects should be whitelisted."""
        assert "auto_generate_projects" in ALLOWED_OVERRIDES
        assert ALLOWED_OVERRIDES["auto_generate_projects"] is bool

    def test_enable_context_collection_in_whitelist(self) -> None:
        """enable_context_collection should be whitelisted."""
        assert "enable_context_collection" in ALLOWED_OVERRIDES
        assert ALLOWED_OVERRIDES["enable_context_collection"] is bool

    def test_whitelist_types_are_valid(self) -> None:
        """All whitelisted keys should have valid type mappings."""
        for key, expected_type in ALLOWED_OVERRIDES.items():
            assert expected_type in (bool, str, int, float), f"Invalid type for {key}"

    def test_all_expected_keys_present(self) -> None:
        """Verify all expected config keys are whitelisted."""
        expected_keys = {
            "prompt_injection_block_suspicious",
            "enable_llm_response_cache",
            "enable_prompt_cache",
            "enable_sse_streaming",
            "auto_generate_projects",
            "enable_context_collection",
        }
        assert expected_keys == set(ALLOWED_OVERRIDES.keys())


class TestGetOverride:
    """Tests for get_override function."""

    @patch("backend.services.runtime_config._get_redis_client")
    def test_returns_none_for_non_whitelisted_key(self, mock_redis: MagicMock) -> None:
        """Non-whitelisted keys should return None."""
        result = get_override("not_allowed_key")
        assert result is None
        mock_redis.assert_not_called()

    @patch("backend.services.runtime_config._get_redis_client")
    def test_returns_none_when_redis_unavailable(self, mock_redis: MagicMock) -> None:
        """Should return None when Redis is unavailable."""
        mock_redis.return_value = None
        result = get_override("prompt_injection_block_suspicious")
        assert result is None

    @patch("backend.services.runtime_config._get_redis_client")
    def test_returns_none_when_not_set(self, mock_redis: MagicMock) -> None:
        """Should return None when override not set in Redis."""
        mock_client = MagicMock()
        mock_client.get.return_value = None
        mock_redis.return_value = mock_client

        result = get_override("prompt_injection_block_suspicious")
        assert result is None
        mock_client.get.assert_called_once_with(
            f"{REDIS_KEY_PREFIX}prompt_injection_block_suspicious"
        )

    @patch("backend.services.runtime_config._get_redis_client")
    def test_returns_true_for_true_string(self, mock_redis: MagicMock) -> None:
        """Should parse 'true' string to True boolean."""
        mock_client = MagicMock()
        mock_client.get.return_value = "true"
        mock_redis.return_value = mock_client

        result = get_override("prompt_injection_block_suspicious")
        assert result is True

    @patch("backend.services.runtime_config._get_redis_client")
    def test_returns_false_for_false_string(self, mock_redis: MagicMock) -> None:
        """Should parse 'false' string to False boolean."""
        mock_client = MagicMock()
        mock_client.get.return_value = "false"
        mock_redis.return_value = mock_client

        result = get_override("prompt_injection_block_suspicious")
        assert result is False


class TestSetOverride:
    """Tests for set_override function."""

    @patch("backend.services.runtime_config._get_redis_client")
    def test_rejects_non_whitelisted_key(self, mock_redis: MagicMock) -> None:
        """Non-whitelisted keys should be rejected."""
        result = set_override("not_allowed_key", True)
        assert result is False
        mock_redis.assert_not_called()

    @patch("backend.services.runtime_config._get_redis_client")
    def test_rejects_wrong_type(self, mock_redis: MagicMock) -> None:
        """Wrong type values should be rejected."""
        result = set_override("prompt_injection_block_suspicious", "not_a_bool")
        assert result is False
        mock_redis.assert_not_called()

    @patch("backend.services.runtime_config._get_redis_client")
    def test_returns_false_when_redis_unavailable(self, mock_redis: MagicMock) -> None:
        """Should return False when Redis is unavailable."""
        mock_redis.return_value = None
        result = set_override("prompt_injection_block_suspicious", True)
        assert result is False

    @patch("backend.services.runtime_config._get_redis_client")
    def test_sets_true_value(self, mock_redis: MagicMock) -> None:
        """Should set 'true' string for True boolean."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        result = set_override("prompt_injection_block_suspicious", True)
        assert result is True
        mock_client.set.assert_called_once_with(
            f"{REDIS_KEY_PREFIX}prompt_injection_block_suspicious", "true"
        )

    @patch("backend.services.runtime_config._get_redis_client")
    def test_sets_false_value(self, mock_redis: MagicMock) -> None:
        """Should set 'false' string for False boolean."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        result = set_override("prompt_injection_block_suspicious", False)
        assert result is True
        mock_client.set.assert_called_once_with(
            f"{REDIS_KEY_PREFIX}prompt_injection_block_suspicious", "false"
        )


class TestClearOverride:
    """Tests for clear_override function."""

    @patch("backend.services.runtime_config._get_redis_client")
    def test_rejects_non_whitelisted_key(self, mock_redis: MagicMock) -> None:
        """Non-whitelisted keys should be rejected."""
        result = clear_override("not_allowed_key")
        assert result is False
        mock_redis.assert_not_called()

    @patch("backend.services.runtime_config._get_redis_client")
    def test_returns_false_when_redis_unavailable(self, mock_redis: MagicMock) -> None:
        """Should return False when Redis is unavailable."""
        mock_redis.return_value = None
        result = clear_override("prompt_injection_block_suspicious")
        assert result is False

    @patch("backend.services.runtime_config._get_redis_client")
    def test_deletes_key(self, mock_redis: MagicMock) -> None:
        """Should delete the Redis key."""
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        result = clear_override("prompt_injection_block_suspicious")
        assert result is True
        mock_client.delete.assert_called_once_with(
            f"{REDIS_KEY_PREFIX}prompt_injection_block_suspicious"
        )


class TestGetAllOverrides:
    """Tests for get_all_overrides function."""

    @patch("backend.services.runtime_config.get_override")
    @patch("backend.services.runtime_config.get_settings")
    def test_returns_all_whitelisted_keys(
        self, mock_settings: MagicMock, mock_get_override: MagicMock
    ) -> None:
        """Should return info for all whitelisted keys."""
        mock_settings.return_value.prompt_injection_block_suspicious = True
        mock_get_override.return_value = None

        result = get_all_overrides()

        assert "prompt_injection_block_suspicious" in result
        item = result["prompt_injection_block_suspicious"]
        assert item["key"] == "prompt_injection_block_suspicious"
        assert item["default_value"] is True
        assert item["override_value"] is None
        assert item["effective_value"] is True
        assert item["is_overridden"] is False

    @patch("backend.services.runtime_config.get_override")
    @patch("backend.services.runtime_config.get_settings")
    def test_shows_override_when_set(
        self, mock_settings: MagicMock, mock_get_override: MagicMock
    ) -> None:
        """Should show override value when set."""
        mock_settings.return_value.prompt_injection_block_suspicious = True
        mock_get_override.return_value = False

        result = get_all_overrides()

        item = result["prompt_injection_block_suspicious"]
        assert item["default_value"] is True
        assert item["override_value"] is False
        assert item["effective_value"] is False
        assert item["is_overridden"] is True


class TestGetEffectiveValue:
    """Tests for get_effective_value function."""

    @patch("backend.services.runtime_config.get_override")
    @patch("backend.services.runtime_config.get_settings")
    def test_returns_override_when_set(
        self, mock_settings: MagicMock, mock_get_override: MagicMock
    ) -> None:
        """Should return override value when set."""
        mock_settings.return_value.prompt_injection_block_suspicious = True
        mock_get_override.return_value = False

        result = get_effective_value("prompt_injection_block_suspicious")
        assert result is False

    @patch("backend.services.runtime_config.get_override")
    @patch("backend.services.runtime_config.get_settings")
    def test_returns_default_when_no_override(
        self, mock_settings: MagicMock, mock_get_override: MagicMock
    ) -> None:
        """Should return default value when no override."""
        mock_settings.return_value.prompt_injection_block_suspicious = True
        mock_get_override.return_value = None

        result = get_effective_value("prompt_injection_block_suspicious")
        assert result is True
