"""
Analytics Dashboard Admin Views

Custom Django Admin views for the Analytics Dashboard.

"""

from django.contrib import admin
from django.contrib.admin import AdminSite
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import render
from django.urls import path
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_http_methods
from django.core.serializers.json import DjangoJSONEncoder
import json
import logging

from .services import (
    get_user_lifecycle_metrics,
    get_waitlist_metrics,
    get_host_metrics,
    get_live_events_analytics,
    get_completed_events_analytics,
    get_host_deep_analytics,
    get_payment_analytics,
)

logger = logging.getLogger(__name__)


def is_staff_user(user):
    """Check if user is staff (required for dashboard access)"""
    return user.is_authenticated and user.is_staff


def staff_required(view_func):
    """Decorator that returns 403 Forbidden for non-staff users"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return HttpResponseForbidden("Authentication required")
        if not request.user.is_staff:
            return HttpResponseForbidden("Staff access required")
        return view_func(request, *args, **kwargs)
    return wrapper


@staff_required
def custom_admin_index_view(request, extra_context=None):
    """
    Custom admin index view that includes analytics dashboard link.
    This replaces the default admin index view.
    """
    # Call the original index method to get all proper context
    # This ensures we have all required context variables like log_entries, app_list, etc.
    original_response = _original_index(request, extra_context)
    
    # If it's a TemplateResponse, we can modify the context and template
    if hasattr(original_response, 'context_data'):
        # Add our dashboard context variables (not strictly needed since template doesn't check them)
        original_response.context_data['show_analytics_dashboard'] = True
        original_response.context_data['analytics_dashboard_url'] = '/django/admin/dashboard/'
        
        # CRITICAL: Django's template loader finds templates in INSTALLED_APPS order
        # Since django.contrib.admin comes before analytics, get_template() finds the default template first
        # Solution: Use select_template with explicit paths, or load our template directly
        from django.template.loader import select_template
        from django.template.response import TemplateResponse
        from pathlib import Path
        
        try:
            # Try to load our custom template explicitly by using select_template
            # with a list that prioritizes our app's template
            # First, try to find our template by checking if it exists
            analytics_template_path = Path(__file__).parent / 'templates' / 'admin' / 'index.html'
            
            if analytics_template_path.exists():
                # Use select_template with explicit template names
                # This will search in order and return the first match
                # We specify 'analytics/admin/index.html' first to prioritize it
                try:
                    # Try loading with explicit app prefix
                    custom_template = select_template([
                        'analytics/admin/index.html',  # Try our app's template first
                        'admin/index.html',  # Fallback to default
                    ])
                    
                    template_origin = str(custom_template.origin) if hasattr(custom_template, 'origin') else ''
                    logger.info(f"✅ Template loaded via select_template: {template_origin}")
                    
                    # Check if we got our custom template
                    if 'analytics' in template_origin.lower():
                        # Success! We got our custom template
                        new_response = TemplateResponse(
                            request=request,
                            template=custom_template,
                            context=original_response.context_data,
                            using=None
                        )
                        logger.info("✅ Successfully using custom analytics admin index template")
                        return new_response
                    else:
                        logger.warning(f"⚠️  select_template still found default template: {template_origin}")
                except Exception as e:
                    logger.warning(f"⚠️  select_template failed: {e}")
            
            # If select_template didn't work, inject the banner HTML directly into the rendered response
            # This is a more reliable approach that doesn't depend on template loading order
            logger.info("⚠️  Using HTML injection method to add dashboard banner")
            
            # Render the original response first
            original_response.render()
            
            # Get the rendered HTML content
            rendered_html = original_response.content.decode('utf-8')
            
            # Create the dashboard banner HTML
            # Using inline styles to ensure visibility and proper positioning
            dashboard_banner = '''
<div id="analytics-dashboard-banner" style="margin: 20px 0; padding: 20px; background: linear-gradient(135deg, #417690 0%, #205067 100%); border-radius: 8px; box-shadow: 0 2px 8px rgba(0,0,0,0.15); width: 100%; box-sizing: border-box; position: relative; z-index: 10;">
    <h2 style="margin: 0 0 12px 0; color: white; font-size: 24px; font-weight: bold;">
        <a href="/django/admin/dashboard/" style="color: white; text-decoration: none; display: inline-flex; align-items: center; gap: 10px;">
            <span style="font-size: 28px; vertical-align: middle;">📊</span>
            <span style="vertical-align: middle;">Analytics Dashboard</span>
        </a>
    </h2>
    <p style="margin: 0 0 12px 0; color: #e0e0e0; font-size: 14px; line-height: 1.5;">
        View platform-wide KPIs, user lifecycle metrics, host analytics, and event performance.
    </p>
    <div style="margin-top: 12px;">
        <a href="/django/admin/dashboard/" style="display: inline-block; padding: 10px 20px; background: white; color: #417690; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 14px; transition: all 0.3s ease;">
            Open Dashboard →
        </a>
    </div>
</div>
'''
            
            # Inject the banner right after the opening of the content div
            # Django admin uses various structures, so we'll try multiple insertion points
            import re
            banner_injected = False
            
            # Try multiple insertion points in order of preference
            insertion_patterns = [
                # Pattern 1: <div id="content">
                (r'(<div[^>]*id="content"[^>]*>)', 'id="content"'),
                # Pattern 2: <div class="content">
                (r'(<div[^>]*class="[^"]*content[^"]*"[^>]*>)', 'class="content"'),
                # Pattern 3: <div id="content-main">
                (r'(<div[^>]*id="content-main"[^>]*>)', 'id="content-main"'),
                # Pattern 4: After <h1> (admin page title)
                (r'(</h1>)', 'after </h1>'),
                # Pattern 5: After the first <div> with class containing "content"
                (r'(<div[^>]*class="[^"]*content[^"]*"[^>]*>)', 'class with content'),
            ]
            
            for pattern, description in insertion_patterns:
                match = re.search(pattern, rendered_html, re.IGNORECASE)
                if match:
                    # Inject the banner right after the matched element
                    insert_pos = match.end()
                    rendered_html = (
                        rendered_html[:insert_pos] + 
                        dashboard_banner + 
                        rendered_html[insert_pos:]
                    )
                    logger.info(f"✅ Injected banner after {description} at position {insert_pos}")
                    banner_injected = True
                    break
            
            # If none of the patterns matched, try a more aggressive approach
            if not banner_injected:
                # Look for the main content area by finding the first significant div after the header
                # This is a fallback that should work in most cases
                header_end = rendered_html.find('</header>')
                if header_end == -1:
                    header_end = rendered_html.find('</div>', rendered_html.find('<div id="header"'))
                
                if header_end > 0:
                    # Find the next <div> after the header
                    next_div = rendered_html.find('<div', header_end)
                    if next_div > 0:
                        # Find the end of that div tag
                        div_end = rendered_html.find('>', next_div)
                        if div_end > 0:
                            rendered_html = (
                                rendered_html[:div_end + 1] + 
                                dashboard_banner + 
                                rendered_html[div_end + 1:]
                            )
                            logger.info(f"✅ Injected banner after header at position {div_end + 1}")
                            banner_injected = True
            
            if not banner_injected:
                logger.warning("⚠️  Could not find insertion point for dashboard banner")
                # Last resort: inject at the very beginning of the body
                body_start = rendered_html.find('<body')
                if body_start > 0:
                    body_tag_end = rendered_html.find('>', body_start) + 1
                    rendered_html = (
                        rendered_html[:body_tag_end] + 
                        dashboard_banner + 
                        rendered_html[body_tag_end:]
                    )
                    logger.info("✅ Injected banner at body start as last resort")
            
            # Verify the banner was injected by checking if it's in the HTML
            if 'analytics-dashboard-banner' in rendered_html:
                logger.info("✅ Banner HTML confirmed in response content")
            else:
                logger.warning("⚠️  Banner HTML not found in response - injection may have failed")
            
            # Create a new HttpResponse with the modified content
            from django.http import HttpResponse
            response = HttpResponse(rendered_html, content_type=original_response.get('Content-Type', 'text/html'))
            response.status_code = original_response.status_code
            
            # Copy headers from original response
            for header, value in original_response.items():
                if header.lower() != 'content-length':  # Don't copy content-length as it will be wrong
                    response[header] = value
            
            logger.info(f"✅ Successfully injected dashboard banner into response (response size: {len(rendered_html)} bytes)")
            return response
            
        except Exception as e:
            logger.error(f"❌ Failed to load custom admin index template: {e}", exc_info=True)
            # Fall back to original response if template loading fails
            return original_response
    
    return original_response


@staff_required
def analytics_dashboard_view(request):
    """
    Main analytics dashboard view.
    Renders the dashboard template with all KPIs.
    """
    period = request.GET.get('period', 'monthly')
    
    # Validate period
    if period not in ['weekly', 'monthly', 'yearly']:
        period = 'monthly'
    
    # Gather all metrics
    try:
        # Get pagination parameters
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        
        user_metrics = get_user_lifecycle_metrics(period=period, limit=100, offset=0)  # Trend data pagination
        waitlist_metrics = get_waitlist_metrics(period=period, limit=100, offset=0)  # Trend data pagination
        host_metrics = get_host_metrics(period=period, limit=100, offset=0)  # Trend data pagination
        live_events = get_live_events_analytics(period=period, limit=limit, offset=offset)
        
        # Completed events filters
        paid_only = request.GET.get('paid_only', 'false').lower() == 'true'
        free_only = request.GET.get('free_only', 'false').lower() == 'true'
        completed_events = get_completed_events_analytics(
            paid_only=paid_only,
            free_only=free_only,
            limit=limit,
            offset=offset
        )
        
        # Host deep analytics (optional - can be loaded on demand)
        host_id = request.GET.get('host_id')
        host_analytics = get_host_deep_analytics(
            host_id=int(host_id) if host_id else None,
            limit=limit,
            offset=offset
        )
        
        # Payment analytics
        payment_analytics = get_payment_analytics(period=period)
        
    except Exception as e:
        logger.error(f"Error loading analytics dashboard: {e}", exc_info=True)
        # Return empty metrics on error
        user_metrics = {
            'total_users': 0,
            'active_users': 0,
            'waitlisted_users': 0,
            'approval_rate': 0.0,
            'trend': [],
            'pagination': {'limit': 100, 'offset': 0, 'total': 0, 'has_more': False},
        }
        waitlist_metrics = {
            'total_waitlisted': 0,
            'approval_rate': 0.0,
            'waitlist_promotion': {
                'users_scheduled_for_promotion': 0,
                'users_promoting_soon': 0,
                'avg_expected_duration_hours': 0.0,
                'promotion_window_min_hours': 3.5,
                'promotion_window_max_hours': 4.0,
            },
            'trend': [],
            'pagination': {'limit': 100, 'offset': 0, 'total': 0, 'has_more': False},
        }
        host_metrics = {
            'total_hosts': 0,
            'conversion_rate': 0.0,
            'new_hosts': [],
            'pagination': {'limit': 100, 'offset': 0, 'total': 0, 'has_more': False},
        }
        live_events = {
            'running_events': 0,
            'events': [],
            'trend': [],
            'pagination': {'limit': 50, 'offset': 0, 'total': 0, 'has_more': False},
        }
        completed_events = {
            'completed_events': [],
            'pagination': {'limit': 50, 'offset': 0, 'total': 0, 'has_more': False},
        }
        host_analytics = {
            'hosts': [],
            'total_hosts_analyzed': 0,
            'pagination': {'limit': 50, 'offset': 0, 'total': 0, 'has_more': False},
        }
        payment_analytics = {
            'total_orders': 0,
            'successful': 0,
            'failed': 0,
            'retry_attempts': 0,
            'created_pending': 0,
            'refunded': 0,
            'cancelled': 0,
            'expired': 0,
            'success_rate': 0.0,
            'failure_rate': 0.0,
            'retry_rate': 0.0,
            'chart_data': {'labels': [], 'data': [], 'colors': []},
            'status_breakdown': [],
            'final_vs_retry': {},
            'trend': [],
            'period': period,
        }
    
    # Serialize data for JavaScript charts
    context = {
        'user_metrics': user_metrics,
        'waitlist_metrics': waitlist_metrics,
        'host_metrics': host_metrics,
        'live_events': live_events,
        'completed_events': completed_events,
        'host_analytics': host_analytics,
        'current_period': period,
        'paid_only': paid_only,
        'free_only': free_only,
        'host_id': host_id,
        # JSON serialized data for JavaScript
        'user_trend_json': json.dumps(user_metrics.get('trend', []), cls=DjangoJSONEncoder),
        'waitlist_trend_json': json.dumps(waitlist_metrics.get('trend', []), cls=DjangoJSONEncoder),
        'hosts_trend_json': json.dumps(host_metrics.get('new_hosts', []), cls=DjangoJSONEncoder),
        'live_events_trend_json': json.dumps(live_events.get('trend', []), cls=DjangoJSONEncoder),
    }
    
    return render(request, 'admin/analytics/dashboard.html', context)


@require_http_methods(["GET"])
@staff_required
def analytics_api_users(request):
    """
    API endpoint: /admin/dashboard/api/users
    Returns user lifecycle metrics.
    """
    period = request.GET.get('period', 'monthly')
    if period not in ['weekly', 'monthly', 'yearly']:
        period = 'monthly'
    
    try:
        limit = int(request.GET.get('limit', 100))
        offset = int(request.GET.get('offset', 0))
        data = get_user_lifecycle_metrics(period=period, limit=limit, offset=offset)
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"Error in users API: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
@staff_required
def analytics_api_events(request):
    """
    API endpoint: /admin/dashboard/api/events
    Returns events analytics (live and completed).
    """
    period = request.GET.get('period', 'monthly')
    event_type = request.GET.get('type', 'live')  # 'live' or 'completed'
    
    if period not in ['weekly', 'monthly', 'yearly']:
        period = 'monthly'
    
    try:
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        if event_type == 'live':
            data = get_live_events_analytics(period=period, limit=limit, offset=offset)
        elif event_type == 'completed':
            paid_only = request.GET.get('paid_only', 'false').lower() == 'true'
            free_only = request.GET.get('free_only', 'false').lower() == 'true'
            data = get_completed_events_analytics(paid_only=paid_only, free_only=free_only, limit=limit, offset=offset)
        else:
            return JsonResponse({'error': 'Invalid event type. Use "live" or "completed"'}, status=400)
        
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"Error in events API: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


@require_http_methods(["GET"])
@staff_required
def analytics_api_hosts(request):
    """
    API endpoint: /admin/dashboard/api/hosts
    Returns host metrics and deep analytics.
    """
    period = request.GET.get('period', 'monthly')
    host_id = request.GET.get('host_id')
    
    if period not in ['weekly', 'monthly', 'yearly']:
        period = 'monthly'
    
    try:
        limit = int(request.GET.get('limit', 50))
        offset = int(request.GET.get('offset', 0))
        # Get host metrics
        host_metrics = get_host_metrics(period=period, limit=limit, offset=offset)
        
        # Get deep analytics if host_id provided, otherwise all hosts
        host_analytics = get_host_deep_analytics(
            host_id=int(host_id) if host_id else None,
            limit=limit,
            offset=offset
        )
        
        data = {
            **host_metrics,
            'hosts': host_analytics.get('hosts', []),
        }
        
        return JsonResponse(data, safe=False)
    except Exception as e:
        logger.error(f"Error in hosts API: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# Legacy endpoint for backward compatibility
@require_http_methods(["GET"])
@staff_required
def analytics_api_view(request):
    """
    Legacy API endpoint for AJAX requests (backward compatibility).
    Use specific endpoints: /api/users, /api/events, /api/hosts
    """
    period = request.GET.get('period', 'monthly')
    metric_type = request.GET.get('metric_type', 'user_lifecycle')
    
    if period not in ['weekly', 'monthly', 'yearly']:
        period = 'monthly'
    
    try:
        if metric_type == 'user_lifecycle':
            data = get_user_lifecycle_metrics(period=period)
        elif metric_type == 'waitlist':
            data = get_waitlist_metrics(period=period)
        elif metric_type == 'hosts':
            data = get_host_metrics(period=period)
        elif metric_type == 'live_events':
            data = get_live_events_analytics(period=period)
        elif metric_type == 'completed_events':
            paid_only = request.GET.get('paid_only', 'false').lower() == 'true'
            free_only = request.GET.get('free_only', 'false').lower() == 'true'
            data = get_completed_events_analytics(paid_only=paid_only, free_only=free_only)
        elif metric_type == 'host_deep':
            host_id = request.GET.get('host_id')
            data = get_host_deep_analytics(host_id=int(host_id) if host_id else None)
        else:
            return JsonResponse({'error': 'Invalid metric_type'}, status=400)
        
        return JsonResponse(data, safe=False)
    
    except Exception as e:
        logger.error(f"Error in analytics API: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)


# Custom AdminSite to add dashboard URL
class AnalyticsAdminSite(AdminSite):
    """Custom admin site with analytics dashboard"""
    
    def get_urls(self):
        """Add analytics dashboard URL to admin URLs"""
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', AnalyticsDashboardView(), name='analytics_dashboard'),
            path('dashboard/api/', analytics_api_view, name='analytics_api'),
        ]
        return custom_urls + urls


# Create custom admin site instance
# Note: We'll integrate this into the main admin site instead of replacing it
# by overriding admin.site.get_urls() in a different way

# Store original index method globally so custom_admin_index_view can access it
_original_index = None

# Instead, let's patch the default admin site
def patch_admin_site():
    """Patch the default admin site to add analytics dashboard"""
    global _original_index
    original_get_urls = admin.site.get_urls
    _original_index = admin.site.index

    def get_urls_with_dashboard(self):
        """Add dashboard URLs to admin site"""
        urls = original_get_urls()
        custom_urls = [
            path('dashboard/', analytics_dashboard_view, name='analytics_dashboard'),
            # Specific API endpoints as per spec
            path('dashboard/api/users', analytics_api_users, name='analytics_api_users'),
            path('dashboard/api/events', analytics_api_events, name='analytics_api_events'),
            path('dashboard/api/hosts', analytics_api_hosts, name='analytics_api_hosts'),
            # Legacy endpoint for backward compatibility
            path('dashboard/api/', analytics_api_view, name='analytics_api'),
        ]
        # Prepend custom URLs so they take precedence
        return custom_urls + urls
    
    def index_with_dashboard(self, request, extra_context=None):
        """Override admin index view to use our custom view"""
        return custom_admin_index_view(request, extra_context)
    
    admin.site.get_urls = get_urls_with_dashboard.__get__(admin.site, AdminSite)
    admin.site.index = index_with_dashboard.__get__(admin.site, AdminSite)
    # Set custom admin index template
    admin.site.index_template = 'admin/index.html'


# Apply the patch when module is imported
patch_admin_site()
