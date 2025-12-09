"""Tests for checkpointer factory (P2: PostgreSQL checkpoint persistence)."""

import logging
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_create_checkpointer_redis_default(monkeypatch):
    """Test factory creates Redis checkpointer by default."""
    monkeypatch.setenv("CHECKPOINT_BACKEND", "redis")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_DB", "0")
    monkeypatch.setenv("REDIS_PASSWORD", "")

    # Reset settings singleton
    from bo1.config import reset_settings

    reset_settings()

    with patch("langgraph.checkpoint.redis.aio.AsyncRedisSaver") as mock_redis_saver:
        mock_redis_saver.return_value = MagicMock()

        from bo1.graph.checkpointer_factory import create_checkpointer

        checkpointer = create_checkpointer()

        mock_redis_saver.assert_called_once()
        assert checkpointer is not None

    reset_settings()


@pytest.mark.unit
def test_create_checkpointer_explicit_redis():
    """Test factory creates Redis checkpointer when explicitly requested."""
    with patch("langgraph.checkpoint.redis.aio.AsyncRedisSaver") as mock_redis_saver:
        mock_redis_saver.return_value = MagicMock()

        from bo1.graph.checkpointer_factory import create_checkpointer

        checkpointer = create_checkpointer(backend="redis")

        mock_redis_saver.assert_called_once()
        assert checkpointer is not None


@pytest.mark.unit
def test_create_checkpointer_postgres(monkeypatch):
    """Test factory creates PostgreSQL checkpointer when requested."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    # Reset settings singleton
    from bo1.config import reset_settings

    reset_settings()

    # Reset the postgres setup flag
    import bo1.graph.checkpointer_factory as factory_module

    factory_module._postgres_setup_complete = False

    with (
        patch.object(factory_module, "_run_postgres_setup_sync") as mock_setup,
        patch("psycopg_pool.AsyncConnectionPool") as mock_pool,
        patch("langgraph.checkpoint.postgres.aio.AsyncPostgresSaver") as mock_pg_saver,
    ):
        mock_pg_saver.return_value = MagicMock()

        checkpointer = factory_module.create_checkpointer(backend="postgres")

        mock_pool.assert_called_once()
        mock_pg_saver.assert_called_once()
        mock_setup.assert_called_once()  # Auto-setup on first use
        assert checkpointer is not None

    reset_settings()
    factory_module._postgres_setup_complete = False


@pytest.mark.unit
def test_create_checkpointer_postgres_setup_once(monkeypatch):
    """Test PostgreSQL setup() is only called once (singleton pattern)."""
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    from bo1.config import reset_settings

    reset_settings()

    import bo1.graph.checkpointer_factory as factory_module

    factory_module._postgres_setup_complete = False

    with (
        patch.object(factory_module, "_run_postgres_setup_sync") as mock_setup,
        patch("psycopg_pool.AsyncConnectionPool"),
        patch("langgraph.checkpoint.postgres.aio.AsyncPostgresSaver") as mock_pg_saver,
    ):
        mock_pg_saver.return_value = MagicMock()

        # First call - should setup
        factory_module.create_checkpointer(backend="postgres")
        assert mock_setup.call_count == 1

        # Second call - should NOT setup again
        factory_module.create_checkpointer(backend="postgres")
        assert mock_setup.call_count == 1  # Still 1

    reset_settings()
    factory_module._postgres_setup_complete = False


@pytest.mark.unit
def test_create_checkpointer_invalid_backend():
    """Test factory raises error for invalid backend."""
    from bo1.graph.checkpointer_factory import create_checkpointer

    with pytest.raises(ValueError, match="Unknown checkpoint backend"):
        create_checkpointer(backend="invalid")


@pytest.mark.unit
def test_create_checkpointer_wraps_with_logging():
    """Test factory wraps checkpointer with LoggingCheckpointerWrapper."""
    with patch("langgraph.checkpoint.redis.aio.AsyncRedisSaver") as mock_redis_saver:
        mock_redis_saver.return_value = MagicMock()

        from bo1.graph.checkpointer import LoggingCheckpointerWrapper
        from bo1.graph.checkpointer_factory import create_checkpointer

        checkpointer = create_checkpointer(backend="redis")

        assert isinstance(checkpointer, LoggingCheckpointerWrapper)


@pytest.mark.unit
def test_get_checkpointer_info_redis(monkeypatch):
    """Test get_checkpointer_info returns Redis config."""
    monkeypatch.setenv("CHECKPOINT_BACKEND", "redis")
    monkeypatch.setenv("REDIS_HOST", "testhost")
    monkeypatch.setenv("REDIS_PORT", "6380")
    monkeypatch.setenv("REDIS_DB", "1")
    monkeypatch.setenv("REDIS_PASSWORD", "secret")

    from bo1.config import reset_settings

    reset_settings()

    from bo1.graph.checkpointer_factory import get_checkpointer_info

    info = get_checkpointer_info()

    assert info["backend"] == "redis"
    assert info["host"] == "testhost"
    assert info["port"] == 6380
    assert info["db"] == 1
    assert info["has_auth"] is True

    reset_settings()


@pytest.mark.unit
def test_get_checkpointer_info_postgres(monkeypatch):
    """Test get_checkpointer_info returns Postgres config with masked password."""
    monkeypatch.setenv("CHECKPOINT_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret@host:5432/db")

    from bo1.config import reset_settings

    reset_settings()

    from bo1.graph.checkpointer_factory import get_checkpointer_info

    info = get_checkpointer_info()

    assert info["backend"] == "postgres"
    assert "***" in info["url"]
    assert "secret" not in info["url"]

    reset_settings()


@pytest.mark.unit
def test_mask_password():
    """Test password masking in connection URLs."""
    from bo1.graph.checkpointer_factory import _mask_password

    url = "postgresql://user:mypassword@localhost:5432/db"
    masked = _mask_password(url)

    assert masked == "postgresql://user:***@localhost:5432/db"
    assert "mypassword" not in masked


@pytest.mark.unit
def test_mask_password_no_auth():
    """Test password masking handles URLs without auth."""
    from bo1.graph.checkpointer_factory import _mask_password

    url = "postgresql://localhost:5432/db"
    masked = _mask_password(url)

    assert masked == url  # No change


@pytest.mark.unit
def test_factory_logs_creation(caplog):
    """Test factory logs checkpointer creation."""
    caplog.set_level(logging.INFO)

    with patch("langgraph.checkpoint.redis.aio.AsyncRedisSaver") as mock_redis_saver:
        mock_redis_saver.return_value = MagicMock()

        from bo1.graph.checkpointer_factory import create_checkpointer

        create_checkpointer(backend="redis")

        assert "Created Redis checkpointer" in caplog.text
