# payments/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from core.base_models import TimeStampedModel
from core.choices import (
    PAYMENT_STATUS_CHOICES,
    PAYMENT_PROVIDER_CHOICES,
    CURRENCY_CHOICES,
)
from events.models import Event
import uuid


class PaymentOrder(TimeStampedModel):
    """Model for tracking payment orders"""
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    event = models.ForeignKey(
        Event, 
        on_delete=models.CASCADE,
        related_name="payment_orders"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="payment_orders"
    )
    order_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        validators=[MinValueValidator(0.01)]
    )
    currency = models.CharField(
        max_length=10, 
        choices=CURRENCY_CHOICES,
        default="INR"
    )
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    provider = models.CharField(
        max_length=50, 
        choices=PAYMENT_PROVIDER_CHOICES,
        default='razorpay'
    )
    provider_payment_id = models.CharField(max_length=100, blank=True)
    provider_response = models.JSONField(default=dict, blank=True)
    payment_method = models.CharField(max_length=50, blank=True)
    transaction_id = models.CharField(max_length=100, blank=True)
    failure_reason = models.TextField(blank=True)
    refund_amount = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True
    )
    refund_reason = models.TextField(blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["order_id"]),
            models.Index(fields=["provider_payment_id"]),
            models.Index(fields=["event", "user"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"Order {self.order_id} - {self.user} - {self.amount} {self.currency}"

    def save(self, *args, **kwargs):
        if not self.order_id:
            self.order_id = self.generate_order_id()
        if not self.expires_at:
            self.expires_at = timezone.now() + timezone.timedelta(hours=24)
        super().save(*args, **kwargs)

    def generate_order_id(self):
        """Generate a unique order ID"""
        return f"ORD_{timezone.now().strftime('%Y%m%d%H%M%S')}_{self.user.id}_{uuid.uuid4().hex[:8]}"

    def mark_completed(self, provider_payment_id=None, transaction_id=None):
        """Mark payment as completed"""
        self.status = 'completed'
        if provider_payment_id:
            self.provider_payment_id = provider_payment_id
        if transaction_id:
            self.transaction_id = transaction_id
        self.save(update_fields=['status', 'provider_payment_id', 'transaction_id', 'updated_at'])
        
        # Track payment completion analytics
        try:
            from analytics.tracker import AnalyticsTracker
            AnalyticsTracker.track_payment_completed(self.user, self, self.event)
        except ImportError:
            pass  # Analytics module not available

    def mark_failed(self, failure_reason=None):
        """Mark payment as failed"""
        self.status = 'failed'
        if failure_reason:
            self.failure_reason = failure_reason
        self.save(update_fields=['status', 'failure_reason', 'updated_at'])
        
        # Track payment failure analytics
        try:
            from analytics.tracker import AnalyticsTracker
            AnalyticsTracker.track_payment_failed(self.user, self, self.event, failure_reason or 'Unknown error')
        except ImportError:
            pass  # Analytics module not available

    def process_refund(self, refund_amount=None, refund_reason=None):
        """Process a refund"""
        if refund_amount is None:
            refund_amount = self.amount
        self.refund_amount = refund_amount
        self.refund_reason = refund_reason or "Refund requested"
        self.refunded_at = timezone.now()
        self.status = 'refunded'
        self.save(update_fields=['refund_amount', 'refund_reason', 'refunded_at', 'status', 'updated_at'])

    @property
    def is_expired(self):
        """Check if payment order has expired"""
        return self.expires_at and timezone.now() > self.expires_at

    @property
    def is_paid(self):
        """Check if payment is completed"""
        return self.status == 'completed'

    @property
    def is_refunded(self):
        """Check if payment is refunded"""
        return self.status == 'refunded'

    @property
    def can_refund(self):
        """Check if payment can be refunded"""
        return self.is_paid and not self.is_refunded


class PaymentTransaction(TimeStampedModel):
    """Model for tracking individual payment transactions"""
    payment_order = models.ForeignKey(
        PaymentOrder, 
        on_delete=models.CASCADE,
        related_name="transactions"
    )
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ('payment', 'Payment'),
            ('refund', 'Refund'),
            ('chargeback', 'Chargeback'),
        ],
        default='payment'
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    provider_transaction_id = models.CharField(max_length=100, blank=True)
    status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default='pending'
    )
    provider_response = models.JSONField(default=dict, blank=True)
    failure_reason = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["transaction_type"]),
            models.Index(fields=["status"]),
            models.Index(fields=["provider_transaction_id"]),
        ]

    def __str__(self):
        return f"Transaction {self.id} - {self.transaction_type} - {self.amount}"


class PaymentWebhook(TimeStampedModel):
    """Model for tracking payment webhooks"""
    payment_order = models.ForeignKey(
        PaymentOrder, 
        on_delete=models.CASCADE,
        related_name="webhooks"
    )
    webhook_type = models.CharField(max_length=50)
    payload = models.JSONField()
    signature = models.CharField(max_length=500, blank=True)
    processed = models.BooleanField(default=False)
    processing_error = models.TextField(blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["webhook_type"]),
            models.Index(fields=["processed"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Webhook {self.id} - {self.webhook_type} - {self.payment_order.order_id}"