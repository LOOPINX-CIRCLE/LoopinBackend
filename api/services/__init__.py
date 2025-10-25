"""
API services for the Loopin Backend application.

This module contains business logic services that handle core operations
separated from API routing logic for better maintainability.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from django.contrib.auth.models import User
from django.db import transaction
from asgiref.sync import sync_to_async

from core.utils.logger import get_logger
from core.exceptions import ValidationError, NotFoundError, BusinessLogicError
from core.permissions import PermissionChecker, RoleBasedPermission

logger = get_logger(__name__)


class BaseService:
    """Base service class with common functionality."""
    
    def __init__(self):
        self.logger = get_logger(f"{self.__class__.__module__}.{self.__class__.__name__}")
    
    async def validate_user_permission(self, user: User, permission: str, obj: Optional[Any] = None) -> bool:
        """Validate user permission."""
        return await sync_to_async(PermissionChecker.check_user_permission)(user, permission, obj)
    
    async def require_user_permission(self, user: User, permission: str, obj: Optional[Any] = None) -> None:
        """Require user permission or raise exception."""
        await sync_to_async(PermissionChecker.require_permission)(user, permission, obj)


class UserService(BaseService):
    """Service for user-related operations."""
    
    async def create_user_profile(self, user: User, profile_data: Dict[str, Any]) -> Any:
        """Create user profile."""
        try:
            from users.models import UserProfile
            
            self.logger.info(f"Creating profile for user {user.id}")
            
            # Create profile
            profile = await sync_to_async(UserProfile.objects.create)(
                user=user,
                **profile_data
            )
            
            self.logger.info(f"Profile created successfully for user {user.id}")
            return profile
            
        except Exception as e:
            self.logger.error(f"Failed to create profile for user {user.id}: {str(e)}")
            raise BusinessLogicError(f"Failed to create user profile: {str(e)}")
    
    async def update_user_profile(self, user: User, profile_data: Dict[str, Any]) -> Any:
        """Update user profile."""
        try:
            from users.models import UserProfile
            
            self.logger.info(f"Updating profile for user {user.id}")
            
            # Get or create profile
            try:
                profile = await sync_to_async(lambda: user.profile)()
            except AttributeError:
                profile = await self.create_user_profile(user, profile_data)
                return profile
            
            # Update fields
            for field, value in profile_data.items():
                if hasattr(profile, field) and value is not None:
                    setattr(profile, field, value)
            
            # Save profile
            await sync_to_async(profile.save)()
            
            self.logger.info(f"Profile updated successfully for user {user.id}")
            return profile
            
        except Exception as e:
            self.logger.error(f"Failed to update profile for user {user.id}: {str(e)}")
            raise BusinessLogicError(f"Failed to update user profile: {str(e)}")
    
    async def get_user_profile(self, user: User) -> Optional[Any]:
        """Get user profile."""
        try:
            from users.models import UserProfile
            
            profile = await sync_to_async(UserProfile.objects.get)(user=user)
            return profile
            
        except UserProfile.DoesNotExist:
            return None
        except Exception as e:
            self.logger.error(f"Failed to get profile for user {user.id}: {str(e)}")
            raise BusinessLogicError(f"Failed to get user profile: {str(e)}")


class EventService(BaseService):
    """Service for event-related operations."""
    
    async def create_event(self, host: User, event_data: Dict[str, Any]) -> Any:
        """Create a new event."""
        try:
            from events.models import Event
            
            self.logger.info(f"Creating event for host {host.id}")
            
            # Validate host permissions
            await self.require_user_permission(host, "events.add_event")
            
            # Create event
            event = await sync_to_async(Event.objects.create)(
                host=host,
                **event_data
            )
            
            self.logger.info(f"Event created successfully: {event.id}")
            return event
            
        except Exception as e:
            self.logger.error(f"Failed to create event for host {host.id}: {str(e)}")
            raise BusinessLogicError(f"Failed to create event: {str(e)}")
    
    async def update_event(self, event_id: int, user: User, event_data: Dict[str, Any]) -> Any:
        """Update an existing event."""
        try:
            from events.models import Event
            
            self.logger.info(f"Updating event {event_id} by user {user.id}")
            
            # Get event
            event = await sync_to_async(Event.objects.get)(id=event_id)
            
            # Check permissions
            await self.require_user_permission(user, "events.change_event", event)
            
            # Update fields
            for field, value in event_data.items():
                if hasattr(event, field) and value is not None:
                    setattr(event, field, value)
            
            # Save event
            await sync_to_async(event.save)()
            
            self.logger.info(f"Event updated successfully: {event.id}")
            return event
            
        except Event.DoesNotExist:
            raise NotFoundError(f"Event {event_id} not found")
        except Exception as e:
            self.logger.error(f"Failed to update event {event_id}: {str(e)}")
            raise BusinessLogicError(f"Failed to update event: {str(e)}")
    
    async def get_event(self, event_id: int, user: Optional[User] = None) -> Any:
        """Get event by ID."""
        try:
            from events.models import Event
            
            event = await sync_to_async(Event.objects.get)(id=event_id)
            
            # Check if user can view this event
            if user and not await self.validate_user_permission(user, "events.view_event", event):
                raise NotFoundError(f"Event {event_id} not found")
            
            return event
            
        except Event.DoesNotExist:
            raise NotFoundError(f"Event {event_id} not found")
        except Exception as e:
            self.logger.error(f"Failed to get event {event_id}: {str(e)}")
            raise BusinessLogicError(f"Failed to get event: {str(e)}")
    
    async def list_events(self, user: Optional[User] = None, filters: Optional[Dict[str, Any]] = None) -> List[Any]:
        """List events with optional filters."""
        try:
            from events.models import Event
            
            # Build queryset
            queryset = Event.objects.all()
            
            # Apply filters
            if filters:
                if 'host_id' in filters:
                    queryset = queryset.filter(host_id=filters['host_id'])
                if 'is_public' in filters:
                    queryset = queryset.filter(is_public=filters['is_public'])
                if 'start_time_after' in filters:
                    queryset = queryset.filter(start_time__gte=filters['start_time_after'])
                if 'start_time_before' in filters:
                    queryset = queryset.filter(start_time__lte=filters['start_time_before'])
            
            # Filter by user permissions if provided
            if user and not await self.validate_user_permission(user, "events.view_event"):
                queryset = queryset.filter(is_public=True)
            
            events = await sync_to_async(list)(queryset)
            return events
            
        except Exception as e:
            self.logger.error(f"Failed to list events: {str(e)}")
            raise BusinessLogicError(f"Failed to list events: {str(e)}")


class PaymentService(BaseService):
    """Service for payment-related operations."""
    
    async def create_payment_order(self, user: User, event_id: int, amount: float, currency: str = "INR") -> Any:
        """Create a payment order."""
        try:
            from payments.models import PaymentOrder
            from events.models import Event
            
            self.logger.info(f"Creating payment order for user {user.id}, event {event_id}")
            
            # Get event
            event = await sync_to_async(Event.objects.get)(id=event_id)
            
            # Validate amount
            if amount <= 0:
                raise ValidationError("Payment amount must be greater than zero")
            
            # Create payment order
            payment_order = await sync_to_async(PaymentOrder.objects.create)(
                user=user,
                event=event,
                amount=amount,
                currency=currency,
                status='pending'
            )
            
            self.logger.info(f"Payment order created successfully: {payment_order.id}")
            return payment_order
            
        except Event.DoesNotExist:
            raise NotFoundError(f"Event {event_id} not found")
        except Exception as e:
            self.logger.error(f"Failed to create payment order: {str(e)}")
            raise BusinessLogicError(f"Failed to create payment order: {str(e)}")
    
    async def process_payment(self, payment_order_id: int, payment_data: Dict[str, Any]) -> Any:
        """Process a payment."""
        try:
            from payments.models import PaymentOrder, PaymentTransaction
            
            self.logger.info(f"Processing payment for order {payment_order_id}")
            
            # Get payment order
            payment_order = await sync_to_async(PaymentOrder.objects.get)(id=payment_order_id)
            
            # Create payment transaction
            transaction = await sync_to_async(PaymentTransaction.objects.create)(
                payment_order=payment_order,
                provider_payment_id=payment_data.get('provider_payment_id'),
                amount=payment_order.amount,
                currency=payment_order.currency,
                status='processing',
                provider_response=payment_data
            )
            
            # Update payment order status
            payment_order.status = 'processing'
            await sync_to_async(payment_order.save)()
            
            self.logger.info(f"Payment processing initiated for order {payment_order_id}")
            return transaction
            
        except PaymentOrder.DoesNotExist:
            raise NotFoundError(f"Payment order {payment_order_id} not found")
        except Exception as e:
            self.logger.error(f"Failed to process payment: {str(e)}")
            raise BusinessLogicError(f"Failed to process payment: {str(e)}")


class AttendanceService(BaseService):
    """Service for attendance-related operations."""
    
    async def create_attendance_record(self, user: User, event_id: int, seats: int = 1) -> Any:
        """Create an attendance record."""
        try:
            from attendances.models import AttendanceRecord
            from events.models import Event
            
            self.logger.info(f"Creating attendance record for user {user.id}, event {event_id}")
            
            # Get event
            event = await sync_to_async(Event.objects.get)(id=event_id)
            
            # Validate seats
            if seats <= 0:
                raise ValidationError("Number of seats must be greater than zero")
            
            if event.current_attendees + seats > event.max_capacity:
                raise ValidationError("Not enough capacity for requested seats")
            
            # Create attendance record
            attendance = await sync_to_async(AttendanceRecord.objects.create)(
                user=user,
                event=event,
                seats=seats,
                status='pending'
            )
            
            # Update event attendee count
            event.current_attendees += seats
            await sync_to_async(event.save)()
            
            self.logger.info(f"Attendance record created successfully: {attendance.id}")
            return attendance
            
        except Event.DoesNotExist:
            raise NotFoundError(f"Event {event_id} not found")
        except Exception as e:
            self.logger.error(f"Failed to create attendance record: {str(e)}")
            raise BusinessLogicError(f"Failed to create attendance record: {str(e)}")
    
    async def check_in_user(self, attendance_id: int, user: User) -> Any:
        """Check in user for an event."""
        try:
            from attendances.models import AttendanceRecord
            
            self.logger.info(f"Checking in user {user.id} for attendance {attendance_id}")
            
            # Get attendance record
            attendance = await sync_to_async(AttendanceRecord.objects.get)(id=attendance_id)
            
            # Validate user
            if attendance.user != user:
                raise ValidationError("User can only check in for their own attendance")
            
            # Check in
            await sync_to_async(attendance.check_in)()
            
            self.logger.info(f"User checked in successfully for attendance {attendance_id}")
            return attendance
            
        except AttendanceRecord.DoesNotExist:
            raise NotFoundError(f"Attendance record {attendance_id} not found")
        except Exception as e:
            self.logger.error(f"Failed to check in user: {str(e)}")
            raise BusinessLogicError(f"Failed to check in user: {str(e)}")


class NotificationService(BaseService):
    """Service for notification-related operations."""
    
    async def send_notification(self, recipient_id: int, title: str, message: str, 
                              notification_type: str, data: Optional[Dict[str, Any]] = None) -> Any:
        """Send a notification to a user."""
        try:
            from notifications.models import Notification
            from django.contrib.auth.models import User
            
            self.logger.info(f"Sending notification to user {recipient_id}")
            
            # Get recipient
            recipient = await sync_to_async(User.objects.get)(id=recipient_id)
            
            # Create notification
            notification = await sync_to_async(Notification.objects.create)(
                recipient=recipient,
                title=title,
                message=message,
                notification_type=notification_type,
                data=data or {}
            )
            
            self.logger.info(f"Notification sent successfully: {notification.id}")
            return notification
            
        except User.DoesNotExist:
            raise NotFoundError(f"User {recipient_id} not found")
        except Exception as e:
            self.logger.error(f"Failed to send notification: {str(e)}")
            raise BusinessLogicError(f"Failed to send notification: {str(e)}")
    
    async def get_user_notifications(self, user: User, unread_only: bool = False) -> List[Any]:
        """Get notifications for a user."""
        try:
            from notifications.models import Notification
            
            queryset = Notification.objects.filter(recipient=user)
            
            if unread_only:
                queryset = queryset.filter(is_read=False)
            
            notifications = await sync_to_async(list)(queryset.order_by('-created_at'))
            return notifications
            
        except Exception as e:
            self.logger.error(f"Failed to get notifications for user {user.id}: {str(e)}")
            raise BusinessLogicError(f"Failed to get notifications: {str(e)}")
