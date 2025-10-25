from django.apps import AppConfig


class AuditConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'audit'
    verbose_name = 'System Auditing'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import audit.signals
        except ImportError:
            pass
