from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponse
from django.shortcuts import render
from .models import UserProfile, EventInterest, PhoneOTP

# Register your models here.

class UserProfileInline(admin.StackedInline):
    """Inline admin for UserProfile in User admin"""
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'Profile'
    extra = 0
    fields = ('name', 'phone_number', 'gender', 'is_verified', 'is_active')
    readonly_fields = ('created_at', 'updated_at')

class UserAdmin(BaseUserAdmin):
    """Custom User admin for all users with profile status"""
    inlines = (UserProfileInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_superuser', 'is_active', 'date_joined', 'has_profile', 'profile_status')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'date_joined', 'profile__is_verified')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'profile__name', 'profile__phone_number')
    readonly_fields = ('date_joined', 'last_login')
    
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
    
    def profile_status(self, obj):
        """Get profile completion status"""
        if hasattr(obj, 'profile') and obj.profile:
            profile = obj.profile
            if profile.is_verified:
                return '✅ Complete'
            elif profile.name and profile.profile_pictures:
                return '🔄 Pending Verification'
            else:
                return '⚠️ Incomplete'
        return '❌ No Profile'
    profile_status.short_description = 'Profile Status'
    
    def get_queryset(self, request):
        """Show all users with optimized queries"""
        return super().get_queryset(request).select_related('profile').all()

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    """Admin for User Profile management (Normal Users)"""
    list_display = ('name', 'phone_number', 'gender', 'location', 'pictures_count', 'interests_count', 'is_verified', 'is_active', 'created_at')
    list_filter = ('is_verified', 'is_active', 'gender', 'created_at', 'updated_at', 'location')
    search_fields = ('name', 'phone_number', 'user__username', 'location', 'bio')
    readonly_fields = ('created_at', 'updated_at', 'user', 'pictures_count', 'interests_count')
    filter_horizontal = ('event_interests',)
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('user', 'name', 'phone_number', 'gender'),
            'description': 'Essential contact and identification information'
        }),
        ('Profile Details', {
            'fields': ('bio', 'location', 'birth_date', 'profile_pictures'),
            'description': 'Additional profile information'
        }),
        ('Event Interests', {
            'fields': ('event_interests', 'interests_count'),
            'description': 'User selected event interests (1-5 required)'
        }),
        ('Statistics', {
            'fields': ('pictures_count',),
            'classes': ('collapse',),
            'description': 'Profile completion statistics'
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
    
    def pictures_count(self, obj):
        """Count of profile pictures"""
        if obj.profile_pictures:
            count = len(obj.profile_pictures)
            status = '✅' if count >= 1 else '⚠️'
            return f'{status} {count}/6 pictures'
        return '❌ No pictures'
    pictures_count.short_description = 'Profile Pictures'
    
    def interests_count(self, obj):
        """Count of event interests"""
        count = obj.event_interests.count()
        status = '✅' if count >= 1 else '⚠️'
        return f'{status} {count}/5 interests'
    interests_count.short_description = 'Event Interests'
    
    def get_queryset(self, request):
        """Show all users with profiles (including staff/superusers)"""
        qs = super().get_queryset(request)
        return qs.prefetch_related('event_interests').all()

@admin.register(EventInterest)
class EventInterestAdmin(admin.ModelAdmin):
    """Admin for Event Interest management"""
    list_display = ('name', 'description', 'users_count', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    readonly_fields = ('created_at', 'updated_at', 'users_count')
    actions = ['activate_interests', 'deactivate_interests']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'description'),
            'description': 'Event interest details'
        }),
        ('Statistics', {
            'fields': ('users_count',),
            'classes': ('collapse',),
            'description': 'Number of users who selected this interest'
        }),
        ('Status', {
            'fields': ('is_active',),
            'description': 'Whether this interest is active for selection'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Automatically managed timestamps'
        }),
    )
    
    def users_count(self, obj):
        """Count of users who selected this interest"""
        count = obj.userprofile_set.count()
        return f'👥 {count} users'
    users_count.short_description = 'Users Count'
    
    def activate_interests(self, request, queryset):
        """Activate selected interests"""
        updated = queryset.update(is_active=True)
        self.message_user(request, f'Successfully activated {updated} interests.')
    activate_interests.short_description = "Activate selected interests"
    
    def deactivate_interests(self, request, queryset):
        """Deactivate selected interests"""
        updated = queryset.update(is_active=False)
        self.message_user(request, f'Successfully deactivated {updated} interests.')
    deactivate_interests.short_description = "Deactivate selected interests"


@admin.register(PhoneOTP)
class PhoneOTPAdmin(admin.ModelAdmin):
    """Admin for Phone OTP Lead Management"""
    list_display = ('phone_number', 'otp_code', 'verification_status', 'attempts', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'created_at', 'expires_at')
    search_fields = ('phone_number',)
    readonly_fields = ('created_at', 'expires_at', 'otp_code')
    actions = ['mark_as_verified', 'resend_otp']
    
    fieldsets = (
        ('Lead Information', {
            'fields': ('phone_number', 'otp_code'),
            'description': 'Phone number and OTP details'
        }),
        ('Verification Status', {
            'fields': ('is_verified', 'attempts'),
            'description': 'Lead verification and attempt tracking'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'expires_at'),
            'classes': ('collapse',),
            'description': 'Automatically managed timestamps'
        }),
    )
    
    def verification_status(self, obj):
        """Get verification status with emoji"""
        if obj.is_verified:
            return '✅ Verified (Converted)'
        else:
            return '📞 Unverified (Follow-up needed)'
    verification_status.short_description = 'Status'
    
    def mark_as_verified(self, request, queryset):
        """Mark selected OTPs as verified"""
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'Successfully marked {updated} leads as verified.')
    mark_as_verified.short_description = "Mark selected leads as verified"
    
    def resend_otp(self, request, queryset):
        """Regenerate OTP for selected leads"""
        from .services import twilio_service
        updated = 0
        for otp in queryset:
            otp.generate_otp()
            otp.save()
            # Note: In production, you might want to actually send SMS
            updated += 1
        self.message_user(request, f'Successfully regenerated OTP for {updated} leads.')
    resend_otp.short_description = "Regenerate OTP for selected leads"
    
    def get_queryset(self, request):
        """Order by creation date, newest first"""
        return super().get_queryset(request).order_by('-created_at')


# Customize admin site headers
admin.site.site_header = "Loopin Backend Administration"
admin.site.site_title = "Loopin Admin"
admin.site.index_title = "Welcome to Loopin Backend Administration"

# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)