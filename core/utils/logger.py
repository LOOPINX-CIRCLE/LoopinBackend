"""
Logging utilities for the Loopin Backend application.
"""

import logging
import logging.config
from typing import Optional, Dict, Any
from django.conf import settings


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    Get a configured logger instance.
    
    Args:
        name: Logger name (usually __name__)
        level: Optional log level override
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    
    if level:
        logger.setLevel(getattr(logging, level.upper()))
    
    return logger


def setup_logging(config: Optional[Dict[str, Any]] = None) -> None:
    """
    Setup logging configuration.
    
    Args:
        config: Optional logging configuration
    """
    if config is None:
        config = {
            'version': 1,
            'disable_existing_loggers': False,
            'formatters': {
                'verbose': {
                    'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
                    'style': '{',
                },
                'simple': {
                    'format': '{levelname} {message}',
                    'style': '{',
                },
            },
            'handlers': {
                'console': {
                    'level': 'INFO',
                    'class': 'logging.StreamHandler',
                    'formatter': 'simple',
                },
                'file': {
                    'level': 'DEBUG',
                    'class': 'logging.FileHandler',
                    'filename': 'logs/django.log',
                    'formatter': 'verbose',
                },
            },
            'loggers': {
                'django': {
                    'handlers': ['console', 'file'],
                    'level': 'INFO',
                    'propagate': True,
                },
                'core': {
                    'handlers': ['console', 'file'],
                    'level': 'DEBUG',
                    'propagate': True,
                },
            },
        }
    
    logging.config.dictConfig(config)


class StructuredLogger:
    """
    Structured logger for consistent log formatting.
    """
    
    def __init__(self, name: str):
        self.logger = get_logger(name)
    
    def _log(self, level: str, message: str, **kwargs) -> None:
        """Log with structured data."""
        extra = {k: v for k, v in kwargs.items() if v is not None}
        getattr(self.logger, level)(message, extra=extra)
    
    def debug(self, message: str, **kwargs) -> None:
        """Log debug message."""
        self._log('debug', message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        """Log info message."""
        self._log('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        """Log warning message."""
        self._log('warning', message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        """Log error message."""
        self._log('error', message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        """Log critical message."""
        self._log('critical', message, **kwargs)


def log_function_call(func_name: str, **kwargs) -> None:
    """
    Log function call with parameters.
    
    Args:
        func_name: Function name
        **kwargs: Function parameters
    """
    logger = get_logger('core.function_calls')
    logger.info(f"Function call: {func_name}", extra=kwargs)


def log_api_request(method: str, path: str, user_id: Optional[int] = None, **kwargs) -> None:
    """
    Log API request.
    
    Args:
        method: HTTP method
        path: Request path
        user_id: User ID (if authenticated)
        **kwargs: Additional request data
    """
    logger = get_logger('core.api_requests')
    logger.info(f"API request: {method} {path}", extra={
        'method': method,
        'path': path,
        'user_id': user_id,
        **kwargs
    })


def log_database_query(query: str, duration: float, **kwargs) -> None:
    """
    Log database query performance.
    
    Args:
        query: SQL query
        duration: Query duration in seconds
        **kwargs: Additional query data
    """
    logger = get_logger('core.database_queries')
    logger.info(f"Database query: {duration:.3f}s", extra={
        'query': query,
        'duration': duration,
        **kwargs
    })


def log_external_service_call(service: str, endpoint: str, duration: float, status_code: Optional[int] = None, **kwargs) -> None:
    """
    Log external service call.
    
    Args:
        service: Service name
        endpoint: API endpoint
        duration: Call duration in seconds
        status_code: HTTP status code
        **kwargs: Additional call data
    """
    logger = get_logger('core.external_services')
    logger.info(f"External service call: {service} {endpoint}", extra={
        'service': service,
        'endpoint': endpoint,
        'duration': duration,
        'status_code': status_code,
        **kwargs
    })
