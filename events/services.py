"""
Business logic services for events.
"""

from django.utils import timezone
from django.db import transaction
from events.models import Event, EventRequest, EventInvite, EventAttendee
from core.exceptions import ValidationError
import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Payment Validation Utilities
# ============================================================================

def verify_payment_for_event(event: Event, user_profile) -> bool:
    """
    Verify that user has a successful payment for a paid event.
    
    Payment enforcement rule:
    - For paid events (event.is_paid == True), require PAYMENT_ORDER.status == 'paid'
    - For free events (event.is_paid == False), always return True
    
    Args:
        event: Event instance
        user_profile: UserProfile instance
        
    Returns:
        bool: True if payment verified (or event is free), False otherwise
    """
    # Free events don't require payment
    if not event.is_paid:
        return True
    
    # For paid events, check for successful payment order
    from payments.models import PaymentOrder
    
    paid_order = PaymentOrder.objects.filter(
        event=event,
        user=user_profile,
        status='paid',  # Only 'paid' status is accepted
    ).exists()
    
    return paid_order


def require_payment_for_event(event: Event, user_profile, action_name: str = "access this event"):
    """
    Enforce payment requirement for paid events.
    
    Raises ValidationError if payment is required but not found.
    
    Args:
        event: Event instance
        user_profile: UserProfile instance
        action_name: Description of action being blocked (for error message)
        
    Raises:
        ValidationError: If payment is required but not found
    """
    if event.is_paid:
        if not verify_payment_for_event(event, user_profile):
            raise ValidationError(
                f"Payment required to {action_name}. Please complete payment first.",
                code="PAYMENT_REQUIRED",
                details={
                    "event_id": event.id,
                    "event_title": event.title,
                    "is_paid": True,
                    "ticket_price": float(event.ticket_price) if event.ticket_price else 0,
                }
            )


def get_user_payment_status(event: Event, user_profile) -> dict:
    """
    Get payment status for user and event.
    
    Returns:
        dict: Payment status information
    """
    if not event.is_paid:
        return {
            "is_paid_event": False,
            "payment_required": False,
            "payment_status": "not_required",
        }
    
    from payments.models import PaymentOrder
    
    # Check for paid order
    paid_order = PaymentOrder.objects.filter(
        event=event,
        user=user_profile,
        status='paid',
    ).first()
    
    if paid_order:
        return {
            "is_paid_event": True,
            "payment_required": False,
            "payment_status": "paid",
            "order_id": paid_order.order_id,
        }
    
    # Check for pending/created orders
    pending_order = PaymentOrder.objects.filter(
        event=event,
        user=user_profile,
        status__in=['created', 'pending'],
    ).order_by('-created_at').first()
    
    if pending_order:
        return {
            "is_paid_event": True,
            "payment_required": True,
            "payment_status": pending_order.status,
            "order_id": pending_order.order_id,
        }
    
    return {
        "is_paid_event": True,
        "payment_required": True,
        "payment_status": "not_initiated",
    }


# ============================================================================
# Event Service
# ============================================================================

