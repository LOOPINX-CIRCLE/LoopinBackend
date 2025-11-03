"""
Production-ready Events API router for FastAPI.
Implements high-performance CRUD operations with Django ORM, JWT auth, and optimized queries.
CTO-style implementation according to complete ERD.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
import jwt
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    Path,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Prefetch
from asgiref.sync import sync_to_async
import logging

from core.utils.logger import get_logger
from core.exceptions import AuthorizationError, NotFoundError, ValidationError
from events.models import Event, Venue, EventRequest, EventInvite, EventAttendee, EventInterestMap, EventImage
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
    
    user = await sync_to_async(User.objects.get)(id=user_id)
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
    if event.host == user:
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
) -> tuple[List[Event], int]:
    """
    Get optimized events queryset with filtering and pagination.
    
    Returns:
        Tuple of (events list, total count)
    """
    # Base queryset with select_related and prefetch_related
    queryset = Event.objects.select_related("host", "venue").filter(is_active=True)
    
    # Apply filters
    if host_id:
        queryset = queryset.filter(host_id=host_id)
    if venue_id:
        queryset = queryset.filter(venue_id=venue_id)
    if status:
        queryset = queryset.filter(status=status)
    if is_public is not None:
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
    
    # Get total count before pagination
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
        raise NotFoundError(f"Event {event_id} not found", code="EVENT_NOT_FOUND")


@sync_to_async
def create_event_with_relationships(
    host: User,
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
    """Create event with all relationships"""
    if cover_images is None:
        cover_images = []
    if event_interest_ids is None:
        event_interest_ids = []
    
    with transaction.atomic():
        venue = None
        if venue_id:
            try:
                venue = Venue.objects.get(id=venue_id, is_active=True)
            except Venue.DoesNotExist:
                raise ValidationError(f"Venue {venue_id} not found", code="VENUE_NOT_FOUND")
        
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
    """Update event with permission check"""
    try:
        event = Event.objects.select_related("host", "venue").get(id=event_id, is_active=True)
    except Event.DoesNotExist:
        raise NotFoundError(f"Event {event_id} not found", code="EVENT_NOT_FOUND")
    
    # Check permission
    if not check_event_permission(user, event, action="edit"):
        raise AuthorizationError(
            f"User {user.id} cannot edit event {event_id}",
            code="PERMISSION_DENIED",
        )
    
    with transaction.atomic():
        # Handle venue update
        if "venue_id" in update_data:
            venue_id = update_data.pop("venue_id")
            if venue_id is None:
                event.venue = None
            else:
                try:
                    venue = Venue.objects.get(id=venue_id, is_active=True)
                    event.venue = venue
                except Venue.DoesNotExist:
                    raise ValidationError(f"Venue {venue_id} not found", code="VENUE_NOT_FOUND")
        
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
        raise NotFoundError(f"Event {event_id} not found", code="EVENT_NOT_FOUND")
    
    # Check permission
    if not check_event_permission(user, event, action="delete"):
        raise AuthorizationError(
            f"User {user.id} cannot delete event {event_id}",
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
    """Create venue"""
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
    
    logger.info(f"Venue created: {venue.id}")
    return venue


@sync_to_async
def get_venue_by_id(venue_id: int) -> Venue:
    """Get venue by ID"""
    try:
        return Venue.objects.get(id=venue_id, is_active=True)
    except Venue.DoesNotExist:
        raise NotFoundError(f"Venue {venue_id} not found", code="VENUE_NOT_FOUND")


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
    )
    
    # Filter private events if not authenticated
    filtered_events = []
    for event in events:
        if event.is_public or (user and event.host == user):
            filtered_events.append(event)
    
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "data": [EventResponse.from_orm(e, include_interests=True).model_dump() for e in filtered_events],
    }


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event_endpoint(
    event_data: EventCreate,
    user: User = Depends(get_current_user),
):
    """
    Create a new event with all ERD fields.
    
    - **Auth**: Required (JWT)
    - **Validation**: Title, date/time validation, capacity checks, pricing
    - **Performance**: Atomic transaction with select_related
    - **Features**: Supports venue linking, event interests, pricing, capacity, restrictions
    """
    event = await create_event_with_relationships(
        host=user,
        title=event_data.title,
        description=event_data.description,
        start_time=event_data.start_time,
        end_time=event_data.end_time,
        venue_id=event_data.venue_id,
        venue_text=event_data.venue_text,
        status=event_data.status,
        is_public=event_data.is_public,
        max_capacity=event_data.max_capacity,
        is_paid=event_data.is_paid,
        ticket_price=float(event_data.ticket_price),
        allow_plus_one=event_data.allow_plus_one,
        gst_number=event_data.gst_number or "",
        allowed_genders=event_data.allowed_genders,
        cover_images=event_data.cover_images,
        event_interest_ids=event_data.event_interest_ids,
    )
    
    # Refresh from DB to get all relationships
    event = await get_event_by_id(event.id, include_interests=True)
    return EventResponse.from_orm(event, include_interests=True)


# ============================================================================
# Venue Endpoints (MUST BE BEFORE /{event_id} ROUTE)
# ============================================================================

@router.get("/venues", response_model=Dict[str, Any])
async def list_venues(
    city: Optional[str] = Query(None, description="Filter by city"),
    venue_type: Optional[str] = Query(None, description="Filter by venue type"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
):
    """List venues with filtering"""
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
    """Create a new venue"""
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


@router.get("/venues/{venue_id}", response_model=VenueResponse)
async def get_venue(
    venue_id: int = Path(..., description="Venue ID"),
):
    """Get venue by ID"""
    venue = await get_venue_by_id(venue_id)
    return VenueResponse.from_orm(venue)


# ============================================================================
# Event Detail Endpoints
# ============================================================================

@router.get("/{event_id}", response_model=EventResponse)
async def get_event(
    event_id: int = Path(..., description="Event ID"),
    user: Optional[User] = Depends(get_optional_user),
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
            raise NotFoundError(f"Event {event_id} not found", code="EVENT_NOT_FOUND")
    
    event = await get_event_with_permissions()
    
    # Check permissions for soft-deleted events
    if not event.is_active and (not user or event.host != user):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Event not found",
        )
    
    # Check permissions for private events
    if not event.is_public and (not user or event.host != user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view this event",
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
    - **Features**: Supports partial updates, venue changes, interest updates
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to view requests",
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
    event = await get_event_by_id(event_id)
    
    @sync_to_async
    @transaction.atomic
    def create_request():
        # Check if request already exists
        existing = EventRequest.objects.filter(event=event, requester=user).first()
        if existing:
            if existing.status == 'pending':
                raise ValidationError("You already have a pending request", code="DUPLICATE_REQUEST")
            if existing.status == 'accepted':
                raise ValidationError("You are already accepted", code="ALREADY_ACCEPTED")
        
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
    
    request = await create_request()
    
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
