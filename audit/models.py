# audit/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from core.base_models import TimeStampedModel
from core.choices import (
    AUDIT_ACTION_CHOICES,
)


class AuditLog(TimeStampedModel):
    """Model for tracking sensitive actions and changes in the system"""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        on_delete=models.SET_NULL,
        related_name="audit_logs"
    )
    action = models.CharField(
        max_length=50,
        choices=AUDIT_ACTION_CHOICES
    )
    object_type = models.CharField(max_length=100)
    object_id = models.CharField(max_length=50, blank=True)
    object_uuid = models.CharField(max_length=36, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    session_key = models.CharField(max_length=40, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    old_values = models.JSONField(default=dict, blank=True)
    new_values = models.JSONField(default=dict, blank=True)
    severity = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium'
    )
    is_successful = models.BooleanField(default=True)
    error_message = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["action"]),
            models.Index(fields=["object_type"]),
            models.Index(fields=["object_id"]),
            models.Index(fields=["severity"]),
            models.Index(fields=["is_successful"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["user", "action"]),
            models.Index(fields=["object_type", "object_id"]),
        ]

    def __str__(self):
        return f"{self.action} on {self.object_type} by {self.user or 'System'}"

    @classmethod
    def log_action(cls, user, action, object_type, object_id=None, **kwargs):
        """Convenience method to create audit log entries"""
        return cls.objects.create(
            user=user,
            action=action,
            object_type=object_type,
            object_id=object_id,
            **kwargs
        )

    @classmethod
    def log_login(cls, user, ip_address=None, user_agent=None, is_successful=True):
        """Log user login attempts"""
        return cls.objects.create(
            user=user,
            action='login',
            object_type='user',
            object_id=str(user.id) if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            is_successful=is_successful,
            severity='medium'
        )

    @classmethod
    def log_logout(cls, user, ip_address=None, user_agent=None):
        """Log user logout"""
        return cls.objects.create(
            user=user,
            action='logout',
            object_type='user',
            object_id=str(user.id) if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            severity='low'
        )

    @classmethod
    def log_password_change(cls, user, ip_address=None, user_agent=None):
        """Log password changes"""
        return cls.objects.create(
            user=user,
            action='password_change',
            object_type='user',
            object_id=str(user.id) if user else None,
            ip_address=ip_address,
            user_agent=user_agent,
            severity='high'
        )

    @classmethod
    def log_profile_update(cls, user, old_values=None, new_values=None, ip_address=None):
        """Log profile updates"""
        return cls.objects.create(
            user=user,
            action='profile_update',
            object_type='user_profile',
            object_id=str(user.id) if user else None,
            ip_address=ip_address,
            old_values=old_values or {},
            new_values=new_values or {},
            severity='medium'
        )

    @classmethod
    def log_event_creation(cls, user, event, ip_address=None):
        """Log event creation"""
        return cls.objects.create(
            user=user,
            action='create',
            object_type='event',
            object_id=str(event.id),
            object_uuid=str(event.uuid) if hasattr(event, 'uuid') else '',
            ip_address=ip_address,
            severity='medium'
        )

    @classmethod
    def log_payment(cls, user, payment_order, action, ip_address=None):
        """Log payment-related actions"""
        return cls.objects.create(
            user=user,
            action=action,
            object_type='payment_order',
            object_id=str(payment_order.id),
            object_uuid=str(payment_order.uuid) if hasattr(payment_order, 'uuid') else '',
            ip_address=ip_address,
            severity='high'
        )

    @property
    def is_critical(self):
        """Check if this is a critical audit log entry"""
        return self.severity == 'critical'

    @property
    def is_failed_action(self):
        """Check if this represents a failed action"""
        return not self.is_successful

    @property
    def has_changes(self):
        """Check if this audit log contains field changes"""
        return bool(self.old_values or self.new_values)


class AuditLogSummary(TimeStampedModel):
    """Model for storing audit log summaries and statistics"""
    date = models.DateField()
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        null=True, 
        on_delete=models.SET_NULL,
        related_name="audit_summaries"
    )
    action = models.CharField(max_length=50)
    count = models.PositiveIntegerField(default=0)
    successful_count = models.PositiveIntegerField(default=0)
    failed_count = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("date", "user", "action")
        indexes = [
            models.Index(fields=["date"]),
            models.Index(fields=["user"]),
            models.Index(fields=["action"]),
            models.Index(fields=["date", "user"]),
        ]

    def __str__(self):
        return f"{self.date} - {self.user} - {self.action} ({self.count})"

    @property
    def success_rate(self):
        """Calculate success rate for this action"""
        if self.count == 0:
            return 0
        return (self.successful_count / self.count) * 100