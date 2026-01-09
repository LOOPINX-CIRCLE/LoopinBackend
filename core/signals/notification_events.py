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
            from notifications.services.dispatcher import get_push_dispatcher
            from notifications.services.messages import NotificationTemplate
            dispatcher = get_push_dispatcher()
            
            dispatcher.send_template_notification(
                recipient=instance.host,
                template=NotificationTemplate.EVENT_CREATED,
                context={
                    'event_name': instance.title
                },
                reference_type='Event',
                reference_id=instance.id,
                additional_data={
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
        
        # Use push dispatcher for notifications (handles both push and Notification record)
        try:
            from notifications.services.dispatcher import get_push_dispatcher
            from notifications.services.messages import NotificationTemplate
            dispatcher = get_push_dispatcher()
            
            if instance.status == 'completed':
                dispatcher.send_template_notification(
                    recipient=instance.user,
                    template=NotificationTemplate.PAYMENT_SUCCESS,
                    context={
                        'event_name': instance.event.title
                    },
                    reference_type='PaymentOrder',
                    reference_id=instance.id,
                    additional_data={
                        'event_id': instance.event.id,
                        'payment_order_id': instance.id,
                    },
                )
                
            elif instance.status == 'failed':
                dispatcher.send_template_notification(
                    recipient=instance.user,
                    template=NotificationTemplate.PAYMENT_FAILED,
                    context={
                        'event_name': instance.event.title
                    },
                    reference_type='PaymentOrder',
                    reference_id=instance.id,
                    additional_data={
                        'event_id': instance.event.id,
                        'payment_order_id': instance.id,
                    },
                )
            
            logger.info(f"Payment status notification sent to user {instance.user.id}")
        except Exception as e:
            # Fallback to direct Notification creation if dispatcher fails
            logger.warning(f"Push dispatcher failed, falling back to direct notification: {str(e)}")
            try:
                from notifications.services.messages import NotificationTemplate, render_template
                if instance.status == 'completed':
                    rendered = render_template(
                        NotificationTemplate.PAYMENT_SUCCESS,
                        {'event_name': instance.event.title}
                    )
                    Notification.objects.create(
                        recipient=instance.user,
                        title=rendered['title'],
                        message=rendered['body'],
                        type="payment_success",
                        metadata={
                            'payment_id': instance.id,
                            'event_id': instance.event.id,
                            'amount': str(instance.amount),
                        },
                        reference_type='PaymentOrder',
                        reference_id=instance.id,
                    )
                elif instance.status == 'failed':
                    rendered = render_template(
                        NotificationTemplate.PAYMENT_FAILED,
                        {'event_name': instance.event.title}
                    )
                    Notification.objects.create(
                        recipient=instance.user,
                        title=rendered['title'],
                        message=rendered['body'],
                        type="payment_failed",
                        metadata={
                            'payment_id': instance.id,
                            'event_id': instance.event.id,
                            'amount': str(instance.amount),
                        },
                        reference_type='PaymentOrder',
                        reference_id=instance.id,
                    )
            except Exception as fallback_error:
                logger.error(f"Failed to create fallback notification: {str(fallback_error)}")
        
    except Exception as e:
        logger.error(f"Failed to send payment status notification: {str(e)}")


@receiver(post_save, sender='events.EventRequest')
def event_request_notification(sender, instance, created, **kwargs):
    """Send notification when event request is created or updated."""
    
    if created:
        logger.info(f"Event request created: {instance.id}")
        
        # Send notification to event host
        try:
            from notifications.services.dispatcher import get_push_dispatcher
            from notifications.services.messages import NotificationTemplate
            dispatcher = get_push_dispatcher()
            
            dispatcher.send_template_notification(
                recipient=instance.event.host,
                template=NotificationTemplate.NEW_JOIN_REQUEST,
                context={
                    'user_name': instance.requester.name or instance.requester.username,
                    'event_name': instance.event.title
                },
                sender=instance.requester,
                reference_type='EventRequest',
                reference_id=instance.id,
                additional_data={
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
            from notifications.services.dispatcher import get_push_dispatcher
            from notifications.services.messages import NotificationTemplate
            dispatcher = get_push_dispatcher()
            
            if instance.status == 'accepted':
                dispatcher.send_template_notification(
                    recipient=instance.requester,
                    template=NotificationTemplate.REQUEST_APPROVED,
                    context={
                        'event_name': instance.event.title,
                        'host_name': instance.event.host.name or instance.event.host.username
                    },
                    sender=instance.event.host,
                    reference_type='EventRequest',
                    reference_id=instance.id,
                    additional_data={
                        'request_id': instance.id,
                        'event_id': instance.event.id,
                    }
                )
                
            elif instance.status == 'declined':
                dispatcher.send_template_notification(
                    recipient=instance.requester,
                    template=NotificationTemplate.REQUEST_DECLINED,
                    context={
                        'event_name': instance.event.title
                    },
                    sender=instance.event.host,
                    reference_type='EventRequest',
                    reference_id=instance.id,
                    additional_data={
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
            from notifications.services.dispatcher import get_push_dispatcher
            from notifications.services.messages import NotificationTemplate
            dispatcher = get_push_dispatcher()
            
            dispatcher.send_template_notification(
                recipient=instance,
                template=NotificationTemplate.PROFILE_COMPLETED,
                context={},  # No parameters needed
                reference_type='UserProfile',
                reference_id=instance.id,
                additional_data={
                    'user_id': instance.user.id,
                }
            )
            
            logger.info(f"Profile completion notification sent to user {instance.user.id}")
            
        except Exception as e:
            logger.error(f"Failed to send profile completion notification: {str(e)}")
