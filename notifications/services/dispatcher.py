"""
Push notification dispatcher service.

Orchestrates push notification delivery:
- Resolves USER_PROFILE → active player_ids
- Applies notification preferences
- De-duplicates devices
- Calls OneSignal client
- Persists NOTIFICATION record regardless of push success

This is the ONLY place that sends push notifications.

All transactional notifications MUST use templates from messages.py.
"""
import logging
from typing import List, Dict, Any, Optional
from django.db import transaction
from django.utils import timezone

from notifications.models import Notification, UserDevice
from notifications.services.onesignal import OneSignalClient
from notifications.services.preferences import NotificationPreferencesService

logger = logging.getLogger(__name__)


class PushNotificationDispatcher:
    """
    Service for dispatching push notifications.
    
    Responsibilities:
    - Resolve USER_PROFILE → active player_ids
    - Apply notification preferences
    - De-duplicate devices
    - Send push via OneSignal
    - Persist NOTIFICATION record (audit trail)
    - Handle failures gracefully (never block business logic)
    """
    
    def __init__(self):
        """Initialize dispatcher with OneSignal client."""
        self.onesignal_client = OneSignalClient()
        self.preferences_service = NotificationPreferencesService()
    
   def send_notification(
        self,
        recipient: 'UserProfile',
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        sender: Optional['UserProfile'] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Send push notification to a USER_PROFILE.
        
        This method:
        1. Checks notification preferences
        2. Resolves user → active devices
        3. Sends push via OneSignal
        4. Persists NOTIFICATION record (regardless of push success)
        5. Handles invalid player IDs (deactivates devices)
        
        Args:
            recipient: UserProfile receiving notification
            notification_type: Type of notification (from NOTIFICATION_TYPE_CHOICES)
            title: Notification title
            message: Notification message body
            data: Optional payload data dict (for mobile app routing)
            sender: Optional UserProfile sending notification
            reference_type: Optional related model type (e.g., 'Event', 'Payment')
            reference_id: Optional related object ID
            
        Returns:
            Dict with 'notification_saved' (bool), 'push_sent' (bool), 
            'device_count' (int), 'errors' (list)
            
        Never raises exceptions - always returns result dict.
        """
        result = {
            'notification_saved': False,
            'push_sent': False,
            'device_count': 0,
            'errors': [],
        }
        
        try:
            # SECURITY: Only send to USER_PROFILE, never AUTH_USER
            if not hasattr(recipient, 'user'):
                logger.error(f"Invalid recipient type: {type(recipient)}. Must be UserProfile.")
                result['errors'].append('Invalid recipient type')
                return result
            
            # Check notification preferences
            if not self.preferences_service.is_notification_enabled(recipient, notification_type):
                logger.debug(
                    f"Notification type '{notification_type}' disabled for user {recipient.id}. "
                    f"Skipping push but saving notification record."
                )
                # Still save notification record (preferences don't affect audit trail)
            
            # Get active devices for user
            active_devices = UserDevice.objects.filter(
                user_profile=recipient,
                is_active=True,
            ).select_related('user_profile')
            
            player_ids = list(active_devices.values_list('onesignal_player_id', flat=True))
            
            # De-duplicate player IDs (in case of race conditions)
            player_ids = list(dict.fromkeys(player_ids))  # Preserves order
            
            result['device_count'] = len(player_ids)
            
            # Send push notification (non-blocking, best-effort)
            push_result = None
            if player_ids and self.preferences_service.is_notification_enabled(recipient, notification_type):
                push_result = self.onesignal_client.send_push(
                    player_ids=player_ids,
                    title=title,
                    body=message,
                    data=data or {},
                )
                result['push_sent'] = push_result.get('success', False)
                result['errors'].extend(push_result.get('errors', []))
                
                # Handle invalid player IDs (deactivate devices)
                invalid_player_ids = push_result.get('invalid_player_ids', [])
                if invalid_player_ids:
                    self._deactivate_invalid_devices(invalid_player_ids)
            elif not player_ids:
                logger.debug(f"No active devices found for user {recipient.id}. Skipping push.")
            else:
                logger.debug(f"Notification disabled for user {recipient.id}. Skipping push.")
            
            # ALWAYS persist NOTIFICATION record (audit trail, in-app inbox)
            # This happens regardless of push success/failure
            notification = self._save_notification(
                recipient=recipient,
                notification_type=notification_type,
                title=title,
                message=message,
                data=data,
                sender=sender,
                reference_type=reference_type,
                reference_id=reference_id,
            )
            result['notification_saved'] = notification is not None
            
            logger.info(
                f"Notification dispatched: type={notification_type}, "
                f"recipient={recipient.id}, devices={len(player_ids)}, "
                f"push_sent={result['push_sent']}, saved={result['notification_saved']}"
            )
            
        except Exception as e:
            logger.error(
                f"Error dispatching push notification: {str(e)}",
                exc_info=True
            )
            result['errors'].append(f"Dispatch error: {str(e)}")
            
            # Still try to save notification record (critical audit trail)
            try:
                notification = self._save_notification(
                    recipient=recipient,
                    notification_type=notification_type,
                    title=title,
                    message=message,
                    data=data,
                    sender=sender,
                    reference_type=reference_type,
                    reference_id=reference_id,
                )
                result['notification_saved'] = notification is not None
            except Exception as save_error:
                logger.error(f"Failed to save notification record: {str(save_error)}")
                result['errors'].append(f"Save error: {str(save_error)}")
        
        return result
    
    def _save_notification(
        self,
        recipient: 'UserProfile',
        notification_type: str,
        title: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
        sender: Optional['UserProfile'] = None,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
    ) -> Optional[Notification]:
        """
        Save notification record to database.
        
        This is separate from push delivery and always executes.
        """
        try:
            notification = Notification.objects.create(
                recipient=recipient,
                sender=sender,
                type=notification_type,
                title=title,
                message=message,
                reference_type=reference_type or '',
                reference_id=reference_id,
                metadata=data or {},
            )
            return notification
        except Exception as e:
            logger.error(f"Failed to save notification record: {str(e)}", exc_info=True)
            return None
    
    def _deactivate_invalid_devices(self, invalid_player_ids: List[str]) -> None:
        """
        Deactivate devices with invalid player IDs.
        
        Called when OneSignal returns invalid_player_ids in response.
        """
        if not invalid_player_ids:
            return
        
        try:
            updated = UserDevice.objects.filter(
                onesignal_player_id__in=invalid_player_ids
            ).update(is_active=False)
            
            logger.info(f"Deactivated {updated} devices with invalid player IDs")
            
        except Exception as e:
            logger.error(f"Error deactivating invalid devices: {str(e)}", exc_info=True)


# Singleton instance for use across the application
_dispatcher_instance: Optional[PushNotificationDispatcher] = None


def get_push_dispatcher() -> PushNotificationDispatcher:
    """Get singleton PushNotificationDispatcher instance."""
    global _dispatcher_instance
    if _dispatcher_instance is None:
        _dispatcher_instance = PushNotificationDispatcher()
    return _dispatcher_instance

