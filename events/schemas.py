"""
Production-grade Pydantic schemas for Events API.
Comprehensive validation, documentation, and type safety.
"""

from pydantic import BaseModel, Field, validator, HttpUrl, model_validator, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import re


# ============================================================================
# VENUE SCHEMAS
# ============================================================================

class VenueCreate(BaseModel):
    """
    Schema for creating a venue reference record.
    
    Note: Venues are reference data only—the platform does not manage physical venues.
    This record helps avoid duplicating location details. The `capacity` field is
    informational only; actual event capacity is controlled by `Event.max_capacity`.
    Multiple events can reference the same venue simultaneously.
    """
    name: str = Field(..., min_length=1, max_length=150, description="Venue name")
    address: str = Field(..., description="Full address")
    city: str = Field(..., min_length=1, max_length=100, description="City name")
    venue_type: str = Field(default='indoor', description="Type of venue")
    capacity: int = Field(default=0, ge=0, description="Venue capacity - informational only (0 for unlimited)")
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90, description="Latitude")
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180, description="Longitude")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional metadata")
    is_active: bool = Field(default=True, description="Is venue active")
    
    @validator('venue_type')
    def validate_venue_type(cls, v):
        valid_types = ['indoor', 'outdoor', 'virtual', 'hybrid']
        if v.lower() not in valid_types:
            raise ValueError(f'Venue type must be one of: {", ".join(valid_types)}')
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "name": "Central Park",
                "address": "123 Main St, Manhattan, NY",
                "city": "New York",
                "venue_type": "outdoor",
                "capacity": 1000,
                "latitude": 40.785091,
                "longitude": -73.968285
            }
        }


class VenueUpdate(BaseModel):
    """Schema for updating a venue"""
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    address: Optional[str] = None
    city: Optional[str] = Field(None, min_length=1, max_length=100)
    venue_type: Optional[str] = None
    capacity: Optional[int] = Field(None, ge=0)
    latitude: Optional[Decimal] = Field(None, ge=-90, le=90)
    longitude: Optional[Decimal] = Field(None, ge=-180, le=180)
    metadata: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class VenueResponse(BaseModel):
    """Schema for venue response"""
    id: int
    uuid: str
    name: str
    address: str
    city: str
    venue_type: str
    capacity: int
    latitude: Optional[Decimal]
    longitude: Optional[Decimal]
    metadata: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    @field_validator('uuid', mode='before')
    @classmethod
    def convert_uuid(cls, v):
        """Convert UUID objects to strings"""
        return str(v) if v else v
    
    class Config:
        from_attributes = True


# ============================================================================
# EVENT SCHEMAS
# ============================================================================

class EventCreate(BaseModel):
    """Schema for creating an event with all ERD fields"""
    title: str = Field(..., min_length=3, max_length=200, description="Event title")
    description: Optional[str] = Field(None, max_length=20000, description="Event description")
    slug: Optional[str] = Field(None, description="URL-friendly slug (auto-generated if not provided)")
    
    # Venue - Option 1: Use existing venue reference by ID
    venue_id: Optional[int] = Field(None, description="Existing venue reference ID (fetch from /venues list)")
    
    # Venue - Option 2: Auto-create new venue reference with full details
    venue_create: Optional[VenueCreate] = Field(None, description="Create new venue reference inline to avoid duplicating location details (ignored if venue_id provided)")
    
    # Venue - Option 3: Custom venue text (no venue record)
    venue_text: Optional[str] = Field(None, max_length=255, description="Custom venue text without creating venue record")
    
    # Note: Venues are reference data only—platform does not manage physical venues or bookings.
    # Multiple events can reference the same venue simultaneously. Event capacity is controlled
    # by max_capacity, not the venue's capacity field.
    
    # Scheduling
    start_time: datetime = Field(..., description="Event start time")
    duration_hours: float = Field(..., gt=0, description="Event duration in hours (e.g., 2.5 for 2.5 hours)")
    
    # Capacity & Pricing
    max_capacity: int = Field(default=0, ge=0, description="Maximum capacity (0 for unlimited)")
    is_paid: bool = Field(default=False, description="Is event paid")
    ticket_price: Decimal = Field(default=0, ge=0, description="Ticket price")
    allow_plus_one: bool = Field(default=True, description="Allow bringing a guest")
    
    # GST
    gst_number: Optional[str] = Field(None, max_length=50, description="Host GST number")
    
    # Gender restrictions
    allowed_genders: str = Field(default='all', description="Gender restrictions")
    
    # Media
    cover_images: List[str] = Field(default_factory=list, description="Cover image URLs (1-3)")
    
    # Status & Visibility
    status: str = Field(default='draft', description="Event status")
    is_public: bool = Field(default=True, description="Is event public")
    
    # Event interests
    event_interest_ids: List[int] = Field(default_factory=list, description="Event interest IDs")
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['draft', 'published', 'cancelled', 'completed', 'postponed']
        if v.lower() not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v.lower()
    
    @validator('allowed_genders')
    def validate_allowed_genders(cls, v):
        valid_genders = ['all', 'male', 'female', 'non_binary']
        if v.lower() not in valid_genders:
            raise ValueError(f'Allowed genders must be one of: {", ".join(valid_genders)}')
        return v.lower()
    
    @validator('cover_images')
    def validate_cover_images(cls, v):
        if len(v) > 3:
            raise ValueError('Maximum 3 cover images allowed')
        return v
    
    @model_validator(mode='after')
    def validate_venue_options(self):
        """Ensure only one venue option is provided"""
        venue_id = self.venue_id
        venue_create = self.venue_create
        venue_text = self.venue_text
        
        provided = sum([
            venue_id is not None,
            venue_create is not None,
            venue_text not in (None, '')
        ])
        
        if provided > 1:
            raise ValueError('Please provide only ONE of: venue_id, venue_create, or venue_text')
        
        return self
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Summer Music Festival",
                "description": "A fun outdoor music festival",
                "venue_id": 1,
                "start_time": "2024-07-15T18:00:00Z",
                "duration_hours": 4,
                "max_capacity": 100,
                "is_paid": True,
                "ticket_price": 50.00,
                "allow_plus_one": True,
                "allowed_genders": "all",
                "cover_images": ["https://example.com/image1.jpg"],
                "status": "published",
                "is_public": True
            }
        }


