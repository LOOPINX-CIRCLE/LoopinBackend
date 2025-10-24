"""
Analytics views for API endpoints

Provides analytics data through REST API endpoints for dashboards and reporting.
"""

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from typing import Dict, Any

from .models import (
    DailyEventMetrics, UserEngagementMetrics, EventCategoryMetrics,
    VenueMetrics, ConversionFunnelMetrics, RevenueMetrics, UserSegmentMetrics
)
from events.models import Event, EventRequest, AttendanceRecord
from users.models import UserProfile, EventInterest
from payments.models import PaymentOrder


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def analytics_overview(request):
    """Get analytics overview for the current user"""
    try:
        user = request.user
        
        # Get user-specific metrics
        user_metrics = {
            'events_requested': EventRequest.objects.filter(requester=user).count(),
            'events_attended': AttendanceRecord.objects.filter(user=user).count(),
            'events_hosted': Event.objects.filter(host=user).count(),
            'total_payments': PaymentOrder.objects.filter(user=user).count(),
            'successful_payments': PaymentOrder.objects.filter(user=user, status='completed').count(),
        }
        
        # Calculate conversion rates
        if user_metrics['events_requested'] > 0:
            user_metrics['request_to_attendance_rate'] = (
                user_metrics['events_attended'] / user_metrics['events_requested'] * 100
            )
        else:
            user_metrics['request_to_attendance_rate'] = 0
            
        if user_metrics['total_payments'] > 0:
            user_metrics['payment_success_rate'] = (
                user_metrics['successful_payments'] / user_metrics['total_payments'] * 100
            )
        else:
            user_metrics['payment_success_rate'] = 0
        
        return Response({
            'success': True,
            'data': user_metrics
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def admin_analytics_overview(request):
    """Get comprehensive analytics overview for admin users"""
    try:
        # Get date range from query parameters
        days = int(request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Overall metrics
        overview = {
            'total_users': UserProfile.objects.filter(created_at__date__range=[start_date, end_date]).count(),
            'total_events': Event.objects.filter(created_at__date__range=[start_date, end_date]).count(),
            'total_requests': EventRequest.objects.filter(created_at__date__range=[start_date, end_date]).count(),
            'total_attendees': AttendanceRecord.objects.filter(created_at__date__range=[start_date, end_date]).count(),
            'total_revenue': sum(
                float(p.amount) for p in PaymentOrder.objects.filter(
                    created_at__date__range=[start_date, end_date],
                    status='completed'
                )
            ),
        }
        
        # Conversion funnel
        funnel = {
            'users_registered': overview['total_users'],
            'events_created': overview['total_events'],
            'requests_made': overview['total_requests'],
            'attendances': overview['total_attendees'],
        }
        
        # Calculate conversion rates
        if funnel['users_registered'] > 0:
            funnel['event_creation_rate'] = (funnel['events_created'] / funnel['users_registered'] * 100)
        else:
            funnel['event_creation_rate'] = 0
            
        if funnel['events_created'] > 0:
            funnel['request_rate'] = (funnel['requests_made'] / funnel['events_created'] * 100)
        else:
            funnel['request_rate'] = 0
            
        if funnel['requests_made'] > 0:
            funnel['attendance_rate'] = (funnel['attendances'] / funnel['requests_made'] * 100)
        else:
            funnel['attendance_rate'] = 0
        
        return Response({
            'success': True,
            'data': {
                'overview': overview,
                'funnel': funnel,
                'date_range': {
                    'start_date': start_date.isoformat(),
                    'end_date': end_date.isoformat(),
                    'days': days
                }
            }
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def event_category_analytics(request):
    """Get analytics by event category/interest"""
    try:
        days = int(request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get metrics by event interest
        interests = EventInterest.objects.filter(is_active=True)
        category_metrics = []
        
        for interest in interests:
            # Get events with this interest
            events = Event.objects.filter(
                created_at__date__range=[start_date, end_date],
                attendees__user__profile__event_interests=interest
            ).distinct()
            
            metrics = {
                'interest_name': interest.name,
                'total_events': events.count(),
                'total_requests': EventRequest.objects.filter(
                    event__in=events
                ).count(),
                'total_attendees': AttendanceRecord.objects.filter(
                    event__in=events
                ).count(),
                'total_revenue': sum(
                    float(p.amount) for p in PaymentOrder.objects.filter(
                        event__in=events,
                        status='completed'
                    )
                ),
            }
            
            # Calculate rates
            if metrics['total_requests'] > 0:
                metrics['attendance_rate'] = (metrics['total_attendees'] / metrics['total_requests'] * 100)
            else:
                metrics['attendance_rate'] = 0
                
            category_metrics.append(metrics)
        
        return Response({
            'success': True,
            'data': category_metrics
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def revenue_analytics(request):
    """Get revenue analytics"""
    try:
        days = int(request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get payment data
        payments = PaymentOrder.objects.filter(
            created_at__date__range=[start_date, end_date]
        )
        
        revenue_metrics = {
            'total_revenue': sum(float(p.amount) for p in payments.filter(status='completed')),
            'total_refunds': sum(float(p.refund_amount or 0) for p in payments.filter(status='refunded')),
            'total_transactions': payments.count(),
            'successful_transactions': payments.filter(status='completed').count(),
            'failed_transactions': payments.filter(status='failed').count(),
            'refunded_transactions': payments.filter(status='refunded').count(),
        }
        
        # Calculate rates
        if revenue_metrics['total_transactions'] > 0:
            revenue_metrics['success_rate'] = (
                revenue_metrics['successful_transactions'] / revenue_metrics['total_transactions'] * 100
            )
        else:
            revenue_metrics['success_rate'] = 0
            
        revenue_metrics['net_revenue'] = revenue_metrics['total_revenue'] - revenue_metrics['total_refunds']
        
        if revenue_metrics['successful_transactions'] > 0:
            revenue_metrics['average_transaction_value'] = (
                revenue_metrics['total_revenue'] / revenue_metrics['successful_transactions']
            )
        else:
            revenue_metrics['average_transaction_value'] = 0
        
        return Response({
            'success': True,
            'data': revenue_metrics
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([IsAdminUser])
def user_segment_analytics(request):
    """Get user segment analytics by demographics"""
    try:
        days = int(request.GET.get('days', 30))
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get user segments by gender
        gender_segments = []
        for gender in ['male', 'female', 'other']:
            profiles = UserProfile.objects.filter(
                created_at__date__range=[start_date, end_date],
                gender=gender
            )
            
            users = [p.user for p in profiles]
            
            segment_data = {
                'segment_type': 'gender',
                'segment_value': gender,
                'total_users': profiles.count(),
                'active_users': profiles.filter(is_active=True).count(),
                'events_requested': EventRequest.objects.filter(
                    requester__in=users,
                    created_at__date__range=[start_date, end_date]
                ).count(),
                'events_attended': AttendanceRecord.objects.filter(
                    user__in=users,
                    created_at__date__range=[start_date, end_date]
                ).count(),
                'total_revenue': sum(
                    float(p.amount) for p in PaymentOrder.objects.filter(
                        user__in=users,
                        created_at__date__range=[start_date, end_date],
                        status='completed'
                    )
                ),
            }
            
            gender_segments.append(segment_data)
        
        return Response({
            'success': True,
            'data': gender_segments
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAdminUser])
def run_analytics_aggregation(request):
    """Manually trigger analytics aggregation"""
    try:
        from .tasks import AnalyticsAggregator
        
        # Get date from request or use today
        date_str = request.data.get('date')
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = timezone.now().date()
        
        # Run aggregation
        AnalyticsAggregator.run_daily_aggregation(date)
        
        return Response({
            'success': True,
            'message': f'Analytics aggregation completed for {date}'
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
