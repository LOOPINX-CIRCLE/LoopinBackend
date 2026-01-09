"""
Constants and choices for the LoopinBackend project.

This module contains all the choice fields, status options, and constants
used across different models in the application.
"""

# ============================================================================
# USER RELATED CHOICES
# ============================================================================

GENDER_CHOICES = [
    ('male', 'Male'),
    ('female', 'Female'),
    ('other', 'Other'),
    ('prefer_not_to_say', 'Prefer not to say'),
]

USER_STATUS_CHOICES = [
    ('active', 'Active'),
    ('inactive', 'Inactive'),
    ('suspended', 'Suspended'),
    ('pending_verification', 'Pending Verification'),
]

VERIFICATION_STATUS_CHOICES = [
    ('unverified', 'Unverified'),
    ('pending', 'Pending'),
    ('verified', 'Verified'),
    ('rejected', 'Rejected'),
]

# ============================================================================
# EVENT RELATED CHOICES
# ============================================================================


EVENT_STATUS_CHOICES = [
    ('draft', 'Draft'),
    ('published', 'Published'),
    ('cancelled', 'Cancelled'),
    ('completed', 'Completed'),
    ('postponed', 'Postponed'),
]

ALLOWED_GENDER_CHOICES = [
    ('all', 'All'),
    ('male', 'Male Only'),
    ('female', 'Female Only'),
    ('non_binary', 'Non-binary'),
]

TICKET_TYPE_CHOICES = [
    ('standard', 'Standard'),
    ('vip', 'VIP'),
    ('early_bird', 'Early Bird'),
    ('premium', 'Premium'),
    ('general', 'General'),
    ('group', 'Group'),
    ('couple', 'Couple'),
    ('family', 'Family'),
    ('student', 'Student'),
    ('senior_citizen', 'Senior Citizen'),
    ('disabled', 'Disabled'),
    ('other', 'Other'),
]

INVITE_TYPE_CHOICES = [
    ('direct', 'Direct'),
    ('share_link', 'Share Link'),
]


# ============================================================================
# ATTENDANCE RELATED CHOICES
# ============================================================================

ATTENDANCE_STATUS_CHOICES = [
    ('going', 'Going'),
    ('not_going', 'Not Going'),
    ('maybe', 'Maybe'),
    ('checked_in', 'Checked In'),
    ('cancelled', 'Cancelled'),
]

REQUEST_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('accepted', 'Accepted'),
    ('declined', 'Declined'),
    ('cancelled', 'Cancelled'),
    ('expired', 'Expired'),
]

INVITE_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('accepted', 'Accepted'),
    ('declined', 'Declined'),
    ('expired', 'Expired'),
]


# ============================================================================
# PAYMENT RELATED CHOICES
# ============================================================================

PAYMENT_STATUS_CHOICES = [
    ('created', 'Created'),
    ('pending', 'Pending'),
    ('paid', 'Paid'),
    ('completed', 'Completed'),
    ('failed', 'Failed'),
    ('cancelled', 'Cancelled'),
    ('refunded', 'Refunded'),
    ('unpaid', 'Unpaid'),  # For attendance records
]

PAYMENT_PROVIDER_CHOICES = [
    ('razorpay', 'Razorpay'),
    ('stripe', 'Stripe'),
    ('paypal', 'PayPal'),
    ('paytm', 'Paytm'),
    ('phonepe', 'PhonePe'),
    ('gpay', 'Google Pay'),
    ('payu', 'PayU'),
    ('cash', 'Cash'),
    ('bank_transfer', 'Bank Transfer'),
]

CURRENCY_CHOICES = [
    ('INR', 'Indian Rupee (₹)'),
    ('USD', 'US Dollar ($)'),
    ('EUR', 'Euro (€)'),
    ('GBP', 'British Pound (£)'),
]


# ============================================================================
# NOTIFICATION RELATED CHOICES
# ============================================================================

NOTIFICATION_TYPE_CHOICES = [
    ('event_request', 'Event Request'),
    ('event_invite', 'Event Invite'),
    ('event_update', 'Event Update'),
    ('event_cancelled', 'Event Cancelled'),
    ('event_live', 'Event Goes Live'),
    ('payment_success', 'Payment Success'),
    ('payment_failed', 'Payment Failed'),
    ('booking_success', 'Booking Success'),
    ('request_approved', 'Request Approved'),
    ('new_join_request', 'New Join Request'),
    ('ticket_confirmed', 'Ticket Confirmed'),
    ('event_started', 'Event Started'),
    ('payout_reminder', 'Payout Reminder'),
    ('reminder', 'Reminder'),
    ('system', 'System'),
    ('promotional', 'Promotional'),
]


# ============================================================================
# AUDIT RELATED CHOICES
# ============================================================================

AUDIT_ACTION_CHOICES = [
    ('create', 'Create'),
    ('update', 'Update'),
    ('delete', 'Delete'),
    ('login', 'Login'),
    ('logout', 'Logout'),
    ('password_change', 'Password Change'),
    ('profile_update', 'Profile Update'),
]


# ============================================================================
# VENUE RELATED CHOICES
# ============================================================================

VENUE_TYPE_CHOICES = [
    ('indoor', 'Indoor'),
    ('outdoor', 'Outdoor'),
    ('virtual', 'Virtual'),
    ('hybrid', 'Hybrid'),
]


# ============================================================================
# OTP RELATED CHOICES
# ============================================================================

OTP_TYPE_CHOICES = [
    ('signup', 'Signup'),
    ('login', 'Login'),
    ('password_reset', 'Password Reset'),
    ('phone_verification', 'Phone Verification'),
    ('transaction', 'Transaction'),
]

OTP_STATUS_CHOICES = [
    ('pending', 'Pending'),
    ('verified', 'Verified'),
    ('expired', 'Expired'),
    ('failed', 'Failed'),
]

# ============================================================================
# CONSTANTS
# ============================================================================

# OTP Configuration
OTP_VALIDITY_MINUTES = 10
OTP_MAX_ATTEMPTS = 3
OTP_LENGTH = 4

# Profile Configuration
MIN_PROFILE_PICTURES = 1
MAX_PROFILE_PICTURES = 6
MIN_EVENT_INTERESTS = 1
MAX_EVENT_INTERESTS = 5

# Event Configuration
MIN_EVENT_TITLE_LENGTH = 3
MAX_EVENT_TITLE_LENGTH = 200
MIN_EVENT_DESCRIPTION_LENGTH = 10
MAX_EVENT_DESCRIPTION_LENGTH = 20000


# Notification Configuration
NOTIFICATION_RETENTION_DAYS = 30
PUSH_NOTIFICATION_BATCH_SIZE = 100

# File Upload Configuration
MAX_FILE_SIZE_MB = 5
ALLOWED_IMAGE_FORMATS = ['jpg', 'jpeg', 'png', 'webp']
ALLOWED_DOCUMENT_FORMATS = ['pdf', 'doc', 'docx']

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_choice_display(choices, value):
    """
    Get the display value for a choice field.
    
    Args:
        choices: List of tuples (value, display)
        value: The actual value
        
    Returns:
        str: Display value or the original value if not found
    """
    choice_dict = dict(choices)
    return choice_dict.get(value, value)

def get_choice_values(choices):
    """
    Get all values from a choices list.
    
    Args:
        choices: List of tuples (value, display)
        
    Returns:
        list: List of all values
    """
    return [choice[0] for choice in choices]

def get_choice_displays(choices):
    """
    Get all display values from a choices list.
    
    Args:
        choices: List of tuples (value, display)
        
    Returns:
        list: List of all display values
    """
    return [choice[1] for choice in choices]
