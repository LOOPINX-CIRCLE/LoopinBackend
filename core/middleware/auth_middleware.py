"""
Authentication middleware for the Loopin Backend application.

This middleware handles JWT token authentication and user context
for API requests.
"""

import jwt
import logging
from typing import Callable, Optional
from django.http import HttpRequest, HttpResponse
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser
from django.conf import settings
from asgiref.sync import sync_to_async

from core.utils.logger import get_logger
from core.exceptions import AuthenticationError


class AuthMiddleware(MiddlewareMixin):
    """
    Middleware to handle JWT authentication for API requests.
    """
    
    def __init__(self, get_response: Callable = None):
        super().__init__(get_response)
        self.logger = get_logger('core.auth_middleware')
    
    def process_request(self, request: HttpRequest) -> None:
        """Process incoming request for authentication."""
        
        # Skip authentication for certain paths
        if self.should_skip_auth(request.path):
            return
        
        # Extract token from Authorization header
        token = self.extract_token(request)
        
        if token:
            try:
                # Decode and validate token
                user = self.validate_token(token)
                if user:
                    request.user = user
                    request._authenticated = True
                else:
                    request.user = AnonymousUser()
                    request._authenticated = False
            except Exception as e:
                self.logger.warning(f"Token validation failed: {str(e)}")
                request.user = AnonymousUser()
                request._authenticated = False
        else:
            request.user = AnonymousUser()
            request._authenticated = False
    
    def should_skip_auth(self, path: str) -> bool:
        """Check if authentication should be skipped for this path."""
        
        skip_paths = [
            '/api/auth/signup',
            '/api/auth/verify-otp',
            '/api/health',
            '/admin/',
            '/static/',
            '/media/',
        ]
        
        return any(path.startswith(skip_path) for skip_path in skip_paths)
    
    def extract_token(self, request: HttpRequest) -> Optional[str]:
        """Extract JWT token from Authorization header."""
        
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header.startswith('Bearer '):
            return None
        
        return auth_header[7:]  # Remove 'Bearer ' prefix
    
    def validate_token(self, token: str):
        """Validate JWT token and return user."""
        
        try:
            # Decode token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=['HS256']
            )
            
            # Extract user ID
            user_id = payload.get('user_id')
            if not user_id:
                raise AuthenticationError("Invalid token: missing user_id")
            
            # Get user from database
            from django.contrib.auth.models import User
            user = User.objects.get(id=user_id)
            
            # Check if user is active
            if not user.is_active:
                raise AuthenticationError("User account is disabled")
            
            return user
            
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token has expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
        except User.DoesNotExist:
            raise AuthenticationError("User not found")
    
    def process_response(self, request: HttpRequest, response: HttpResponse) -> HttpResponse:
        """Process outgoing response."""
        
        # Add authentication status to response headers for debugging
        if hasattr(request, '_authenticated'):
            response['X-Authenticated'] = str(request._authenticated)
        
        return response
