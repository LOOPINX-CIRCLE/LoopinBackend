"""
Event Attendance, Requests, Invitations, and Ticket Management API Router
CTO-Level Production Implementation

This module provides comprehensive endpoints for:
- User event requests (create, check status)
- Host request management (view, accept/decline single and bulk)
- Host invitations (create, manage)
- User invitation responses (Going/Not Going)
- Attendance confirmation (free and paid events)
- Ticket generation and viewing
- User profile visibility for hosts
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
import secrets
import string
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    Path,
    Body,
)
from fastapi.security import HTTPBearer
from django.contrib.auth.models import User
from django.db import transaction
from django.db.models import Q, Prefetch
from django.utils import timezone
from asgiref.sync import sync_to_async
from pydantic import BaseModel, Field, validator
import logging

from core.utils.logger import get_logger
from core.exceptions import ValidationError, NotFoundError, AuthorizationError, AuthenticationError
from events.models import (
    Event,
    EventRequest,
    EventInvite,
    EventAttendee,
)
from attendances.models import AttendanceRecord
from users.models import UserProfile

logger = get_logger(__name__)
router = APIRouter(prefix="/events", tags=["events"])
security = HTTPBearer()


# ============================================================================
# Pydantic Schemas
# ============================================================================

class RequestStatusResponse(BaseModel):
    """Response schema for user's request status"""
    request_id: int
    event_id: int
    event_title: str
    status: str
    message: Optional[str] = None
    host_message: Optional[str] = None
    seats_requested: int
    created_at: datetime
    updated_at: datetime
    can_confirm: bool = Field(False, description="Whether user can confirm attendance after acceptance")


class BulkRequestActionRequest(BaseModel):
    """Schema for bulk accept/decline requests"""
    request_ids: List[int] = Field(..., min_items=1, max_items=100, description="List of request IDs")
    host_message: Optional[str] = Field(None, max_length=500, description="Optional message for all requests")
    action: str = Field(..., regex="^(accept|decline)$", description="Action to perform: accept or decline")


class BulkRequestActionResponse(BaseModel):
    """Response for bulk request actions"""
    success: bool
    processed_count: int
    accepted_count: int = 0
    declined_count: int = 0
    errors: List[Dict[str, Any]] = Field(default_factory=list)


class InviteUsersRequest(BaseModel):
    """Schema for inviting users to an event"""
    user_ids: List[int] = Field(..., min_items=1, max_items=50, description="List of user IDs to invite")
    message: Optional[str] = Field(None, max_length=500, description="Personal message for invitations")
    expires_at: Optional[datetime] = Field(None, description="Optional expiration date for invitations")


class InviteResponse(BaseModel):
    """Response for invitation creation"""
    invite_id: int
    user_id: int
    user_name: str
    status: str
    message: Optional[str] = None


class BulkInviteResponse(BaseModel):
    """Response for bulk invitation creation"""
    success: bool
    created_count: int
    skipped_count: int = 0
    errors: List[Dict[str, Any]] = Field(default_factory=list)
    invites: List[InviteResponse] = Field(default_factory=list)


class InvitationResponseRequest(BaseModel):
    """Schema for responding to an invitation"""
    response: str = Field(..., regex="^(going|not_going)$", description="Response: going or not_going")
    message: Optional[str] = Field(None, max_length=200, description="Optional response message")


class AttendanceConfirmationRequest(BaseModel):
    """Schema for confirming attendance after request acceptance"""
    seats: int = Field(1, ge=1, le=10, description="Number of seats to confirm")


class TicketResponse(BaseModel):
    """Response schema for ticket information"""
    ticket_id: int
    event_id: int
    event_title: str
    event_start_time: datetime
    event_end_time: datetime
    ticket_secret: str
    seats: int
    is_paid: bool
    payment_status: Optional[str] = None
    status: str
    created_at: datetime
    qr_code_data: Optional[str] = Field(None, description="QR code data for ticket scanning")


