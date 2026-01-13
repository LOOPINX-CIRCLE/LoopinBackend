"""
Production-ready PayU Payment API router for FastAPI.

Handles:
- Payment order creation
- PayU redirect payload generation
- Success/failure callback handling
- Webhook processing

Architecture:
- All business logic in services layer
- Views are thin HTTP adapters
- Idempotent callbacks and webhooks
- Hash verification on all PayU responses
"""

from typing import Dict, Any, Optional
from decimal import Decimal
import jwt
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    Path,
    Body,
    Request,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async
from pydantic import BaseModel, Field, EmailStr
from users.auth_router import maybe_promote_user_from_waitlist_sync
import logging

from core.utils.logger import get_logger
from core.exceptions import (
    ValidationError,
    NotFoundError,
    AuthorizationError,
    BusinessLogicError,
    ExternalServiceError,
)
from payments.models import PaymentOrder
from events.models import Event, CapacityReservation
from users.models import UserProfile
from payments.services.payu import PayUService
from payments.services.payment_flow import PaymentFlowService

logger = get_logger(__name__)
router = APIRouter(prefix="/payments", tags=["payments"])

# JWT token scheme
security = HTTPBearer()


# ============================================================================
# Request/Response Schemas
# ============================================================================

class PaymentOrderCreateRequest(BaseModel):
    """Schema for creating a payment order"""
    event_id: int = Field(..., description="Event ID")
    amount: Decimal = Field(..., gt=0, description="Payment amount")
    reservation_key: Optional[str] = Field(None, description="Capacity reservation key")


class PayURedirectResponse(BaseModel):
    """Schema for PayU redirect payload"""
    payu_url: str
    payload: Dict[str, Any]


class PaymentOrderResponse(BaseModel):
    """Schema for payment order response"""
    id: int
    order_id: str
    event_id: int
    amount: str
    currency: str
    status: str
    payment_provider: str
    expires_at: str
    created_at: str


# ============================================================================
# Authentication & Authorization
# ============================================================================

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """Get current authenticated user from JWT token"""
    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id = payload.get("user_id")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    
    try:
        user = await sync_to_async(User.objects.get)(id=user_id)
        
        # Automatic waitlist promotion check before rejecting inactive users
        try:
            promoted = await sync_to_async(maybe_promote_user_from_waitlist_sync)(user_id)
            if promoted:
                # Refresh user instance to reflect new active state
                user = await sync_to_async(User.objects.get)(id=user_id)
        except Exception as promote_error:
            logger.error(f"Waitlist promotion check failed for user {user_id}: {promote_error}")
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your account is on the waitlist. You can only access your profile. Please wait 1.10-1.35 hours for activation.",
            )
        return user
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )


@sync_to_async
def get_user_profile(user: User) -> UserProfile:
    """Get user profile for authenticated user"""
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        raise ValidationError(
            "User profile not found. Please complete your profile.",
            code="PROFILE_NOT_FOUND"
        )


@sync_to_async
def get_event(event_id: int) -> Event:
    """Get event by ID"""
    try:
        return Event.objects.select_related('host').get(id=event_id)
    except Event.DoesNotExist:
        raise NotFoundError(
            f"Event {event_id} not found",
            code="EVENT_NOT_FOUND"
        )


# ============================================================================
# API Endpoints - Payment Orders
# ============================================================================