class EventUpdate(BaseModel):
    """Schema for updating an event"""
    title: Optional[str] = Field(None, min_length=3, max_length=200)
    description: Optional[str] = Field(None, max_length=20000)
    slug: Optional[str] = None
    
    # Venue
    venue_id: Optional[int] = None
    venue_text: Optional[str] = Field(None, max_length=255)
    
    # Scheduling
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    # Capacity & Pricing
    max_capacity: Optional[int] = Field(None, ge=0)
    is_paid: Optional[bool] = None
    ticket_price: Optional[Decimal] = Field(None, ge=0)
    allow_plus_one: Optional[bool] = None
    
    # GST
    gst_number: Optional[str] = Field(None, max_length=50)
    
    # Gender restrictions
    allowed_genders: Optional[str] = None
    
    # Media
    cover_images: Optional[List[str]] = None
    
    # Status & Visibility
    status: Optional[str] = None
    is_public: Optional[bool] = None
    is_active: Optional[bool] = None
    
    # Event interests
    event_interest_ids: Optional[List[int]] = None
    
    @validator('end_time')
    def validate_end_after_start(cls, v, values):
        if "start_time" in values and v is not None:
            start = values.get("start_time")
            if start and v <= start:
                raise ValueError("End time must be after start time")
        return v
    
    @validator('status')
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ['draft', 'published', 'cancelled', 'completed', 'postponed']
            if v.lower() not in valid_statuses:
                raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v.lower() if v else None
    
    @validator('allowed_genders')
    def validate_allowed_genders(cls, v):
        if v is not None:
            valid_genders = ['all', 'male', 'female', 'non_binary']
            if v.lower() not in valid_genders:
                raise ValueError(f'Allowed genders must be one of: {", ".join(valid_genders)}')
        return v.lower() if v else None


class EventResponse(BaseModel):
    """Schema for event response with all fields"""
    id: int
    uuid: str
    title: str
    slug: Optional[str]
    description: Optional[str]
    host: Dict[str, Any]
    venue: Optional[Dict[str, Any]]
    venue_text: Optional[str]
    start_time: datetime
    end_time: datetime
    max_capacity: int
    going_count: int
    requests_count: int
    is_paid: bool
    ticket_price: Decimal
    allow_plus_one: bool
    gst_number: str
    allowed_genders: str
    cover_images: List[str]
    status: str
    is_public: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
    event_interests: List[Dict[str, Any]] = Field(default_factory=list)
    
    @classmethod
    def from_orm(cls, event, include_interests=False):
        """Create response from ORM instance"""
        from django.db import models
        from asgiref.sync import sync_to_async
        
        # Get event interests if requested
        interests = []
        if include_interests:
            try:
                # Use prefetch_related results if available, otherwise query
                if hasattr(event, '_prefetched_objects_cache') and 'interest_maps' in event._prefetched_objects_cache:
                    interest_maps = event._prefetched_objects_cache['interest_maps']
                else:
                    interest_maps = event.interest_maps.select_related('event_interest').all()
                
                interests = [
                    {
                        "id": im.event_interest.id,
                        "name": im.event_interest.name,
                        "slug": im.event_interest.slug,
                    }
                    for im in interest_maps
                ]
            except Exception as e:
                # Log error for debugging
                import logging
                logging.error(f"Error loading event interests: {e}")
                pass
        
        return cls(
            id=event.id,
            uuid=str(event.uuid),
            title=event.title,
            slug=event.slug,
            description=event.description,
            host={
                "id": event.host.id,
                "username": event.host.username,
                "email": event.host.email,
            },
            venue={
                "id": event.venue.id,
                "uuid": str(event.venue.uuid),
                "name": event.venue.name,
                "city": event.venue.city,
                "venue_type": event.venue.venue_type,
                "address": event.venue.address,
            } if event.venue else None,
            venue_text=event.venue_text,
            start_time=event.start_time,
            end_time=event.end_time,
            max_capacity=event.max_capacity,
            going_count=event.going_count,
            requests_count=event.requests_count,
            is_paid=event.is_paid,
            ticket_price=event.ticket_price,
            allow_plus_one=event.allow_plus_one,
            gst_number=event.gst_number,
            allowed_genders=event.allowed_genders,
            cover_images=event.cover_images or [],
            status=event.status,
            is_public=event.is_public,
            is_active=event.is_active,
            created_at=event.created_at,
            updated_at=event.updated_at,
            event_interests=interests,
        )
    
    class Config:
        from_attributes = True