class UserProfileSummaryResponse(BaseModel):
    """Summary user profile for host viewing"""
    user_id: int
    name: str
    phone_number: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[str] = None
    location: Optional[str] = None
    profile_pictures: List[str] = Field(default_factory=list)
    event_interests: List[Dict[str, str]] = Field(default_factory=list)
    is_verified: bool


# ============================================================================
# Helper Functions
# ============================================================================

@sync_to_async
def get_current_user_from_token(token: str) -> User:
    """Get current user from JWT token"""
    import jwt
    from django.conf import settings
    
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise AuthenticationError(
                "Your session has expired. Please log in again.",
                code="INVALID_TOKEN"
            )
        
        user = User.objects.get(id=user_id, is_active=True)
        return user
    except jwt.ExpiredSignatureError:
        raise AuthenticationError(
            "Your session has expired. Please log in again.",
            code="TOKEN_EXPIRED"
        )
    except (jwt.InvalidTokenError, User.DoesNotExist):
        raise AuthenticationError(
            "Invalid authentication. Please log in again.",
            code="INVALID_TOKEN"
        )


async def get_current_user(credentials=Depends(security)) -> User:
    """Dependency to get current authenticated user"""
    return await get_current_user_from_token(credentials.credentials)


@sync_to_async
def get_event_with_checks(event_id: int, user: User) -> Event:
    """Get event with permission checks"""
    try:
        event = Event.objects.select_related("host", "venue").get(id=event_id, is_active=True)
    except Event.DoesNotExist:
        raise NotFoundError(
            f"The event you're looking for doesn't exist or has been removed.",
            code="EVENT_NOT_FOUND"
        )
    return event


@sync_to_async
def check_host_permission(user: User, event: Event) -> bool:
    """Check if user is the event host"""
    return event.host == user


