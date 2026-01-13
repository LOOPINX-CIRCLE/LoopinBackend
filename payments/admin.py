"""
Production-grade Django Admin configuration for Payments app.
CEO-level admin interface with rich displays, financial insights, and powerful actions.
"""
from django.contrib import admin
from django.db.models import Count, Sum, Q
from django.utils.safestring import mark_safe
from django.urls import reverse
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from .models import PaymentOrder, PaymentTransaction, PaymentWebhook


# ============================================================================
# INLINE MODELS
# ============================================================================

class PaymentTransactionInline(admin.TabularInline):
    """Inline for viewing payment transactions"""
    model = PaymentTransaction
    extra = 0
    readonly_fields = (
        'transaction_type',
        'amount',
        'provider_transaction_id',
        'status',
        'failure_reason',
        'created_at',
    )
    fields = ('transaction_type', 'amount', 'status', 'provider_transaction_id', 'created_at')
    can_delete = False
    show_change_link = True
    verbose_name = "Transaction"
    verbose_name_plural = "Transactions"
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-created_at')[:20]  # Limit for performance


class PaymentWebhookInline(admin.TabularInline):
    """Inline for viewing payment webhooks"""
    model = PaymentWebhook
    extra = 0
    readonly_fields = (
        'webhook_type',
        'signature',
        'processed',
        'processing_error',
        'created_at',
    )
    fields = ('webhook_type', 'processed', 'created_at')
    can_delete = False
    show_change_link = True
    verbose_name = "Webhook"
    verbose_name_plural = "Webhooks"
    
    def has_add_permission(self, request, obj=None):
        return False
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('-created_at')[:10]  # Limit for performance


# ============================================================================
# PAYMENT ORDER ADMIN
# ============================================================================

