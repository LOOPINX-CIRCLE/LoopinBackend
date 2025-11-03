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
    description = models.TextField(blank=True, help_text="Description of the event interest")
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
    """Model for storing phone number OTP verification"""
    phone_number = models.CharField(max_length=15, unique=True)
    otp_code = models.CharField(max_length=6)
    otp_type = models.CharField(
        max_length=20,
        choices=OTP_TYPE_CHOICES,
        default='signup',
        help_text="Type of OTP (signup, login, etc.)"
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