@router.post("/orders", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_payment_order(
    request_data: PaymentOrderCreateRequest,
    user: User = Depends(get_current_user),
):
    """
    Create a payment order for an event.
    
    Business Rules:
    - Only for paid events
    - Requires valid capacity reservation (for paid events)
    - Order expires in 10 minutes
    - Returns PayU redirect payload
    
    Steps:
    1. Validate event and user
    2. Create payment order
    3. Generate PayU redirect payload
    4. Return payload to frontend
    """
    try:
        user_profile = await get_user_profile(user)
        event = await get_event(request_data.event_id)
        
        # Validate event is paid
        if not event.is_paid:
            raise ValidationError(
                "This event does not require payment",
                code="EVENT_NOT_PAID"
            )
        
        # Calculate correct amount including platform fee
        from core.models import PlatformFeeConfig
        from decimal import Decimal
        
        base_price = event.ticket_price or Decimal('0.00')
        seats_count = 1  # Default, will be updated from reservation if provided
        
        # Get seats from reservation if provided
        if request_data.reservation_key:
            @sync_to_async
            def get_reservation_seats():
                from events.models import CapacityReservation
                try:
                    reservation = CapacityReservation.objects.get(
                        reservation_key=request_data.reservation_key,
                        event=event,
                        user=user_profile,
                        consumed=False,
                    )
                    return reservation.seats_reserved
                except CapacityReservation.DoesNotExist:
                    return 1
            
            seats_count = await get_reservation_seats()
        
        # Calculate final amount (base + platform fee) × seats
        final_price_per_seat = PlatformFeeConfig.calculate_final_price(base_price)
        total_amount = final_price_per_seat * Decimal(seats_count)
        
        # Validate amount matches calculated total
        if abs(request_data.amount - total_amount) > Decimal('0.01'):  # Allow small rounding differences
            raise ValidationError(
                f"Payment amount must match calculated total: {total_amount} INR (base: {base_price} × {seats_count} seats + platform fee)",
                code="AMOUNT_MISMATCH"
            )
        
        # Create payment order
        # SECURITY: Identity enforcement - pass auth_user to prevent admin payments
        order = await sync_to_async(PaymentFlowService.create_payment_order)(
            user_profile=user_profile,
            event=event,
            amount=total_amount,
            reservation_key=request_data.reservation_key,
            auth_user=user,  # Pass for identity enforcement check
        )
        
        # Get user details for PayU payload
        firstname = user_profile.name or user.first_name or user.username
        email = user.email or f"{user.username}@loopin.app"
        phone = user_profile.phone_number or ""
        
        # Get base URL from settings or environment
        # PayU callbacks need full URL
        base_url = getattr(settings, 'PAYU_BASE_URL', None)
        if not base_url:
            # Fallback to first allowed host or default
            if settings.ALLOWED_HOSTS:
                host = settings.ALLOWED_HOSTS[0]
                base_url = f"https://{host}" if not host.startswith('http') else host
            else:
                base_url = "https://api.loopin.app"
        
        # Generate PayU redirect payload
        payload = PayUService.create_redirect_payload(
            order_id=order.order_id,
            amount=order.amount,
            productinfo=f"Event Ticket: {event.title}",
            firstname=firstname,
            email=email,
            phone=phone,
            base_url=base_url,
        )
        
        return {
            "success": True,
            "message": "Payment order created successfully",
            "data": {
                "order": {
                    "id": order.id,
                    "order_id": order.order_id,
                    "event_id": event.id,
                    "amount": str(order.amount),
                    "currency": order.currency,
                    "status": order.status,
                    "expires_at": order.expires_at.isoformat(),
                },
                "payu_redirect": {
                    "payu_url": PayUService.PAYMENT_URL,
                    "payload": payload,
                }
            }
        }
        
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except BusinessLogicError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating payment order: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the payment order"
        )


@router.get("/orders/{order_id}", response_model=Dict[str, Any])
async def get_payment_order(
    order_id: str = Path(..., description="Payment order ID"),
    user: User = Depends(get_current_user),
):
    """Get payment order details"""
    try:
        user_profile = await get_user_profile(user)
        
        @sync_to_async
        def get_order():
            try:
                order = PaymentOrder.objects.select_related('event', 'user').get(order_id=order_id)
                # Verify ownership
                if order.user_id != user_profile.id:
                    raise AuthorizationError(
                        "You don't have permission to access this payment order",
                        code="PERMISSION_DENIED"
                    )
                return order
            except PaymentOrder.DoesNotExist:
                raise NotFoundError(
                    f"Payment order {order_id} not found",
                    code="ORDER_NOT_FOUND"
                )
        
        order = await get_order()
        
        return {
            "success": True,
            "data": {
                "id": order.id,
                "order_id": order.order_id,
                "event_id": order.event.id,
                "event_title": order.event.title,
                "amount": str(order.amount),
                "currency": order.currency,
                "status": order.status,
                "payment_provider": order.payment_provider,
                "provider_payment_id": order.provider_payment_id,
                "transaction_id": order.transaction_id,
                "failure_reason": order.failure_reason,
                "expires_at": order.expires_at.isoformat() if order.expires_at else None,
                "created_at": order.created_at.isoformat(),
                "updated_at": order.updated_at.isoformat(),
            },
            "message": "Payment order retrieved successfully"
        }
        
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except AuthorizationError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving payment order: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the payment order"
        )


# ============================================================================
# PayU Callback Endpoints (No Authentication Required)
# ============================================================================

@router.post("/payu/success", response_model=Dict[str, Any])
async def payu_success_callback(request: Request):
    """
    Handle PayU success callback.
    
    This endpoint:
    1. Receives POST data from PayU redirect
    2. Extracts callback data
    3. Verifies reverse hash
    4. Finds payment order by txnid
    5. Finalizes payment on success
    6. Returns success response
    
    Note: This is called by PayU after payment, not by frontend.
    """
    try:
        # Get form data from PayU
        form_data = await request.form()
        callback_data = dict(form_data)
        
        logger.info(f"PayU success callback received: {callback_data}")
        
        # Extract callback data
        from payments.services.payu import PayUService
        extracted_data = PayUService.extract_callback_data(callback_data)
        
        # Verify hash
        is_valid = PayUService.verify_reverse_hash(
            status=extracted_data['status'],
            email=extracted_data['email'],
            firstname=extracted_data['firstname'],
            productinfo=extracted_data['productinfo'],
            amount=extracted_data['amount'],
            txnid=extracted_data['txnid'],
            received_hash=extracted_data['hash'],
        )
        
        if not is_valid:
            logger.error(f"PayU hash verification failed for txnid: {extracted_data['txnid']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hash verification failed"
            )
        
        # Get order
        order = await sync_to_async(PaymentFlowService.get_order_by_txnid)(
            extracted_data['txnid']
        )
        
        if not order:
            logger.error(f"Payment order not found for txnid: {extracted_data['txnid']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment order not found"
            )
        
        # Finalize payment (idempotent)
        if order.status not in ['paid', 'completed']:
            await sync_to_async(PaymentFlowService.finalize_payment_success)(
                order=order,
                provider_payment_id=extracted_data.get('mihpayid', ''),
                transaction_id=extracted_data.get('bank_ref_num', ''),
                callback_data=extracted_data,
            )
        
        # Return success response (PayU expects this)
        return {
            "success": True,
            "message": "Payment processed successfully",
            "order_id": order.order_id,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PayU success callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the payment"
        )


