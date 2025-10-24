"""
Core analytics models for comprehensive data collection and AI-driven insights.

This module defines the foundational models for capturing user behavior,
business metrics, AI insights, and system performance data.
"""

from django.db import models
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.utils import timezone
from django.core.validators import MinValueValidator, MaxValueValidator
from loopin_backend.base_models import TimeStampedModel
import uuid
import json
from typing import Dict, Any, Optional


class BaseAnalyticsModel(TimeStampedModel):
    """Base model for all analytics data with common fields"""
    
    # Unique identifier for this analytics record
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    # Source of the data (api, signal, manual, ai_generated, etc.)
    source = models.CharField(
        max_length=50,
        choices=[
            ('api', 'API Request'),
            ('signal', 'Django Signal'),
            ('manual', 'Manual Entry'),
            ('ai_generated', 'AI Generated'),
            ('system', 'System Event'),
            ('middleware', 'Middleware'),
            ('batch_job', 'Batch Job'),
        ],
        default='api'
    )
    
    # Data lineage tracking
    parent_uuid = models.UUIDField(null=True, blank=True, help_text="Parent analytics record")
    lineage_depth = models.PositiveIntegerField(default=0, help_text="Depth in data lineage")
    
    # Retention and archival
    retention_days = models.PositiveIntegerField(default=365, help_text="Days to retain this data")
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        abstract = True


class UserEvent(BaseAnalyticsModel):
    """Captures all user interactions and behaviors"""
    
    # User and session information
    user = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='analytics_events'
    )
    session_id = models.CharField(max_length=100, db_index=True)
    anonymous_id = models.CharField(max_length=100, blank=True, help_text="For anonymous users")
    
    # Event classification
    event_type = models.CharField(
        max_length=50,
        choices=[
            ('page_view', 'Page View'),
            ('api_call', 'API Call'),
            ('user_action', 'User Action'),
            ('system_event', 'System Event'),
            ('error', 'Error'),
            ('conversion', 'Conversion'),
            ('engagement', 'Engagement'),
        ],
        db_index=True
    )
    
    # Event details
    event_name = models.CharField(max_length=100, db_index=True)
    page_url = models.URLField(blank=True)
    action = models.CharField(max_length=100, blank=True)
    
    # Context and metadata
    metadata = models.JSONField(default=dict, blank=True)
    user_agent = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    referrer = models.URLField(blank=True)
    
    # Performance metrics
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    status_code = models.PositiveIntegerField(null=True, blank=True)
    
    # Behavioral context
    device_type = models.CharField(max_length=20, blank=True)  # mobile, desktop, tablet
    browser = models.CharField(max_length=50, blank=True)
    os = models.CharField(max_length=50, blank=True)
    
    # AI-processed fields
    sentiment_score = models.FloatField(
        null=True, 
        blank=True,
        validators=[MinValueValidator(-1.0), MaxValueValidator(1.0)]
    )
    intent_classification = models.CharField(max_length=50, blank=True)
    engagement_level = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('very_high', 'Very High'),
        ],
        blank=True
    )
    
    # Business context
    revenue_impact = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    conversion_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    class Meta:
        indexes = [
            models.Index(fields=['user', 'created_at']),
            models.Index(fields=['session_id', 'created_at']),
            models.Index(fields=['event_type', 'created_at']),
            models.Index(fields=['event_name', 'created_at']),
            models.Index(fields=['sentiment_score']),
            models.Index(fields=['engagement_level']),
        ]

    def __str__(self):
        return f"{self.event_name} - {self.user or self.anonymous_id} - {self.created_at}"


