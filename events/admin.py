"""
Production-grade Django Admin configuration for Events app.
Designed for optimal performance, usability, and maintainability.
"""
from django.contrib import admin
from django.db.models import Count, Q, Sum
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from django import forms
import uuid
import json

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
    """Inline for managing event images with preview"""
    model = EventImage
    extra = 1
    fields = ('image_preview', 'image_url', 'position')
    readonly_fields = ('image_preview',)
    ordering = ('position',)
    verbose_name = "Event Image"
    verbose_name_plural = "Event Images"
    
    def image_preview(self, obj):
        """Display image preview in inline"""
        if obj and obj.image_url:
            from html import escape
            escaped_url = escape(obj.image_url)
            return mark_safe(f'<img src="{escaped_url}" style="max-width: 100px; max-height: 100px; object-fit: cover; border-radius: 4px;" />')
        return mark_safe('<span style="color: #999;">No image</span>')
    image_preview.short_description = "Preview"


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
            return mark_safe('<span style="color: red;">No Limit</span>')
        return f"{obj.capacity:,}"
    capacity_display.short_description = "Capacity"
    capacity_display.admin_order_field = 'capacity'
    
    def active_events_count(self, obj):
        """Display count of active events at this venue"""
        count = getattr(obj, 'active_events', obj.events.filter(is_active=True, status='published').count())
        color = 'green' if count > 0 else 'gray'
        return mark_safe(f'<span style="font-weight: bold; color: {color};">{count}</span>')
    active_events_count.short_description = "Active Events"
    active_events_count.admin_order_field = 'active_events'
    
    def metadata_display(self, obj):
        """Display metadata in a readable format"""
        if not obj.metadata:
            return "No additional information"
        import json
        return mark_safe(f'<pre style="max-height: 200px; overflow-y: auto;">{json.dumps(obj.metadata, indent=2)}</pre>')
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
# EVENT ADMIN FORMS
# ============================================================================

class EventAdminForm(forms.ModelForm):
    """Custom form for Event admin with user-friendly cover images fields"""
    
    cover_image_1 = forms.URLField(
        required=False,
        label="Cover Image 1 (URL)",
        help_text="Enter the full URL of the first cover image (e.g., https://example.com/image1.jpg)",
        widget=forms.URLInput(attrs={
            'placeholder': 'https://example.com/image1.jpg',
            'style': 'width: 100%; padding: 8px;',
        })
    )
    cover_image_2 = forms.URLField(
        required=False,
        label="Cover Image 2 (URL)",
        help_text="Enter the full URL of the second cover image (optional)",
        widget=forms.URLInput(attrs={
            'placeholder': 'https://example.com/image2.jpg',
            'style': 'width: 100%; padding: 8px;',
        })
    )
    cover_image_3 = forms.URLField(
        required=False,
        label="Cover Image 3 (URL)",
        help_text="Enter the full URL of the third cover image (optional)",
        widget=forms.URLInput(attrs={
            'placeholder': 'https://example.com/image3.jpg',
            'style': 'width: 100%; padding: 8px;',
        })
    )
    
    class Meta:
        model = Event
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate the individual image fields from the cover_images JSONField
        if self.instance and self.instance.pk:
            cover_images = self.instance.cover_images or []
            if isinstance(cover_images, list):
                if len(cover_images) > 0:
                    self.fields['cover_image_1'].initial = cover_images[0]
                if len(cover_images) > 1:
                    self.fields['cover_image_2'].initial = cover_images[1]
                if len(cover_images) > 2:
                    self.fields['cover_image_3'].initial = cover_images[2]
    
    def clean(self):
        cleaned_data = super().clean()
        # Collect non-empty image URLs
        cover_images = []
        for i in range(1, 4):
            image_url = cleaned_data.get(f'cover_image_{i}', '').strip()
            if image_url:
                cover_images.append(image_url)
        
        # Validate: at least 1 image, max 3 images
        if len(cover_images) == 0:
            raise ValidationError("At least one cover image URL is required.")
        if len(cover_images) > 3:
            raise ValidationError("Maximum 3 cover images allowed.")
        
        # Store in the cover_images JSONField
        cleaned_data['cover_images'] = cover_images
        return cleaned_data


# ============================================================================
# EVENT ADMIN
# ============================================================================

