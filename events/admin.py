"""
Production-grade Django Admin configuration for Events app.
Designed for optimal performance, usability, and maintainability.
"""
from django.contrib import admin
from django.db.models import Count, Q, Sum
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import uuid

from .models import (
    Venue,
    Event,
    EventRequest,
    EventInvite,
    EventAttendee,
    EventInterestMap,
    CapacityReservation,
    EventImage,
)


# ============================================================================
# INLINE MODELS
# ============================================================================

class EventInterestMapInline(admin.TabularInline):
    """Inline for managing event interests"""
    model = EventInterestMap
    extra = 0
    autocomplete_fields = ['event_interest']
    verbose_name = "Event Interest"
    verbose_name_plural = "Event Interests"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('event_interest')


class EventImageInline(admin.TabularInline):
    """Inline for managing event images"""
    model = EventImage
    extra = 1
    fields = ('image_url', 'position')
    ordering = ('position',)
    verbose_name = "Event Image"
    verbose_name_plural = "Event Images"


class EventAttendeeInline(admin.TabularInline):
    """Inline for viewing attendees (read-only)"""
    model = EventAttendee
    extra = 0
    fields = ('user', 'status', 'ticket_type', 'is_paid', 'checked_in_at')
    readonly_fields = fields
    can_delete = False
    show_change_link = True
    verbose_name = "Attendee"
    verbose_name_plural = "Attendees"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'event')
    
    def has_add_permission(self, request, obj=None):
        return False


class EventRequestInline(admin.TabularInline):
    """Inline for viewing event requests"""
    model = EventRequest
    extra = 0
    fields = ('requester', 'status', 'seats_requested', 'created_at', 'host_message')
    readonly_fields = ('requester', 'seats_requested', 'created_at')
    can_delete = True
    show_change_link = True
    verbose_name = "Request"
    verbose_name_plural = "Requests"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('requester', 'event').order_by('-created_at')
    
    def has_add_permission(self, request, obj=None):
        return False


class EventInviteInline(admin.TabularInline):
    """Inline for viewing event invites"""
    model = EventInvite
    extra = 0
    fields = ('invited_user', 'status', 'invite_type', 'expires_at')
    readonly_fields = ('invited_user', 'created_at')
    can_delete = True
    show_change_link = True
    verbose_name = "Invite"
    verbose_name_plural = "Invites"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('invited_user', 'event', 'host').order_by('-created_at')
    
    def has_add_permission(self, request, obj=None):
        return False


class CapacityReservationInline(admin.TabularInline):
    """Inline for viewing capacity reservations"""
    model = CapacityReservation
    extra = 0
    fields = ('reservation_key', 'user', 'seats_reserved', 'consumed', 'expires_at')
    readonly_fields = ('reservation_key', 'user', 'seats_reserved')
    can_delete = False
    show_change_link = True
    verbose_name = "Reservation"
    verbose_name_plural = "Capacity Reservations"
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user', 'event').order_by('-created_at')
    
    def has_add_permission(self, request, obj=None):
        return False


# ============================================================================
# VENUE ADMIN
# ============================================================================