class EventService:
    """Service for event-related business logic"""
    
    @staticmethod
    @transaction.atomic
    def create_event(host, title, description, start_time, end_time, venue=None, 
                     status='draft', is_public=True, max_capacity=0, cover_images=None, auth_user=None):
        """
        Create a new event with validation.
        
        SECURITY ENFORCEMENT (IDENTITY MODEL):
        - host must be USER_PROFILE (not AUTH_USER)
        - AUTH_USER (admin) cannot create events as customers
        
        Args:
            host: UserProfile hosting the event
            title: Event title
            description: Event description
            start_time: Event start time
            end_time: Event end time
            venue: Optional venue
            status: Event status (default: draft)
            is_public: Is event public (default: True)
            max_capacity: Maximum capacity (default: 0 for unlimited)
            cover_images: List of cover image URLs
            auth_user: Optional AUTH_USER for identity enforcement check
        
        Returns:
            Event instance
            
        Raises:
            AuthorizationError: If AUTH_USER attempts to create event
        """
        # SECURITY: Identity enforcement - verify host is USER_PROFILE
        from users.models import UserProfile
        if not isinstance(host, UserProfile):
            from core.exceptions import ValidationError
            raise ValidationError(
                "Event host must be a UserProfile instance, not AUTH_USER.",
                code="INVALID_HOST_TYPE"
            )
        
        # SECURITY: If auth_user is provided, ensure it's not an admin creating events
        if auth_user:
            from django.contrib.auth.models import User
            if isinstance(auth_user, User) and (auth_user.is_staff or auth_user.is_superuser):
                from core.exceptions import AuthorizationError
                raise AuthorizationError(
                    "Admin accounts (AUTH_USER) cannot create events as customers. Only USER_PROFILE can create events.",
                    code="ADMIN_CANNOT_CREATE_EVENT"
                )
        
        if cover_images is None:
            cover_images = []
        
        # Validate times
        if end_time <= start_time:
            raise ValueError("End time must be after start time")
        
        if start_time < timezone.now():
            raise ValueError("Start time cannot be in the past")
        
        event = Event.objects.create(
            host=host,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            venue=venue,
            status=status,
            is_public=is_public,
            max_capacity=max_capacity,
            cover_images=cover_images
        )
        
        logger.info(f"Event created: {event.id} by {host.username}")
        return event
    
    @staticmethod
    def update_event_status(event, new_status):
        """
        Update event status.
        
        Triggers notifications when event goes live (published):
        - Notifies users matching event interests (excludes host)
        
        Args:
            event: Event instance
            new_status: New status
        
        Returns:
            Updated event instance
        """
        old_status = event.status
        if new_status not in [choice[0] for choice in Event._meta.get_field('status').choices]:
            raise ValueError(f"Invalid status: {new_status}")
        
        event.status = new_status
        event.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"Event {event.id} status updated from {old_status} to {new_status}")
        
        # Trigger "Event Goes Live" notification when status changes to 'published'
        if old_status != 'published' and new_status == 'published' and event.is_public:
            try:
                from notifications.services.dispatcher import get_push_dispatcher
                from notifications.services.messages import NotificationTemplate
                dispatcher = get_push_dispatcher()
                
                # Find users matching event interests (excluding host)
                matching_users = EventService._get_users_matching_event_interests(event)
                
                for user_profile in matching_users:
                    try:
                        dispatcher.send_template_notification(
                            recipient=user_profile,
                            template=NotificationTemplate.EVENT_LIVE,
                            context={
                                'event_name': event.title,
                                'host_name': event.host.name or event.host.username
                            },
                            sender=event.host,
                            reference_type='Event',
                            reference_id=event.id,
                            additional_data={
                                'event_id': event.id,
                            },
                        )
                    except Exception as e:
                        logger.error(f"Failed to send event_live notification to user {user_profile.id}: {str(e)}")
                        
            except Exception as e:
                # Never block status update on notification failure
                logger.error(f"Failed to send event_live push notifications: {str(e)}")
        
        return event
    
    @staticmethod
    def _get_users_matching_event_interests(event):
        """
        Get USER_PROFILEs matching event interests for discovery notifications.
        
        Rules:
        - Event must be public
        - Users must have matching event interests
        - Exclude event host
        - Return active users only
        
        Args:
            event: Event instance
            
        Returns:
            QuerySet of UserProfile instances
        """
        from users.models import UserProfile
        
        if not event.is_public:
            return UserProfile.objects.none()
        
        # Get event interest IDs
        event_interest_ids = list(
            event.interest_maps.values_list('event_interest_id', flat=True)
        )
        
        if not event_interest_ids:
            # No interests specified, return empty (or all users? - keeping it empty for now)
            return UserProfile.objects.none()
        
        # Find users with matching interests (excluding host)
        matching_users = UserProfile.objects.filter(
            event_interests__id__in=event_interest_ids,
            is_active=True,
        ).exclude(
            id=event.host.id
        ).distinct()
        
        return matching_users
    
    @staticmethod
    def cancel_event(event):
        """
        Cancel an event.
        
        Args:
            event: Event instance
        
        Returns:
            Updated event instance
        """
        event.status = 'cancelled'
        event.is_active = False
        event.save(update_fields=['status', 'is_active', 'updated_at'])
        
        logger.info(f"Event {event.id} cancelled")
        
        # Send push notifications to all paid attendees (non-blocking, best-effort)
        try:
            from notifications.services.dispatcher import get_push_dispatcher
            from events.models import EventAttendee
            dispatcher = get_push_dispatcher()
            
            # Get all paid attendees
            paid_attendees = EventAttendee.objects.filter(
                event=event,
                status='going',
                is_paid=True,
            ).select_related('user')
            
            for attendee in paid_attendees:
                try:
                    from notifications.services.messages import NotificationTemplate
                    dispatcher.send_template_notification(
                        recipient=attendee.user,
                        template=NotificationTemplate.EVENT_CANCELLED,
                        context={
                            'event_name': event.title
                        },
                        reference_type='Event',
                        reference_id=event.id,
                        additional_data={
                            'event_id': event.id,
                        },
                    )
                except Exception as e:
                    logger.error(f"Failed to send cancellation notification to attendee {attendee.user.id}: {str(e)}")
                    
        except Exception as e:
            # Never block event cancellation on notification failure
            logger.error(f"Failed to send event cancellation push notifications: {str(e)}")
        
        return event


