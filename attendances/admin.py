"""
Production-grade Django Admin configuration for Attendances app.
Modern admin interface with optimized queries, rich displays, and bulk actions.
"""
from django.contrib import admin
from django.db.models import Count, Q, Sum
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import AttendanceRecord, TicketSecret


# ============================================================================
# INLINE MODELS
# ============================================================================

class TicketSecretInline(admin.TabularInline):
    """Inline for viewing ticket secrets"""
    model = TicketSecret
    extra = 0
    fields = ('is_redeemed', 'redeemed_at')
    readonly_fields = ('is_redeemed', 'redeemed_at')
    can_delete = False
    show_change_link = True
    verbose_name = "Ticket Secret"
    verbose_name_plural = "Ticket Secrets"
    
    def has_add_permission(self, request, obj=None):
        return False


# ============================================================================
# ATTENDANCE RECORD ADMIN
# ============================================================================

@admin.register(AttendanceRecord)
class AttendanceRecordAdmin(admin.ModelAdmin):
    """Comprehensive admin configuration for AttendanceRecord model"""
    
    list_display = [
        'event_link',
        'user_link',
        'status_display',
        'payment_status_display',
        'seats',
        'ticket_secret_short',
        'check_in_status',
        'created_at',
    ]
    list_filter = [
        'status',
        'payment_status',
        ('checked_in_at', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
        'event__is_paid',
    ]
    search_fields = [
        'event__title',
        'user__username',
        'user__email',
        'ticket_secret',
        'notes',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
        'ticket_secret',
        'duration_display',
        'is_checked_in_display',
    ]
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('event', 'user', 'ticket_secret')
        }),
        (_('Attendance Status'), {
            'fields': ('status', 'seats', 'payment_status')
        }),
        (_('Check-in Information'), {
            'fields': ('checked_in_at', 'checked_out_at', 'is_checked_in_display', 'duration_display')
        }),
        (_('Additional Notes'), {
            'fields': ('notes',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    autocomplete_fields = ['event', 'user']
    inlines = [
        TicketSecretInline,
    ]
    date_hierarchy = 'checked_in_at'
    save_on_top = True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('event', 'event__host', 'user').prefetch_related(
            'ticket_secret_obj',
        ).order_by('-created_at')
    
    def event_link(self, obj):
        """Link to event"""
        url = reverse('admin:events_event_change', args=[obj.event_id])
        return mark_safe(f'<a href="{url}">{obj.event.title}</a>')
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def user_link(self, obj):
        """Link to user"""
        url = reverse('admin:auth_user_change', args=[obj.user_id])
        return mark_safe(f'<a href="{url}">{obj.user.username}</a>')
    user_link.short_description = "User"
    user_link.admin_order_field = 'user__username'
    
    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'going': 'green',
            'not_going': 'red',
            'maybe': 'orange',
            'checked_in': 'blue',
            'cancelled': 'gray',
        }
        color = colors.get(obj.status, 'black')
        return mark_safe(f'<span style="font-weight: bold; color: {color};">{obj.get_status_display()}</span>')
    status_display.short_description = "Status"
    status_display.admin_order_field = 'status'
    
    def payment_status_display(self, obj):
        """Display payment status with color"""
        colors = {
            'unpaid': 'red',
            'paid': 'green',
            'pending': 'orange',
            'refunded': 'gray',
            'failed': 'red',
        }
        color = colors.get(obj.payment_status, 'black')
        return mark_safe(f'<span style="font-weight: bold; color: {color};">{obj.get_payment_status_display()}</span>')
    payment_status_display.short_description = "Payment"
    payment_status_display.admin_order_field = 'payment_status'
    
    def ticket_secret_short(self, obj):
        """Display shortened ticket secret"""
        if obj.ticket_secret:
            secret_display = obj.ticket_secret[:16] + '...' if len(obj.ticket_secret) > 16 else obj.ticket_secret
            return mark_safe(f'<code style="font-size: 11px;">{secret_display}</code>')
        return '-'
    ticket_secret_short.short_description = "Ticket Secret"
    
    def check_in_status(self, obj):
        """Display check-in status"""
        if obj.checked_in_at:
            if obj.checked_out_at:
                in_time = obj.checked_in_at.strftime('%Y-%m-%d %H:%M')
                out_time = obj.checked_out_at.strftime('%Y-%m-%d %H:%M')
                return mark_safe(f'<span style="color: gray;">Checked Out</span><br><small style="color: gray;">In: {in_time}, Out: {out_time}</small>')
            in_time = obj.checked_in_at.strftime('%Y-%m-%d %H:%M')
            return mark_safe(f'<span style="color: green; font-weight: bold;">✓ Checked In</span><br><small style="color: gray;">{in_time}</small>')
        return mark_safe('<span style="color: orange;">Not Checked In</span>')
    check_in_status.short_description = "Check-in Status"
    
    def duration_display(self, obj):
        """Display attendance duration"""
        duration = obj.attendance_duration
        if duration:
            hours = duration.total_seconds() / 3600
            if hours < 1:
                minutes = duration.total_seconds() / 60
                return f"{int(minutes)} minutes"
            elif hours == int(hours):
                return f"{int(hours)} hours"
            else:
                return f"{hours:.1f} hours"
        return '-'
    duration_display.short_description = "Duration"
    
    def is_checked_in_display(self, obj):
        """Display if currently checked in"""
        if not obj:
            return mark_safe('<span style="color: gray;">Not set</span>')
        is_checked = obj.is_checked_in
        color = 'green' if is_checked else 'gray'
        text = 'Yes' if is_checked else 'No'
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{text}</span>')
    is_checked_in_display.short_description = "Currently Checked In"
    # Note: boolean = True removed - this returns HTML, not a boolean
    
    actions = [
        'check_in_selected',
        'check_out_selected',
        'mark_as_paid',
        'mark_as_unpaid',
        'cancel_attendance',
    ]
    
    def check_in_selected(self, request, queryset):
        """Bulk check in selected attendees"""
        count = 0
        for record in queryset.filter(status='going'):
            record.check_in()
            count += 1
        self.message_user(request, f'{count} attendee(s) checked in successfully.')
    check_in_selected.short_description = "Check in selected attendees"
    
    def check_out_selected(self, request, queryset):
        """Bulk check out selected attendees"""
        count = 0
        for record in queryset.filter(status='checked_in'):
            record.check_out()
            count += 1
        self.message_user(request, f'{count} attendee(s) checked out successfully.')
    check_out_selected.short_description = "Check out selected attendees"
    
    def mark_as_paid(self, request, queryset):
        """Bulk mark as paid"""
        updated = queryset.update(payment_status='paid')
        self.message_user(request, f'{updated} record(s) marked as paid.')
    mark_as_paid.short_description = "Mark as paid"
    
    def mark_as_unpaid(self, request, queryset):
        """Bulk mark as unpaid"""
        updated = queryset.update(payment_status='unpaid')
        self.message_user(request, f'{updated} record(s) marked as unpaid.')
    mark_as_unpaid.short_description = "Mark as unpaid"
    
    def cancel_attendance(self, request, queryset):
        """Bulk cancel attendance"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} attendance(s) cancelled.')
    cancel_attendance.short_description = "Cancel selected attendance"


# ============================================================================
# TICKET SECRET ADMIN
# ============================================================================

@admin.register(TicketSecret)
class TicketSecretAdmin(admin.ModelAdmin):
    """Admin configuration for TicketSecret model"""
    
    list_display = [
        'attendance_record_link',
        'is_redeemed_display',
        'redeemed_at',
        'created_at',
    ]
    list_filter = [
        'is_redeemed',
        ('redeemed_at', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
    ]
    search_fields = [
        'attendance_record__event__title',
        'attendance_record__user__username',
        'attendance_record__user__email',
        'attendance_record__ticket_secret',
    ]
    readonly_fields = [
        'attendance_record',
        'secret_hash',
        'secret_salt',
        'created_at',
        'updated_at',
        'is_redeemed_display',
    ]
    fieldsets = (
        (_('Ticket Information'), {
            'fields': ('attendance_record',)
        }),
        (_('Security'), {
            'fields': ('secret_hash', 'secret_salt'),
            'classes': ('collapse',),
            'description': 'Hashed ticket secret for verification'
        }),
        (_('Redemption Status'), {
            'fields': ('is_redeemed', 'redeemed_at', 'is_redeemed_display')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'attendance_record',
            'attendance_record__event',
            'attendance_record__user',
        ).order_by('-created_at')
    
    def attendance_record_link(self, obj):
        """Link to attendance record"""
        url = reverse('admin:attendances_attendancerecord_change', args=[obj.attendance_record_id])
        event_title = obj.attendance_record.event.title
        user_name = obj.attendance_record.user.username
        return mark_safe(f'<a href="{url}">{event_title} - {user_name}</a>')
    attendance_record_link.short_description = "Attendance Record"
    attendance_record_link.admin_order_field = 'attendance_record__event__title'
    
    def is_redeemed_display(self, obj):
        """Display redemption status"""
        if not obj:
            return mark_safe('<span style="color: gray;">Not set</span>')
        color = 'red' if obj.is_redeemed else 'green'
        text = 'Redeemed' if obj.is_redeemed else 'Not Redeemed'
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{text}</span>')
    is_redeemed_display.short_description = "Status"
    # Note: boolean = True removed - this returns HTML, not a boolean
    
    actions = ['mark_as_redeemed', 'mark_as_not_redeemed']
    
    def mark_as_redeemed(self, request, queryset):
        """Bulk mark as redeemed"""
        count = 0
        for ticket in queryset.filter(is_redeemed=False):
            ticket.mark_redeemed()
            count += 1
        self.message_user(request, f'{count} ticket(s) marked as redeemed.')
    mark_as_redeemed.short_description = "Mark as redeemed"
    
    def mark_as_not_redeemed(self, request, queryset):
        """Bulk mark as not redeemed"""
        updated = queryset.update(is_redeemed=False, redeemed_at=None)
        self.message_user(request, f'{updated} ticket(s) marked as not redeemed.')
    mark_as_not_redeemed.short_description = "Mark as not redeemed"
