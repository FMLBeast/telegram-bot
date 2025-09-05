"""Custom exceptions for the bot."""

from typing import Optional, Any


class BotError(Exception):
    """Base exception for bot errors."""
    
    def __init__(self, message: str, details: Optional[Any] = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details


class ConfigurationError(BotError):
    """Configuration related errors."""
    pass


class DatabaseError(BotError):
    """Database related errors."""
    pass


class APIError(BotError):
    """External API related errors."""
    pass


class RateLimitError(BotError):
    """Rate limiting errors."""
    pass


class AuthenticationError(BotError):
    """Authentication related errors."""
    pass


class ValidationError(BotError):
    """Data validation errors."""
    pass