# ============================================================================
# Event Request Service
# ============================================================================

class EventRequestService:
    """Service for event request business logic"""
    
    @staticmethod
    @transaction.atomic
    def create_request(requester, event, message='', seats_requested=1, auth_user=None):
        """
        Create an event request.
        
        SECURITY ENFORCEMENT (IDENTITY MODEL):
        - requester must be USER_PROFILE (not AUTH_USER)
        - AUTH_USER (admin) cannot make event requests
        
        For paid events, this only creates the request. Payment must be completed
        before attendance can be confirmed.
        
        Args:
            requester: UserProfile making the request
            event: Event being requested
            message: Optional request message
            seats_requested: Number of seats requested
            auth_user: Optional AUTH_USER for identity enforcement check
        
        Returns:
            EventRequest instance
            
        Raises:
            AuthorizationError: If AUTH_USER attempts to create request
        """
        # SECURITY: Identity enforcement - verify requester is USER_PROFILE
        from users.models import UserProfile
        if not isinstance(requester, UserProfile):
            from core.exceptions import ValidationError
            raise ValidationError(
                "Event request requester must be a UserProfile instance, not AUTH_USER.",
                code="INVALID_REQUESTER_TYPE"
            )
        
        # SECURITY: If auth_user is provided, ensure it's not an admin
        if auth_user:
            from django.contrib.auth.models import User
            if isinstance(auth_user, User) and (auth_user.is_staff or auth_user.is_superuser):
                from core.exceptions import AuthorizationError
                raise AuthorizationError(
                    "Admin accounts (AUTH_USER) cannot make event requests. Only USER_PROFILE can request to join events.",
                    code="ADMIN_CANNOT_REQUEST_EVENT"
                )
        # Check if event is available for requests
        if event.status != 'published':
            raise ValueError("Can only request for published events")
        
        if event.is_past:
            raise ValueError("Cannot request for past events")
        
        if event.is_full:
            raise ValueError("Event is at capacity")
        
        # Check if request already exists
        existing = EventRequest.objects.filter(event=event, requester=requester).first()
        if existing:
            if existing.status == 'pending':
                raise ValueError("You already have a pending request for this event")
            if existing.status == 'accepted':
                raise ValueError("You are already accepted for this event")
        
        request = EventRequest.objects.create(
            requester=requester,
            event=event,
            message=message,
            seats_requested=seats_requested,
            status='pending'
        )
        
        logger.info(f"Event request created: {request.id} for event {event.id}")
        
        # Notify host about new join request (non-blocking, best-effort)
        try:
            from notifications.services.dispatcher import get_push_dispatcher
            from notifications.services.messages import NotificationTemplate
            dispatcher = get_push_dispatcher()
            
            dispatcher.send_template_notification(
                recipient=event.host,
                template=NotificationTemplate.NEW_JOIN_REQUEST,
                context={
                    'user_name': requester.name or requester.username,
                    'event_name': event.title
                },
                sender=requester,
                reference_type='EventRequest',
                reference_id=request.id,
                additional_data={
                    'event_id': event.id,
                    'request_id': request.id,
                },
            )
        except Exception as e:
            # Never block request creation on notification failure
            logger.error(f"Failed to send new_join_request notification to host: {str(e)}")
        
        return request
    
    @staticmethod
    @transaction.atomic
    def accept_request(request):
        """
        Accept an event request.
        
        Payment enforcement:
        - For FREE events: Creates attendee immediately
        - For PAID events: Does NOT create attendee. User must complete payment first.
        
        Args:
            request: EventRequest instance
        
        Returns:
            Tuple of (updated request, attendee or None)
        """
        if request.status != 'pending':
            raise ValueError("Can only accept pending requests")
        
        event = request.event
        
        # Check if event has capacity
        if event.max_capacity > 0:
            current_count = EventAttendee.objects.filter(
                event=event,
                status='going'
            ).count()
            if current_count + request.seats_requested > event.max_capacity:
                raise ValueError("Accepting this request would exceed event capacity")
        
        # Update request status
        request.status = 'accepted'
        request.save(update_fields=['status', 'updated_at'])
        
        attendee = None
        
        # For FREE events: Create attendee immediately
        # For PAID events: Do NOT create attendee until payment is completed
        if not event.is_paid:
            # Create or update attendee record for free events
            attendee, created = EventAttendee.objects.get_or_create(
                event=event,
                user=request.requester,
                defaults={
                    'status': 'going',
                    'seats': request.seats_requested,
                    'is_paid': False,
                    'price_paid': 0,
                }
            )
            
            if not created:
                attendee.status = 'going'
                attendee.seats = request.seats_requested
                attendee.is_paid = False
                attendee.price_paid = 0
                attendee.save(update_fields=['status', 'seats', 'is_paid', 'price_paid', 'updated_at'])
            
            # Update event going_count
            event.going_count = EventAttendee.objects.filter(
                event=event,
                status='going'
            ).count()
            event.save(update_fields=['going_count'])
            
            logger.info(f"Event request {request.id} accepted, attendee created (free event)")
        else:
            # For paid events, attendee will be created after payment success
            # Payment flow handles attendee creation in PaymentFlowService.finalize_payment_success()
            logger.info(f"Event request {request.id} accepted, payment required before attendee creation")
        
        # Notify requester about request approval (non-blocking, best-effort)
        try:
            from notifications.services.dispatcher import get_push_dispatcher
            from notifications.services.messages import NotificationTemplate
            dispatcher = get_push_dispatcher()
            
            dispatcher.send_template_notification(
                recipient=request.requester,
                template=NotificationTemplate.REQUEST_APPROVED,
                context={
                    'event_name': event.title,
                    'host_name': event.host.name or event.host.username
                },
                sender=event.host,
                reference_type='EventRequest',
                reference_id=request.id,
                additional_data={
                    'event_id': event.id,
                    'route': 'event_payment_or_ticket' if event.is_paid else 'event_details',
                },
            )
        except Exception as e:
            # Never block request acceptance on notification failure
            logger.error(f"Failed to send request_approved notification: {str(e)}")
        
        return request, attendee
    
    @staticmethod
    def decline_request(request):
        """
        Decline an event request.
        
        Args:
            request: EventRequest instance
        
        Returns:
            Updated request
        """
        if request.status != 'pending':
            raise ValueError("Can only decline pending requests")
        
        request.status = 'declined'
        request.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"Event request {request.id} declined")
        return request