# ============================================================================
# EVENT REQUEST SCHEMAS
# ============================================================================

class EventRequestSubmit(BaseModel):
    """Schema for submitting an event request"""
    message: Optional[str] = Field(None, max_length=2000, description="Request message")
    seats_requested: int = Field(default=1, ge=1, description="Number of seats requested")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "I would love to attend!",
                "seats_requested": 2
            }
        }


class EventRequestResponse(BaseModel):
    """Schema for event request response"""
    id: int
    uuid: str
    event_id: int
    requester_id: int
    requester_name: str
    status: str
    message: Optional[str]
    host_message: Optional[str]
    seats_requested: int
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EventRequestUpdate(BaseModel):
    """Schema for updating event request (host response)"""
    status: str = Field(..., description="Request status (accepted/rejected)")
    host_message: Optional[str] = Field(None, max_length=2000, description="Host's response message")
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['accepted', 'rejected']
        if v.lower() not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v.lower()


# ============================================================================
# EVENT INVITE SCHEMAS
# ============================================================================

class EventInviteCreate(BaseModel):
    """Schema for creating event invites"""
    invited_user_ids: List[int] = Field(..., description="User IDs to invite")
    invite_type: str = Field(default='direct', description="Type of invite")
    message: Optional[str] = Field(None, max_length=2000, description="Invite message")
    expires_at: Optional[datetime] = Field(None, description="Invite expiration time")
    
    @validator('invite_type')
    def validate_invite_type(cls, v):
        valid_types = ['direct', 'share_link']
        if v.lower() not in valid_types:
            raise ValueError(f'Invite type must be one of: {", ".join(valid_types)}')
        return v.lower()
    
    class Config:
        json_schema_extra = {
            "example": {
                "invited_user_ids": [1, 2, 3],
                "invite_type": "direct",
                "message": "You're invited!"
            }
        }


class EventInviteResponse(BaseModel):
    """Schema for event invite response"""
    id: int
    uuid: str
    event_id: int
    host_id: Optional[int]
    host_name: Optional[str]
    invited_user_id: int
    invited_user_name: str
    status: str
    invite_type: str
    message: Optional[str]
    expires_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class EventInviteUpdate(BaseModel):
    """Schema for updating invite status"""
    status: str = Field(..., description="Invite status (accepted/rejected)")
    
    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['accepted', 'rejected']
        if v.lower() not in valid_statuses:
            raise ValueError(f'Status must be one of: {", ".join(valid_statuses)}')
        return v.lower()


# ============================================================================
# EVENT ATTENDEE SCHEMAS
# ============================================================================

class EventAttendeeResponse(BaseModel):
    """Schema for event attendee response"""
    id: int
    uuid: str
    event_id: int
    user_id: int
    user_name: str
    status: str
    ticket_type: str
    seats: int
    is_paid: bool
    price_paid: Decimal
    platform_fee: Decimal
    checked_in_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# EVENT INTEREST MAP SCHEMAS
# ============================================================================

class EventInterestMapResponse(BaseModel):
    """Schema for event interest map response"""
    id: int
    event_id: int
    event_interest_id: int
    event_interest_name: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============================================================================
# PAGINATION & FILTERING
# ============================================================================

class PaginatedResponse(BaseModel):
    """Generic paginated response wrapper"""
    total: int
    offset: int
    limit: int
    data: List[Any]
    
    class Config:
        json_schema_extra = {
            "example": {
                "total": 100,
                "offset": 0,
                "limit": 20,
                "data": []
            }
        }


class EventFilterParams(BaseModel):
    """Query parameters for filtering events"""
    host_id: Optional[int] = None
    venue_id: Optional[int] = None
    status: Optional[str] = None
    is_public: Optional[bool] = None
    is_paid: Optional[bool] = None
    allowed_genders: Optional[str] = None
    min_price: Optional[Decimal] = None
    max_price: Optional[Decimal] = None
    event_interest_id: Optional[int] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    search: Optional[str] = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=20, ge=1, le=100)

