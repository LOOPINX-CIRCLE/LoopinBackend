"""
Notification template registry - Single source of truth for all transactional notifications.

IDEA-1: Stable, Centralized, System-Owned Notification Templates

This module provides:
- NotificationTemplate enum for template keys (not strings)
- TEMPLATES registry with title, body, target_screen, type
- Template rendering with strict parameter validation
- Fail-loud behavior on missing parameters

⚠️ CRITICAL RULES:
1. All transactional notifications MUST use templates from here
2. No raw strings allowed in services/signals/dispatcher
3. Template changes require product review and QA
4. Missing parameters cause exceptions (no silent fallbacks)
5. This is the ONLY place with notification copy

Change Policy:
- Templates change max once per month
- Changes go through product review + QA
- No emergency edits unless critical bug
"""

import re
from enum import Enum
from typing import Dict, Any, Optional
from dataclasses import dataclass


class NotificationTemplate(Enum):
    """Enum of all notification template keys.
    
    Use enum values (e.g., NotificationTemplate.BOOKING_CONFIRMED) NOT strings.
    This prevents typos and ensures consistency.
    """
    # Payment & Booking Notifications
    BOOKING_CONFIRMED = "booking_confirmed"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    
    # Event Notifications
    EVENT_LIVE = "event_live"
    EVENT_CANCELLED = "event_cancelled"
    EVENT_CREATED = "event_created"
    
    # Request & Invite Notifications
    EVENT_INVITE = "event_invite"
    INVITE_ACCEPTED = "invite_accepted"
    INVITE_DECLINED = "invite_declined"
    REQUEST_APPROVED = "request_approved"
    REQUEST_DECLINED = "request_declined"
    NEW_JOIN_REQUEST = "new_join_request"
    
    # Attendance & Check-in
    TICKET_CONFIRMED = "ticket_confirmed"
    CHECK_IN_STARTED = "check_in_started"
    
    # System Notifications
    PROFILE_COMPLETED = "profile_completed"


@dataclass
class NotificationTemplateDefinition:
    """Template definition with all required fields."""
    title: str  # Template string with {{param}} placeholders
    body: str  # Template string with {{param}} placeholders
    target_screen: str  # Route/screen name for mobile app navigation
    type: str  # Notification type (must match NOTIFICATION_TYPE_CHOICES)
    required_params: set  # Set of required parameter names


# Template Registry - Single Source of Truth
TEMPLATES: Dict[NotificationTemplate, NotificationTemplateDefinition] = {
    # Payment & Booking
    NotificationTemplate.BOOKING_CONFIRMED: NotificationTemplateDefinition(
        title="Booking Confirmed!",
        body="Your spot at {{event_name}} is locked. View your ticket now.",
        target_screen="ticket_detail",
        type="payment_success",
        required_params={"event_name"}
    ),
    NotificationTemplate.PAYMENT_SUCCESS: NotificationTemplateDefinition(
        title="Payment Successful",
        body="Your payment for event '{{event_name}}' has been processed successfully.",
        target_screen="event_detail",
        type="payment_success",
        required_params={"event_name"}
    ),
    NotificationTemplate.PAYMENT_FAILED: NotificationTemplateDefinition(
        title="Payment Failed",
        body="Your payment for event '{{event_name}}' could not be processed. Please try again.",
        target_screen="payment_retry",
        type="payment_failed",
        required_params={"event_name"}
    ),
    
    # Event Notifications
    NotificationTemplate.EVENT_LIVE: NotificationTemplateDefinition(
        title="New Event Alert!",
        body="{{event_name}} by {{host_name}} is live. Request your spot!",
        target_screen="event_details",
        type="event_update",
        required_params={"event_name", "host_name"}
    ),
    NotificationTemplate.EVENT_CANCELLED: NotificationTemplateDefinition(
        title="Event Cancelled",
        body="The event '{{event_name}}' has been cancelled.",
        target_screen="event_detail",
        type="event_cancelled",
        required_params={"event_name"}
    ),
    NotificationTemplate.EVENT_CREATED: NotificationTemplateDefinition(
        title="Event Created Successfully",
        body="Your event '{{event_name}}' has been created successfully.",
        target_screen="event_detail",
        type="event_update",
        required_params={"event_name"}
    ),
    
    # Request & Invite
    NotificationTemplate.EVENT_INVITE: NotificationTemplateDefinition(
        title="You're Invited!",
        body="{{host_name}} sent you a private invite to {{event_name}}.",
        target_screen="event_detail",
        type="event_invite",
        required_params={"host_name", "event_name"}
    ),
    NotificationTemplate.INVITE_ACCEPTED: NotificationTemplateDefinition(
        title="Invitation Accepted: {{event_name}}",
        body="{{user_name}} has accepted your invitation to '{{event_name}}'",
        target_screen="event_detail",
        type="event_invite",
        required_params={"event_name", "user_name"}
    ),
    NotificationTemplate.INVITE_DECLINED: NotificationTemplateDefinition(
        title="Invitation Declined: {{event_name}}",
        body="{{user_name}} has declined your invitation to '{{event_name}}'",
        target_screen="event_detail",
        type="event_invite",
        required_params={"event_name", "user_name"}
    ),
    NotificationTemplate.REQUEST_APPROVED: NotificationTemplateDefinition(
        title="Request Accepted!",
        body="You're approved for {{event_name}} by {{host_name}}.",
        target_screen="event_detail",
        type="event_request",
        required_params={"event_name", "host_name"}
    ),
    NotificationTemplate.REQUEST_DECLINED: NotificationTemplateDefinition(
        title="Event Request Declined",
        body="Your request to join '{{event_name}}' has been declined.",
        target_screen="event_detail",
        type="event_request",
        required_params={"event_name"}
    ),
    NotificationTemplate.NEW_JOIN_REQUEST: NotificationTemplateDefinition(
        title="New Request!",
        body="{{user_name}} wants to join {{event_name}}. Tap to approve.",
        target_screen="event_detail",
        type="event_request",
        required_params={"user_name", "event_name"}
    ),
    
    # Attendance & Check-in
    NotificationTemplate.TICKET_CONFIRMED: NotificationTemplateDefinition(
        title="Ticket Confirmed",
        body="Your ticket for '{{event_name}}' has been confirmed! Check your tickets.",
        target_screen="ticket_detail",
        type="reminder",
        required_params={"event_name"}
    ),
    NotificationTemplate.CHECK_IN_STARTED: NotificationTemplateDefinition(
        title="Check-in is Live!",
        body="{{event_name}} has started. Start scanning guest tickets now.",
        target_screen="check_in",
        type="reminder",
        required_params={"event_name"}
    ),
    
    # System
    NotificationTemplate.PROFILE_COMPLETED: NotificationTemplateDefinition(
        title="Profile Completed",
        body="Congratulations! Your profile has been completed successfully.",
        target_screen="profile",
        type="system",
        required_params=set()  # No parameters needed
    ),
}


