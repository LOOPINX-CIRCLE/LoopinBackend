"""
AI Services for analytics and intelligence layer.

This module provides AI-driven insights, predictions, and behavioral analysis
using OpenAI API and local ML models.
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q, Count, Avg, Sum
from django.utils import timezone
import openai
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from textblob import TextBlob
import nltk
from nltk.sentiment import SentimentIntensityAnalyzer

from .models import UserEvent, AIInsight, UserPersona, UserBehaviorProfile, BusinessMetric

logger = logging.getLogger(__name__)


class AIServiceManager:
    """Central manager for all AI services"""
    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    @classmethod
    def initialize(cls):
        """Initialize AI services"""
        if not cls._initialized:
            cls._instance = cls()
            cls._instance._setup_openai()
            cls._instance._setup_nltk()
            cls._initialized = True
            logger.info("AI Service Manager initialized successfully")
    
    def _setup_openai(self):
        """Setup OpenAI client"""
        try:
            openai.api_key = os.getenv('OPENAI_API_KEY')
            self.openai_client = openai.OpenAI(api_key=openai.api_key)
            logger.info("OpenAI client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI: {e}")
            self.openai_client = None
    
    def _setup_nltk(self):
        """Setup NLTK resources"""
        try:
            nltk.download('vader_lexicon', quiet=True)
            nltk.download('punkt', quiet=True)
            self.sentiment_analyzer = SentimentIntensityAnalyzer()
            logger.info("NLTK resources downloaded")
        except Exception as e:
            logger.error(f"Failed to setup NLTK: {e}")
            self.sentiment_analyzer = None


class SentimentAnalysisService:
    """Service for sentiment analysis and emotional insights"""
    
    def __init__(self):
        self.ai_manager = AIServiceManager()
        self.sentiment_analyzer = self.ai_manager.sentiment_analyzer
    
    def analyze_text_sentiment(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment of text using multiple methods"""
        if not text:
            return {'sentiment': 'neutral', 'score': 0.0, 'confidence': 0.0}
        
        results = {}
        
        # TextBlob sentiment
        blob = TextBlob(text)
        results['textblob_polarity'] = blob.sentiment.polarity
        results['textblob_subjectivity'] = blob.sentiment.subjectivity
        
        # VADER sentiment
        if self.sentiment_analyzer:
            vader_scores = self.sentiment_analyzer.polarity_scores(text)
            results.update(vader_scores)
        
        # OpenAI sentiment analysis
        if self.ai_manager.openai_client:
            try:
                openai_sentiment = self._analyze_with_openai(text)
                results['openai_sentiment'] = openai_sentiment
            except Exception as e:
                logger.error(f"OpenAI sentiment analysis failed: {e}")
        
        # Aggregate sentiment score
        sentiment_score = self._aggregate_sentiment_scores(results)
        
        return {
            'sentiment': self._classify_sentiment(sentiment_score),
            'score': sentiment_score,
            'confidence': self._calculate_confidence(results),
            'details': results
        }
    
    def _analyze_with_openai(self, text: str) -> Dict[str, Any]:
        """Analyze sentiment using OpenAI"""
        prompt = f"""
        Analyze the sentiment of this text and provide:
        1. Overall sentiment (positive, negative, neutral)
        2. Emotional intensity (1-10 scale)
        3. Key emotions detected
        4. Confidence level (0-1)
        
        Text: "{text}"
        
        Respond in JSON format.
        """
        
        response = self.ai_manager.openai_client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3
        )
        
        return json.loads(response.choices[0].message.content)
    
    def _aggregate_sentiment_scores(self, results: Dict[str, Any]) -> float:
        """Aggregate multiple sentiment scores into a single score"""
        scores = []
        
        if 'textblob_polarity' in results:
            scores.append(results['textblob_polarity'])
        
        if 'compound' in results:
            scores.append(results['compound'])
        
        if 'openai_sentiment' in results and 'score' in results['openai_sentiment']:
            scores.append(results['openai_sentiment']['score'])
        
        return np.mean(scores) if scores else 0.0
    
    def _classify_sentiment(self, score: float) -> str:
        """Classify sentiment based on score"""
        if score > 0.1:
            return 'positive'
        elif score < -0.1:
            return 'negative'
        else:
            return 'neutral'
    
    def _calculate_confidence(self, results: Dict[str, Any]) -> float:
        """Calculate confidence based on agreement between methods"""
        scores = []
        
        if 'textblob_polarity' in results:
            scores.append(abs(results['textblob_polarity']))
        
        if 'compound' in results:
            scores.append(abs(results['compound']))
        
        return np.mean(scores) if scores else 0.0


