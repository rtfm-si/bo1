"""Custom exceptions for Board of One.

Provides a hierarchy of domain-specific exceptions for better error handling
and more informative error messages. These replace broad `except Exception`
blocks throughout the codebase.

Usage:
    from bo1.exceptions import (
        Bo1Error,
        ConfigurationError,
        DatabaseError,
        ExternalServiceError,
        ValidationError,
    )

    try:
        await some_operation()
    except ValidationError as e:
        # Handle validation errors specifically
        logger.warning(f"Validation failed: {e}")
    except ExternalServiceError as e:
        # Handle external service failures
        logger.error(f"External service error: {e}")
    except Bo1Error as e:
        # Catch-all for known application errors
        logger.error(f"Application error: {e}")
"""

from typing import Any


class Bo1Error(Exception):
    """Base exception for all Board of One errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(self, message: str, details: dict[str, Any] | None = None) -> None:
        """Initialize the exception with a message and optional details."""
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def __str__(self) -> str:
        """Return a string representation of the error."""
        if self.details:
            return f"{self.message} - {self.details}"
        return self.message


# Configuration Errors
class ConfigurationError(Bo1Error):
    """Raised when there's a configuration problem."""

    pass


class MissingConfigError(ConfigurationError):
    """Raised when a required configuration value is missing."""

    pass


# Database Errors
class DatabaseError(Bo1Error):
    """Base class for database-related errors."""

    pass


class ConnectionError(DatabaseError):
    """Raised when database connection fails."""

    pass


class QueryError(DatabaseError):
    """Raised when a database query fails."""

    pass


class NotFoundError(DatabaseError):
    """Raised when a requested resource is not found in the database."""

    pass


class DuplicateError(DatabaseError):
    """Raised when attempting to create a duplicate resource."""

    pass


# External Service Errors
class ExternalServiceError(Bo1Error):
    """Base class for external service errors (APIs, etc.)."""

    pass


class AnthropicError(ExternalServiceError):
    """Raised when Anthropic API calls fail."""

    pass


class VoyageError(ExternalServiceError):
    """Raised when Voyage AI API calls fail."""

    pass


class TavilyError(ExternalServiceError):
    """Raised when Tavily search API calls fail."""

    pass


class BraveSearchError(ExternalServiceError):
    """Raised when Brave Search API calls fail."""

    pass


class RedisError(ExternalServiceError):
    """Raised when Redis operations fail."""

    pass


# Validation Errors
class ValidationError(Bo1Error):
    """Base class for validation errors."""

    pass


class InputValidationError(ValidationError):
    """Raised when user input fails validation."""

    pass


class StateValidationError(ValidationError):
    """Raised when application state is invalid."""

    pass


# Deliberation Errors
class DeliberationError(Bo1Error):
    """Base class for deliberation-related errors."""

    pass


class SessionError(DeliberationError):
    """Raised for session-related issues."""

    pass


class SessionNotFoundError(SessionError, NotFoundError):
    """Raised when a session cannot be found."""

    pass


class SessionStateError(SessionError):
    """Raised when session is in an invalid state for the requested operation."""

    pass


class TimeoutError(DeliberationError):
    """Raised when a deliberation operation times out."""

    pass


class LoopDetectedError(DeliberationError):
    """Raised when an infinite loop is detected in deliberation."""

    pass


class CostLimitError(DeliberationError):
    """Raised when cost limits are exceeded."""

    pass


# Authentication/Authorization Errors
class AuthError(Bo1Error):
    """Base class for authentication/authorization errors."""

    pass


class AuthenticationError(AuthError):
    """Raised when authentication fails."""

    pass


class AuthorizationError(AuthError):
    """Raised when user lacks permission for an operation."""

    pass


class RateLimitError(AuthError):
    """Raised when rate limits are exceeded."""

    pass


# Enrichment Errors
class EnrichmentError(Bo1Error):
    """Base class for data enrichment errors."""

    pass


class CompetitorDetectionError(EnrichmentError):
    """Raised when competitor detection fails."""

    pass


class MarketTrendsError(EnrichmentError):
    """Raised when market trends analysis fails."""

    pass