# ============================================================================
# Event Invite Service
# ============================================================================

class EventInviteService:
    """Service for event invite business logic"""
    
    @staticmethod
    @transaction.atomic
    def create_invite(event, invited_user, message='', expires_at=None):
        """
        Create an event invite.
        
        Args:
            event: Event being invited to
            invited_user: UserProfile to invite
            message: Optional invite message
            expires_at: Optional expiration time
        
        Returns:
            EventInvite instance
        """
        # Check if already invited
        existing = EventInvite.objects.filter(event=event, invited_user=invited_user).first()
        if existing:
            if existing.status == 'pending':
                raise ValueError("User already has a pending invite for this event")
        
        invite = EventInvite.objects.create(
            event=event,
            invited_user=invited_user,
            message=message,
            expires_at=expires_at,
            status='pending'
        )
        
        logger.info(f"Event invite created: {invite.id} for user {invited_user.id}")
        
        # Notify invited user about direct invite (non-blocking, best-effort)
        try:
            from notifications.services.dispatcher import get_push_dispatcher
            from notifications.services.messages import NotificationTemplate
            dispatcher = get_push_dispatcher()
            
            host_name = event.host.name or event.host.username if hasattr(event.host, 'name') else event.host.username
            
            dispatcher.send_template_notification(
                recipient=invited_user,
                template=NotificationTemplate.EVENT_INVITE,
                context={
                    'host_name': host_name,
                    'event_name': event.title
                },
                sender=event.host,
                reference_type='EventInvite',
                reference_id=invite.id,
                additional_data={
                    'event_id': event.id,
                    'invite_id': invite.id,
                },
            )
        except Exception as e:
            # Never block invite creation on notification failure
            logger.error(f"Failed to send event_invite notification: {str(e)}")
        
        return invite
    
    @staticmethod
    @transaction.atomic
    def accept_invite(invite):
        """
        Accept an event invite.
        
        Payment enforcement:
        - For FREE events: Creates attendee immediately
        - For PAID events: Does NOT create attendee. User must complete payment first.
        
        Args:
            invite: EventInvite instance
        
        Returns:
            Tuple of (updated invite, attendee or None)
        """
        if invite.status != 'pending':
            raise ValueError("Can only accept pending invites")
        
        if invite.expires_at and invite.expires_at < timezone.now():
            invite.status = 'expired'
            invite.save()
            raise ValueError("Invite has expired")
        
        event = invite.event
        
        # Check if event has capacity
        if event.max_capacity > 0:
            current_count = EventAttendee.objects.filter(
                event=event,
                status='going'
            ).count()
            if current_count + 1 > event.max_capacity:
                raise ValueError("Event is at capacity")
        
        # Update invite status
        invite.status = 'accepted'
        invite.save(update_fields=['status', 'updated_at'])
        
        attendee = None
        
        # For FREE events: Create attendee immediately
        # For PAID events: Do NOT create attendee until payment is completed
        if not event.is_paid:
            # Create or update attendee record for free events
            attendee, created = EventAttendee.objects.get_or_create(
                event=event,
                user=invite.invited_user,
                defaults={
                    'status': 'going',
                    'seats': 1,
                    'is_paid': False,
                    'price_paid': 0,
                }
            )
            
            if not created:
                attendee.status = 'going'
                attendee.seats = 1
                attendee.is_paid = False
                attendee.price_paid = 0
                attendee.save(update_fields=['status', 'seats', 'is_paid', 'price_paid', 'updated_at'])
            
            # Update event going_count
            event.going_count = EventAttendee.objects.filter(
                event=event,
                status='going'
            ).count()
            event.save(update_fields=['going_count'])
            
            logger.info(f"Event invite {invite.id} accepted, attendee created (free event)")
        else:
            # For paid events, attendee will be created after payment success
            # Payment flow handles attendee creation in PaymentFlowService.finalize_payment_success()
            logger.info(f"Event invite {invite.id} accepted, payment required before attendee creation")
        
        return invite, attendee
    
    @staticmethod
    def decline_invite(invite):
        """
        Decline an event invite.
        
        Args:
            invite: EventInvite instance
        
        Returns:
            Updated invite
        """
        if invite.status != 'pending':
            raise ValueError("Can only decline pending invites")
        
        invite.status = 'declined'
        invite.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"Event invite {invite.id} declined")
        return invite