def render_template(
    template: NotificationTemplate,
    context: Dict[str, Any]
) -> Dict[str, str]:
    """
    Render notification template with context parameters.
    
    Args:
        template: NotificationTemplate enum key
        context: Dictionary of parameter values (e.g., {"event_name": "Concert", ...})
        
    Returns:
        Dict with 'title', 'body', 'target_screen', 'type' keys
        
    Raises:
        ValueError: If template not found or required parameters missing
        KeyError: If template key invalid
    """
    if template not in TEMPLATES:
        raise ValueError(f"Template {template} not found in registry")
    
    template_def = TEMPLATES[template]
    
    # Extract all {{param}} placeholders from title and body
    title_params = set(re.findall(r'\{\{(\w+)\}\}', template_def.title))
    body_params = set(re.findall(r'\{\{(\w+)\}\}', template_def.body))
    all_required_params = title_params | body_params | template_def.required_params
    
    # Validate all required parameters are provided
    missing_params = all_required_params - set(context.keys())
    if missing_params:
        raise ValueError(
            f"Template {template.value} missing required parameters: {missing_params}. "
            f"Provided: {set(context.keys())}, Required: {all_required_params}"
        )
    
    # Render title and body with parameter substitution
    rendered_title = template_def.title
    rendered_body = template_def.body
    
    for param, value in context.items():
        # Escape any existing braces and replace placeholders
        placeholder = f"{{{{{param}}}}}"
        rendered_title = rendered_title.replace(placeholder, str(value))
        rendered_body = rendered_body.replace(placeholder, str(value))
    
    # Verify no unreplaced placeholders remain (fail loudly)
    remaining_title_params = re.findall(r'\{\{(\w+)\}\}', rendered_title)
    remaining_body_params = re.findall(r'\{\{(\w+)\}\}', rendered_body)
    if remaining_title_params or remaining_body_params:
        raise ValueError(
            f"Template {template.value} has unreplaced placeholders: "
            f"title={remaining_title_params}, body={remaining_body_params}. "
            f"This indicates a template definition error."
        )
    
    return {
        'title': rendered_title,
        'body': rendered_body,
        'target_screen': template_def.target_screen,
        'type': template_def.type,
    }


def get_template_info(template: NotificationTemplate) -> NotificationTemplateDefinition:
    """
    Get template definition without rendering.
    
    Useful for debugging and validation.
    
    Args:
        template: NotificationTemplate enum key
        
    Returns:
        NotificationTemplateDefinition
        
    Raises:
        KeyError: If template not found
    """
    if template not in TEMPLATES:
        raise KeyError(f"Template {template} not found in registry")
    return TEMPLATES[template]
