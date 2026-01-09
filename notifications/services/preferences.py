"""
Notification preferences service.

Handles user opt-in/opt-out logic for different notification types.
Default: All transactional notifications ON.
Marketing ignored (out of scope).
"""
import logging
from typing import Dict, Set
from core.choices import NOTIFICATION_TYPE_CHOICES

logger = logging.getLogger(__name__)


class NotificationPreferencesService:
    """
    Service for managing notification preferences.
    
    Default behavior:
    - All transactional notifications are ON by default
    - Marketing/promotional notifications are out of scope
    
    Design allows preferences to be added later without refactor.
    """
    
    # Transactional notification types (always enabled by default)
    TRANSACTIONAL_TYPES: Set[str] = {
        'payment_success',
        'payment_failed',
        'event_cancelled',
        'event_update',
        'event_request',
        'event_invite',
        'reminder',
        'system',
    }
    
    # Marketing notification types (out of scope for now)
    MARKETING_TYPES: Set[str] = {
        'promotional',
    }
    
    @classmethod
    def is_notification_enabled(
        cls,
        user_profile,
        notification_type: str,
    ) -> bool:
        """
        Check if a notification type is enabled for a user.
        
        Args:
            user_profile: UserProfile instance
            notification_type: Notification type string
            
        Returns:
            bool: True if notification should be sent, False otherwise
            
        Current implementation:
        - All transactional notifications are enabled by default
        - Marketing notifications are disabled (out of scope)
        """
        # Marketing notifications are out of scope
        if notification_type in cls.MARKETING_TYPES:
            return False
        
        # Transactional notifications are enabled by default
        if notification_type in cls.TRANSACTIONAL_TYPES:
            return True
        
        # Unknown types default to disabled (fail closed)
        logger.warning(f"Unknown notification type: {notification_type}. Defaulting to disabled.")
        return False
    
    @classmethod
    def get_enabled_types(cls, user_profile) -> Set[str]:
        """
        Get all enabled notification types for a user.
        
        Args:
            user_profile: UserProfile instance
            
        Returns:
            Set of enabled notification type strings
        """
        enabled = set()
        for notification_type, _ in NOTIFICATION_TYPE_CHOICES:
            if cls.is_notification_enabled(user_profile, notification_type):
                enabled.add(notification_type)
        return enabled

