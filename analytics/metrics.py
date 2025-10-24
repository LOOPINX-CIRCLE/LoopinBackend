"""
KPI/KRI/KR computation system for business intelligence.

This module provides automated computation of key performance indicators,
key risk indicators, and key results for comprehensive business analytics.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from django.utils import timezone
from django.db.models import Count, Sum, Avg, Q, F
from django.contrib.auth.models import User
from django.db import transaction

from .models import BusinessMetric, UserEvent, SystemLog, AIInsight
from events.models import Event, EventRequest, AttendanceRecord
from users.models import UserProfile, PhoneOTP
from payments.models import PaymentOrder, PaymentTransaction

logger = logging.getLogger(__name__)


class KPICalculator:
    """Calculator for Key Performance Indicators"""
    
    @staticmethod
    def calculate_daily_active_users(date: datetime.date) -> Dict[str, Any]:
        """Calculate Daily Active Users (DAU)"""
        try:
            dau = UserEvent.objects.filter(
                created_at__date=date,
                user__isnull=False
            ).values('user').distinct().count()
            
            # Store metric
            BusinessMetric.objects.update_or_create(
                metric_name='daily_active_users',
                period_start=timezone.datetime.combine(date, timezone.datetime.min.time()),
                period_end=timezone.datetime.combine(date, timezone.datetime.max.time()),
                period_type='day',
                defaults={
                    'metric_type': 'kpi',
                    'metric_category': 'engagement',
                    'value': dau,
                    'context': {'date': date.isoformat()}
                }
            )
            
            return {'dau': dau, 'date': date.isoformat()}
            
        except Exception as e:
            logger.error(f"Failed to calculate DAU: {e}")
            return {'dau': 0, 'error': str(e)}
    
    @staticmethod
    def calculate_retention_rate(days: int = 7) -> Dict[str, Any]:
        """Calculate retention rate for specified days"""
        try:
            end_date = timezone.now().date()
            start_date = end_date - timedelta(days=days)
            
            # Users who were active in the period
            active_users = UserEvent.objects.filter(
                created_at__date__range=[start_date, end_date],
                user__isnull=False
            ).values('user').distinct()
            
            # Users who were active in the previous period
            prev_start = start_date - timedelta(days=days)
            prev_end = start_date
            prev_active_users = UserEvent.objects.filter(
                created_at__date__range=[prev_start, prev_end],
                user__isnull=False
            ).values('user').distinct()
            
            # Calculate retention
            active_user_ids = set(user['user'] for user in active_users)
            prev_active_user_ids = set(user['user'] for user in prev_active_users)
            
            retained_users = active_user_ids.intersection(prev_active_user_ids)
            retention_rate = len(retained_users) / len(prev_active_user_ids) if prev_active_user_ids else 0
            
            # Store metric
            BusinessMetric.objects.update_or_create(
                metric_name=f'retention_rate_{days}d',
                period_start=timezone.datetime.combine(start_date, timezone.datetime.min.time()),
                period_end=timezone.datetime.combine(end_date, timezone.datetime.max.time()),
                period_type='day',
                defaults={
                    'metric_type': 'kpi',
                    'metric_category': 'engagement',
                    'value': retention_rate * 100,  # Store as percentage
                    'context': {
                        'days': days,
                        'retained_users': len(retained_users),
                        'prev_active_users': len(prev_active_user_ids)
                    }
                }
            )
            
            return {
                'retention_rate': retention_rate,
                'retained_users': len(retained_users),
                'prev_active_users': len(prev_active_user_ids),
                'days': days
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate retention rate: {e}")
            return {'retention_rate': 0, 'error': str(e)}
    
    @staticmethod
    def calculate_avg_session_length(date: datetime.date) -> Dict[str, Any]:
        """Calculate average session length"""
        try:
            # Get all sessions for the date
            sessions = UserEvent.objects.filter(
                created_at__date=date
            ).values('session_id').annotate(
                session_start=timezone.datetime.min,
                session_end=timezone.datetime.max,
                event_count=Count('id')
            ).filter(event_count__gt=1)  # Only sessions with multiple events
            
            if not sessions.exists():
                return {'avg_session_length_minutes': 0, 'total_sessions': 0}
            
            # Calculate session lengths
            session_lengths = []
            for session in sessions:
                session_events = UserEvent.objects.filter(
                    session_id=session['session_id'],
                    created_at__date=date
                ).order_by('created_at')
                
                if session_events.count() > 1:
                    start_time = session_events.first().created_at
                    end_time = session_events.last().created_at
                    length_minutes = (end_time - start_time).total_seconds() / 60
                    session_lengths.append(length_minutes)
            
            avg_length = sum(session_lengths) / len(session_lengths) if session_lengths else 0
            
            # Store metric
            BusinessMetric.objects.update_or_create(
                metric_name='avg_session_length_minutes',
                period_start=timezone.datetime.combine(date, timezone.datetime.min.time()),
                period_end=timezone.datetime.combine(date, timezone.datetime.max.time()),
                period_type='day',
                defaults={
                    'metric_type': 'kpi',
                    'metric_category': 'engagement',
                    'value': avg_length,
                    'context': {
                        'total_sessions': len(session_lengths),
                        'date': date.isoformat()
                    }
                }
            )
            
            return {
                'avg_session_length_minutes': avg_length,
                'total_sessions': len(session_lengths)
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate avg session length: {e}")
            return {'avg_session_length_minutes': 0, 'error': str(e)}
    
    @staticmethod
    def calculate_conversion_rate(date: datetime.date) -> Dict[str, Any]:
        """Calculate conversion rate (view → join → attend)"""
        try:
            # Get events for the date
            events = Event.objects.filter(created_at__date=date)
            
            total_views = 0
            total_requests = 0
            total_attendances = 0
            
            for event in events:
                # Count views (page views for event)
                views = UserEvent.objects.filter(
                    created_at__date=date,
                    event_name__contains=f'event_{event.id}',
                    event_type='page_view'
                ).count()
                total_views += views
                
                # Count requests
                requests = EventRequest.objects.filter(
                    event=event,
                    created_at__date=date
                ).count()
                total_requests += requests
                
                # Count attendances
                attendances = AttendanceRecord.objects.filter(
                    event=event,
                    created_at__date=date
                ).count()
                total_attendances += attendances
            
            # Calculate conversion rates
            view_to_request_rate = (total_requests / total_views * 100) if total_views > 0 else 0
            request_to_attendance_rate = (total_attendances / total_requests * 100) if total_requests > 0 else 0
            overall_conversion_rate = (total_attendances / total_views * 100) if total_views > 0 else 0
            
            # Store metrics
            metrics_data = [
                ('view_to_request_rate', view_to_request_rate),
                ('request_to_attendance_rate', request_to_attendance_rate),
                ('overall_conversion_rate', overall_conversion_rate)
            ]
            
            for metric_name, value in metrics_data:
                BusinessMetric.objects.update_or_create(
                    metric_name=metric_name,
                    period_start=timezone.datetime.combine(date, timezone.datetime.min.time()),
                    period_end=timezone.datetime.combine(date, timezone.datetime.max.time()),
                    period_type='day',
                    defaults={
                        'metric_type': 'kpi',
                        'metric_category': 'conversion',
                        'value': value,
                        'context': {
                            'total_views': total_views,
                            'total_requests': total_requests,
                            'total_attendances': total_attendances,
                            'date': date.isoformat()
                        }
                    }
                )
            
            return {
                'view_to_request_rate': view_to_request_rate,
                'request_to_attendance_rate': request_to_attendance_rate,
                'overall_conversion_rate': overall_conversion_rate,
                'total_views': total_views,
                'total_requests': total_requests,
                'total_attendances': total_attendances
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate conversion rate: {e}")
            return {'conversion_rate': 0, 'error': str(e)}
    
    @staticmethod
    def calculate_revenue_per_user(date: datetime.date) -> Dict[str, Any]:
        """Calculate Revenue Per User (RPU)"""
        try:
            # Get revenue for the date
            revenue = PaymentOrder.objects.filter(
                created_at__date=date,
                status='completed'
            ).aggregate(total_revenue=Sum('amount'))['total_revenue'] or 0
            
            # Get active users for the date
            active_users = UserEvent.objects.filter(
                created_at__date=date,
                user__isnull=False
            ).values('user').distinct().count()
            
            rpu = float(revenue) / active_users if active_users > 0 else 0
            
            # Store metric
            BusinessMetric.objects.update_or_create(
                metric_name='revenue_per_user',
                period_start=timezone.datetime.combine(date, timezone.datetime.min.time()),
                period_end=timezone.datetime.combine(date, timezone.datetime.max.time()),
                period_type='day',
                defaults={
                    'metric_type': 'kpi',
                    'metric_category': 'revenue',
                    'value': rpu,
                    'context': {
                        'total_revenue': float(revenue),
                        'active_users': active_users,
                        'date': date.isoformat()
                    }
                }
            )
            
            return {
                'revenue_per_user': rpu,
                'total_revenue': float(revenue),
                'active_users': active_users
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate RPU: {e}")
            return {'revenue_per_user': 0, 'error': str(e)}


class KRICalculator:
    """Calculator for Key Risk Indicators"""
    
    @staticmethod
    def calculate_payment_failure_rate(date: datetime.date) -> Dict[str, Any]:
        """Calculate payment failure spike rate"""
        try:
            # Get payment data for the date
            payments = PaymentOrder.objects.filter(created_at__date=date)
            
            total_payments = payments.count()
            failed_payments = payments.filter(status='failed').count()
            
            failure_rate = (failed_payments / total_payments * 100) if total_payments > 0 else 0
            
            # Store metric
            BusinessMetric.objects.update_or_create(
                metric_name='payment_failure_rate',
                period_start=timezone.datetime.combine(date, timezone.datetime.min.time()),
                period_end=timezone.datetime.combine(date, timezone.datetime.max.time()),
                period_type='day',
                defaults={
                    'metric_type': 'kri',
                    'metric_category': 'payment',
                    'value': failure_rate,
                    'warning_threshold': 10.0,  # 10% failure rate warning
                    'critical_threshold': 20.0,  # 20% failure rate critical
                    'context': {
                        'total_payments': total_payments,
                        'failed_payments': failed_payments,
                        'date': date.isoformat()
                    }
                }
            )
            
            return {
                'payment_failure_rate': failure_rate,
                'total_payments': total_payments,
                'failed_payments': failed_payments
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate payment failure rate: {e}")
            return {'payment_failure_rate': 0, 'error': str(e)}
    
    @staticmethod
    def calculate_otp_verification_failure_rate(date: datetime.date) -> Dict[str, Any]:
        """Calculate OTP verification failure rate"""
        try:
            # Get OTP data for the date
            otps = PhoneOTP.objects.filter(created_at__date=date)
            
            total_otps = otps.count()
            failed_otps = otps.filter(status='failed').count()
            
            failure_rate = (failed_otps / total_otps * 100) if total_otps > 0 else 0
            
            # Store metric
            BusinessMetric.objects.update_or_create(
                metric_name='otp_verification_failure_rate',
                period_start=timezone.datetime.combine(date, timezone.datetime.min.time()),
                period_end=timezone.datetime.combine(date, timezone.datetime.max.time()),
                period_type='day',
                defaults={
                    'metric_type': 'kri',
                    'metric_category': 'authentication',
                    'value': failure_rate,
                    'warning_threshold': 15.0,  # 15% failure rate warning
                    'critical_threshold': 25.0,  # 25% failure rate critical
                    'context': {
                        'total_otps': total_otps,
                        'failed_otps': failed_otps,
                        'date': date.isoformat()
                    }
                }
            )
            
            return {
                'otp_verification_failure_rate': failure_rate,
                'total_otps': total_otps,
                'failed_otps': failed_otps
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate OTP failure rate: {e}")
            return {'otp_verification_failure_rate': 0, 'error': str(e)}
    
    @staticmethod
    def calculate_host_cancellation_rate(date: datetime.date) -> Dict[str, Any]:
        """Calculate host cancellation frequency"""
        try:
            # Get events for the date
            events = Event.objects.filter(created_at__date=date)
            
            total_events = events.count()
            cancelled_events = events.filter(status='cancelled').count()
            
            cancellation_rate = (cancelled_events / total_events * 100) if total_events > 0 else 0
            
            # Store metric
            BusinessMetric.objects.update_or_create(
                metric_name='host_cancellation_rate',
                period_start=timezone.datetime.combine(date, timezone.datetime.min.time()),
                period_end=timezone.datetime.combine(date, timezone.datetime.max.time()),
                period_type='day',
                defaults={
                    'metric_type': 'kri',
                    'metric_category': 'events',
                    'value': cancellation_rate,
                    'warning_threshold': 5.0,  # 5% cancellation rate warning
                    'critical_threshold': 10.0,  # 10% cancellation rate critical
                    'context': {
                        'total_events': total_events,
                        'cancelled_events': cancelled_events,
                        'date': date.isoformat()
                    }
                }
            )
            
            return {
                'host_cancellation_rate': cancellation_rate,
                'total_events': total_events,
                'cancelled_events': cancelled_events
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate host cancellation rate: {e}")
            return {'host_cancellation_rate': 0, 'error': str(e)}
    
    @staticmethod
    def calculate_high_churn_probability(date: datetime.date) -> Dict[str, Any]:
        """Calculate percentage of users with high churn probability"""
        try:
            # Get AI insights for churn risk
            churn_insights = AIInsight.objects.filter(
                insight_type='churn_risk',
                created_at__date=date,
                confidence_score__gte=0.7
            )
            
            high_churn_users = churn_insights.filter(
                output_data__churn_probability__gte=0.7
            ).count()
            
            total_users = User.objects.filter(is_active=True).count()
            
            high_churn_percentage = (high_churn_users / total_users * 100) if total_users > 0 else 0
            
            # Store metric
            BusinessMetric.objects.update_or_create(
                metric_name='high_churn_probability_rate',
                period_start=timezone.datetime.combine(date, timezone.datetime.min.time()),
                period_end=timezone.datetime.combine(date, timezone.datetime.max.time()),
                period_type='day',
                defaults={
                    'metric_type': 'kri',
                    'metric_category': 'retention',
                    'value': high_churn_percentage,
                    'warning_threshold': 10.0,  # 10% high churn warning
                    'critical_threshold': 20.0,  # 20% high churn critical
                    'context': {
                        'high_churn_users': high_churn_users,
                        'total_users': total_users,
                        'date': date.isoformat()
                    }
                }
            )
            
            return {
                'high_churn_probability_rate': high_churn_percentage,
                'high_churn_users': high_churn_users,
                'total_users': total_users
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate high churn probability: {e}")
            return {'high_churn_probability_rate': 0, 'error': str(e)}


class KRCalculator:
    """Calculator for Key Results"""
    
    @staticmethod
    def calculate_monthly_event_creation_growth() -> Dict[str, Any]:
        """Calculate monthly event creation growth"""
        try:
            current_month = timezone.now().replace(day=1)
            previous_month = (current_month - timedelta(days=1)).replace(day=1)
            
            # Get event counts
            current_events = Event.objects.filter(
                created_at__gte=current_month
            ).count()
            
            previous_events = Event.objects.filter(
                created_at__gte=previous_month,
                created_at__lt=current_month
            ).count()
            
            growth_rate = ((current_events - previous_events) / previous_events * 100) if previous_events > 0 else 0
            
            # Store metric
            BusinessMetric.objects.update_or_create(
                metric_name='monthly_event_creation_growth',
                period_start=current_month,
                period_end=timezone.now(),
                period_type='month',
                defaults={
                    'metric_type': 'kr',
                    'metric_category': 'growth',
                    'value': growth_rate,
                    'context': {
                        'current_month_events': current_events,
                        'previous_month_events': previous_events,
                        'current_month': current_month.isoformat(),
                        'previous_month': previous_month.isoformat()
                    }
                }
            )
            
            return {
                'monthly_event_creation_growth': growth_rate,
                'current_month_events': current_events,
                'previous_month_events': previous_events
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate monthly event creation growth: {e}")
            return {'monthly_event_creation_growth': 0, 'error': str(e)}
    
    @staticmethod
    def calculate_ticket_purchase_success_ratio(date: datetime.date) -> Dict[str, Any]:
        """Calculate ticket purchase success ratio"""
        try:
            # Get payment data for the date
            payments = PaymentOrder.objects.filter(created_at__date=date)
            
            total_attempts = payments.count()
            successful_purchases = payments.filter(status='completed').count()
            
            success_ratio = (successful_purchases / total_attempts * 100) if total_attempts > 0 else 0
            
            # Store metric
            BusinessMetric.objects.update_or_create(
                metric_name='ticket_purchase_success_ratio',
                period_start=timezone.datetime.combine(date, timezone.datetime.min.time()),
                period_end=timezone.datetime.combine(date, timezone.datetime.max.time()),
                period_type='day',
                defaults={
                    'metric_type': 'kr',
                    'metric_category': 'conversion',
                    'value': success_ratio,
                    'context': {
                        'total_attempts': total_attempts,
                        'successful_purchases': successful_purchases,
                        'date': date.isoformat()
                    }
                }
            )
            
            return {
                'ticket_purchase_success_ratio': success_ratio,
                'total_attempts': total_attempts,
                'successful_purchases': successful_purchases
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate ticket purchase success ratio: {e}")
            return {'ticket_purchase_success_ratio': 0, 'error': str(e)}
    
    @staticmethod
    def calculate_user_verification_completion_rate(date: datetime.date) -> Dict[str, Any]:
        """Calculate user verification completion percentage"""
        try:
            # Get user profiles
            total_profiles = UserProfile.objects.filter(created_at__date=date).count()
            verified_profiles = UserProfile.objects.filter(
                created_at__date=date,
                is_verified=True
            ).count()
            
            completion_rate = (verified_profiles / total_profiles * 100) if total_profiles > 0 else 0
            
            # Store metric
            BusinessMetric.objects.update_or_create(
                metric_name='user_verification_completion_rate',
                period_start=timezone.datetime.combine(date, timezone.datetime.min.time()),
                period_end=timezone.datetime.combine(date, timezone.datetime.max.time()),
                period_type='day',
                defaults={
                    'metric_type': 'kr',
                    'metric_category': 'onboarding',
                    'value': completion_rate,
                    'context': {
                        'total_profiles': total_profiles,
                        'verified_profiles': verified_profiles,
                        'date': date.isoformat()
                    }
                }
            )
            
            return {
                'user_verification_completion_rate': completion_rate,
                'total_profiles': total_profiles,
                'verified_profiles': verified_profiles
            }
            
        except Exception as e:
            logger.error(f"Failed to calculate user verification completion rate: {e}")
            return {'user_verification_completion_rate': 0, 'error': str(e)}


class MetricsProcessor:
    """Main processor for all KPI/KRI/KR calculations"""
    
    @staticmethod
    def process_daily_metrics(date: datetime.date = None):
        """Process all daily metrics"""
        if date is None:
            date = timezone.now().date()
        
        logger.info(f"Processing daily metrics for {date}")
        
        results = {}
        
        # Process KPIs
        results['kpis'] = {
            'dau': KPICalculator.calculate_daily_active_users(date),
            'retention_7d': KPICalculator.calculate_retention_rate(7),
            'retention_30d': KPICalculator.calculate_retention_rate(30),
            'avg_session_length': KPICalculator.calculate_avg_session_length(date),
            'conversion_rate': KPICalculator.calculate_conversion_rate(date),
            'revenue_per_user': KPICalculator.calculate_revenue_per_user(date)
        }
        
        # Process KRIs
        results['kris'] = {
            'payment_failure_rate': KRICalculator.calculate_payment_failure_rate(date),
            'otp_verification_failure_rate': KRICalculator.calculate_otp_verification_failure_rate(date),
            'host_cancellation_rate': KRICalculator.calculate_host_cancellation_rate(date),
            'high_churn_probability': KRICalculator.calculate_high_churn_probability(date)
        }
        
        # Process KRs
        results['krs'] = {
            'monthly_event_creation_growth': KRCalculator.calculate_monthly_event_creation_growth(),
            'ticket_purchase_success_ratio': KRCalculator.calculate_ticket_purchase_success_ratio(date),
            'user_verification_completion_rate': KRCalculator.calculate_user_verification_completion_rate(date)
        }
        
        logger.info(f"Completed processing daily metrics for {date}")
        return results
    
    @staticmethod
    def check_alert_thresholds():
        """Check if any metrics exceed alert thresholds"""
        alerts = []
        
        # Get recent metrics with thresholds
        recent_metrics = BusinessMetric.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=24),
            warning_threshold__isnull=False
        )
        
        for metric in recent_metrics:
            if metric.warning_threshold and metric.value >= metric.warning_threshold:
                alert_level = 'critical' if metric.critical_threshold and metric.value >= metric.critical_threshold else 'warning'
                
                alerts.append({
                    'metric_name': metric.metric_name,
                    'current_value': float(metric.value),
                    'threshold': float(metric.warning_threshold),
                    'alert_level': alert_level,
                    'timestamp': metric.created_at.isoformat()
                })
                
                # Mark metric as alert triggered
                metric.is_alert_triggered = True
                metric.save(update_fields=['is_alert_triggered'])
        
        return alerts
