from django.apps import AppConfig


class AttendancesConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'attendances'
    verbose_name = 'Attendance Tracking'
    
    def ready(self):
        """Import signals when app is ready."""
        try:
            import attendances.signals
        except ImportError:
            pass
