"""
Data collection layer for analytics.

This module provides middleware, signals, and event tracking
for comprehensive data collection across the platform.
"""

import time
import json
import logging
import uuid
from typing import Dict, Any, Optional
from django.utils.deprecation import MiddlewareMixin
from django.dispatch import receiver
from django.db.models.signals import post_save, pre_save, post_delete
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.contrib.auth.models import User
from django.utils import timezone
from django.conf import settings
import posthog

from .models import UserEvent, SystemLog, BusinessMetric, AIInsight
from .ai_services import SentimentAnalysisService, UserBehaviorAnalysisService

logger = logging.getLogger(__name__)


class AnalyticsMiddleware(MiddlewareMixin):
    """Middleware for comprehensive analytics data collection"""
    
    def __init__(self, get_response):
        self.get_response = get_response
        self.sentiment_service = SentimentAnalysisService()
        super().__init__(get_response)
    
    def process_request(self, request):
        """Process incoming request"""
        request.analytics_start_time = time.time()
        request.analytics_session_id = self._get_or_create_session_id(request)
        request.analytics_user_id = getattr(request.user, 'id', None) if hasattr(request, 'user') else None
        
        # Log system event
        self._log_system_event(request, 'request_start')
        
        return None
    
    def process_response(self, request, response):
        """Process outgoing response"""
        if hasattr(request, 'analytics_start_time'):
            response_time_ms = int((time.time() - request.analytics_start_time) * 1000)
            
            # Create user event
            self._create_user_event(request, response, response_time_ms)
            
            # Log system event
            self._log_system_event(request, 'request_end', {
                'response_time_ms': response_time_ms,
                'status_code': response.status_code
            })
        
        return response
    
    def process_exception(self, request, exception):
        """Process exceptions"""
        self._log_system_event(request, 'exception', {
            'exception_type': type(exception).__name__,
            'exception_message': str(exception)
        })
        
        # Create error event
        self._create_user_event(request, None, None, event_type='error', 
                              metadata={'exception': str(exception)})
        
        return None
    
    def _get_or_create_session_id(self, request) -> str:
        """Get or create session ID for analytics"""
        session_id = request.session.get('analytics_session_id')
        if not session_id:
            session_id = str(uuid.uuid4())
            request.session['analytics_session_id'] = session_id
        return session_id
    
    def _create_user_event(self, request, response, response_time_ms: Optional[int], 
                          event_type: str = 'api_call', metadata: Dict[str, Any] = None):
        """Create user event record"""
        try:
            # Extract user information
            user = getattr(request, 'user', None)
            user_id = user.id if user and user.is_authenticated else None
            
            # Extract request information
            event_name = f"{request.method} {request.path}"
            action = request.method.lower()
            
            # Extract device information
            user_agent = request.META.get('HTTP_USER_AGENT', '')
            device_type = self._extract_device_type(user_agent)
            browser = self._extract_browser(user_agent)
            os = self._extract_os(user_agent)
            
            # Analyze sentiment if there's text content
            sentiment_score = None
            if hasattr(response, 'content') and response.content:
                try:
                    content_str = str(response.content)[:1000]  # Limit content length
                    sentiment_result = self.sentiment_service.analyze_text_sentiment(content_str)
                    sentiment_score = sentiment_result['score']
                except Exception as e:
                    logger.warning(f"Sentiment analysis failed: {e}")
            
            # Create event
            event = UserEvent.objects.create(
                user_id=user_id,
                session_id=getattr(request, 'analytics_session_id', ''),
                event_type=event_type,
                event_name=event_name,
                page_url=request.build_absolute_uri(),
                action=action,
                metadata=metadata or {},
                user_agent=user_agent,
                ip_address=self._get_client_ip(request),
                referrer=request.META.get('HTTP_REFERER', ''),
                response_time_ms=response_time_ms,
                status_code=getattr(response, 'status_code', None),
                device_type=device_type,
                browser=browser,
                os=os,
                sentiment_score=sentiment_score,
                source='middleware'
            )
            
            # Send to PostHog
            self._send_to_posthog(event, user)
            
        except Exception as e:
            logger.error(f"Failed to create user event: {e}")
    
    def _log_system_event(self, request, operation: str, metadata: Dict[str, Any] = None):
        """Log system-level event"""
        try:
            SystemLog.objects.create(
                log_level='info',
                component='middleware',
                operation=operation,
                resource=request.path,
                duration_ms=int((time.time() - getattr(request, 'analytics_start_time', time.time())) * 1000),
                request_id=getattr(request, 'analytics_session_id', ''),
                user_id=str(getattr(request.user, 'id', '')) if hasattr(request, 'user') and request.user.is_authenticated else '',
                session_id=getattr(request, 'analytics_session_id', ''),
                metadata=metadata or {},
                source='middleware'
            )
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")
    
    def _send_to_posthog(self, event: UserEvent, user: Optional[User]):
        """Send event to PostHog"""
        try:
            if not posthog.api_key:
                return
            
            distinct_id = str(user.id) if user and user.is_authenticated else event.session_id
            
            # Prepare PostHog properties
            properties = {
                'event_type': event.event_type,
                'page_url': event.page_url,
                'action': event.action,
                'device_type': event.device_type,
                'browser': event.browser,
                'os': event.os,
                'response_time_ms': event.response_time_ms,
                'status_code': event.status_code,
                'sentiment_score': event.sentiment_score,
                'session_id': event.session_id,
            }
            
            # Add metadata
            properties.update(event.metadata)
            
            # Send to PostHog
            posthog.capture(distinct_id, event.event_name, properties)
            
        except Exception as e:
            logger.error(f"Failed to send to PostHog: {e}")
    
    def _extract_device_type(self, user_agent: str) -> str:
        """Extract device type from user agent"""
        user_agent_lower = user_agent.lower()
        if 'mobile' in user_agent_lower or 'android' in user_agent_lower:
            return 'mobile'
        elif 'tablet' in user_agent_lower or 'ipad' in user_agent_lower:
            return 'tablet'
        else:
            return 'desktop'
    
    def _extract_browser(self, user_agent: str) -> str:
        """Extract browser from user agent"""
        user_agent_lower = user_agent.lower()
        if 'chrome' in user_agent_lower:
            return 'chrome'
        elif 'firefox' in user_agent_lower:
            return 'firefox'
        elif 'safari' in user_agent_lower:
            return 'safari'
        elif 'edge' in user_agent_lower:
            return 'edge'
        else:
            return 'unknown'
    
    def _extract_os(self, user_agent: str) -> str:
        """Extract OS from user agent"""
        user_agent_lower = user_agent.lower()
        if 'windows' in user_agent_lower:
            return 'windows'
        elif 'mac' in user_agent_lower or 'macos' in user_agent_lower:
            return 'macos'
        elif 'linux' in user_agent_lower:
            return 'linux'
        elif 'android' in user_agent_lower:
            return 'android'
        elif 'ios' in user_agent_lower:
            return 'ios'
        else:
            return 'unknown'
    
    def _get_client_ip(self, request) -> str:
        """Get client IP address"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


# Signal handlers for automatic event tracking

@receiver(user_logged_in)
def track_user_login(sender, request, user, **kwargs):
    """Track user login events"""
    try:
        # Create user event
        UserEvent.objects.create(
            user=user,
            session_id=request.session.get('analytics_session_id', ''),
            event_type='user_action',
            event_name='user_logged_in',
            action='login',
            metadata={
                'login_method': 'password',  # Could be enhanced to detect OTP, etc.
                'ip_address': AnalyticsMiddleware()._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')
            },
            source='signal'
        )
        
        # Send to PostHog
        posthog.capture(str(user.id), 'User Logged In', {
            'login_method': 'password',
            'user_id': user.id,
            'username': user.username
        })
        
        logger.info(f"Tracked login for user {user.id}")
        
    except Exception as e:
        logger.error(f"Failed to track user login: {e}")


@receiver(user_logged_out)
def track_user_logout(sender, request, user, **kwargs):
    """Track user logout events"""
    try:
        # Create user event
        UserEvent.objects.create(
            user=user,
            session_id=request.session.get('analytics_session_id', ''),
            event_type='user_action',
            event_name='user_logged_out',
            action='logout',
            metadata={
                'ip_address': AnalyticsMiddleware()._get_client_ip(request),
                'user_agent': request.META.get('HTTP_USER_AGENT', '')
            },
            source='signal'
        )
        
        # Send to PostHog
        posthog.capture(str(user.id), 'User Logged Out', {
            'user_id': user.id,
            'username': user.username
        })
        
        logger.info(f"Tracked logout for user {user.id}")
        
    except Exception as e:
        logger.error(f"Failed to track user logout: {e}")


# Event tracking signals for business events

@receiver(post_save, sender='events.Event')
def track_event_creation(sender, instance, created, **kwargs):
    """Track event creation"""
    if created:
        try:
            UserEvent.objects.create(
                user=instance.host,
                event_type='conversion',
                event_name='event_created',
                action='create',
                metadata={
                    'event_id': instance.id,
                    'event_title': instance.title,
                    'event_status': instance.status,
                    'is_public': instance.is_public,
                    'max_capacity': instance.max_capacity
                },
                source='signal'
            )
            
            # Send to PostHog
            posthog.capture(str(instance.host.id), 'Event Created', {
                'event_id': instance.id,
                'event_title': instance.title,
                'event_status': instance.status,
                'is_public': instance.is_public,
                'max_capacity': instance.max_capacity
            })
            
        except Exception as e:
            logger.error(f"Failed to track event creation: {e}")


@receiver(post_save, sender='events.EventRequest')
def track_event_request(sender, instance, created, **kwargs):
    """Track event requests"""
    if created:
        try:
            UserEvent.objects.create(
                user=instance.requester,
                event_type='conversion',
                event_name='event_requested',
                action='request',
                metadata={
                    'event_id': instance.event.id,
                    'event_title': instance.event.title,
                    'seats_requested': instance.seats_requested,
                    'has_message': bool(instance.message)
                },
                source='signal'
            )
            
            # Send to PostHog
            posthog.capture(str(instance.requester.id), 'Event Requested', {
                'event_id': instance.event.id,
                'event_title': instance.event.title,
                'seats_requested': instance.seats_requested,
                'has_message': bool(instance.message)
            })
            
        except Exception as e:
            logger.error(f"Failed to track event request: {e}")


@receiver(post_save, sender='payments.PaymentOrder')
def track_payment_events(sender, instance, created, **kwargs):
    """Track payment events"""
    try:
        if created:
            # Payment initiated
            UserEvent.objects.create(
                user=instance.user,
                event_type='conversion',
                event_name='payment_initiated',
                action='initiate_payment',
                metadata={
                    'payment_order_id': instance.id,
                    'event_id': instance.event.id,
                    'amount': float(instance.amount),
                    'currency': instance.currency,
                    'provider': instance.provider
                },
                revenue_impact=float(instance.amount),
                source='signal'
            )
            
            posthog.capture(str(instance.user.id), 'Payment Initiated', {
                'payment_order_id': instance.id,
                'event_id': instance.event.id,
                'amount': float(instance.amount),
                'currency': instance.currency,
                'provider': instance.provider
            })
        
        # Check for status changes
        if instance.status == 'completed':
            UserEvent.objects.create(
                user=instance.user,
                event_type='conversion',
                event_name='payment_completed',
                action='complete_payment',
                metadata={
                    'payment_order_id': instance.id,
                    'event_id': instance.event.id,
                    'amount': float(instance.amount),
                    'currency': instance.currency,
                    'provider': instance.provider
                },
                revenue_impact=float(instance.amount),
                source='signal'
            )
            
            posthog.capture(str(instance.user.id), 'Payment Completed', {
                'payment_order_id': instance.id,
                'event_id': instance.event.id,
                'amount': float(instance.amount),
                'currency': instance.currency,
                'provider': instance.provider
            })
        
        elif instance.status == 'failed':
            UserEvent.objects.create(
                user=instance.user,
                event_type='error',
                event_name='payment_failed',
                action='fail_payment',
                metadata={
                    'payment_order_id': instance.id,
                    'event_id': instance.event.id,
                    'amount': float(instance.amount),
                    'currency': instance.currency,
                    'provider': instance.provider,
                    'failure_reason': instance.failure_reason
                },
                source='signal'
            )
            
            posthog.capture(str(instance.user.id), 'Payment Failed', {
                'payment_order_id': instance.id,
                'event_id': instance.event.id,
                'amount': float(instance.amount),
                'currency': instance.currency,
                'provider': instance.provider,
                'failure_reason': instance.failure_reason
            })
            
    except Exception as e:
        logger.error(f"Failed to track payment event: {e}")


@receiver(post_save, sender='attendances.AttendanceRecord')
def track_attendance_events(sender, instance, created, **kwargs):
    """Track attendance events"""
    try:
        if created:
            # Attendance record created
            UserEvent.objects.create(
                user=instance.user,
                event_type='conversion',
                event_name='attendance_recorded',
                action='record_attendance',
                metadata={
                    'attendance_record_id': instance.id,
                    'event_id': instance.event.id,
                    'status': instance.status,
                    'payment_status': instance.payment_status,
                    'seats': instance.seats
                },
                source='signal'
            )
            
            posthog.capture(str(instance.user.id), 'Attendance Recorded', {
                'attendance_record_id': instance.id,
                'event_id': instance.event.id,
                'status': instance.status,
                'payment_status': instance.payment_status,
                'seats': instance.seats
            })
        
        # Check for status changes (check-in/check-out)
        if instance.status == 'checked_in' and instance.checked_in_at:
            UserEvent.objects.create(
                user=instance.user,
                event_type='engagement',
                event_name='event_checked_in',
                action='check_in',
                metadata={
                    'attendance_record_id': instance.id,
                    'event_id': instance.event.id,
                    'checked_in_at': instance.checked_in_at.isoformat()
                },
                source='signal'
            )
            
            posthog.capture(str(instance.user.id), 'Event Checked In', {
                'attendance_record_id': instance.id,
                'event_id': instance.event.id,
                'checked_in_at': instance.checked_in_at.isoformat()
            })
        
        elif instance.status == 'not_going' and instance.checked_out_at:
            UserEvent.objects.create(
                user=instance.user,
                event_type='engagement',
                event_name='event_checked_out',
                action='check_out',
                metadata={
                    'attendance_record_id': instance.id,
                    'event_id': instance.event.id,
                    'checked_out_at': instance.checked_out_at.isoformat(),
                    'attendance_duration': str(instance.attendance_duration) if instance.attendance_duration else None
                },
                source='signal'
            )
            
            posthog.capture(str(instance.user.id), 'Event Checked Out', {
                'attendance_record_id': instance.id,
                'event_id': instance.event.id,
                'checked_out_at': instance.checked_out_at.isoformat()
            })
            
    except Exception as e:
        logger.error(f"Failed to track attendance event: {e}")


@receiver(post_save, sender='users.UserProfile')
def track_profile_updates(sender, instance, created, **kwargs):
    """Track profile updates"""
    if not created:  # Only track updates, not initial creation
        try:
            UserEvent.objects.create(
                user=instance.user,
                event_type='user_action',
                event_name='profile_updated',
                action='update_profile',
                metadata={
                    'profile_id': instance.id,
                    'is_verified': instance.is_verified,
                    'has_bio': bool(instance.bio),
                    'has_location': bool(instance.location),
                    'has_profile_pictures': bool(instance.profile_pictures),
                    'gender': instance.gender
                },
                source='signal'
            )
            
            posthog.capture(str(instance.user.id), 'Profile Updated', {
                'profile_id': instance.id,
                'is_verified': instance.is_verified,
                'has_bio': bool(instance.bio),
                'has_location': bool(instance.location),
                'has_profile_pictures': bool(instance.profile_pictures),
                'gender': instance.gender
            })
            
        except Exception as e:
            logger.error(f"Failed to track profile update: {e}")


@receiver(post_save, sender='users.PhoneOTP')
def track_otp_events(sender, instance, created, **kwargs):
    """Track OTP verification events"""
    try:
        if created:
            # OTP generated
            UserEvent.objects.create(
                user_id=None,  # OTP might be for anonymous user
                session_id='',  # Will be filled by middleware
                event_type='user_action',
                event_name='otp_generated',
                action='generate_otp',
                metadata={
                    'phone_number': instance.phone_number,
                    'otp_type': instance.otp_type,
                    'expires_at': instance.expires_at.isoformat()
                },
                source='signal'
            )
        
        # Check for verification
        if instance.is_verified and instance.status == 'verified':
            UserEvent.objects.create(
                user_id=None,  # Will be linked to user after verification
                session_id='',
                event_type='conversion',
                event_name='otp_verified',
                action='verify_otp',
                metadata={
                    'phone_number': instance.phone_number,
                    'otp_type': instance.otp_type,
                    'attempts': instance.attempts
                },
                source='signal'
            )
            
    except Exception as e:
        logger.error(f"Failed to track OTP event: {e}")