@admin.register(Venue)
class VenueAdmin(admin.ModelAdmin):
    """Admin configuration for Venue model"""
    
    list_display = [
        'name',
        'city',
        'venue_type',
        'capacity_display',
        'active_events_count',
        'is_active',
        'created_at',
    ]
    list_filter = [
        'venue_type',
        'is_active',
        'city',
        'created_at',
    ]
    search_fields = [
        'name',
        'address',
        'city',
        'uuid',
    ]
    readonly_fields = [
        'uuid',
        'created_at',
        'updated_at',
        'active_events_count',
        'metadata_display',
    ]
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('uuid', 'name', 'venue_type', 'is_active')
        }),
        (_('Location'), {
            'fields': ('address', 'city', 'latitude', 'longitude')
        }),
        (_('Capacity'), {
            'fields': ('capacity', 'active_events_count')
        }),
        (_('Additional Information'), {
            'fields': ('metadata_display',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    autocomplete_fields = []
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Annotate with count of active events for performance
        return qs.annotate(
            active_events=Count('events', filter=Q(events__is_active=True, events__status='published'))
        )
    
    def capacity_display(self, obj):
        """Display capacity with styling"""
        if obj.capacity == 0:
            return format_html('<span style="color: red;">No Limit</span>')
        return f"{obj.capacity:,}"
    capacity_display.short_description = "Capacity"
    capacity_display.admin_order_field = 'capacity'
    
    def active_events_count(self, obj):
        """Display count of active events at this venue"""
        count = getattr(obj, 'active_events', obj.events.filter(is_active=True, status='published').count())
        return format_html(
            '<span style="font-weight: bold; color: {};">{}</span>',
            'green' if count > 0 else 'gray',
            count
        )
    active_events_count.short_description = "Active Events"
    active_events_count.admin_order_field = 'active_events'
    
    def metadata_display(self, obj):
        """Display metadata in a readable format"""
        if not obj.metadata:
            return "No additional information"
        import json
        return format_html(
            '<pre style="max-height: 200px; overflow-y: auto;">{}</pre>',
            json.dumps(obj.metadata, indent=2)
        )
    metadata_display.short_description = "Metadata (JSON)"
    
    actions = ['activate_venues', 'deactivate_venues']
    
    def activate_venues(self, request, queryset):
        """Bulk activate venues"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} venue(s) activated successfully.')
    activate_venues.short_description = "Activate selected venues"
    
    def deactivate_venues(self, request, queryset):
        """Bulk deactivate venues"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} venue(s) deactivated successfully.')
    deactivate_venues.short_description = "Deactivate selected venues"


# ============================================================================
# EVENT ADMIN
# ============================================================================

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Comprehensive admin configuration for Event model"""
    
    list_display = [
        'title',
        'host_link',
        'venue_link',
        'start_time',
        'status_display',
        'capacity_info',
        'is_paid_display',
        'is_active',
        'created_at',
    ]
    list_filter = [
        'status',
        'is_active',
        'is_public',
        'is_paid',
        'allowed_genders',
        ('start_time', admin.DateFieldListFilter),
        ('created_at', admin.DateFieldListFilter),
    ]
    search_fields = [
        'title',
        'description',
        'slug',
        'uuid',
        'host__username',
        'host__email',
        'venue__name',
    ]
    readonly_fields = [
        'uuid',
        'slug',
        'going_count',
        'requests_count',
        'created_at',
        'updated_at',
        'is_past_display',
        'is_full_display',
        'capacity_status',
        'revenue_display',
        'duration_display',
    ]
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('uuid', 'slug', 'title', 'description', 'host')
        }),
        (_('Venue & Location'), {
            'fields': ('venue', 'venue_text')
        }),
        (_('Event Schedule'), {
            'fields': ('start_time', 'end_time', 'duration_display')
        }),
        (_('Capacity & Pricing'), {
            'fields': (
                'max_capacity',
                'is_paid',
                'ticket_price',
                'allow_plus_one',
                'capacity_status',
            )
        }),
        (_('GST Information'), {
            'fields': ('gst_number',),
            'classes': ('collapse',)
        }),
        (_('Restrictions'), {
            'fields': ('allowed_genders',)
        }),
        (_('Media'), {
            'fields': ('cover_images',)
        }),
        (_('Status & Visibility'), {
            'fields': ('status', 'is_public', 'is_active')
        }),
        (_('Statistics'), {
            'fields': ('going_count', 'requests_count', 'revenue_display'),
            'classes': ('collapse',)
        }),
        (_('Metadata'), {
            'fields': ('is_past_display', 'is_full_display'),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    autocomplete_fields = ['host', 'venue']
    inlines = [
        EventInterestMapInline,
        EventImageInline,
        EventAttendeeInline,
        EventRequestInline,
        EventInviteInline,
        CapacityReservationInline,
    ]
    date_hierarchy = 'start_time'
    save_on_top = True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('host', 'venue').prefetch_related(
            'interest_maps__event_interest',
            'attendees',
            'requests',
            'invites',
            'capacity_reservations',
        ).annotate(
            total_revenue=Sum('attendees__price_paid')
        )
    
    def host_link(self, obj):
        """Link to host's profile"""
        url = reverse('admin:auth_user_change', args=[obj.host_id])
        return format_html('<a href="{}">{}</a>', url, obj.host.username)
    host_link.short_description = "Host"
    host_link.admin_order_field = 'host__username'
    
    def venue_link(self, obj):
        """Link to venue with fallback to venue_text"""
        if obj.venue:
            url = reverse('admin:events_venue_change', args=[obj.venue_id])
            return format_html('<a href="{}">{}</a>', url, obj.venue.name)
        elif obj.venue_text:
            return format_html('<em>{}</em>', obj.venue_text)
        return '-'
    venue_link.short_description = "Venue"
    venue_link.admin_order_field = 'venue__name'
    
    def status_display(self, obj):
        """Display status with color coding"""
        colors = {
            'draft': 'gray',
            'published': 'green',
            'cancelled': 'red',
            'completed': 'blue',
            'postponed': 'orange',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="font-weight: bold; color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"
    status_display.admin_order_field = 'status'
    
    def capacity_info(self, obj):
        """Display capacity with fill percentage"""
        if obj.max_capacity == 0:
            return mark_safe('<span style="color: gray;">Unlimited</span>')
        
        percentage = (obj.going_count / obj.max_capacity) * 100
        color = 'red' if percentage >= 90 else 'orange' if percentage >= 70 else 'green'
        return format_html(
            '<span style="color: {};">{} / {} ({}%)</span>',
            color,
            obj.going_count,
            obj.max_capacity,
            int(percentage)
        )
    capacity_info.short_description = "Capacity"
    capacity_info.admin_order_field = 'going_count'
    
    def is_paid_display(self, obj):
        """Display payment status with price"""
        if obj.is_paid:
            return format_html(
                '<span style="color: green; font-weight: bold;">₹{}</span>',
                f"{obj.ticket_price:.2f}"
            )
        return mark_safe('<span style="color: gray;">Free</span>')
    is_paid_display.short_description = "Price"
    is_paid_display.admin_order_field = 'is_paid'
    
    def capacity_status(self, obj):
        """Display detailed capacity status"""
        if obj.max_capacity == 0:
            return "No capacity limit"
        
        percentage = (obj.going_count / obj.max_capacity) * 100 if obj.max_capacity > 0 else 0
        return f"{obj.going_count} attendees ({percentage:.1f}% full)"
    capacity_status.short_description = "Capacity Status"
    
    def revenue_display(self, obj):
        """Display total revenue from this event"""
        revenue = getattr(obj, 'total_revenue', 0) or 0
        return format_html(
            '<span style="font-weight: bold; color: green;">₹{}</span>',
            f"{revenue:.2f}"
        )
    revenue_display.short_description = "Total Revenue"
    
    def is_past_display(self, obj):
        """Display if event is past"""
        if not obj or not obj.end_time:
            return mark_safe('<span style="color: gray;">Not set</span>')
        is_past = obj.is_past
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            'red' if is_past else 'green',
            'Past Event' if is_past else 'Upcoming/Current'
        )
    is_past_display.short_description = "Timing Status"
    
    def is_full_display(self, obj):
        """Display if event is full"""
        if not obj:
            return mark_safe('<span style="color: gray;">Not set</span>')
        is_full = obj.is_full
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            'red' if is_full else 'green',
            'FULL' if is_full else 'Available'
        )
    is_full_display.short_description = "Availability"
    
    def duration_display(self, obj):
        """Display event duration in hours"""
        if not obj.start_time or not obj.end_time:
            return '-'
        
        duration = obj.end_time - obj.start_time
        total_seconds = duration.total_seconds()
        hours = total_seconds / 3600
        
        if hours < 1:
            minutes = total_seconds / 60
            return format_html('<span style="color: blue; font-weight: bold;">{:.1f} min</span>', minutes)
        elif hours == int(hours):
            return format_html('<span style="color: blue; font-weight: bold;">{} hr</span>', int(hours))
        else:
            return format_html('<span style="color: blue; font-weight: bold;">{:.1f} hr</span>', hours)
    duration_display.short_description = "Duration"
    
    actions = [
        'publish_events',
        'cancel_events',
        'activate_events',
        'deactivate_events',
        'mark_as_completed',
    ]
    
    def publish_events(self, request, queryset):
        """Bulk publish events"""
        count = 0
        for event in queryset.filter(status='draft'):
            event.status = 'published'
            event.save()
            count += 1
        self.message_user(request, f'{count} event(s) published successfully.')
    publish_events.short_description = "Publish selected events"
    
    def cancel_events(self, request, queryset):
        """Bulk cancel events"""
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} event(s) cancelled successfully.')
    cancel_events.short_description = "Cancel selected events"
    
    def activate_events(self, request, queryset):
        """Bulk activate events"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'{updated} event(s) activated successfully.')
    activate_events.short_description = "Activate selected events"
    
    def deactivate_events(self, request, queryset):
        """Bulk deactivate events"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'{updated} event(s) deactivated successfully.')
    deactivate_events.short_description = "Deactivate selected events"
    
    def mark_as_completed(self, request, queryset):
        """Bulk mark events as completed"""
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} event(s) marked as completed.')
    mark_as_completed.short_description = "Mark as completed"


