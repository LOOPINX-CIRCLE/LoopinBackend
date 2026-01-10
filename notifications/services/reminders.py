"""
Time-based notification service (stubs).

These are placeholders for future scheduled notification functionality.
No scheduler implemented yet - can be added later (Celery, cron, etc.).
"""
import logging
from typing import List
from django.utils import timezone
from notifications.services.dispatcher import get_push_dispatcher
# from notifications.services.messages import NotificationTemplate, render_template  # TODO: Use when implementing

logger = logging.getLogger(__name__)


def send_event_reminders(event_id: int) -> None:
    """
    Send reminder notifications for an upcoming event (STUB).
    
    This function is a placeholder for future scheduled reminder functionality.
    Currently does nothing - scheduler not implemented yet.
    
    Args:
        event_id: Event ID to send reminders for
        
    Future Implementation:
    - Query event and all attendees
    - Check if reminder should be sent (e.g., 1 day before)
    - Send push notifications to all attendees
    - This should be called by a scheduled job (Celery, cron, etc.)
    """
    logger.info(f"Event reminder stub called for event {event_id} (not implemented yet)")
    
    # TODO: Implement reminder logic when scheduler is added
    # from events.models import Event, EventAttendee
    # dispatcher = get_push_dispatcher()
    # event = Event.objects.get(id=event_id)
    # attendees = EventAttendee.objects.filter(event=event, status='going')
    # 
    # for attendee in attendees:
    #     dispatcher.send_notification(
    #         recipient=attendee.user,
    #         notification_type='reminder',
    #         title=f"Reminder: {event.title}",
    #         message=f"Don't forget! {event.title} starts tomorrow at {event.start_time}",
    #         data={
    #             'type': 'reminder',
    #             'event_id': event.id,
    #             'route': 'event_detail',
    #         },
    #         reference_type='Event',
    #         reference_id=event.id,
    #     )


def notify_event_kickoff(event_id: int) -> None:
    """
    Notify host when event starts (STUB - time-based).
    
    Triggered when:
    - Current time >= EVENT.start_time
    - Event status is 'published'
    - Triggered once (idempotent)
    
    Args:
        event_id: Event ID
        
    Future Implementation:
    - Query event by ID
    - Check if event.start_time <= now() and status == 'published'
    - Check if notification already sent (idempotency check)
    - Send notification to host
    - Mark as sent (prevent duplicates)
    - This should be called by a scheduled job (Celery, cron, etc.)
    """
    logger.info(f"Event kickoff notification stub called for event {event_id} (not implemented yet)")
    
    # TODO: Implement when scheduler is added
    # from events.models import Event
    # from notifications.models import Notification
    # 
    # try:
    #     event = Event.objects.get(id=event_id, status='published')
    #     
    #     # Idempotency check - ensure we haven't already sent this notification
    #     existing = Notification.objects.filter(
    #         recipient=event.host,
    #         type='event_started',
    #         reference_type='Event',
    #         reference_id=event.id,
    #     ).exists()
    #     
    #     if existing:
    #         logger.info(f"Event kickoff notification already sent for event {event_id}")
    #         return
    #     
    #     # Check if event has started
    #     if timezone.now() >= event.start_time:
    #         dispatcher = get_push_dispatcher()
    #         messages = NotificationMessages()
    #         
    #         dispatcher.send_notification(
    #             recipient=event.host,
    #             notification_type='event_started',
    #             title=messages.event_started_title(event.title),
    #             message=messages.event_started_body(event.title),
    #             data={
    #                 'type': 'event_started',
    #                 'event_id': event.id,
    #                 'route': 'host_scanner',
    #             },
    #             reference_type='Event',
    #             reference_id=event.id,
    #         )
    #         
    #         logger.info(f"Event kickoff notification sent to host for event {event_id}")
    # except Event.DoesNotExist:
    #     logger.warning(f"Event {event_id} not found or not published")
    # except Exception as e:
    #     logger.error(f"Failed to send event kickoff notification: {str(e)}")


def notify_payout_reminder(event_id: int) -> None:
    """
    Notify host to add bank account for payout (STUB - time-based).
    
    Triggered when:
    - Current time > EVENT.end_time
    - Host has no verified bank account
    - Event is paid (is_paid == True)
    - Triggered once (idempotent)
    
    Args:
        event_id: Event ID
        
    Future Implementation:
    - Query event by ID
    - Check if event.end_time < now() and event.is_paid == True
    - Check if host has verified bank account
    - Check if notification already sent (idempotency check)
    - Send notification to host
    - Mark as sent (prevent duplicates)
    - This should be called by a scheduled job (Celery, cron, etc.)
    """
    logger.info(f"Payout reminder notification stub called for event {event_id} (not implemented yet)")
    
    # TODO: Implement when scheduler is added
    # from events.models import Event
    # from users.models import BankAccount
    # from notifications.models import Notification
    # 
    # try:
    #     event = Event.objects.get(id=event_id)
    #     
    #     # Only for paid events that have ended
    #     if not event.is_paid or timezone.now() <= event.end_time:
    #         return
    #     
    #     # Check if host has verified bank account
    #     has_verified_account = BankAccount.objects.filter(
    #         host=event.host,
    #         is_verified=True,
    #         is_active=True,
    #     ).exists()
    #     
    #     if has_verified_account:
    #         logger.debug(f"Host {event.host.id} already has verified bank account, skipping payout reminder")
    #         return
    #     
    #     # Idempotency check - ensure we haven't already sent this notification
    #     existing = Notification.objects.filter(
    #         recipient=event.host,
    #         type='payout_reminder',
    #         reference_type='Event',
    #         reference_id=event.id,
    #     ).exists()
    #     
    #     if existing:
    #         logger.info(f"Payout reminder notification already sent for event {event_id}")
    #         return
    #     
    #     dispatcher = get_push_dispatcher()
    #     messages = NotificationMessages()
    #     
    #     dispatcher.send_notification(
    #         recipient=event.host,
    #         notification_type='payout_reminder',
    #         title=messages.payout_reminder_title(event.title),
    #         message=messages.payout_reminder_body(event.title),
    #         data={
    #             'type': 'payout_reminder',
    #             'event_id': event.id,
    #             'route': 'bank_setup',
    #         },
    #         reference_type='Event',
    #         reference_id=event.id,
    #     )
    #     
    #     logger.info(f"Payout reminder notification sent to host for event {event_id}")
    # except Event.DoesNotExist:
    #     logger.warning(f"Event {event_id} not found")
    # except Exception as e:
    #     logger.error(f"Failed to send payout reminder notification: {str(e)}")

