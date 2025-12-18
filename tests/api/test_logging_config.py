"""Unit tests for logging configuration."""

import logging

from backend.api.logging_config import NOISY_LOGGERS, configure_logging


class TestConfigureLogging:
    """Tests for configure_logging function."""

    def setup_method(self) -> None:
        """Reset logging before each test."""
        # Store original handler count
        self.original_handlers = logging.root.handlers[:]

    def teardown_method(self) -> None:
        """Restore logging after each test."""
        # Remove all handlers added during test
        for handler in logging.root.handlers[:]:
            logging.root.removeHandler(handler)
        # Restore original handlers
        for handler in self.original_handlers:
            logging.root.addHandler(handler)

    def test_sets_root_log_level_debug(self) -> None:
        """Root logger level should be set to DEBUG."""
        configure_logging(log_level="DEBUG")
        assert logging.root.level == logging.DEBUG

    def test_sets_root_log_level_info(self) -> None:
        """Root logger level should be set to INFO."""
        configure_logging(log_level="INFO")
        assert logging.root.level == logging.INFO

    def test_sets_root_log_level_warning(self) -> None:
        """Root logger level should be set to WARNING."""
        configure_logging(log_level="WARNING")
        assert logging.root.level == logging.WARNING

    def test_sets_root_log_level_error(self) -> None:
        """Root logger level should be set to ERROR."""
        configure_logging(log_level="ERROR")
        assert logging.root.level == logging.ERROR

    def test_silences_noisy_loggers_by_default(self) -> None:
        """Noisy loggers should be silenced to WARNING by default."""
        configure_logging(log_level="DEBUG", verbose_libs=False)

        for logger_name in NOISY_LOGGERS:
            logger = logging.getLogger(logger_name)
            assert logger.level >= logging.WARNING, (
                f"Logger {logger_name} should be silenced to WARNING+, but level is {logger.level}"
            )

    def test_verbose_libs_enables_noisy_loggers(self) -> None:
        """Noisy loggers should not be silenced when verbose_libs=True."""
        configure_logging(log_level="DEBUG", verbose_libs=True)

        # When verbose_libs is True, loggers should be reset to NOTSET (0)
        # so they inherit from root
        for logger_name in NOISY_LOGGERS:
            logger = logging.getLogger(logger_name)
            # Level should be NOTSET (0) to inherit from parent
            assert logger.level == logging.NOTSET, (
                f"Logger {logger_name} should be NOTSET with verbose_libs=True, "
                f"but level is {logger.level}"
            )

    def test_uvicorn_error_logger_not_silenced(self) -> None:
        """uvicorn.error should always be at configured level for startup messages."""
        configure_logging(log_level="INFO")
        uvicorn_error = logging.getLogger("uvicorn.error")
        assert uvicorn_error.level == logging.INFO

    def test_creates_handler(self) -> None:
        """Should create a stream handler."""
        configure_logging(log_level="INFO")
        assert len(logging.root.handlers) >= 1
        assert any(isinstance(h, logging.StreamHandler) for h in logging.root.handlers)

    def test_text_format(self) -> None:
        """Text format should use pipe-separated human-readable format."""
        configure_logging(log_level="INFO", log_format="text")
        handler = logging.root.handlers[-1]
        assert handler.formatter is not None
        # Text format uses pipe separators
        assert "|" in handler.formatter._fmt

    def test_json_format(self) -> None:
        """JSON format should use structured JSON format."""
        configure_logging(log_level="INFO", log_format="json")
        handler = logging.root.handlers[-1]
        assert handler.formatter is not None
        # JSON format starts with timestamp
        assert '"timestamp"' in handler.formatter._fmt


class TestNoisyLoggers:
    """Tests for NOISY_LOGGERS constant."""

    def test_includes_uvicorn_access(self) -> None:
        """uvicorn.access should be in noisy loggers list."""
        assert "uvicorn.access" in NOISY_LOGGERS

    def test_includes_httpx(self) -> None:
        """httpx should be in noisy loggers list."""
        assert "httpx" in NOISY_LOGGERS

    def test_includes_asyncpg(self) -> None:
        """asyncpg should be in noisy loggers list."""
        assert "asyncpg" in NOISY_LOGGERS

    def test_includes_httpcore(self) -> None:
        """httpcore should be in noisy loggers list."""
        assert "httpcore" in NOISY_LOGGERS
