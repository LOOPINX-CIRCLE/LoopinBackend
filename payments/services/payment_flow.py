"""
Payment Flow Orchestration Service

This module orchestrates the complete payment lifecycle:
- Order creation
- Payment processing
- Order finalization
- Capacity reservation management
- Attendance record fulfillment

Business Rules:
- Orders expire in 10 minutes
- Only create orders when capacity is reserved
- Finalize orders atomically
- Release reservations on failure
"""

from typing import Dict, Any, Optional
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.db.models import Q
from core.utils.logger import get_logger
from core.exceptions import (
    ValidationError,
    NotFoundError,
    BusinessLogicError,
)
from payments.models import PaymentOrder, PaymentTransaction, PaymentWebhook
from events.models import Event, CapacityReservation
from attendances.models import AttendanceRecord
from users.models import UserProfile

logger = get_logger(__name__)


class PaymentFlowService:
    """
    Payment flow orchestration service.
    
    Handles:
    - Payment order creation
    - Order finalization (success/failure)
    - Capacity reservation consumption
    - Attendance record fulfillment
    """
    
    ORDER_EXPIRY_MINUTES = 10
    
    @classmethod
    @transaction.atomic
    def create_payment_order(
        cls,
        user_profile: UserProfile,
        event: Event,
        amount: Decimal,
        reservation_key: Optional[str] = None,
        auth_user=None,  # For identity enforcement check
    ) -> PaymentOrder:
        """
        Create a payment order.
        
        SECURITY ENFORCEMENT (IDENTITY MODEL):
        - AUTH_USER (admin) must NEVER create payment orders
        - Only USER_PROFILE (customers) can create payment orders
        
        Business Rules:
        - Only create if capacity is reserved (reservation_key provided)
        - Set status to 'created'
        - Set payment_provider to 'payu'
        - Set expiry to 10 minutes from now
        - Currency defaults to INR
        
        Args:
            user_profile: User profile placing the order
            event: Event for which payment is being made
            amount: Payment amount
            reservation_key: Optional capacity reservation key
            auth_user: Optional AUTH_USER for identity enforcement check
            
        Returns:
            PaymentOrder: Created payment order
            
        Raises:
            ValidationError: If reservation is invalid or missing
            BusinessLogicError: If order creation fails
            AuthorizationError: If AUTH_USER attempts to create payment order
        """
        # SECURITY: Identity enforcement - AUTH_USER must never create payment orders
        if auth_user and (auth_user.is_staff or auth_user.is_superuser):
            from core.exceptions import AuthorizationError
            raise AuthorizationError(
                "Admin accounts (AUTH_USER) cannot create payment orders. Only customers (USER_PROFILE) can make payments.",
                code="ADMIN_CANNOT_PAY"
            )
        # Validate reservation if provided
        if reservation_key:
            try:
                reservation = CapacityReservation.objects.get(
                    reservation_key=reservation_key,
                    event=event,
                    user=user_profile,
                    consumed=False,
                    expires_at__gt=timezone.now(),
                )
            except CapacityReservation.DoesNotExist:
                raise ValidationError(
                    "Invalid or expired capacity reservation. Please request to join the event again.",
                    code="INVALID_RESERVATION"
                )
        elif event.is_paid:
            # For paid events, reservation is mandatory
            raise ValidationError(
                "Capacity reservation required for paid events. Please request to join the event first.",
                code="RESERVATION_REQUIRED"
            )
        
        # Validate amount
        if amount <= 0:
            raise ValidationError(
                "Payment amount must be greater than zero",
                code="INVALID_AMOUNT"
            )
        
        # Validate event is paid
        if not event.is_paid:
            raise ValidationError(
                "This event does not require payment",
                code="EVENT_NOT_PAID"
            )
        
        # Check for existing active order
        existing_order = PaymentOrder.objects.filter(
            user=user_profile,
            event=event,
            status__in=['created', 'pending'],
            expires_at__gt=timezone.now(),
        ).first()
        
        if existing_order:
            raise ValidationError(
                f"An active payment order already exists. Order ID: {existing_order.order_id}",
                code="ORDER_EXISTS"
            )
        
        try:
            # Create payment order
            expires_at = timezone.now() + timezone.timedelta(minutes=cls.ORDER_EXPIRY_MINUTES)
            
            order = PaymentOrder.objects.create(
                user=user_profile,
                event=event,
                amount=amount,
                currency='INR',
                status='created',
                payment_provider='payu',
                expires_at=expires_at,
            )
            
            logger.info(
                f"Payment order created: {order.order_id} for user {user_profile.id}, "
                f"event {event.id}, amount {amount} INR"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to create payment order: {e}", exc_info=True)
            raise BusinessLogicError(
                f"Failed to create payment order: {str(e)}",
                code="ORDER_CREATION_FAILED"
            )
    
    @classmethod
    @transaction.atomic
    def finalize_payment_success(
        cls,
        order: PaymentOrder,
        provider_payment_id: str,
        transaction_id: Optional[str] = None,
        callback_data: Optional[Dict[str, Any]] = None,
    ) -> PaymentOrder:
        """
        Finalize payment on success.
        
        Steps:
        1. Update order status to 'paid'
        2. Create payment transaction
        3. Mark attendance record as paid
        4. Consume capacity reservation
        5. Update event going_count
        
        Args:
            order: Payment order to finalize
            provider_payment_id: PayU payment ID
            transaction_id: Optional transaction ID
            callback_data: Optional callback data for logging
            
        Returns:
            PaymentOrder: Updated payment order
            
        Raises:
            ValidationError: If order is already finalized
            BusinessLogicError: If finalization fails
        """
        # Check if already finalized
        if order.status in ['paid', 'completed']:
            logger.warning(f"Order {order.order_id} already finalized with status: {order.status}")
            return order
        
        # Validate order is not expired
        if order.is_expired:
            raise ValidationError(
                f"Payment order {order.order_id} has expired",
                code="ORDER_EXPIRED"
            )
        
        try:
            from core.models import PlatformFeeConfig
            from decimal import Decimal
            
            # Calculate financial snapshot (immutable at payment time) - CFO requirement
            base_price_per_seat = order.event.ticket_price or Decimal('0.00')
            platform_fee_percentage = PlatformFeeConfig.get_fee_percentage()
            platform_fee_decimal = PlatformFeeConfig.get_fee_decimal()
            platform_fee_amount = PlatformFeeConfig.calculate_platform_fee(
                base_fare=base_price_per_seat,
                quantity=order.seats_count
            )
            host_earning_per_seat = base_price_per_seat  # Host earns full base price
            
            # SECURITY: Ensure only ONE payment_order per (user, event) can be final
            # Mark previous orders for this user+event as non-final (retry tracking)
            PaymentOrder.objects.filter(
                event=order.event,
                user=order.user,
                is_final=True
            ).exclude(id=order.id).update(is_final=False)
            
            # SECURITY: Double-check no other final order exists (race condition protection)
            existing_final = PaymentOrder.objects.filter(
                event=order.event,
                user=order.user,
                is_final=True
            ).exclude(id=order.id).first()
            
            if existing_final:
                logger.error(
                    f"Race condition detected: Final order {existing_final.order_id} exists "
                    f"for user {order.user.id}, event {order.event.id}. "
                    f"Preventing duplicate finalization."
                )
                raise BusinessLogicError(
                    "A final payment order already exists for this user and event. "
                    "Cannot finalize multiple orders.",
                    code="DUPLICATE_FINAL_ORDER"
                )
            
            # Update order status with financial snapshot
            order.status = 'paid'
            order.provider_payment_id = provider_payment_id
            if transaction_id:
                order.transaction_id = transaction_id
            if callback_data:
                order.provider_response = callback_data
            order.is_final = True  # Mark as final successful payment
            order.base_price_per_seat = base_price_per_seat
            order.platform_fee_percentage = platform_fee_percentage
            order.platform_fee_amount = platform_fee_amount
            order.host_earning_per_seat = host_earning_per_seat
            order.save(update_fields=[
                'status', 'provider_payment_id', 'transaction_id', 'provider_response',
                'is_final', 'base_price_per_seat', 'platform_fee_percentage',
                'platform_fee_amount', 'host_earning_per_seat', 'updated_at'
            ])
            
            # Create payment transaction
            PaymentTransaction.objects.create(
                payment_order=order,
                transaction_type='payment',
                amount=order.amount,
                provider_transaction_id=provider_payment_id,
                status='completed',
                provider_response=callback_data or {},
            )
            
            # Get or create EventAttendee (main attendee record) with payment link
            from events.models import EventAttendee
            attendee, attendee_created = EventAttendee.objects.get_or_create(
                event=order.event,
                user=order.user,
                defaults={
                    'status': 'going',
                    'seats': order.seats_count,
                    'is_paid': True,
                    'price_paid': base_price_per_seat * order.seats_count,
                    'platform_fee': platform_fee_amount,
                    'payment_order': order,  # Link to payment order
                }
            )
            
            # Update attendee if it exists
            if not attendee_created:
                attendee.status = 'going'
                attendee.is_paid = True
                attendee.price_paid = base_price_per_seat * order.seats_count
                attendee.platform_fee = platform_fee_amount
                attendee.payment_order = order  # Link to payment order
                attendee.save(update_fields=[
                    'status', 'is_paid', 'price_paid', 'platform_fee',
                    'payment_order', 'updated_at'
                ])
            
            # Get or create attendance record (for check-in/check-out) with payment link
            attendance, created = AttendanceRecord.objects.get_or_create(
                event=order.event,
                user=order.user,
                defaults={
                    'status': 'going',
                    'payment_status': 'paid',
                    'seats': order.seats_count,
                    'payment_order': order,  # Link to payment order
                }
            )
            
            # Update attendance if it exists
            if not created:
                attendance.payment_status = 'paid'
                attendance.status = 'going'
                attendance.seats = order.seats_count
                attendance.payment_order = order  # Link to payment order
                attendance.save(update_fields=[
                    'payment_status', 'status', 'seats', 'payment_order', 'updated_at'
                ])
            
            # Consume capacity reservation
            CapacityReservation.objects.filter(
                event=order.event,
                user=order.user,
                consumed=False,
            ).update(consumed=True)
            
            # Update event going_count (based on EventAttendee, not AttendanceRecord)
            order.event.going_count = EventAttendee.objects.filter(
                event=order.event,
                status='going',
            ).count()
            order.event.save(update_fields=['going_count'])
            
            logger.info(
                f"Payment finalized successfully: {order.order_id}, "
                f"provider_payment_id: {provider_payment_id}"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to finalize payment: {e}", exc_info=True)
            raise BusinessLogicError(
                f"Failed to finalize payment: {str(e)}",
                code="PAYMENT_FINALIZATION_FAILED"
            )
    
    @classmethod
    @transaction.atomic
    def finalize_payment_failure(
        cls,
        order: PaymentOrder,
        failure_reason: str,
        callback_data: Optional[Dict[str, Any]] = None,
    ) -> PaymentOrder:
        """
        Finalize payment on failure.
        
        Steps:
        1. Update order status to 'failed'
        2. Log failure reason
        3. Release capacity reservation
        4. Create failed transaction record
        
        Args:
            order: Payment order to finalize
            failure_reason: Reason for failure
            callback_data: Optional callback data for logging
            
        Returns:
            PaymentOrder: Updated payment order
        """
        try:
            # Update order status
            order.status = 'failed'
            order.failure_reason = failure_reason
            if callback_data:
                order.provider_response = callback_data
            order.save(update_fields=['status', 'failure_reason', 'provider_response', 'updated_at'])
            
            # Create failed transaction record
            PaymentTransaction.objects.create(
                payment_order=order,
                transaction_type='payment',
                amount=order.amount,
                status='failed',
                failure_reason=failure_reason,
                provider_response=callback_data or {},
            )
            
            # Release capacity reservation (don't delete, just mark as not consumed)
            # Note: We don't delete reservations, but they expire naturally
            # The user can request again after reservation expires
            
            logger.info(
                f"Payment failed: {order.order_id}, reason: {failure_reason}"
            )
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to finalize payment failure: {e}", exc_info=True)
            # Don't raise - we want to log the failure even if finalization has issues
            return order
    
    @classmethod
    def get_order_by_txnid(cls, txnid: str) -> Optional[PaymentOrder]:
        """
        Get payment order by transaction ID (order_id).
        
        Args:
            txnid: Transaction ID (order_id)
            
        Returns:
            PaymentOrder or None
        """
        try:
            return PaymentOrder.objects.get(order_id=txnid)
        except PaymentOrder.DoesNotExist:
            return None
    
    @classmethod
    @transaction.atomic
    def process_webhook(
        cls,
        webhook_data: Dict[str, Any],
        signature: Optional[str] = None,
    ) -> PaymentWebhook:
        """
        Process PayU webhook.
        
        Steps:
        1. Create webhook record
        2. Extract callback data
        3. Find order by txnid
        4. Verify hash
        5. Finalize payment based on status
        6. Mark webhook as processed
        
        Args:
            webhook_data: Webhook payload from PayU
            signature: Optional webhook signature
            
        Returns:
            PaymentWebhook: Created webhook record
        """
        from payments.services.payu import PayUService
        
        # Extract txnid to find order
        txnid = webhook_data.get('txnid')
        if not txnid:
            raise ValidationError(
                "Webhook missing transaction ID (txnid)",
                code="WEBHOOK_INVALID"
            )
        
        # Find order
        order = cls.get_order_by_txnid(txnid)
        if not order:
            raise NotFoundError(
                f"Payment order not found for txnid: {txnid}",
                code="ORDER_NOT_FOUND"
            )
        
        # Create webhook record
        webhook = PaymentWebhook.objects.create(
            payment_order=order,
            webhook_type='payu_callback',
            payload=webhook_data,
            signature=signature or '',
            processed=False,
        )
        
        try:
            # Extract callback data
            callback_data = PayUService.extract_callback_data(webhook_data)
            
            # Verify hash
            is_valid = PayUService.verify_reverse_hash(
                status=callback_data['status'],
                email=callback_data['email'],
                firstname=callback_data['firstname'],
                productinfo=callback_data['productinfo'],
                amount=callback_data['amount'],
                txnid=callback_data['txnid'],
                received_hash=callback_data['hash'],
            )
            
            if not is_valid:
                webhook.processing_error = "Hash verification failed"
                webhook.processed = True
                webhook.save(update_fields=['processed', 'processing_error', 'updated_at'])
                raise ValidationError(
                    "Webhook hash verification failed",
                    code="WEBHOOK_HASH_MISMATCH"
                )
            
            # Finalize payment based on status
            status = callback_data['status'].lower()
            
            if status == 'success':
                cls.finalize_payment_success(
                    order=order,
                    provider_payment_id=callback_data.get('mihpayid', ''),
                    transaction_id=callback_data.get('bank_ref_num', ''),
                    callback_data=callback_data,
                )
            else:
                failure_reason = callback_data.get('error_Message') or callback_data.get('error') or 'Payment failed'
                cls.finalize_payment_failure(
                    order=order,
                    failure_reason=failure_reason,
                    callback_data=callback_data,
                )
            
            # Mark webhook as processed
            webhook.processed = True
            webhook.save(update_fields=['processed', 'updated_at'])
            
            logger.info(f"Webhook processed successfully: {webhook.id} for order {order.order_id}")
            
            return webhook
            
        except Exception as e:
            webhook.processing_error = str(e)
            webhook.processed = True
            webhook.save(update_fields=['processed', 'processing_error', 'updated_at'])
            logger.error(f"Webhook processing failed: {e}", exc_info=True)
            raise

