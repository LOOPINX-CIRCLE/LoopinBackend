"""
Pydantic schemas for user authentication API
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
import re


class PhoneNumberRequest(BaseModel):
    """Request model for phone number signup"""
    phone_number: str = Field(..., description="Phone number with country code (e.g., +1234567890)")
    
    @validator('phone_number')
    def validate_phone_number(cls, v):
        # Remove any spaces or dashes
        phone = re.sub(r'[\s\-\(\)]', '', v)
        
        # Check if it's a valid phone number format
        if not re.match(r'^\+?[1-9]\d{7,14}$', phone):
            raise ValueError('Invalid phone number format')
        
        return phone


class OTPVerificationRequest(BaseModel):
    """Request model for OTP verification"""
    phone_number: str = Field(..., description="Phone number with country code")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")
    
    @validator('otp_code')
    def validate_otp_code(cls, v):
        if not v.isdigit():
            raise ValueError('OTP code must contain only digits')
        return v


class CompleteProfileRequest(BaseModel):
    """Request model for completing user profile"""
    phone_number: str = Field(..., description="Phone number with country code")
    name: str = Field(..., min_length=2, max_length=100, description="Full name")
    email: str = Field(..., description="Email address")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    location: Optional[str] = Field(None, max_length=100, description="User location")
    birth_date: Optional[str] = Field(None, description="Birth date in YYYY-MM-DD format")
    avatar: Optional[str] = Field(None, description="Profile picture URL")


class LoginRequest(BaseModel):
    """Request model for user login"""
    phone_number: str = Field(..., description="Phone number with country code")
    otp_code: str = Field(..., min_length=6, max_length=6, description="6-digit OTP code")


class AuthResponse(BaseModel):
    """Response model for authentication"""
    success: bool
    message: str
    data: Optional[dict] = None
    token: Optional[str] = None


class UserProfileResponse(BaseModel):
    """Response model for user profile"""
    id: int
    name: str
    email: str
    phone_number: str
    bio: Optional[str] = None
    location: Optional[str] = None
    birth_date: Optional[str] = None
    avatar: Optional[str] = None
    is_verified: bool
    is_active: bool
    created_at: str
    updated_at: str
