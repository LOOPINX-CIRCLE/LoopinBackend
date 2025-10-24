"""
Analytics admin interface for Django admin
"""

from django.contrib import admin
from django.db.models import Count, Sum, Avg
from django.utils.html import format_html
from .models import (
    DailyEventMetrics, UserEngagementMetrics, EventCategoryMetrics,
    VenueMetrics, ConversionFunnelMetrics, RevenueMetrics, UserSegmentMetrics
)


@admin.register(DailyEventMetrics)
class DailyEventMetricsAdmin(admin.ModelAdmin):
    list_display = ['date', 'event', 'total_requests', 'approved_requests', 'total_attendees', 'total_revenue']
    list_filter = ['date', 'event__status', 'event__is_public']
    search_fields = ['event__title', 'event__host__username']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('event', 'event__host')


@admin.register(UserEngagementMetrics)
class UserEngagementMetricsAdmin(admin.ModelAdmin):
    list_display = ['date', 'user', 'events_requested', 'events_attended', 'events_hosted', 'request_to_attendance_rate']
    list_filter = ['date', 'user__is_active']
    search_fields = ['user__username', 'user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('user')


@admin.register(EventCategoryMetrics)
class EventCategoryMetricsAdmin(admin.ModelAdmin):
    list_display = ['date', 'interest', 'total_events', 'total_requests', 'total_attendees', 'total_revenue', 'average_attendance_rate']
    list_filter = ['date', 'interest__is_active']
    search_fields = ['interest__name']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('interest')


@admin.register(VenueMetrics)
class VenueMetricsAdmin(admin.ModelAdmin):
    list_display = ['date', 'venue', 'total_events', 'total_attendees', 'capacity_utilization_rate', 'total_revenue']
    list_filter = ['date', 'venue__venue_type', 'venue__is_active']
    search_fields = ['venue__name', 'venue__city']
    readonly_fields = ['created_at', 'updated_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('venue')


@admin.register(ConversionFunnelMetrics)
class ConversionFunnelMetricsAdmin(admin.ModelAdmin):
    list_display = ['date', 'users_registered', 'users_attended', 'overall_conversion_rate', 'attendance_rate']
    list_filter = ['date']
    readonly_fields = ['created_at', 'updated_at']
    
    def overall_conversion_rate(self, obj):
        if obj.users_registered > 0:
            rate = (obj.users_attended / obj.users_registered) * 100
            color = 'green' if rate > 10 else 'orange' if rate > 5 else 'red'
            return format_html('<span style="color: {};">{:.1f}%</span>', color, rate)
        return '0%'
    overall_conversion_rate.short_description = 'Overall Conversion Rate'


@admin.register(RevenueMetrics)
class RevenueMetricsAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_revenue', 'net_revenue', 'total_transactions', 'payment_success_rate', 'average_transaction_value']
    list_filter = ['date']
    readonly_fields = ['created_at', 'updated_at']
    
    def payment_success_rate(self, obj):
        if obj.total_transactions > 0:
            rate = (obj.successful_transactions / obj.total_transactions) * 100
            color = 'green' if rate > 90 else 'orange' if rate > 80 else 'red'
            return format_html('<span style="color: {};">{:.1f}%</span>', color, rate)
        return '0%'
    payment_success_rate.short_description = 'Payment Success Rate'


@admin.register(UserSegmentMetrics)
class UserSegmentMetricsAdmin(admin.ModelAdmin):
    list_display = ['date', 'segment_type', 'segment_value', 'total_users', 'active_users', 'total_revenue']
    list_filter = ['date', 'segment_type']
    search_fields = ['segment_value']
    readonly_fields = ['created_at', 'updated_at']