# ============================================================================
# EVENT REQUEST ADMIN
# ============================================================================

@admin.register(EventRequest)
class EventRequestAdmin(admin.ModelAdmin):
    """Admin configuration for EventRequest model"""
    
    list_display = [
        'event_link',
        'requester_link',
        'status_display',
        'seats_requested',
        'has_host_message',
        'created_at',
    ]
    list_filter = [
        'status',
        'created_at',
    ]
    search_fields = [
        'event__title',
        'requester__username',
        'requester__email',
        'message',
        'host_message',
        'uuid',
    ]
    readonly_fields = [
        'uuid',
        'created_at',
        'updated_at',
    ]
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('uuid', 'event', 'requester')
        }),
        (_('Request Details'), {
            'fields': ('status', 'seats_requested', 'message')
        }),
        (_('Host Response'), {
            'fields': ('host_message',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    autocomplete_fields = ['event', 'requester']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('event', 'requester').order_by('-created_at')
    
    def event_link(self, obj):
        """Link to event"""
        url = reverse('admin:events_event_change', args=[obj.event_id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title)
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def requester_link(self, obj):
        """Link to requester's profile"""
        url = reverse('admin:auth_user_change', args=[obj.requester_id])
        return format_html('<a href="{}">{}</a>', url, obj.requester.username)
    requester_link.short_description = "Requester"
    requester_link.admin_order_field = 'requester__username'
    
    def status_display(self, obj):
        """Display status with color"""
        colors = {
            'pending': 'orange',
            'accepted': 'green',
            'rejected': 'red',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="font-weight: bold; color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"
    status_display.admin_order_field = 'status'
    
    def has_host_message(self, obj):
        """Show if host has responded"""
        if not obj:
            return mark_safe('<span style="color: gray;">-</span>')
        has_message = bool(obj.host_message)
        return format_html(
            '<span style="color: {};">{}</span>',
            'green' if has_message else 'gray',
            '✓' if has_message else '✗'
        )
    has_host_message.short_description = "Host Replied"
    # Note: boolean = True removed - this returns HTML, not a boolean
    
    actions = ['accept_requests', 'reject_requests']
    
    def accept_requests(self, request, queryset):
        """Bulk accept requests"""
        updated = queryset.update(status='accepted')
        self.message_user(request, f'{updated} request(s) accepted.')
    accept_requests.short_description = "Accept selected requests"
    
    def reject_requests(self, request, queryset):
        """Bulk reject requests"""
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} request(s) rejected.')
    reject_requests.short_description = "Reject selected requests"


# ============================================================================
# EVENT INVITE ADMIN
# ============================================================================

@admin.register(EventInvite)
class EventInviteAdmin(admin.ModelAdmin):
    """Admin configuration for EventInvite model"""
    
    list_display = [
        'event_link',
        'host_link',
        'invited_user_link',
        'invite_type',
        'status_display',
        'is_expired_display',
        'created_at',
    ]
    list_filter = [
        'invite_type',
        'status',
        'created_at',
    ]
    search_fields = [
        'event__title',
        'host__username',
        'invited_user__username',
        'invited_user__email',
        'uuid',
    ]
    readonly_fields = [
        'uuid',
        'created_at',
        'updated_at',
        'is_expired_display',
    ]
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('uuid', 'event', 'host', 'invited_user')
        }),
        (_('Invitation Details'), {
            'fields': ('invite_type', 'status', 'message')
        }),
        (_('Expiration'), {
            'fields': ('expires_at', 'is_expired_display')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    autocomplete_fields = ['event', 'host', 'invited_user']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('event', 'host', 'invited_user').order_by('-created_at')
    
    def event_link(self, obj):
        """Link to event"""
        url = reverse('admin:events_event_change', args=[obj.event_id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title)
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def host_link(self, obj):
        """Link to host"""
        if obj.host:
            url = reverse('admin:auth_user_change', args=[obj.host_id])
            return format_html('<a href="{}">{}</a>', url, obj.host.username)
        return '-'
    host_link.short_description = "Host"
    host_link.admin_order_field = 'host__username'
    
    def invited_user_link(self, obj):
        """Link to invited user"""
        url = reverse('admin:auth_user_change', args=[obj.invited_user_id])
        return format_html('<a href="{}">{}</a>', url, obj.invited_user.username)
    invited_user_link.short_description = "Invited User"
    invited_user_link.admin_order_field = 'invited_user__username'
    
    def status_display(self, obj):
        """Display status with color"""
        colors = {
            'pending': 'orange',
            'accepted': 'green',
            'rejected': 'red',
            'expired': 'gray',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="font-weight: bold; color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"
    status_display.admin_order_field = 'status'
    
    def is_expired_display(self, obj):
        """Display if invite is expired"""
        if not obj or not obj.expires_at:
            return mark_safe('<span style="color: gray;">Not set</span>')
        is_expired = obj.expires_at < timezone.now()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            'red' if is_expired else 'green',
            'Expired' if is_expired else 'Valid'
        )
    is_expired_display.short_description = "Expiration"
    
    actions = ['accept_invites', 'reject_invites']
    
    def accept_invites(self, request, queryset):
        """Bulk accept invites"""
        updated = queryset.update(status='accepted')
        self.message_user(request, f'{updated} invite(s) accepted.')
    accept_invites.short_description = "Accept selected invites"
    
    def reject_invites(self, request, queryset):
        """Bulk reject invites"""
        updated = queryset.update(status='rejected')
        self.message_user(request, f'{updated} invite(s) rejected.')
    reject_invites.short_description = "Reject selected invites"


# ============================================================================
# EVENT ATTENDEE ADMIN
# ============================================================================

@admin.register(EventAttendee)
class EventAttendeeAdmin(admin.ModelAdmin):
    """Admin configuration for EventAttendee model"""
    
    list_display = [
        'event_link',
        'user_link',
        'origin_display',
        'status_display',
        'ticket_type',
        'seats',
        'payment_status',
        'checked_in_display',
        'created_at',
    ]
    list_filter = [
        'status',
        'ticket_type',
        'is_paid',
        'checked_in_at',
        'created_at',
    ]
    search_fields = [
        'event__title',
        'user__username',
        'user__email',
        'uuid',
    ]
    readonly_fields = [
        'uuid',
        'created_at',
        'updated_at',
        'payment_total',
    ]
    fieldsets = (
        (_('Basic Information'), {
            'fields': ('uuid', 'event', 'user')
        }),
        (_('Origin'), {
            'fields': ('request', 'invite'),
            'description': 'Track whether attendee came from a request or invitation'
        }),
        (_('Attendance Details'), {
            'fields': ('status', 'ticket_type', 'seats', 'checked_in_at')
        }),
        (_('Payment Information'), {
            'fields': ('is_paid', 'price_paid', 'platform_fee', 'payment_total')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    autocomplete_fields = ['event', 'user', 'request', 'invite']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('event', 'user', 'request', 'invite').order_by('-created_at')
    
    def event_link(self, obj):
        """Link to event"""
        url = reverse('admin:events_event_change', args=[obj.event_id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title)
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def user_link(self, obj):
        """Link to user"""
        url = reverse('admin:auth_user_change', args=[obj.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = "User"
    user_link.admin_order_field = 'user__username'
    
    def origin_display(self, obj):
        """Display origin (request or invite)"""
        if obj.request:
            url = reverse('admin:events_eventrequest_change', args=[obj.request_id])
            return format_html(
                '<span style="color: blue;">Request: <a href="{}">#{}</a></span>',
                url,
                obj.request.id
            )
        elif obj.invite:
            url = reverse('admin:events_eventinvite_change', args=[obj.invite_id])
            return format_html(
                '<span style="color: green;">Invite: <a href="{}">#{}</a></span>',
                url,
                obj.invite.id
            )
        return mark_safe('<span style="color: gray;">Direct</span>')
    origin_display.short_description = "Origin"
    
    def status_display(self, obj):
        """Display status with color"""
        colors = {
            'going': 'green',
            'not_going': 'red',
            'maybe': 'orange',
            'checked_in': 'blue',
            'cancelled': 'gray',
        }
        color = colors.get(obj.status, 'black')
        return format_html(
            '<span style="font-weight: bold; color: {};">{}</span>',
            color,
            obj.get_status_display()
        )
    status_display.short_description = "Status"
    status_display.admin_order_field = 'status'
    
    def payment_status(self, obj):
        """Display payment status"""
        if obj.is_paid:
            return format_html(
                '<span style="color: green; font-weight: bold;">✓ Paid</span>'
            )
        if obj.price_paid > 0:
            return format_html(
                '<span style="color: orange; font-weight: bold;">₹{}</span>',
                f"{obj.price_paid:.2f}"
            )
        return mark_safe('<span style="color: gray;">Free</span>')
    payment_status.short_description = "Payment"
    
    def payment_total(self, obj):
        """Display total payment"""
        total = obj.price_paid + obj.platform_fee
        return format_html(
            '<span style="font-weight: bold;">₹{}</span>',
            f"{total:.2f}"
        )
    payment_total.short_description = "Total Amount"
    
    def checked_in_display(self, obj):
        """Display check-in status"""
        if not obj:
            return mark_safe('<span style="color: gray;">Not set</span>')
        if obj.checked_in_at:
            return mark_safe(
                '<span style="color: green; font-weight: bold;">✓ Yes</span>'
            )
        return mark_safe('<span style="color: gray;">No</span>')
    checked_in_display.short_description = "Checked In"
    # Note: boolean = True removed - this returns HTML, not a boolean


# ============================================================================
# EVENT INTEREST MAP ADMIN
# ============================================================================

@admin.register(EventInterestMap)
class EventInterestMapAdmin(admin.ModelAdmin):
    """Admin configuration for EventInterestMap model"""
    
    list_display = [
        'event_link',
        'event_interest_link',
        'created_at',
    ]
    list_filter = [
        'created_at',
    ]
    search_fields = [
        'event__title',
        'event_interest__name',
    ]
    readonly_fields = [
        'created_at',
        'updated_at',
    ]
    autocomplete_fields = ['event', 'event_interest']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('event', 'event_interest')
    
    def event_link(self, obj):
        """Link to event"""
        url = reverse('admin:events_event_change', args=[obj.event_id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title)
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def event_interest_link(self, obj):
        """Link to event interest"""
        url = reverse('admin:users_eventinterest_change', args=[obj.event_interest_id])
        return format_html('<a href="{}">{}</a>', url, obj.event_interest.name)
    event_interest_link.short_description = "Interest"
    event_interest_link.admin_order_field = 'event_interest__name'


# ============================================================================
# CAPACITY RESERVATION ADMIN
# ============================================================================

@admin.register(CapacityReservation)
class CapacityReservationAdmin(admin.ModelAdmin):
    """Admin configuration for CapacityReservation model"""
    
    list_display = [
        'reservation_key',
        'event_link',
        'user_link',
        'seats_reserved',
        'consumed_display',
        'is_expired_display',
        'created_at',
    ]
    list_filter = [
        'consumed',
        'created_at',
        'expires_at',
    ]
    search_fields = [
        'reservation_key',
        'event__title',
        'user__username',
        'user__email',
    ]
    readonly_fields = [
        'reservation_key',
        'created_at',
        'updated_at',
        'is_expired_display',
    ]
    fieldsets = (
        (_('Reservation Information'), {
            'fields': ('reservation_key', 'event', 'user', 'seats_reserved')
        }),
        (_('Status'), {
            'fields': ('consumed', 'expires_at', 'is_expired_display')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    autocomplete_fields = ['event', 'user']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('event', 'user').order_by('-created_at')
    
    def event_link(self, obj):
        """Link to event"""
        url = reverse('admin:events_event_change', args=[obj.event_id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title)
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def user_link(self, obj):
        """Link to user"""
        url = reverse('admin:auth_user_change', args=[obj.user_id])
        return format_html('<a href="{}">{}</a>', url, obj.user.username)
    user_link.short_description = "User"
    user_link.admin_order_field = 'user__username'
    
    def consumed_display(self, obj):
        """Display if reservation is consumed"""
        if not obj:
            return mark_safe('<span style="color: gray;">Not set</span>')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            'green' if obj.consumed else 'orange',
            '✓ Consumed' if obj.consumed else 'Pending'
        )
    consumed_display.short_description = "Status"
    # Note: boolean = True removed - this returns HTML, not a boolean
    
    def is_expired_display(self, obj):
        """Display if reservation is expired"""
        if not obj or not obj.expires_at:
            return mark_safe('<span style="color: gray;">Not set</span>')
        is_expired = obj.expires_at < timezone.now()
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            'red' if is_expired else 'green',
            'Expired' if is_expired else 'Valid'
        )
    is_expired_display.short_description = "Expiration"
    
    actions = ['mark_as_consumed']
    
    def mark_as_consumed(self, request, queryset):
        """Bulk mark reservations as consumed"""
        updated = queryset.update(consumed=True)
        self.message_user(request, f'{updated} reservation(s) marked as consumed.')
    mark_as_consumed.short_description = "Mark as consumed"


# ============================================================================
# EVENT IMAGE ADMIN
# ============================================================================

@admin.register(EventImage)
class EventImageAdmin(admin.ModelAdmin):
    """Admin configuration for EventImage model"""
    
    list_display = [
        'event_link',
        'position',
        'image_preview',
        'created_at',
    ]
    list_filter = [
        'position',
        'created_at',
    ]
    search_fields = [
        'event__title',
        'image_url',
    ]
    readonly_fields = [
        'image_preview',
        'created_at',
        'updated_at',
    ]
    fieldsets = (
        (_('Image Information'), {
            'fields': ('event', 'image_url', 'position')
        }),
        (_('Preview'), {
            'fields': ('image_preview',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    autocomplete_fields = ['event']
    ordering = ['event', 'position']
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('event').order_by('event', 'position')
    
    def event_link(self, obj):
        """Link to event"""
        url = reverse('admin:events_event_change', args=[obj.event_id])
        return format_html('<a href="{}">{}</a>', url, obj.event.title)
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def image_preview(self, obj):
        """Display image preview"""
        if obj.image_url:
            return format_html(
                '<img src="{}" style="max-width: 200px; max-height: 200px;" />',
                obj.image_url
            )
        return 'No image'
    image_preview.short_description = "Preview"


# ============================================================================
# ADMIN SITE CONFIGURATION
# ============================================================================

# Configure admin site header and title for better UX
admin.site.site_header = _("Loopin Backend Administration")
admin.site.site_title = _("Loopin Admin")