def generate_ticket_secret() -> str:
    """Generate unique 32-character ticket secret"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))


def send_notification(
    recipient: 'UserProfile', 
    notification_type: str, 
    title: str, 
    message: str, 
    data: Dict[str, Any] = None,
    sender: Optional['UserProfile'] = None,
    reference_type: Optional[str] = None,
    reference_id: Optional[int] = None
):
    """
    Send notification to user profile.
    
    This is a synchronous function that can be called from sync contexts
    (like inside @sync_to_async decorated functions).
    
    Args:
        recipient: UserProfile receiving the notification
        notification_type: Type of notification
        title: Notification title
        message: Notification message
        data: Optional metadata dictionary (stored in metadata field)
        sender: Optional UserProfile sending the notification
        reference_type: Optional related model type
        reference_id: Optional related object ID
    """
    try:
        from notifications.models import Notification
        Notification.objects.create(
            recipient=recipient,
            sender=sender,
            type=notification_type,
            title=title,
            message=message,
            metadata=data or {},
            reference_type=reference_type or "",
            reference_id=reference_id,
        )
        logger.info(f"Notification sent to user profile {recipient.id}: {notification_type}")
    except ImportError:
        logger.warning("Notifications module not available, skipping notification")
    except Exception as e:
        logger.error(f"Failed to send notification: {str(e)}", exc_info=True)


# ============================================================================
# User Request Endpoints
# ============================================================================

@router.get("/my-requests", response_model=List[RequestStatusResponse])
async def get_my_requests(
    status_filter: Optional[str] = Query(None, regex="^(pending|accepted|declined|cancelled)$"),
    user: User = Depends(get_current_user),
):
    """
    Get all event requests made by the current user.
    
    - **Auth**: Required
    - **Query Params**: 
      - `status_filter`: Optional filter by status (pending, accepted, declined, cancelled)
    - **Returns**: List of user's event requests with status
    """
    @sync_to_async
    def get_requests():
        queryset = EventRequest.objects.select_related("event", "event__host", "event__venue").filter(
            requester=user
        ).order_by("-created_at")
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return list(queryset)
    
    requests = await get_requests()
    
    return [
        RequestStatusResponse(
            request_id=r.id,
            event_id=r.event.id,
            event_title=r.event.title,
            status=r.status,
            message=r.message,
            host_message=r.host_message,
            seats_requested=r.seats_requested,
            created_at=r.created_at,
            updated_at=r.updated_at,
            can_confirm=r.status == 'accepted' and not EventAttendee.objects.filter(
                event=r.event,
                user=user,
                status='going'
            ).exists(),
        )
        for r in requests
    ]


@router.get("/{event_id}/my-request", response_model=RequestStatusResponse)
async def get_my_request_for_event(
    event_id: int,
    user: User = Depends(get_current_user),
):
    """
    Get the current user's request status for a specific event.
    
    - **Auth**: Required
    - **Returns**: Request status if exists, 404 if not found
    """
    event = await get_event_with_checks(event_id, user)
    
    @sync_to_async
    def get_request():
        try:
            return EventRequest.objects.select_related("event").get(
                event=event,
                requester=user
            )
        except EventRequest.DoesNotExist:
            raise NotFoundError(
                "You haven't submitted a request to attend this event yet.",
                code="REQUEST_NOT_FOUND"
            )
    
    request = await get_request()
    
    can_confirm = await sync_to_async(lambda: request.status == 'accepted' and not EventAttendee.objects.filter(
        event=event,
        user=user,
        status='going'
    ).exists())()
    
    return RequestStatusResponse(
        request_id=request.id,
        event_id=request.event.id,
        event_title=request.event.title,
        status=request.status,
        message=request.message,
        host_message=request.host_message,
        seats_requested=request.seats_requested,
        created_at=request.created_at,
        updated_at=request.updated_at,
        can_confirm=can_confirm,
    )


# ============================================================================
# Host Request Management Endpoints
# ============================================================================

@router.get("/{event_id}/requests/{request_id}/profile", response_model=UserProfileSummaryResponse)
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
    event = await get_event_with_checks(event_id, user)
    
    if not await check_host_permission(user, event):
        raise AuthorizationError(
            "Only the event host can view requester profiles.",
            code="PERMISSION_DENIED"
        )
    
    @sync_to_async
    def get_request_with_profile():
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
            raise NotFoundError(
                "The request you're looking for doesn't exist or has already been processed.",
                code="REQUEST_NOT_FOUND"
            )
    
    profile_data = await get_request_with_profile()
    return UserProfileSummaryResponse(**profile_data)


@router.put("/{event_id}/requests/{request_id}/accept", response_model=RequestStatusResponse)
async def accept_event_request(
    event_id: int,
    request_id: int,
    host_message: Optional[str] = Body(None, max_length=500),
    user: User = Depends(get_current_user),
):
    """
    Accept a single event request (host only).
    
    - **Auth**: Required
    - **Permission**: Event host only
    - **Body**: Optional host_message
    - **Returns**: Updated request status
    - **Side Effects**: 
      - Updates request status to 'accepted'
      - Sends notification to requester
      - Updates event going_count
    """
    event = await get_event_with_checks(event_id, user)
    
    if not await check_host_permission(user, event):
        raise AuthorizationError(
            "Only the event host can accept requests for this event.",
            code="PERMISSION_DENIED"
        )
    
    @sync_to_async
    @transaction.atomic
    def accept_request():
        try:
            request = EventRequest.objects.select_related("requester", "event").get(
                id=request_id,
                event=event,
                status='pending'
            )
        except EventRequest.DoesNotExist:
            raise NotFoundError(
                "The request you're trying to accept doesn't exist or has already been processed.",
                code="REQUEST_NOT_FOUND"
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
        
        # Send notification
        send_notification(
            recipient=request.requester,
            notification_type='event_request',
            title=f"Request Accepted: {event.title}",
            message=f"Your request to attend '{event.title}' has been accepted! Please confirm your attendance.",
            data={"action": "accepted"},
            sender=event.host,
            reference_type="EventRequest",
            reference_id=request.id
        )
        
        logger.info(f"Event request {request_id} accepted by host {user.id}")
        return request
    
    request = await accept_request()
    
    return RequestStatusResponse(
        request_id=request.id,
        event_id=request.event.id,
        event_title=request.event.title,
        status=request.status,
        message=request.message,
        host_message=request.host_message,
        seats_requested=request.seats_requested,
        created_at=request.created_at,
        updated_at=request.updated_at,
        can_confirm=True,
    )


@router.put("/{event_id}/requests/{request_id}/decline", response_model=RequestStatusResponse)
async def decline_event_request(
    event_id: int,
    request_id: int,
    host_message: Optional[str] = Body(None, max_length=500),
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
    event = await get_event_with_checks(event_id, user)
    
    if not await check_host_permission(user, event):
        raise AuthorizationError(
            "Only the event host can decline requests for this event.",
            code="PERMISSION_DENIED"
        )
    
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
            raise NotFoundError(
                "The request you're trying to decline doesn't exist or has already been processed.",
                code="REQUEST_NOT_FOUND"
            )
        
        request.status = 'declined'
        if host_message:
            request.host_message = host_message
        request.save(update_fields=['status', 'host_message', 'updated_at'])
        
        # Update event requests count
        event.requests_count = EventRequest.objects.filter(event=event, status='pending').count()
        event.save(update_fields=['requests_count'])
        
        # Send notification
        send_notification(
            recipient=request.requester,
            notification_type='event_request',
            title=f"Request Declined: {event.title}",
            message=f"Your request to attend '{event.title}' has been declined.",
            data={"action": "declined"},
            sender=event.host,
            reference_type="EventRequest",
            reference_id=request.id
        )
        
        logger.info(f"Event request {request_id} declined by host {user.id}")
        return request
    
    request = await decline_request()
    
    return RequestStatusResponse(
        request_id=request.id,
        event_id=request.event.id,
        event_title=request.event.title,
        status=request.status,
        message=request.message,
        host_message=request.host_message,
        seats_requested=request.seats_requested,
        created_at=request.created_at,
        updated_at=request.updated_at,
        can_confirm=False,
    )


@router.post("/{event_id}/requests/bulk-action", response_model=BulkRequestActionResponse)
async def bulk_accept_decline_requests(
    event_id: int,
    action_data: BulkRequestActionRequest,
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
    event = await get_event_with_checks(event_id, user)
    
    if not await check_host_permission(user, event):
        raise AuthorizationError(
            "Only the event host can perform bulk actions on requests for this event.",
            code="PERMISSION_DENIED"
        )
    
    @sync_to_async
    @transaction.atomic
    def process_bulk_action():
        # Get all pending requests
        requests = list(EventRequest.objects.select_related("requester", "event").filter(
            id__in=action_data.request_ids,
            event=event,
            status='pending'
        ))
        
        if not requests:
            raise ValidationError(
                "No pending requests found with the provided IDs. They may have already been processed.",
                code="NO_PENDING_REQUESTS"
            )
        
        accepted_count = 0
        declined_count = 0
        errors = []
        
        if action_data.action == 'accept':
            # Check total capacity
            current_count = EventAttendee.objects.filter(event=event, status='going').count()
            total_seats_requested = sum(r.seats_requested for r in requests)
            
            if event.max_capacity > 0 and current_count + total_seats_requested > event.max_capacity:
                available = event.max_capacity - current_count
                raise ValidationError(
                    f"Cannot accept all requests. The event has reached its capacity. Only {available} seat(s) available, but {total_seats_requested} seat(s) requested.",
                    code="CAPACITY_EXCEEDED",
                    details={
                        "current_attendees": current_count,
                        "max_capacity": event.max_capacity,
                        "requested_seats": total_seats_requested,
                        "available_seats": available
                    }
                )
            
            # Accept all requests
            for request in requests:
                try:
                    request.status = 'accepted'
                    if action_data.host_message:
                        request.host_message = action_data.host_message
                    request.save(update_fields=['status', 'host_message', 'updated_at'])
                    
                    # Send notification
                    send_notification(
                        recipient=request.requester,
                        notification_type='event_request',
                        title=f"Request Accepted: {event.title}",
                        message=f"Your request to attend '{event.title}' has been accepted!",
                        data={"action": "accepted"},
                        sender=event.host,
                        reference_type="EventRequest",
                        reference_id=request.id
                    )
                    
                    accepted_count += 1
                except Exception as e:
                    errors.append({"request_id": request.id, "error": str(e)})
        
        elif action_data.action == 'decline':
            # Decline all requests
            for request in requests:
                try:
                    request.status = 'declined'
                    if action_data.host_message:
                        request.host_message = action_data.host_message
                    request.save(update_fields=['status', 'host_message', 'updated_at'])
                    
                    # Send notification
                    send_notification(
                        recipient=request.requester,
                        notification_type='event_request',
                        title=f"Request Declined: {event.title}",
                        message=f"Your request to attend '{event.title}' has been declined.",
                        data={"action": "declined"},
                        sender=event.host,
                        reference_type="EventRequest",
                        reference_id=request.id
                    )
                    
                    declined_count += 1
                except Exception as e:
                    errors.append({"request_id": request.id, "error": str(e)})
        
        # Update event counts
        event.requests_count = EventRequest.objects.filter(event=event, status='pending').count()
        event.going_count = EventAttendee.objects.filter(event=event, status='going').count()
        event.save(update_fields=['requests_count', 'going_count'])
        
        logger.info(f"Bulk {action_data.action} processed: {accepted_count + declined_count} requests for event {event_id}")
        
        return {
            "processed_count": accepted_count + declined_count,
            "accepted_count": accepted_count,
            "declined_count": declined_count,
            "errors": errors,
        }
    
    result = await process_bulk_action()
    
    return BulkRequestActionResponse(
        success=len(result["errors"]) == 0,
        processed_count=result["processed_count"],
        accepted_count=result["accepted_count"],
        declined_count=result["declined_count"],
        errors=result["errors"],
    )


# ============================================================================
# Attendance Confirmation Endpoints (Free Events)
# ============================================================================

@router.post("/{event_id}/confirm-attendance", response_model=TicketResponse)
async def confirm_attendance_free_event(
    event_id: int,
    confirmation: AttendanceConfirmationRequest,
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
    - **Returns**: Generated ticket with secret code
    """
    event = await get_event_with_checks(event_id, user)
    
    @sync_to_async
    @transaction.atomic
    def confirm_attendance():
        # Check if request exists and is accepted
        try:
            request = EventRequest.objects.get(event=event, requester=user, status='accepted')
        except EventRequest.DoesNotExist:
            raise ValidationError(
                "You need to have an accepted request before confirming attendance. Please wait for the host to accept your request.",
                code="NO_ACCEPTED_REQUEST"
            )
        
        # Check if already confirmed
        existing_attendee = EventAttendee.objects.filter(event=event, user=user, status='going').first()
        if existing_attendee:
            raise ValidationError(
                "You have already confirmed your attendance for this event.",
                code="ALREADY_CONFIRMED"
            )
        
        # Check capacity
        if event.max_capacity > 0:
            current_count = EventAttendee.objects.filter(event=event, status='going').count()
            if current_count + confirmation.seats > event.max_capacity:
                available = event.max_capacity - current_count
                raise ValidationError(
                    f"The event is at full capacity. Only {available} seat(s) available, but {confirmation.seats} seat(s) requested.",
                    code="CAPACITY_FULL",
                    details={
                        "current_attendees": current_count,
                        "max_capacity": event.max_capacity,
                        "requested_seats": confirmation.seats,
                        "available_seats": available
                    }
                )
        
        # Create attendee record
        attendee = EventAttendee.objects.create(
            event=event,
            user=user,
            request=request,
            seats=confirmation.seats,
            status='going',
            is_paid=False,
            price_paid=Decimal('0.00'),
        )
        
        # Create attendance record with ticket
        ticket_secret = generate_ticket_secret()
        attendance_record = AttendanceRecord.objects.create(
            event=event,
            user=user,
            status='going',
            payment_status='unpaid',  # Free event
            ticket_secret=ticket_secret,
            seats=confirmation.seats,
        )
        
        # Update event going_count
        event.going_count = EventAttendee.objects.filter(event=event, status='going').count()
        event.save(update_fields=['going_count'])
        
        logger.info(f"Attendance confirmed for user {user.id} at event {event_id}, ticket: {ticket_secret}")
        
        return attendance_record
    
    attendance = await confirm_attendance()
    
    # Generate QR code data (placeholder - implement QR code generation service)
    qr_code_data = f"EVENT:{event.id}:TICKET:{attendance.ticket_secret}"
    
    return TicketResponse(
        ticket_id=attendance.id,
        event_id=event.id,
        event_title=event.title,
        event_start_time=event.start_time,
        event_end_time=event.end_time,
        ticket_secret=attendance.ticket_secret,
        seats=attendance.seats,
        is_paid=False,
        payment_status=attendance.payment_status,
        status=attendance.status,
        created_at=attendance.created_at,
        qr_code_data=qr_code_data,
    )


