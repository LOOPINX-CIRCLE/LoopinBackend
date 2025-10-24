"""
Base Django settings for loopin_backend project.
This file contains common settings shared across all environments.
"""

import os
from pathlib import Path
from decouple import config
import dj_database_url

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-rq1k3nfrru@$ds6bwf$t&3hk*s7bg5ef3it&o@s*6_jbbbfp(j')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'rest_framework',
    'corsheaders',
]

LOCAL_APPS = [
    'users',
    'events',
    'attendances',
    'payments',
    'notifications',
    'audit',
    'analytics',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'posthog.integrations.django.PosthogContextMiddleware',
    'analytics.middleware.AnalyticsMiddleware',  # Custom analytics middleware
]

ROOT_URLCONF = 'loopin_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# ASGI application
ASGI_APPLICATION = 'loopin_backend.asgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
# Import custom database utility for IPv4/IPv6 handling
from loopin_backend.db_utils import get_database_config

DATABASES = {
    'default': get_database_config(
        database_url=config('DATABASE_URL', default='sqlite:///db.sqlite3')
    )
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'  # India timezone
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.2/howto/static-files/
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
# Only add STATICFILES_DIRS if the static directory exists
STATICFILES_DIRS = []
if (BASE_DIR / 'static').exists():
    STATICFILES_DIRS.append(BASE_DIR / 'static')

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/5.2/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
}

# JWT Settings
JWT_SECRET_KEY = config('JWT_SECRET_KEY', default=SECRET_KEY)
JWT_ALGORITHM = config('JWT_ALGORITHM', default='HS256')
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = config('JWT_ACCESS_TOKEN_EXPIRE_MINUTES', default=30, cast=int)

# CORS settings
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:3000').split(',')

# Security settings
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# PostHog Analytics Configuration
POSTHOG_API_KEY = config('POSTHOG_API_KEY', default='')
POSTHOG_HOST = config('POSTHOG_HOST', default='https://us.i.posthog.com')

# PostHog Middleware Configuration
POSTHOG_MW_CAPTURE_EXCEPTIONS = True

def add_user_tags(request):
    """Add user tags to PostHog events"""
    tags = {}
    if hasattr(request, 'user') and request.user.is_authenticated:
        tags['user_id'] = request.user.id
        tags['username'] = request.user.username
        if hasattr(request.user, 'profile'):
            profile = request.user.profile
            tags['is_verified'] = profile.is_verified
            tags['gender'] = profile.gender
            tags['location'] = profile.location
    return tags

POSTHOG_MW_EXTRA_TAGS = add_user_tags

def should_track_request(request):
    """Filter requests to track"""
    # Don't track health checks, admin, or static files
    if request.path.startswith(('/health', '/admin', '/static', '/media')):
        return False
    return True

POSTHOG_MW_REQUEST_FILTER = should_track_request

def clean_tags(tags):
    """Clean and modify default tags"""
    # Remove sensitive data
    tags.pop('user_agent', None)
    return tags

POSTHOG_MW_TAG_MAP = clean_tags

# Analytics Configuration
ANALYTICS_ENABLED = config('ANALYTICS_ENABLED', default=True, cast=bool)
ANALYTICS_RETENTION_DAYS = config('ANALYTICS_RETENTION_DAYS', default=365, cast=int)
ANALYTICS_BATCH_SIZE = config('ANALYTICS_BATCH_SIZE', default=1000, cast=int)

# AI Services Configuration
OPENAI_API_KEY = config('OPENAI_API_KEY', default='')
AI_SERVICES_ENABLED = config('AI_SERVICES_ENABLED', default=True, cast=bool)

# Celery Configuration for Analytics
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default='redis://localhost:6379/0')
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Analytics Task Configuration
CELERY_BEAT_SCHEDULE = {
    'process-daily-metrics': {
        'task': 'analytics.tasks.process_daily_metrics_calculation',
        'schedule': 60.0 * 60.0,  # Every hour
    },
    'generate-user-insights': {
        'task': 'analytics.tasks.generate_predictive_insights',
        'schedule': 60.0 * 60.0 * 6,  # Every 6 hours
    },
    'detect-anomalies': {
        'task': 'analytics.tasks.detect_anomalies_batch',
        'schedule': 60.0 * 30,  # Every 30 minutes
    },
    'cleanup-analytics-data': {
        'task': 'analytics.tasks.cleanup_old_analytics_data',
        'schedule': 60.0 * 60.0 * 24,  # Daily
    },
    'generate-daily-summary': {
        'task': 'analytics.tasks.generate_daily_insights_summary',
        'schedule': 60.0 * 60.0 * 24,  # Daily
    },
}