class BusinessMetric(BaseAnalyticsModel):
    """Stores real-time computed KPIs, KRIs, and KRs"""
    
    # Metric classification
    metric_type = models.CharField(
        max_length=20,
        choices=[
            ('kpi', 'Key Performance Indicator'),
            ('kri', 'Key Risk Indicator'),
            ('kr', 'Key Result'),
            ('custom', 'Custom Metric'),
        ],
        db_index=True
    )
    
    # Metric identification
    metric_name = models.CharField(max_length=100, db_index=True)
    metric_category = models.CharField(max_length=50, db_index=True)
    metric_subcategory = models.CharField(max_length=50, blank=True)
    
    # Metric values
    value = models.DecimalField(max_digits=15, decimal_places=4)
    previous_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    target_value = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    
    # Change metrics
    change_percentage = models.FloatField(null=True, blank=True)
    change_direction = models.CharField(
        max_length=10,
        choices=[
            ('up', 'Up'),
            ('down', 'Down'),
            ('stable', 'Stable'),
        ],
        blank=True
    )
    
    # Time period
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    period_type = models.CharField(
        max_length=20,
        choices=[
            ('minute', 'Minute'),
            ('hour', 'Hour'),
            ('day', 'Day'),
            ('week', 'Week'),
            ('month', 'Month'),
            ('quarter', 'Quarter'),
            ('year', 'Year'),
        ]
    )
    
    # Context and metadata
    context = models.JSONField(default=dict, blank=True)
    dimensions = models.JSONField(default=dict, blank=True)  # e.g., {"segment": "premium", "region": "US"}
    
    # Alert thresholds
    warning_threshold = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    critical_threshold = models.DecimalField(max_digits=15, decimal_places=4, null=True, blank=True)
    is_alert_triggered = models.BooleanField(default=False)
    
    class Meta:
        indexes = [
            models.Index(fields=['metric_type', 'metric_name', 'created_at']),
            models.Index(fields=['period_start', 'period_end']),
            models.Index(fields=['is_alert_triggered']),
        ]

    def __str__(self):
        return f"{self.metric_name} - {self.value} - {self.period_type}"


class AIInsight(BaseAnalyticsModel):
    """Stores AI-generated insights and predictions"""
    
    # Insight classification
    insight_type = models.CharField(
        max_length=50,
        choices=[
            ('prediction', 'Prediction'),
            ('classification', 'Classification'),
            ('recommendation', 'Recommendation'),
            ('anomaly', 'Anomaly Detection'),
            ('sentiment', 'Sentiment Analysis'),
            ('clustering', 'User Clustering'),
            ('churn_risk', 'Churn Risk'),
            ('engagement', 'Engagement Analysis'),
            ('persona', 'User Persona'),
            ('optimization', 'Optimization Suggestion'),
        ],
        db_index=True
    )
    
    # Target entity
    target_type = models.CharField(max_length=50)  # user, event, payment, etc.
    target_id = models.CharField(max_length=100)
    
    # Insight content
    title = models.CharField(max_length=200)
    description = models.TextField()
    confidence_score = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    
    # AI model information
    model_name = models.CharField(max_length=100)
    model_version = models.CharField(max_length=50)
    input_features = models.JSONField(default=list, blank=True)
    output_data = models.JSONField(default=dict, blank=True)
    
    # Actionability
    is_actionable = models.BooleanField(default=False)
    suggested_actions = models.JSONField(default=list, blank=True)
    priority = models.CharField(
        max_length=20,
        choices=[
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('critical', 'Critical'),
        ],
        default='medium'
    )
    
    # Status and validation
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', 'Pending'),
            ('validated', 'Validated'),
            ('rejected', 'Rejected'),
            ('expired', 'Expired'),
        ],
        default='pending'
    )
    
    validated_at = models.DateTimeField(null=True, blank=True)
    validation_notes = models.TextField(blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['insight_type', 'target_type']),
            models.Index(fields=['confidence_score']),
            models.Index(fields=['priority', 'status']),
            models.Index(fields=['is_actionable']),
        ]

    def __str__(self):
        return f"{self.insight_type} - {self.title} - {self.confidence_score:.2f}"


