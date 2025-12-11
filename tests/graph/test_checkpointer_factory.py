"""Tests for checkpointer factory (P2: PostgreSQL checkpoint persistence)."""

import logging
from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_create_checkpointer_redis_default(monkeypatch):
    """Test factory creates Redis checkpointer by default."""
    monkeypatch.setenv("CHECKPOINT_BACKEND", "redis")
    monkeypatch.setenv("CHECKPOINT_FALLBACK_ENABLED", "false")  # Skip Redis health check
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


@pytest.mark.unit
def test_check_checkpoint_health_redis_healthy(monkeypatch):
    """Test checkpoint health check returns healthy for Redis."""
    monkeypatch.setenv("CHECKPOINT_BACKEND", "redis")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_DB", "0")
    monkeypatch.setenv("REDIS_PASSWORD", "")

    from bo1.config import reset_settings

    reset_settings()

    with patch("redis.from_url") as mock_redis:
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        from bo1.graph.checkpointer_factory import check_checkpoint_health

        health = check_checkpoint_health()

        assert health["healthy"] is True
        assert health["backend"] == "redis"
        assert "healthy" in health["message"].lower()
        mock_client.ping.assert_called_once()

    reset_settings()


@pytest.mark.unit
def test_check_checkpoint_health_redis_unhealthy(monkeypatch):
    """Test checkpoint health check returns unhealthy when Redis fails."""
    monkeypatch.setenv("CHECKPOINT_BACKEND", "redis")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_DB", "0")
    monkeypatch.setenv("REDIS_PASSWORD", "")

    from bo1.config import reset_settings

    reset_settings()

    with patch("redis.from_url") as mock_redis:
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Connection refused")
        mock_redis.return_value = mock_client

        from bo1.graph.checkpointer_factory import check_checkpoint_health

        health = check_checkpoint_health()

        assert health["healthy"] is False
        assert health["backend"] == "redis"
        assert health["error"] is not None

    reset_settings()


@pytest.mark.unit
def test_check_checkpoint_health_postgres_healthy(monkeypatch):
    """Test checkpoint health check returns healthy for Postgres."""
    monkeypatch.setenv("CHECKPOINT_BACKEND", "postgres")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test:test@localhost:5432/test")

    from bo1.config import reset_settings

    reset_settings()

    with patch("psycopg2.connect") as mock_connect:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value.__enter__ = MagicMock(return_value=mock_cursor)
        mock_conn.cursor.return_value.__exit__ = MagicMock(return_value=False)
        mock_connect.return_value = mock_conn

        from bo1.graph.checkpointer_factory import check_checkpoint_health

        health = check_checkpoint_health()

        assert health["healthy"] is True
        assert health["backend"] == "postgres"
        mock_cursor.execute.assert_called_once_with("SELECT 1")

    reset_settings()


@pytest.mark.unit
def test_redis_unavailable_falls_back_to_memory(monkeypatch, caplog):
    """Test Redis failure triggers fallback to MemorySaver."""
    monkeypatch.setenv("CHECKPOINT_BACKEND", "redis")
    monkeypatch.setenv("CHECKPOINT_FALLBACK_ENABLED", "true")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")
    monkeypatch.setenv("REDIS_DB", "0")
    monkeypatch.setenv("REDIS_PASSWORD", "")

    from bo1.config import reset_settings

    reset_settings()

    import bo1.graph.checkpointer_factory as factory_module

    # Reset fallback state
    factory_module._using_fallback = False
    factory_module._fallback_reason = None
    factory_module._original_backend = None

    caplog.set_level(logging.WARNING)

    with (
        patch("redis.from_url") as mock_redis,
        patch("langgraph.checkpoint.memory.MemorySaver") as mock_memory_saver,
    ):
        # Simulate Redis connection failure
        mock_client = MagicMock()
        mock_client.ping.side_effect = Exception("Connection refused")
        mock_redis.return_value = mock_client
        mock_memory_saver.return_value = MagicMock()

        checkpointer = factory_module.create_checkpointer(backend="redis")

        # Verify MemorySaver was created
        mock_memory_saver.assert_called_once()
        assert checkpointer is not None

        # Verify fallback state was set
        assert factory_module._using_fallback is True
        assert factory_module._original_backend == "redis"
        assert "Redis unavailable" in factory_module._fallback_reason

        # Verify warning was logged
        assert "falling back to in-memory" in caplog.text.lower()

    reset_settings()
    factory_module._using_fallback = False
    factory_module._fallback_reason = None
    factory_module._original_backend = None


