from django.contrib import admin
from notifications.models import Notification, UserDevice


@admin.register(UserDevice)
class UserDeviceAdmin(admin.ModelAdmin):
    """Admin for UserDevice model"""
    list_display = ('user_profile', 'platform', 'onesignal_player_id_short', 'is_active', 'last_seen_at', 'created_at')
    list_filter = ('platform', 'is_active', 'created_at', 'last_seen_at')
    search_fields = ('user_profile__phone_number', 'user_profile__name', 'onesignal_player_id')
    readonly_fields = ('created_at', 'updated_at', 'last_seen_at')
    ordering = ('-last_seen_at', '-created_at')
    
    def onesignal_player_id_short(self, obj):
        """Display shortened player ID"""
        if obj.onesignal_player_id:
            return f"{obj.onesignal_player_id[:16]}..." if len(obj.onesignal_player_id) > 16 else obj.onesignal_player_id
        return "-"
    onesignal_player_id_short.short_description = "Player ID"
    
    fieldsets = (
        ('Device Information', {
            'fields': ('user_profile', 'onesignal_player_id', 'platform')
        }),
        ('Status', {
            'fields': ('is_active', 'last_seen_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['deactivate_devices', 'reactivate_devices']
    
    def deactivate_devices(self, request, queryset):
        """Bulk deactivate devices"""
        count = queryset.update(is_active=False)
        self.message_user(request, f'{count} device(s) deactivated.')
    deactivate_devices.short_description = "Deactivate selected devices"
    
    def reactivate_devices(self, request, queryset):
        """Bulk reactivate devices"""
        count = queryset.update(is_active=True)
        self.message_user(request, f'{count} device(s) reactivated.')
    reactivate_devices.short_description = "Reactivate selected devices"


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    """Admin for Notification model"""
    list_display = ('type', 'recipient', 'title', 'is_read', 'created_at')
    list_filter = ('type', 'is_read', 'created_at')
    search_fields = ('title', 'message', 'recipient__phone_number', 'recipient__name')
    readonly_fields = ('uuid', 'created_at', 'updated_at')
    ordering = ('-created_at',)
    
    fieldsets = (
        ('Recipients', {
            'fields': ('recipient', 'sender')
        }),
        ('Notification Content', {
            'fields': ('type', 'title', 'message', 'metadata')
        }),
        ('Reference', {
            'fields': ('reference_type', 'reference_id'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read',)
        }),
        ('Timestamps', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        """Mark notifications as read"""
        count = queryset.update(is_read=True)
        self.message_user(request, f'{count} notification(s) marked as read.')
    mark_as_read.short_description = "Mark selected as read"
    
    def mark_as_unread(self, request, queryset):
        """Mark notifications as unread"""
        count = queryset.update(is_read=False)
        self.message_user(request, f'{count} notification(s) marked as unread.')
    mark_as_unread.short_description = "Mark selected as unread"
