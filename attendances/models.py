# attendances/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from core.base_models import TimeStampedModel
from core.choices import (
    ATTENDANCE_STATUS_CHOICES,
    PAYMENT_STATUS_CHOICES,
)
from events.models import Event
import secrets
import string


class AttendanceRecord(TimeStampedModel):
    """
    Model for tracking event attendance with payment and check-in.
    
    Financial Linkage (CFO):
    - Direct link to PaymentOrder enables reconciliation
    - Clear audit trail: payment → attendance → check-in
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attendance_records")
    user = models.ForeignKey(
        'users.UserProfile', 
        on_delete=models.CASCADE,
        related_name="attendance_records",
        help_text="User profile attending the event"
    )
    payment_order = models.ForeignKey(
        'payments.PaymentOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendance_records",
        help_text="Payment order that fulfilled this attendance (for paid events)"
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
            models.Index(fields=["payment_order"]),  # For tracing payment → attendance
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

    def validate_ticket_secret_for_checkin(self):
        """
        Validate ticket secret can be used for check-in.
        
        SECURITY ENFORCEMENT (MANDATORY):
        - ticket_secret can be validated ONLY IF:
          - event.is_paid == False (free event)
          OR
          - payment_order.status == "paid" (verified payment)
        
        Even if EVENT_ATTENDEE and ATTENDANCE_RECORD exist, this check
        prevents unpaid users from checking in to paid events.
        
        Raises:
            ValidationError: If payment is required but not verified
        """
        from core.exceptions import ValidationError
        
        # Free events: always allow
        if not self.event.is_paid:
            return True
        
        # Paid events: MUST have payment_order with status='paid'
        if not self.payment_order:
            raise ValidationError(
                "Payment verification failed. Cannot check in without confirmed payment.",
                code="PAYMENT_NOT_VERIFIED"
            )
        
        if self.payment_order.status != 'paid':
            raise ValidationError(
                f"Payment order status is '{self.payment_order.status}', not 'paid'. Cannot check in without confirmed payment.",
                code="PAYMENT_NOT_VERIFIED"
            )
        
        # Double-check payment_status field matches
        if self.payment_status != 'paid':
            raise ValidationError(
                "Payment verification failed. Payment status mismatch.",
                code="PAYMENT_NOT_VERIFIED"
            )
        
        return True
    
    def check_in(self):
        """
        Mark user as checked in.
        
        SECURITY ENFORCEMENT:
        - For paid events, validates payment_order.status == 'paid' before check-in
        - Prevents unpaid users from checking in even if records exist
        """
        if self.status == 'going':
            # SECURITY: Validate ticket secret and payment before check-in
            self.validate_ticket_secret_for_checkin()
            
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


class TicketSecret(TimeStampedModel):
    """Cryptographically secure ticket secrets for attendees"""
    attendance_record = models.OneToOneField(
        AttendanceRecord,
        on_delete=models.CASCADE,
        related_name="ticket_secret_obj"
    )
    secret_hash = models.TextField(help_text="Hashed ticket secret")
    secret_salt = models.TextField(help_text="Salt for hashing")
    is_redeemed = models.BooleanField(default=False, help_text="Whether ticket has been redeemed")
    redeemed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["is_redeemed"]),
        ]

    def __str__(self):
        return f"Ticket secret for {self.attendance_record.user} - {self.attendance_record.event.title}"

    def mark_redeemed(self):
        """Mark ticket as redeemed"""
        from django.utils import timezone
        self.is_redeemed = True
        self.redeemed_at = timezone.now()
        self.save(update_fields=['is_redeemed', 'redeemed_at', 'updated_at'])