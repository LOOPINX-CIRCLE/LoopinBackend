# Analytics Intelligence Layer Documentation

## 🧠 Overview

The Analytics Intelligence Layer is a comprehensive, AI-driven analytics system designed to be the brain of the Loopin platform. It combines behavioral analytics, business intelligence, and AI-driven psychological insights to enable data-driven decision making, automation, and growth optimization.

## 🏗️ Architecture

### Core Components

1. **Data Collection Layer**
   - Custom Django middleware for comprehensive request tracking
   - Django signals for automatic event capture
   - PostHog integration for real-time analytics

2. **AI Services Layer**
   - Sentiment analysis using multiple NLP libraries
   - User behavior analysis and persona generation
   - Predictive analytics and recommendation engine
   - Anomaly detection and clustering

3. **Business Intelligence Layer**
   - KPI/KRI/KR computation system
   - Real-time metrics calculation
   - Alert system with configurable thresholds

4. **Async Processing Layer**
   - Celery for background task processing
   - Redis for task queuing and caching
   - Batch processing for large-scale analytics

## 📊 Data Models

### BaseAnalyticsModel
All analytics models inherit from this base class providing:
- UUID for unique identification
- Source tracking (API, signal, manual, AI-generated)
- Data lineage with parent-child relationships
- Retention policies and archival
- Timestamps (created_at, updated_at)

### Core Models

#### UserEvent
Captures all user interactions:
```python
- user: ForeignKey to User
- session_id: Session tracking
- event_type: Classification (page_view, api_call, user_action, etc.)
- event_name: Specific event identifier
- metadata: JSON field for additional context
- sentiment_score: AI-analyzed sentiment (-1 to 1)
- engagement_level: Calculated engagement (low, medium, high, very_high)
- revenue_impact: Financial impact of the event
```

#### BusinessMetric
Stores computed KPIs, KRIs, and KRs:
```python
- metric_type: kpi, kri, kr, custom
- metric_name: Unique metric identifier
- value: Current metric value
- previous_value: Previous period value
- change_percentage: Percentage change
- warning_threshold: Alert threshold
- critical_threshold: Critical alert threshold
```

#### AIInsight
Stores AI-generated insights:
```python
- insight_type: prediction, classification, recommendation, anomaly, etc.
- target_type: user, event, payment, etc.
- confidence_score: AI confidence (0-1)
- is_actionable: Whether insight can trigger actions
- suggested_actions: List of recommended actions
- priority: low, medium, high, critical
```

#### UserBehaviorProfile
Comprehensive user behavior analysis:
```python
- engagement_score: Overall engagement (0-1)
- churn_risk_score: Predicted churn probability (0-1)
- conversion_probability: Likelihood to convert (0-1)
- primary_persona: Assigned behavioral persona
- preferred_event_types: User preferences
- last_analysis_at: Last analysis timestamp
```

## 🔄 Data Collection

### Middleware Integration

The `AnalyticsMiddleware` automatically captures:
- All HTTP requests and responses
- Response times and status codes
- User agent and device information
- IP addresses and referrers
- Session tracking
- Sentiment analysis of content

### Signal Handlers

Automatic event tracking via Django signals:
- User login/logout events
- Event creation and management
- Payment processing
- Attendance tracking
- Profile updates
- OTP verification

### PostHog Integration

All events are automatically sent to PostHog for:
- Real-time dashboards
- Funnel analysis
- Cohort analysis
- A/B testing
- Feature flags

## 🤖 AI Services

### SentimentAnalysisService
- Multi-method sentiment analysis (TextBlob, VADER, OpenAI)
- Confidence scoring
- Emotional intensity detection
- Real-time text processing

### UserBehaviorAnalysisService
- Comprehensive behavior pattern analysis
- Engagement scoring
- Activity pattern recognition
- Risk factor identification
- Persona suggestion

### PredictiveAnalyticsService
- Event attendance prediction
- Anomaly detection using statistical methods
- Personalized recommendations
- Churn risk assessment

### UserClusteringService
- K-means clustering for user segmentation
- Behavioral characteristic analysis
- Silhouette scoring for cluster quality
- Dynamic persona assignment

## 📈 KPI/KRI/KR System

### Key Performance Indicators (KPIs)
- **Daily Active Users (DAU)**: Unique active users per day
- **Retention Rate**: 7-day and 30-day user retention
- **Average Session Length**: Mean session duration in minutes
- **Conversion Rate**: View → Join → Attend funnel
- **Revenue Per User (RPU)**: Average revenue per active user

### Key Risk Indicators (KRIs)
- **Payment Failure Rate**: Percentage of failed payments
- **OTP Verification Failure Rate**: Authentication failure rate
- **Host Cancellation Rate**: Event cancellation frequency
- **High Churn Probability**: Users with >70% churn risk

### Key Results (KRs)
- **Monthly Event Creation Growth**: Month-over-month growth
- **Ticket Purchase Success Ratio**: Successful payment rate
- **User Verification Completion Rate**: Profile completion percentage

## ⚡ Async Processing

### Celery Tasks

#### Event Processing
- `process_user_events_batch`: Batch process events for AI analysis
- `generate_user_behavior_insights`: Generate comprehensive user insights
- `process_daily_metrics_calculation`: Calculate all daily metrics

