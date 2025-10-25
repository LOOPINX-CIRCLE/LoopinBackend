from django.apps import AppConfig
import posthog
from django.conf import settings
import os
import logging

logger = logging.getLogger(__name__)


class AnalyticsConfig(AppConfig):
    name = 'analytics'
    default_auto_field = 'django.db.models.BigAutoField'

    def ready(self):
        """Initialize analytics when Django starts"""
        # Configure PostHog
        posthog.api_key = os.getenv('POSTHOG_API_KEY', '')
        posthog.host = os.getenv('POSTHOG_HOST', 'https://us.i.posthog.com')
        
        # Optional: Set debug mode
        if settings.DEBUG:
            posthog.debug = True
            
        # Import signals to register them
        try:
            from . import signals
            logger.info("Analytics signals registered successfully")
        except ImportError as e:
            logger.warning(f"Failed to import analytics signals: {e}")
        
        # Initialize AI services
        try:
            from .ai_services import AIServiceManager
            AIServiceManager.initialize()
            logger.info("AI services initialized successfully")
        except ImportError as e:
            logger.warning(f"Failed to initialize AI services: {e}")