@pytest.mark.unit
def test_fallback_disabled_does_not_check_redis(monkeypatch):
    """Test fallback disabled skips Redis health check."""
    monkeypatch.setenv("CHECKPOINT_BACKEND", "redis")
    monkeypatch.setenv("CHECKPOINT_FALLBACK_ENABLED", "false")
    monkeypatch.setenv("REDIS_HOST", "localhost")
    monkeypatch.setenv("REDIS_PORT", "6379")

    from bo1.config import reset_settings

    reset_settings()

    import bo1.graph.checkpointer_factory as factory_module

    factory_module._using_fallback = False

    with (
        patch("redis.from_url") as mock_redis,
        patch("langgraph.checkpoint.redis.aio.AsyncRedisSaver") as mock_redis_saver,
    ):
        mock_redis_saver.return_value = MagicMock()

        checkpointer = factory_module.create_checkpointer(backend="redis")

        # Redis ping should NOT be called when fallback is disabled
        mock_redis.assert_not_called()
        mock_redis_saver.assert_called_once()
        assert checkpointer is not None

    reset_settings()
    factory_module._using_fallback = False


@pytest.mark.unit
def test_health_check_reports_degraded_state(monkeypatch):
    """Test health check reports degraded=True when using fallback."""
    monkeypatch.setenv("CHECKPOINT_BACKEND", "redis")

    from bo1.config import reset_settings

    reset_settings()

    import bo1.graph.checkpointer_factory as factory_module

    # Simulate fallback state
    factory_module._using_fallback = True
    factory_module._fallback_reason = "Redis unavailable: Connection refused"
    factory_module._original_backend = "redis"

    health = factory_module.check_checkpoint_health()

    assert health["healthy"] is True
    assert health["degraded"] is True
    assert health["backend"] == "memory"
    assert health["original_backend"] == "redis"
    assert "Connection refused" in health["fallback_reason"]
    assert "degraded mode" in health["message"].lower()

    reset_settings()
    factory_module._using_fallback = False
    factory_module._fallback_reason = None
    factory_module._original_backend = None


@pytest.mark.unit
def test_checkpointer_info_shows_fallback_status(monkeypatch):
    """Test get_checkpointer_info includes fallback status."""
    monkeypatch.setenv("CHECKPOINT_BACKEND", "redis")

    from bo1.config import reset_settings

    reset_settings()

    import bo1.graph.checkpointer_factory as factory_module

    # Simulate fallback state
    factory_module._using_fallback = True
    factory_module._fallback_reason = "Redis unavailable: timeout"
    factory_module._original_backend = "redis"

    info = factory_module.get_checkpointer_info()

    assert info["backend"] == "memory"
    assert info["using_fallback"] is True
    assert info["original_backend"] == "redis"
    assert "timeout" in info["fallback_reason"]

    reset_settings()
    factory_module._using_fallback = False
    factory_module._fallback_reason = None
    factory_module._original_backend = None


@pytest.mark.unit
def test_checkpointer_info_no_fallback(monkeypatch):
    """Test get_checkpointer_info shows using_fallback=False when not degraded."""
    monkeypatch.setenv("CHECKPOINT_BACKEND", "redis")
    monkeypatch.setenv("REDIS_HOST", "localhost")

    from bo1.config import reset_settings

    reset_settings()

    import bo1.graph.checkpointer_factory as factory_module

    factory_module._using_fallback = False

    info = factory_module.get_checkpointer_info()

    assert info["backend"] == "redis"
    assert info["using_fallback"] is False

    reset_settings()


@pytest.mark.unit
def test_health_check_degraded_false_when_healthy(monkeypatch):
    """Test health check reports degraded=False when backend is healthy."""
    monkeypatch.setenv("CHECKPOINT_BACKEND", "redis")
    monkeypatch.setenv("REDIS_HOST", "localhost")

    from bo1.config import reset_settings

    reset_settings()

    import bo1.graph.checkpointer_factory as factory_module

    factory_module._using_fallback = False

    with patch("redis.from_url") as mock_redis:
        mock_client = MagicMock()
        mock_redis.return_value = mock_client

        health = factory_module.check_checkpoint_health()

        assert health["healthy"] is True
        assert health["degraded"] is False
        assert health["fallback_reason"] is None

    reset_settings()
