"""
Notification message templates.

Centralized message strings for all notification scenarios.
DO NOT hardcode messages in service methods - use these templates.
"""


class NotificationMessages:
    """Centralized notification message templates."""
    
    # ========================================================================
    # CONSUMER-FOCUSED MESSAGES (ATTENDEES)
    # ========================================================================
    
    @staticmethod
    def event_live_title(event_name: str, host_name: str) -> str:
        """Title for event goes live notification."""
        return "New Event Alert!"
    
    @staticmethod
    def event_live_body(event_name: str, host_name: str) -> str:
        """Body for event goes live notification."""
        return f"{event_name} by {host_name} is live. Request your spot!"
    
    @staticmethod
    def invite_received_title(host_name: str, event_name: str) -> str:
        """Title for direct invite received notification."""
        return "You're Invited!"
    
    @staticmethod
    def invite_received_body(host_name: str, event_name: str) -> str:
        """Body for direct invite received notification."""
        return f"{host_name} sent you a private invite to {event_name}."
    
    @staticmethod
    def request_approved_title(event_name: str, host_name: str) -> str:
        """Title for request approved notification."""
        return "Request Accepted!"
    
    @staticmethod
    def request_approved_body(event_name: str, host_name: str) -> str:
        """Body for request approved notification."""
        return f"You're approved for {event_name} by {host_name}."
    
    @staticmethod
    def booking_success_title(event_name: str) -> str:
        """Title for booking success notification."""
        return "Booking Confirmed!"
    
    @staticmethod
    def booking_success_body(event_name: str) -> str:
        """Body for booking success notification."""
        return f"Your spot at {event_name} is locked. View your ticket now!"
    
    # ========================================================================
    # HOST-FOCUSED MESSAGES
    # ========================================================================
    
    @staticmethod
    def new_join_request_title(user_name: str, event_name: str) -> str:
        """Title for new join request notification (host)."""
        return "New Request!"
    
    @staticmethod
    def new_join_request_body(user_name: str, event_name: str) -> str:
        """Body for new join request notification (host)."""
        return f"{user_name} wants to join {event_name}. Tap to approve."
    
    @staticmethod
    def event_started_title(event_name: str) -> str:
        """Title for event kick-off notification (host)."""
        return "Check-in is Live!"
    
    @staticmethod
    def event_started_body(event_name: str) -> str:
        """Body for event kick-off notification (host)."""
        return f"{event_name} has started. Start scanning guest tickets now."
    
    @staticmethod
    def payout_reminder_title(event_name: str) -> str:
        """Title for payout reminder notification (host)."""
        return "Payout Ready!"
    
    @staticmethod
    def payout_reminder_body(event_name: str) -> str:
        """Body for payout reminder notification (host)."""
        return f"Event over! Add your bank account to receive funds for {event_name}."

