"""
Caching utilities for the Loopin Backend application.
"""

import json
import hashlib
from typing import Any, Optional, Callable, Dict
from django.core.cache import cache
from django.conf import settings
from django.core.cache.utils import make_template_fragment_key
import functools


def cache_key_generator(*args, **kwargs) -> str:
    """
    Generate cache key from arguments.
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        Generated cache key
    """
    # Create a string representation of all arguments
    key_data = str(args) + str(sorted(kwargs.items()))
    
    # Hash the string to create a shorter key
    key_hash = hashlib.md5(key_data.encode()).hexdigest()
    
    return f"cache:{key_hash}"


def cache_result(timeout: int = 300, key_prefix: str = "", key_func: Optional[Callable] = None):
    """
    Decorator to cache function results.
    
    Args:
        timeout: Cache timeout in seconds
        key_prefix: Prefix for cache key
        key_func: Custom key generation function
        
    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = cache_key_generator(*args, **kwargs)
            
            if key_prefix:
                cache_key = f"{key_prefix}:{cache_key}"
            
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


def cache_model_instance(model_class, instance_id: int, timeout: int = 300) -> Optional[Any]:
    """
    Cache a model instance.
    
    Args:
        model_class: Django model class
        instance_id: Instance ID
        timeout: Cache timeout in seconds
        
    Returns:
        Cached instance or None
    """
    cache_key = f"model:{model_class.__name__}:{instance_id}"
    return cache.get(cache_key)


def set_model_instance_cache(instance: Any, timeout: int = 300) -> None:
    """
    Cache a model instance.
    
    Args:
        instance: Django model instance
        timeout: Cache timeout in seconds
    """
    cache_key = f"model:{instance.__class__.__name__}:{instance.pk}"
    cache.set(cache_key, instance, timeout)


def invalidate_model_cache(model_class, instance_id: int) -> None:
    """
    Invalidate cached model instance.
    
    Args:
        model_class: Django model class
        instance_id: Instance ID
    """
    cache_key = f"model:{model_class.__name__}:{instance_id}"
    cache.delete(cache_key)


def cache_queryset(queryset, timeout: int = 300, key_suffix: str = "") -> Any:
    """
    Cache a queryset result.
    
    Args:
        queryset: Django queryset
        timeout: Cache timeout in seconds
        key_suffix: Additional key suffix
        
    Returns:
        Cached queryset result
    """
    # Generate cache key from queryset
    query_str = str(queryset.query)
    cache_key = f"queryset:{hashlib.md5(query_str.encode()).hexdigest()}"
    
    if key_suffix:
        cache_key = f"{cache_key}:{key_suffix}"
    
    # Try to get from cache
    result = cache.get(cache_key)
    if result is not None:
        return result
    
    # Execute queryset and cache result
    result = list(queryset)
    cache.set(cache_key, result, timeout)
    return result


def cache_user_session(user_id: int, session_data: Dict[str, Any], timeout: int = 3600) -> None:
    """
    Cache user session data.
    
    Args:
        user_id: User ID
        session_data: Session data dictionary
        timeout: Cache timeout in seconds
    """
    cache_key = f"user_session:{user_id}"
    cache.set(cache_key, session_data, timeout)


def get_user_session(user_id: int) -> Optional[Dict[str, Any]]:
    """
    Get cached user session data.
    
    Args:
        user_id: User ID
        
    Returns:
        Cached session data or None
    """
    cache_key = f"user_session:{user_id}"
    return cache.get(cache_key)


def invalidate_user_session(user_id: int) -> None:
    """
    Invalidate user session cache.
    
    Args:
        user_id: User ID
    """
    cache_key = f"user_session:{user_id}"
    cache.delete(cache_key)


def cache_api_response(endpoint: str, params: Dict[str, Any], response_data: Any, timeout: int = 300) -> None:
    """
    Cache API response.
    
    Args:
        endpoint: API endpoint
        params: Request parameters
        response_data: Response data
        timeout: Cache timeout in seconds
    """
    # Generate cache key from endpoint and params
    params_str = json.dumps(params, sort_keys=True)
    cache_key = f"api:{endpoint}:{hashlib.md5(params_str.encode()).hexdigest()}"
    
    cache.set(cache_key, response_data, timeout)


def get_cached_api_response(endpoint: str, params: Dict[str, Any]) -> Optional[Any]:
    """
    Get cached API response.
    
    Args:
        endpoint: API endpoint
        params: Request parameters
        
    Returns:
        Cached response data or None
    """
    # Generate cache key from endpoint and params
    params_str = json.dumps(params, sort_keys=True)
    cache_key = f"api:{endpoint}:{hashlib.md5(params_str.encode()).hexdigest()}"
    
    return cache.get(cache_key)


def invalidate_api_cache(endpoint: str, params: Optional[Dict[str, Any]] = None) -> None:
    """
    Invalidate API cache.
    
    Args:
        endpoint: API endpoint
        params: Optional specific parameters to invalidate
    """
    if params:
        # Invalidate specific cache entry
        params_str = json.dumps(params, sort_keys=True)
        cache_key = f"api:{endpoint}:{hashlib.md5(params_str.encode()).hexdigest()}"
        cache.delete(cache_key)
    else:
        # Invalidate all cache entries for endpoint
        cache_key_pattern = f"api:{endpoint}:*"
        # Note: This is a simplified approach. In production, you might want to use
        # a more sophisticated cache invalidation strategy
        cache.delete_many([cache_key_pattern])


def cache_template_fragment(fragment_name: str, vary_on: list, timeout: int = 300) -> Callable:
    """
    Cache template fragment.
    
    Args:
        fragment_name: Template fragment name
        vary_on: List of variables to vary cache on
        timeout: Cache timeout in seconds
        
    Returns:
        Decorator function
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = make_template_fragment_key(fragment_name, vary_on)
            
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


def clear_all_cache() -> None:
    """
    Clear all cache entries.
    """
    cache.clear()


def get_cache_stats() -> Dict[str, Any]:
    """
    Get cache statistics.
    
    Returns:
        Cache statistics dictionary
    """
    # This is a simplified implementation
    # In production, you might want to use cache-specific statistics
    return {
        'backend': getattr(settings, 'CACHES', {}).get('default', {}).get('BACKEND', 'unknown'),
        'location': getattr(settings, 'CACHES', {}).get('default', {}).get('LOCATION', 'unknown'),
    }


class CacheManager:
    """
    Cache manager for organized cache operations.
    """
    
    def __init__(self, prefix: str = ""):
        self.prefix = prefix
    
    def _get_key(self, key: str) -> str:
        """Get full cache key with prefix."""
        return f"{self.prefix}:{key}" if self.prefix else key
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        return cache.get(self._get_key(key))
    
    def set(self, key: str, value: Any, timeout: int = 300) -> None:
        """Set value in cache."""
        cache.set(self._get_key(key), value, timeout)
    
    def delete(self, key: str) -> None:
        """Delete value from cache."""
        cache.delete(self._get_key(key))
    
    def get_or_set(self, key: str, default: Any, timeout: int = 300) -> Any:
        """Get value from cache or set default."""
        return cache.get_or_set(self._get_key(key), default, timeout)
    
    def clear(self) -> None:
        """Clear all cache entries with this prefix."""
        # Note: This is a simplified approach
        # In production, you might want to use a more sophisticated approach
        cache.clear()
