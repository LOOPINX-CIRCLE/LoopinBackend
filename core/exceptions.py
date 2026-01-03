"""
Custom exceptions for the Loopin Backend application.
"""

from typing import Optional, Dict, Any


class LoopinBaseException(Exception):
    """
    Base exception class for Loopin Backend.
    """
    
    def __init__(self, message: str, code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)


class ValidationError(LoopinBaseException):
    """
    Custom validation error.
    """
    pass


class AuthenticationError(LoopinBaseException):
    """
    Authentication related error.
    """
    pass


class AuthorizationError(LoopinBaseException):
    """
    Authorization related error.
    """
    pass


class NotFoundError(LoopinBaseException):
    """
    Resource not found error.
    """
    pass


class ConflictError(LoopinBaseException):
    """
    Resource conflict error.
    """
    pass


class ExternalServiceError(LoopinBaseException):
    """
    External service error.
    """
    pass


class DatabaseError(LoopinBaseException):
    """
    Database related error.
    """
    pass


class CacheError(LoopinBaseException):
    """
    Cache related error.
    """
    pass


class ConfigurationError(LoopinBaseException):
    """
    Configuration related error.
    """
    pass


class RateLimitError(LoopinBaseException):
    """
    Rate limit exceeded error.
    """
    pass


class BusinessLogicError(LoopinBaseException):
    """
    Business logic error.
    """
    pass
