"""
Celery tasks for async analytics processing.

This module provides background tasks for AI processing, metrics calculation,
and data aggregation to ensure non-blocking analytics operations.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any
from celery import shared_task
from django.utils import timezone
from django.contrib.auth.models import User
from django.db import transaction

from .models import UserEvent, AIInsight, UserBehaviorProfile, UserPersona, BusinessMetric
from .ai_services import (
    SentimentAnalysisService, 
    UserBehaviorAnalysisService, 
    PredictiveAnalyticsService,
    UserClusteringService
)
from .metrics import MetricsProcessor

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def process_user_events_batch(self, event_ids: List[int]):
    """Process a batch of user events for AI analysis"""
    try:
        events = UserEvent.objects.filter(id__in=event_ids)
        
        if not events.exists():
            logger.warning(f"No events found for IDs: {event_ids}")
            return {'processed': 0, 'errors': 0}
        
        processed = 0
        errors = 0
        
        for event in events:
            try:
                # Analyze sentiment if not already done
                if event.sentiment_score is None and event.metadata:
                    sentiment_service = SentimentAnalysisService()
                    
                    # Extract text from metadata
                    text_content = ""
                    if 'message' in event.metadata:
                        text_content = event.metadata['message']
                    elif 'description' in event.metadata:
                        text_content = event.metadata['description']
                    
                    if text_content:
                        sentiment_result = sentiment_service.analyze_text_sentiment(text_content)
                        event.sentiment_score = sentiment_result['score']
                        event.save(update_fields=['sentiment_score'])
                
                # Classify intent if not already done
                if not event.intent_classification:
                    intent = classify_event_intent(event)
                    if intent:
                        event.intent_classification = intent
                        event.save(update_fields=['intent_classification'])
                
                # Calculate engagement level
                if not event.engagement_level:
                    engagement = calculate_engagement_level(event)
                    if engagement:
                        event.engagement_level = engagement
                        event.save(update_fields=['engagement_level'])
                
                processed += 1
                
            except Exception as e:
                logger.error(f"Error processing event {event.id}: {e}")
                errors += 1
        
        logger.info(f"Processed {processed} events, {errors} errors")
        return {'processed': processed, 'errors': errors}
        
    except Exception as e:
        logger.error(f"Failed to process user events batch: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_user_behavior_insights(self, user_id: int):
    """Generate AI insights for a specific user"""
    try:
        user = User.objects.get(id=user_id)
        
        # Analyze user behavior
        behavior_service = UserBehaviorAnalysisService()
        analysis = behavior_service.analyze_user_behavior(user)
        
        # Create or update behavior profile
        behavior_profile, created = UserBehaviorProfile.objects.get_or_create(
            user=user,
            defaults={
                'engagement_score': analysis['engagement_score'],
                'activity_frequency': analysis['activity_patterns'].get('frequency', 'medium'),
                'preferred_event_types': analysis['preferences'].get('event_types', {}),
                'preferred_times': analysis['activity_patterns'].get('peak_hours', []),
                'preferred_locations': analysis['preferences'].get('locations', []),
                'churn_risk_score': analysis['predictions']['churn_risk'],
                'conversion_probability': analysis['predictions']['conversion_probability'],
                'last_analysis_at': timezone.now(),
                'analysis_version': '1.0'
            }
        )
        
        if not created:
            # Update existing profile
            behavior_profile.engagement_score = analysis['engagement_score']
            behavior_profile.activity_frequency = analysis['activity_patterns'].get('frequency', 'medium')
            behavior_profile.preferred_event_types = analysis['preferences'].get('event_types', {})
            behavior_profile.preferred_times = analysis['activity_patterns'].get('peak_hours', [])
            behavior_profile.preferred_locations = analysis['preferences'].get('locations', [])
            behavior_profile.churn_risk_score = analysis['predictions']['churn_risk']
            behavior_profile.conversion_probability = analysis['predictions']['conversion_probability']
            behavior_profile.last_analysis_at = timezone.now()
            behavior_profile.save()
        
        # Generate AI insights
        insights_created = 0
        
        # Churn risk insight
        if analysis['predictions']['churn_risk'] > 0.7:
            AIInsight.objects.create(
                insight_type='churn_risk',
                target_type='user',
                target_id=str(user_id),
                title=f'High Churn Risk Detected',
                description=f'User {user.username} shows signs of potential churn with {analysis["predictions"]["churn_risk"]:.1%} probability',
                confidence_score=analysis['predictions']['churn_risk'],
                model_name='behavior_analysis_v1',
                model_version='1.0',
                input_features=['engagement_score', 'activity_patterns', 'risk_factors'],
                output_data=analysis['predictions'],
                is_actionable=True,
                suggested_actions=['send_retention_email', 'offer_discount', 'personalized_recommendations'],
                priority='high' if analysis['predictions']['churn_risk'] > 0.8 else 'medium'
            )
            insights_created += 1
        
        # Engagement insight
        if analysis['engagement_score'] < 0.3:
            AIInsight.objects.create(
                insight_type='engagement',
                target_type='user',
                target_id=str(user_id),
                title=f'Low Engagement Detected',
                description=f'User {user.username} has low engagement score of {analysis["engagement_score"]:.2f}',
                confidence_score=0.8,
                model_name='behavior_analysis_v1',
                model_version='1.0',
                input_features=['engagement_score', 'activity_patterns'],
                output_data={'engagement_score': analysis['engagement_score']},
                is_actionable=True,
                suggested_actions=['send_engagement_email', 'show_tutorial', 'recommend_events'],
                priority='medium'
            )
            insights_created += 1
        
        # Persona assignment
        if analysis['persona_suggestions']:
            persona_name = analysis['persona_suggestions'][0]
            persona, created = UserPersona.objects.get_or_create(
                persona_name=persona_name,
                defaults={
                    'persona_description': f'User persona: {persona_name}',
                    'behavior_patterns': analysis['activity_patterns'],
                    'engagement_preferences': analysis['preferences'],
                    'risk_factors': analysis['risk_factors'],
                    'model_confidence': 0.7,
                    'features_used': ['engagement_score', 'activity_patterns', 'preferences']
                }
            )
            
            if not created:
                behavior_profile.primary_persona = persona
                behavior_profile.save()
        
        logger.info(f"Generated {insights_created} insights for user {user_id}")
        return {'user_id': user_id, 'insights_created': insights_created}
        
    except User.DoesNotExist:
        logger.error(f"User {user_id} not found")
        return {'error': 'User not found'}
    except Exception as e:
        logger.error(f"Failed to generate user behavior insights: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def process_daily_metrics_calculation(self, date_str: str = None):
    """Calculate all daily metrics"""
    try:
        if date_str:
            date = datetime.strptime(date_str, '%Y-%m-%d').date()
        else:
            date = timezone.now().date()
        
        logger.info(f"Processing daily metrics for {date}")
        
        # Process all metrics
        results = MetricsProcessor.process_daily_metrics(date)
        
        # Check for alerts
        alerts = MetricsProcessor.check_alert_thresholds()
        
        logger.info(f"Completed daily metrics calculation for {date}")
        return {
            'date': date.isoformat(),
            'metrics_processed': len(results.get('kpis', {})) + len(results.get('kris', {})) + len(results.get('krs', {})),
            'alerts_triggered': len(alerts),
            'alerts': alerts
        }
        
    except Exception as e:
        logger.error(f"Failed to process daily metrics: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def perform_user_clustering(self, n_clusters: int = 5):
    """Perform user clustering analysis"""
    try:
        clustering_service = UserClusteringService()
        results = clustering_service.cluster_users(n_clusters)
        
        if 'error' in results:
            logger.error(f"Clustering failed: {results['error']}")
            return results
        
        # Create insights for each cluster
        insights_created = 0
        for cluster_name, cluster_data in results['clusters'].items():
            AIInsight.objects.create(
                insight_type='clustering',
                target_type='user_segment',
                target_id=cluster_name,
                title=f'User Cluster: {cluster_data["characteristics"]["type"]}',
                description=f'Cluster with {cluster_data["user_count"]} users, avg engagement: {cluster_data["characteristics"]["avg_engagement"]:.2f}',
                confidence_score=0.8,
                model_name='kmeans_clustering_v1',
                model_version='1.0',
                input_features=['engagement_score', 'churn_risk_score', 'conversion_probability'],
                output_data=cluster_data,
                is_actionable=True,
                suggested_actions=['targeted_marketing', 'personalized_recommendations', 'segment_analysis'],
                priority='medium'
            )
            insights_created += 1
        
        logger.info(f"Created {insights_created} clustering insights")
        return {
            'clusters_created': len(results['clusters']),
            'insights_created': insights_created,
            'silhouette_score': results.get('silhouette_score', 0)
        }
        
    except Exception as e:
        logger.error(f"Failed to perform user clustering: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def generate_predictive_insights(self, user_id: int = None):
    """Generate predictive insights for users or events"""
    try:
        predictive_service = PredictiveAnalyticsService()
        insights_created = 0
        
        if user_id:
            # Generate insights for specific user
            user = User.objects.get(id=user_id)
            
            # Event attendance prediction
            # This would need event data - simplified for example
            prediction = predictive_service.predict_event_attendance(user, 1)  # Placeholder event ID
            
            if prediction['probability'] > 0.7:
                AIInsight.objects.create(
                    insight_type='prediction',
                    target_type='user',
                    target_id=str(user_id),
                    title='High Event Attendance Probability',
                    description=f'User likely to attend events with {prediction["probability"]:.1%} probability',
                    confidence_score=prediction['confidence'],
                    model_name='attendance_prediction_v1',
                    model_version='1.0',
                    input_features=prediction['factors'],
                    output_data=prediction,
                    is_actionable=True,
                    suggested_actions=['send_event_invites', 'prioritize_recommendations'],
                    priority='medium'
                )
                insights_created += 1
            
            # Generate recommendations
            recommendations = predictive_service.generate_recommendations(user)
            
            for rec in recommendations:
                AIInsight.objects.create(
                    insight_type='recommendation',
                    target_type='user',
                    target_id=str(user_id),
                    title=rec['title'],
                    description=rec['description'],
                    confidence_score=0.7,
                    model_name='recommendation_engine_v1',
                    model_version='1.0',
                    input_features=['user_behavior', 'preferences', 'engagement'],
                    output_data=rec,
                    is_actionable=True,
                    suggested_actions=[rec['action']],
                    priority=rec['priority']
                )
                insights_created += 1
        
        else:
            # Generate insights for all users (batch processing)
            users = User.objects.filter(is_active=True)[:100]  # Limit for performance
            
            for user in users:
                try:
                    # Generate recommendations for each user
                    recommendations = predictive_service.generate_recommendations(user)
                    
                    for rec in recommendations:
                        AIInsight.objects.create(
                            insight_type='recommendation',
                            target_type='user',
                            target_id=str(user.id),
                            title=rec['title'],
                            description=rec['description'],
                            confidence_score=0.7,
                            model_name='recommendation_engine_v1',
                            model_version='1.0',
                            input_features=['user_behavior', 'preferences', 'engagement'],
                            output_data=rec,
                            is_actionable=True,
                            suggested_actions=[rec['action']],
                            priority=rec['priority']
                        )
                        insights_created += 1
                        
                except Exception as e:
                    logger.error(f"Failed to generate insights for user {user.id}: {e}")
                    continue
        
        logger.info(f"Generated {insights_created} predictive insights")
        return {'insights_created': insights_created}
        
    except Exception as e:
        logger.error(f"Failed to generate predictive insights: {e}")
        raise self.retry(exc=e, countdown=60)


@shared_task(bind=True, max_retries=3)
def detect_anomalies_batch(self, metric_names: List[str] = None):
    """Detect anomalies in business metrics"""
    try:
        if metric_names is None:
            metric_names = [
                'daily_active_users',
                'payment_failure_rate',
                'conversion_rate',
                'revenue_per_user'
            ]
        
        predictive_service = PredictiveAnalyticsService()
        anomalies_detected = 0
        
        for metric_name in metric_names:
            try:
                anomalies = predictive_service.detect_anomalies(metric_name)
                
                for anomaly in anomalies:
                    AIInsight.objects.create(
                        insight_type='anomaly',
                        target_type='metric',
                        target_id=metric_name,
                        title=f'Anomaly Detected: {metric_name}',
                        description=f'Metric value {anomaly["actual_value"]:.2f} deviates significantly from expected {anomaly["expected_value"]:.2f}',
                        confidence_score=min(anomaly['z_score'] / 3.0, 1.0),  # Normalize z-score to 0-1
                        model_name='anomaly_detection_v1',
                        model_version='1.0',
                        input_features=[metric_name],
                        output_data=anomaly,
                        is_actionable=True,
                        suggested_actions=['investigate_root_cause', 'monitor_closely', 'alert_team'],
                        priority='critical' if anomaly['severity'] == 'high' else 'medium'
                    )
                    anomalies_detected += 1
                    
            except Exception as e:
                logger.error(f"Failed to detect anomalies for {metric_name}: {e}")
                continue
        
        logger.info(f"Detected {anomalies_detected} anomalies")
        return {'anomalies_detected': anomalies_detected}
        
    except Exception as e:
        logger.error(f"Failed to detect anomalies batch: {e}")
        raise self.retry(exc=e, countdown=60)


# Helper functions for event processing

def classify_event_intent(event: UserEvent) -> str:
    """Classify the intent of an event"""
    event_name = event.event_name.lower()
    
    if 'login' in event_name or 'signin' in event_name:
        return 'authentication'
    elif 'signup' in event_name or 'register' in event_name:
        return 'registration'
    elif 'event' in event_name and 'create' in event_name:
        return 'event_creation'
    elif 'event' in event_name and 'request' in event_name:
        return 'event_request'
    elif 'payment' in event_name:
        return 'payment'
    elif 'profile' in event_name:
        return 'profile_management'
    elif 'search' in event_name:
        return 'search'
    elif 'browse' in event_name:
        return 'browsing'
    else:
        return 'general_interaction'


def calculate_engagement_level(event: UserEvent) -> str:
    """Calculate engagement level for an event"""
    # Simple heuristic based on event type and metadata
    if event.event_type == 'conversion':
        return 'very_high'
    elif event.event_type == 'engagement':
        return 'high'
    elif event.event_type == 'user_action':
        return 'medium'
    elif event.event_type == 'page_view':
        return 'low'
    else:
        return 'low'


# Periodic tasks

@shared_task
def cleanup_old_analytics_data():
    """Clean up old analytics data based on retention policies"""
    try:
        from .models import BaseAnalyticsModel
        
        # Get all analytics models
        analytics_models = [
            UserEvent, AIInsight, BusinessMetric, SystemLog
        ]
        
        cleaned_records = 0
        
        for model in analytics_models:
            if hasattr(model, 'retention_days'):
                cutoff_date = timezone.now() - timedelta(days=365)  # Default 1 year
                
                old_records = model.objects.filter(
                    created_at__lt=cutoff_date,
                    is_archived=False
                )
                
                # Archive instead of delete
                updated = old_records.update(
                    is_archived=True,
                    archived_at=timezone.now()
                )
                
                cleaned_records += updated
                logger.info(f"Archived {updated} {model.__name__} records")
        
        logger.info(f"Cleaned up {cleaned_records} analytics records")
        return {'cleaned_records': cleaned_records}
        
    except Exception as e:
        logger.error(f"Failed to cleanup old analytics data: {e}")
        return {'error': str(e)}


@shared_task
def generate_daily_insights_summary():
    """Generate daily insights summary for stakeholders"""
    try:
        yesterday = timezone.now().date() - timedelta(days=1)
        
        # Get key metrics
        metrics = BusinessMetric.objects.filter(
            created_at__date=yesterday,
            metric_type__in=['kpi', 'kri']
        )
        
        # Get insights
        insights = AIInsight.objects.filter(
            created_at__date=yesterday,
            priority__in=['high', 'critical']
        )
        
        # Get alerts
        alerts = BusinessMetric.objects.filter(
            created_at__date=yesterday,
            is_alert_triggered=True
        )
        
        summary = {
            'date': yesterday.isoformat(),
            'metrics_count': metrics.count(),
            'insights_count': insights.count(),
            'alerts_count': alerts.count(),
            'key_metrics': {},
            'critical_insights': [],
            'alerts': []
        }
        
        # Compile key metrics
        for metric in metrics:
            summary['key_metrics'][metric.metric_name] = {
                'value': float(metric.value),
                'type': metric.metric_type,
                'category': metric.metric_category
            }
        
        # Compile critical insights
        for insight in insights:
            summary['critical_insights'].append({
                'type': insight.insight_type,
                'title': insight.title,
                'priority': insight.priority,
                'confidence': insight.confidence_score
            })
        
        # Compile alerts
        for alert in alerts:
            summary['alerts'].append({
                'metric': alert.metric_name,
                'value': float(alert.value),
                'threshold': float(alert.warning_threshold or 0)
            })
        
        logger.info(f"Generated daily insights summary for {yesterday}")
        return summary
        
    except Exception as e:
        logger.error(f"Failed to generate daily insights summary: {e}")
        return {'error': str(e)}