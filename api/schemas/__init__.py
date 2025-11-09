"""
API schemas for the Loopin Backend application.

This module contains Pydantic schemas for request/response validation
and serialization across all API endpoints.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, date
from pydantic import BaseModel, EmailStr, Field, validator
from enum import Enum


# Base schemas
class BaseResponse(BaseModel):
    """Base response schema with common fields."""
    success: bool = True
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class ErrorResponse(BaseResponse):
    """Error response schema."""
    success: bool = False
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class PaginatedResponse(BaseResponse):
    """Paginated response schema."""
    page: int = Field(ge=1, description="Current page number")
    page_size: int = Field(ge=1, le=100, description="Number of items per page")
    total_items: int = Field(ge=0, description="Total number of items")
    total_pages: int = Field(ge=0, description="Total number of pages")
    has_next: bool = Field(description="Whether there is a next page")
    has_previous: bool = Field(description="Whether there is a previous page")


# Authentication schemas
class PhoneAuthRequest(BaseModel):
    """Phone authentication request schema."""
    phone_number: str = Field(..., regex=r'^\+[1-9]\d{1,14}$', description="Phone number in E.164 format")


class OTPVerificationRequest(BaseModel):
    """OTP verification request schema."""
    phone_number: str = Field(..., regex=r'^\+[1-9]\d{1,14}$', description="Phone number in E.164 format")
    otp: str = Field(..., min_length=4, max_length=6, description="OTP code")


class AuthResponse(BaseResponse):
    """Authentication response schema."""
    access_token: str = Field(..., description="JWT access token")
    refresh_token: Optional[str] = Field(None, description="JWT refresh token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(..., description="Token expiration time in seconds")
    user_id: int = Field(..., description="User ID")
    needs_profile_completion: bool = Field(..., description="Whether user needs to complete profile")


# User schemas
class UserProfileBase(BaseModel):
    """Base user profile schema."""
    name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    bio: Optional[str] = Field(None, max_length=500, description="User biography")
    location: Optional[str] = Field(None, max_length=100, description="User location")
    birth_date: Optional[date] = Field(None, description="User's birth date")
    gender: Optional[str] = Field(None, regex=r'^(male|female|other)$', description="User gender")


class UserProfileCreate(UserProfileBase):
    """User profile creation schema."""
    pass


class UserProfileUpdate(BaseModel):
    """User profile update schema."""
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    location: Optional[str] = Field(None, max_length=100)
    birth_date: Optional[date] = None
    gender: Optional[str] = Field(None, regex=r'^(male|female|other)$')


class UserProfileResponse(UserProfileBase):
    """User profile response schema."""
    id: int = Field(..., description="User ID")
    phone_number: str = Field(..., description="User's phone number")
    is_verified: bool = Field(..., description="Whether user is verified")
    is_active: bool = Field(..., description="Whether user account is active")
    created_at: datetime = Field(..., description="Account creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Event schemas
class EventBase(BaseModel):
    """Base event schema."""
    title: str = Field(..., min_length=3, max_length=200, description="Event title")
    description: Optional[str] = Field(None, max_length=2000, description="Event description")
    start_time: datetime = Field(..., description="Event start time")
    end_time: Optional[datetime] = Field(None, description="Event end time")
    location: Optional[str] = Field(None, max_length=200, description="Event location")
    max_capacity: int = Field(..., ge=1, le=10000, description="Maximum event capacity")
    is_public: bool = Field(default=True, description="Whether event is public")


class EventCreate(EventBase):
    """Event creation schema."""
    pass


class EventUpdate(BaseModel):
    """Event update schema."""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    location: Optional[str] = Field(None, max_length=200)
    max_capacity: Optional[int] = Field(None, ge=1, le=10000)
    is_public: Optional[bool] = None


class EventResponse(EventBase):
    """Event response schema."""
    id: int = Field(..., description="Event ID")
    host_id: int = Field(..., description="Event host user ID")
    current_attendees: int = Field(..., ge=0, description="Current number of attendees")
    status: str = Field(..., description="Event status")
    created_at: datetime = Field(..., description="Event creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")


# Payment schemas
class PaymentRequest(BaseModel):
    """Payment request schema."""
    event_id: int = Field(..., description="Event ID")
    amount: float = Field(..., gt=0, description="Payment amount")
    currency: str = Field(default="INR", description="Payment currency")
    payment_method: str = Field(..., description="Payment method")


class PaymentResponse(BaseResponse):
    """Payment response schema."""
    payment_id: str = Field(..., description="Payment ID")
    order_id: str = Field(..., description="Order ID")
    amount: float = Field(..., description="Payment amount")
    currency: str = Field(..., description="Payment currency")
    status: str = Field(..., description="Payment status")
    payment_url: Optional[str] = Field(None, description="Payment gateway URL")


# Attendance schemas
class AttendanceRequest(BaseModel):
    """Attendance request schema."""
    event_id: int = Field(..., description="Event ID")
    seats: int = Field(..., ge=1, le=10, description="Number of seats requested")


class AttendanceResponse(BaseResponse):
    """Attendance response schema."""
    attendance_id: int = Field(..., description="Attendance record ID")
    event_id: int = Field(..., description="Event ID")
    user_id: int = Field(..., description="User ID")
    seats: int = Field(..., description="Number of seats")
    status: str = Field(..., description="Attendance status")
    ticket_secret: str = Field(..., description="Ticket secret for check-in")


# Notification schemas
class NotificationRequest(BaseModel):
    """Notification request schema."""
    recipient_id: int = Field(..., description="Recipient user ID")
    title: str = Field(..., min_length=1, max_length=200, description="Notification title")
    message: str = Field(..., min_length=1, max_length=1000, description="Notification message")
    notification_type: str = Field(..., description="Notification type")
    data: Optional[Dict[str, Any]] = Field(None, description="Additional notification data")


class NotificationResponse(BaseResponse):
    """Notification response schema."""
    notification_id: int = Field(..., description="Notification ID")
    recipient_id: int = Field(..., description="Recipient user ID")
    title: str = Field(..., description="Notification title")
    message: str = Field(..., description="Notification message")
    notification_type: str = Field(..., description="Notification type")
    is_read: bool = Field(..., description="Whether notification is read")
    created_at: datetime = Field(..., description="Notification creation timestamp")


# Health check schema
class HealthCheckResponse(BaseResponse):
    """Health check response schema."""
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    status: str = Field(..., description="Service status")
    dependencies: Optional[Dict[str, str]] = Field(None, description="Dependency statuses")
