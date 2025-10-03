from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render
from .models import UserProfile

# Register your models here.

class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile in User admin"""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'

class UserAdmin(BaseUserAdmin):
    """Custom User admin for all users with profile status"""
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active', 'date_joined', 'has_profile')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    
    fieldsets = (
        ('Authentication', {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('first_name', 'last_name', 'email')
        }),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    def has_profile(self, obj):
        """Check if user has a profile"""
        return hasattr(obj, 'profile') and obj.profile is not None
    has_profile.boolean = True
    has_profile.short_description = 'Has Profile'
    
    def get_queryset(self, request):
        """Show all users"""
        return super().get_queryset(request).all()

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin for User Profile management (Normal Users)"""
    list_display = ('name', 'email', 'phone_number', 'location', 'is_verified', 'is_active', 'created_at')
    list_filter = ('is_verified', 'is_active', 'created_at', 'updated_at', 'location')
    search_fields = ('name', 'email', 'phone_number', 'user__username', 'location')
    readonly_fields = ('created_at', 'updated_at', 'user')
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'email', 'phone_number'),
            'description': 'Essential contact and identification information'
        }),
        ('Profile Details', {
            'fields': ('bio', 'location', 'birth_date', 'avatar'),
            'description': 'Additional profile information'
        }),
        ('Status', {
            'fields': ('is_verified', 'is_active'),
            'description': 'Profile status and verification'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Automatically managed timestamps'
        }),
    )
    
    def get_queryset(self, request):
        """Show all users with profiles (including staff/superusers)"""
        qs = super().get_queryset(request)
        return qs.all()

# Customize admin site headers
admin.site.site_header = "Loopin Backend Administration"
admin.site.site_title = "Loopin Admin"
admin.site.index_title = "Welcome to Loopin Backend Administration"

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)