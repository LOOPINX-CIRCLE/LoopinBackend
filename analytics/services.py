"""
Analytics Services Module

Production-grade analytics aggregation logic for the Admin Dashboard.
All heavy queries and data processing live here, not in views.

Architecture:
- Uses Django ORM with optimized queries (select_related, prefetch_related)
- Implements time-based grouping (TruncWeek, TruncMonth, TruncYear)
- Returns structured data ready for JSON serialization
- Designed for caching (Redis-ready)
"""

from django.db.models import (
    Count, Sum, Avg, Q, F, DecimalField, IntegerField,
    Case, When, Value, CharField
)
from django.db.models.functions import TruncWeek, TruncMonth, TruncYear, Coalesce
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from typing import Dict, List, Any, Optional
from collections import defaultdict
import logging

logger = logging.getLogger(__name__)

# Import models
from django.contrib.auth.models import User
from users.models import UserProfile
from events.models import Event, Venue
from attendances.models import AttendanceRecord
from payments.models import PaymentOrder
from users.models import HostPayoutRequest


# ============================================================================
# USER LIFECYCLE ANALYTICS
# ============================================================================

def get_user_lifecycle_metrics(
    period: str = 'monthly',
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get user lifecycle metrics with time-series data.
    
    Args:
        period: 'weekly', 'monthly', or 'yearly'
        limit: Maximum number of trend data points to return (default: 100, max: 1000)
        offset: Number of trend data points to skip (default: 0)
    
    Returns:
        Dict with metrics and time-series graph data
    """
    now = timezone.now()
    
    # Determine truncation function based on period
    trunc_func = {
        'weekly': TruncWeek,
        'monthly': TruncMonth,
        'yearly': TruncYear,
    }.get(period, TruncMonth)
    
    # Base queryset - all users with profiles
    users_qs = User.objects.select_related('profile').all()
    
    # Total metrics
    total_users = users_qs.count()
    active_users = users_qs.filter(is_active=True).count()
    waitlisted_users = users_qs.filter(is_active=False).count()
    
    # Approval conversion rate
    approval_rate = (active_users / total_users * 100) if total_users > 0 else 0
    
    # Time-series: new users per period
    time_series = (
        users_qs
        .annotate(period=trunc_func('date_joined'))
        .values('period')
        .annotate(
            total_registered=Count('id'),
            active_registered=Count('id', filter=Q(is_active=True)),
            waitlisted_registered=Count('id', filter=Q(is_active=False))
        )
        .order_by('period')
    )
    
    # Convert to list format for Chart.js
    time_series_list = [
        {
            'period': str(item['period']),
            'total': item['total_registered'],
            'active': item['active_registered'],
            'waitlisted': item['waitlisted_registered'],
        }
        for item in time_series
    ]
    
    # Apply pagination to trend data
    total_trend_points = len(time_series_list)
    limit = min(limit, 1000)  # Cap at 1000
    paginated_trend = time_series_list[offset:offset + limit]
    
    # New users in selected period
    period_delta = {
        'weekly': timedelta(weeks=1),
        'monthly': timedelta(days=30),
        'yearly': timedelta(days=365),
    }.get(period, timedelta(days=30))
    
    new_users_period = users_qs.filter(
        date_joined__gte=now - period_delta
    ).count()
    
    return {
        'total_users': total_users,
        'active_users': active_users,
        'waitlisted_users': waitlisted_users,
        'approval_rate': round(approval_rate / 100, 4),  # Convert to decimal (0.92 not 92%)
        'trend': paginated_trend,  # Match spec field name
        'pagination': {
            'limit': limit,
            'offset': offset,
            'total': total_trend_points,
            'has_more': (offset + limit) < total_trend_points,
        },
    }


def get_waitlist_metrics(
    period: str = 'monthly',
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get waitlist-specific metrics.
    
    Args:
        period: 'weekly', 'monthly', or 'yearly'
        limit: Maximum number of trend data points to return (default: 100, max: 1000)
        offset: Number of trend data points to skip (default: 0)
    
    Returns:
        Dict with waitlist metrics and trend graph
    """
    now = timezone.now()
    
    trunc_func = {
        'weekly': TruncWeek,
        'monthly': TruncMonth,
        'yearly': TruncYear,
    }.get(period, TruncMonth)
    
    users_qs = User.objects.all()
    
    total_users = users_qs.count()
    waitlisted_users = users_qs.filter(is_active=False).count()
    active_users = users_qs.filter(is_active=True).count()
    
    approval_rate = (active_users / total_users * 100) if total_users > 0 else 0
    
    # Trend: new waitlisted users per period
    waitlist_trend = (
        users_qs
        .filter(is_active=False)
        .annotate(period=trunc_func('date_joined'))
        .values('period')
        .annotate(count=Count('id'))
        .order_by('period')
    )
    
    trend_list = [
        {
            'period': str(item['period']),
            'count': item['count'],
        }
        for item in waitlist_trend
    ]
    
    # Apply pagination
    total_trend_points = len(trend_list)
    limit = min(limit, 1000)  # Cap at 1000
    paginated_trend = trend_list[offset:offset + limit]
    
    return {
        'total_waitlisted': waitlisted_users,
        'approval_rate': round(approval_rate, 2),
        'trend': paginated_trend,
        'pagination': {
            'limit': limit,
            'offset': offset,
            'total': total_trend_points,
            'has_more': (offset + limit) < total_trend_points,
        },
    }


# ============================================================================
# HOST METRICS
# ============================================================================

def get_host_metrics(
    period: str = 'monthly',
    limit: int = 100,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get host-related metrics.
    
    A user becomes a Host when they create at least one event.
    
    Args:
        period: 'weekly', 'monthly', or 'yearly'
        limit: Maximum number of trend data points to return (default: 100, max: 1000)
        offset: Number of trend data points to skip (default: 0)
    
    Returns:
        Dict with host metrics
    """
    trunc_func = {
        'weekly': TruncWeek,
        'monthly': TruncMonth,
        'yearly': TruncYear,
    }.get(period, TruncMonth)
    
    # Total hosts = distinct event hosts
    total_hosts = Event.objects.values('host').distinct().count()
    
    # New hosts over time
    new_hosts_trend = (
        Event.objects
        .annotate(period=trunc_func('created_at'))
        .values('period', 'host')
        .distinct()
        .values('period')
        .annotate(count=Count('host', distinct=True))
        .order_by('period')
    )
    
    trend_list = [
        {
            'period': str(item['period']),
            'count': item['count'],
        }
        for item in new_hosts_trend
    ]
    
    # Apply pagination
    total_trend_points = len(trend_list)
    limit = min(limit, 1000)  # Cap at 1000
    paginated_trend = trend_list[offset:offset + limit]
    
    # Host approval-to-host conversion rate
    # Get all active users
    active_users = User.objects.filter(is_active=True).count()
    # Get users who have created at least one event
    users_with_events = User.objects.filter(
        profile__hosted_events__isnull=False
    ).distinct().count()
    
    conversion_rate = (users_with_events / active_users * 100) if active_users > 0 else 0
    
    return {
        'total_hosts': total_hosts,
        'conversion_rate': round(conversion_rate / 100, 4),  # Convert to decimal
        'new_hosts': paginated_trend,  # Match spec field name
        'pagination': {
            'limit': limit,
            'offset': offset,
            'total': total_trend_points,
            'has_more': (offset + limit) < total_trend_points,
        },
    }


# ============================================================================
# LIVE EVENTS ANALYTICS
# ============================================================================

def get_live_events_analytics(
    period: str = 'monthly',
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get analytics for running/live events.
    
    Running event = status='published' AND start_time <= now <= end_time
    
    Args:
        period: 'weekly', 'monthly', or 'yearly'
        limit: Maximum number of events to return (default: 50, max: 500)
        offset: Number of events to skip (default: 0)
    
    Returns:
        Dict with live events metrics
    """
    now = timezone.now()
    
    trunc_func = {
        'weekly': TruncWeek,
        'monthly': TruncMonth,
        'yearly': TruncYear,
    }.get(period, TruncMonth)
    
    # Current running events
    running_events = Event.objects.filter(
        status='published',
        start_time__lte=now,
        end_time__gte=now
    ).select_related('host', 'venue').prefetch_related(
        'attendance_records',
        'payment_orders'
    )
    
    total_running = running_events.count()
    
    # Apply pagination
    limit = min(limit, 500)  # Cap at 500
    paginated_events = running_events[offset:offset + limit]
    
    # For each running event, get attendees and revenue
    events_detail = []
    for event in paginated_events:
        attendees_count = event.attendance_records.filter(status='going').count()
        
        # Revenue from completed payments
        revenue = PaymentOrder.objects.filter(
            event=event,
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        events_detail.append({
            'event_id': event.id,
            'title': event.title,
            'host': event.host.name or event.host.user.username,  # Match spec field name
            'venue': event.venue.name if event.venue else event.venue_text,
            'start_time': event.start_time.isoformat(),
            'end_time': event.end_time.isoformat(),
            'attendees': attendees_count,  # Match spec field name
            'revenue': float(revenue),
        })
    
    # Time-series: number of active events over time
    # This is tricky - we need to count events that were running at each period
    # For simplicity, we'll count events that started in each period
    active_events_trend = (
        Event.objects
        .filter(
            status='published',
            start_time__lte=now,
            end_time__gte=now
        )
        .annotate(period=trunc_func('start_time'))
        .values('period')
        .annotate(count=Count('id'))
        .order_by('period')
    )
    
    trend_data = [
        {
            'period': str(item['period']),
            'count': item['count'],
        }
        for item in active_events_trend
    ]
    
    return {
        'running_events': total_running,  # Match spec field name
        'events': events_detail,  # Match spec field name
        'trend': trend_data,
        'pagination': {
            'limit': limit,
            'offset': offset,
            'total': total_running,
            'has_more': (offset + limit) < total_running,
        },
    }


# ============================================================================
# COMPLETED EVENTS ANALYTICS
# ============================================================================

def get_completed_events_analytics(
    paid_only: bool = False,
    free_only: bool = False,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get analytics for completed events.
    
    Completed = status='completed'
    
    Args:
        paid_only: Filter to only paid events
        free_only: Filter to only free events
        limit: Maximum number of events to return (default: 50, max: 500)
        offset: Number of events to skip (default: 0)
    
    Returns:
        Dict with completed events metrics
    """
    # Base queryset
    completed_events = Event.objects.filter(
        status='completed'
    ).select_related('host', 'venue').prefetch_related(
        'attendance_records__user',
        'payment_orders',
        'payout_requests'
    )
    
    # Apply filters
    if paid_only:
        completed_events = completed_events.filter(is_paid=True)
    elif free_only:
        completed_events = completed_events.filter(is_paid=False)
    
    # Get total count before pagination
    total_completed = completed_events.count()
    
    # Apply pagination
    limit = min(limit, 500)  # Cap at 500
    paginated_events = completed_events[offset:offset + limit]
    
    events_detail = []
    
    for event in paginated_events:
        # Get attendees
        attendees = event.attendance_records.filter(status='going').select_related('user')
        attendees_list = [
            {
                'name': att.user.name or att.user.user.username,
                'phone': att.user.phone_number,
                'seats': att.seats,
                'checked_in': att.status == 'checked_in',
            }
            for att in attendees
        ]
        
        # Seats filled
        seats_filled = sum(att.seats for att in attendees)
        
        # Revenue from completed payments
        completed_payments = event.payment_orders.filter(status='completed')
        total_revenue = completed_payments.aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Get payout request if exists
        payout_request = event.payout_requests.first()
        
        if payout_request:
            base_fare = float(payout_request.base_ticket_fare)
            platform_fee = float(payout_request.platform_fee_amount)
            gross_revenue = float(payout_request.final_ticket_fare * payout_request.total_tickets_sold)
            host_earnings = float(payout_request.final_earning)
            payout_status = payout_request.status
        else:
            # Calculate from payment orders if no payout request
            base_fare = float(event.ticket_price) if event.is_paid else 0.0
            platform_fee = float(total_revenue * Decimal('0.10'))  # 10% platform fee
            gross_revenue = float(total_revenue)
            host_earnings = float(total_revenue - platform_fee)
            payout_status = 'no_request'
        
        # Attendance conversion rate
        total_requests = event.requests_count
        approved_requests = event.going_count
        attendance_conversion = (approved_requests / total_requests * 100) if total_requests > 0 else 0
        
        # No-show rate
        going_count = event.going_count
        checked_in_count = event.attendance_records.filter(status='checked_in').count()
        no_show_rate = ((going_count - checked_in_count) / going_count * 100) if going_count > 0 else 0
        
        events_detail.append({
            'event_id': event.id,
            'title': event.title,
            'host': event.host.name or event.host.user.username,  # Match spec field name
            'event_date': event.start_time.isoformat(),
            'venue': event.venue.name if event.venue else event.venue_text,
            'is_paid': event.is_paid,
            'attendees': attendees_list,
            'attendees_count': len(attendees_list),  # Add count for convenience
            'seats_filled': seats_filled,
            'base_fare': float(base_fare),  # Ensure Decimal to float
            'platform_fee': float(platform_fee),
            'revenue': float(gross_revenue),  # Match spec field name
            'host_earning': float(host_earnings),  # Match spec field name
            'payout_status': payout_status,
            'conversion_rate': round(attendance_conversion / 100, 4),  # Convert to decimal
            'conversion_rate_display': round(attendance_conversion, 2),  # For display as percentage
            'no_show_rate': round(no_show_rate / 100, 4),  # Convert to decimal
            'no_show_rate_display': round(no_show_rate, 2),  # For display as percentage
        })
    
    return {
        'completed_events': events_detail,  # Match spec field name
        'pagination': {
            'limit': limit,
            'offset': offset,
            'total': total_completed,
            'has_more': (offset + limit) < total_completed,
        },
    }


# ============================================================================
# HOST-LEVEL DEEP ANALYTICS
# ============================================================================

def get_host_deep_analytics(
    host_id: Optional[int] = None,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    """
    Get deep analytics for a specific host or all hosts.
    
    Args:
        host_id: Optional UserProfile ID to filter to one host
        limit: Maximum number of hosts to return (default: 50, max: 500)
        offset: Number of hosts to skip (default: 0)
    
    Returns:
        Dict with host-level analytics
    """
    from users.models import UserProfile
    
    if host_id:
        hosts_qs = UserProfile.objects.filter(id=host_id)
    else:
        # Get all hosts (users who have created at least one event)
        hosts_qs = UserProfile.objects.filter(
            hosted_events__isnull=False
        ).distinct()
    
    # Get total count before pagination
    total_hosts_count = hosts_qs.count()
    
    # Apply pagination (only if not filtering by host_id)
    if not host_id:
        limit = min(limit, 500)  # Cap at 500
        hosts_qs = hosts_qs[offset:offset + limit]
    
    hosts_analytics = []
    
    for host in hosts_qs.select_related('user').prefetch_related(
        'hosted_events',
        'hosted_events__attendance_records',
        'hosted_events__payment_orders',
        'hosted_events__payout_requests'
    ):
        events = host.hosted_events.all()
        
        # Event summary by status
        event_summary = {
            'draft': events.filter(status='draft').count(),
            'published': events.filter(status='published').count(),
            'cancelled': events.filter(status='cancelled').count(),
            'completed': events.filter(status='completed').count(),
        }
        total_events = events.count()
        
        # Performance metrics for each event
        events_performance = []
        total_lifetime_revenue = Decimal('0.00')
        total_platform_fees = Decimal('0.00')
        
        for event in events:
            # Seats sold
            seats_sold = event.attendance_records.filter(status='going').aggregate(
                total=Sum('seats')
            )['total'] or 0
            
            # Revenue
            event_revenue = event.payment_orders.filter(status='completed').aggregate(
                total=Sum('amount')
            )['total'] or Decimal('0.00')
            
            total_lifetime_revenue += event_revenue
            
            # Payment success rate
            total_payments = event.payment_orders.count()
            successful_payments = event.payment_orders.filter(status='completed').count()
            payment_success_rate = (successful_payments / total_payments * 100) if total_payments > 0 else 0
            
            # Attendance check-in rate
            going_count = event.going_count
            checked_in_count = event.attendance_records.filter(status='checked_in').count()
            check_in_rate = (checked_in_count / going_count * 100) if going_count > 0 else 0
            
            # Platform fee (10% of revenue)
            platform_fee = event_revenue * Decimal('0.10')
            total_platform_fees += platform_fee
            
            events_performance.append({
                'event_id': event.id,
                'title': event.title,
                'status': event.status,
                'seats_sold': seats_sold,
                'revenue': float(event_revenue),
                'payment_success_rate': round(payment_success_rate, 2),
                'check_in_rate': round(check_in_rate, 2),
            })
        
        # Financial KPIs from payout requests
        payout_requests = HostPayoutRequest.objects.filter(
            event__host=host
        ).select_related('event')
        
        total_earnings = payout_requests.aggregate(
            total=Sum('final_earning')
        )['total'] or Decimal('0.00')
        
        total_platform_fees_from_payouts = payout_requests.aggregate(
            total=Sum('platform_fee_amount')
        )['total'] or Decimal('0.00')
        
        payout_statuses = payout_requests.values('status').annotate(
            count=Count('id')
        )
        
        payout_status_summary = {item['status']: item['count'] for item in payout_statuses}
        
        # Average earning per event
        completed_events_count = events.filter(status='completed').count()
        avg_earning_per_event = (
            float(total_earnings / completed_events_count)
            if completed_events_count > 0 else 0.0
        )
        
        # Host engagement score (composite metric)
        # Formula: score = (events*0.4) + (attendance_rate*0.3) + (revenue_factor*0.3)
        # Normalize to 0-100 scale
        
        # Events factor (0-40 points): normalize events count (assume 20 events = max)
        events_factor = min((total_events / 20.0) * 40, 40) if total_events > 0 else 0
        
        # Attendance rate factor (0-30 points): average check-in rate across completed events
        completed_events_list = events.filter(status='completed')
        if completed_events_list.exists():
            attendance_rates = []
            for event in completed_events_list:
                going_count = event.going_count
                if going_count > 0:
                    checked_in = event.attendance_records.filter(status='checked_in').count()
                    attendance_rates.append((checked_in / going_count) * 100)
            avg_attendance_rate = sum(attendance_rates) / len(attendance_rates) if attendance_rates else 0
        else:
            avg_attendance_rate = 0
        attendance_rate_factor = (avg_attendance_rate / 100.0) * 30  # 0-30 points
        
        # Revenue factor (0-30 points): normalize revenue (assume ₹100,000 = max)
        revenue_factor = min((float(total_lifetime_revenue) / 100000.0) * 30, 30) if total_lifetime_revenue > 0 else 0
        
        engagement_score = round(events_factor + attendance_rate_factor + revenue_factor, 2)
        
        hosts_analytics.append({
            'host_id': host.id,
            'name': host.name or host.user.username,  # Match spec field name
            'events_hosted': total_events,  # Match spec field name
            'breakdown': event_summary,  # Match spec field name
            'lifetime_revenue': float(total_lifetime_revenue),  # Match spec field name
            'lifetime_earnings': float(total_earnings),  # Match spec field name
            'platform_fees': float(total_platform_fees_from_payouts),  # Match spec field name
            'events_performance': events_performance,
            'payout_requests_count': payout_requests.count(),
            'payout_status_summary': payout_status_summary,
            'engagement_score': engagement_score,
        })
    
    return {
        'hosts': hosts_analytics,
        'total_hosts_analyzed': len(hosts_analytics),
        'pagination': {
            'limit': limit if not host_id else 1,
            'offset': offset if not host_id else 0,
            'total': total_hosts_count,
            'has_more': (offset + limit) < total_hosts_count if not host_id else False,
        },
    }

