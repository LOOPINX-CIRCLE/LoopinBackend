from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'
    verbose_name = 'User Notifications'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import notifications.signals
        except ImportError:
            pass
