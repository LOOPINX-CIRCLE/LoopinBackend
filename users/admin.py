from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.http import HttpResponse, HttpResponseRedirect
from django.db.models import Count
from django.utils.text import Truncator
from django.urls import reverse
from django.utils.html import format_html

from .forms import HostLeadWhatsAppForm
from .models import (
    BankAccount,
    EventInterest,
    HostLead,
    HostPayoutRequest,
    HostLeadWhatsAppMessage,
    HostLeadWhatsAppTemplate,
    PhoneOTP,
    UserProfile,
)
from .services import TwilioConfigurationError, TwilioServiceError, get_twilio_service

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


@admin.register(HostLeadWhatsAppTemplate)
class HostLeadWhatsAppTemplateAdmin(admin.ModelAdmin):
    """Admin for managing reusable host lead WhatsApp templates"""
    list_display = ('name', 'message_preview', 'usage_count')
    search_fields = ('name', 'message')
    fields = ('name', 'message')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.annotate(usage_count=Count('messages'))

    def message_preview(self, obj):
        return Truncator(obj.message).chars(80)
    message_preview.short_description = "Message"

    def usage_count(self, obj):
        return getattr(obj, 'usage_count', 0)
    usage_count.short_description = "Times Used"


@admin.register(HostLeadWhatsAppMessage)
class HostLeadWhatsAppMessageAdmin(admin.ModelAdmin):
    """Read-only log of WhatsApp communications with host leads"""
    list_display = ('lead', 'status', 'twilio_sid', 'sent_by', 'created_at')
    list_filter = ('status', 'created_at', 'template')
    search_fields = ('lead__first_name', 'lead__last_name', 'lead__phone_number', 'twilio_sid', 'error_code')
    readonly_fields = (
        'lead',
        'template',
        'content_sid',
        'variables',
        'body_variable',
        'status',
        'twilio_sid',
        'error_code',
        'error_message',
        'sent_by',
        'created_at',
        'updated_at',
    )
    
    fieldsets = (
        ('Recipient', {
            'fields': ('lead', 'template', 'sent_by', 'status'),
        }),
        ('Message Details', {
            'fields': ('content_sid', 'variables', 'body_variable', 'twilio_sid'),
        }),
        ('Errors', {
            'fields': ('error_code', 'error_message'),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    
    def has_view_permission(self, request, obj=None):
        return True


# Customize admin site headers
admin.site.site_header = "Loopin Backend Administration"
admin.site.site_title = "Loopin Admin"
admin.site.index_title = "Welcome to Loopin Backend Administration"


class HostLeadWhatsAppMessageInline(admin.TabularInline):
    """Readonly log of WhatsApp messages sent to host leads"""
    model = HostLeadWhatsAppMessage
    fields = (
        'created_at',
        'template',
        'body_variable',
        'status',
        'twilio_sid',
        'error_code',
        'error_message',
        'sent_by',
    )
    readonly_fields = fields
    extra = 0
    can_delete = False
    show_change_link = False
    ordering = ('-created_at',)
    verbose_name = "WhatsApp Message"
    verbose_name_plural = "WhatsApp Message History"


@admin.register(HostLead)
class HostLeadAdmin(admin.ModelAdmin):
    """Admin for 'Become a Host' Lead Management"""
    change_form_template = "admin/users/hostlead/change_form.html"
    list_display = (
        'full_name',
        'phone_number',
        'is_contacted',
        'is_converted',
        'status_badge',
        'last_whatsapp_status',
        'send_whatsapp_action',
        'created_at',
        'days_since_submission',
    )
    list_filter = ('is_contacted', 'is_converted', 'created_at', 'updated_at')
    search_fields = ('first_name', 'last_name', 'phone_number', 'notes')
    readonly_fields = ('created_at', 'updated_at')
    date_hierarchy = 'created_at'
    actions = ['mark_as_contacted', 'mark_as_converted', 'mark_as_uncontacted']
    ordering = ('-created_at',)
    inlines = (HostLeadWhatsAppMessageInline,)
    
    fieldsets = (
        ('Lead Information', {
            'fields': ('first_name', 'last_name', 'phone_number', 'message'),
            'description': 'Basic contact information of the potential host'
        }),
        ('Lead Status', {
            'fields': ('is_contacted', 'is_converted'),
            'description': 'Track lead progress and conversion status'
        }),
        ('Internal Notes', {
            'fields': ('notes',),
            'description': 'Add any notes about communication or follow-ups'
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
            'description': 'Automatically managed timestamps'
        }),
    )
    
    def full_name(self, obj):
        """Display full name"""
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Name'
    
    def status_badge(self, obj):
        """Get status with color-coded emoji"""
        if obj.is_converted:
            return '✅ Converted to Host'
        elif obj.is_contacted:
            return '📞 Contacted - Awaiting Response'
        else:
            return '🆕 New Lead - Action Needed'
    status_badge.short_description = 'Status'
    
    def days_since_submission(self, obj):
        """Calculate days since submission"""
        from django.utils import timezone
        delta = timezone.now() - obj.created_at
        days = delta.days
        if days == 0:
            return '📅 Today'
        elif days == 1:
            return '📅 1 day ago'
        elif days < 7:
            return f'📅 {days} days ago'
        elif days < 30:
            return f'📅 {days // 7} weeks ago'
        else:
            return f'📅 {days // 30} months ago'
    days_since_submission.short_description = 'Age'
    
    def mark_as_contacted(self, request, queryset):
        """Mark selected leads as contacted"""
        updated = queryset.update(is_contacted=True)
        self.message_user(request, f'✅ Successfully marked {updated} lead(s) as contacted.')
    mark_as_contacted.short_description = "Mark selected leads as contacted"
    
    def mark_as_converted(self, request, queryset):
        """Mark selected leads as converted to hosts"""
        updated = queryset.update(is_converted=True, is_contacted=True)
        self.message_user(request, f'✅ Successfully marked {updated} lead(s) as converted hosts!')
    mark_as_converted.short_description = "Mark selected leads as converted (hosts)"
    
    def mark_as_uncontacted(self, request, queryset):
        """Reset contact status for selected leads"""
        updated = queryset.update(is_contacted=False)
        self.message_user(request, f'✅ Successfully reset contact status for {updated} lead(s).')
    mark_as_uncontacted.short_description = "Reset contact status"
    
    def export_to_csv(self, request, queryset):
        """Export selected leads to CSV"""
        import csv
        from django.http import HttpResponse
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="host_leads.csv"'
        
        writer = csv.writer(response)
        writer.writerow(['First Name', 'Last Name', 'Phone Number', 'Message', 'Contacted', 'Converted', 'Submitted Date', 'Notes'])
        
        for lead in queryset:
            writer.writerow([
                lead.first_name,
                lead.last_name,
                lead.phone_number,
                lead.message,
                'Yes' if lead.is_contacted else 'No',
                'Yes' if lead.is_converted else 'No',
                lead.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                lead.notes
            ])
        
        return response
    export_to_csv.short_description = "Export selected leads to CSV"
    actions.append(export_to_csv)
    
    def get_queryset(self, request):
        """Optimize queryset with all fields"""
        qs = super().get_queryset(request).all()
        return qs.prefetch_related('whatsapp_messages')
    
    def export_new_leads_to_csv(self, request, queryset):
        """Export only new (uncontacted) leads to CSV"""
        new_leads = queryset.filter(is_contacted=False)
        self.export_to_csv(request, new_leads)
    export_new_leads_to_csv.short_description = "Export new (uncontacted) leads to CSV"
    actions.append(export_new_leads_to_csv)

    def last_whatsapp_status(self, obj):
        """Return latest WhatsApp send status for quick scanning"""
        message = getattr(obj, 'whatsapp_messages', None)
        if message is None:
            message = obj.whatsapp_messages
        latest = message.order_by('-created_at').first()
        if not latest:
            return '—'
        status_icon = {
            'sent': '✅',
            'delivered': '📬',
            'undelivered': '⚠️',
            'failed': '❌',
            'queued': '⏳',
            'test-mode': '🧪',
        }.get(latest.status, 'ℹ️')
        return f"{status_icon} {latest.status.title()}"
    last_whatsapp_status.short_description = 'WhatsApp Status'

    def send_whatsapp_action(self, obj):
        """Button that routes to the change page WhatsApp composer"""
        url = reverse('admin:users_hostlead_change', args=[obj.pk])
        return format_html('<a class="button" href="{}#whatsapp">Compose WhatsApp</a>', url)
    send_whatsapp_action.short_description = 'Send WhatsApp'

    def _recommendation_queryset(self):
        return HostLeadWhatsAppTemplate.objects.annotate(
            usage_count=Count('messages')
        ).order_by('-usage_count', 'name', 'id')

    def changeform_view(self, request, object_id=None, form_url='', extra_context=None):
        extra_context = extra_context or {}
        lead = None
        if object_id:
            lead = self.get_object(request, object_id)
        templates_qs = self._recommendation_queryset()

        if request.method == 'POST' and '_send_whatsapp' in request.POST:
            form = HostLeadWhatsAppForm(request.POST, templates_qs=templates_qs)
            if not lead:
                messages.error(request, "Lead not found. Please try again.")
            elif form.is_valid():
                template = form.cleaned_data.get('template')
                message_text = form.cleaned_data['whatsapp_message'].strip()

                template = form.cleaned_data.get("template")

                try:
                    twilio_service_instance = get_twilio_service()
                except TwilioConfigurationError as exc:
                    form.add_error(None, f"Twilio configuration error: {exc}")
                except TwilioServiceError as exc:
                    form.add_error(None, f"Twilio service error: {exc}")
                else:
                    content_sid = twilio_service_instance.config.whatsapp_content_sid
                    if not content_sid:
                        form.add_error(None, "WhatsApp template SID is not configured. Set TWILIO_WHATSAPP_TEMPLATE_SID in the environment.")
                    else:
                        content_variables = {
                            "1": lead.first_name or lead.last_name or "",
                            "2": message_text,
                        }
                        success, response_msg, details = twilio_service_instance.send_whatsapp_message(
                            phone_number=lead.phone_number,
                            content_sid=content_sid,
                            content_variables=content_variables,
                        )

                        status = details.get("status") or ("sent" if success else "failed")
                        twilio_sid = details.get("sid") or ""
                        error_code = details.get("error_code") or ""
                        error_message = "" if success else response_msg

                        HostLeadWhatsAppMessage.objects.create(
                            lead=lead,
                            template=template,
                            content_sid=content_sid,
                            variables=content_variables,
                            body_variable=message_text,
                            status=status,
                            twilio_sid=twilio_sid,
                            error_code=error_code,
                            error_message=error_message,
                            sent_by=request.user,
                        )

                        if success:
                            if not lead.is_contacted:
                                lead.is_contacted = True
                                lead.save(update_fields=['is_contacted', 'updated_at'])
                            messages.success(request, f"WhatsApp message queued successfully: {response_msg}")
                        else:
                            messages.error(request, f"Failed to send WhatsApp message: {response_msg}")

                        return HttpResponseRedirect(request.path)
            extra_context['whatsapp_form'] = form
        else:
            extra_context.setdefault('whatsapp_form', HostLeadWhatsAppForm(templates_qs=templates_qs))

        extra_context['whatsapp_recommendations'] = templates_qs
        return super().changeform_view(request, object_id, form_url, extra_context=extra_context)

# ============================================================================
# Bank Account Admin
# ============================================================================

@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    """Admin for managing host bank accounts"""
    list_display = (
        'id',
        'account_holder_name',
        'bank_name',
        'masked_account_number_display',
        'ifsc_code',
        'host',
        'is_primary',
        'is_verified',
        'is_active',
        'created_at',
    )
    list_filter = ('is_primary', 'is_verified', 'is_active', 'created_at', 'bank_name')
    search_fields = (
        'account_holder_name',
        'bank_name',
        'account_number',
        'ifsc_code',
        'host__username',
        'host__email',
        'host__first_name',
        'host__last_name',
    )
    readonly_fields = ('uuid', 'masked_account_number', 'created_at', 'updated_at')
    raw_id_fields = ('host',)
    
    fieldsets = (
        ('Account Information', {
            'fields': (
                'uuid',
                'host',
                'account_holder_name',
                'bank_name',
                'account_number',
                'ifsc_code',
            )
        }),
        ('Status & Verification', {
            'fields': (
                'is_primary',
                'is_verified',
                'is_active',
            )
        }),
        ('Security', {
            'fields': ('masked_account_number',),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    def masked_account_number_display(self, obj):
        """Display masked account number in list view"""
        return obj.masked_account_number
    masked_account_number_display.short_description = 'Account Number'


# ============================================================================
# Host Payout Request Admin
# ============================================================================

@admin.register(HostPayoutRequest)
class HostPayoutRequestAdmin(admin.ModelAdmin):
    """Admin for managing host payout requests"""
    list_display = (
        'id',
        'event_name_display',
        'host_name',
        'event_date',
        'total_tickets_sold',
        'final_earning_display',
        'platform_fee_amount_display',
        'status',
        'created_at',
        'processed_at',
    )
    list_filter = ('status', 'created_at', 'processed_at', 'event_date')
    search_fields = (
        'event_name',
        'host_name',
        'event_location',
        'bank_account__account_holder_name',
        'bank_account__bank_name',
        'transaction_reference',
        'event__id',
    )
    readonly_fields = (
        'uuid',
        'event',
        'bank_account',
        'host_name',
        'event_name',
        'event_date',
        'event_location',
        'total_capacity',
        'base_ticket_fare',
        'final_ticket_fare',
        'total_tickets_sold',
        'attendees_details_display',
        'platform_fee_amount',
        'platform_fee_percentage',
        'final_earning',
        'created_at',
        'updated_at',
        'processed_at',
    )
    raw_id_fields = ('event', 'bank_account')
    date_hierarchy = 'created_at'
    
    fieldsets = (
        ('Request Information', {
            'fields': (
                'uuid',
                'event',
                'bank_account',
                'status',
            )
        }),
        ('Event Snapshot', {
            'fields': (
                'host_name',
                'event_name',
                'event_date',
                'event_location',
                'total_capacity',
            )
        }),
        ('Financial Details', {
            'fields': (
                'base_ticket_fare',
                'final_ticket_fare',
                'total_tickets_sold',
                'platform_fee_amount',
                'platform_fee_percentage',
                'final_earning',
            )
        }),
        ('Attendees', {
            'fields': ('attendees_details_display',),
            'classes': ('collapse',),
        }),
        ('Processing Information', {
            'fields': (
                'transaction_reference',
                'processed_at',
                'rejection_reason',
                'notes',
            ),
            'classes': ('collapse',),
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )
    
    actions = ['approve_payout', 'reject_payout', 'mark_processing', 'mark_completed']
    
    def event_name_display(self, obj):
        """Display event name with link"""
        if obj.event:
            url = reverse('admin:events_event_change', args=[obj.event.pk])
            return format_html('<a href="{}">{}</a>', url, obj.event_name)
        return obj.event_name
    event_name_display.short_description = 'Event'
    
    def final_earning_display(self, obj):
        """Display final earning with currency"""
        return f"₹{obj.final_earning:,.2f}"
    final_earning_display.short_description = 'Final Earning'
    final_earning_display.admin_order_field = 'final_earning'
    
    def platform_fee_amount_display(self, obj):
        """Display platform fee with currency"""
        return f"₹{obj.platform_fee_amount:,.2f}"
    platform_fee_amount_display.short_description = 'Platform Fee'
    platform_fee_amount_display.admin_order_field = 'platform_fee_amount'
    
    def attendees_details_display(self, obj):
        """Display attendees in a readable format"""
        if not obj.attendees_details:
            return "No attendees"
        
        html = "<ul>"
        for attendee in obj.attendees_details:
            name = attendee.get('name', 'Unknown')
            contact = attendee.get('contact', 'N/A')
            html += f"<li><strong>{name}</strong> - {contact}</li>"
        html += "</ul>"
        return format_html(html)
    attendees_details_display.short_description = 'Attendees'
    
    def approve_payout(self, request, queryset):
        """Approve selected payout requests"""
        count = queryset.filter(status='pending').update(status='approved')
        self.message_user(request, f'✅ {count} payout request(s) approved.')
    approve_payout.short_description = "Approve selected payout requests"
    
    def reject_payout(self, request, queryset):
        """Reject selected payout requests"""
        count = queryset.filter(status__in=['pending', 'approved']).update(
            status='rejected'
        )
        self.message_user(request, f'❌ {count} payout request(s) rejected.')
    reject_payout.short_description = "Reject selected payout requests"
    
    def mark_processing(self, request, queryset):
        """Mark selected payout requests as processing"""
        from django.utils import timezone
        count = queryset.filter(status='approved').update(
            status='processing',
            processed_at=timezone.now()
        )
        self.message_user(request, f'⏳ {count} payout request(s) marked as processing.')
    mark_processing.short_description = "Mark as processing"
    
    def mark_completed(self, request, queryset):
        """Mark selected payout requests as completed"""
        from django.utils import timezone
        count = queryset.filter(status='processing').update(
            status='completed',
            processed_at=timezone.now()
        )
        self.message_user(request, f'✅ {count} payout request(s) marked as completed.')
    mark_completed.short_description = "Mark as completed"


# Unregister the default User admin and register our custom one
admin.site.unregister(User)
admin.site.register(User, UserAdmin)