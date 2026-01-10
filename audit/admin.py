"""
Production-grade Django Admin configuration for Audit app.
CEO-level admin interface for security, compliance, and audit trail management.
"""
from django.contrib import admin
from django.db.models import Count, Q
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.utils.translation import gettext_lazy as _
import json

from .models import AuditLog, AuditLogSummary


# ============================================================================
# AUDIT LOG ADMIN
# ============================================================================

@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    """
    CEO-level admin interface for Audit Logs.
    
    Features:
    - Security-focused display
    - Severity-based filtering
    - Failed action highlighting
    - IP address and user agent tracking
    - Change tracking visualization
    - Export capabilities
    """
    
    list_display = (
        'created_at',
        'action_badge',
        'actor_display',
        'object_type',
        'object_link',
        'severity_badge',
        'success_badge',
        'ip_address_short',
        'has_changes_indicator',
    )
    list_filter = (
        'action',
        'object_type',
        'severity',
        'is_successful',
        ('created_at', admin.DateFieldListFilter),
    )
    search_fields = (
        'action',
        'object_type',
        'object_id',
        'object_uuid',
        'actor_user__username',
        'actor_user__email',
        'ip_address',
        'user_agent',
        'error_message',
        'payload',
    )
    readonly_fields = (
        'actor_user',
        'user',
        'action',
        'action_badge_display',
        'object_type',
        'object_id',
        'object_uuid',
        'payload_display',
        'old_values_display',
        'new_values_display',
        'ip_address',
        'user_agent',
        'session_key',
        'severity',
        'severity_badge_display',
        'is_successful',
        'success_badge_display',
        'error_message',
        'metadata_display',
        'created_at',
        'updated_at',
        'object_link_display',
        'change_diff_display',
    )
    fieldsets = (
        (_('Action Information'), {
            'fields': (
                'created_at',
                'action_badge_display',
                'actor_user',
                'user',
                'object_link_display',
            )
        }),
        (_('Object Reference'), {
            'fields': ('object_type', 'object_id', 'object_uuid'),
            'classes': ('collapse',)
        }),
        (_('Security & Tracking'), {
            'fields': (
                'severity_badge_display',
                'is_successful',
                'success_badge_display',
                'ip_address',
                'user_agent',
                'session_key',
            )
        }),
        (_('Change Tracking'), {
            'fields': (
                'change_diff_display',
                'old_values_display',
                'new_values_display',
            ),
            'description': 'Track what changed in this action'
        }),
        (_('Payload & Metadata'), {
            'fields': ('payload_display', 'metadata_display'),
            'classes': ('collapse',),
            'description': 'Complete snapshot of action data'
        }),
        (_('Error Information'), {
            'fields': ('error_message',),
            'classes': ('collapse',),
            'description': 'Error details if action failed'
        }),
        (_('Timestamps'), {
            'fields': ('updated_at',),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    save_on_top = True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('actor_user', 'user').order_by('-created_at')
    
    def action_badge(self, obj):
        """Display action with badge"""
        action_colors = {
            'create': '#4caf50',
            'update': '#2196f3',
            'delete': '#f44336',
            'login': '#ff9800',
            'logout': '#9e9e9e',
            'password_change': '#e91e63',
            'profile_update': '#00bcd4',
            'campaign_create': '#9c27b0',
            'campaign_execute': '#607d8b',
        }
        color = action_colors.get(obj.action, '#9e9e9e')
        return format_html(
            '<span style="background: {}; color: white; padding: 4px 10px; border-radius: 4px; font-size: 11px; font-weight: bold; text-transform: uppercase;">{}</span>',
            color,
            obj.get_action_display()
        )
    action_badge.short_description = "Action"
    action_badge.admin_order_field = 'action'
    
    def action_badge_display(self, obj):
        """Display action badge in detail view"""
        return self.action_badge(obj)
    action_badge_display.short_description = "Action"
    
    def actor_display(self, obj):
        """Display actor user"""
        user = obj.actor_user or obj.user
        if user:
            url = reverse('admin:auth_user_change', args=[user.pk])
            return format_html(
                '<a href="{}">{}</a>',
                url,
                user.username
            )
        return format_html('<span style="color: gray;">System</span>')
    actor_display.short_description = "Actor"
    actor_display.admin_order_field = 'actor_user__username'
    
    def object_link(self, obj):
        """Display object link if possible"""
        if not obj.object_type or not obj.object_id:
            return '-'
        
        # Try to generate admin URL based on object_type
        try:
            app_label, model_name = obj.object_type.split('.') if '.' in obj.object_type else (None, obj.object_type.lower())
            
            # Common model mappings
            url_mappings = {
                'paymentorder': ('payments', 'paymentorder'),
                'event': ('events', 'event'),
                'userprofile': ('users', 'userprofile'),
                'campaign': ('notifications', 'campaign'),
                'user': ('auth', 'user'),
            }
            
            if model_name.lower() in url_mappings:
                app, model = url_mappings[model_name.lower()]
                url = reverse(f'admin:{app}_{model}_change', args=[obj.object_id])
                return format_html(
                    '<a href="{}">{} #{}</a>',
                    url,
                    obj.object_type,
                    obj.object_id
                )
        except Exception:
            pass
        
        return format_html('<span>{}</span>', obj.object_type)
    object_link.short_description = "Object"
    
    def object_link_display(self, obj):
        """Display object link in detail view"""
        return self.object_link(obj)
    object_link_display.short_description = "Object"
    
    def severity_badge(self, obj):
        """Display severity badge"""
        colors = {
            'low': '#4caf50',
            'medium': '#ff9800',
            'high': '#f44336',
            'critical': '#e91e63',
        }
        color = colors.get(obj.severity, '#9e9e9e')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px; font-weight: bold;">{}</span>',
            color,
            obj.get_severity_display().upper()
        )
    severity_badge.short_description = "Severity"
    severity_badge.admin_order_field = 'severity'
    
    def severity_badge_display(self, obj):
        """Display severity badge in detail view"""
        return self.severity_badge(obj)
    severity_badge_display.short_description = "Severity"
    
    def success_badge(self, obj):
        """Display success/failure badge"""
        if not obj:
            return format_html('<span style="color: gray;">Not set</span>')
        if obj.is_successful:
            return format_html(
                '<span style="background: #4caf50; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px;">✓ Success</span>'
            )
        else:
            return format_html(
                '<span style="background: #f44336; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px;">✗ Failed</span>'
            )
    success_badge.short_description = "Status"
    success_badge.admin_order_field = 'is_successful'
    # Note: boolean = True removed - this returns HTML, not a boolean
    
    def success_badge_display(self, obj):
        """Display success badge in detail view"""
        return self.success_badge(obj)
    success_badge_display.short_description = "Status"
    
    def ip_address_short(self, obj):
        """Display IP address"""
        if obj.ip_address:
            return format_html('<code style="font-size: 11px;">{}</code>', obj.ip_address)
        return '-'
    ip_address_short.short_description = "IP Address"
    
    def has_changes_indicator(self, obj):
        """Indicator if log has field changes"""
        if not obj:
            return format_html('<span style="color: gray;">-</span>')
        has_changes = obj.has_changes
        return format_html(
            '<span style="color: {};">{}</span>',
            '#4caf50' if has_changes else '#9e9e9e',
            '✓' if has_changes else '-'
        )
    has_changes_indicator.short_description = "Changes"
    # Note: boolean = True removed - this returns HTML, not a boolean
    
    def payload_display(self, obj):
        """Display payload in readable format"""
        if not obj.payload:
            return format_html('<span style="color: gray;">No payload</span>')
        
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; max-height: 300px; overflow-y: auto; font-size: 11px;">{}</pre>',
            json.dumps(obj.payload, indent=2)
        )
    payload_display.short_description = "Payload"
    
    def old_values_display(self, obj):
        """Display old values"""
        if not obj.old_values:
            return format_html('<span style="color: gray;">No old values</span>')
        
        return format_html(
            '<pre style="background: #ffebee; padding: 10px; border-radius: 4px; max-height: 200px; overflow-y: auto; font-size: 11px;">{}</pre>',
            json.dumps(obj.old_values, indent=2)
        )
    old_values_display.short_description = "Old Values"
    
    def new_values_display(self, obj):
        """Display new values"""
        if not obj.new_values:
            return format_html('<span style="color: gray;">No new values</span>')
        
        return format_html(
            '<pre style="background: #e8f5e9; padding: 10px; border-radius: 4px; max-height: 200px; overflow-y: auto; font-size: 11px;">{}</pre>',
            json.dumps(obj.new_values, indent=2)
        )
    new_values_display.short_description = "New Values"
    
    def change_diff_display(self, obj):
        """Display change diff"""
        if not obj.has_changes:
            return format_html('<span style="color: gray;">No field changes tracked</span>')
        
        html = '<div style="background: #fff3cd; padding: 15px; border-radius: 4px; border-left: 4px solid #ff9800;">'
        html += '<h4 style="margin-top: 0;">Field Changes</h4>'
        html += '<table style="width: 100%; border-collapse: collapse; font-size: 12px;">'
        
        # Get all changed fields
        old_vals = obj.old_values or {}
        new_vals = obj.new_values or {}
        all_fields = set(old_vals.keys()) | set(new_vals.keys())
        
        for field in sorted(all_fields):
            old_val = old_vals.get(field, '<em>None</em>')
            new_val = new_vals.get(field, '<em>None</em>')
            
            html += format_html(
                '<tr style="border-bottom: 1px solid #ddd;">'
                '<td style="padding: 5px; font-weight: bold; width: 30%;">{}</td>'
                '<td style="padding: 5px; background: #ffebee; width: 35%;">{}</td>'
                '<td style="padding: 5px; text-align: center; width: 5%;">→</td>'
                '<td style="padding: 5px; background: #e8f5e9; width: 35%;">{}</td>'
                '</tr>',
                field,
                old_val if isinstance(old_val, str) else json.dumps(old_val),
                new_val if isinstance(new_val, str) else json.dumps(new_val)
            )
        
        html += '</table></div>'
        return format_html(html)
    change_diff_display.short_description = "Change Diff"
    
    def metadata_display(self, obj):
        """Display metadata"""
        if not obj.metadata:
            return format_html('<span style="color: gray;">No metadata</span>')
        
        return format_html(
            '<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; max-height: 200px; overflow-y: auto; font-size: 11px;">{}</pre>',
            json.dumps(obj.metadata, indent=2)
        )
    metadata_display.short_description = "Metadata"
    
    def has_add_permission(self, request):
        """Audit logs should not be created manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Audit logs are immutable"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete audit logs (for compliance)"""
        return request.user.is_superuser
    
    actions = ['export_selected', 'mark_critical']
    
    def export_selected(self, request, queryset):
        """Export selected audit logs (CSV format)"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="audit_logs_export.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Created At',
            'Action',
            'Actor',
            'Object Type',
            'Object ID',
            'Severity',
            'Success',
            'IP Address',
            'Error Message'
        ])
        
        for log in queryset:
            actor = (log.actor_user or log.user).username if (log.actor_user or log.user) else 'System'
            writer.writerow([
                log.created_at.isoformat(),
                log.action,
                actor,
                log.object_type,
                log.object_id,
                log.severity,
                'Yes' if log.is_successful else 'No',
                log.ip_address or '',
                log.error_message or ''
            ])
        
        self.message_user(request, f'✅ Exported {queryset.count()} audit log(s) to CSV.')
        return response
    export_selected.short_description = "Export selected to CSV"
    
    def mark_critical(self, request, queryset):
        """Mark selected logs as critical (use with caution)"""
        count = queryset.update(severity='critical')
        self.message_user(request, f'⚠️ {count} audit log(s) marked as critical.')
    mark_critical.short_description = "Mark as critical"


# ============================================================================
# AUDIT LOG SUMMARY ADMIN
# ============================================================================

@admin.register(AuditLogSummary)
class AuditLogSummaryAdmin(admin.ModelAdmin):
    """Admin for audit log summaries"""
    
    list_display = (
        'date',
        'user_link',
        'action_badge',
        'count',
        'success_rate_display',
        'successful_count',
        'failed_count',
    )
    list_filter = (
        'action',
        'date',
    )
    search_fields = (
        'user__username',
        'user__email',
        'action',
    )
    readonly_fields = (
        'date',
        'user',
        'action',
        'count',
        'successful_count',
        'failed_count',
        'success_rate_display',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        (_('Summary Information'), {
            'fields': ('date', 'user', 'action')
        }),
        (_('Statistics'), {
            'fields': (
                'count',
                'successful_count',
                'failed_count',
                'success_rate_display',
            )
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'date'
    ordering = ('-date', '-count')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user').order_by('-date', '-count')
    
    def user_link(self, obj):
        """Link to user"""
        if obj.user:
            url = reverse('admin:auth_user_change', args=[obj.user.pk])
            return format_html('<a href="{}">{}</a>', url, obj.user.username)
        return format_html('<span style="color: gray;">All Users</span>')
    user_link.short_description = "User"
    user_link.admin_order_field = 'user__username'
    
    def action_badge(self, obj):
        """Display action badge"""
        action_colors = {
            'create': '#4caf50',
            'update': '#2196f3',
            'delete': '#f44336',
            'login': '#ff9800',
            'logout': '#9e9e9e',
            'password_change': '#e91e63',
        }
        color = action_colors.get(obj.action, '#9e9e9e')
        return format_html(
            '<span style="background: {}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px; text-transform: uppercase;">{}</span>',
            color,
            obj.action
        )
    action_badge.short_description = "Action"
    action_badge.admin_order_field = 'action'
    
    def success_rate_display(self, obj):
        """Display success rate with color"""
        rate = obj.success_rate
        color = '#4caf50' if rate >= 90 else '#ff9800' if rate >= 70 else '#f44336'
        return format_html(
            '<span style="color: {}; font-weight: bold; font-size: 14px;">{:.1f}%</span>',
            color,
            rate
        )
    success_rate_display.short_description = "Success Rate"
    
    def has_add_permission(self, request):
        """Summaries are generated automatically"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Summaries are immutable"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """Only superusers can delete summaries"""
        return request.user.is_superuser