class UserBehaviorAnalysisService:
    """Service for analyzing user behavior patterns"""
    
    def __init__(self):
        self.ai_manager = AIServiceManager()
    
    def analyze_user_behavior(self, user: User, days: int = 30) -> Dict[str, Any]:
        """Comprehensive user behavior analysis"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        # Get user events
        events = UserEvent.objects.filter(
            user=user,
            created_at__range=[start_date, end_date]
        ).order_by('created_at')
        
        if not events.exists():
            return self._default_behavior_profile()
        
        # Analyze patterns
        analysis = {
            'engagement_score': self._calculate_engagement_score(events),
            'activity_patterns': self._analyze_activity_patterns(events),
            'preferences': self._extract_preferences(events),
            'risk_factors': self._identify_risk_factors(events),
            'persona_suggestions': self._suggest_personas(events),
            'predictions': self._generate_predictions(user, events)
        }
        
        return analysis
    
    def _calculate_engagement_score(self, events) -> float:
        """Calculate user engagement score"""
        if not events.exists():
            return 0.0
        
        # Factors affecting engagement
        total_events = events.count()
        unique_days = events.values('created_at__date').distinct().count()
        session_count = events.values('session_id').distinct().count()
        
        # Event type weights
        event_weights = {
            'conversion': 3.0,
            'engagement': 2.0,
            'user_action': 1.5,
            'page_view': 1.0,
            'api_call': 0.8,
        }
        
        weighted_score = sum(
            event_weights.get(event.event_type, 1.0) 
            for event in events
        )
        
        # Normalize score
        max_possible_score = total_events * 3.0
        engagement_score = weighted_score / max_possible_score if max_possible_score > 0 else 0.0
        
        # Boost for consistency
        consistency_boost = min(unique_days / 30.0, 1.0) * 0.2
        
        return min(engagement_score + consistency_boost, 1.0)
    
    def _analyze_activity_patterns(self, events) -> Dict[str, Any]:
        """Analyze user activity patterns"""
        patterns = {
            'peak_hours': [],
            'peak_days': [],
            'session_length': 0,
            'events_per_session': 0,
            'response_times': []
        }
        
        if not events.exists():
            return patterns
        
        # Analyze by hour
        hour_counts = {}
        day_counts = {}
        session_lengths = {}
        response_times = []
        
        for event in events:
            hour = event.created_at.hour
            day = event.created_at.weekday()
            
            hour_counts[hour] = hour_counts.get(hour, 0) + 1
            day_counts[day] = day_counts.get(day, 0) + 1
            
            if event.response_time_ms:
                response_times.append(event.response_time_ms)
            
            # Session analysis
            session_id = event.session_id
            if session_id not in session_lengths:
                session_lengths[session_id] = {
                    'start': event.created_at,
                    'end': event.created_at,
                    'count': 0
                }
            
            session_lengths[session_id]['end'] = event.created_at
            session_lengths[session_id]['count'] += 1
        
        # Find peak hours and days
        if hour_counts:
            patterns['peak_hours'] = sorted(
                hour_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
        
        if day_counts:
            patterns['peak_days'] = sorted(
                day_counts.items(), 
                key=lambda x: x[1], 
                reverse=True
            )[:3]
        
        # Calculate session metrics
        if session_lengths:
            lengths = [
                (session['end'] - session['start']).total_seconds() / 60
                for session in session_lengths.values()
            ]
            patterns['session_length'] = np.mean(lengths) if lengths else 0
            
            counts = [session['count'] for session in session_lengths.values()]
            patterns['events_per_session'] = np.mean(counts) if counts else 0
        
        if response_times:
            patterns['response_times'] = {
                'mean': np.mean(response_times),
                'median': np.median(response_times),
                'p95': np.percentile(response_times, 95)
            }
        
        return patterns
    
    def _extract_preferences(self, events) -> Dict[str, Any]:
        """Extract user preferences from events"""
        preferences = {
            'event_types': {},
            'actions': {},
            'pages': {},
            'devices': {},
            'browsers': {}
        }
        
        for event in events:
            # Event types
            if event.event_name:
                preferences['event_types'][event.event_name] = \
                    preferences['event_types'].get(event.event_name, 0) + 1
            
            # Actions
            if event.action:
                preferences['actions'][event.action] = \
                    preferences['actions'].get(event.action, 0) + 1
            
            # Pages
            if event.page_url:
                preferences['pages'][event.page_url] = \
                    preferences['pages'].get(event.page_url, 0) + 1
            
            # Devices
            if event.device_type:
                preferences['devices'][event.device_type] = \
                    preferences['devices'].get(event.device_type, 0) + 1
            
            # Browsers
            if event.browser:
                preferences['browsers'][event.browser] = \
                    preferences['browsers'].get(event.browser, 0) + 1
        
        # Sort by frequency
        for key in preferences:
            preferences[key] = dict(
                sorted(preferences[key].items(), key=lambda x: x[1], reverse=True)
            )
        
        return preferences
    
    def _identify_risk_factors(self, events) -> List[str]:
        """Identify potential risk factors"""
        risk_factors = []
        
        # Low engagement
        if events.count() < 5:
            risk_factors.append('low_engagement')
        
        # High error rate
        error_events = events.filter(event_type='error')
        if error_events.count() / events.count() > 0.1:
            risk_factors.append('high_error_rate')
        
        # Slow response times
        slow_events = events.filter(response_time_ms__gt=5000)
        if slow_events.count() / events.count() > 0.2:
            risk_factors.append('slow_performance')
        
        # Negative sentiment
        negative_events = events.filter(sentiment_score__lt=-0.3)
        if negative_events.count() / events.count() > 0.3:
            risk_factors.append('negative_sentiment')
        
        return risk_factors
    
    def _suggest_personas(self, events) -> List[str]:
        """Suggest user personas based on behavior"""
        personas = []
        
        # Analyze behavior patterns
        event_types = [event.event_type for event in events]
        actions = [event.action for event in events if event.action]
        
        # Social Explorer
        if 'engagement' in event_types and 'conversion' in event_types:
            personas.append('social_explorer')
        
        # Event Regular
        if event_types.count('user_action') > event_types.count('page_view'):
            personas.append('event_regular')
        
        # Passive Observer
        if event_types.count('page_view') > event_types.count('user_action'):
            personas.append('passive_observer')
        
        # Power User
        if events.count() > 50 and 'api_call' in event_types:
            personas.append('power_user')
        
        return personas
    
    def _generate_predictions(self, user: User, events) -> Dict[str, Any]:
        """Generate predictions for user behavior"""
        predictions = {
            'churn_risk': 0.0,
            'conversion_probability': 0.0,
            'engagement_trend': 'stable',
            'next_action': 'unknown'
        }
        
        # Simple prediction logic (can be enhanced with ML models)
        recent_events = events.filter(
            created_at__gte=timezone.now() - timedelta(days=7)
        )
        
        if recent_events.count() < 2:
            predictions['churn_risk'] = 0.7
        elif recent_events.count() > 10:
            predictions['churn_risk'] = 0.2
        
        # Conversion probability based on engagement
        engagement_score = self._calculate_engagement_score(events)
        predictions['conversion_probability'] = engagement_score * 0.8
        
        return predictions
    
    def _default_behavior_profile(self) -> Dict[str, Any]:
        """Return default profile for users with no events"""
        return {
            'engagement_score': 0.0,
            'activity_patterns': {},
            'preferences': {},
            'risk_factors': ['no_activity'],
            'persona_suggestions': ['new_user'],
            'predictions': {
                'churn_risk': 0.8,
                'conversion_probability': 0.1,
                'engagement_trend': 'unknown',
                'next_action': 'unknown'
            }
        }


class PredictiveAnalyticsService:
    """Service for predictive analytics and recommendations"""
    
    def __init__(self):
        self.ai_manager = AIServiceManager()
    
    def predict_event_attendance(self, user: User, event_id: int) -> Dict[str, Any]:
        """Predict if user will attend an event"""
        # Get user behavior profile
        try:
            behavior_profile = user.behavior_profile
        except UserBehaviorProfile.DoesNotExist:
            behavior_profile = None
        
        # Get user's event history
        past_events = UserEvent.objects.filter(
            user=user,
            event_name__contains='event'
        ).order_by('-created_at')[:10]
        
        # Simple prediction based on engagement and preferences
        base_probability = 0.5
        
        if behavior_profile:
            base_probability = behavior_profile.conversion_probability
        
        # Adjust based on past behavior
        if past_events.filter(event_name__contains='attendance').exists():
            base_probability += 0.2
        
        if past_events.filter(event_name__contains='request').exists():
            base_probability += 0.1
        
        return {
            'probability': min(base_probability, 1.0),
            'confidence': 0.7,
            'factors': ['engagement_score', 'past_attendance', 'event_requests']
        }
    
    def detect_anomalies(self, metric_name: str, days: int = 7) -> List[Dict[str, Any]]:
        """Detect anomalies in business metrics"""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        metrics = BusinessMetric.objects.filter(
            metric_name=metric_name,
            created_at__range=[start_date, end_date]
        ).order_by('created_at')
        
        if metrics.count() < 3:
            return []
        
        values = [float(m.value) for m in metrics]
        
        # Simple anomaly detection using z-score
        mean_val = np.mean(values)
        std_val = np.std(values)
        
        anomalies = []
        for i, metric in enumerate(metrics):
            z_score = abs((values[i] - mean_val) / std_val) if std_val > 0 else 0
            
            if z_score > 2.0:  # Threshold for anomaly
                anomalies.append({
                    'metric': metric,
                    'z_score': z_score,
                    'severity': 'high' if z_score > 3.0 else 'medium',
                    'expected_value': mean_val,
                    'actual_value': values[i]
                })
        
        return anomalies
    
    def generate_recommendations(self, user: User) -> List[Dict[str, Any]]:
        """Generate personalized recommendations for user"""
        recommendations = []
        
        try:
            behavior_profile = user.behavior_profile
        except UserBehaviorProfile.DoesNotExist:
            behavior_profile = None
        
        # Event recommendations based on preferences
        if behavior_profile and behavior_profile.preferred_event_types:
            recommendations.append({
                'type': 'event_suggestion',
                'title': 'Events You Might Like',
                'description': f'Based on your interest in {behavior_profile.preferred_event_types[0]}',
                'priority': 'high',
                'action': 'browse_events'
            })
        
        # Engagement recommendations
        if behavior_profile and behavior_profile.engagement_score < 0.3:
            recommendations.append({
                'type': 'engagement',
                'title': 'Boost Your Engagement',
                'description': 'Try exploring different event types to find what interests you',
                'priority': 'medium',
                'action': 'explore_categories'
            })
        
        # Profile completion recommendations
        if not behavior_profile or not behavior_profile.user.profile.is_verified:
            recommendations.append({
                'type': 'profile',
                'title': 'Complete Your Profile',
                'description': 'Add more details to get better event recommendations',
                'priority': 'high',
                'action': 'complete_profile'
            })
        
        return recommendations


class UserClusteringService:
    """Service for clustering users based on behavior"""
    
    def __init__(self):
        self.ai_manager = AIServiceManager()
    
    def cluster_users(self, n_clusters: int = 5) -> Dict[str, Any]:
        """Cluster users based on behavioral features"""
        # Get user behavior profiles
        profiles = UserBehaviorProfile.objects.all()
        
        if profiles.count() < n_clusters:
            return {'error': 'Not enough users for clustering'}
        
        # Prepare features
        features = []
        user_ids = []
        
        for profile in profiles:
            feature_vector = [
                profile.engagement_score,
                profile.churn_risk_score,
                profile.conversion_probability,
                len(profile.preferred_event_types),
                len(profile.preferred_times),
                len(profile.preferred_locations)
            ]
            features.append(feature_vector)
            user_ids.append(profile.user.id)
        
        # Normalize features
        scaler = StandardScaler()
        features_scaled = scaler.fit_transform(features)
        
        # Perform clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42)
        cluster_labels = kmeans.fit_predict(features_scaled)
        
        # Analyze clusters
        clusters = {}
        for i in range(n_clusters):
            cluster_users = [user_ids[j] for j in range(len(user_ids)) if cluster_labels[j] == i]
            clusters[f'cluster_{i}'] = {
                'user_count': len(cluster_users),
                'user_ids': cluster_users,
                'centroid': kmeans.cluster_centers_[i].tolist(),
                'characteristics': self._analyze_cluster_characteristics(
                    cluster_users, features_scaled, cluster_labels, i
                )
            }
        
        return {
            'clusters': clusters,
            'inertia': kmeans.inertia_,
            'silhouette_score': self._calculate_silhouette_score(features_scaled, cluster_labels)
        }
    
    def _analyze_cluster_characteristics(self, user_ids: List[int], features: np.ndarray, 
                                       labels: np.ndarray, cluster_id: int) -> Dict[str, Any]:
        """Analyze characteristics of a cluster"""
        cluster_indices = [i for i, label in enumerate(labels) if label == cluster_id]
        cluster_features = features[cluster_indices]
        
        characteristics = {
            'avg_engagement': float(np.mean(cluster_features[:, 0])),
            'avg_churn_risk': float(np.mean(cluster_features[:, 1])),
            'avg_conversion_prob': float(np.mean(cluster_features[:, 2])),
            'avg_preferences_count': float(np.mean(cluster_features[:, 3:6]))
        }
        
        # Determine cluster type
        if characteristics['avg_engagement'] > 0.7:
            characteristics['type'] = 'high_engagement'
        elif characteristics['avg_churn_risk'] > 0.7:
            characteristics['type'] = 'churn_risk'
        elif characteristics['avg_conversion_prob'] > 0.7:
            characteristics['type'] = 'high_conversion'
        else:
            characteristics['type'] = 'average'
        
        return characteristics
    
    def _calculate_silhouette_score(self, features: np.ndarray, labels: np.ndarray) -> float:
        """Calculate silhouette score for clustering quality"""
        try:
            from sklearn.metrics import silhouette_score
            return float(silhouette_score(features, labels))
        except ImportError:
            return 0.0