@admin.register(PaymentOrder)
class PaymentOrderAdmin(admin.ModelAdmin):
    """
    CEO-level admin interface for Payment Orders.
    
    Features:
    - Financial snapshot display (CFO requirement)
    - Retry tracking visualization (CTO requirement)
    - Revenue analytics
    - Quick refund actions
    - Provider response inspection
    """
    
    list_display = (
        'order_id_short',
        'event_link',
        'user_link',
        'amount_display',
        'status_badge',
        'financial_breakdown',
        'retry_info',
        'provider_badge',
        'is_expired_display',
        'created_at',
    )
    list_filter = (
        'status',
        'payment_provider',
        'is_final',
        'currency',
        ('created_at', admin.DateFieldListFilter),
        ('expires_at', admin.DateFieldListFilter),
        'event__is_paid',
    )
    search_fields = (
        'order_id',
        'order_reference',
        'provider_payment_id',
        'transaction_id',
        'event__title',
        'user__name',
        'user__phone_number',
    )
    readonly_fields = (
        'uuid',
        'order_id',
        'order_reference',
        'created_at',
        'updated_at',
        'financial_snapshot_display',
        'retry_tree_display',
        'provider_response_display',
        'provider_badge_display',
        'is_expired_display',
        'total_host_earning_display',
        'total_platform_fee_display',
    )
    fieldsets = (
        (_('Order Information'), {
            'fields': ('uuid', 'order_id', 'order_reference', 'event', 'user', 'seats_count')
        }),
        (_('Payment Amount'), {
            'fields': ('amount', 'currency')
        }),
        (_('Financial Snapshot (Immutable)'), {
            'fields': (
                'base_price_per_seat',
                'platform_fee_percentage',
                'platform_fee_amount',
                'host_earning_per_seat',
                'total_host_earning_display',
                'total_platform_fee_display',
                'financial_snapshot_display',
            ),
            'description': 'These values are captured at payment time and never change (CFO requirement).'
        }),
        (_('Payment Status & Provider'), {
            'fields': (
                'status',
                'payment_provider',
                'provider_payment_id',
                'payment_method',
                'transaction_id',
                'provider_badge_display',
                'is_expired_display',
            )
        }),
        (_('Retry Tracking (CTO Requirement)'), {
            'fields': (
                'parent_order',
                'is_final',
                'retry_tree_display',
            ),
            'description': 'Track retry attempts and identify final successful payments.',
            'classes': ('collapse',)
        }),
        (_('Refund Information'), {
            'fields': (
                'refund_amount',
                'refund_reason',
                'refunded_at',
            ),
            'classes': ('collapse',)
        }),
        (_('Failure Information'), {
            'fields': ('failure_reason',),
            'classes': ('collapse',)
        }),
        (_('Provider Response'), {
            'fields': ('provider_response_display',),
            'classes': ('collapse',),
            'description': 'Raw provider response for debugging'
        }),
        (_('Expiration'), {
            'fields': ('expires_at',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    autocomplete_fields = ['event', 'user', 'parent_order']
    inlines = [PaymentTransactionInline, PaymentWebhookInline]
    date_hierarchy = 'created_at'
    save_on_top = True
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related(
            'event',
            'event__host',
            'user',
            'parent_order',
        ).prefetch_related(
            'transactions',
            'webhooks',
        ).annotate(
            retry_count=Count('retry_attempts'),
        ).order_by('-created_at')
    
    def order_id_short(self, obj):
        """Display shortened order ID with link"""
        short_id = obj.order_id[:20] + '...' if len(obj.order_id) > 20 else obj.order_id
        url = reverse('admin:payments_paymentorder_change', args=[obj.pk])
        return mark_safe(f'<a href="{url}"><code style="font-size: 11px;">{short_id}</code></a>')
    order_id_short.short_description = "Order ID"
    order_id_short.admin_order_field = 'order_id'
    
    def event_link(self, obj):
        """Link to event"""
        url = reverse('admin:events_event_change', args=[obj.event_id])
        return mark_safe(f'<a href="{url}">{obj.event.title}</a>')
    event_link.short_description = "Event"
    event_link.admin_order_field = 'event__title'
    
    def user_link(self, obj):
        """Link to user profile"""
        url = reverse('admin:users_userprofile_change', args=[obj.user_id])
        name = obj.user.name or obj.user.phone_number
        return mark_safe(f'<a href="{url}">{name}</a>')
    user_link.short_description = "User"
    user_link.admin_order_field = 'user__name'
    
    def amount_display(self, obj):
        """Display amount with currency"""
        color = 'green' if obj.is_paid else 'red' if obj.status == 'failed' else 'orange'
        currency_symbol = '₹' if obj.currency == 'INR' else obj.currency + ' '
        return mark_safe(f'<span style="color: {color}; font-weight: bold; font-size: 13px;">{currency_symbol}{obj.amount:,.2f}</span>')
    amount_display.short_description = "Amount"
    amount_display.admin_order_field = 'amount'
    
    def status_badge(self, obj):
        """Display status with colored badge"""
        colors = {
            'created': '#9e9e9e',
            'pending': '#ff9800',
            'paid': '#4caf50',
            'completed': '#2196f3',
            'failed': '#f44336',
            'cancelled': '#9e9e9e',
            'refunded': '#e91e63',
            'unpaid': '#ff5722',
        }
        color = colors.get(obj.status, '#9e9e9e')
        badge_style = (
            f'background: {color}; color: white; padding: 4px 10px; '
            f'border-radius: 4px; font-size: 11px; font-weight: bold; display: inline-block;'
        )
        return mark_safe(f'<span style="{badge_style}">{obj.get_status_display()}</span>')
    status_badge.short_description = "Status"
    status_badge.admin_order_field = 'status'
    
    def financial_breakdown(self, obj):
        """Display financial breakdown (CEO view)"""
        if obj.status not in ['paid', 'completed']:
            return mark_safe('<span style="color: gray;">-</span>')
        
        if obj.base_price_per_seat and obj.seats_count:
            base_total = obj.base_price_per_seat * obj.seats_count
            platform_fee = obj.platform_fee_amount or 0
            host_earning = obj.host_earning_per_seat * obj.seats_count if obj.host_earning_per_seat else 0
            
            return mark_safe(
                f'<div style="font-size: 11px; line-height: 1.4;">'
                f'<div>💰 Total: <strong>₹{obj.amount:,.2f}</strong></div>'
                f'<div style="color: green;">✓ Host: ₹{host_earning:,.2f}</div>'
                f'<div style="color: blue;">✓ Platform: ₹{platform_fee:,.2f}</div>'
                f'</div>'
            )
        return mark_safe('<span style="color: gray;">No snapshot</span>')
    financial_breakdown.short_description = "Financial Breakdown"
    
    def retry_info(self, obj):
        """Display retry information"""
        retry_count = getattr(obj, 'retry_count', obj.retry_attempts.count())
        if obj.parent_order:
            url = reverse('admin:payments_paymentorder_change', args=[obj.parent_order_id])
            return mark_safe(f'<span style="color: orange; font-size: 11px;">↻ Retry of <a href="{url}">#{obj.parent_order.id}</a></span>')
        elif retry_count > 0:
            return mark_safe(f'<span style="color: blue; font-size: 11px;">↻ Has {retry_count} retry(s)</span>')
        elif obj.is_final:
            return mark_safe('<span style="color: green; font-size: 11px;">✓ Final</span>')
        return mark_safe('<span style="color: gray; font-size: 11px;">-</span>')
    retry_info.short_description = "Retry Info"
    
    def provider_badge(self, obj):
        """Display payment provider badge"""
        provider_colors = {
            'razorpay': '#6366f1',
            'stripe': '#635bff',
            'payu': '#ff6b6b',
            'paytm': '#00baf2',
            'phonepe': '#5f259f',
            'gpay': '#4285f4',
            'cash': '#9e9e9e',
            'bank_transfer': '#4caf50',
        }
        color = provider_colors.get(obj.payment_provider, '#9e9e9e')
        return mark_safe(f'<span style="background: {color}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px; text-transform: uppercase;">{obj.get_payment_provider_display()}</span>')
    provider_badge.short_description = "Provider"
    provider_badge.admin_order_field = 'payment_provider'
    
    def is_expired_display(self, obj):
        """Display expiration status"""
        if not obj or not obj.expires_at:
            return mark_safe('<span style="color: gray;">Not set</span>')
        is_expired = obj.is_expired
        color = 'red' if is_expired else 'green'
        text = '⚠️ Expired' if is_expired else '✓ Valid'
        return mark_safe(f'<span style="color: {color}; font-weight: bold;">{text}</span>')
    is_expired_display.short_description = "Expiration"
    
    def financial_snapshot_display(self, obj):
        """Display financial snapshot in readable format"""
        if not obj.base_price_per_seat:
            return mark_safe('<span style="color: gray;">Financial snapshot not captured yet</span>')
        
        return mark_safe(
            f'<div style="background: #f5f5f5; padding: 15px; border-radius: 4px; border-left: 4px solid #4caf50;">'
            f'<h4 style="margin-top: 0; color: #333;">Financial Snapshot (Immutable)</h4>'
            f'<table style="width: 100%; border-collapse: collapse;">'
            f'<tr><td style="padding: 5px; font-weight: bold;">Base Price/Seat:</td><td style="padding: 5px;">₹{obj.base_price_per_seat:.2f}</td></tr>'
            f'<tr><td style="padding: 5px; font-weight: bold;">Seats:</td><td style="padding: 5px;">{obj.seats_count}</td></tr>'
            f'<tr><td style="padding: 5px; font-weight: bold;">Platform Fee %:</td><td style="padding: 5px;">{obj.platform_fee_percentage}%</td></tr>'
            f'<tr><td style="padding: 5px; font-weight: bold;">Platform Fee Amount:</td><td style="padding: 5px; color: blue;">₹{(obj.platform_fee_amount or 0):.2f}</td></tr>'
            f'<tr><td style="padding: 5px; font-weight: bold;">Host Earning/Seat:</td><td style="padding: 5px; color: green;">₹{(obj.host_earning_per_seat or 0):.2f}</td></tr>'
            f'<tr><td style="padding: 5px; font-weight: bold;">Total Host Earning:</td><td style="padding: 5px; color: green; font-size: 16px;"><strong>₹{(obj.total_host_earning or 0):.2f}</strong></td></tr>'
            f'<tr><td style="padding: 5px; font-weight: bold;">Total Amount Paid:</td><td style="padding: 5px; font-size: 16px;"><strong>₹{obj.amount:.2f}</strong></td></tr>'
            f'</table>'
            f'<p style="margin-top: 10px; margin-bottom: 0; font-size: 11px; color: #666;">'
            f'⚠️ These values are immutable and captured at payment time (CFO requirement)'
            f'</p>'
            f'</div>'
        )
    financial_snapshot_display.short_description = "Financial Snapshot"
    
    def retry_tree_display(self, obj):
        """Display retry tree visualization"""
        html = '<div style="background: #fff3cd; padding: 10px; border-radius: 4px;">'
        
        if obj.parent_order:
            url = reverse('admin:payments_paymentorder_change', args=[obj.parent_order_id])
            html += f'<div style="margin-bottom: 5px;">'
            html += f'↻ <strong>This is a retry attempt</strong><br>'
            html += f'Parent Order: <a href="{url}">#{obj.parent_order.id}</a>'
            html += '</div>'
        
        retry_count = obj.retry_attempts.count()
        if retry_count > 0:
            html += f'<div style="margin-top: 5px;">'
            html += f'This order has <strong>{retry_count} retry attempt(s)</strong>:<br>'
            for retry in obj.retry_attempts.all()[:5]:
                retry_url = reverse('admin:payments_paymentorder_change', args=[retry.id])
                status_color = 'green' if retry.is_paid else 'red'
                html += f'  → <a href="{retry_url}">Order #{retry.id}</a> '
                html += f'<span style="color: {status_color};">({retry.get_status_display()})</span><br>'
            html += '</div>'
        
        if obj.is_final:
            html += '<div style="margin-top: 10px; padding: 5px; background: #d4edda; border-radius: 3px;">'
            html += '<strong style="color: green;">✓ This is the final successful payment</strong>'
            html += '</div>'
        
        html += '</div>'
        return mark_safe(html)
    retry_tree_display.short_description = "Retry Tree"
    
    def provider_response_display(self, obj):
        """Display provider response in readable format"""
        if not obj.provider_response:
            return mark_safe('<span style="color: gray;">No provider response</span>')
        
        import json
        return mark_safe(f'<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; max-height: 300px; overflow-y: auto; font-size: 11px;">{json.dumps(obj.provider_response, indent=2)}</pre>')
    provider_response_display.short_description = "Provider Response"
    
    def provider_badge_display(self, obj):
        """Display provider badge in detail view"""
        return self.provider_badge(obj)
    provider_badge_display.short_description = "Provider"
    
    def total_host_earning_display(self, obj):
        """Display total host earning"""
        earning = obj.total_host_earning
        if earning:
            return mark_safe(f'<span style="color: green; font-weight: bold; font-size: 16px;">₹{earning:.2f}</span>')
        return '-'
    total_host_earning_display.short_description = "Total Host Earning"
    
    def total_platform_fee_display(self, obj):
        """Display total platform fee"""
        fee = obj.total_platform_fee
        if fee:
            return mark_safe(f'<span style="color: blue; font-weight: bold; font-size: 16px;">₹{fee:.2f}</span>')
        return '-'
    total_platform_fee_display.short_description = "Total Platform Fee"
    
    actions = [
        'mark_as_paid',
        'mark_as_failed',
        'process_refund',
        'cancel_orders',
    ]
    
    def mark_as_paid(self, request, queryset):
        """Bulk mark as paid (use with caution)"""
        count = 0
        for order in queryset.filter(status__in=['created', 'pending']):
            order.mark_completed()
            count += 1
        self.message_user(request, f'✅ {count} order(s) marked as paid.')
    mark_as_paid.short_description = "Mark as paid (Bulk)"
    
    def mark_as_failed(self, request, queryset):
        """Bulk mark as failed"""
        count = queryset.filter(status__in=['created', 'pending']).update(
            status='failed',
            failure_reason='Bulk marked as failed from admin'
        )
        self.message_user(request, f'❌ {count} order(s) marked as failed.')
    mark_as_failed.short_description = "Mark as failed (Bulk)"
    
    def process_refund(self, request, queryset):
        """Bulk process refund"""
        refundable = queryset.filter(status__in=['paid', 'completed'], refund_amount__isnull=True)
        count = 0
        for order in refundable:
            order.process_refund(refund_reason='Bulk refund from admin')
            count += 1
        self.message_user(request, f'💰 {count} order(s) refunded.')
    process_refund.short_description = "Process refund (Bulk)"
    
    def cancel_orders(self, request, queryset):
        """Bulk cancel orders"""
        count = queryset.filter(status__in=['created', 'pending']).update(status='cancelled')
        self.message_user(request, f'❌ {count} order(s) cancelled.')
    cancel_orders.short_description = "Cancel selected orders"


# ============================================================================
# PAYMENT TRANSACTION ADMIN
# ============================================================================

@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    """Admin for individual payment transactions"""
    
    list_display = (
        'payment_order_link',
        'transaction_type_badge',
        'amount_display',
        'status_badge',
        'provider_transaction_id_short',
        'created_at',
    )
    list_filter = (
        'transaction_type',
        'status',
        ('created_at', admin.DateFieldListFilter),
    )
    search_fields = (
        'payment_order__order_id',
        'payment_order__order_reference',
        'provider_transaction_id',
        'payment_order__event__title',
        'payment_order__user__name',
    )
    readonly_fields = (
        'payment_order',
        'transaction_type',
        'amount',
        'provider_transaction_id',
        'status',
        'provider_response_display',
        'failure_reason',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        (_('Transaction Information'), {
            'fields': ('payment_order', 'transaction_type', 'amount', 'status')
        }),
        (_('Provider Details'), {
            'fields': ('provider_transaction_id', 'provider_response_display')
        }),
        (_('Failure Information'), {
            'fields': ('failure_reason',),
            'classes': ('collapse',)
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('payment_order', 'payment_order__event', 'payment_order__user').order_by('-created_at')
    
    def payment_order_link(self, obj):
        """Link to payment order"""
        url = reverse('admin:payments_paymentorder_change', args=[obj.payment_order_id])
        return mark_safe(f'<a href="{url}">Order #{obj.payment_order.id}</a>')
    payment_order_link.short_description = "Payment Order"
    payment_order_link.admin_order_field = 'payment_order__id'
    
    def transaction_type_badge(self, obj):
        """Display transaction type with badge"""
        colors = {
            'payment': '#4caf50',
            'refund': '#ff9800',
            'chargeback': '#f44336',
        }
        color = colors.get(obj.transaction_type, '#9e9e9e')
        return mark_safe(f'<span style="background: {color}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px; text-transform: uppercase;">{obj.get_transaction_type_display()}</span>')
    transaction_type_badge.short_description = "Type"
    transaction_type_badge.admin_order_field = 'transaction_type'
    
    def amount_display(self, obj):
        """Display amount"""
        color = 'green' if obj.transaction_type == 'payment' else 'red'
        return mark_safe(f'<span style="font-weight: bold; color: {color};">₹{obj.amount:.2f}</span>')
    amount_display.short_description = "Amount"
    amount_display.admin_order_field = 'amount'
    
    def status_badge(self, obj):
        """Display status badge"""
        colors = {
            'pending': '#ff9800',
            'completed': '#4caf50',
            'failed': '#f44336',
        }
        color = colors.get(obj.status, '#9e9e9e')
        return mark_safe(f'<span style="background: {color}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px;">{obj.get_status_display()}</span>')
    status_badge.short_description = "Status"
    status_badge.admin_order_field = 'status'
    
    def provider_transaction_id_short(self, obj):
        """Display shortened provider transaction ID"""
        if obj.provider_transaction_id:
            short_id = obj.provider_transaction_id[:20] + '...' if len(obj.provider_transaction_id) > 20 else obj.provider_transaction_id
            return mark_safe(f'<code style="font-size: 11px;">{short_id}</code>')
        return '-'
    provider_transaction_id_short.short_description = "Provider TXN ID"
    
    def provider_response_display(self, obj):
        """Display provider response"""
        if not obj.provider_response:
            return mark_safe('<span style="color: gray;">No response</span>')
        
        import json
        return mark_safe(f'<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; max-height: 200px; overflow-y: auto; font-size: 11px;">{json.dumps(obj.provider_response, indent=2)}</pre>')
    provider_response_display.short_description = "Provider Response"
    
    def has_add_permission(self, request):
        return False


# ============================================================================
# PAYMENT WEBHOOK ADMIN
# ============================================================================

@admin.register(PaymentWebhook)
class PaymentWebhookAdmin(admin.ModelAdmin):
    """Admin for payment webhooks"""
    
    list_display = (
        'payment_order_link',
        'webhook_type',
        'processed_badge',
        'signature_short',
        'created_at',
    )
    list_filter = (
        'webhook_type',
        'processed',
        ('created_at', admin.DateFieldListFilter),
    )
    search_fields = (
        'payment_order__order_id',
        'webhook_type',
        'signature',
        'processing_error',
    )
    readonly_fields = (
        'payment_order',
        'webhook_type',
        'payload_display',
        'signature',
        'processed',
        'processing_error',
        'created_at',
        'updated_at',
    )
    fieldsets = (
        (_('Webhook Information'), {
            'fields': ('payment_order', 'webhook_type', 'signature')
        }),
        (_('Payload'), {
            'fields': ('payload_display',),
            'description': 'Raw webhook payload from payment provider'
        }),
        (_('Processing Status'), {
            'fields': ('processed', 'processing_error')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    date_hierarchy = 'created_at'
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('payment_order').order_by('-created_at')
    
    def payment_order_link(self, obj):
        """Link to payment order"""
        url = reverse('admin:payments_paymentorder_change', args=[obj.payment_order_id])
        return mark_safe(f'<a href="{url}">Order #{obj.payment_order.id}</a>')
    payment_order_link.short_description = "Payment Order"
    payment_order_link.admin_order_field = 'payment_order__id'
    
    def processed_badge(self, obj):
        """Display processed status"""
        if not obj:
            return mark_safe('<span style="color: gray;">Not set</span>')
        color = '#4caf50' if obj.processed else '#ff9800'
        text = '✓ Processed' if obj.processed else '⏳ Pending'
        return mark_safe(f'<span style="background: {color}; color: white; padding: 3px 8px; border-radius: 3px; font-size: 10px;">{text}</span>')
    processed_badge.short_description = "Processed"
    processed_badge.admin_order_field = 'processed'
    # Note: boolean = True removed - this returns HTML, not a boolean
    
    def signature_short(self, obj):
        """Display shortened signature"""
        if obj.signature:
            short = obj.signature[:30] + '...' if len(obj.signature) > 30 else obj.signature
            return mark_safe(f'<code style="font-size: 11px;">{short}</code>')
        return '-'
    signature_short.short_description = "Signature"
    
    def payload_display(self, obj):
        """Display payload in readable format"""
        import json
        return mark_safe(f'<pre style="background: #f5f5f5; padding: 10px; border-radius: 4px; max-height: 400px; overflow-y: auto; font-size: 11px;">{json.dumps(obj.payload, indent=2)}</pre>')
    payload_display.short_description = "Payload"
    
    def has_add_permission(self, request):
        return False
    
    actions = ['mark_as_processed', 'mark_as_unprocessed']
    
    def mark_as_processed(self, request, queryset):
        """Bulk mark as processed"""
        count = queryset.update(processed=True)
        self.message_user(request, f'✅ {count} webhook(s) marked as processed.')
    mark_as_processed.short_description = "Mark as processed"
    
    def mark_as_unprocessed(self, request, queryset):
        """Bulk mark as unprocessed"""
        count = queryset.update(processed=False)
        self.message_user(request, f'⏳ {count} webhook(s) marked as unprocessed.')
    mark_as_unprocessed.short_description = "Mark as unprocessed"