# ============================================================================
# Attendance Service
# ============================================================================

class AttendanceService:
    """Service for attendance business logic"""
    
    @staticmethod
    def check_in_attendee(attendee):
        """
        Check in an attendee at the event.
        
        Payment enforcement:
        - For paid events, verifies payment before allowing check-in.
        
        Args:
            attendee: EventAttendee instance
        
        Returns:
            Updated attendee
        
        Raises:
            ValidationError: If payment is required but not verified
        """
        if attendee.status != 'going':
            raise ValueError("Can only check in attendees with 'going' status")
        
        # Payment enforcement: For paid events, verify payment
        if attendee.event.is_paid:
            require_payment_for_event(
                attendee.event,
                attendee.user,
                action_name="check in to this event"
            )
            
            # Double-check attendee.is_paid matches payment status
            if not attendee.is_paid:
                raise ValidationError(
                    "Payment verification failed. Cannot check in without confirmed payment.",
                    code="PAYMENT_NOT_VERIFIED"
                )
        
        attendee.status = 'checked_in'
        attendee.checked_in_at = timezone.now()
        attendee.save(update_fields=['status', 'checked_in_at', 'updated_at'])
        
        logger.info(f"Attendee {attendee.id} checked in")
        return attendee
    
    @staticmethod
    @transaction.atomic
    def update_attendance_status(event, user, new_status, seats=1):
        """
        Update user's attendance status for an event.
        
        Payment enforcement:
        - For paid events, requires payment before setting status to 'going'.
        
        Args:
            event: Event instance
            user: UserProfile instance
            new_status: New attendance status
            seats: Number of seats
        
        Returns:
            Updated or created EventAttendee instance
        
        Raises:
            ValidationError: If payment is required but not verified
        """
        # Payment enforcement: For paid events going to 'going' status, require payment
        if event.is_paid and new_status == 'going':
            require_payment_for_event(
                event,
                user,
                action_name="confirm attendance for this event"
            )
        
        attendee, created = EventAttendee.objects.get_or_create(
            event=event,
            user=user,
            defaults={
                'status': new_status,
                'seats': seats,
                'is_paid': event.is_paid and verify_payment_for_event(event, user),
                'price_paid': event.ticket_price if (event.is_paid and verify_payment_for_event(event, user)) else 0,
            }
        )
        
        if not created:
            attendee.status = new_status
            attendee.seats = seats
            # Update payment status based on actual payment verification
            if event.is_paid:
                attendee.is_paid = verify_payment_for_event(event, user)
                attendee.price_paid = event.ticket_price if attendee.is_paid else 0
            attendee.save(update_fields=['status', 'seats', 'is_paid', 'price_paid', 'updated_at'])
        
        # Update event going_count
        if new_status == 'going':
            event.going_count = EventAttendee.objects.filter(
                event=event,
                status='going'
            ).count()
            event.save(update_fields=['going_count'])
        
        logger.info(f"Attendance updated: {attendee.id} to status {new_status}")
        return attendee
