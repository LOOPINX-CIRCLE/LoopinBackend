"""
Analytics URL configuration
"""

from django.urls import path
from . import views

app_name = 'analytics'

urlpatterns = [
    # User analytics
    path('overview/', views.analytics_overview, name='analytics_overview'),
    
    # Admin analytics
    path('admin/overview/', views.admin_analytics_overview, name='admin_analytics_overview'),
    path('admin/categories/', views.event_category_analytics, name='event_category_analytics'),
    path('admin/revenue/', views.revenue_analytics, name='revenue_analytics'),
    path('admin/segments/', views.user_segment_analytics, name='user_segment_analytics'),
    path('admin/aggregate/', views.run_analytics_aggregation, name='run_analytics_aggregation'),
]
