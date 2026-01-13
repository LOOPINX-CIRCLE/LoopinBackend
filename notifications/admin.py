from django.contrib import admin
from django import forms
from django.urls import path, reverse
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.safestring import mark_safe
from django.utils import timezone
import json

from notifications.models import (
    Notification, UserDevice, Campaign, CampaignExecution,
    NotificationTemplate as NotificationTemplateModel,
    TemplateVariableHint
)
from notifications.services.campaign_service import CampaignService, CampaignServiceError
from notifications.services.rule_engine import RuleEngine, RuleEngineError
from users.models import EventInterest


class CampaignAdminForm(forms.ModelForm):
    """
    Marketing-Friendly UI-Based Campaign Form
    
    Replaces JSON editing with simple form fields that non-technical users can understand.
    """
    
    # Profile-based filters - CEO-friendly options
    profile_completed = forms.ChoiceField(
        choices=[('', 'All users (don\'t filter)'), ('true', 'Yes - Only users with complete profiles'), ('false', 'No - Only users with incomplete profiles')],
        required=False,
        help_text="Filter by profile completion status"
    )
    is_verified = forms.ChoiceField(
        choices=[('', 'All users (don\'t filter)'), ('true', 'Yes - Only verified users'), ('false', 'No - Only unverified users')],
        required=False,
        help_text="Filter by verification status"
    )
    is_active = forms.ChoiceField(
        choices=[('', 'All users (don\'t filter)'), ('true', 'Yes - Only active users'), ('false', 'No - Only inactive users')],
        required=False,
        help_text="Filter by active status"
    )
    location = forms.CharField(
        required=False,
        help_text="Filter by location (e.g., 'Bangalore', 'Mumbai'). Leave empty to include all locations."
    )
    
    # Event interest filter
    event_interests = forms.ModelMultipleChoiceField(
        queryset=EventInterest.objects.filter(is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text="Select event interests. Users who have ANY of these selected interests will be included. Leave empty to include all interests."
    )
    
    # Activity filters
    has_attended_event = forms.ChoiceField(
        choices=[('', 'All users (don\'t filter)'), ('true', 'Yes - Only users who have attended events'), ('false', 'No - Only users who have never attended events')],
        required=False,
        help_text="Filter by event attendance history"
    )
    has_active_devices = forms.ChoiceField(
        choices=[('', 'All users (default: active devices only)'), ('true', 'Yes - Only users with active devices'), ('false', 'No - Only users without active devices')],
        required=False,
        help_text="Filter by active device status. For push notifications, users need active devices."
    )
    
    class Meta:
        model = Campaign
        fields = ['name', 'description', 'template', 'status']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Remove template_variables from form - we'll add dynamic fields instead
        if 'template_variables' in self.fields:
            del self.fields['template_variables']
        
        # Load existing audience_rules into form fields if editing
        if self.instance and self.instance.pk and self.instance.audience_rules:
            rules = self.instance.audience_rules
            all_rules = rules.get('all', [])
            
            for rule in all_rules:
                field = rule.get('field')
                value = rule.get('value')
                op = rule.get('op', '=')
                
                if field == 'profile_completed' and op == '=':
                    self.fields['profile_completed'].initial = 'true' if value else 'false'
                elif field == 'is_verified' and op == '=':
                    self.fields['is_verified'].initial = 'true' if value else 'false'
                elif field == 'is_active' and op == '=':
                    self.fields['is_active'].initial = 'true' if value else 'false'
                elif field == 'location':
                    if op == '=':
                        self.fields['location'].initial = value
                    elif op in ['contains', 'icontains']:
                        self.fields['location'].initial = value
                elif field == 'interest':
                    # Load interests from 'any' rules
                    if 'any' in rules:
                        interest_names = [r.get('value') for r in rules['any'] if r.get('field') == 'interest']
                        if interest_names:
                            interests = EventInterest.objects.filter(name__in=interest_names)
                            self.fields['event_interests'].initial = interests
                elif field == 'has_attended_event' and op == '=':
                    self.fields['has_attended_event'].initial = 'true' if value else 'false'
                elif field == 'has_active_devices' and op == '=':
                    self.fields['has_active_devices'].initial = 'true' if value else 'false'
        
        # Dynamically add template variable fields based on selected template
        # If editing and template is set, or if form data has template selected
        template = None
        if self.instance and self.instance.pk and self.instance.template:
            template = self.instance.template
        elif self.data and 'template' in self.data:
            try:
                template = NotificationTemplateModel.objects.get(pk=self.data['template'])
            except (NotificationTemplateModel.DoesNotExist, ValueError):
                pass
        
        if template:
            required_vars = template.get_required_variables()
            hints_dict = template.get_variable_hints_dict()
            
            # Add a field for each required variable
            for var in required_vars:
                field_name = f'template_var_{var}'
                hint = hints_dict.get(var, f'Value for {var}')
                
                self.fields[field_name] = forms.CharField(
                    required=True,
                    label=f"{{{{ {var} }}}}",
                    help_text=hint,
                    max_length=500,
                    widget=forms.TextInput(attrs={
                        'placeholder': f'Enter value for {var}',
                        'style': 'width: 100%; padding: 8px;'
                    })
                )
                
                # Load existing value if editing
                if self.instance and self.instance.pk and self.instance.template_variables:
                    if var in self.instance.template_variables:
                        self.fields[field_name].initial = self.instance.template_variables[var]
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Load existing audience_rules into form fields if editing
        if self.instance and self.instance.pk and self.instance.audience_rules:
            rules = self.instance.audience_rules
            all_rules = rules.get('all', [])
            
            for rule in all_rules:
                field = rule.get('field')
                value = rule.get('value')
                op = rule.get('op', '=')
                
                if field == 'profile_completed' and op == '=':
                    self.fields['profile_completed'].initial = 'true' if value else 'false'
                elif field == 'is_verified' and op == '=':
                    self.fields['is_verified'].initial = 'true' if value else 'false'
                elif field == 'is_active' and op == '=':
                    self.fields['is_active'].initial = 'true' if value else 'false'
                elif field == 'location':
                    if op == '=':
                        self.fields['location'].initial = value
                    elif op in ['contains', 'icontains']:
                        self.fields['location'].initial = value
                elif field == 'interest':
                    # Load interests from 'any' rules
                    if 'any' in rules:
                        interest_names = [r.get('value') for r in rules['any'] if r.get('field') == 'interest']
                        if interest_names:
                            interests = EventInterest.objects.filter(name__in=interest_names)
                            self.fields['event_interests'].initial = interests
                elif field == 'has_attended_event' and op == '=':
                    self.fields['has_attended_event'].initial = 'true' if value else 'false'
                elif field == 'has_active_devices' and op == '=':
                    self.fields['has_active_devices'].initial = 'true' if value else 'false'
        
    
    def clean(self):
        """Validate template and required variables"""
        cleaned_data = super().clean()
        template = cleaned_data.get('template')
        
        if template:
            required_vars = template.get_required_variables()
            missing_vars = []
            
            # Check all required variables are provided
            for var in required_vars:
                field_name = f'template_var_{var}'
                if field_name not in self.cleaned_data or not self.cleaned_data[field_name]:
                    missing_vars.append(var)
            
            if missing_vars:
                raise forms.ValidationError(
                    f"Please provide values for all required template variables: {', '.join([f'{{{{ {v} }}}}' for v in missing_vars])}"
                )
        
        return cleaned_data
    
    def save(self, commit=True):
        """Convert UI fields to audience_rules JSON and template_variables"""
        instance = super().save(commit=False)
        
        # Build template_variables from dynamic form fields
        if instance.template:
            required_vars = instance.template.get_required_variables()
            template_vars = {}
            for var in required_vars:
                field_name = f'template_var_{var}'
                if field_name in self.cleaned_data:
                    template_vars[var] = self.cleaned_data[field_name]
            instance.template_variables = template_vars
        
        # Build audience_rules from form fields
        all_rules = []
        any_rules = []
        
        # Profile completion
        profile_completed = self.cleaned_data.get('profile_completed')
        if profile_completed:
            all_rules.append({
                'field': 'profile_completed',
                'op': '=',
                'value': profile_completed == 'true'
            })
        
        # Verification status
        is_verified = self.cleaned_data.get('is_verified')
        if is_verified:
            all_rules.append({
                'field': 'is_verified',
                'op': '=',
                'value': is_verified == 'true'
            })
        
        # Active status
        is_active = self.cleaned_data.get('is_active')
        if is_active:
            all_rules.append({
                'field': 'is_active',
                'op': '=',
                'value': is_active == 'true'
            })
        
        # Location
        location = self.cleaned_data.get('location', '').strip()
        if location:
            all_rules.append({
                'field': 'location',
                'op': 'icontains',
                'value': location
            })
        
        # Event interests (OR logic)
        event_interests = self.cleaned_data.get('event_interests')
        if event_interests:
            for interest in event_interests:
                any_rules.append({
                    'field': 'interest',
                    'op': 'contains',
                    'value': interest.name
                })
        
        # Has attended event
        has_attended = self.cleaned_data.get('has_attended_event')
        if has_attended:
            all_rules.append({
                'field': 'has_attended_event',
                'op': '=',
                'value': has_attended == 'true'
            })
        
        # Has active devices (default to true if not specified, as it's required for push)
        has_devices = self.cleaned_data.get('has_active_devices')
        if has_devices:
            all_rules.append({
                'field': 'has_active_devices',
                'op': '=',
                'value': has_devices == 'true'
            })
        else:
            # Default: require active devices for push notifications
            all_rules.append({
                'field': 'has_active_devices',
                'op': '=',
                'value': True
            })
        
        # Build final rules structure
        audience_rules = {}
        if all_rules:
            audience_rules['all'] = all_rules
        if any_rules:
            audience_rules['any'] = any_rules
        
        instance.audience_rules = audience_rules
        
        if commit:
            instance.save()
        return instance


# ============================================================================
# NOTIFICATION TEMPLATE ADMIN
# ============================================================================

class TemplateVariableHintInline(admin.TabularInline):
    """Inline for managing template variable hints - fully UI-based!"""
    model = TemplateVariableHint
    extra = 1
    fields = ('variable_name', 'help_text')
    verbose_name = "Variable Hint"
    verbose_name_plural = "Variable Hints (Help Text for Template Variables)"
    
    def get_queryset(self, request):
        """Optimize queryset"""
        return super().get_queryset(request).select_related('template')


@admin.register(NotificationTemplateModel)
class NotificationTemplateAdmin(admin.ModelAdmin):
    """
    CEO-Level Admin for Dynamic Notification Templates
    
    Marketing team can create and manage notification templates here.
    Templates can be reused across multiple campaigns.
    """
    list_display = (
        'name',
        'key',
        'version',
        'notification_type',
        'variables_count',
        'is_immutable_indicator',
        'is_active',
        'usage_count',
        'created_at',
    )
    list_filter = ('is_active', 'notification_type', 'created_at', 'created_by')
    search_fields = ('name', 'key', 'title', 'body')
    inlines = [TemplateVariableHintInline]
    
    readonly_fields = (
        'uuid',
        'key',
        'version',
        'is_content_locked_indicator',
        'variables_preview',
        'usage_count',
        'created_by',
        'created_at',
        'updated_at',
    )
    
    fieldsets = (
        ('Template Information', {
            'fields': ('name', 'key', 'version', 'uuid'),
            'description': 'Basic template identification. Version is auto-incremented on content changes.'
        }),
        ('🔒 Immutability Status', {
            'fields': ('is_content_locked_indicator',),
            'description': '⚠️ Templates become LOCKED (immutable) once used in any campaign. Locked templates cannot have their content (title, body, target_screen, notification_type) changed. This ensures historical campaigns always reference the exact template they were created with.'
        }),
        ('Notification Content', {
            'fields': ('title', 'body', 'variables_preview'),
            'description': 'Use {{variable_name}} for dynamic content. Example: "Hi {{name}}, welcome to {{event_name}}!" or "New event: {{event_name}} by {{host_name}}". ⚠️ These fields are LOCKED if template is used in any campaign.'
        }),
        ('Configuration', {
            'fields': ('target_screen', 'notification_type'),
            'description': 'Configure where users will be directed when they tap the notification and notification type. ⚠️ These fields are LOCKED if template is used in any campaign.'
        }),
        ('Variable Hints', {
            'fields': (),
            'description': 'Add help text for each variable below. This helps marketing team understand what values to provide when creating campaigns.'
        }),
        ('Status', {
            'fields': ('is_active', 'usage_count'),
            'description': 'Usage count shows how many campaigns use this template.'
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def is_immutable_indicator(self, obj):
        """Display immutability status in list view"""
        if not obj.pk:
            return "-"
        if obj.is_immutable:
            return mark_safe(
                '<span style="background: #ff9800; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px; font-weight: bold;">🔒 LOCKED</span>'
            )
        return mark_safe(
            '<span style="background: #4caf50; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px;">✓ Editable</span>'
        )
    is_immutable_indicator.short_description = "Status"
    is_immutable_indicator.admin_order_field = 'key'
    
    def is_content_locked_indicator(self, obj):
        """Display immutability status in detail view"""
        if not obj.pk:
            return mark_safe('<em>Template will be locked once used in any campaign</em>')
        if obj.is_immutable:
            count = obj.campaigns.count()
            return mark_safe(
                f'<div style="background: #fff3cd; border-left: 4px solid #ff9800; padding: 15px; margin: 10px 0; border-radius: 4px;">'
                f'<strong style="color: #856404;">🔒 TEMPLATE IS LOCKED</strong><br>'
                f'<span style="color: #856404;">This template is used in <strong>{count}</strong> campaign(s). '
                f'Content fields (title, body, target_screen, notification_type) cannot be changed. '
                f'To make changes, create a new template version.</span>'
                f'</div>'
            )
        return mark_safe(
            '<div style="background: #d4edda; border-left: 4px solid #4caf50; padding: 15px; margin: 10px 0; border-radius: 4px;">'
            '<strong style="color: #155724;">✓ Template is editable</strong><br>'
            '<span style="color: #155724;">This template has not been used in any campaigns yet. '
            'You can freely edit all fields. Once used in a campaign, content fields will be locked.</span>'
            '</div>'
        )
    is_content_locked_indicator.short_description = "Immutability Status"
    
    def variables_preview(self, obj):
        """Show required variables"""
        if not obj.pk:
            return mark_safe('<em>Save template to see variables</em>')
        vars = obj.get_required_variables()
        if vars:
            hints_dict = obj.get_variable_hints_dict()
            var_list = []
            for var in vars:
                hint = hints_dict.get(var, '')
                if hint:
                    var_list.append(f"<strong>{{{{ {var} }}}}</strong> - {hint}")
                else:
                    var_list.append(f"<strong>{{{{ {var} }}}}</strong>")
            return mark_safe(f'<ul>{"".join([f"<li>{v}</li>" for v in var_list])}</ul>')
        return mark_safe('<em>No variables required</em>')
    variables_preview.short_description = "Required Variables"
    
    def variables_count(self, obj):
        """Count of required variables"""
        if not obj.pk:
            return "-"
        return len(obj.get_required_variables())
    variables_count.short_description = "Variables"
    variables_count.admin_order_field = 'key'
    
    def usage_count(self, obj):
        """Count of campaigns using this template"""
        if not obj.pk:
            return "-"
        count = obj.campaigns.count()
        if count > 0:
            url = reverse('admin:notifications_campaign_changelist') + f'?template__id__exact={obj.pk}'
            return mark_safe(f'<a href="{url}">{count}</a>')
        return "0"
    usage_count.short_description = "Used In Campaigns"
    
    def get_readonly_fields(self, request, obj=None):
        """
        Enforce template immutability rules.
        
        IMMUTABILITY ENFORCEMENT:
        - Key is always readonly after creation (cannot change)
        - Content fields (title, body, target_screen, notification_type) are readonly if template is used in any campaign
        - Version is auto-managed, readonly in admin
        - This ensures historical campaigns always reference the exact template they were created with
        """
        readonly = list(self.readonly_fields)
        if obj and obj.pk:
            readonly.append('key')  # Key cannot be changed after creation
            if obj.is_immutable:
                # Lock content fields if template is used in any campaign
                readonly.extend(['title', 'body', 'target_screen', 'notification_type'])
        return readonly
    
    def save_model(self, request, obj, form, change):
        """
        Handle template saves with versioning and immutability enforcement.
        
        VERSIONING RULE:
        - Version starts at 1 for new templates
        - Version increments on meaningful content changes (title, body, target_screen, notification_type)
        - Each version is stored as a separate record (unique_together: key, version)
        - Campaigns store immutable template_version snapshot
        """
        if change and obj.pk:
            # Check if content fields changed
            old_obj = NotificationTemplateModel.objects.get(pk=obj.pk)
            content_fields = ['title', 'body', 'target_screen', 'notification_type']
            content_changed = any(
                getattr(old_obj, field) != getattr(obj, field)
                for field in content_fields
            )
            
            # Enforce immutability: cannot change content if used in campaigns
            if content_changed and obj.is_immutable:
                from django.contrib import messages
                messages.error(
                    request,
                    f"Cannot modify content fields (title, body, target_screen, notification_type) "
                    f"because this template is used in {obj.campaigns.count()} campaign(s). "
                    f"Templates are immutable once used to preserve historical accuracy. "
                    f"Create a new template if you need different content."
                )
                # Restore old values
                obj.title = old_obj.title
                obj.body = old_obj.body
                obj.target_screen = old_obj.target_screen
                obj.notification_type = old_obj.notification_type
                return  # Don't save changes
            
            # Increment version on content changes (if not locked)
            if content_changed and not obj.is_immutable:
                obj.version = old_obj.version + 1
        
        if not change:
            obj.created_by = request.user
        
        super().save_model(request, obj, form, change)


# ============================================================================
# USER DEVICE ADMIN
# ============================================================================

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
    """
    CEO-level admin interface for Notifications.
    
    Features:
    - Rich display with campaign tracking
    - Read/unread status badges
    - Campaign relationship display
    - Performance-optimized queries
    """
    list_display = (
        'type_badge',
        'recipient_link',
        'title_short',
        'campaign_link',
        'is_read_badge',
        'created_at',
    )
    list_filter = (
        'type',
        'is_read',
        'campaign',
        ('created_at', admin.DateFieldListFilter),
    )
    search_fields = (
        'title',
        'message',
        'recipient__phone_number',
        'recipient__name',
        'sender__name',
        'campaign__name',
        'reference_id',
    )
    readonly_fields = (
        'uuid',
        'created_at',
        'updated_at',
        'campaign_link_display',
        'type_badge_display',
        'is_read_badge_display',
    )
    fieldsets = (
        ('Recipients', {
            'fields': ('recipient', 'sender')
        }),
        ('Notification Content', {
            'fields': ('type', 'type_badge_display', 'title', 'message', 'metadata')
        }),
        ('Campaign Tracking', {
            'fields': ('campaign', 'campaign_link_display'),
            'description': 'Links to campaign if this notification was sent via a campaign',
            'classes': ('collapse',)
        }),
        ('Reference', {
            'fields': ('reference_type', 'reference_id'),
            'classes': ('collapse',)
        }),
        ('Status', {
            'fields': ('is_read', 'is_read_badge_display')
        }),
        ('Timestamps', {
            'fields': ('uuid', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    autocomplete_fields = ['recipient', 'sender', 'campaign']
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('recipient', 'sender', 'campaign').order_by('-created_at')
    
    def type_badge(self, obj):
        """Display type with badge"""
        type_colors = {
            'event_request': '#2196f3',
            'event_invite': '#4caf50',
            'event_update': '#ff9800',
            'event_cancelled': '#f44336',
            'payment_success': '#4caf50',
            'payment_failed': '#f44336',
            'reminder': '#9c27b0',
            'system': '#607d8b',
            'promotional': '#e91e63',
        }
        color = type_colors.get(obj.type, '#9e9e9e')
        return mark_safe(f'<span style="background: {color}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px; text-transform: uppercase;">{obj.get_type_display()}</span>')
    type_badge.short_description = "Type"
    type_badge.admin_order_field = 'type'
    
    def type_badge_display(self, obj):
        """Display type badge in detail view"""
        return self.type_badge(obj)
    type_badge_display.short_description = "Type"
    
    def recipient_link(self, obj):
        """Link to recipient"""
        url = reverse('admin:users_userprofile_change', args=[obj.recipient_id])
        name = obj.recipient.name or obj.recipient.phone_number
        return mark_safe(f'<a href="{url}">{name}</a>')
    recipient_link.short_description = "Recipient"
    recipient_link.admin_order_field = 'recipient__name'
    
    def title_short(self, obj):
        """Display shortened title"""
        from html import escape
        if len(obj.title) > 50:
            escaped_title = escape(obj.title)
            return mark_safe(f'<span title="{escaped_title}">{escape(obj.title[:47])}...</span>')
        return obj.title
    title_short.short_description = "Title"
    title_short.admin_order_field = 'title'
    
    def campaign_link(self, obj):
        """Display campaign link if exists"""
        if obj.campaign:
            from html import escape
            url = reverse('admin:notifications_campaign_change', args=[obj.campaign_id])
            campaign_name = obj.campaign.name[:30] + '...' if len(obj.campaign.name) > 30 else obj.campaign.name
            escaped_name = escape(campaign_name)
            return mark_safe(f'<a href="{url}" style="color: #9c27b0;">📢 {escaped_name}</a>')
        return mark_safe('<span style="color: gray;">-</span>')
    campaign_link.short_description = "Campaign"
    campaign_link.admin_order_field = 'campaign__name'
    
    def campaign_link_display(self, obj):
        """Display campaign link in detail view"""
        return self.campaign_link(obj)
    campaign_link_display.short_description = "Campaign"
    
    def is_read_badge(self, obj):
        """Display read status with badge"""
        if not obj:
            return mark_safe('<span style="color: gray;">Not set</span>')
        if obj.is_read:
            return mark_safe(
                '<span style="background: #4caf50; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px;">✓ Read</span>'
            )
        return mark_safe(
            '<span style="background: #ff9800; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px;">📬 Unread</span>'
        )
    is_read_badge.short_description = "Status"
    is_read_badge.admin_order_field = 'is_read'
    # Note: boolean = True removed - this returns HTML, not a boolean
    
    def is_read_badge_display(self, obj):
        """Display read badge in detail view"""
        return self.is_read_badge(obj)
    is_read_badge_display.short_description = "Read Status"
    
    actions = ['mark_as_read', 'mark_as_unread']
    
    def mark_as_read(self, request, queryset):
        """Mark notifications as read"""
        count = queryset.update(is_read=True)
        self.message_user(request, f'✅ {count} notification(s) marked as read.')
    mark_as_read.short_description = "Mark selected as read"
    
    def mark_as_unread(self, request, queryset):
        """Mark notifications as unread"""
        count = queryset.update(is_read=False)
        self.message_user(request, f'📬 {count} notification(s) marked as unread.')
    mark_as_unread.short_description = "Mark selected as unread"


# ============================================================================
# CAMPAIGN EXECUTION INLINE
# ============================================================================

class CampaignExecutionInline(admin.TabularInline):
    """Inline for viewing campaign execution records"""
    model = CampaignExecution
    extra = 0
    readonly_fields = ('user_profile', 'notification', 'sent_successfully', 'error_message', 'delivered_at', 'created_at')
    fields = ('user_profile', 'sent_successfully', 'error_message', 'delivered_at')
    can_delete = False
    show_change_link = True
    verbose_name = "Execution Record"
    verbose_name_plural = "Execution Records"
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user_profile', 'notification', 'campaign').order_by('-created_at')[:50]  # Limit for performance


# ============================================================================
# CAMPAIGN ADMIN
# ============================================================================

@admin.register(Campaign)
class CampaignAdmin(admin.ModelAdmin):
    """
    Amazing admin interface for Notification Campaigns
    
    Features:
    - Rich rule builder UI
    - Template selector with preview
    - Audience preview before sending
    - Safe execution with confirmation
    - Comprehensive audit trail
    """
    
    form = CampaignAdminForm
    
    list_display = (
        'name',
        'template_display',
        'status_badge',
        'preview_count_display',
        'results_display',
        'created_by',
        'sent_at_display',
        'actions_display'
    )
    list_filter = ('status', 'template', 'created_at', 'sent_at', 'created_by')
    search_fields = ('name', 'description', 'template__name', 'template__key')
    readonly_fields = (
        'uuid',
        'template_version',
        'status',
        'preview_count',
        'preview_computed_at',
        'sent_at',
        'sent_by',
        'total_sent',
        'total_failed',
        'execution_metadata_display',
        'cancelled_at',
        'cancelled_by',
        'created_by',
        'created_at',
        'updated_at',
        'audience_description',
        'template_preview',
        'preview_button'
    )
    
    fieldsets = (
        ('Campaign Information', {
            'fields': ('name', 'description', 'uuid')
        }),
        ('Template Selection', {
            'fields': ('template', 'template_version', 'template_preview'),
            'description': 'Select a notification template (create new templates in Notification Templates). Template version is automatically captured when campaign is created for audit trail. After selecting template, template variable fields will appear below.'
        }),
        ('Template Variables', {
            'fields': (),
            'description': 'Fill in the values for template variables here. These fields appear automatically after you select a template above.'
        }),
        ('🎯 Audience Selection (Marketing-Friendly)', {
            'fields': (
                'profile_completed',
                'is_verified',
                'is_active',
                'location',
                'event_interests',
                'has_attended_event',
                'has_active_devices',
            ),
            'description': '🎯 AUDIENCE LOGIC: All filters use AND logic (user must match ALL selected conditions). Event interests use OR logic (user must have ANY selected interest). Final: (ALL filters) AND (ANY selected interests). Leave dropdowns as "All users (don\'t filter)" to skip that filter. Use negative options (e.g., "No - Only users with incomplete profiles") to exclude users.'
        }),
        ('Audience Preview', {
            'fields': ('audience_description', 'preview_button', 'preview_count', 'preview_computed_at'),
            'description': 'Preview how many users match your selection before sending.'
        }),
        ('Status & Execution', {
            'fields': ('status', 'sent_at', 'sent_by', 'total_sent', 'total_failed', 'execution_metadata_display'),
            'classes': ('collapse',)
        }),
        ('Cancellation', {
            'fields': ('cancelled_at', 'cancelled_by', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    inlines = [CampaignExecutionInline]
    
    actions = ['preview_campaigns', 'cancel_campaigns']
    
    # Note: Custom CSS/JS files can be added later if needed
    # class Media:
    #     css = {
    #         'all': ('admin/css/campaign_admin.css',)
    #     }
    #     js = ('admin/js/campaign_admin.js',)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<path:object_id>/preview/', self.admin_site.admin_view(self.preview_view), name='notifications_campaign_preview'),
            path('<path:object_id>/execute/', self.admin_site.admin_view(self.execute_view), name='notifications_campaign_execute'),
        ]
        return custom_urls + urls
    
    def get_readonly_fields(self, request, obj=None):
        """Make fields readonly after campaign is sent"""
        readonly = list(self.readonly_fields)
        if obj and obj.is_immutable:
            readonly.extend(['name', 'description', 'template', 'template_variables', 'audience_rules'])
            # Also make UI fields readonly
            readonly.extend(['profile_completed', 'is_verified', 'is_active', 'location', 'event_interests', 'has_attended_event', 'has_active_devices'])
        return readonly
    
    def save_model(self, request, obj, form, change):
        """Set created_by on creation and log audit"""
        if not change:
            obj.created_by = request.user
            # Audit log campaign creation
            try:
                from audit.models import AuditLog
                AuditLog.log_action(
                    user=request.user,
                    action='campaign_create',
                    object_type='Campaign',
                    object_id=obj.id if obj.id else None,
                    payload={
                        'campaign_name': obj.name,
                        'template': obj.template.key if obj.template else None,
                        'status': obj.status
                    },
                    severity='medium'
                )
            except Exception:
                pass  # Don't fail if audit logging fails
        super().save_model(request, obj, form, change)
    
    def template_display(self, obj):
        """Display template with badge and link"""
        if obj.template:
            from html import escape
            url = reverse('admin:notifications_notificationtemplate_change', args=[obj.template.pk])
            escaped_name = escape(obj.template.name)
            return mark_safe(f'<a href="{url}" style="background: #e3f2fd; padding: 4px 8px; border-radius: 4px; font-size: 11px; text-decoration: none; color: #1976d2;">{escaped_name}</a>')
        return "-"
    template_display.short_description = "Template"
    template_display.admin_order_field = 'template__name'
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'draft': '#9e9e9e',
            'previewed': '#2196f3',
            'scheduled': '#ff9800',
            'sending': '#ff5722',
            'sent': '#4caf50',
            'cancelled': '#f44336',
            'failed': '#e91e63',
        }
        color = colors.get(obj.status, '#9e9e9e')
        return mark_safe(f'<span style="background: {color}; color: white; padding: 4px 8px; border-radius: 4px; font-size: 11px; font-weight: bold;">{obj.get_status_display()}</span>')
    status_badge.short_description = "Status"
    status_badge.admin_order_field = 'status'
    
    def preview_count_display(self, obj):
        """Display preview count"""
        if obj.preview_count is not None:
            return mark_safe(f'<span style="font-weight: bold;">{obj.preview_count:,}</span> users')
        return mark_safe('<span style="color: #f44336;">Not previewed</span>')
    preview_count_display.short_description = "Audience Size"
    
    def results_display(self, obj):
        """Display execution results"""
        if obj.status == 'sent':
            success_rate = (obj.total_sent / (obj.total_sent + obj.total_failed) * 100) if (obj.total_sent + obj.total_failed) > 0 else 0
            return mark_safe(
                f'<div style="font-size: 11px;">'
                f'<span style="color: #4caf50;">✓ {obj.total_sent:,}</span><br>'
                f'<span style="color: #f44336;">✗ {obj.total_failed:,}</span><br>'
                f'<span style="color: #2196f3;">{success_rate:.1f}% success</span>'
                f'</div>'
            )
        return "-"
    results_display.short_description = "Results"
    
    def sent_at_display(self, obj):
        """Display sent at time"""
        if obj.sent_at:
            return obj.sent_at.strftime('%Y-%m-%d %H:%M')
        return "-"
    sent_at_display.short_description = "Sent At"
    sent_at_display.admin_order_field = 'sent_at'
    
    def actions_display(self, obj):
        """Display action buttons"""
        actions = []
        if obj.can_be_sent:
            if obj.preview_count is None:
                actions.append(
                    mark_safe(f'<a href="{reverse("admin:notifications_campaign_preview", args=[obj.pk])}" class="button" style="background: #2196f3; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; margin-right: 5px;">Preview</a>')
                )
            else:
                actions.append(
                    mark_safe(f'<a href="{reverse("admin:notifications_campaign_execute", args=[obj.pk])}" class="button" style="background: #4caf50; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none; margin-right: 5px;">Send</a>')
                )
        if obj.status in ['draft', 'previewed', 'scheduled']:
            actions.append(
                mark_safe(f'<a href="{reverse("admin:notifications_campaign_change", args=[obj.pk])}?cancel=1" class="button" style="background: #f44336; color: white; padding: 6px 12px; border-radius: 4px; text-decoration: none;">Cancel</a>')
            )
        return mark_safe(' '.join(actions)) if actions else "-"
    actions_display.short_description = "Actions"
    
    def audience_description(self, obj):
        """Display human-readable audience description"""
        if obj.audience_rules:
            try:
                description = RuleEngine.generate_human_readable_description(obj.audience_rules)
                return mark_safe(f'<div style="padding: 10px; background: #f5f5f5; border-radius: 4px;">{description}</div>')
            except Exception as e:
                return mark_safe(f'<span style="color: #f44336;">Error: {str(e)}</span>')
        return "-"
    audience_description.short_description = "Audience Description"
    
    def template_preview(self, obj):
        """Display template preview"""
        if obj and obj.template:
            try:
                preview_title = obj.template.title
                preview_body = obj.template.body
                
                # Replace variables if provided
                if obj.template_variables:
                    for key, value in obj.template_variables.items():
                        preview_title = preview_title.replace(f'{{{{{key}}}}}', str(value))
                        preview_body = preview_body.replace(f'{{{{{key}}}}}', str(value))
                
                # Check for unreplaced variables
                import re
                missing_vars = set(re.findall(r'\{\{(\w+)\}\}', preview_title + preview_body))
                warning = ""
                if missing_vars:
                    missing_vars_str = ', '.join([f"{{{{ {v} }}}}" for v in missing_vars])
                    warning = mark_safe(
                        f'<div style="margin-top: 8px; padding: 8px; background: #fff3cd; border-radius: 4px; font-size: 11px; color: #856404;">'
                        f'⚠️ Missing variables: {missing_vars_str}</div>'
                    )
                
                from html import escape
                escaped_title = escape(preview_title)
                escaped_body = escape(preview_body)
                return mark_safe(
                    f'<div style="border: 1px solid #ddd; border-radius: 4px; padding: 15px; background: white;">'
                    f'<div style="font-weight: bold; margin-bottom: 8px; color: #333;">{escaped_title}</div>'
                    f'<div style="color: #666; font-size: 13px;">{escaped_body}</div>'
                    f'<div style="margin-top: 8px; font-size: 11px; color: #999;">Target Screen: {obj.template.target_screen}</div>'
                    f'{warning}'
                    f'</div>'
                )
            except Exception as e:
                return mark_safe(f'<span style="color: #f44336;">Error: {str(e)}</span>')
        return mark_safe('<span style="color: #999;">Select a template to preview</span>')
    template_preview.short_description = "Template Preview"
    
    def preview_button(self, obj):
        """Display preview button"""
        if obj.pk:
            return mark_safe(f'<a href="{reverse("admin:notifications_campaign_preview", args=[obj.pk])}" class="button" style="background: #2196f3; color: white; padding: 10px 20px; border-radius: 4px; text-decoration: none; display: inline-block; margin-top: 10px;">Preview Audience</a>')
        return mark_safe('<span style="color: #999;">Save campaign first to preview</span>')
    preview_button.short_description = "Preview"
    
    def execution_metadata_display(self, obj):
        """Display execution metadata in readable format"""
        if obj.execution_metadata:
            return mark_safe(f'<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto;">{json.dumps(obj.execution_metadata, indent=2)}</pre>')
        return "-"
    execution_metadata_display.short_description = "Execution Metadata"
    
    def preview_view(self, request, object_id):
        """Preview campaign audience"""
        campaign = Campaign.objects.get(pk=object_id)
        
        if request.method == 'POST':
            try:
                preview_result = CampaignService.preview_campaign(campaign, request.user)
                messages.success(
                    request,
                    f'Preview complete: {preview_result["count"]:,} users match the audience rules.'
                )
                return redirect('admin:notifications_campaign_change', object_id)
            except CampaignServiceError as e:
                messages.error(request, str(e))
            except Exception as e:
                messages.error(request, f'Preview failed: {str(e)}')
        
        # Get preview (or recompute)
        preview_result = None
        try:
            preview_result = RuleEngine.preview_audience(campaign.audience_rules)
        except Exception as e:
            messages.error(request, f'Error previewing audience: {str(e)}')
        
        context = {
            **self.admin_site.each_context(request),
            'campaign': campaign,
            'preview_result': preview_result,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request, campaign),
        }
        
        return render(request, 'admin/notifications/campaign_preview.html', context)
    
    def execute_view(self, request, object_id):
        """Execute campaign"""
        campaign = Campaign.objects.get(pk=object_id)
        
        if request.method == 'POST':
            if 'confirm' in request.POST:
                try:
                    result = CampaignService.execute_campaign(campaign, request.user)
                    messages.success(
                        request,
                        f'Campaign sent successfully! {result["total_sent"]:,} notifications sent, '
                        f'{result["total_failed"]:,} failed.'
                    )
                    return redirect('admin:notifications_campaign_change', object_id)
                except CampaignServiceError as e:
                    messages.error(request, str(e))
                except Exception as e:
                    messages.error(request, f'Execution failed: {str(e)}')
            else:
                messages.error(request, 'Execution cancelled.')
        
        # Show confirmation page
        context = {
            **self.admin_site.each_context(request),
            'campaign': campaign,
            'opts': self.model._meta,
            'has_view_permission': self.has_view_permission(request, campaign),
        }
        
        return render(request, 'admin/notifications/campaign_execute.html', context)
    
    def preview_campaigns(self, request, queryset):
        """Bulk preview campaigns"""
        count = 0
        for campaign in queryset:
            if campaign.can_be_sent:
                try:
                    CampaignService.preview_campaign(campaign, request.user)
                    count += 1
                except Exception as e:
                    self.message_user(request, f'Error previewing {campaign.name}: {str(e)}', level=messages.ERROR)
        
        self.message_user(request, f'{count} campaign(s) previewed successfully.')
    preview_campaigns.short_description = "Preview selected campaigns"
    
    def cancel_campaigns(self, request, queryset):
        """Bulk cancel campaigns"""
        count = 0
        for campaign in queryset:
            if campaign.status in ['draft', 'previewed', 'scheduled']:
                try:
                    campaign.cancel(request.user, "Bulk cancelled from admin")
                    count += 1
                except Exception as e:
                    self.message_user(request, f'Error cancelling {campaign.name}: {str(e)}', level=messages.ERROR)
        
        self.message_user(request, f'{count} campaign(s) cancelled successfully.')
    cancel_campaigns.short_description = "Cancel selected campaigns"


@admin.register(CampaignExecution)
class CampaignExecutionAdmin(admin.ModelAdmin):
    """Admin for campaign execution records"""
    list_display = ('campaign', 'user_profile', 'sent_successfully_badge', 'delivered_at', 'created_at')
    list_filter = ('sent_successfully', 'delivered_at', 'created_at', 'campaign')
    search_fields = ('campaign__name', 'user_profile__name', 'user_profile__phone_number', 'error_message')
    readonly_fields = ('campaign', 'notification', 'user_profile', 'sent_successfully', 'error_message', 'onesignal_response', 'delivered_at', 'created_at', 'updated_at')
    
    def sent_successfully_badge(self, obj):
        """Display success status with badge"""
        if obj.sent_successfully:
            return mark_safe('<span style="color: #4caf50; font-weight: bold;">✓ Success</span>')
        else:
            return mark_safe('<span style="color: #f44336; font-weight: bold;">✗ Failed</span>')
    sent_successfully_badge.short_description = "Status"
    sent_successfully_badge.admin_order_field = 'sent_successfully'
    
    def has_add_permission(self, request):
        return False