class SystemLog(BaseAnalyticsModel):
    """Logs system-level events for performance analytics"""
    
    # System event classification
    log_level = models.CharField(
        max_length=20,
        choices=[
            ('debug', 'Debug'),
            ('info', 'Info'),
            ('warning', 'Warning'),
            ('error', 'Error'),
            ('critical', 'Critical'),
        ],
        db_index=True
    )
    
    # Event details
    component = models.CharField(max_length=100, db_index=True)  # api, database, cache, etc.
    operation = models.CharField(max_length=100, db_index=True)  # create, read, update, delete, etc.
    resource = models.CharField(max_length=200, blank=True)  # specific resource being accessed
    
    # Performance metrics
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    memory_usage_mb = models.FloatField(null=True, blank=True)
    cpu_usage_percent = models.FloatField(null=True, blank=True)
    
    # Error details
    error_code = models.CharField(max_length=50, blank=True)
    error_message = models.TextField(blank=True)
    stack_trace = models.TextField(blank=True)
    
    # Context
    request_id = models.CharField(max_length=100, blank=True)
    user_id = models.CharField(max_length=100, blank=True)
    session_id = models.CharField(max_length=100, blank=True)
    
    # Additional metadata
    metadata = models.JSONField(default=dict, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['log_level', 'created_at']),
            models.Index(fields=['component', 'operation']),
            models.Index(fields=['duration_ms']),
            models.Index(fields=['error_code']),
        ]

    def __str__(self):
        return f"{self.log_level} - {self.component} - {self.operation}"


class UserPersona(BaseAnalyticsModel):
    """AI-generated user behavioral personas"""
    
    # Persona identification
    persona_name = models.CharField(max_length=100, unique=True)
    persona_description = models.TextField()
    
    # Behavioral characteristics
    behavior_patterns = models.JSONField(default=dict, blank=True)
    engagement_preferences = models.JSONField(default=dict, blank=True)
    risk_factors = models.JSONField(default=dict, blank=True)
    
    # AI model information
    model_confidence = models.FloatField(
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    features_used = models.JSONField(default=list, blank=True)
    
    # Business impact
    conversion_rate = models.FloatField(null=True, blank=True)
    lifetime_value = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    churn_probability = models.FloatField(null=True, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['persona_name']),
            models.Index(fields=['model_confidence']),
        ]

    def __str__(self):
        return f"{self.persona_name} - {self.model_confidence:.2f}"


class UserBehaviorProfile(BaseAnalyticsModel):
    """Comprehensive user behavior profile"""
    
    user = models.OneToOneField(
        User, 
        on_delete=models.CASCADE, 
        related_name='behavior_profile'
    )
    
    # Behavioral metrics
    engagement_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    activity_frequency = models.CharField(
        max_length=20,
        choices=[
            ('very_low', 'Very Low'),
            ('low', 'Low'),
            ('medium', 'Medium'),
            ('high', 'High'),
            ('very_high', 'Very High'),
        ],
        default='medium'
    )
    
    # Persona assignment
    primary_persona = models.ForeignKey(
        UserPersona, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='primary_users'
    )
    secondary_personas = models.ManyToManyField(
        UserPersona, 
        blank=True,
        related_name='secondary_users'
    )
    
    # Predictive scores
    churn_risk_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    conversion_probability = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)]
    )
    lifetime_value_prediction = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    
    # Behavioral patterns
    preferred_event_types = models.JSONField(default=list, blank=True)
    preferred_times = models.JSONField(default=list, blank=True)
    preferred_locations = models.JSONField(default=list, blank=True)
    
    # Last analysis
    last_analysis_at = models.DateTimeField(null=True, blank=True)
    analysis_version = models.CharField(max_length=50, blank=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['engagement_score']),
            models.Index(fields=['churn_risk_score']),
            models.Index(fields=['conversion_probability']),
            models.Index(fields=['last_analysis_at']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.primary_persona or 'No Persona'} - {self.engagement_score:.2f}"