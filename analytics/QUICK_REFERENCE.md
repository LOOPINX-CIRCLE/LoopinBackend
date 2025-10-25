# 📋 Analytics Quick Reference Guide

## 🚀 Quick Start

### **For Developers**
```bash
# Install dependencies
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Start Celery worker
celery -A loopin_backend worker --loglevel=info

# Start Celery beat (scheduler)
celery -A loopin_backend beat --loglevel=info

# Test analytics
python manage.py test analytics
```

### **For Business Users**
1. **Access Analytics**: Go to `/api/analytics/overview`
2. **View Insights**: Check `/api/analytics/insights`
3. **Monitor Health**: Visit `/api/analytics/health`
4. **Export Data**: Use `/api/analytics/export/events`

---

## 📊 Common Operations

### **Track Custom Events**
```python
from analytics.models import UserEvent

# Track a button click
UserEvent.objects.create(
    user=request.user,
    event_type='user_action',
    event_name='button_clicked',
    action='click',
    metadata={'button_id': 'signup_cta', 'page': 'landing'}
)

# Track API call
UserEvent.objects.create(
    user=request.user,
    event_type='api_call',
    event_name='create_event',
    action='post',
    response_time_ms=250,
    status_code=201
)
```

### **Generate User Insights**
```python
from analytics.tasks import generate_user_behavior_insights

# Queue user analysis
generate_user_behavior_insights.delay(user_id=123)

# Check results
from analytics.models import UserBehaviorProfile, AIInsight
profile = UserBehaviorProfile.objects.get(user_id=123)
insights = AIInsight.objects.filter(target_id='123')
```

### **Calculate Metrics**
```python
from analytics.metrics import MetricsProcessor

# Calculate daily metrics
results = MetricsProcessor.process_daily_metrics()

# Check specific KPI
from analytics.models import BusinessMetric
dau = BusinessMetric.objects.filter(
    metric_name='daily_active_users',
    created_at__date=timezone.now().date()
).first()
```

### **Analyze Sentiment**
```python
from analytics.ai_services import SentimentAnalysisService

service = SentimentAnalysisService()
result = service.analyze_text_sentiment("I love this event!")

print(f"Sentiment: {result['sentiment']}")
print(f"Score: {result['score']}")
print(f"Confidence: {result['confidence']}")
```

---

## 🔧 Configuration

### **Environment Variables**
```env
# Required
ANALYTICS_ENABLED=true
POSTHOG_API_KEY=your-posthog-key
CELERY_BROKER_URL=redis://localhost:6379/0

# Optional
OPENAI_API_KEY=your-openai-key
ANALYTICS_RETENTION_DAYS=365
ANALYTICS_BATCH_SIZE=1000
```

### **Django Settings**
```python
# Add to INSTALLED_APPS
INSTALLED_APPS = [
    'analytics',
    'posthog',
]

# Add to MIDDLEWARE
MIDDLEWARE = [
    'analytics.middleware.AnalyticsMiddleware',
    'posthog.integrations.django.PosthogContextMiddleware',
]
```

---

## 📈 Key Metrics

### **KPIs (Key Performance Indicators)**
- **DAU**: Daily Active Users
- **Retention Rate**: 7-day and 30-day retention
- **Session Length**: Average session duration
- **Conversion Rate**: View → Join → Attend funnel
- **RPU**: Revenue Per User

### **KRIs (Key Risk Indicators)**
- **Payment Failure Rate**: Failed transaction percentage
- **OTP Failure Rate**: Authentication failure rate
- **Cancellation Rate**: Event cancellation frequency
- **Churn Risk**: Users likely to leave

### **KRs (Key Results)**
- **Event Growth**: Month-over-month event creation
- **Success Ratio**: Ticket purchase success rate
- **Verification Rate**: Profile completion percentage

---

## 🤖 AI Services

### **Available Services**
- **SentimentAnalysisService**: Text sentiment analysis
- **UserBehaviorAnalysisService**: User behavior patterns
- **PredictiveAnalyticsService**: Predictions and recommendations
- **UserClusteringService**: User segmentation

### **Common AI Operations**
```python
# Analyze user behavior
behavior_service = UserBehaviorAnalysisService()
analysis = behavior_service.analyze_user_behavior(user, days=30)

# Generate predictions
predictive_service = PredictiveAnalyticsService()
attendance_prob = predictive_service.predict_event_attendance(user, event_id)

# Detect anomalies
anomalies = predictive_service.detect_anomalies('payment_failure_rate')

# Cluster users
clustering_service = UserClusteringService()
clusters = clustering_service.cluster_users(n_clusters=5)
```

---

## 🚨 Troubleshooting

### **Common Issues**

#### **No Analytics Data**
```bash
# Check if analytics is enabled
python manage.py shell
>>> from django.conf import settings
>>> print(settings.ANALYTICS_ENABLED)

# Check middleware
>>> print(settings.MIDDLEWARE)
```

