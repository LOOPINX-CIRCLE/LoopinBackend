"""
Core utilities for the Loopin Backend application.

This module provides common utility functions used across the application.
"""

import logging
import functools
import hashlib
import secrets
from typing import Any, Dict, Optional, Callable
from django.core.cache import cache
from django.conf import settings
from django.core.exceptions import ValidationError
import re


def get_logger(name: str) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def cache_result(timeout: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache key
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = f"{key_prefix}:{func.__name__}:{hash(str(args) + str(kwargs))}"
            
            # Try to get from cache
            result = cache.get(cache_key)
            if result is not None:
                return result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache.set(cache_key, result, timeout)
            return result
        
        return wrapper
    return decorator


def generate_secret_key(length: int = 32) -> str:
    """
    Generate a secure random secret key.
    
    Args:
        length: Length of the secret key
        
    Returns:
        Random secret key
    """
    return secrets.token_urlsafe(length)


def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    """
    Hash a password with salt.
    
    Args:
        password: Plain text password
        salt: Optional salt (generated if not provided)
        
    Returns:
        Tuple of (hashed_password, salt)
    """
    if salt is None:
        salt = secrets.token_hex(16)
    
    # Combine password and salt
    combined = f"{password}{salt}"
    
    # Hash using SHA-256
    hashed = hashlib.sha256(combined.encode()).hexdigest()
    
    return hashed, salt


def validate_phone_number(phone_number: str) -> bool:
    """
    Validate phone number format.
    
    Args:
        phone_number: Phone number to validate
        
    Returns:
        True if valid, False otherwise
    """
    # Remove all non-digit characters except +
    cleaned = re.sub(r'[^\d+]', '', phone_number)
    
    # Check if it starts with + and has 10-15 digits
    pattern = r'^\+\d{10,15}$'
    return bool(re.match(pattern, cleaned))


def format_phone_number(phone_number: str) -> str:
    """
    Format phone number to standard format.
    
    Args:
        phone_number: Phone number to format
        
    Returns:
        Formatted phone number
    """
    # Remove all non-digit characters
    digits = re.sub(r'\D', '', phone_number)
    
    # Add + prefix if not present
    if not phone_number.startswith('+'):
        digits = '+' + digits
    
    return digits


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename for safe storage.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    # Remove or replace unsafe characters
    filename = re.sub(r'[^\w\-_\.]', '_', filename)
    
    # Remove multiple underscores
    filename = re.sub(r'_+', '_', filename)
    
    # Remove leading/trailing underscores
    filename = filename.strip('_')
    
    return filename


def get_client_ip(request) -> str:
    """
    Get client IP address from request.
    
    Args:
        request: Django request object
        
    Returns:
        Client IP address
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def is_valid_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address to validate
        
    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def truncate_string(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate string to specified length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add when truncating
        
    Returns:
        Truncated string
    """
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def deep_merge_dicts(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """
    Deep merge two dictionaries.
    
    Args:
        dict1: First dictionary
        dict2: Second dictionary
        
    Returns:
        Merged dictionary
    """
    result = dict1.copy()
    
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    
    return result


def get_setting(key: str, default: Any = None) -> Any:
    """
    Get Django setting with fallback.
    
    Args:
        key: Setting key
        default: Default value if setting not found
        
    Returns:
        Setting value or default
    """
    return getattr(settings, key, default)


def validate_json_schema(data: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    Basic JSON schema validation.
    
    Args:
        data: Data to validate
        schema: Schema definition
        
    Returns:
        True if valid, False otherwise
    """
    try:
        # Basic validation - can be extended with jsonschema library
        for field, rules in schema.items():
            if field not in data:
                if rules.get('required', False):
                    return False
                continue
            
            value = data[field]
            field_type = rules.get('type')
            
            if field_type == 'string' and not isinstance(value, str):
                return False
            elif field_type == 'integer' and not isinstance(value, int):
                return False
            elif field_type == 'boolean' and not isinstance(value, bool):
                return False
            elif field_type == 'array' and not isinstance(value, list):
                return False
            elif field_type == 'object' and not isinstance(value, dict):
                return False
        
        return True
    except Exception:
        return False


def retry_on_exception(max_retries: int = 3, delay: float = 1.0):
    """
    Decorator to retry function on exception.
    
    Args:
        max_retries: Maximum number of retries
        delay: Delay between retries in seconds
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import time
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries:
                        raise e
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
            
        return wrapper
    return decorator
