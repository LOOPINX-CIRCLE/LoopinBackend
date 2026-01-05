"""
Pydantic schemas for user authentication API
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date
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
    otp_code: str = Field(..., min_length=4, max_length=4, description="4-digit OTP code")
    
    @validator('otp_code')
    def validate_otp_code(cls, v):
        if not v.isdigit():
            raise ValueError('OTP code must contain only digits')
        if len(v) != 4:
            raise ValueError('OTP code must be exactly 4 digits')
        return v


class CompleteProfileRequest(BaseModel):
    """Request model for completing user profile"""
    phone_number: str = Field(..., description="Phone number with country code")
    name: str = Field(..., min_length=2, max_length=100, description="Full name (minimum 2 characters)")
    birth_date: str = Field(..., description="Birth date in YYYY-MM-DD format")
    gender: str = Field(..., description="User gender")
    event_interests: List[int] = Field(..., min_items=1, max_items=5, description="List of event interest IDs (1-5 selections)")
    profile_pictures: List[str] = Field(..., min_items=1, max_items=6, description="List of profile picture URLs (1-6 pictures required)")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    location: Optional[str] = Field(None, max_length=100, description="User location")
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        if len(v.strip()) < 2:
            raise ValueError('Name must be at least 2 characters long')
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-\']+$", v.strip()):
            raise ValueError('Name contains invalid characters')
        return v.strip()
    
    @validator('birth_date')
    def validate_birth_date(cls, v):
        try:
            birth_date = datetime.strptime(v, '%Y-%m-%d').date()
            today = date.today()
            age = today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))
            if age < 16:
                raise ValueError('User must be 16 years or older')
            return v
        except ValueError as e:
            if 'time data' in str(e):
                raise ValueError('Invalid date format. Use YYYY-MM-DD')
            raise e
    
    @validator('gender')
    def validate_gender(cls, v):
        valid_genders = ['male', 'female', 'other']
        if v.lower() not in valid_genders:
            raise ValueError(f'Gender must be one of: {', '.join(valid_genders)}')
        return v.lower()
    
    @validator('profile_pictures')
    def validate_profile_pictures(cls, v):
        if not v:
            raise ValueError('At least 1 profile picture is required')
        if len(v) > 6:
            raise ValueError('Maximum 6 profile pictures allowed')
        
        # Validate each picture URL
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        
        for i, picture_url in enumerate(v):
            if not url_pattern.match(picture_url):
                raise ValueError(f'Invalid URL format for profile picture {i+1}')
        
        return v


class LoginRequest(BaseModel):
    """Request model for user login"""
    phone_number: str = Field(..., description="Phone number with country code")
    otp_code: str = Field(..., min_length=4, max_length=4, description="4-digit OTP code")
    
    @validator('otp_code')
    def validate_otp_code(cls, v):
        if not v.isdigit():
            raise ValueError('OTP code must contain only digits')
        if len(v) != 4:
            raise ValueError('OTP code must be exactly 4 digits')
        return v


class AuthResponse(BaseModel):
    """Response model for authentication"""
    success: bool
    message: str
    data: Optional[dict] = None
    token: Optional[str] = None


class EventInterestResponse(BaseModel):
    """Response model for event interest"""
    id: int
    name: str
    is_active: bool
    created_at: str
    updated_at: str


class UserProfileResponse(BaseModel):
    """Response model for user profile"""
    id: int
    name: str
    phone_number: str
    gender: Optional[str] = None
    bio: Optional[str] = None
    location: Optional[str] = None
    birth_date: Optional[str] = None
    event_interests: List[EventInterestResponse] = []
    profile_pictures: List[str] = []
    is_verified: bool
    is_active: bool
    created_at: str
    updated_at: str


# ============================================================================
# Bank Account Schemas
# ============================================================================

class BankAccountCreate(BaseModel):
    """Request model for creating a bank account"""
    bank_name: str = Field(..., min_length=2, max_length=100, description="Name of the bank")
    account_number: str = Field(..., min_length=8, max_length=30, description="Bank account number")
    ifsc_code: str = Field(..., min_length=11, max_length=11, description="IFSC code (11 characters)")
    account_holder_name: str = Field(..., min_length=2, max_length=100, description="Account holder name")
    is_primary: bool = Field(default=False, description="Set as primary bank account")
    
    @validator('ifsc_code')
    def validate_ifsc_code(cls, v):
        import re
        v = v.strip().upper()
        if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', v):
            raise ValueError('Invalid IFSC code format. Must be 11 characters: 4 letters, 0, then 6 alphanumeric')
        return v
    
    @validator('account_number')
    def validate_account_number(cls, v):
        if not v.isdigit():
            raise ValueError('Account number must contain only digits')
        return v.strip()
    
    @validator('bank_name', 'account_holder_name')
    def validate_name_fields(cls, v):
        v = v.strip()
        if not v or len(v) < 2:
            raise ValueError('Field cannot be empty or too short')
        return v


class BankAccountUpdate(BaseModel):
    """Request model for updating a bank account"""
    bank_name: Optional[str] = Field(None, min_length=2, max_length=100)
    account_number: Optional[str] = Field(None, min_length=8, max_length=30)
    ifsc_code: Optional[str] = Field(None, min_length=11, max_length=11)
    account_holder_name: Optional[str] = Field(None, min_length=2, max_length=100)
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None
    
    @validator('ifsc_code')
    def validate_ifsc_code(cls, v):
        if v is None:
            return v
        import re
        v = v.strip().upper()
        if not re.match(r'^[A-Z]{4}0[A-Z0-9]{6}$', v):
            raise ValueError('Invalid IFSC code format')
        return v


class BankAccountResponse(BaseModel):
    """Response model for bank account"""
    id: int
    uuid: str
    bank_name: str
    masked_account_number: str
    ifsc_code: str
    account_holder_name: str
    is_primary: bool
    is_verified: bool
    is_active: bool
    created_at: str
    updated_at: str
    
    class Config:
        from_attributes = True


# ============================================================================
# Payout Request Schemas
# ============================================================================

class AttendeeDetail(BaseModel):
    """Attendee detail in payout request"""
    name: str
    contact: str  # phone number or email


class PayoutRequestCreate(BaseModel):
    """Request model for creating a payout request"""
    event_id: int = Field(..., description="Event ID for which payout is requested")
    bank_account_id: int = Field(..., description="Bank account ID to receive payout")


class PayoutRequestResponse(BaseModel):
    """Response model for payout request"""
    id: int
    uuid: str
    bank_account: BankAccountResponse
    event_id: int
    host_name: str
    event_name: str
    event_date: str
    event_location: str
    total_capacity: int
    base_ticket_fare: float
    final_ticket_fare: float
    total_tickets_sold: int
    attendees_details: List[AttendeeDetail]
    platform_fee_amount: float
    platform_fee_percentage: float
    final_earning: float
    status: str
    transaction_reference: Optional[str]
    rejection_reason: Optional[str]
    notes: Optional[str]
    created_at: str
    updated_at: str
    processed_at: Optional[str]
    
    class Config:
        from_attributes = True
