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
    
    # Campaign tracking (optional - only for campaign-driven notifications)
    campaign = models.ForeignKey(
        'Campaign',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='notifications',
        help_text="Campaign that triggered this notification (if applicable)"
    )

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
        return f"{self.type} - {self.recipient.name or self.recipient.phone_number}"

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


class TemplateVariableHint(TimeStampedModel):
    """
    Variable hints for notification templates - UI-based, no JSON!
    
    Each variable gets its own record with clear help text.
    Marketing team can easily understand and edit these.
    """
    template = models.ForeignKey(
        'NotificationTemplate',
        on_delete=models.CASCADE,
        related_name='variable_hints_list',
        help_text="Template this hint belongs to"
    )
    variable_name = models.CharField(
        max_length=100,
        help_text="Variable name (without braces, e.g., 'event_name')"
    )
    help_text = models.TextField(
        help_text="Help text explaining what this variable is for (e.g., 'Name of the event')"
    )
    
    class Meta:
        verbose_name = "Template Variable Hint"
        verbose_name_plural = "Template Variable Hints"
        unique_together = [['template', 'variable_name']]
        ordering = ['variable_name']
    
    def __str__(self):
        return f"{self.template.name} - {self.variable_name}"


class NotificationTemplate(TimeStampedModel):
    """
    Dynamic Notification Template - Created by admins/marketing team
    
    Allows creating custom notification templates without code changes.
    Templates can be reused across multiple campaigns.
    
    IMMUTABILITY RULES:
    - Templates become immutable (locked) once used in at least one campaign
    - Content fields (title, body, target_screen, notification_type) cannot be edited when locked
    - Version is incremented on meaningful content changes
    - Campaigns store immutable template_version snapshot for audit trail
    
    NOTE: This is IDEA-2 (Campaign System). IDEA-1 (Automated System Notifications)
    uses the templates in notifications/services/messages.py and works independently.
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Public UUID")
    name = models.CharField(
        max_length=255,
        unique=True,
        help_text="Template name (e.g., 'Profile Completion Reminder')"
    )
    key = models.SlugField(
        max_length=100,
        unique=True,
        db_index=True,
        help_text="Unique template key (e.g., 'profile_completion_reminder')"
    )
    title = models.CharField(
        max_length=200,
        help_text="Notification title with {{variable}} placeholders (e.g., 'Complete Your Profile!' or 'Hi {{name}}, check out {{event_name}}!')"
    )
    body = models.TextField(
        help_text="Notification message with {{variable}} placeholders (e.g., 'Hi {{name}}, complete your profile to join events!' or 'New event: {{event_name}} by {{host_name}}')"
    )
    target_screen = models.CharField(
        max_length=100,
        default="home",
        help_text="Mobile app screen to navigate to when user taps notification (e.g., 'profile', 'event_detail', 'home')"
    )
    notification_type = models.CharField(
        max_length=50,
        choices=NOTIFICATION_TYPE_CHOICES,
        default='system',
        help_text="Type of notification (affects how it appears to users)"
    )
    
    # Versioning (for audit trail and analytics)
    version = models.PositiveIntegerField(
        default=1,
        db_index=True,
        help_text="Template version number. Incremented on content changes. Campaigns store immutable version snapshot."
    )
    
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this template is available for use in campaigns"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='templates_created',
        help_text="Admin user who created this template"
    )
    
    class Meta:
        verbose_name = "Notification Template"
        verbose_name_plural = "Notification Templates"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["key"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["key", "version"]),
        ]
        unique_together = [['key', 'version']]  # Each version must be unique per key
    
    def __str__(self):
        return f"{self.name} v{self.version} ({self.key})"
    
    @property
    def is_immutable(self):
        """
        Check if template is locked (used in at least one campaign).
        
        IMMUTABILITY RULE:
        - Once a template is used in any campaign (even draft/previewed),
          its content fields (title, body, target_screen, notification_type) cannot be changed
        - This ensures historical campaigns always reference the exact template they were created with
        - Admins must create a new version to make changes (which creates a new template record)
        """
        return self.campaigns.exists()
    
    @property
    def is_content_locked(self):
        """Alias for is_immutable for clarity in admin UI"""
        return self.is_immutable
    
    def get_required_variables(self):
        """Extract required variables from title and body"""
        import re
        title_vars = set(re.findall(r'\{\{(\w+)\}\}', self.title))
        body_vars = set(re.findall(r'\{\{(\w+)\}\}', self.body))
        return sorted(title_vars | body_vars)
    
    def get_variable_hints_dict(self):
        """Get variable hints as a dictionary (for backward compatibility)"""
        return {hint.variable_name: hint.help_text for hint in self.variable_hints_list.all()}


class Campaign(TimeStampedModel):
    """
    Dynamic, Admin-Driven Notification Campaign System
    
    A campaign represents a single admin-initiated notification send.
    Campaigns are immutable once sent and fully auditable.
    
    Now supports:
    - UI-based audience selection (no JSON required)
    - Dynamic templates (created in admin)
    """
    CAMPAIGN_STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('previewed', 'Previewed'),
        ('scheduled', 'Scheduled'),
        ('sending', 'Sending'),
        ('sent', 'Sent'),
        ('cancelled', 'Cancelled'),
        ('failed', 'Failed'),
    ]
    
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Public UUID")
    name = models.CharField(
        max_length=255,
        help_text="Human-readable campaign name (e.g., 'Profile Incomplete Reminder - Bangalore Music')"
    )
    description = models.TextField(
        blank=True,
        help_text="Optional description explaining why this campaign was created"
    )
    
    # Template selection with versioning (immutable snapshot)
    template = models.ForeignKey(
        'NotificationTemplate',
        on_delete=models.PROTECT,
        related_name='campaigns',
        null=True,
        blank=True,
        help_text="Notification template to use (create new templates in Notification Templates)"
    )
    template_version = models.PositiveIntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="Immutable template version snapshot at campaign creation time. Used for audit trail and analytics."
    )
    # Template variables stored as JSON internally but edited via UI
    template_variables = models.JSONField(
        default=dict,
        blank=True,
        help_text="Variable values (auto-populated from UI fields, not directly edited)"
    )
    
    # UI-based audience selection fields (stored as JSON for rule engine compatibility)
    # These are populated from form fields, not directly edited
    audience_rules = models.JSONField(
        default=dict,
        help_text="Audience selection rules (auto-generated from UI fields)"
    )
    
    # Status and execution tracking
    status = models.CharField(
        max_length=20,
        choices=CAMPAIGN_STATUS_CHOICES,
        default='draft',
        db_index=True,
        help_text="Current campaign status"
    )
    
    # Preview information (computed before sending)
    preview_count = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Number of users matching audience rules (computed during preview)"
    )
    preview_computed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When preview was last computed"
    )
    
    # Execution tracking
    sent_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When campaign was actually sent (null if not sent yet)"
    )
    sent_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns_sent',
        help_text="Admin user who sent this campaign"
    )
    
    # Results (populated after execution)
    total_sent = models.PositiveIntegerField(
        default=0,
        help_text="Total notifications successfully sent"
    )
    total_failed = models.PositiveIntegerField(
        default=0,
        help_text="Total notifications that failed to send"
    )
    execution_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Additional execution metadata (errors, warnings, batch info)"
    )
    
    # Safety and audit
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='campaigns_created',
        help_text="Admin user who created this campaign"
    )
    cancelled_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="When campaign was cancelled (if applicable)"
    )
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='campaigns_cancelled',
        help_text="Admin user who cancelled this campaign"
    )
    cancellation_reason = models.TextField(
        blank=True,
        help_text="Reason for cancellation (if applicable)"
    )
    
    class Meta:
        verbose_name = "Notification Campaign"
        verbose_name_plural = "Notification Campaigns"
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["template"]),
            models.Index(fields=["created_at"]),
            models.Index(fields=["sent_at"]),
            models.Index(fields=["created_by"]),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        """
        Override save to capture template version snapshot on creation.
        
        IMMUTABILITY RULE:
        - On campaign creation, store immutable template_version snapshot
        - This ensures campaigns always reference the exact template version they were created with
        - Template version cannot be changed after campaign creation
        """
        # Capture template version on creation or if template changed
        if self.pk is None or 'template' in kwargs.get('update_fields', []):
            if self.template:
                self.template_version = self.template.version
        super().save(*args, **kwargs)
    
    @property
    def is_immutable(self):
        """
        Check if campaign can be modified.
        
        IMMUTABILITY RULE:
        - Campaigns are immutable once sent or sending
        - Draft/previewed/scheduled campaigns can be edited
        - Once sent, all fields are locked for audit trail
        """
        return self.status in ['sent', 'sending', 'cancelled']
    
    @property
    def can_be_sent(self):
        """Check if campaign is in a state that allows sending"""
        return self.status in ['draft', 'previewed', 'scheduled']
    
    @property
    def can_be_executed(self):
        """
        Check if campaign can be executed (idempotency guard).
        
        IDEMPOTENCY RULE:
        - Campaign can only be executed once
        - Must be in draft/previewed/scheduled status
        - Must have been previewed (preview_count set)
        - Once sent or sending, cannot be re-executed (even if failed)
        """
        if self.status in ['sent', 'sending']:
            return False
        return self.status in ['draft', 'previewed', 'scheduled'] and self.preview_count is not None
    
    def cancel(self, user, reason=""):
        """Cancel a campaign (only if not already sent)"""
        if self.is_immutable:
            raise ValueError(f"Cannot cancel campaign in status: {self.status}")
        from django.utils import timezone
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.cancelled_by = user
        self.cancellation_reason = reason
        self.save(update_fields=['status', 'cancelled_at', 'cancelled_by', 'cancellation_reason', 'updated_at'])


class CampaignExecution(TimeStampedModel):
    """
    Individual notification send tracking for a campaign.
    
    Links each Notification record to its parent Campaign for audit purposes.
    """
    campaign = models.ForeignKey(
        Campaign,
        on_delete=models.CASCADE,
        related_name='executions',
        help_text="Parent campaign"
    )
    notification = models.ForeignKey(
        Notification,
        on_delete=models.CASCADE,
        related_name='campaign_executions',
        help_text="Notification record created for this execution"
    )
    user_profile = models.ForeignKey(
        'users.UserProfile',
        on_delete=models.CASCADE,
        related_name='campaign_notifications',
        help_text="User profile who received this notification"
    )
    
    # Delivery tracking
    sent_successfully = models.BooleanField(
        default=False,
        db_index=True,
        help_text="Whether notification was successfully delivered via OneSignal"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Error message if delivery failed"
    )
    onesignal_response = models.JSONField(
        default=dict,
        blank=True,
        help_text="Raw OneSignal API response (for debugging)"
    )
    delivered_at = models.DateTimeField(
        null=True,
        blank=True,
        db_index=True,
        help_text="When notification was actually delivered"
    )
    
    class Meta:
        verbose_name = "Campaign Execution"
        verbose_name_plural = "Campaign Executions"
        indexes = [
            models.Index(fields=["campaign", "sent_successfully"]),
            models.Index(fields=["user_profile", "sent_successfully"]),
            models.Index(fields=["delivered_at"]),
        ]
        ordering = ['-created_at']
    
    def __str__(self):
        status = "✅" if self.sent_successfully else "❌"
        return f"{status} {self.campaign.name} → {self.user_profile}"