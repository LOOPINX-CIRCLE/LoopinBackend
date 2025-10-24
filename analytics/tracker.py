"""
PostHog Analytics Tracker

This module provides a centralized way to track events across the application.
It includes event tracking for user actions, event management, payments, and attendance.
"""

import posthog
from django.conf import settings
from django.contrib.auth.models import User
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AnalyticsTracker:
    """Centralized analytics tracking using PostHog"""
    
    @staticmethod
    def capture_event(
        user: Optional[User], 
        event_name: str, 
        properties: Dict[str, Any] = None,
        distinct_id: Optional[str] = None
    ):
        """
        Capture an event in PostHog
        
        Args:
            user: Django user object (optional)
            event_name: Name of the event to track
            properties: Dictionary of event properties
            distinct_id: Custom distinct ID (defaults to user.id)
        """
        try:
            if not posthog.api_key:
                logger.warning("PostHog API key not configured, skipping event tracking")
                return
                
            # Use user ID as distinct_id if user is provided
            if user and user.is_authenticated:
                distinct_id = distinct_id or str(user.id)
                
                # Set user properties
                posthog.identify(distinct_id, {
                    'email': user.email if hasattr(user, 'email') else None,
                    'username': user.username if hasattr(user, 'username') else None,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                })
            else:
                # Use session-based distinct_id for anonymous users
                distinct_id = distinct_id or 'anonymous'
            
            # Capture the event
            posthog.capture(distinct_id, event_name, properties or {})
            
        except Exception as e:
            logger.error(f"Failed to capture event {event_name}: {str(e)}")
    
    @staticmethod
    def track_user_registration(user: User, phone_number: str, method: str = 'phone'):
        """Track user registration events"""
        AnalyticsTracker.capture_event(
            user, 
            'User Registered',
            {
                'registration_method': method,
                'phone_number': phone_number,
                'user_type': 'new_user'
            }
        )
    
    @staticmethod
    def track_user_login(user: User, method: str = 'phone_otp'):
        """Track user login events"""
        AnalyticsTracker.capture_event(
            user,
            'User Logged In',
            {
                'login_method': method,
                'user_type': 'returning_user' if user.date_joined else 'new_user'
            }
        )
    
    @staticmethod
    def track_profile_completion(user: User, profile_data: Dict[str, Any]):
        """Track profile completion events"""
        AnalyticsTracker.capture_event(
            user,
            'Profile Completed',
            {
                'profile_fields_completed': len([k for k, v in profile_data.items() if v]),
                'has_interests': bool(profile_data.get('interests')),
                'has_profile_pictures': bool(profile_data.get('profile_pictures')),
                'gender': profile_data.get('gender'),
                'location': profile_data.get('location')
            }
        )
    
    @staticmethod
    def track_event_creation(user: User, event, venue=None):
        """Track event creation events"""
        properties = {
            'event_id': event.id,
            'event_title': event.title,
            'event_status': event.status,
            'is_public': event.is_public,
            'max_capacity': event.max_capacity,
            'has_venue': bool(venue),
            'venue_type': venue.venue_type if venue else None,
            'venue_city': venue.city if venue else None
        }
        
        AnalyticsTracker.capture_event(user, 'Event Created', properties)
    
    @staticmethod
    def track_event_request(user: User, event, seats_requested: int, message: str = ''):
        """Track event request events"""
        properties = {
            'event_id': event.id,
            'event_title': event.title,
            'event_host_id': event.host.id,
            'seats_requested': seats_requested,
            'has_message': bool(message.strip()),
            'event_capacity': event.max_capacity,
            'event_current_attendance': event.going_count
        }
        
        AnalyticsTracker.capture_event(user, 'Event Requested', properties)
    
    @staticmethod
    def track_event_invite(user: User, event, invited_user: User, message: str = ''):
        """Track event invite events"""
        properties = {
            'event_id': event.id,
            'event_title': event.title,
            'invited_user_id': invited_user.id,
            'has_message': bool(message.strip()),
            'event_capacity': event.max_capacity,
            'event_current_attendance': event.going_count
        }
        
        AnalyticsTracker.capture_event(user, 'Event Invite Sent', properties)
    
    @staticmethod
    def track_payment_initiated(user: User, payment_order, event):
        """Track payment initiation events"""
        properties = {
            'payment_order_id': payment_order.id,
            'event_id': event.id,
            'event_title': event.title,
            'amount': float(payment_order.amount),
            'currency': payment_order.currency,
            'payment_provider': payment_order.provider,
            'order_expires_at': payment_order.expires_at.isoformat() if payment_order.expires_at else None
        }
        
        AnalyticsTracker.capture_event(user, 'Payment Initiated', properties)
    
    @staticmethod
    def track_payment_completed(user: User, payment_order, event):
        """Track payment completion events"""
        properties = {
            'payment_order_id': payment_order.id,
            'event_id': event.id,
            'event_title': event.title,
            'amount': float(payment_order.amount),
            'currency': payment_order.currency,
            'payment_provider': payment_order.provider,
            'payment_method': payment_order.payment_method,
            'transaction_id': payment_order.transaction_id
        }
        
        AnalyticsTracker.capture_event(user, 'Payment Completed', properties)
    
    @staticmethod
    def track_payment_failed(user: User, payment_order, event, failure_reason: str):
        """Track payment failure events"""
        properties = {
            'payment_order_id': payment_order.id,
            'event_id': event.id,
            'event_title': event.title,
            'amount': float(payment_order.amount),
            'currency': payment_order.currency,
            'payment_provider': payment_order.provider,
            'failure_reason': failure_reason
        }
        
        AnalyticsTracker.capture_event(user, 'Payment Failed', properties)
    
    @staticmethod
    def track_attendance_checkin(user: User, attendance_record, event):
        """Track attendance check-in events"""
        properties = {
            'attendance_record_id': attendance_record.id,
            'event_id': event.id,
            'event_title': event.title,
            'seats': attendance_record.seats,
            'payment_status': attendance_record.payment_status,
            'event_capacity': event.max_capacity
        }
        
        AnalyticsTracker.capture_event(user, 'Event Checked In', properties)
    
    @staticmethod
    def track_attendance_checkout(user: User, attendance_record, event):
        """Track attendance check-out events"""
        properties = {
            'attendance_record_id': attendance_record.id,
            'event_id': event.id,
            'event_title': event.title,
            'seats': attendance_record.seats,
            'attendance_duration_minutes': attendance_record.attendance_duration.total_seconds() / 60 if attendance_record.attendance_duration else None
        }
        
        AnalyticsTracker.capture_event(user, 'Event Checked Out', properties)
    
    @staticmethod
    def track_event_interest_selection(user: User, interests: list):
        """Track event interest selection events"""
        properties = {
            'interests_selected': interests,
            'interest_count': len(interests),
            'interests': [interest.name for interest in interests] if interests else []
        }
        
        AnalyticsTracker.capture_event(user, 'Event Interests Selected', properties)
    
    @staticmethod
    def track_venue_creation(user: User, venue):
        """Track venue creation events"""
        properties = {
            'venue_id': venue.id,
            'venue_name': venue.name,
            'venue_city': venue.city,
            'venue_type': venue.venue_type,
            'venue_capacity': venue.capacity
        }
        
        AnalyticsTracker.capture_event(user, 'Venue Created', properties)


# Convenience functions for easy importing
def track_event(user, event_name, properties=None):
    """Convenience function to track events"""
    AnalyticsTracker.capture_event(user, event_name, properties)

def track_user_action(user, action, **kwargs):
    """Convenience function to track user actions"""
    AnalyticsTracker.capture_event(user, f'User {action}', kwargs)