#### **AI Services Not Working**
```bash
# Check OpenAI API key
python manage.py shell
>>> import os
>>> print(bool(os.getenv('OPENAI_API_KEY')))

# Test sentiment analysis
>>> from analytics.ai_services import SentimentAnalysisService
>>> service = SentimentAnalysisService()
>>> result = service.analyze_text_sentiment("Test message")
```

#### **Celery Tasks Not Running**
```bash
# Check Celery worker
celery -A loopin_backend inspect active

# Check Redis connection
python manage.py shell
>>> from django.core.cache import cache
>>> cache.set('test', 'ok')
>>> print(cache.get('test'))
```

#### **Slow Performance**
```python
# Check database queries
from django.db import connection
print(len(connection.queries))

# Optimize queries
UserEvent.objects.select_related('user').filter(user_id=123)

# Use caching
from django.core.cache import cache
cache.set('key', 'value', 300)  # 5 minutes
```

---

## 📊 API Endpoints

### **Analytics Overview**
```http
GET /api/analytics/overview?days=7
Authorization: Bearer your-jwt-token
```

### **User Behavior**
```http
POST /api/analytics/user-behavior
Content-Type: application/json
Authorization: Bearer your-jwt-token

{
  "user_id": 123,
  "days": 30
}
```

### **Sentiment Analysis**
```http
POST /api/analytics/sentiment
Content-Type: application/json
Authorization: Bearer your-jwt-token

{
  "text": "I love this event!"
}
```

### **Custom Event Tracking**
```http
POST /api/analytics/events/track
Content-Type: application/json
Authorization: Bearer your-jwt-token

{
  "event_name": "button_clicked",
  "event_type": "user_action",
  "metadata": {
    "button_id": "signup_cta",
    "page": "landing"
  }
}
```

### **Health Check**
```http
GET /api/analytics/health
```

---

## 🔍 Monitoring

### **Health Checks**
```python
# Check system health
GET /api/analytics/health

# Detailed health check
GET /api/analytics/health/detailed

# Debug information (admin only)
GET /api/analytics/debug/info
```

### **Logs**
```bash
# View analytics logs
tail -f logs/analytics.log

# Check Celery logs
celery -A loopin_backend events

# Monitor Redis
redis-cli monitor
```

### **Metrics**
```python
# Check recent metrics
from analytics.models import BusinessMetric
recent_metrics = BusinessMetric.objects.filter(
    created_at__gte=timezone.now() - timedelta(hours=24)
)

# Check alerts
alerts = BusinessMetric.objects.filter(is_alert_triggered=True)
```

---

## 📚 Useful Commands

### **Django Management Commands**
```bash
# Run analytics tests
python manage.py test analytics

# Check analytics configuration
python manage.py shell
>>> from analytics.apps import AnalyticsConfig
>>> AnalyticsConfig.ready()

# Debug analytics
python manage.py debug_analytics --check-data --test-ai
```

### **Celery Commands**
```bash
# Start worker
celery -A loopin_backend worker --loglevel=info

# Start beat scheduler
celery -A loopin_backend beat --loglevel=info

# Monitor tasks
celery -A loopin_backend flower

# Inspect active tasks
celery -A loopin_backend inspect active

# Purge all tasks
celery -A loopin_backend purge
```

### **Database Commands**
```sql
-- Check analytics tables
SELECT table_name FROM information_schema.tables 
WHERE table_name LIKE 'analytics_%';

-- Check recent events
SELECT COUNT(*) FROM analytics_userevent 
WHERE created_at >= NOW() - INTERVAL '1 day';

-- Check metrics
SELECT metric_name, value, created_at 
FROM analytics_businessmetric 
ORDER BY created_at DESC LIMIT 10;
```

---

## 🎯 Best Practices

### **Event Tracking**
- Use consistent event names
- Include relevant metadata
- Avoid tracking sensitive data
- Use appropriate event types

### **Performance**
- Use batch operations for large datasets
- Implement proper caching
- Monitor database queries
- Use async processing for heavy operations

### **Privacy**
- Anonymize personal data
- Implement data retention policies
- Use encryption for sensitive data
- Regular privacy audits

### **Monitoring**
- Set up health checks
- Monitor key metrics
- Implement alerting
- Regular system maintenance

---

## 📞 Support

### **Documentation**
- [Main Documentation](README.md)
- [Technical Documentation](TECHNICAL_DOCS.md)
- [API Reference](api.py)

### **Contact**
- **Technical Issues**: dev-team@loopin.com
- **Analytics Questions**: analytics@loopin.com
- **Business Inquiries**: business@loopin.com

---

*This quick reference guide provides essential information for working with the analytics system. For detailed information, refer to the full documentation.*
