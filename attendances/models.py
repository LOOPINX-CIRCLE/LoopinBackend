# attendances/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from core.base_models import TimeStampedModel
from core.choices import (
    ATTENDANCE_STATUS_CHOICES,
    PAYMENT_STATUS_CHOICES,
    OTP_LENGTH,
)
from events.models import Event
import secrets
import string


class AttendanceRecord(TimeStampedModel):
    """Model for tracking event attendance with payment and check-in"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attendance_records")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )
    status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_STATUS_CHOICES,
        default='going'
    )
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='unpaid'
    )
    ticket_secret = models.CharField(max_length=64, unique=True, blank=True)
    seats = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    checked_in_at = models.DateTimeField(null=True, blank=True)
    checked_out_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("event", "user")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["payment_status"]),
            models.Index(fields=["event", "user"]),
            models.Index(fields=["checked_in_at"]),
        ]

    def __str__(self):
        return f"{self.user} - {self.event.title} ({self.status})"

    def save(self, *args, **kwargs):
        if not self.ticket_secret:
            self.ticket_secret = self.generate_ticket_secret()
        super().save(*args, **kwargs)

    def generate_ticket_secret(self):
        """Generate a unique ticket secret for this attendance"""
        return ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

    def check_in(self):
        """Mark user as checked in"""
        if self.status == 'going':
            from django.utils import timezone
            self.checked_in_at = timezone.now()
            self.status = 'checked_in'
            self.save(update_fields=['checked_in_at', 'status', 'updated_at'])
            
            # Track check-in analytics
            try:
                from analytics.tracker import AnalyticsTracker
                AnalyticsTracker.track_attendance_checkin(self.user, self, self.event)
            except ImportError:
                pass  # Analytics module not available

    def check_out(self):
        """Mark user as checked out"""
        if self.status == 'checked_in':
            from django.utils import timezone
            self.checked_out_at = timezone.now()
            self.status = 'not_going'
            self.save(update_fields=['checked_out_at', 'status', 'updated_at'])
            
            # Track check-out analytics
            try:
                from analytics.tracker import AnalyticsTracker
                AnalyticsTracker.track_attendance_checkout(self.user, self, self.event)
            except ImportError:
                pass  # Analytics module not available

    @property
    def is_checked_in(self):
        """Check if user is currently checked in"""
        return self.checked_in_at is not None and self.checked_out_at is None

    @property
    def attendance_duration(self):
        """Calculate attendance duration if checked out"""
        if self.checked_in_at and self.checked_out_at:
            return self.checked_out_at - self.checked_in_at
        return None


class AttendanceOTP(TimeStampedModel):
    """Model for generating OTPs for event check-in"""
    attendance_record = models.ForeignKey(
        AttendanceRecord, 
        on_delete=models.CASCADE, 
        related_name="checkin_otps"
    )
    otp_code = models.CharField(max_length=OTP_LENGTH)
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["otp_code"]),
            models.Index(fields=["is_used"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"Check-in OTP for {self.attendance_record.user}"

    def is_expired(self):
        """Check if OTP has expired"""
        from django.utils import timezone
        return timezone.now() > self.expires_at

    def is_valid(self):
        """Check if OTP is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired()