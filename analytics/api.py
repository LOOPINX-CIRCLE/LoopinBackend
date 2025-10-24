"""
FastAPI analytics endpoints for comprehensive analytics API.

This module provides REST API endpoints for accessing analytics data,
AI insights, and business intelligence metrics.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.security import HTTPBearer
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field
import logging

from django.contrib.auth.models import User
from django.utils import timezone
from django.db.models import Q, Count, Sum, Avg

from .models import (
    UserEvent, BusinessMetric, AIInsight, SystemLog, 
    UserPersona, UserBehaviorProfile
)
from .ai_services import (
    SentimentAnalysisService, 
    UserBehaviorAnalysisService,
    PredictiveAnalyticsService,
    UserClusteringService
)
from .metrics import MetricsProcessor
from .tasks import (
    process_user_events_batch,
    generate_user_behavior_insights,
    process_daily_metrics_calculation,
    perform_user_clustering,
    generate_predictive_insights,
    detect_anomalies_batch
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analytics", tags=["analytics"])
security = HTTPBearer()


# Pydantic models for API requests/responses

class AnalyticsOverviewResponse(BaseModel):
    """Response model for analytics overview"""
    total_events: int
    total_users: int
    total_revenue: float
    active_users_today: int
    conversion_rate: float
    avg_session_length: float
    top_insights: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]


class UserBehaviorRequest(BaseModel):
    """Request model for user behavior analysis"""
    user_id: int
    days: int = Field(default=30, ge=1, le=365)


class UserBehaviorResponse(BaseModel):
    """Response model for user behavior analysis"""
    user_id: int
    engagement_score: float
    activity_patterns: Dict[str, Any]
    preferences: Dict[str, Any]
    risk_factors: List[str]
    persona_suggestions: List[str]
    predictions: Dict[str, Any]


class MetricsRequest(BaseModel):
    """Request model for metrics calculation"""
    date: Optional[str] = None
    metric_types: List[str] = Field(default=["kpi", "kri", "kr"])


class MetricsResponse(BaseModel):
    """Response model for metrics"""
    date: str
    kpis: Dict[str, Any]
    kris: Dict[str, Any]
    krs: Dict[str, Any]
    alerts_triggered: int


class InsightRequest(BaseModel):
    """Request model for AI insights"""
    insight_types: List[str] = Field(default=["prediction", "recommendation", "anomaly"])
    priority: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=200)


class InsightResponse(BaseModel):
    """Response model for AI insights"""
    insights: List[Dict[str, Any]]
    total_count: int
    has_more: bool


class SentimentAnalysisRequest(BaseModel):
    """Request model for sentiment analysis"""
    text: str = Field(..., min_length=1, max_length=10000)


class SentimentAnalysisResponse(BaseModel):
    """Response model for sentiment analysis"""
    sentiment: str
    score: float
    confidence: float
    details: Dict[str, Any]


# Dependency functions

async def get_current_user(token: str = Depends(security)) -> User:
    """Get current authenticated user"""
    # This would integrate with your JWT authentication
    # For now, return a placeholder
    try:
        # Decode JWT token and get user
        # user = decode_jwt_token(token.credentials)
        # return User.objects.get(id=user['user_id'])
        return User.objects.first()  # Placeholder
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid authentication token")


async def get_admin_user(user: User = Depends(get_current_user)) -> User:
    """Ensure user is admin"""
    if not user.is_staff:
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# Analytics Overview Endpoints

@router.get("/overview", response_model=AnalyticsOverviewResponse)
async def get_analytics_overview(
    user: User = Depends(get_current_user),
    days: int = Query(default=7, ge=1, le=30)
):
    """Get comprehensive analytics overview"""
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        # Get basic metrics
        total_events = UserEvent.objects.filter(
            created_at__date__range=[start_date, end_date]
        ).count()
        
        total_users = User.objects.filter(
            date_joined__date__range=[start_date, end_date]
        ).count()
        
        # Get revenue (simplified)
        from payments.models import PaymentOrder
        total_revenue = PaymentOrder.objects.filter(
            created_at__date__range=[start_date, end_date],
            status='completed'
        ).aggregate(total=Sum('amount'))['total'] or 0
        
        # Get active users today
        active_users_today = UserEvent.objects.filter(
            created_at__date=end_date,
            user__isnull=False
        ).values('user').distinct().count()
        
        # Get conversion rate
        conversion_metric = BusinessMetric.objects.filter(
            metric_name='overall_conversion_rate',
            created_at__date=end_date
        ).first()
        conversion_rate = float(conversion_metric.value) if conversion_metric else 0
        
        # Get average session length
        session_metric = BusinessMetric.objects.filter(
            metric_name='avg_session_length_minutes',
            created_at__date=end_date
        ).first()
        avg_session_length = float(session_metric.value) if session_metric else 0
        
        # Get top insights
        top_insights = AIInsight.objects.filter(
            created_at__date__range=[start_date, end_date],
            priority__in=['high', 'critical']
        ).order_by('-confidence_score')[:5]
        
        insights_data = []
        for insight in top_insights:
            insights_data.append({
                'id': insight.id,
                'type': insight.insight_type,
                'title': insight.title,
                'priority': insight.priority,
                'confidence': insight.confidence_score,
                'is_actionable': insight.is_actionable
            })
        
        # Get alerts
        alerts = BusinessMetric.objects.filter(
            created_at__date__range=[start_date, end_date],
            is_alert_triggered=True
        )
        
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                'metric_name': alert.metric_name,
                'value': float(alert.value),
                'threshold': float(alert.warning_threshold or 0),
                'severity': 'critical' if alert.critical_threshold and alert.value >= alert.critical_threshold else 'warning'
            })
        
        return AnalyticsOverviewResponse(
            total_events=total_events,
            total_users=total_users,
            total_revenue=float(total_revenue),
            active_users_today=active_users_today,
            conversion_rate=conversion_rate,
            avg_session_length=avg_session_length,
            top_insights=insights_data,
            alerts=alerts_data
        )
        
    except Exception as e:
        logger.error(f"Failed to get analytics overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# User Behavior Analysis Endpoints

@router.post("/user-behavior", response_model=UserBehaviorResponse)
async def analyze_user_behavior(
    request: UserBehaviorRequest,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user)
):
    """Analyze user behavior patterns"""
    try:
        target_user = User.objects.get(id=request.user_id)
        
        # Perform behavior analysis
        behavior_service = UserBehaviorAnalysisService()
        analysis = behavior_service.analyze_user_behavior(target_user, request.days)
        
        # Queue background task for detailed insights
        background_tasks.add_task(
            generate_user_behavior_insights,
            request.user_id
        )
        
        return UserBehaviorResponse(
            user_id=request.user_id,
            engagement_score=analysis['engagement_score'],
            activity_patterns=analysis['activity_patterns'],
            preferences=analysis['preferences'],
            risk_factors=analysis['risk_factors'],
            persona_suggestions=analysis['persona_suggestions'],
            predictions=analysis['predictions']
        )
        
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Failed to analyze user behavior: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Metrics Endpoints

@router.post("/metrics/calculate", response_model=MetricsResponse)
async def calculate_metrics(
    request: MetricsRequest,
    background_tasks: BackgroundTasks,
    admin_user: User = Depends(get_admin_user)
):
    """Calculate business metrics"""
    try:
        # Queue background task for metrics calculation
        task = background_tasks.add_task(
            process_daily_metrics_calculation,
            request.date
        )
        
        # For immediate response, get recent metrics
        date = datetime.strptime(request.date, '%Y-%m-%d').date() if request.date else timezone.now().date()
        
        kpis = {}
        kris = {}
        krs = {}
        
        for metric_type in request.metric_types:
            metrics = BusinessMetric.objects.filter(
                metric_type=metric_type,
                created_at__date=date
            )
            
            for metric in metrics:
                metric_data = {
                    'value': float(metric.value),
                    'previous_value': float(metric.previous_value) if metric.previous_value else None,
                    'change_percentage': metric.change_percentage,
                    'context': metric.context
                }
                
                if metric_type == 'kpi':
                    kpis[metric.metric_name] = metric_data
                elif metric_type == 'kri':
                    kris[metric.metric_name] = metric_data
                elif metric_type == 'kr':
                    krs[metric.metric_name] = metric_data
        
        # Get alerts
        alerts_count = BusinessMetric.objects.filter(
            created_at__date=date,
            is_alert_triggered=True
        ).count()
        
        return MetricsResponse(
            date=date.isoformat(),
            kpis=kpis,
            kris=kris,
            krs=krs,
            alerts_triggered=alerts_count
        )
        
    except Exception as e:
        logger.error(f"Failed to calculate metrics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics/{metric_name}")
async def get_metric_history(
    metric_name: str,
    days: int = Query(default=30, ge=1, le=365),
    admin_user: User = Depends(get_admin_user)
):
    """Get historical data for a specific metric"""
    try:
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        metrics = BusinessMetric.objects.filter(
            metric_name=metric_name,
            created_at__date__range=[start_date, end_date]
        ).order_by('created_at')
        
        history = []
        for metric in metrics:
            history.append({
                'date': metric.created_at.date().isoformat(),
                'value': float(metric.value),
                'previous_value': float(metric.previous_value) if metric.previous_value else None,
                'change_percentage': metric.change_percentage,
                'is_alert_triggered': metric.is_alert_triggered
            })
        
        return {
            'metric_name': metric_name,
            'period': f"{start_date.isoformat()} to {end_date.isoformat()}",
            'history': history,
            'total_points': len(history)
        }
        
    except Exception as e:
        logger.error(f"Failed to get metric history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# AI Insights Endpoints

@router.post("/insights", response_model=InsightResponse)
async def get_ai_insights(
    request: InsightRequest,
    user: User = Depends(get_current_user)
):
    """Get AI-generated insights"""
    try:
        query = AIInsight.objects.all()
        
        if request.insight_types:
            query = query.filter(insight_type__in=request.insight_types)
        
        if request.priority:
            query = query.filter(priority=request.priority)
        
        total_count = query.count()
        insights = query.order_by('-created_at')[:request.limit]
        
        insights_data = []
        for insight in insights:
            insights_data.append({
                'id': insight.id,
                'type': insight.insight_type,
                'title': insight.title,
                'description': insight.description,
                'confidence_score': insight.confidence_score,
                'priority': insight.priority,
                'is_actionable': insight.is_actionable,
                'suggested_actions': insight.suggested_actions,
                'created_at': insight.created_at.isoformat(),
                'target_type': insight.target_type,
                'target_id': insight.target_id
            })
        
        return InsightResponse(
            insights=insights_data,
            total_count=total_count,
            has_more=total_count > request.limit
        )
        
    except Exception as e:
        logger.error(f"Failed to get AI insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/insights/generate")
async def generate_insights(
    background_tasks: BackgroundTasks,
    user_id: Optional[int] = None,
    admin_user: User = Depends(get_admin_user)
):
    """Generate new AI insights"""
    try:
        # Queue background tasks
        if user_id:
            background_tasks.add_task(generate_predictive_insights, user_id)
        else:
            background_tasks.add_task(generate_predictive_insights)
            background_tasks.add_task(detect_anomalies_batch)
        
        return {
            'message': 'Insight generation queued',
            'user_id': user_id,
            'tasks_queued': 1 if user_id else 2
        }
        
    except Exception as e:
        logger.error(f"Failed to generate insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Sentiment Analysis Endpoints

@router.post("/sentiment", response_model=SentimentAnalysisResponse)
async def analyze_sentiment(
    request: SentimentAnalysisRequest,
    user: User = Depends(get_current_user)
):
    """Analyze sentiment of text"""
    try:
        sentiment_service = SentimentAnalysisService()
        result = sentiment_service.analyze_text_sentiment(request.text)
        
        return SentimentAnalysisResponse(
            sentiment=result['sentiment'],
            score=result['score'],
            confidence=result['confidence'],
            details=result['details']
        )
        
    except Exception as e:
        logger.error(f"Failed to analyze sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# User Clustering Endpoints

@router.post("/clustering")
async def perform_user_clustering(
    n_clusters: int = Query(default=5, ge=2, le=20),
    background_tasks: BackgroundTasks = None,
    admin_user: User = Depends(get_admin_user)
):
    """Perform user clustering analysis"""
    try:
        # Queue background task
        background_tasks.add_task(perform_user_clustering, n_clusters)
        
        return {
            'message': 'User clustering analysis queued',
            'n_clusters': n_clusters,
            'status': 'processing'
        }
        
    except Exception as e:
        logger.error(f"Failed to perform user clustering: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Event Tracking Endpoints

@router.post("/events/track")
async def track_custom_event(
    event_name: str,
    event_type: str = "custom",
    metadata: Dict[str, Any] = {},
    user: User = Depends(get_current_user)
):
    """Track a custom event"""
    try:
        # Create user event
        event = UserEvent.objects.create(
            user=user,
            event_type=event_type,
            event_name=event_name,
            metadata=metadata,
            source='api'
        )
        
        # Send to PostHog
        import posthog
        posthog.capture(str(user.id), event_name, metadata)
        
        return {
            'event_id': event.id,
            'event_name': event_name,
            'tracked_at': event.created_at.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to track custom event: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# System Health Endpoints

@router.get("/health")
async def analytics_health_check():
    """Check analytics system health"""
    try:
        # Check database connectivity
        recent_events = UserEvent.objects.filter(
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).count()
        
        # Check AI services
        from .ai_services import AIServiceManager
        ai_manager = AIServiceManager()
        ai_status = 'healthy' if ai_manager.openai_client else 'degraded'
        
        # Check PostHog connectivity
        import posthog
        posthog_status = 'healthy' if posthog.api_key else 'disabled'
        
        return {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'components': {
                'database': 'healthy',
                'ai_services': ai_status,
                'posthog': posthog_status,
                'recent_events': recent_events
            }
        }
        
    except Exception as e:
        logger.error(f"Analytics health check failed: {e}")
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': timezone.now().isoformat()
        }


# Data Export Endpoints

@router.get("/export/events")
async def export_events(
    start_date: str,
    end_date: str,
    format: str = Query(default="json", regex="^(json|csv)$"),
    admin_user: User = Depends(get_admin_user)
):
    """Export events data"""
    try:
        start = datetime.strptime(start_date, '%Y-%m-%d').date()
        end = datetime.strptime(end_date, '%Y-%m-%d').date()
        
        events = UserEvent.objects.filter(
            created_at__date__range=[start, end]
        ).order_by('created_at')
        
        if format == 'csv':
            # Generate CSV data
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'id', 'user_id', 'event_name', 'event_type', 'action',
                'created_at', 'sentiment_score', 'engagement_level'
            ])
            
            # Write data
            for event in events:
                writer.writerow([
                    event.id,
                    event.user_id,
                    event.event_name,
                    event.event_type,
                    event.action,
                    event.created_at.isoformat(),
                    event.sentiment_score,
                    event.engagement_level
                ])
            
            return {
                'format': 'csv',
                'data': output.getvalue(),
                'records': events.count()
            }
        
        else:  # JSON format
            events_data = []
            for event in events:
                events_data.append({
                    'id': event.id,
                    'user_id': event.user_id,
                    'event_name': event.event_name,
                    'event_type': event.event_type,
                    'action': event.action,
                    'created_at': event.created_at.isoformat(),
                    'sentiment_score': event.sentiment_score,
                    'engagement_level': event.engagement_level,
                    'metadata': event.metadata
                })
            
            return {
                'format': 'json',
                'data': events_data,
                'records': len(events_data)
            }
        
    except Exception as e:
        logger.error(f"Failed to export events: {e}")
        raise HTTPException(status_code=500, detail=str(e))