@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    """Comprehensive admin configuration for Event model"""
    form = EventAdminForm
    
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
        'host__name',
        'host__phone_number',
        'host__user__username',
        'host__user__email',
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
        'cover_images_preview',
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
            'fields': ('cover_image_1', 'cover_image_2', 'cover_image_3', 'cover_images_preview'),
            'description': 'Add 1-3 cover image URLs. Images will be displayed in the order you enter them.',
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
        url = reverse('admin:users_userprofile_change', args=[obj.host_id])
        name = obj.host.name if obj.host.name else (obj.host.user.username if obj.host.user else f'Profile #{obj.host_id}')
        return mark_safe(f'<a href="{url}">{name}</a>')
    host_link.short_description = "Host"
    host_link.admin_order_field = 'host__name'
    
    def venue_link(self, obj):
        """Link to venue with fallback to venue_text"""
        if obj.venue:
            url = reverse('admin:events_venue_change', args=[obj.venue_id])
            return mark_safe(f'<a href="{url}">{obj.venue.name}</a>')
        elif obj.venue_text:
            return mark_safe(f'<em>{obj.venue_text}</em>')
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
        return mark_safe(f'<span style="font-weight: bold; color: {color};">{obj.get_status_display()}</span>')
    status_display.short_description = "Status"
    status_display.admin_order_field = 'status'
    
    def capacity_info(self, obj):
        """Display capacity with fill percentage"""
        if obj.max_capacity == 0:
            return mark_safe('<span style="color: gray;">Unlimited</span>')
        
        percentage = (obj.going_count / obj.max_capacity) * 100
        color = 'red' if percentage >= 90 else 'orange' if percentage >= 70 else 'green'
        return mark_safe(f'<span style="color: {color};">{obj.going_count} / {obj.max_capacity} ({int(percentage)}%)</span>')
    capacity_info.short_description = "Capacity"
    capacity_info.admin_order_field = 'going_count'
    
    def is_paid_display(self, obj):
        """Display payment status with price"""
        if obj.is_paid:
            return mark_safe(f'<span style="color: green; font-weight: bold;">₹{obj.ticket_price:.2f}</span>')
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
        return mark_safe(f'<span style="font-weight: bold; color: green;">₹{revenue:.2f}</span>')
    revenue_display.short_description = "Total Revenue"
    
    def is_past_display(self, obj):
        """Display if event is past"""
        if not obj or not obj.end_time:
            return mark_safe('<span style="color: gray;">Not set</span>')
        is_past = obj.is_past
        color = 'red' if is_past else 'green'
        text = 'Past Event' if is_past else 'Upcoming/Current'
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{text}</span>')
    is_past_display.short_description = "Timing Status"
    
    def cover_images_preview(self, obj):
        """Display preview of cover images with thumbnails"""
        if not obj or not obj.cover_images:
            return mark_safe('<p style="color: #999; font-style: italic; padding: 10px; background: #f5f5f5; border-radius: 4px;">No cover images added yet. Add image URLs above and save to see previews.</p>')
        
        cover_images = obj.cover_images if isinstance(obj.cover_images, list) else []
        if not cover_images:
            return mark_safe('<p style="color: #999; font-style: italic; padding: 10px; background: #f5f5f5; border-radius: 4px;">No cover images added yet.</p>')
        
        from html import escape
        preview_html = '<div style="display: flex; gap: 15px; flex-wrap: wrap; margin-top: 10px;">'
        
        for i, image_url in enumerate(cover_images, 1):
            if image_url:
                escaped_url = escape(image_url)
                preview_html += f'''
                    <div style="border: 1px solid #ddd; border-radius: 8px; padding: 10px; background: #f9f9f9; text-align: center;">
                        <div style="font-weight: bold; margin-bottom: 8px; color: #417690;">Image {i}</div>
                        <img src="{escaped_url}" 
                             style="max-width: 200px; max-height: 200px; object-fit: cover; border-radius: 4px; border: 2px solid #ddd;"
                             onerror="this.style.display='none'; this.nextElementSibling.style.display='block';" />
                        <div style="display: none; color: #f44336; padding: 10px; font-size: 12px;">
                            ❌ Image failed to load<br/>
                            <small style="word-break: break-all;">{escaped_url}</small>
                        </div>
                        <div style="margin-top: 8px; font-size: 11px; color: #666; word-break: break-all; max-width: 200px;">
                            {escaped_url}
                        </div>
                    </div>
                '''
        
        preview_html += '</div>'
        preview_html += f'<p style="margin-top: 15px; color: #666; font-size: 12px;"><strong>Total:</strong> {len(cover_images)} image(s) added</p>'
        
        return mark_safe(preview_html)
    cover_images_preview.short_description = "Image Previews"
    
    def is_full_display(self, obj):
        """Display if event is full"""
        if not obj:
            return mark_safe('<span style="color: gray;">Not set</span>')
        is_full = obj.is_full
        color = 'red' if is_full else 'green'
        text = 'FULL' if is_full else 'Available'
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{text}</span>')
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
            return mark_safe(f'<span style="color: blue; font-weight: bold;">{minutes:.1f} min</span>')
        elif hours == int(hours):
            return mark_safe(f'<span style="color: blue; font-weight: bold;">{int(hours)} hr</span>')
        else:
            return mark_safe(f'<span style="color: blue; font-weight: bold;">{hours:.1f} hr</span>')
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
        'requester__name',
        'requester__phone_number',
        'requester__user__username',
        'requester__user__email',
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
        return mark_safe(f'<a href="{url}">{obj.event.title}</a>')
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def requester_link(self, obj):
        """Link to requester's profile"""
        url = reverse('admin:users_userprofile_change', args=[obj.requester_id])
        name = obj.requester.name if obj.requester.name else (obj.requester.user.username if obj.requester.user else f'Profile #{obj.requester_id}')
        return mark_safe(f'<a href="{url}">{name}</a>')
    requester_link.short_description = "Requester"
    requester_link.admin_order_field = 'requester__name'
    
    def status_display(self, obj):
        """Display status with color"""
        colors = {
            'pending': 'orange',
            'accepted': 'green',
            'rejected': 'red',
        }
        color = colors.get(obj.status, 'black')
        return mark_safe(f'<span style="font-weight: bold; color: {color};">{obj.get_status_display()}</span>')
    status_display.short_description = "Status"
    status_display.admin_order_field = 'status'
    
    def has_host_message(self, obj):
        """Show if host has responded"""
        if not obj:
            return mark_safe('<span style="color: gray;">-</span>')
        has_message = bool(obj.host_message)
        color = 'green' if has_message else 'gray'
        symbol = '✓' if has_message else '✗'
        return mark_safe(f'<span style="color: {color};">{symbol}</span>')
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
        'host__name',
        'host__phone_number',
        'host__user__username',
        'invited_user__name',
        'invited_user__phone_number',
        'invited_user__user__username',
        'invited_user__user__email',
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
        return mark_safe(f'<a href="{url}">{obj.event.title}</a>')
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def host_link(self, obj):
        """Link to host"""
        if obj.host:
            url = reverse('admin:users_userprofile_change', args=[obj.host_id])
            name = obj.host.name if obj.host.name else (obj.host.user.username if obj.host.user else f'Profile #{obj.host_id}')
            return mark_safe(f'<a href="{url}">{name}</a>')
        return '-'
    host_link.short_description = "Host"
    host_link.admin_order_field = 'host__name'
    
    def invited_user_link(self, obj):
        """Link to invited user"""
        url = reverse('admin:users_userprofile_change', args=[obj.invited_user_id])
        name = obj.invited_user.name if obj.invited_user.name else (obj.invited_user.user.username if obj.invited_user.user else f'Profile #{obj.invited_user_id}')
        return mark_safe(f'<a href="{url}">{name}</a>')
    invited_user_link.short_description = "Invited User"
    invited_user_link.admin_order_field = 'invited_user__name'
    
    def status_display(self, obj):
        """Display status with color"""
        colors = {
            'pending': 'orange',
            'accepted': 'green',
            'rejected': 'red',
            'expired': 'gray',
        }
        color = colors.get(obj.status, 'black')
        return mark_safe(f'<span style="font-weight: bold; color: {color};">{obj.get_status_display()}</span>')
    status_display.short_description = "Status"
    status_display.admin_order_field = 'status'
    
    def is_expired_display(self, obj):
        """Display if invite is expired"""
        if not obj or not obj.expires_at:
            return mark_safe('<span style="color: gray;">Not set</span>')
        is_expired = obj.expires_at < timezone.now()
        color = 'red' if is_expired else 'green'
        text = 'Expired' if is_expired else 'Valid'
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{text}</span>')
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
        'user__name',
        'user__phone_number',
        'user__user__username',
        'user__user__email',
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
        return mark_safe(f'<a href="{url}">{obj.event.title}</a>')
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def user_link(self, obj):
        """Link to user"""
        url = reverse('admin:users_userprofile_change', args=[obj.user_id])
        name = obj.user.name if obj.user.name else (obj.user.user.username if obj.user.user else f'Profile #{obj.user_id}')
        return mark_safe(f'<a href="{url}">{name}</a>')
    user_link.short_description = "User"
    user_link.admin_order_field = 'user__name'
    
    def origin_display(self, obj):
        """Display origin (request or invite)"""
        if obj.request:
            url = reverse('admin:events_eventrequest_change', args=[obj.request_id])
            return mark_safe(f'<span style="color: blue;">Request: <a href="{url}">#{obj.request.id}</a></span>')
        elif obj.invite:
            url = reverse('admin:events_eventinvite_change', args=[obj.invite_id])
            return mark_safe(f'<span style="color: green;">Invite: <a href="{url}">#{obj.invite.id}</a></span>')
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
        return mark_safe(f'<span style="font-weight: bold; color: {color};">{obj.get_status_display()}</span>')
    status_display.short_description = "Status"
    status_display.admin_order_field = 'status'
    
    def payment_status(self, obj):
        """Display payment status"""
        if obj.is_paid:
            return mark_safe('<span style="color: green; font-weight: bold;">✓ Paid</span>')
        if obj.price_paid > 0:
            return mark_safe(f'<span style="color: orange; font-weight: bold;">₹{obj.price_paid:.2f}</span>')
        return mark_safe('<span style="color: gray;">Free</span>')
    payment_status.short_description = "Payment"
    
    def payment_total(self, obj):
        """Display total payment"""
        total = obj.price_paid + obj.platform_fee
        return mark_safe(f'<span style="font-weight: bold;">₹{total:.2f}</span>')
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
        return mark_safe(f'<a href="{url}">{obj.event.title}</a>')
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def event_interest_link(self, obj):
        """Link to event interest"""
        url = reverse('admin:users_eventinterest_change', args=[obj.event_interest_id])
        return mark_safe(f'<a href="{url}">{obj.event_interest.name}</a>')
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
        'user__name',
        'user__phone_number',
        'user__user__username',
        'user__user__email',
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
        return mark_safe(f'<a href="{url}">{obj.event.title}</a>')
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def user_link(self, obj):
        """Link to user"""
        url = reverse('admin:users_userprofile_change', args=[obj.user_id])
        name = obj.user.name if obj.user.name else (obj.user.user.username if obj.user.user else f'Profile #{obj.user_id}')
        return mark_safe(f'<a href="{url}">{name}</a>')
    user_link.short_description = "User"
    user_link.admin_order_field = 'user__name'
    
    def consumed_display(self, obj):
        """Display if reservation is consumed"""
        if not obj:
            return mark_safe('<span style="color: gray;">Not set</span>')
        color = 'green' if obj.consumed else 'orange'
        text = '✓ Consumed' if obj.consumed else 'Pending'
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{text}</span>')
    consumed_display.short_description = "Status"
    # Note: boolean = True removed - this returns HTML, not a boolean
    
    def is_expired_display(self, obj):
        """Display if reservation is expired"""
        if not obj or not obj.expires_at:
            return mark_safe('<span style="color: gray;">Not set</span>')
        is_expired = obj.expires_at < timezone.now()
        color = 'red' if is_expired else 'green'
        text = 'Expired' if is_expired else 'Valid'
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{text}</span>')
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
        return mark_safe(f'<a href="{url}">{obj.event.title}</a>')
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def image_preview(self, obj):
        """Display image preview"""
        if obj.image_url:
            return mark_safe(f'<img src="{obj.image_url}" style="max-width: 200px; max-height: 200px;" />')
        return 'No image'
    image_preview.short_description = "Preview"


# ============================================================================
# ADMIN SITE CONFIGURATION
# ============================================================================

# Configure admin site header and title for better UX
admin.site.site_header = _("Loopin Backend Administration")
admin.site.site_title = _("Loopin Admin")