# ============================================================================
# Invitation Management Endpoints
# ============================================================================

@router.post("/{event_id}/invitations", response_model=BulkInviteResponse)
async def invite_users_to_event(
    event_id: int,
    invite_data: InviteUsersRequest,
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
    event = await get_event_with_checks(event_id, user)
    
    if not await check_host_permission(user, event):
        raise AuthorizationError(
            "Only the event host can invite users to this event.",
            code="PERMISSION_DENIED"
        )
    
    @sync_to_async
    @transaction.atomic
    def create_invitations():
        # Validate users exist
        valid_users = list(User.objects.filter(id__in=invite_data.user_ids, is_active=True))
        
        if len(valid_users) != len(invite_data.user_ids):
            invalid_ids = set(invite_data.user_ids) - {u.id for u in valid_users}
            raise ValidationError(
                f"Some of the user IDs you provided are invalid or don't exist: {list(invalid_ids)}. Please check and try again.",
                code="INVALID_USER_IDS",
                details={"invalid_user_ids": list(invalid_ids)}
            )
        
        created_invites = []
        skipped_count = 0
        errors = []
        
        for invited_user in valid_users:
            try:
                # Check if invite already exists
                existing = EventInvite.objects.filter(
                    event=event,
                    invited_user=invited_user
                ).first()
                
                if existing:
                    skipped_count += 1
                    continue
                
                # Create invitation
                invite = EventInvite.objects.create(
                    event=event,
                    host=user,
                    invited_user=invited_user,
                    message=invite_data.message or "",
                    status='pending',
                    expires_at=invite_data.expires_at,
                )
                
                # Send notification - need to get UserProfile for invited_user
                # Note: invited_user is currently a User object, need to get UserProfile
                try:
                    invited_user_profile = invited_user.profile
                except AttributeError:
                    from users.models import UserProfile
                    invited_user_profile, _ = UserProfile.objects.get_or_create(user=invited_user)
                
                send_notification(
                    recipient=invited_user_profile,
                    notification_type='event_invite',
                    title=f"You're Invited: {event.title}",
                    message=f"You've been invited to attend '{event.title}'!",
                    data={},
                    sender=event.host if hasattr(event.host, 'id') else None,
                    reference_type="EventInvite",
                    reference_id=invite.id
                )
                
                created_invites.append(invite)
            except Exception as e:
                errors.append({"user_id": invited_user.id, "error": str(e)})
        
        logger.info(f"Created {len(created_invites)} invitations for event {event_id}")
        
        return {
            "created_count": len(created_invites),
            "skipped_count": skipped_count,
            "errors": errors,
            "invites": created_invites,
        }
    
    result = await create_invitations()
    
    return BulkInviteResponse(
        success=len(result["errors"]) == 0,
        created_count=result["created_count"],
        skipped_count=result["skipped_count"],
        errors=result["errors"],
        invites=[
            InviteResponse(
                invite_id=invite.id,
                user_id=invite.invited_user.id,
                user_name=invite.invited_user.username,
                status=invite.status,
                message=invite.message,
            )
            for invite in result["invites"]
        ],
    )


@router.get("/{event_id}/invitations", response_model=List[InviteResponse])
async def list_event_invitations(
    event_id: int,
    status_filter: Optional[str] = Query(None, regex="^(pending|accepted|declined|expired)$"),
    user: User = Depends(get_current_user),
):
    """
    List all invitations for an event (host only).
    
    - **Auth**: Required
    - **Permission**: Event host only
    - **Query Params**: Optional status_filter
    - **Returns**: List of invitations with user details
    """
    event = await get_event_with_checks(event_id, user)
    
    if not await check_host_permission(user, event):
        raise AuthorizationError(
            "Only the event host can view invitations for this event.",
            code="PERMISSION_DENIED"
        )
    
    @sync_to_async
    def get_invitations():
        queryset = EventInvite.objects.select_related("invited_user", "host").filter(
            event=event
        ).order_by("-created_at")
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return list(queryset)
    
    invitations = await get_invitations()
    
    return [
        InviteResponse(
            invite_id=inv.id,
            user_id=inv.invited_user.id,
            user_name=inv.invited_user.username,
            status=inv.status,
            message=inv.message,
        )
        for inv in invitations
    ]


@router.get("/my-invitations", response_model=List[Dict[str, Any]])
async def get_my_invitations(
    status_filter: Optional[str] = Query(None, regex="^(pending|accepted|declined|expired)$"),
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
        queryset = EventInvite.objects.select_related(
            "event",
            "event__host",
            "event__venue",
            "host"
        ).filter(
            invited_user=user
        ).order_by("-created_at")
        
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        
        return list(queryset)
    
    invitations = await get_invitations()
    
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
        for inv in invitations
    ]


@router.put("/invitations/{invite_id}/respond", response_model=Dict[str, Any])
async def respond_to_invitation(
    invite_id: int,
    response_data: InvitationResponseRequest,
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
        try:
            invite = EventInvite.objects.select_related("event", "invited_user", "event__host").get(
                id=invite_id,
                invited_user=user,
                status='pending'
            )
        except EventInvite.DoesNotExist:
            raise NotFoundError(
                "The invitation you're looking for doesn't exist or you've already responded to it.",
                code="INVITATION_NOT_FOUND"
            )
        
        # Check expiration
        if invite.expires_at and invite.expires_at < timezone.now():
            invite.status = 'expired'
            invite.save()
            raise ValidationError(
                "This invitation has expired. Please contact the event host for a new invitation.",
                code="INVITATION_EXPIRED"
            )
        
        event = invite.event
        
        if response_data.response == 'going':
            invite.status = 'accepted'
            invite.save(update_fields=['status', 'updated_at'])
            
            # Check capacity
            if event.max_capacity > 0:
                current_count = EventAttendee.objects.filter(event=event, status='going').count()
                if current_count + 1 > event.max_capacity:
                    available = event.max_capacity - current_count
                    raise ValidationError(
                        f"The event is at full capacity. Only {available} seat(s) available.",
                        code="CAPACITY_FULL",
                        details={
                            "current_attendees": current_count,
                            "max_capacity": event.max_capacity,
                            "available_seats": available
                        }
                    )
            
            # Create attendee record
            attendee, created = EventAttendee.objects.get_or_create(
                event=event,
                user=user,
                defaults={
                    'status': 'going',
                    'seats': 1,
                    'is_paid': event.is_paid,
                    'price_paid': Decimal('0.00') if not event.is_paid else event.ticket_price,
                }
            )
            
            # For free events, generate ticket immediately
            if not event.is_paid:
                ticket_secret = generate_ticket_secret()
                AttendanceRecord.objects.get_or_create(
                    event=event,
                    user=user,
                    defaults={
                        'status': 'going',
                        'payment_status': 'unpaid',
                        'ticket_secret': ticket_secret,
                        'seats': 1,
                    }
                )
            
            # Update event going_count
            event.going_count = EventAttendee.objects.filter(event=event, status='going').count()
            event.save(update_fields=['going_count'])
            
            # Notify host - get UserProfile for user
            try:
                user_profile = user.profile
                user_display_name = user_profile.name or user_profile.phone_number or user.username
            except AttributeError:
                from users.models import UserProfile
                user_profile, _ = UserProfile.objects.get_or_create(user=user)
                user_display_name = user_profile.name or user_profile.phone_number or user.username
            
            send_notification(
                recipient=event.host,
                notification_type='event_invite',
                title=f"Invitation Accepted: {event.title}",
                message=f"{user_display_name} has accepted your invitation to '{event.title}'",
                data={},
                sender=user_profile,
                reference_type="EventInvite",
                reference_id=invite.id
            )
            
            logger.info(f"Invitation {invite_id} accepted by user {user.id}")
            
        elif response_data.response == 'not_going':
            invite.status = 'declined'
            invite.save(update_fields=['status', 'updated_at'])
            
            # Notify host - get UserProfile for user
            try:
                user_profile = user.profile
                user_display_name = user_profile.name or user_profile.phone_number or user.username
            except AttributeError:
                from users.models import UserProfile
                user_profile, _ = UserProfile.objects.get_or_create(user=user)
                user_display_name = user_profile.name or user_profile.phone_number or user.username
            
            send_notification(
                recipient=event.host,
                notification_type='event_invite',
                title=f"Invitation Declined: {event.title}",
                message=f"{user_display_name} has declined your invitation to '{event.title}'",
                data={},
                sender=user_profile,
                reference_type="EventInvite",
                reference_id=invite.id
            )
            
            logger.info(f"Invitation {invite_id} declined by user {user.id}")
        
        return {
            "invite_id": invite.id,
            "status": invite.status,
            "event_id": event.id,
            "event_title": event.title,
            "is_paid": event.is_paid,
            "requires_payment": response_data.response == 'going' and event.is_paid,
        }
    
    result = await process_response()
    return result


# ============================================================================
# Ticket Management Endpoints
# ============================================================================

@router.get("/my-tickets", response_model=List[TicketResponse])
async def get_my_tickets(
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
        
        return list(queryset)
    
    tickets = await get_tickets()
    
    return [
        TicketResponse(
            ticket_id=ticket.id,
            event_id=ticket.event.id,
            event_title=ticket.event.title,
            event_start_time=ticket.event.start_time,
            event_end_time=ticket.event.end_time,
            ticket_secret=ticket.ticket_secret,
            seats=ticket.seats,
            is_paid=ticket.event.is_paid,
            payment_status=ticket.payment_status,
            status=ticket.status,
            created_at=ticket.created_at,
            qr_code_data=f"EVENT:{ticket.event.id}:TICKET:{ticket.ticket_secret}",
        )
        for ticket in tickets
    ]


@router.get("/{event_id}/my-ticket", response_model=TicketResponse)
async def get_my_ticket_for_event(
    event_id: int,
    user: User = Depends(get_current_user),
):
    """
    Get ticket for a specific event.
    
    - **Auth**: Required
    - **Returns**: Ticket details with secret code and QR code data
    """
    event = await get_event_with_checks(event_id, user)
    
    @sync_to_async
    def get_ticket():
        try:
            return AttendanceRecord.objects.select_related("event").get(
                event=event,
                user=user,
                status='going'
            )
        except AttendanceRecord.DoesNotExist:
            raise NotFoundError(
                "You don't have a ticket for this event. Please confirm your attendance first.",
                code="TICKET_NOT_FOUND"
            )
    
    ticket = await get_ticket()
    
    return TicketResponse(
        ticket_id=ticket.id,
        event_id=ticket.event.id,
        event_title=ticket.event.title,
        event_start_time=ticket.event.start_time,
        event_end_time=ticket.event.end_time,
        ticket_secret=ticket.ticket_secret,
        seats=ticket.seats,
        is_paid=ticket.event.is_paid,
        payment_status=ticket.payment_status,
        status=ticket.status,
        created_at=ticket.created_at,
        qr_code_data=f"EVENT:{ticket.event.id}:TICKET:{ticket.ticket_secret}",
    )
