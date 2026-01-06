"""
Production-ready Events API router for FastAPI.
Implements high-performance CRUD operations with Django ORM, JWT auth, and optimized queries.
"""

from typing import Optional, List, Dict, Any
import json
from datetime import datetime
from decimal import Decimal
import secrets
import string
import jwt
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    Path,
    Body,
    Form,
    File,
    UploadFile,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Prefetch
from asgiref.sync import sync_to_async
from pydantic import BaseModel, Field
import logging

from core.utils.logger import get_logger
from core.exceptions import AuthorizationError, NotFoundError, ValidationError
from core.services.storage import get_storage_service
from events.models import Event, Venue, EventRequest, EventInvite, EventAttendee, EventInterestMap, EventImage
from attendances.models import AttendanceRecord
from users.models import UserProfile
from events.schemas import (
    EventCreate,
    EventUpdate,
    EventResponse,
    EventRequestSubmit as EventRequestSubmission,
    EventRequestResponse,
    VenueCreate,
    VenueUpdate,
    VenueResponse,
    EventInviteCreate,
    EventInviteResponse,
    EventAttendeeResponse,
    PaginatedResponse,
    EventFilterParams,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/events", tags=["events"])

# JWT token scheme
security = HTTPBearer()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class ConfirmAttendanceRequest(BaseModel):
    """Schema for confirming attendance"""
    seats: int = Field(1, ge=1, le=10, description="Number of seats (1-10)")


class BulkActionRequest(BaseModel):
    """Schema for bulk accept/decline actions"""
    request_ids: List[int] = Field(..., min_items=1, max_items=100, description="List of request IDs")
    action: str = Field(..., pattern="^(accept|decline)$", description="Action: 'accept' or 'decline'")
    host_message: Optional[str] = Field(None, max_length=500, description="Optional message for all requests")


# ============================================================================
# Authentication & Authorization
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get current authenticated user from JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    try:
        user = await sync_to_async(User.objects.get)(id=user_id)
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user",
        )
    return user


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False)),
) -> Optional[User]:
    """Get optional authenticated user"""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def check_event_permission(user: User, event: Event, action: str = "view") -> bool:
    """Check if user has permission to perform action on event"""
    # Admin can do everything
    if user.is_superuser or user.is_staff:
        return True
    
    # Host can do everything on their events
    if event.host.user == user:
        return True
    
    # Public events can be viewed by anyone
    if action == "view" and event.is_public:
        return True
    
    return False


# ============================================================================
# Sync-to-Async Helper Functions
# ============================================================================

@sync_to_async
def get_events_queryset(
    host_id: Optional[int] = None,
    venue_id: Optional[int] = None,
    status: Optional[str] = None,
    is_public: Optional[bool] = None,
    is_paid: Optional[bool] = None,
    allowed_genders: Optional[str] = None,
    event_interest_id: Optional[int] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    search: Optional[str] = None,
    offset: int = 0,
    limit: int = 20,
    user: Optional[User] = None,
) -> tuple[List[Event], int]:
    """
    Get optimized events queryset with filtering and pagination.
    
    Args:
        user: Authenticated user for privacy filtering (only show public events or user's own events)
    
    Returns:
        Tuple of (events list, total count after privacy filtering)
    """
    # Base queryset with select_related and prefetch_related
    queryset = Event.objects.select_related("host", "host__user", "venue").filter(is_active=True)
    
    # Apply privacy filter: only show public events or events hosted by the current user
    if user is not None:
        # Filter: show public events OR events hosted by this user (via UserProfile.user FK)
        from users.models import UserProfile
        user_profile = UserProfile.objects.filter(user=user).first()
        
        if user_profile:
            # Show public events OR events hosted by this user's profile
            queryset = queryset.filter(
                Q(is_public=True) | Q(host=user_profile)
            )
        else:
            # No profile exists, only show public events
            queryset = queryset.filter(is_public=True)
    else:
        # No user provided, only show public events
        queryset = queryset.filter(is_public=True)
    
    # Apply filters
    if host_id:
        queryset = queryset.filter(host_id=host_id)
    if venue_id:
        queryset = queryset.filter(venue_id=venue_id)
    if status:
        queryset = queryset.filter(status=status)
    if is_public is not None:
        # If explicitly filtering by is_public, combine with privacy filter
        queryset = queryset.filter(is_public=is_public)
    if is_paid is not None:
        queryset = queryset.filter(is_paid=is_paid)
    if allowed_genders:
        queryset = queryset.filter(allowed_genders=allowed_genders)
    if event_interest_id:
        queryset = queryset.filter(interest_maps__event_interest_id=event_interest_id)
    if start_date:
        queryset = queryset.filter(start_time__gte=start_date)
    if end_date:
        queryset = queryset.filter(end_time__lte=end_date)
    if search:
        queryset = queryset.filter(
            Q(title__icontains=search) | Q(description__icontains=search)
        )
    
    # Get total count AFTER all filters (including privacy filter)
    total = queryset.count()
    
    # Apply pagination
    queryset = queryset.order_by("-start_time")[offset : offset + limit]
    
    # Convert to list to avoid lazy evaluation issues
    return list(queryset), total


@sync_to_async
def get_event_by_id(event_id: int, include_interests: bool = False) -> Event:
    """Get event by ID with select_related"""
    try:
        queryset = Event.objects.select_related("host", "venue")
        
        if include_interests:
            queryset = queryset.prefetch_related("interest_maps__event_interest")
        
        return queryset.get(id=event_id, is_active=True)
    except Event.DoesNotExist:
        raise NotFoundError(
            f"The event you're looking for doesn't exist or has been removed.",
            code="EVENT_NOT_FOUND"
        )


@sync_to_async
def create_event_with_relationships(
    host: 'UserProfile',
    title: str,
    description: Optional[str],
    start_time: datetime,
    end_time: datetime,
    venue_id: Optional[int] = None,
    venue_text: Optional[str] = None,
    status: str = "draft",
    is_public: bool = True,
    max_capacity: int = 0,
    is_paid: bool = False,
    ticket_price: float = 0,
    allow_plus_one: bool = True,
    gst_number: str = "",
    allowed_genders: str = "all",
    cover_images: List[str] = None,
    event_interest_ids: List[int] = None,
) -> Event:
    """
    Create event with all relationships.
    
    Note: Venues are reference data only—multiple events can reference the same venue.
    Event capacity is controlled by max_capacity parameter, not the venue's capacity field.
    """
    if cover_images is None:
        cover_images = []
    if event_interest_ids is None:
        event_interest_ids = []
    
    with transaction.atomic():
        # Link to venue reference if provided (venue is reference data, not a booking)
        venue = None
        if venue_id:
            try:
                venue = Venue.objects.get(id=venue_id, is_active=True)
            except Venue.DoesNotExist:
                raise NotFoundError(
                    f"The venue you selected could not be found. Please select a different venue or create a new one.",
                    code="VENUE_NOT_FOUND"
                )
        
        # Ensure venue_text is empty string if None (CharField requirement)
        if venue_text is None:
            venue_text = ""
        
        event = Event.objects.create(
            host=host,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            venue=venue,
            venue_text=venue_text,
            status=status,
            is_public=is_public,
            max_capacity=max_capacity,
            is_paid=is_paid,
            ticket_price=ticket_price,
            allow_plus_one=allow_plus_one,
            gst_number=gst_number,
            allowed_genders=allowed_genders,
            cover_images=cover_images,
        )
        
        # Add event interests
        if event_interest_ids:
            from users.models import EventInterest
            for interest_id in event_interest_ids:
                try:
                    interest = EventInterest.objects.get(id=interest_id, is_active=True)
                    EventInterestMap.objects.create(event=event, event_interest=interest)
                except EventInterest.DoesNotExist:
                    pass  # Skip invalid interests
        
        logger.info(f"Event created: {event.id} by user {host.id}")
        return event


