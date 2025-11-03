"""
Request logging middleware for the Loopin Backend application.

This middleware logs all incoming requests with detailed information
for monitoring and debugging purposes.
"""

import time
import logging
from typing import Callable
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from core.utils.logger import get_logger


class RequestLoggingMiddleware(MiddlewareMixin):
    """
    Middleware to log all HTTP requests with timing and metadata.
    """
    
    def __init__(self, get_response: Callable = None):
        super().__init__(get_response)
        self.logger = get_logger('core.request_logging')
    
    def process_request(self, request: HttpRequest) -> None:
        """Process incoming request."""
        # Store start time for timing calculation
        request._start_time = time.time()
        
        # Log request details
        self.logger.info(
            f"Request started: {request.method} {request.path}",
            extra={
                'method': request.method,
                'path': request.path,
                'query_params': dict(request.GET),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'remote_addr': self.get_client_ip(request),
                'content_type': request.META.get('CONTENT_TYPE', ''),
                'content_length': request.META.get('CONTENT_LENGTH', ''),
            }
        )
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Process outgoing response."""
        # Calculate request duration
        duration = time.time() - getattr(request, '_start_time', time.time())
        
        # Log response details
        self.logger.info(
            f"Request completed: {request.method} {request.path} - {response.status_code}",
            extra={
                'method': request.method,
                'path': request.path,
                'status_code': response.status_code,
                'duration': duration,
                'response_size': len(response.content) if hasattr(response, 'content') else 0,
                'user_id': getattr(request, 'user', {}).get('id') if hasattr(request, 'user') else None,
            }
        )
        
        return response
    
    def process_exception(self, request: HttpRequest, exception: Exception) -> None:
        """Process exceptions during request handling."""
        duration = time.time() - getattr(request, '_start_time', time.time())
        
        self.logger.error(
            f"Request failed: {request.method} {request.path} - {type(exception).__name__}: {str(exception)}",
            extra={
                'method': request.method,
                'path': request.path,
                'exception_type': type(exception).__name__,
                'exception_message': str(exception),
                'duration': duration,
                'user_id': getattr(request, 'user', {}).get('id') if hasattr(request, 'user') else None,
            },
            exc_info=True
        )
    
    def get_client_ip(self, request: HttpRequest) -> str:
        """Get client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
