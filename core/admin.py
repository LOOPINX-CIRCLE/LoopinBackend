"""
Django Admin configuration for core models.
"""

from django.contrib import admin
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from django import forms
from django.utils.html import format_html
from django.core.cache import cache
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import transaction

from .models import PlatformFeeConfig


class PlatformFeeConfigAdminForm(forms.ModelForm):
    """
    Custom admin form for Platform Fee Configuration.
    Requires password confirmation for changes and restricts to superusers.
    """
    
    password_confirmation = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'placeholder': 'Enter your password to confirm changes',
            'autocomplete': 'new-password'
        }),
        help_text="Enter your password to confirm platform fee changes. Only superusers can modify this configuration.",
        required=True,
    )
    
    class Meta:
        model = PlatformFeeConfig
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        # Request is set via get_form wrapper, not passed as kwarg
        super().__init__(*args, **kwargs)
        
        # Make password field required only when editing (not creating)
        if self.instance and self.instance.pk:
            self.fields['password_confirmation'].required = True
        else:
            self.fields['password_confirmation'].required = False
    
    def clean_password_confirmation(self):
        """Validate password confirmation"""
        password = self.cleaned_data.get('password_confirmation')
        
        if not self.request:
            raise ValidationError("Request context is required for password validation.")
        
        # Only require password when making changes (not initial creation)
        if self.instance and self.instance.pk:
            if not password:
                raise ValidationError("Password confirmation is required to modify platform fee configuration.")
            
            # Authenticate user with provided password
            user = authenticate(
                username=self.request.user.username,
                password=password
            )
            
            if not user or user != self.request.user:
                raise ValidationError("Invalid password. Please enter your correct password to confirm changes.")
            
            # Verify user is superuser
            if not self.request.user.is_superuser:
                raise ValidationError("Only superusers can modify platform fee configuration.")
        
        return password


@admin.register(PlatformFeeConfig)
class PlatformFeeConfigAdmin(admin.ModelAdmin):
    """
    Admin interface for Platform Fee Configuration.
    
    Enforces singleton pattern: only one configuration can exist.
    Provides clear UI for managing platform fee percentage.
    Requires password confirmation and superuser privileges for changes.
    """
    
    form = PlatformFeeConfigAdminForm
    
    list_display = (
        'id',
        'fee_percentage_display',
        'fee_decimal_display',
        'is_active',
        'updated_by',
        'updated_at',
    )
    
    list_filter = ('is_active', 'updated_at')
    
    fieldsets = (
        ('Security', {
            'fields': ('password_confirmation',),
            'description': (
                '<div class="help" style="padding: 10px; margin-bottom: 10px;">'
                '<strong>⚠️ Security Notice:</strong><br>'
                '• Only superusers can modify platform fee configuration<br>'
                '• Password confirmation is required for all changes<br>'
                '• This affects all financial calculations system-wide'
                '</div>'
            ),
        }),
        ('Platform Fee Configuration', {
            'fields': (
                'fee_percentage',
                'fee_percentage_display',
                'fee_decimal_display',
                'is_active',
            ),
            'description': (
                '<div class="help" style="padding: 10px; margin-bottom: 10px;">'
                '<strong>Platform Fee Model:</strong><br>'
                '• Buyer pays: Base ticket fare + Platform fee<br>'
                '• Host earns: Base ticket fare (no deduction)<br>'
                '• Platform collects: Platform fee from buyers<br><br>'
                '<strong>Example:</strong> If base fare is ₹100 and fee is 10%:<br>'
                '• Buyer pays: ₹110 (₹100 + ₹10)<br>'
                '• Host earns: ₹100<br>'
                '• Platform collects: ₹10 per ticket'
                '</div>'
            ),
        }),
        ('Additional Information', {
            'fields': ('description', 'updated_by'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    readonly_fields = (
        'id',
        'fee_percentage_display',
        'fee_decimal_display',
        'updated_by',
        'created_at',
        'updated_at',
    )
    
    def has_add_permission(self, request):
        """Prevent adding multiple configurations (singleton pattern)"""
        try:
        count = PlatformFeeConfig.objects.count()
        if count >= 1:
            return False
        # Only superusers can add (if no config exists)
        return request.user.is_superuser and super().has_add_permission(request)
        except Exception:
            # Handle case where table doesn't exist yet (before migrations)
            # Allow add permission during initial setup
            return request.user.is_superuser and super().has_add_permission(request)
    
    def has_change_permission(self, request, obj=None):
        """Only superusers can modify platform fee configuration"""
        if not request.user.is_superuser:
            return False
        return super().has_change_permission(request, obj)
    
    def has_view_permission(self, request, obj=None):
        """All staff users can view, but only superusers can modify"""
        return request.user.is_staff
    
    def has_delete_permission(self, request, obj=None):
        """Prevent deleting the configuration (must always exist)"""
        return False
    
    def get_form(self, request, obj=None, **kwargs):
        """Pass request to form for password validation"""
        Form = super().get_form(request, obj, **kwargs)
        
        class PlatformFeeConfigForm(Form):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.request = request
        
        return PlatformFeeConfigForm
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('updated_by')
    
    def save_model(self, request, obj, form, change):
        """Override save to set updated_by and clear cache"""
        # Security check: Only superusers can save
        if not request.user.is_superuser:
            messages.error(
                request,
                'Permission denied. Only superusers can modify platform fee configuration.'
            )
            raise PermissionDenied("Only superusers can modify platform fee configuration.")
        
        # Password validation is handled in form.clean_password_confirmation()
        # but we double-check here for security
        if change:
            password = form.cleaned_data.get('password_confirmation')
            if not password:
                messages.error(
                    request,
                    'Password confirmation is required to modify platform fee configuration.'
                )
                raise ValidationError("Password confirmation required.")
            
            # Verify authentication
            user = authenticate(username=request.user.username, password=password)
            if not user or user != request.user:
                messages.error(request, 'Invalid password. Changes were not saved.')
                raise ValidationError("Invalid password.")
        
        if change:
            obj.updated_by = request.user
        
        # Clear cache before saving
        cache.delete('platform_fee_percentage')
        cache.delete('platform_fee_decimal')
        cache.delete('platform_fee_config')
        
        super().save_model(request, obj, form, change)
        
        # Show success message with impact
        messages.success(
            request,
            f'Platform fee updated to {obj.fee_percentage}%. '
            f'This will affect all new payout calculations.'
        )
    
    def fee_percentage_display(self, obj):
        """Display formatted fee percentage"""
        if obj.pk:
            return format_html(
                '<strong style="color: #417690; font-size: 16px;">{}</strong>',
                obj.get_fee_percentage_display()
            )
        return '-'
    fee_percentage_display.short_description = 'Fee Percentage'
    fee_percentage_display.admin_order_field = 'fee_percentage'
    
    def fee_decimal_display(self, obj):
        """Display fee as decimal multiplier"""
        if obj.pk:
            return format_html(
                '<code>{}</code>',
                obj.get_fee_decimal_display()
            )
        return '-'
    fee_decimal_display.short_description = 'Fee Decimal'
    
    def changelist_view(self, request, extra_context=None):
        """Customize changelist to show singleton message"""
        extra_context = extra_context or {}
        
        # Get current config
        try:
            config = PlatformFeeConfig.get_current_config()
            extra_context['current_config'] = config
            extra_context['show_singleton_message'] = True
        except Exception:
            pass
        
        return super().changelist_view(request, extra_context)