@sync_to_async
def update_event_with_relationships(
    event_id: int,
    user: User,
    update_data: dict,
    event_interest_ids: Optional[List[int]] = None,
) -> Event:
    """
    Update event with permission check.
    
    Note: Venues are reference data only—updating venue_id links to a different venue
    reference but does not affect booking availability. Multiple events can use the same venue.
    """
    try:
        event = Event.objects.select_related("host", "venue").get(id=event_id, is_active=True)
    except Event.DoesNotExist:
        raise NotFoundError(
            f"The event you're trying to update doesn't exist or has been removed.",
            code="EVENT_NOT_FOUND"
        )
    
    # Check permission
    if not check_event_permission(user, event, action="edit"):
        raise AuthorizationError(
            f"You don't have permission to edit this event. Only the event host can make changes.",
            code="PERMISSION_DENIED",
        )
    
    with transaction.atomic():
        # Handle venue reference update (venue is reference data, not a booking)
        if "venue_id" in update_data:
            venue_id = update_data.pop("venue_id")
            if venue_id is None:
                event.venue = None
            else:
                try:
                    venue = Venue.objects.get(id=venue_id, is_active=True)
                    event.venue = venue
                except Venue.DoesNotExist:
                    raise NotFoundError(
                        f"The venue you selected could not be found. Please select a different venue.",
                        code="VENUE_NOT_FOUND"
                    )
        
        # Update other fields
        for field, value in update_data.items():
            setattr(event, field, value)
        
        event.save()
        
        # Update event interests if provided
        if event_interest_ids is not None:
            EventInterestMap.objects.filter(event=event).delete()
            if event_interest_ids:
                from users.models import EventInterest
                for interest_id in event_interest_ids:
                    try:
                        interest = EventInterest.objects.get(id=interest_id, is_active=True)
                        EventInterestMap.objects.create(event=event, event_interest=interest)
                    except EventInterest.DoesNotExist:
                        pass
        
        logger.info(f"Event updated: {event.id} by user {user.id}")
        return event


@sync_to_async
def delete_event(event_id: int, user: User) -> None:
    """Soft delete event"""
    try:
        event = Event.objects.select_related("host", "venue").get(id=event_id, is_active=True)
    except Event.DoesNotExist:
        raise NotFoundError(
            f"The event you're trying to delete doesn't exist or has already been removed.",
            code="EVENT_NOT_FOUND"
        )
    
    # Check permission
    if not check_event_permission(user, event, action="delete"):
        raise AuthorizationError(
            f"You don't have permission to delete this event. Only the event host can delete it.",
            code="PERMISSION_DENIED",
        )
    
    with transaction.atomic():
        event.is_active = False
        event.save()
        logger.info(f"Event deleted: {event.id} by user {user.id}")


@sync_to_async
def create_venue(
    name: str,
    address: str,
    city: str,
    venue_type: str = "indoor",
    capacity: int = 0,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    metadata: Optional[dict] = None,
) -> Venue:
    """
    Create a venue record (reference data only).
    
    Note: This creates a venue reference record to avoid duplicating location details.
    The platform does NOT manage physical venues or bookings. Multiple events can
    reference the same venue simultaneously. The `capacity` field is informational
    only; actual event capacity is controlled by `Event.max_capacity`.
    """
    if metadata is None:
        metadata = {}
    
    venue = Venue.objects.create(
        name=name,
        address=address,
        city=city,
        venue_type=venue_type,
        capacity=capacity,
        latitude=latitude,
        longitude=longitude,
        metadata=metadata,
    )
    
    logger.info(f"Venue reference created: {venue.id}")
    return venue


@sync_to_async
def get_venue_by_id(venue_id: int) -> Venue:
    """Get venue by ID"""
    try:
        return Venue.objects.get(id=venue_id, is_active=True)
    except Venue.DoesNotExist:
        raise NotFoundError(
            f"The venue you're looking for doesn't exist or has been removed.",
            code="VENUE_NOT_FOUND"
        )


