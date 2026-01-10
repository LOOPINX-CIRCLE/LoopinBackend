from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
import random
import string
import uuid

from core.base_models import TimeStampedModel
from core.choices import (
    GENDER_CHOICES,
    OTP_STATUS_CHOICES,
    OTP_TYPE_CHOICES,
    OTP_VALIDITY_MINUTES,
    OTP_MAX_ATTEMPTS,
    OTP_LENGTH,
    MIN_PROFILE_PICTURES,
    MAX_PROFILE_PICTURES,
)

# Create your models here.

class UserProfile(TimeStampedModel):
    """Extended user profile model for normal users"""
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Public UUID")
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Basic profile information
    name = models.CharField(max_length=100, blank=True, help_text="Full name of the user")
    phone_number = models.CharField(max_length=15, blank=True, help_text="Contact phone number")
    
    # Additional profile details
    bio = models.TextField(max_length=500, blank=True, help_text="User biography")
    location = models.CharField(max_length=100, blank=True, help_text="User location")
    birth_date = models.DateField(null=True, blank=True, help_text="Date of birth")
    
    # New required fields
    gender = models.CharField(
        max_length=20, 
        choices=GENDER_CHOICES,
        blank=True, 
        help_text="User gender"
    )
    event_interests = models.ManyToManyField(
        'EventInterest', 
        blank=True, 
        help_text="User's event interests (1-5 selections required)"
    )
    profile_pictures = models.JSONField(
        default=list, 
        blank=True, 
        help_text=f"List of profile picture URLs ({MIN_PROFILE_PICTURES}-{MAX_PROFILE_PICTURES} pictures required)"
    )
    
    # Profile status
    is_verified = models.BooleanField(default=False, help_text="Whether the user profile is verified")
    is_active = models.BooleanField(default=True, help_text="Whether the user profile is active")
    
    # Waitlist state tracking (mirrors Django User.is_active flag)
    waitlist_started_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when the user was first placed on the waitlist"
    )
    waitlist_promote_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Scheduled promotion time from waitlist to active state"
    )
    
    # Additional fields from ERD
    metadata = models.JSONField(default=dict, blank=True, help_text="Additional metadata")

    def __str__(self):
        return f"{self.name} ({self.phone_number})"

    def save(self, *args, **kwargs):
        """Override save to track profile completion"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Track profile completion analytics
        if not is_new:  # Only track updates, not initial creation
            try:
                from analytics.tracker import AnalyticsTracker
                profile_data = {
                    'name': self.name,
                    'bio': self.bio,
                    'location': self.location,
                    'gender': self.gender,
                    'birth_date': self.birth_date,
                    'profile_pictures': self.profile_pictures,
                    'interests': list(self.event_interests.values_list('name', flat=True))
                }
                AnalyticsTracker.track_profile_completion(self.user, profile_data)
            except ImportError:
                pass  # Analytics module not available

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ['-created_at']


class EventInterest(TimeStampedModel):
    """Model for event interests/categories"""
    name = models.CharField(max_length=100, unique=True, help_text="Name of the event interest")
    slug = models.SlugField(max_length=100, unique=True, blank=True, help_text="URL-friendly slug")
    is_active = models.BooleanField(default=True, help_text="Whether this interest is active")
    
    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
            # Ensure unique slug
            original_slug = self.slug
            count = 1
            while EventInterest.objects.filter(slug=self.slug).exclude(pk=self.pk if self.pk is not None else None).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = "Event Interest"
        verbose_name_plural = "Event Interests"
        ordering = ['name']


class PhoneOTP(TimeStampedModel):
    """
    Model for storing phone number OTP verification for normal users (customers).
    
    Used by USER_PROFILE (normal users) for phone-based authentication:
    - Signup (new customer registration)
    - Login (existing customer authentication)
    - Password reset
    - Phone verification
    - Transaction security
    
    Note: Admin users (AUTH_USER with is_staff=True) typically don't use phone OTP.
    Phone number links to USER_PROFILE.phone_number for normal users.
    """
    phone_number = models.CharField(
        max_length=15, 
        unique=True,
        help_text="Phone number used by normal users (customers) for authentication. Links to USER_PROFILE.phone_number."
    )
    otp_code = models.CharField(max_length=6)
    otp_type = models.CharField(
        max_length=20,
        choices=OTP_TYPE_CHOICES,
        default='signup',
        help_text="Type of OTP for normal users (signup, login, password_reset, phone_verification, transaction)"
    )
    status = models.CharField(
        max_length=20,
        choices=OTP_STATUS_CHOICES,
        default='pending',
        help_text="OTP verification status"
    )
    is_verified = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # OTP expires in configured minutes
            self.expires_at = timezone.now() + timedelta(minutes=OTP_VALIDITY_MINUTES)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def generate_otp(self):
        """Generate a configured-length OTP"""
        self.otp_code = ''.join(random.choices(string.digits, k=OTP_LENGTH))
        self.expires_at = timezone.now() + timedelta(minutes=OTP_VALIDITY_MINUTES)
        self.attempts = 0
        self.is_verified = False
        self.status = 'pending'
    
    def verify_otp(self, otp_code):
        """Verify the OTP code"""
        if self.is_expired():
            self.status = 'expired'
            self.save(update_fields=['status', 'updated_at'])
            return False, "OTP has expired"
        
        if self.attempts >= OTP_MAX_ATTEMPTS:
            self.status = 'failed'
            self.save(update_fields=['status', 'updated_at'])
            return False, "Too many attempts. Please request a new OTP"
        
        if self.otp_code == otp_code:
            self.is_verified = True
            self.status = 'verified'
            self.save(update_fields=['is_verified', 'status', 'updated_at'])
            return True, "OTP verified successfully"
        else:
            self.attempts += 1
            self.save(update_fields=['attempts', 'updated_at'])
            return False, f"Invalid OTP. {OTP_MAX_ATTEMPTS - self.attempts} attempts remaining"
    
    def __str__(self):
        return f"OTP for {self.phone_number}"
    
    class Meta:
        verbose_name = "Phone OTP"
        verbose_name_plural = "Phone OTPs"
        ordering = ['-created_at']


class HostLead(models.Model):
    """Model for storing 'Become a Host' lead information"""
    first_name = models.CharField(max_length=100, help_text="First name of the potential host")
    last_name = models.CharField(max_length=100, help_text="Last name of the potential host")
    phone_number = models.CharField(max_length=20, unique=True, help_text="Phone number of the potential host")
    message = models.TextField(blank=True, help_text="Optional message from the potential host")
    
    # Additional fields for tracking
    is_contacted = models.BooleanField(default=False, help_text="Whether the lead has been contacted")
    is_converted = models.BooleanField(default=False, help_text="Whether the lead became a host")
    notes = models.TextField(blank=True, help_text="Internal notes about the lead")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.phone_number})"
    
    class Meta:
        verbose_name = "Host Lead"
        verbose_name_plural = "Host Leads"
        ordering = ['-created_at']


class HostLeadWhatsAppTemplate(models.Model):
    """
    Recommended WhatsApp message snippet for host leads.

    Only two business-managed fields are required:
    - ``name``: short identifier used in the admin picker
    - ``message``: text injected into template variable {{2}}
    """

    name = models.CharField(
        max_length=120,
        unique=True,
        help_text="Short identifier for the marketing message (e.g., 'Intro Message').",
    )
    message = models.TextField(
        help_text="Pre-approved copy inserted into template variable {{2}}.",
    )

    class Meta:
        verbose_name = "Host Lead WhatsApp Template"
        verbose_name_plural = "Host Lead WhatsApp Templates"
        ordering = ['name']
    
    def __str__(self):
        return self.name


class HostLeadWhatsAppMessage(TimeStampedModel):
    """Log of WhatsApp messages sent to host leads through the admin panel"""
    
    STATUS_CHOICES = (
        ("queued", "Queued / Sending"),
        ("sent", "Sent"),
        ("delivered", "Delivered"),
        ("undelivered", "Undelivered"),
        ("failed", "Failed"),
        ("test-mode", "Test Mode"),
    )
    
    lead = models.ForeignKey(
        HostLead,
        on_delete=models.CASCADE,
        related_name="whatsapp_messages",
        help_text="Host lead recipient"
    )
    template = models.ForeignKey(
        HostLeadWhatsAppTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="messages",
        help_text="Template used (if any)"
    )
    content_sid = models.CharField(
        max_length=80,
        help_text="Twilio Content Template SID used for this send"
    )
    variables = models.JSONField(
        default=dict,
        help_text="Content variables sent to Twilio (e.g., {'1': 'Name', '2': 'Message'})"
    )
    body_variable = models.TextField(
        help_text="Final text value used for variable {{2}}"
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="queued",
        help_text="Latest known delivery status"
    )
    twilio_sid = models.CharField(
        max_length=64,
        blank=True,
        help_text="Twilio message SID for tracking"
    )
    error_code = models.CharField(
        max_length=50,
        blank=True,
        help_text="Twilio error code (if any)"
    )
    error_message = models.TextField(
        blank=True,
        help_text="Human-readable error message (if any)"
    )
    sent_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="hostlead_whatsapp_messages",
        help_text="Admin user who triggered the message"
    )
    
    class Meta:
        verbose_name = "Host Lead WhatsApp Message"
        verbose_name_plural = "Host Lead WhatsApp Messages"
        ordering = ['-created_at']
    
    def __str__(self):
        base = f"Message to {self.lead.first_name} {self.lead.last_name}"
        if self.twilio_sid:
            return f"{base} (SID: {self.twilio_sid})"
        return base


class BankAccount(TimeStampedModel):
    """
    Bank account details for hosts to receive payouts.
    
    Hosts can add multiple bank accounts, but only one can be set as primary.
    Bank account information is encrypted at rest and validated before payout processing.
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Public UUID")
    host = models.ForeignKey(
        'UserProfile',
        on_delete=models.CASCADE,
        related_name="bank_accounts",
        help_text="Host user profile who owns this bank account"
    )
    bank_name = models.CharField(
        max_length=100,
        help_text="Name of the bank (e.g., 'State Bank of India', 'HDFC Bank')"
    )
    account_number = models.CharField(
        max_length=30,
        help_text="Bank account number"
    )
    ifsc_code = models.CharField(
        max_length=11,
        help_text="IFSC (Indian Financial System Code) - 11 characters"
    )
    account_holder_name = models.CharField(
        max_length=100,
        help_text="Name of the account holder as registered with the bank"
    )
    is_primary = models.BooleanField(
        default=False,
        help_text="Whether this is the primary bank account for payouts"
    )
    is_verified = models.BooleanField(
        default=False,
        help_text="Whether this bank account has been verified"
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this bank account is active and can receive payouts"
    )

    class Meta:
        verbose_name = "Bank Account"
        verbose_name_plural = "Bank Accounts"
        ordering = ['-is_primary', '-created_at']
        indexes = [
            models.Index(fields=["host"]),
            models.Index(fields=["is_primary"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.account_holder_name} - {self.bank_name} ({self.masked_account_number})"

    @property
    def masked_account_number(self):
        """Return masked account number for security"""
        if not self.account_number:
            return "-"  # NULL-safe
        if len(self.account_number) <= 4:
            return "****"
        return f"****{self.account_number[-4:]}"

    def save(self, *args, **kwargs):
        """Ensure only one primary account per host"""
        if self.is_primary:
            BankAccount.objects.filter(
                host=self.host,
                is_primary=True
            ).exclude(pk=self.pk if self.pk else None).update(is_primary=False)
        super().save(*args, **kwargs)


class HostPayoutRequest(TimeStampedModel):
    """
    Payout request from hosts for event earnings.
    
    Captures a financial snapshot of the event at the time of payout request:
    - Event details (name, date, location, capacity)
    - Ticket pricing (base fare, final fare with platform fee)
    - Sales data (tickets sold, attendees list)
    - Calculated earnings (host receives full base fare)
    
    Business Logic:
    - Buyer pays: Base ticket fare + platform fee (configurable via admin, default: 10%)
    - Host earns: Base ticket fare × Tickets sold (no platform fee deduction)
    - Platform fee: Base ticket fare × platform fee % × Tickets sold (collected from buyers, not deducted from host)
    
    Example (assuming 10% platform fee):
    - Base ticket fare: ₹100
    - Tickets sold: 50
    - Final ticket fare (buyer pays): ₹110 per ticket
    - Host earnings: ₹100 × 50 = ₹5,000
    - Platform fee: ₹10 × 50 = ₹500
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Public UUID")
    bank_account = models.ForeignKey(
        BankAccount,
        on_delete=models.PROTECT,
        related_name="payout_requests",
        help_text="Bank account to receive the payout"
    )
    event = models.ForeignKey(
        'events.Event',
        on_delete=models.PROTECT,
        related_name="payout_requests",
        help_text="Event for which payout is requested"
    )
    
    # Financial snapshot (calculated at request time)
    host_name = models.CharField(
        max_length=200,
        help_text="Host name at the time of request"
    )
    event_name = models.CharField(
        max_length=255,
        help_text="Event name at the time of request"
    )
    event_date = models.DateTimeField(
        help_text="Event date (start_time) at the time of request"
    )
    event_location = models.CharField(
        max_length=255,
        help_text="Event location (venue name or venue_text) at the time of request"
    )
    total_capacity = models.PositiveIntegerField(
        help_text="Total event capacity at the time of request"
    )
    base_ticket_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Base ticket price per attendee"
    )
    final_ticket_fare = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Final ticket price including 10% platform fee"
    )
    total_tickets_sold = models.PositiveIntegerField(
        help_text="Total number of tickets sold at the time of request"
    )
    attendees_details = models.JSONField(
        default=list,
        help_text="List of attendees with name and contact at the time of request"
    )
    platform_fee_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Total platform fee (10% of base ticket fare × tickets sold)"
    )
    final_earning = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        help_text="Host earnings: Base ticket fare × tickets sold (platform fee is added on top, not deducted)"
    )
    
    # Payout status tracking
    PAYOUT_STATUS_CHOICES = (
        ('pending', 'Pending Review'),
        ('approved', 'Approved'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    )
    status = models.CharField(
        max_length=20,
        choices=PAYOUT_STATUS_CHOICES,
        default='pending',
        help_text="Current status of the payout request"
    )
    processed_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp when payout was processed"
    )
    transaction_reference = models.CharField(
        max_length=100,
        blank=True,
        help_text="Bank transaction reference number"
    )
    rejection_reason = models.TextField(
        blank=True,
        help_text="Reason for rejection if status is 'rejected'"
    )
    notes = models.TextField(
        blank=True,
        help_text="Internal notes about this payout request"
    )

    # Payment linkage for reconciliation (CFO requirement)
    payment_orders = models.ManyToManyField(
        'payments.PaymentOrder',
        related_name='payout_requests',
        blank=True,
        help_text="Payment orders that funded this payout (for reconciliation)"
    )
    
    class Meta:
        verbose_name = "Host Payout Request"
        verbose_name_plural = "Host Payout Requests"
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=["event"]),
            models.Index(fields=["bank_account"]),
            models.Index(fields=["status"]),
            models.Index(fields=["event_date"]),
        ]

    def __str__(self):
        return f"Payout Request #{self.id} - {self.event_name} - {self.final_earning} INR"

    @property
    def platform_fee_percentage(self):
        """
        Platform fee percentage from dynamic configuration.
        
        Returns:
            float: Current platform fee percentage (0-100)
        """
        from core.models import PlatformFeeConfig
        try:
            return float(PlatformFeeConfig.get_fee_percentage())
        except Exception:
            # Fallback to default 10% if configuration unavailable
            return 10.0