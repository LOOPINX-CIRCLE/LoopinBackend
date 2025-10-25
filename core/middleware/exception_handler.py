"""
Exception handler middleware for the Loopin Backend application.

This middleware provides centralized exception handling and
converts Django exceptions to appropriate HTTP responses.
"""

import logging
from typing import Callable
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.utils.deprecation import MiddlewareMixin
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import DatabaseError as DjangoDatabaseError
from django.contrib.auth.models import AnonymousUser

from core.utils.logger import get_logger
from core.exceptions import (
    LoopinBaseException,
    ValidationError,
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
    ConflictError,
    ExternalServiceError,
    DatabaseError,
    CacheError,
    ConfigurationError,
    RateLimitError,
    BusinessLogicError,
)


class ExceptionHandlerMiddleware(MiddlewareMixin):
    """
    Middleware to handle exceptions and convert them to appropriate HTTP responses.
    """
    
    def __init__(self, get_response: Callable = None):
        super().__init__(get_response)
        self.logger = get_logger('core.exception_handler')
    
    def process_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse:
        """Process exceptions and return appropriate HTTP response."""
        
        # Handle custom Loopin exceptions
        if isinstance(exception, LoopinBaseException):
            return self.handle_loopin_exception(request, exception)
        
        # Handle Django exceptions
        if isinstance(exception, DjangoValidationError):
            return self.handle_validation_error(request, exception)
        
        if isinstance(exception, DjangoDatabaseError):
            return self.handle_database_error(request, exception)
        
        # Handle other exceptions
        return self.handle_generic_exception(request, exception)
    
    def handle_loopin_exception(self, request: HttpRequest, exception: LoopinBaseException) -> HttpResponse:
        """Handle custom Loopin exceptions."""
        
        # Map exception types to HTTP status codes
        status_mapping = {
            ValidationError: 400,
            AuthenticationError: 401,
            AuthorizationError: 403,
            NotFoundError: 404,
            ConflictError: 409,
            RateLimitError: 429,
            ExternalServiceError: 502,
            DatabaseError: 503,
            CacheError: 503,
            ConfigurationError: 500,
            BusinessLogicError: 500,
        }
        
        status_code = status_mapping.get(type(exception), 500)
        
        # Log the exception
        self.logger.error(
            f"Loopin exception: {type(exception).__name__}: {exception.message}",
            extra={
                'exception_type': type(exception).__name__,
                'exception_code': exception.code,
                'exception_details': exception.details,
                'path': request.path,
                'method': request.method,
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            }
        )
        
        # Return JSON response
        return JsonResponse(
            {
                'success': False,
                'error': exception.message,
                'error_code': exception.code,
                'details': exception.details,
            },
            status=status_code
        )
    
    def handle_validation_error(self, request: HttpRequest, exception: DjangoValidationError) -> HttpResponse:
        """Handle Django validation errors."""
        
        self.logger.warning(
            f"Django validation error: {str(exception)}",
            extra={
                'path': request.path,
                'method': request.method,
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            }
        )
        
        return JsonResponse(
            {
                'success': False,
                'error': 'Validation error',
                'error_code': 'VALIDATION_ERROR',
                'details': str(exception),
            },
            status=400
        )
    
    def handle_database_error(self, request: HttpRequest, exception: DjangoDatabaseError) -> HttpResponse:
        """Handle Django database errors."""
        
        self.logger.error(
            f"Django database error: {str(exception)}",
            extra={
                'path': request.path,
                'method': request.method,
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            },
            exc_info=True
        )
        
        return JsonResponse(
            {
                'success': False,
                'error': 'Database error',
                'error_code': 'DATABASE_ERROR',
                'details': 'An internal error occurred. Please try again later.',
            },
            status=503
        )
    
    def handle_generic_exception(self, request: HttpRequest, exception: Exception) -> HttpResponse:
        """Handle generic exceptions."""
        
        self.logger.error(
            f"Unhandled exception: {type(exception).__name__}: {str(exception)}",
            extra={
                'exception_type': type(exception).__name__,
                'path': request.path,
                'method': request.method,
                'user_id': getattr(request.user, 'id', None) if hasattr(request, 'user') else None,
            },
            exc_info=True
        )
        
        return JsonResponse(
            {
                'success': False,
                'error': 'Internal server error',
                'error_code': 'INTERNAL_ERROR',
                'details': 'An unexpected error occurred. Please try again later.',
            },
            status=500
        )
