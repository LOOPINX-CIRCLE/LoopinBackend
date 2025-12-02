from django.apps import AppConfig


class AnalyticsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'analytics'
    
    def ready(self):
        """Import admin when app is ready to register dashboard URLs"""
        try:
            import analytics.admin  # noqa: F401
        except ImportError:
            pass  # Admin module not available