def generate_ticket_secret() -> str:
    """Generate unique 32-character ticket secret"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))


@sync_to_async
def send_notification(user: User, notification_type: str, title: str, message: str, data: Dict[str, Any] = None, sender: User = None, reference_type: str = None, reference_id: int = None):
    """Send notification to user"""
    try:
        from notifications.models import Notification
        Notification.objects.create(
            recipient=user,
            sender=sender,
            type=notification_type,
            title=title,
            message=message,
            metadata=data or {},
            reference_type=reference_type or "",
            reference_id=reference_id,
        )
        logger.info(f"Notification sent to user {user.id}: {notification_type}")
    except ImportError:
        logger.warning("Notifications module not available, skipping notification")
    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}")


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("", response_model=Dict[str, Any])
async def list_events(
    host_id: Optional[int] = Query(None, description="Filter by host ID"),
    venue_id: Optional[int] = Query(None, description="Filter by venue ID"),
    status: Optional[str] = Query(None, description="Filter by status"),
    is_public: Optional[bool] = Query(None, description="Filter by public/private"),
    is_paid: Optional[bool] = Query(None, description="Filter by paid/free"),
    allowed_genders: Optional[str] = Query(None, description="Filter by allowed genders"),
    event_interest_id: Optional[int] = Query(None, description="Filter by event interest ID"),
    start_date: Optional[datetime] = Query(None, description="Filter by start date"),
    end_date: Optional[datetime] = Query(None, description="Filter by end date"),
    search: Optional[str] = Query(None, description="Search in title and description"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    user: Optional[User] = Depends(get_optional_user),
):
    """
    List events with comprehensive filtering and pagination.
    
    - **Performance**: Optimized with select_related, prefetch_related
    - **Pagination**: Default 20 items per page, max 100
    - **Filtering**: By host, venue, status, paid/free, genders, interests, dates
    - **Search**: Full-text search in title and description
    - **Security**: Public events visible to all, private events to authenticated users only
    - **Authentication**: Optional - unauthenticated users can view public events
    """
    events, total = await get_events_queryset(
        host_id=host_id,
        venue_id=venue_id,
        status=status,
        is_public=is_public,
        is_paid=is_paid,
        allowed_genders=allowed_genders,
        event_interest_id=event_interest_id,
        start_date=start_date,
        end_date=end_date,
        search=search,
        offset=offset,
        limit=limit,
        user=user,  # Pass user for privacy filtering
    )
    
    # Privacy filtering is now done at the database level in get_events_queryset
    # so events are already filtered and total count is accurate
    
    return {
        "total": total,  # This now matches the filtered results
        "offset": offset,
        "limit": limit,
        "data": [EventResponse.from_orm(e, include_interests=True).model_dump() for e in events],
    }


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event_endpoint(
    # Form fields - all required/optional as per EventCreate schema
    title: str = Form(...),
    description: Optional[str] = Form(None),
    start_time: str = Form(...),  # ISO format datetime string
    duration_hours: float = Form(...),
    venue_id: Optional[int] = Form(None),
    venue_text: Optional[str] = Form(None),
    max_capacity: int = Form(0),
    is_paid: bool = Form(False),
    ticket_price: float = Form(0.0),
    allow_plus_one: bool = Form(True),
    gst_number: Optional[str] = Form(None),
    allowed_genders: str = Form("all"),
    status: str = Form("draft"),
    is_public: bool = Form(True),
    event_interest_ids: str = Form("[]"),  # JSON string array
    # File uploads - optional cover images
    cover_images: Optional[List[UploadFile]] = File(None),
    # Authentication
    user: User = Depends(get_current_user),
):
    """
    Create a new event with all ERD fields.
    
    Accepts multipart/form-data with actual image files for cover images.
    Uploads cover images to Supabase Storage (event-images bucket).
    
    - **Auth**: Required (JWT)
    - **Validation**: Title, date/time validation, capacity checks, pricing
    - **Performance**: Atomic transaction with select_related
    - **Features**: Supports venue linking, venue auto-creation, event interests, pricing, capacity, restrictions
    
    **Required Form Fields:**
    - title: Event title
    - start_time: ISO format datetime (e.g., "2024-12-25T18:00:00Z")
    - duration_hours: Event duration in hours
    
    **Optional Form Fields:**
    - description: Event description
    - venue_id: Existing venue ID (JSON number or null)
    - venue_text: Custom venue text
    - max_capacity: Maximum attendees (0 = unlimited)
    - is_paid: Boolean (true/false as string)
    - ticket_price: Ticket price (float)
    - allow_plus_one: Boolean
    - gst_number: GST number
    - allowed_genders: "all", "male", "female", "non_binary"
    - status: "draft", "published", etc.
    - is_public: Boolean
    - event_interest_ids: JSON array string (e.g., "[1,2,3]")
    
    **File Uploads:**
    - cover_images: Optional list of image files (max 3, jpg/jpeg/png/webp, 5MB each)
    
    **Venue Options (Reference Data Only):**
    - `venue_id`: Use existing venue reference (fetch from GET /venues)
    - `venue_text`: Custom venue text without venue record
    
    **Important Notes:**
    - Venues are reference data only—the platform does not manage physical venues or bookings
    - Multiple events can reference the same venue simultaneously without conflicts
    - Event capacity is controlled by `max_capacity`, not the venue's capacity field
    """
    # Validate duration_hours must be greater than zero
    if duration_hours <= 0:
        raise ValidationError(
            "duration_hours must be greater than zero",
            code="INVALID_DURATION"
        )
    
    # Parse start_time from ISO format string
    from datetime import timedelta
    from users.models import UserProfile
    try:
        start_time_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if start_time_dt.tzinfo is None:
            # Assume UTC if no timezone
            from django.utils import timezone
            start_time_dt = timezone.make_aware(start_time_dt, timezone.utc)
    except ValueError as e:
        raise ValidationError(
            f"Invalid start_time format. Expected ISO format datetime (e.g., '2024-12-25T18:00:00Z'): {str(e)}",
            code="INVALID_DATETIME_FORMAT"
        )
    
    # Calculate end_time from start_time and duration_hours
    end_time_dt = start_time_dt + timedelta(hours=duration_hours)
    
    # Parse event_interest_ids from JSON string
    try:
        interest_ids_list = json.loads(event_interest_ids)
        if not isinstance(interest_ids_list, list):
            raise ValueError("event_interest_ids must be a JSON array")
    except (json.JSONDecodeError, ValueError) as e:
        raise ValidationError(
            f"Invalid event_interest_ids format. Expected JSON array (e.g., '[1,2,3]'): {str(e)}",
            code="INVALID_INTEREST_IDS_FORMAT"
        )
    
    # Get UserProfile for the user (Event.host requires UserProfile)
    try:
        user_profile = user.profile
    except UserProfile.DoesNotExist:
        user_profile, _ = await sync_to_async(lambda: UserProfile.objects.get_or_create(user=user))()
    
    # Upload cover images to Supabase Storage if provided
    cover_image_urls = []
    if cover_images:
        # Validate count
        if len(cover_images) > 3:
            raise ValidationError(
                "Maximum 3 cover images allowed",
                code="TOO_MANY_COVER_IMAGES"
            )
        
        try:
            storage_service = get_storage_service()
            cover_image_urls = await storage_service.upload_multiple_files(
                files=cover_images,
                bucket="event-images",
                user_id=user_profile.id,
                folder=None
            )
            logger.info(f"Uploaded {len(cover_image_urls)} cover images for event by user {user.id}")
        except ValidationError as ve:
            raise
        except Exception as upload_error:
            logger.error(f"Error uploading cover images: {upload_error}", exc_info=True)
            raise ValidationError(
                "An error occurred while uploading cover images. Please check file formats and sizes.",
                code="IMAGE_UPLOAD_FAILED"
            )
    
    try:
        event = await create_event_with_relationships(
            host=user_profile,
            title=title,
            description=description,
            start_time=start_time_dt,
            end_time=end_time_dt,
            venue_id=venue_id,
            venue_text=venue_text or "",
            status=status,
            is_public=is_public,
            max_capacity=max_capacity,
            is_paid=is_paid,
            ticket_price=float(ticket_price),
            allow_plus_one=allow_plus_one,
            gst_number=gst_number or "",
            allowed_genders=allowed_genders,
            cover_images=cover_image_urls,
            event_interest_ids=interest_ids_list,
        )
        
        # Refresh from DB to get all relationships
        event = await get_event_by_id(event.id, include_interests=True)
        return EventResponse.from_orm(event, include_interests=True)
    except ValidationError as e:
        # ValidationError is already user-friendly, just re-raise it
        raise
    except NotFoundError as e:
        # NotFoundError is already user-friendly, just re-raise it
        raise
    except Exception as e:
        logger.error(f"Failed to create event: {str(e)}", exc_info=True)
        raise ValidationError(
            "Unable to create the event. Please check your input and try again.",
            code="EVENT_CREATION_FAILED",
            details={"error": str(e)}
        )


# ============================================================================
# Venue Endpoints (MUST BE BEFORE /{event_id} ROUTE)
# ============================================================================

@router.get("/venues", response_model=Dict[str, Any])
async def list_venues(
    city: Optional[str] = Query(None, description="Filter by city"),
    venue_type: Optional[str] = Query(None, description="Filter by venue type"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    user: User = Depends(get_current_user),
):
    """
    List venue references with filtering.
    
    Note: Venues are reference data only—the platform does not manage physical venues.
    Multiple events can reference the same venue simultaneously.
    """
    # Auth required for venue listing
    @sync_to_async
    def get_venues():
        queryset = Venue.objects.filter(is_active=True)
        if city:
            queryset = queryset.filter(city__icontains=city)
        if venue_type:
            queryset = queryset.filter(venue_type=venue_type)
        total = queryset.count()
        venues = list(queryset[offset : offset + limit])
        return venues, total
    
    venues, total = await get_venues()
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "data": [VenueResponse.from_orm(v).model_dump() for v in venues],
    }


@router.post("/venues", response_model=VenueResponse, status_code=status.HTTP_201_CREATED)
async def create_venue_endpoint(
    venue_data: VenueCreate,
    user: User = Depends(get_current_user),
):
    """
    Create a new venue reference record.
    
    Note: This creates a venue reference to avoid duplicating location details.
    The platform does NOT manage physical venues or bookings. The `capacity` field
    is informational only; event capacity is controlled by `Event.max_capacity`.
    """
    try:
        venue = await create_venue(
            name=venue_data.name,
            address=venue_data.address,
            city=venue_data.city,
            venue_type=venue_data.venue_type,
            capacity=venue_data.capacity,
            latitude=float(venue_data.latitude) if venue_data.latitude else None,
            longitude=float(venue_data.longitude) if venue_data.longitude else None,
            metadata=venue_data.metadata,
        )
        return VenueResponse.from_orm(venue)
    except Exception as e:
        logger.error(f"Failed to create venue: {str(e)}", exc_info=True)
        raise ValidationError(
            "Unable to create the venue. Please check your input and try again.",
            code="VENUE_CREATION_FAILED",
            details={"error": str(e)}
        )


@router.get("/venues/{venue_id}", response_model=VenueResponse)
async def get_venue(
    venue_id: int = Path(..., description="Venue ID"),
    user: User = Depends(get_current_user),
):
    """
    Get venue reference by ID.
    
    Note: Venues are reference data only—used to avoid duplicating location details.
    Multiple events can reference the same venue simultaneously.
    """
    # Auth required for venue access
    venue = await get_venue_by_id(venue_id)
    return VenueResponse.from_orm(venue)


# ============================================================================
# User-Specific Endpoints (Must be before /{event_id} route)
# ============================================================================

@router.get("/my-requests", response_model=List[Dict[str, Any]])
async def get_my_requests(
    status_filter: Optional[str] = Query(None, pattern="^(pending|accepted|declined|cancelled)$"),
    user: User = Depends(get_current_user),
):
    """
    Get all event requests made by the current user.
    
    - **Auth**: Required
    - **Query Params**: Optional status_filter (pending, accepted, declined, cancelled)
    - **Returns**: List of user's event requests with status
    """
    @sync_to_async
    def get_requests():
        queryset = EventRequest.objects.select_related("event", "event__host", "event__venue").filter(
            requester=user
        ).order_by("-created_at")
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        requests = list(queryset)
        
        result = []
        for r in requests:
            can_confirm = r.status == 'accepted' and not EventAttendee.objects.filter(
                event=r.event,
                user=user,
                status='going'
            ).exists()
            
            result.append({
                "request_id": r.id,
                "event_id": r.event.id,
                "event_title": r.event.title,
                "status": r.status,
                "message": r.message,
                "host_message": r.host_message,
                "seats_requested": r.seats_requested,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
                "can_confirm": can_confirm,
            })
        
        return result
    
    return await get_requests()


# @router.get("/my-invitations", response_model=List[Dict[str, Any]])
# NOTE: Duplicate route - use events_attendance.py router instead
async def _get_my_invitations_DUPLICATE(
    status_filter: Optional[str] = Query(None, pattern="^(pending|accepted|declined|expired)$"),
    user: User = Depends(get_current_user),
):
    """
    Get all invitations received by the current user.
    
    - **Auth**: Required
    - **Query Params**: Optional status_filter
    - **Returns**: List of received invitations with event details
    """
    @sync_to_async
    def get_invitations():
        from users.models import UserProfile
        # Get UserProfile for the user
        try:
            user_profile = user.profile
        except UserProfile.DoesNotExist:
            user_profile, _ = UserProfile.objects.get_or_create(user=user)
        
        queryset = EventInvite.objects.select_related(
            "event",
            "event__host",
            "event__venue",
            "host"
        ).filter(
            invited_user=user_profile
        ).order_by("-created_at")
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return [
            {
                "invite_id": inv.id,
                "event_id": inv.event.id,
                "event_title": inv.event.title,
                "event_start_time": inv.event.start_time.isoformat(),
                "host_name": inv.event.host.username,
                "status": inv.status,
                "message": inv.message,
                "created_at": inv.created_at.isoformat(),
            }
            for inv in queryset
        ]
    
    return await get_invitations()


# @router.get("/my-tickets", response_model=List[Dict[str, Any]])
# NOTE: Duplicate route - use events_attendance.py router instead
async def _get_my_tickets_DUPLICATE(
    event_id: Optional[int] = Query(None, description="Optional filter by event ID"),
    user: User = Depends(get_current_user),
):
    """
    Get all tickets for the current user.
    
    - **Auth**: Required
    - **Query Params**: Optional event_id filter
    - **Returns**: List of user's tickets with secret codes
    """
    @sync_to_async
    def get_tickets():
        queryset = AttendanceRecord.objects.select_related("event", "user").filter(
            user=user,
            status='going'
        ).order_by("-created_at")
        
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        
        return [
            {
                "ticket_id": ticket.id,
                "event_id": ticket.event.id,
                "event_title": ticket.event.title,
                "event_start_time": ticket.event.start_time.isoformat(),
                "event_end_time": ticket.event.end_time.isoformat(),
                "ticket_secret": ticket.ticket_secret,
                "seats": ticket.seats,
                "is_paid": ticket.event.is_paid,
                "payment_status": ticket.payment_status,
                "status": ticket.status,
                "created_at": ticket.created_at.isoformat(),
                "qr_code_data": f"EVENT:{ticket.event.id}:TICKET:{ticket.ticket_secret}",
            }
            for ticket in queryset
        ]
    
    return await get_tickets()


# ============================================================================
# Event Detail Endpoints
# ============================================================================

@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int = Path(..., description="Event ID"),
    user: User = Depends(get_current_user),
):
    """
    Get event details by ID with all ERD fields.
    
    - **Performance**: Optimized with select_related and prefetch_related
    - **Security**: Public events visible to all, private events to host only
    - **Fields**: Includes all ERD fields (pricing, capacity, venue, interests, etc.)
    - **Soft Deletes**: Hosts can view their own deleted events
    """
    @sync_to_async
    def get_event_with_permissions():
        try:
            queryset = Event.objects.select_related("host", "venue").prefetch_related("interest_maps__event_interest")
            event = queryset.get(id=event_id)
            return event
        except Event.DoesNotExist:
            raise NotFoundError(
                f"The event you're looking for doesn't exist or has been removed.",
                code="EVENT_NOT_FOUND"
            )
    
    event = await get_event_with_permissions()
    
    # Check permissions for soft-deleted events (only host can view)
    if not event.is_active and event.host != user:
        raise NotFoundError(
            "The event you're looking for doesn't exist or has been removed.",
            code="EVENT_NOT_FOUND"
        )
    
    # Check permissions for private events (only host can view)
    if not event.is_public and event.host != user:
        raise AuthorizationError(
            "This is a private event. You don't have permission to view it.",
            code="PERMISSION_DENIED"
        )
    
    return EventResponse.from_orm(event, include_interests=True)


@router.put("/{event_id}", response_model=EventResponse)
async def update_event_endpoint(
    event_id: int,
    event_data: EventUpdate,
    user: User = Depends(get_current_user),
):
    """
    Update an event with all ERD fields.
    
    - **Auth**: Required (JWT)
    - **Permission**: Event host or admin only
    - **Performance**: Atomic transaction with select_related
    - **Features**: Supports partial updates, venue reference changes, interest updates
    
    **Note**: Venues are reference data only—updating venue_id links to a different venue
    reference but does not affect booking availability. Multiple events can use the same venue.
    """
    update_dict = event_data.dict(exclude_unset=True)
    
    # Handle ticket_price conversion
    if "ticket_price" in update_dict:
        update_dict["ticket_price"] = float(update_dict["ticket_price"])
    
    # Handle event interests separately
    event_interest_ids = update_dict.pop("event_interest_ids", None)
    
    event = await update_event_with_relationships(
        event_id, user, update_dict, event_interest_ids=event_interest_ids
    )
    
    # Refresh from DB to get all relationships
    event = await get_event_by_id(event.id, include_interests=True)
    return EventResponse.from_orm(event, include_interests=True)


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event_endpoint(
    event_id: int,
    user: User = Depends(get_current_user),
):
    """
    Delete an event (soft delete).
    
    - **Auth**: Required (JWT)
    - **Permission**: Event host or admin only
    - **Operation**: Soft delete (is_active=False)
    """
    await delete_event(event_id, user)
    return None


# ============================================================================
# Event Request Endpoints
# ============================================================================

@router.get("/{event_id}/requests", response_model=List[EventRequestResponse])
async def list_event_requests(
    event_id: int,
    user: User = Depends(get_current_user),
):
    """
    List requests for an event (host only).
    
    - **Auth**: Required (JWT)
    - **Permission**: Event host or admin only
    """
    event = await get_event_by_id(event_id)
    
    if not check_event_permission(user, event, action="edit"):
        raise AuthorizationError(
            "Only the event host can view requests for this event.",
            code="PERMISSION_DENIED"
        )
    
    # Get requests with optimizations
    requests = await sync_to_async(list)(
        EventRequest.objects.select_related("requester", "event")
        .filter(event=event)
        .order_by("-created_at")
    )
    
    return [
        EventRequestResponse(
            id=r.id,
            uuid=str(r.uuid),
            event_id=r.event.id,
            requester_id=r.requester.id,
            requester_name=r.requester.username,
            status=r.status,
            message=r.message,
            host_message=r.host_message,
            seats_requested=r.seats_requested,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in requests
    ]


@router.post("/{event_id}/requests", response_model=EventRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_event_request(
    event_id: int,
    request_data: EventRequestSubmission,
    user: User = Depends(get_current_user),
):
    """Submit a request to join an event"""
    try:
        event = await get_event_by_id(event_id)
    except NotFoundError:
        raise  # Re-raise with user-friendly message already set
    
    @sync_to_async
    @transaction.atomic
    def create_request():
        # Check if request already exists
        existing = EventRequest.objects.filter(event=event, requester=user).first()
        if existing:
            if existing.status == 'pending':
                raise ValidationError(
                    "You already have a pending request for this event. Please wait for the host's response.",
                    code="DUPLICATE_REQUEST"
                )
            if existing.status == 'accepted':
                raise ValidationError(
                    "You have already been accepted for this event. You can confirm your attendance now.",
                    code="ALREADY_ACCEPTED"
                )
        
        request = EventRequest.objects.create(
            event=event,
            requester=user,
            message=request_data.message,
            seats_requested=request_data.seats_requested,
            status='pending',
        )
        
        # Update event requests count
        event.requests_count = EventRequest.objects.filter(event=event, status='pending').count()
        event.save()
        
        logger.info(f"Event request created: {request.id}")
        return request
    
    try:
        request = await create_request()
    except (ValidationError, NotFoundError) as e:
        # Custom exceptions already have user-friendly messages
        raise
    except Exception as e:
        logger.error(f"Failed to create request: {str(e)}", exc_info=True)
        raise ValidationError(
            "Unable to submit your request. Please try again later.",
            code="REQUEST_CREATION_FAILED",
            details={"error": str(e)}
        )
    
    return EventRequestResponse(
        id=request.id,
        uuid=str(request.uuid),
        event_id=request.event.id,
        requester_id=request.requester.id,
        requester_name=request.requester.username,
        status=request.status,
        message=request.message,
        host_message=request.host_message,
        seats_requested=request.seats_requested,
        created_at=request.created_at,
        updated_at=request.updated_at,
    )


# ============================================================================
# User Request Status Endpoints
# ============================================================================

@router.get("/{event_id}/my-request", response_model=Dict[str, Any])
async def get_my_request_for_event(
    event_id: int,
    user: User = Depends(get_current_user),
):
    """
    Get the current user's request status for a specific event.
    
    - **Auth**: Required
    - **Returns**: Request status if exists, 404 if not found
    """
    event = await get_event_by_id(event_id)
    
    @sync_to_async
    def get_request():
        try:
            request = EventRequest.objects.select_related("event").get(
                event=event,
                requester=user
            )
            can_confirm = request.status == 'accepted' and not EventAttendee.objects.filter(
                event=event,
                user=user,
                status='going'
            ).exists()
            
            return {
                "request_id": request.id,
                "event_id": request.event.id,
                "event_title": request.event.title,
                "status": request.status,
                "message": request.message,
                "host_message": request.host_message,
                "seats_requested": request.seats_requested,
                "created_at": request.created_at,
                "updated_at": request.updated_at,
                "can_confirm": can_confirm,
            }
        except EventRequest.DoesNotExist:
            raise NotFoundError("You have not requested to attend this event", code="REQUEST_NOT_FOUND")
    
    return await get_request()


# ============================================================================
# Host Request Management Endpoints
# ============================================================================

@router.get("/{event_id}/requests/{request_id}/profile", response_model=Dict[str, Any])
async def get_requester_profile(
    event_id: int,
    request_id: int,
    user: User = Depends(get_current_user),
):
    """
    Get detailed profile of a user who requested to attend the event (host only).
    
    - **Auth**: Required
    - **Permission**: Event host only
    - **Returns**: User profile with name, bio, gender, interests, profile pictures
    """
    event = await get_event_by_id(event_id)
    
    if not check_event_permission(user, event, action="edit"):
        raise AuthorizationError("Only the event host can view requester profiles", code="NOT_HOST")
    
    @sync_to_async
    def get_profile():
        try:
            request = EventRequest.objects.select_related(
                "requester",
                "requester__profile"
            ).prefetch_related(
                "requester__profile__event_interests"
            ).get(
                id=request_id,
                event=event
            )
            
            try:
                profile = request.requester.profile
                interests = [
                    {"id": interest.id, "name": interest.name}
                    for interest in profile.event_interests.filter(is_active=True)[:10]
                ]
                
                return {
                    "user_id": request.requester.id,
                    "name": profile.name or request.requester.username,
                    "phone_number": profile.phone_number,
                    "bio": profile.bio,
                    "gender": profile.gender,
                    "location": profile.location,
                    "profile_pictures": profile.profile_pictures or [],
                    "event_interests": interests,
                    "is_verified": profile.is_verified,
                }
            except UserProfile.DoesNotExist:
                return {
                    "user_id": request.requester.id,
                    "name": request.requester.username,
                    "phone_number": None,
                    "bio": None,
                    "gender": None,
                    "location": None,
                    "profile_pictures": [],
                    "event_interests": [],
                    "is_verified": False,
                }
        except EventRequest.DoesNotExist:
            raise NotFoundError("Request not found", code="REQUEST_NOT_FOUND")
    
    return await get_profile()


@router.put("/{event_id}/requests/{request_id}/accept", response_model=Dict[str, Any])
async def accept_event_request(
    event_id: int = Path(..., description="Event ID"),
    request_id: int = Path(..., description="Request ID"),
    host_message: Optional[str] = Body(None, max_length=500, embed=True),
    user: User = Depends(get_current_user),
):
    """
    Accept a single event request (host only).
    
    - **Auth**: Required
    - **Permission**: Event host only
    - **Body**: Optional host_message
    - **Returns**: Updated request status
    - **Side Effects**: Updates request status, sends notification, updates event counts
    """
    try:
        event = await get_event_by_id(event_id)
    except NotFoundError:
        raise  # Re-raise with user-friendly message already set
    
    if not check_event_permission(user, event, action="edit"):
        raise AuthorizationError(
            "Only the event host can accept requests for this event.",
            code="PERMISSION_DENIED"
        )
    
    @sync_to_async
    def accept_request():
        try:
            with transaction.atomic():
                request = EventRequest.objects.select_related("requester", "event").get(
                    id=request_id,
                    event=event,
                    status='pending'
                )
                
                # Check capacity
                if event.max_capacity > 0:
                    current_count = EventAttendee.objects.filter(event=event, status='going').count()
                    if current_count + request.seats_requested > event.max_capacity:
                        available = event.max_capacity - current_count
                        raise ValidationError(
                            f"The event has reached its capacity. Only {available} seat(s) available, but {request.seats_requested} seat(s) requested.",
                            code="CAPACITY_EXCEEDED",
                            details={
                                "current_attendees": current_count,
                                "max_capacity": event.max_capacity,
                                "requested_seats": request.seats_requested,
                                "available_seats": available
                            }
                        )
                
                # Update request
                request.status = 'accepted'
                if host_message:
                    request.host_message = host_message
                request.save(update_fields=['status', 'host_message', 'updated_at'])
                
                # Update event counts
                event.requests_count = EventRequest.objects.filter(event=event, status='pending').count()
                event.going_count = EventAttendee.objects.filter(event=event, status='going').count()
                event.save(update_fields=['requests_count', 'going_count'])
                
                # Send notification (fire and forget in sync context)
                try:
                    from notifications.models import Notification
                    Notification.objects.create(
                        recipient=request.requester,
                        sender=event.host,
                        type='event_request',
                        title=f"Request Accepted: {event.title}",
                        message=f"Your request to attend '{event.title}' has been accepted! Please confirm your attendance.",
                        metadata={"event_id": event.id, "request_id": request.id, "action": "accepted"},
                        reference_type="EventRequest",
                        reference_id=request.id
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification: {str(e)}")
                
                logger.info(f"Event request {request_id} accepted by host {user.id}")
                return {
                    "request_id": request.id,
                    "event_id": request.event.id,
                    "event_title": request.event.title,
                    "status": request.status,
                    "message": request.message,
                    "host_message": request.host_message,
                    "seats_requested": request.seats_requested,
                    "created_at": request.created_at.isoformat(),
                    "updated_at": request.updated_at.isoformat(),
                    "can_confirm": True,
                }
        except EventRequest.DoesNotExist:
            raise NotFoundError(
                "The request you're trying to accept doesn't exist or has already been processed.",
                code="REQUEST_NOT_FOUND"
            )
        except (ValidationError, NotFoundError) as e:
            raise e
        except Exception as e:
            logger.error(f"Error accepting request {request_id}: {str(e)}", exc_info=True)
            raise ValidationError(
                "Unable to accept this request. Please try again later.",
                code="REQUEST_ACCEPT_FAILED",
                details={"error": str(e)}
            )
    
    try:
        return await accept_request()
    except (ValidationError, NotFoundError, AuthorizationError) as e:
        # Custom exceptions already have user-friendly messages and proper status codes
        raise


class DeclineRequestBody(BaseModel):
    """Request body for declining an event request"""
    host_message: Optional[str] = Field(None, max_length=500, description="Optional message from host")

@router.put("/{event_id}/requests/{request_id}/decline", response_model=Dict[str, Any])
async def decline_event_request(
    event_id: int,
    request_id: int,
    request_body: Optional[DeclineRequestBody] = Body(None),
    user: User = Depends(get_current_user),
):
    """
    Decline a single event request (host only).
    
    - **Auth**: Required
    - **Permission**: Event host only
    - **Body**: Optional host_message
    - **Returns**: Updated request status
    - **Side Effects**: Sends notification to requester
    """
    event = await get_event_by_id(event_id)
    
    if not check_event_permission(user, event, action="edit"):
        raise AuthorizationError("Only the event host can decline requests", code="NOT_HOST")
    
    @sync_to_async
    @transaction.atomic
    def decline_request():
        try:
            request = EventRequest.objects.select_related("requester", "event").get(
                id=request_id,
                event=event,
                status='pending'
            )
        except EventRequest.DoesNotExist:
            raise NotFoundError("Request not found or already processed", code="REQUEST_NOT_FOUND")
        
        request.status = 'declined'
        host_message_value = request_body.host_message if request_body and request_body.host_message else None
        if host_message_value:
            request.host_message = host_message_value
        request.save(update_fields=['status', 'host_message', 'updated_at'])
        
        # Update event requests count
        event.requests_count = EventRequest.objects.filter(event=event, status='pending').count()
        event.save(update_fields=['requests_count'])
        
        # Send notification (fire and forget in sync context)
        try:
            from notifications.models import Notification
            Notification.objects.create(
                recipient=request.requester,
                sender=event.host,
                type='event_request',
                title=f"Request Declined: {event.title}",
                message=f"Your request to attend '{event.title}' has been declined.",
                metadata={"event_id": event.id, "request_id": request.id, "action": "declined"},
                reference_type="EventRequest",
                reference_id=request.id
            )
        except Exception as e:
            logger.error(f"Failed to send notification: {str(e)}")
        
        logger.info(f"Event request {request_id} declined by host {user.id}")
        return {
            "request_id": request.id,
            "event_id": request.event.id,
            "event_title": request.event.title,
            "status": request.status,
            "message": request.message,
            "host_message": request.host_message,
            "seats_requested": request.seats_requested,
            "created_at": request.created_at,
            "updated_at": request.updated_at,
            "can_confirm": False,
        }
    
    return await decline_request()


@router.post("/{event_id}/requests/bulk-action", response_model=Dict[str, Any])
async def bulk_accept_decline_requests(
    event_id: int = Path(..., description="Event ID"),
    request_body: BulkActionRequest = Body(...),
    user: User = Depends(get_current_user),
):
    """
    Accept or decline multiple event requests at once (host only).
    
    - **Auth**: Required
    - **Permission**: Event host only
    - **Body**: 
      - `request_ids`: List of request IDs (1-100)
      - `action`: "accept" or "decline"
      - `host_message`: Optional message for all requests
    - **Returns**: Summary of processed requests
    """
    try:
        event = await get_event_by_id(event_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    
    if not check_event_permission(user, event, action="edit"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the event host can perform bulk actions"
        )
    
    # Extract values from request body
    request_ids = request_body.request_ids
    action = request_body.action
    host_message = request_body.host_message
    
    @sync_to_async
    def process_bulk_action():
        try:
            with transaction.atomic():
                # Get all pending requests
                requests = list(EventRequest.objects.select_related("requester", "event").filter(
                    id__in=request_ids,
                    event=event,
                    status='pending'
                ))
                
                if not requests:
                    raise ValidationError("No pending requests found with the provided IDs", code="NO_PENDING_REQUESTS")
                
                accepted_count = 0
                declined_count = 0
                errors = []
                
                if action == 'accept':
                    # Check total capacity
                    current_count = EventAttendee.objects.filter(event=event, status='going').count()
                    total_seats_requested = sum(r.seats_requested for r in requests)
                    
                    if event.max_capacity > 0 and current_count + total_seats_requested > event.max_capacity:
                        available = event.max_capacity - current_count
                        raise ValidationError(
                            f"Cannot accept all requests: would exceed capacity. Available: {available}, Requested: {total_seats_requested}",
                            code="CAPACITY_EXCEEDED"
                        )
                    
                    # Accept all requests
                    for request in requests:
                        try:
                            request.status = 'accepted'
                            if host_message:
                                request.host_message = host_message
                            request.save(update_fields=['status', 'host_message', 'updated_at'])
                            
                            # Send notification (fire and forget in sync context)
                            try:
                                from notifications.models import Notification
                                Notification.objects.create(
                                    recipient=request.requester,
                                    sender=event.host,
                                    type='event_request',
                                    title=f"Request Accepted: {event.title}",
                                    message=f"Your request to attend '{event.title}' has been accepted!",
                                    metadata={"event_id": event.id, "request_id": request.id, "action": "accepted"},
                                    reference_type="EventRequest",
                                    reference_id=request.id
                                )
                            except Exception as e:
                                logger.error(f"Failed to send notification: {str(e)}")
                            
                            accepted_count += 1
                        except Exception as e:
                            errors.append({"request_id": request.id, "error": str(e)})
                
                elif action == 'decline':
                    # Decline all requests
                    for request in requests:
                        try:
                            request.status = 'declined'
                            if host_message:
                                request.host_message = host_message
                            request.save(update_fields=['status', 'host_message', 'updated_at'])
                            
                            # Send notification (fire and forget in sync context)
                            try:
                                from notifications.models import Notification
                                Notification.objects.create(
                                    recipient=request.requester,
                                    sender=event.host,
                                    type='event_request',
                                    title=f"Request Declined: {event.title}",
                                    message=f"Your request to attend '{event.title}' has been declined.",
                                    metadata={"event_id": event.id, "request_id": request.id, "action": "declined"},
                                    reference_type="EventRequest",
                                    reference_id=request.id
                                )
                            except Exception as e:
                                logger.error(f"Failed to send notification: {str(e)}")
                            
                            declined_count += 1
                        except Exception as e:
                            errors.append({"request_id": request.id, "error": str(e)})
                
                # Update event counts
                event.requests_count = EventRequest.objects.filter(event=event, status='pending').count()
                event.going_count = EventAttendee.objects.filter(event=event, status='going').count()
                event.save(update_fields=['requests_count', 'going_count'])
                
                logger.info(f"Bulk {action} processed: {accepted_count + declined_count} requests for event {event_id}")
                
                return {
                    "success": len(errors) == 0,
                    "processed_count": accepted_count + declined_count,
                    "accepted_count": accepted_count,
                    "declined_count": declined_count,
                    "errors": errors,
                }
        except (ValidationError, NotFoundError) as e:
            raise e
        except Exception as e:
            logger.error(f"Error processing bulk action for event {event_id}: {str(e)}", exc_info=True)
            raise ValidationError(
                "Unable to process the bulk action. Please try again later.",
                code="BULK_ACTION_FAILED",
                details={"error": str(e)}
            )
    
    try:
        return await process_bulk_action()
    except (ValidationError, NotFoundError, AuthorizationError) as e:
        # Custom exceptions already have user-friendly messages and proper status codes
        raise


# ============================================================================
# Attendance Confirmation Endpoints (Free Events)
# ============================================================================

@router.post("/{event_id}/confirm-attendance", response_model=Dict[str, Any])
async def confirm_attendance_free_event(
    event_id: int = Path(..., description="Event ID"),
    request_body: ConfirmAttendanceRequest = Body(...),
    user: User = Depends(get_current_user),
):
    """
    Confirm attendance for a free event after request acceptance.
    
    Flow:
    1. User's request must be accepted
    2. User confirms attendance with number of seats
    3. System generates ticket with unique secret code
    4. User can view ticket anytime
    
    - **Auth**: Required
    - **Body**: {"seats": int} (1-10)
    - **Returns**: Generated ticket with secret code
    """
    try:
        event = await get_event_by_id(event_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    seats = request_body.seats
    
    @sync_to_async
    def confirm_attendance():
        try:
            with transaction.atomic():
                # Check if request exists and is accepted
                try:
                    request = EventRequest.objects.get(event=event, requester=user, status='accepted')
                except EventRequest.DoesNotExist:
                    raise ValidationError(
                        "You must have an accepted request to confirm attendance",
                        code="NO_ACCEPTED_REQUEST"
                    )
                
                # Check if already confirmed
                existing_attendee = EventAttendee.objects.filter(event=event, user=user, status='going').first()
                if existing_attendee:
                    raise ValidationError("You have already confirmed attendance", code="ALREADY_CONFIRMED")
                
                # Check capacity
                if event.max_capacity > 0:
                    current_count = EventAttendee.objects.filter(event=event, status='going').count()
                    if current_count + seats > event.max_capacity:
                        raise ValidationError("Event is at full capacity", code="CAPACITY_FULL")
                
                # Create or update attendee record
                attendee, created = EventAttendee.objects.get_or_create(
                    event=event,
                    user=user,
                    defaults={
                        'request': request,
                        'seats': seats,
                        'status': 'going',
                        'is_paid': False,
                        'price_paid': Decimal('0.00'),
                    }
                )
                
                # Update if already exists
                if not created:
                    attendee.request = request
                    attendee.seats = seats
                    attendee.status = 'going'
                    attendee.save(update_fields=['request', 'seats', 'status', 'updated_at'])
                
                # Create or get attendance record with ticket
                ticket_secret = generate_ticket_secret()
                attendance_record, record_created = AttendanceRecord.objects.get_or_create(
                    event=event,
                    user=user,
                    defaults={
                        'status': 'going',
                        'payment_status': 'unpaid',  # Free event
                        'ticket_secret': ticket_secret,
                        'seats': seats,
                    }
                )
                
                # Update if already exists (regenerate ticket secret if needed)
                if not record_created:
                    if not attendance_record.ticket_secret:
                        attendance_record.ticket_secret = ticket_secret
                    attendance_record.status = 'going'
                    attendance_record.seats = seats
                    attendance_record.save(update_fields=['ticket_secret', 'status', 'seats', 'updated_at'])
                
                # Update event going_count
                event.going_count = EventAttendee.objects.filter(event=event, status='going').count()
                event.save(update_fields=['going_count'])
                
                logger.info(f"Attendance confirmed for user {user.id} at event {event_id}, ticket: {ticket_secret}")
                
                return {
                    "ticket_id": attendance_record.id,
                    "event_id": event.id,
                    "event_title": event.title,
                    "event_start_time": event.start_time.isoformat(),
                    "event_end_time": event.end_time.isoformat(),
                    "ticket_secret": attendance_record.ticket_secret,
                    "seats": attendance_record.seats,
                    "is_paid": False,
                    "payment_status": attendance_record.payment_status,
                    "status": attendance_record.status,
                    "created_at": attendance_record.created_at.isoformat(),
                    "qr_code_data": f"EVENT:{event.id}:TICKET:{attendance_record.ticket_secret}",
                }
        except (ValidationError, NotFoundError) as e:
            raise e
        except Exception as e:
            logger.error(f"Error confirming attendance for event {event_id}: {str(e)}", exc_info=True)
            raise ValidationError(
                "Unable to confirm your attendance. Please try again later.",
                code="ATTENDANCE_CONFIRMATION_FAILED",
                details={"error": str(e)}
            )
    
    try:
        return await confirm_attendance()
    except (ValidationError, NotFoundError, AuthorizationError) as e:
        # Custom exceptions already have user-friendly messages and proper status codes
        raise


# ============================================================================
# Invitation Management Endpoints
# NOTE: Duplicate routes removed - use events_attendance.py router instead
# ============================================================================

# @router.post("/{event_id}/invitations", response_model=Dict[str, Any])
async def invite_users_to_event(
    event_id: int,
    user_ids: List[int] = Body(..., min_items=1, max_items=50),
    message: Optional[str] = Body(None, max_length=500),
    expires_at: Optional[datetime] = Body(None),
    user: User = Depends(get_current_user),
):
    """
    Invite multiple users to an event (host only).
    
    - **Auth**: Required
    - **Permission**: Event host only
    - **Body**: 
      - `user_ids`: List of user IDs to invite (1-50)
      - `message`: Optional personal message
      - `expires_at`: Optional expiration date
    - **Returns**: Summary of created invitations
    """
    event = await get_event_by_id(event_id)
    
    if not check_event_permission(user, event, action="edit"):
        raise AuthorizationError("Only the event host can invite users", code="NOT_HOST")
    
    @sync_to_async
    @transaction.atomic
    def create_invitations():
        # Validate users exist
        valid_users = list(User.objects.filter(id__in=user_ids, is_active=True))
        
        if len(valid_users) != len(user_ids):
            invalid_ids = set(user_ids) - {u.id for u in valid_users}
            raise ValidationError(f"Invalid user IDs: {list(invalid_ids)}", code="INVALID_USER_IDS")
        
        created_invites = []
        skipped_count = 0
        errors = []
        
        for invited_user in valid_users:
            try:
                # Get UserProfile for invited_user first (EventInvite requires UserProfile)
                from users.models import UserProfile
                try:
                    invited_user_profile = invited_user.profile
                except UserProfile.DoesNotExist:
                    invited_user_profile, _ = UserProfile.objects.get_or_create(user=invited_user)
                
                # Check if invite already exists
                existing = EventInvite.objects.filter(
                    event=event,
                    invited_user=invited_user_profile
                ).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Create invitation
                invite = EventInvite.objects.create(
                    event=event,
                    host=event.host,
                    invited_user=invited_user_profile,
                    message=message or "",
                    status='pending',
                    expires_at=expires_at,
                )
                
                # Send notification (fire and forget in sync context)
                try:
                    from notifications.models import Notification
                    Notification.objects.create(
                        recipient=invited_user_profile,
                        sender=event.host,
                        type='event_invite',
                        title=f"You're Invited: {event.title}",
                        message=f"You've been invited to attend '{event.title}'!",
                        metadata={"event_id": event.id, "invite_id": invite.id},
                        reference_type="EventInvite",
                        reference_id=invite.id
                    )
                except Exception as e:
                    logger.error(f"Failed to send notification: {str(e)}")
                
                created_invites.append(invite)
            except Exception as e:
                errors.append({"user_id": invited_user.id, "error": str(e)})
        
        logger.info(f"Created {len(created_invites)} invitations for event {event_id}")
        
        return {
            "success": len(errors) == 0,
            "created_count": len(created_invites),
            "skipped_count": skipped_count,
            "errors": errors,
            "invites": [
                {
                    "invite_id": inv.id,
                    "user_id": inv.invited_user.id,
                    "user_name": inv.invited_user.username,
                    "status": inv.status,
                    "message": inv.message,
                }
                for inv in created_invites
            ],
        }
    
    return await create_invitations()


# @router.get("/{event_id}/invitations", response_model=List[Dict[str, Any]])
# NOTE: Duplicate route - use events_attendance.py router instead
async def _list_event_invitations_DUPLICATE(
    event_id: int,
    status_filter: Optional[str] = Query(None, pattern="^(pending|accepted|declined|expired)$"),
    user: User = Depends(get_current_user),
):
    """
    List all invitations for an event (host only).
    
    - **Auth**: Required
    - **Permission**: Event host only
    - **Query Params**: Optional status_filter
    - **Returns**: List of invitations with user details
    """
    event = await get_event_by_id(event_id)
    
    if not check_event_permission(user, event, action="edit"):
        raise AuthorizationError("Only the event host can view invitations", code="NOT_HOST")
    
    @sync_to_async
    def get_invitations():
        queryset = EventInvite.objects.select_related("invited_user", "host").filter(
            event=event
        ).order_by("-created_at")
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return [
            {
                "invite_id": inv.id,
                "user_id": inv.invited_user.id,
                "user_name": inv.invited_user.username,
                "status": inv.status,
                "message": inv.message,
                "created_at": inv.created_at,
            }
            for inv in queryset
        ]
    
    return await get_invitations()


# @router.put("/invitations/{invite_id}/respond", response_model=Dict[str, Any])
# NOTE: Duplicate route - use events_attendance.py router instead
async def _respond_to_invitation_DUPLICATE(
    invite_id: int,
    response: str = Body(..., pattern="^(going|not_going)$"),
    message: Optional[str] = Body(None, max_length=200),
    user: User = Depends(get_current_user),
):
    """
    Respond to an event invitation (Going or Not Going).
    
    - **Auth**: Required
    - **Body**: 
      - `response`: "going" or "not_going"
      - `message`: Optional response message
    - **Returns**: Updated invitation status
    - **Side Effects**: 
      - If "going" for free event: Creates attendee and ticket
      - If "going" for paid event: Creates attendee, requires payment
      - Sends notification to host
    """
    @sync_to_async
    @transaction.atomic
    def process_response():
        from users.models import UserProfile
        # Get UserProfile for the user
        try:
            user_profile = user.profile
        except UserProfile.DoesNotExist:
            user_profile, _ = UserProfile.objects.get_or_create(user=user)
        
        try:
            invite = EventInvite.objects.select_related("event", "invited_user", "event__host").get(
                id=invite_id,
                invited_user=user_profile,
                status='pending'
            )
        except EventInvite.DoesNotExist:
            raise NotFoundError("Invitation not found or already responded", code="INVITATION_NOT_FOUND")
        
        # Check expiration
        if invite.expires_at and invite.expires_at < timezone.now():
            invite.status = 'expired'
            invite.save()
            raise ValidationError("This invitation has expired", code="INVITATION_EXPIRED")
        
        event = invite.event
        
        if response == 'going':
            invite.status = 'accepted'
            invite.save(update_fields=['status', 'updated_at'])
            
            # Check capacity
            if event.max_capacity > 0:
                current_count = EventAttendee.objects.filter(event=event, status='going').count()
                if current_count + 1 > event.max_capacity:
                    raise ValidationError("Event is at full capacity", code="CAPACITY_FULL")
            
            # Create attendee record
            attendee, created = EventAttendee.objects.get_or_create(
                event=event,
                user=user,
                defaults={
                    'invite': invite,
                    'status': 'going',
                    'seats': 1,
                    'is_paid': event.is_paid,
                    'price_paid': Decimal('0.00') if not event.is_paid else event.ticket_price,
                }
            )
            
            # Update invite if attendee already existed
            if not created and not attendee.invite:
                attendee.invite = invite
                attendee.save(update_fields=['invite', 'updated_at'])
            
            # For free events, generate ticket immediately
            if not event.is_paid:
                ticket_secret = generate_ticket_secret()
                attendance_record, record_created = AttendanceRecord.objects.get_or_create(
                    event=event,
                    user=user,
                    defaults={
                        'status': 'going',
                        'payment_status': 'unpaid',
                        'ticket_secret': ticket_secret,
                        'seats': 1,
                    }
                )
                
                # Update if already exists
                if not record_created:
                    if not attendance_record.ticket_secret:
                        attendance_record.ticket_secret = ticket_secret
                    attendance_record.status = 'going'
                    attendance_record.save(update_fields=['ticket_secret', 'status', 'updated_at'])
            
            # Update event going_count
            event.going_count = EventAttendee.objects.filter(event=event, status='going').count()
            event.save(update_fields=['going_count'])
            
            # Notify host (fire and forget in sync context)
            try:
                from notifications.models import Notification
                from users.models import UserProfile
                # Get UserProfile for the user responding to the invitation
                try:
                    user_profile = user.profile
                except UserProfile.DoesNotExist:
                    user_profile, _ = UserProfile.objects.get_or_create(user=user)
                Notification.objects.create(
                    recipient=event.host,
                    sender=user_profile,
                    type='event_invite',
                    title=f"Invitation Accepted: {event.title}",
                    message=f"{user.username} has accepted your invitation to '{event.title}'",
                    metadata={"event_id": event.id, "invite_id": invite.id, "user_id": user.id},
                    reference_type="EventInvite",
                    reference_id=invite.id
                )
            except Exception as e:
                logger.error(f"Failed to send notification: {str(e)}")
            
            logger.info(f"Invitation {invite_id} accepted by user {user.id}")
            
        elif response == 'not_going':
            invite.status = 'declined'
            invite.save(update_fields=['status', 'updated_at'])
            
            # Notify host (fire and forget in sync context)
            try:
                from notifications.models import Notification
                from users.models import UserProfile
                # Get UserProfile for the user responding to the invitation
                try:
                    user_profile = user.profile
                except UserProfile.DoesNotExist:
                    user_profile, _ = UserProfile.objects.get_or_create(user=user)
                Notification.objects.create(
                    recipient=event.host,
                    sender=user_profile,
                    type='event_invite',
                    title=f"Invitation Declined: {event.title}",
                    message=f"{user.username} has declined your invitation to '{event.title}'",
                    metadata={"event_id": event.id, "invite_id": invite.id, "user_id": user.id},
                    reference_type="EventInvite",
                    reference_id=invite.id
                )
            except Exception as e:
                logger.error(f"Failed to send notification: {str(e)}")
            
            logger.info(f"Invitation {invite_id} declined by user {user.id}")
        
        return {
            "invite_id": invite.id,
            "status": invite.status,
            "event_id": event.id,
            "event_title": event.title,
            "is_paid": event.is_paid,
            "requires_payment": response == 'going' and event.is_paid,
        }
    
    return await process_response()


# ============================================================================
# Ticket Management Endpoints
# ============================================================================

# @router.get("/{event_id}/my-ticket", response_model=Dict[str, Any])
# NOTE: Duplicate route - use events_attendance.py router instead
async def _get_my_ticket_for_event_DUPLICATE(
    event_id: int = Path(..., description="Event ID"),
    user: User = Depends(get_current_user),
):
    """
    Get ticket for a specific event.
    
    - **Auth**: Required
    - **Returns**: Ticket details with secret code and QR code data
    """
    try:
        event = await get_event_by_id(event_id)
    except NotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Event {event_id} not found"
        )
    
    @sync_to_async
    def get_ticket():
        try:
            ticket = AttendanceRecord.objects.select_related("event").get(
                event=event,
                user=user,
                status='going'
            )
            return {
                "ticket_id": ticket.id,
                "event_id": ticket.event.id,
                "event_title": ticket.event.title,
                "event_start_time": ticket.event.start_time.isoformat(),
                "event_end_time": ticket.event.end_time.isoformat(),
                "ticket_secret": ticket.ticket_secret,
                "seats": ticket.seats,
                "is_paid": ticket.event.is_paid,
                "payment_status": ticket.payment_status,
                "status": ticket.status,
                "created_at": ticket.created_at.isoformat(),
                "qr_code_data": f"EVENT:{ticket.event.id}:TICKET:{ticket.ticket_secret}",
            }
        except AttendanceRecord.DoesNotExist:
            raise NotFoundError("No ticket found for this event", code="TICKET_NOT_FOUND")
        except Exception as e:
            logger.error(f"Error getting ticket for event {event_id}: {str(e)}", exc_info=True)
            raise ValidationError(
                "Unable to retrieve your ticket. Please try again later.",
                code="TICKET_RETRIEVAL_FAILED",
                details={"error": str(e)}
            )
    
    try:
        return await get_ticket()
    except (NotFoundError, AuthorizationError) as e:
        # Custom exceptions already have user-friendly messages and proper status codes
        raise