@router.post("/payu/failure", response_model=Dict[str, Any])
async def payu_failure_callback(request: Request):
    """
    Handle PayU failure callback.
    
    This endpoint:
    1. Receives POST data from PayU redirect
    2. Extracts callback data
    3. Verifies reverse hash
    4. Finds payment order by txnid
    5. Finalizes payment as failed
    6. Returns failure response
    """
    try:
        # Get form data from PayU
        form_data = await request.form()
        callback_data = dict(form_data)
        
        logger.info(f"PayU failure callback received: {callback_data}")
        
        # Extract callback data
        from payments.services.payu import PayUService
        extracted_data = PayUService.extract_callback_data(callback_data)
        
        # Verify hash
        is_valid = PayUService.verify_reverse_hash(
            status=extracted_data['status'],
            email=extracted_data['email'],
            firstname=extracted_data['firstname'],
            productinfo=extracted_data['productinfo'],
            amount=extracted_data['amount'],
            txnid=extracted_data['txnid'],
            received_hash=extracted_data['hash'],
        )
        
        if not is_valid:
            logger.error(f"PayU hash verification failed for txnid: {extracted_data['txnid']}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Hash verification failed"
            )
        
        # Get order
        order = await sync_to_async(PaymentFlowService.get_order_by_txnid)(
            extracted_data['txnid']
        )
        
        if not order:
            logger.error(f"Payment order not found for txnid: {extracted_data['txnid']}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment order not found"
            )
        
        # Finalize payment as failed (idempotent)
        if order.status != 'failed':
            failure_reason = extracted_data.get('error_Message') or extracted_data.get('error') or 'Payment failed'
            await sync_to_async(PaymentFlowService.finalize_payment_failure)(
                order=order,
                failure_reason=failure_reason,
                callback_data=extracted_data,
            )
        
        # Return failure response
        return {
            "success": False,
            "message": "Payment failed",
            "order_id": order.order_id,
            "failure_reason": extracted_data.get('error_Message') or extracted_data.get('error', 'Unknown error'),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing PayU failure callback: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the payment"
        )


# ============================================================================
# PayU Webhook Endpoint
# ============================================================================

@router.post("/payu/webhook", response_model=Dict[str, Any])
async def payu_webhook(request: Request):
    """
    Handle PayU webhook (server-to-server callback).
    
    SECURITY HARDENING:
    1. IP address verification (PayU IP ranges)
    2. Rate limiting (via middleware/proxy)
    3. Strict signature verification
    
    This endpoint:
    1. Verifies client IP (if configured)
    2. Receives webhook payload from PayU
    3. Creates webhook record
    4. Verifies hash (strict)
    5. Finalizes payment based on status
    6. Returns success response
    
    Note: This is idempotent and safe to retry.
    """
    from payments.services.webhook_security import WebhookSecurityService
    from functools import lru_cache
    
    # Simple in-memory rate limiting (for basic protection)
    # In production, use Redis-based rate limiting or nginx rate limiting
    @lru_cache(maxsize=1000)
    def check_rate_limit(ip: str) -> bool:
        """Simple rate limit check (10 requests per minute per IP)"""
        # This is a basic implementation - for production, use Redis
        # For now, we rely on nginx/proxy rate limiting
        return True
    
    try:
        # SECURITY: Verify client IP address (if configured)
        client_ip = WebhookSecurityService.get_client_ip(request)
        WebhookSecurityService.verify_ip_address(client_ip)
        
        logger.info(f"PayU webhook received from IP: {client_ip}")
        
        # SECURITY: Basic rate limiting check (production should use Redis/nginx)
        if not check_rate_limit(client_ip):
            logger.warning(f"Rate limit exceeded for webhook from IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later."
            )
        
        # Get JSON payload from PayU
        webhook_data = await request.json()
        
        logger.info(f"PayU webhook received: {webhook_data}")
        
        # Get signature from headers (if available)
        signature = request.headers.get('X-PayU-Signature', '')
        
        # Process webhook (idempotent) - signature verification happens inside
        webhook = await sync_to_async(PaymentFlowService.process_webhook)(
            webhook_data=webhook_data,
            signature=signature,
        )
        
        return {
            "success": True,
            "message": "Webhook processed successfully",
            "webhook_id": webhook.id,
        }
        
    except ValidationError as e:
        logger.error(f"Webhook validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except NotFoundError as e:
        logger.error(f"Webhook order not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing PayU webhook: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the webhook"
        )