#### AI Processing
- `perform_user_clustering`: Cluster users by behavior
- `generate_predictive_insights`: Generate predictions and recommendations
- `detect_anomalies_batch`: Detect anomalies in metrics

#### Maintenance
- `cleanup_old_analytics_data`: Archive old data based on retention policies
- `generate_daily_insights_summary`: Create daily summaries for stakeholders

### Task Scheduling
- **Hourly**: Daily metrics calculation
- **Every 6 hours**: User insights generation
- **Every 30 minutes**: Anomaly detection
- **Daily**: Data cleanup and summary generation

## 🔐 Privacy & Security

### Data Protection
- PII anonymization before external transmission
- Encrypted sensitive payloads
- Configurable retention policies
- GDPR-compliant data handling

### Access Control
- Role-based access to analytics data
- Admin-only endpoints for sensitive operations
- API authentication via JWT tokens
- Request filtering for internal endpoints

### Performance Optimization
- Batch inserts for write efficiency
- Redis caching for frequent queries
- Database indexing for fast lookups
- Async processing to prevent request blocking

## 🚀 API Endpoints

### Analytics Overview
- `GET /api/analytics/overview`: Comprehensive analytics dashboard
- `POST /api/analytics/user-behavior`: User behavior analysis
- `GET /api/analytics/health`: System health check

### Metrics
- `POST /api/analytics/metrics/calculate`: Calculate business metrics
- `GET /api/analytics/metrics/{metric_name}`: Historical metric data

### AI Insights
- `POST /api/analytics/insights`: Get AI-generated insights
- `POST /api/analytics/insights/generate`: Generate new insights
- `POST /api/analytics/sentiment`: Analyze text sentiment

### Advanced Analytics
- `POST /api/analytics/clustering`: Perform user clustering
- `POST /api/analytics/events/track`: Track custom events
- `GET /api/analytics/export/events`: Export events data

## 📊 Monitoring & Alerts

### Real-time Monitoring
- System health checks
- Performance metrics tracking
- Error rate monitoring
- Resource utilization tracking

### Alert System
- Configurable thresholds for all metrics
- Multi-level alerts (warning, critical)
- Automated alert triggering
- Integration with notification systems

### Dashboards
- Django Admin interface for analytics data
- PostHog dashboards for real-time visualization
- Custom metrics visualization
- AI insights overview

## 🔧 Configuration

### Environment Variables
```env
# Analytics
ANALYTICS_ENABLED=true
ANALYTICS_RETENTION_DAYS=365
ANALYTICS_BATCH_SIZE=1000

# AI Services
OPENAI_API_KEY=your-openai-key
AI_SERVICES_ENABLED=true

# PostHog
POSTHOG_API_KEY=your-posthog-key
POSTHOG_HOST=https://us.i.posthog.com

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Django Settings
- Analytics middleware configuration
- PostHog integration settings
- Celery task scheduling
- AI services configuration

## 📚 Usage Examples

### Track Custom Event
```python
from analytics.models import UserEvent

# Track a custom event
UserEvent.objects.create(
    user=request.user,
    event_type='user_action',
    event_name='custom_button_click',
    action='click',
    metadata={'button_id': 'signup_cta', 'page': 'landing'}
)
```

### Generate User Insights
```python
from analytics.tasks import generate_user_behavior_insights

# Queue user analysis
generate_user_behavior_insights.delay(user_id=123)
```

### Calculate Metrics
```python
from analytics.metrics import MetricsProcessor

# Process daily metrics
results = MetricsProcessor.process_daily_metrics()
```

### Analyze Sentiment
```python
from analytics.ai_services import SentimentAnalysisService

service = SentimentAnalysisService()
result = service.analyze_text_sentiment("I love this event!")
# Returns: {'sentiment': 'positive', 'score': 0.8, 'confidence': 0.9}
```

## 🎯 Business Impact

### Growth Optimization
- User behavior insights for product improvements
- Conversion funnel analysis for optimization
- Personalized recommendations for engagement
- Churn prediction for retention strategies

### Risk Management
- Real-time anomaly detection
- Payment failure monitoring
- Authentication security tracking
- System performance monitoring

### Decision Making
- Data-driven product decisions
- AI-assisted user segmentation
- Predictive analytics for planning
- Comprehensive business intelligence

## 🔮 Future Enhancements

### Advanced AI Features
- Deep learning models for behavior prediction
- Natural language processing for content analysis
- Computer vision for image sentiment analysis
- Reinforcement learning for recommendation optimization

### Real-time Analytics
- Stream processing with Apache Kafka
- Real-time dashboards with WebSocket updates
- Live user journey tracking
- Instant anomaly detection

### Advanced Personalization
- Dynamic user personas
- Real-time recommendation engine
- Behavioral trigger automation
- Contextual user experiences

## 🛠️ Development & Maintenance

### Testing
- Unit tests for all analytics models
- Integration tests for AI services
- Performance tests for async processing
- End-to-end tests for API endpoints

### Monitoring
- Application performance monitoring
- Database query optimization
- Task queue monitoring
- Error tracking and alerting

### Maintenance
- Regular data cleanup and archival
- Model performance monitoring
- System health checks
- Documentation updates

---

This analytics intelligence layer transforms the Loopin platform into a data-driven, AI-powered system capable of understanding user behavior, predicting outcomes, and optimizing for growth while maintaining privacy and security standards.
