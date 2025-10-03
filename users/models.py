from django.db import models
from django.contrib.auth.models import User
import random
import string
from datetime import datetime, timedelta
from django.utils import timezone

# Create your models here.

class UserProfile(models.Model):
    """Extended user profile model for normal users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Basic profile information
    name = models.CharField(max_length=100, blank=True, help_text="Full name of the user")
    email = models.EmailField(blank=True, help_text="Primary email address")
    phone_number = models.CharField(max_length=15, blank=True, help_text="Contact phone number")
    
    # Additional profile details
    bio = models.TextField(max_length=500, blank=True, help_text="User biography")
    location = models.CharField(max_length=100, blank=True, help_text="User location")
    birth_date = models.DateField(null=True, blank=True, help_text="Date of birth")
    avatar = models.URLField(blank=True, help_text="Profile picture URL")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Profile status
    is_verified = models.BooleanField(default=False, help_text="Whether the user profile is verified")
    is_active = models.BooleanField(default=True, help_text="Whether the user profile is active")

    def __str__(self):
        return f"{self.name} ({self.email})"

    class Meta:
        verbose_name = "User Profile"
        verbose_name_plural = "User Profiles"
        ordering = ['-created_at']


class PhoneOTP(models.Model):
    """Model for storing phone number OTP verification"""
    phone_number = models.CharField(max_length=15, unique=True)
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            # OTP expires in 10 minutes
            self.expires_at = timezone.now() + timedelta(minutes=10)
        super().save(*args, **kwargs)
    
    def is_expired(self):
        return timezone.now() > self.expires_at
    
    def generate_otp(self):
        """Generate a 6-digit OTP"""
        self.otp_code = ''.join(random.choices(string.digits, k=6))
        self.expires_at = timezone.now() + timedelta(minutes=10)
        self.attempts = 0
        self.is_verified = False
    
    def verify_otp(self, otp_code):
        """Verify the OTP code"""
        if self.is_expired():
            return False, "OTP has expired"
        
        if self.attempts >= 3:
            return False, "Too many attempts. Please request a new OTP"
        
        if self.otp_code == otp_code:
            self.is_verified = True
            self.save()
            return True, "OTP verified successfully"
        else:
            self.attempts += 1
            self.save()
            return False, f"Invalid OTP. {3 - self.attempts} attempts remaining"
    
    def __str__(self):
        return f"OTP for {self.phone_number}"
    
    class Meta:
        verbose_name = "Phone OTP"
        verbose_name_plural = "Phone OTPs"
        ordering = ['-created_at']