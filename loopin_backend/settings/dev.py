"""
Development settings for loopin_backend project.
"""

from .base import *

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

# Allow all hosts in development for easier testing
ALLOWED_HOSTS = ['*']

# Development-specific apps
INSTALLED_APPS += [
    # Add development-specific apps here if needed
]

# Development-specific middleware
MIDDLEWARE += [
    # Add development-specific middleware here if needed
]

# Database for development (can override base settings)
# Uncomment if you want different database settings for dev
# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.sqlite3',
#         'NAME': BASE_DIR / 'db.sqlite3',
#     }
# }

# Development logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'api': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# CORS settings for development - Allow all origins
CORS_ALLOW_ALL_ORIGINS = True  # Only for development

# Email backend for development
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
