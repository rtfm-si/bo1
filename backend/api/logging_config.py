"""Logging configuration for Board of One API.

Configures logging levels per environment and silences noisy third-party libraries.
"""

import logging
import sys
from typing import Literal

# Noisy loggers to silence in production (only show WARNING+)
NOISY_LOGGERS = [
    "uvicorn.access",  # HTTP access logs (very noisy)
    "httpx",  # HTTP client requests
    "httpcore",  # HTTP connection internals
    "asyncpg",  # PostgreSQL connection pool
    "aiobotocore",  # S3 client internals
    "botocore",  # AWS SDK internals
    "urllib3",  # HTTP library internals
]


def configure_logging(
    log_level: str = "INFO",
    log_format: Literal["text", "json"] = "text",
    verbose_libs: bool = False,
) -> None:
    """Configure application logging.

    Args:
        log_level: Root logger level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_format: Output format - "text" for human-readable, "json" for structured
        verbose_libs: If True, don't silence noisy third-party loggers

    Examples:
        >>> configure_logging("DEBUG", "text")  # Development
        >>> configure_logging("INFO", "json")   # Production
    """
    # Parse log level string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates on reconfiguration
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler with appropriate format
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(numeric_level)

    if log_format == "json":
        # JSON format for structured logging (Loki/Grafana)
        formatter = logging.Formatter(
            '{"timestamp":"%(asctime)s","level":"%(levelname)s","logger":"%(name)s",'
            '"message":"%(message)s","module":"%(module)s","function":"%(funcName)s"}'
        )
    else:
        # Human-readable text format for development
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%H:%M:%S",
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Silence noisy third-party loggers unless verbose_libs is enabled
    for logger_name in NOISY_LOGGERS:
        logger = logging.getLogger(logger_name)
        if verbose_libs:
            # Reset to NOTSET so they inherit from root
            logger.setLevel(logging.NOTSET)
        else:
            # Silence to WARNING
            logger.setLevel(logging.WARNING)

    # Always keep uvicorn.error at configured level for startup/error messages
    logging.getLogger("uvicorn.error").setLevel(numeric_level)

    # Log configuration summary
    logger = logging.getLogger(__name__)
    logger.info(
        f"Logging configured: level={log_level}, format={log_format}, verbose_libs={verbose_libs}"
    )
