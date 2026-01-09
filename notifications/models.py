# notifications/models.py
from django.db import models
from django.conf import settings
import uuid
from core.base_models import TimeStampedModel
from core.choices import NOTIFICATION_TYPE_CHOICES


class UserDevice(TimeStampedModel):
    """
    Model for mapping USER_PROFILE to OneSignal player IDs.
    
    One user profile can have multiple devices (iOS, Android).
    Player IDs may rotate - old devices are deactivated, not deleted.
    """
    user_profile = models.ForeignKey(
        'users.UserProfile',
        on_delete=models.CASCADE,
        related_name='devices',
        help_text="User profile that owns this device"
    )
    onesignal_player_id = models.CharField(
        max_length=255,
        unique=True,
        db_index=True,
        help_text="OneSignal player ID for this device"
    )
    platform = models.CharField(
        max_length=20,
        choices=[('ios', 'iOS'), ('android', 'Android')],
        help_text="Device platform"
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this device is active (false if player ID invalid)"
    )
    last_seen_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Last time this device was seen/used"
    )

    class Meta:
        indexes = [
            models.Index(fields=["user_profile", "is_active"]),
            models.Index(fields=["onesignal_player_id"]),
            models.Index(fields=["is_active", "last_seen_at"]),
        ]
        unique_together = [["user_profile", "onesignal_player_id"]]
        ordering = ['-last_seen_at', '-created_at']

    def __str__(self):
        return f"{self.user_profile} - {self.platform} ({self.onesignal_player_id[:8]}...)"

    def deactivate(self):
        """Deactivate this device (e.g., if OneSignal returns invalid player ID)"""
        self.is_active = False
        self.save(update_fields=['is_active', 'updated_at'])

    def reactivate(self):
        """Reactivate this device"""
        self.is_active = True
        self.save(update_fields=['is_active', 'updated_at'])


class Notification(TimeStampedModel):
    """Model for in-app notifications to users"""
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Public UUID")
    recipient = models.ForeignKey(
        'users.UserProfile', 
        on_delete=models.CASCADE,
        related_name="received_notifications",
        help_text="User profile receiving the notification"
    )
    sender = models.ForeignKey(
        'users.UserProfile', 
        null=True, 
        blank=True,
        on_delete=models.SET_NULL,
        related_name="sent_notifications",
        help_text="User profile sending the notification (optional)"
    )
    type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES,
        help_text="Type of notification"
    )
    title = models.CharField(max_length=200, help_text="Notification title")
    message = models.TextField(help_text="Notification message")
    reference_type = models.CharField(max_length=100, blank=True, help_text="Related model type (e.g., Event, Payment)")
    reference_id = models.PositiveIntegerField(null=True, blank=True, help_text="Related object ID")
    is_read = models.BooleanField(default=False, help_text="Whether notification has been read")
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional notification data")

    class Meta:
        indexes = [
            models.Index(fields=["recipient"]),
            models.Index(fields=["sender"]),
            models.Index(fields=["type"]),
            models.Index(fields=["is_read"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["recipient", "is_read"]),
            models.Index(fields=["reference_type", "reference_id"]),
        ]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.type} - {self.recipient.username}"

    @property
    def is_unread(self):
        """Check if notification is unread"""
        return not self.is_read

    def mark_as_read(self):
        """Mark notification as read"""
        self.is_read = True
        self.save(update_fields=['is_read', 'updated_at'])

    def mark_as_unread(self):
        """Mark notification as unread"""
        self.is_read = False
        self.save(update_fields=['is_read', 'updated_at'])