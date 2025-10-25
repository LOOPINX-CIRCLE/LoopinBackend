"""
Notification events signals for the Loopin Backend application.

This module contains Django signals for handling notification events
and triggering automated notifications.
"""

import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

from core.utils.logger import get_logger


logger = get_logger(__name__)


@receiver(post_save, sender='events.Event')
def event_created_notification(sender, instance, created, **kwargs):
    """Send notification when a new event is created."""
    
    if created:
        logger.info(f"Event created: {instance.id}")
        
        # Send notification to event host
        try:
            from notifications.models import Notification
            
            Notification.objects.create(
                recipient=instance.host,
                title="Event Created Successfully",
                message=f"Your event '{instance.title}' has been created successfully.",
                notification_type="event_created",
                data={
                    'event_id': instance.id,
                    'event_title': instance.title,
                }
            )
            
            logger.info(f"Event creation notification sent to host {instance.host.id}")
            
        except Exception as e:
            logger.error(f"Failed to send event creation notification: {str(e)}")


@receiver(post_save, sender='attendances.AttendanceRecord')
def attendance_created_notification(sender, instance, created, **kwargs):
    """Send notification when attendance is created."""
    
    if created:
        logger.info(f"Attendance record created: {instance.id}")
        
        # Send notification to event host
        try:
            from notifications.models import Notification
            
            Notification.objects.create(
                recipient=instance.event.host,
                title="New Event Request",
                message=f"{instance.user.username} has requested to attend your event '{instance.event.title}'.",
                notification_type="attendance_request",
                data={
                    'attendance_id': instance.id,
                    'event_id': instance.event.id,
                    'requester_id': instance.user.id,
                }
            )
            
            logger.info(f"Attendance request notification sent to host {instance.event.host.id}")
            
        except Exception as e:
            logger.error(f"Failed to send attendance request notification: {str(e)}")


@receiver(post_save, sender='payments.PaymentOrder')
def payment_status_notification(sender, instance, **kwargs):
    """Send notification when payment status changes."""
    
    logger.info(f"Payment order updated: {instance.id}, status: {instance.status}")
    
    # Send notification based on payment status
    try:
        from notifications.models import Notification
        
        if instance.status == 'completed':
            Notification.objects.create(
                recipient=instance.user,
                title="Payment Successful",
                message=f"Your payment for event '{instance.event.title}' has been processed successfully.",
                notification_type="payment_success",
                data={
                    'payment_id': instance.id,
                    'event_id': instance.event.id,
                    'amount': str(instance.amount),
                }
            )
            
        elif instance.status == 'failed':
            Notification.objects.create(
                recipient=instance.user,
                title="Payment Failed",
                message=f"Your payment for event '{instance.event.title}' could not be processed. Please try again.",
                notification_type="payment_failed",
                data={
                    'payment_id': instance.id,
                    'event_id': instance.event.id,
                    'amount': str(instance.amount),
                }
            )
        
        logger.info(f"Payment status notification sent to user {instance.user.id}")
        
    except Exception as e:
        logger.error(f"Failed to send payment status notification: {str(e)}")


@receiver(post_save, sender='events.EventRequest')
def event_request_notification(sender, instance, created, **kwargs):
    """Send notification when event request is created or updated."""
    
    if created:
        logger.info(f"Event request created: {instance.id}")
        
        # Send notification to event host
        try:
            from notifications.models import Notification
            
            Notification.objects.create(
                recipient=instance.event.host,
                title="New Event Request",
                message=f"{instance.requester.username} has requested to join your event '{instance.event.title}'.",
                notification_type="event_request",
                data={
                    'request_id': instance.id,
                    'event_id': instance.event.id,
                    'requester_id': instance.requester.id,
                }
            )
            
            logger.info(f"Event request notification sent to host {instance.event.host.id}")
            
        except Exception as e:
            logger.error(f"Failed to send event request notification: {str(e)}")
    
    else:
        # Handle request status updates
        logger.info(f"Event request updated: {instance.id}, status: {instance.status}")
        
        try:
            from notifications.models import Notification
            
            if instance.status == 'accepted':
                Notification.objects.create(
                    recipient=instance.requester,
                    title="Event Request Accepted",
                    message=f"Your request to join '{instance.event.title}' has been accepted.",
                    notification_type="event_request_accepted",
                    data={
                        'request_id': instance.id,
                        'event_id': instance.event.id,
                    }
                )
                
            elif instance.status == 'declined':
                Notification.objects.create(
                    recipient=instance.requester,
                    title="Event Request Declined",
                    message=f"Your request to join '{instance.event.title}' has been declined.",
                    notification_type="event_request_declined",
                    data={
                        'request_id': instance.id,
                        'event_id': instance.event.id,
                    }
                )
            
            logger.info(f"Event request status notification sent to requester {instance.requester.id}")
            
        except Exception as e:
            logger.error(f"Failed to send event request status notification: {str(e)}")


@receiver(post_save, sender='users.UserProfile')
def profile_completion_notification(sender, instance, created, **kwargs):
    """Send notification when user profile is completed."""
    
    if not created and instance.is_complete():
        logger.info(f"User profile completed: {instance.user.id}")
        
        try:
            from notifications.models import Notification
            
            Notification.objects.create(
                recipient=instance.user,
                title="Profile Completed",
                message="Congratulations! Your profile has been completed successfully.",
                notification_type="profile_completed",
                data={
                    'user_id': instance.user.id,
                }
            )
            
            logger.info(f"Profile completion notification sent to user {instance.user.id}")
            
        except Exception as e:
            logger.error(f"Failed to send profile completion notification: {str(e)}")
