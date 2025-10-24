"""
Celery configuration for analytics processing.

This module configures Celery for async analytics tasks including
AI processing, metrics calculation, and data aggregation.
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loopin_backend.settings')

app = Celery('loopin_backend')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Celery Beat configuration for periodic tasks
app.conf.beat_schedule = {
    'process-daily-metrics': {
        'task': 'analytics.tasks.process_daily_metrics_calculation',
        'schedule': 60.0 * 60.0,  # Every hour
    },
    'generate-user-insights': {
        'task': 'analytics.tasks.generate_predictive_insights',
        'schedule': 60.0 * 60.0 * 6,  # Every 6 hours
    },
    'detect-anomalies': {
        'task': 'analytics.tasks.detect_anomalies_batch',
        'schedule': 60.0 * 30,  # Every 30 minutes
    },
    'cleanup-analytics-data': {
        'task': 'analytics.tasks.cleanup_old_analytics_data',
        'schedule': 60.0 * 60.0 * 24,  # Daily
    },
    'generate-daily-summary': {
        'task': 'analytics.tasks.generate_daily_insights_summary',
        'schedule': 60.0 * 60.0 * 24,  # Daily
    },
}

# Task routing
app.conf.task_routes = {
    'analytics.tasks.*': {'queue': 'analytics'},
    'analytics.tasks.process_daily_metrics_calculation': {'queue': 'metrics'},
    'analytics.tasks.generate_user_behavior_insights': {'queue': 'ai_processing'},
    'analytics.tasks.perform_user_clustering': {'queue': 'ai_processing'},
    'analytics.tasks.generate_predictive_insights': {'queue': 'ai_processing'},
    'analytics.tasks.detect_anomalies_batch': {'queue': 'anomaly_detection'},
}

# Task time limits
app.conf.task_time_limit = 300  # 5 minutes
app.conf.task_soft_time_limit = 240  # 4 minutes

# Worker configuration
app.conf.worker_prefetch_multiplier = 1
app.conf.worker_max_tasks_per_child = 1000

# Result backend configuration
app.conf.result_expires = 3600  # 1 hour

# Error handling
app.conf.task_acks_late = True
app.conf.worker_disable_rate_limits = False

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')
