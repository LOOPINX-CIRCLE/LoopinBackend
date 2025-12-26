"""
Production-ready Host Payout API router for FastAPI.
Handles bank account management and payout requests for event hosts.

Architecture:
- Bank accounts are linked to User (hosts)
- Payout requests capture financial snapshots of events
- Platform fee is configurable via admin panel (default: 10%)
- All calculations are done at request time for audit trail
"""

from typing import Optional, List, Dict, Any
from datetime import datetime
from decimal import Decimal
import jwt
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    Query,
    Path,
)
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from django.contrib.auth.models import User
from django.conf import settings
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Q, Prefetch
from asgiref.sync import sync_to_async
from pydantic import BaseModel, Field
import logging

from core.utils.logger import get_logger
from core.exceptions import AuthorizationError, NotFoundError, ValidationError
from events.models import Event, Venue
from attendances.models import AttendanceRecord
from payments.models import PaymentOrder
from users.models import BankAccount, HostPayoutRequest, UserProfile
from users.schemas import (
    BankAccountCreate,
    BankAccountUpdate,
    BankAccountResponse,
    PayoutRequestCreate,
    PayoutRequestResponse,
    AttendeeDetail,
)

logger = get_logger(__name__)
router = APIRouter(prefix="/payouts", tags=["payouts"])

# JWT token scheme
security = HTTPBearer()


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
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive",
            )
        return user
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )


# ============================================================================
# Business Logic Functions
# ============================================================================

@sync_to_async
def get_user_bank_accounts(user: User) -> List[BankAccount]:
    """Get all bank accounts for a user"""
    return list(BankAccount.objects.filter(host=user, is_active=True).order_by('-is_primary', '-created_at'))


@sync_to_async
def get_bank_account_by_id(account_id: int, user: User) -> BankAccount:
    """Get a specific bank account for a user"""
    try:
        account = BankAccount.objects.get(id=account_id, host=user)
        return account
    except BankAccount.DoesNotExist:
        raise NotFoundError(
            "Bank account not found or you don't have permission to access it.",
            code="BANK_ACCOUNT_NOT_FOUND"
        )


@sync_to_async
def _create_bank_account(user: User, data: BankAccountCreate) -> BankAccount:
    """Create a new bank account for the user"""
    with transaction.atomic():
        account = BankAccount.objects.create(
            host=user,
            bank_name=data.bank_name,
            account_number=data.account_number,
            ifsc_code=data.ifsc_code,
            account_holder_name=data.account_holder_name,
            is_primary=data.is_primary,
        )
        logger.info(f"Bank account created: {account.id} for user {user.id}")
        return account


@sync_to_async
def _update_bank_account(account: BankAccount, data: BankAccountUpdate) -> BankAccount:
    """Update an existing bank account"""
    with transaction.atomic():
        if data.bank_name is not None:
            account.bank_name = data.bank_name
        if data.account_number is not None:
            account.account_number = data.account_number
        if data.ifsc_code is not None:
            account.ifsc_code = data.ifsc_code
        if data.account_holder_name is not None:
            account.account_holder_name = data.account_holder_name
        if data.is_primary is not None:
            account.is_primary = data.is_primary
        if data.is_active is not None:
            account.is_active = data.is_active
        
        account.save()
        logger.info(f"Bank account updated: {account.id}")
        return account


@sync_to_async
def _delete_bank_account(account: BankAccount) -> None:
    """Soft delete a bank account"""
    with transaction.atomic():
        account.is_active = False
        account.save()
        logger.info(f"Bank account deactivated: {account.id}")


@sync_to_async
def get_event_for_payout(event_id: int, user: User) -> Event:
    """Get event and verify host ownership"""
    try:
        event = Event.objects.select_related('host', 'venue').get(id=event_id)
    except Event.DoesNotExist:
        raise NotFoundError(
            "Event not found.",
            code="EVENT_NOT_FOUND"
        )
    
    # Verify the user is the host of this event
    if event.host_id != user.id:
        raise AuthorizationError(
            "You can only request payouts for events you host.",
            code="NOT_EVENT_HOST"
        )
    
    return event


@sync_to_async
def calculate_event_financials(event: Event) -> Dict[str, Any]:
    """
    Calculate all financial metrics for an event payout request.
    
    Uses PaymentOrder table as source of truth (most reliable):
    - Filters by status='paid' or 'completed' and is_final=True
    - Uses immutable financial snapshots from PaymentOrder
    - Excludes retry attempts (only final payments)
    
    Business Logic:
    - Buyer pays: Base ticket fare + platform fee (configurable via admin)
    - Host earns: Base ticket fare × Tickets sold (no platform fee deduction)
    - Platform fee: Base ticket fare × platform fee % × Tickets sold (from config)
    
    Returns:
        Dictionary containing:
        - total_tickets_sold: Count of seats from paid payment orders
        - attendees_details: List of attendee names and contacts
        - platform_fee_amount: Total platform fee from payment orders (immutable snapshot)
        - final_earning: Total host earnings from payment orders (immutable snapshot)
    """
    from decimal import Decimal, ROUND_HALF_UP
    from payments.models import PaymentOrder
    
    # Get all paid payment orders for this event (final payments only, exclude retry attempts)
    paid_orders = PaymentOrder.objects.filter(
        event=event,
        status__in=['paid', 'completed'],
        is_final=True  # Only count final successful payments, not retry attempts
    )
    
    # Calculate totals from PaymentOrder immutable financial snapshots
    total_host_earning = Decimal('0.00')
    total_platform_fee = Decimal('0.00')
    total_revenue = Decimal('0.00')
    total_tickets_sold = 0
    
    # Get base ticket fare from first order (or event if no orders yet)
    base_ticket_fare = event.ticket_price or Decimal('0.00')
    final_ticket_fare_per_ticket = base_ticket_fare
    
    for order in paid_orders:
        # Use immutable financial snapshots from PaymentOrder
        if order.total_host_earning:
            total_host_earning += order.total_host_earning
        if order.total_platform_fee:
            total_platform_fee += order.total_platform_fee
        total_revenue += order.amount
        total_tickets_sold += order.seats_count
        
        # Get base ticket fare from order snapshot (if available)
        if order.base_price_per_seat:
            base_ticket_fare = order.base_price_per_seat
        
        # Get final ticket fare from calculation (base + platform fee)
        if order.platform_fee_percentage and order.base_price_per_seat:
            from core.models import PlatformFeeConfig
            final_ticket_fare_per_ticket = PlatformFeeConfig.calculate_final_price(order.base_price_per_seat)
    
    # If no orders, use event ticket_price (edge case)
    if total_tickets_sold == 0:
        base_ticket_fare = event.ticket_price or Decimal('0.00')
        from core.models import PlatformFeeConfig
        final_ticket_fare_per_ticket = PlatformFeeConfig.calculate_final_price(base_ticket_fare)
    
    # Round to 2 decimal places
    total_host_earning = total_host_earning.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    total_platform_fee = total_platform_fee.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    final_ticket_fare_per_ticket = final_ticket_fare_per_ticket.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    
    # Final earning is total host earnings from payment orders
    final_earning = total_host_earning
    platform_fee_amount = total_platform_fee
    
    # Get attendees details from EventAttendee (linked to payment orders)
    from events.models import EventAttendee
    paid_attendees = EventAttendee.objects.filter(
        event=event,
        is_paid=True,
        payment_order__isnull=False,
        status__in=['going', 'checked_in']
    ).select_related('user', 'user__profile', 'payment_order')
    
    # Ensure we use same count as payment orders
    # But get attendee details for the response
    attendees_details = []
    for attendee in paid_attendees:
        user = attendee.user
        profile = getattr(user, 'profile', None)
        
        # Get name from profile or user
        name = ""
        if profile and profile.name:
            name = profile.name
        elif user.first_name or user.last_name:
            name = f"{user.first_name or ''} {user.last_name or ''}".strip()
        else:
            name = user.username
        
        # Get contact (phone or email)
        contact = ""
        if profile and profile.phone_number:
            contact = profile.phone_number
        elif user.email:
            contact = user.email
        else:
            contact = user.username
        
        attendees_details.append({
            "name": name,
            "contact": contact
        })
    
    # Get event location
    event_location = ""
    if event.venue:
        event_location = f"{event.venue.name}, {event.venue.city}"
    elif event.venue_text:
        event_location = event.venue_text
    else:
        event_location = "Location not specified"
    
    # Get host name from UserProfile
    host_name = ""
    if event.host.name:
        host_name = event.host.name
    elif event.host.phone_number:
        host_name = event.host.phone_number
    elif hasattr(event.host, 'user') and event.host.user:
        # Fallback to User.username if available
        host_name = event.host.user.username
    else:
        host_name = "Unknown Host"
    
    return {
        "host_name": host_name,
        "event_name": event.title,
        "event_date": event.start_time,
        "event_location": event_location,
        "total_capacity": event.max_capacity,
        "base_ticket_fare": base_ticket_fare,
        "final_ticket_fare": final_ticket_fare_per_ticket,
        "total_tickets_sold": total_tickets_sold,
        "attendees_details": attendees_details,
        "platform_fee_amount": platform_fee_amount,
        "final_earning": final_earning,
    }


@sync_to_async
def create_payout_request(
    user: User,
    event: Event,
    bank_account: BankAccount,
    financials: Dict[str, Any]
) -> HostPayoutRequest:
    """
    Create a payout request with financial snapshot.
    
    Links payment orders to payout for reconciliation (CFO requirement).
    """
    with transaction.atomic():
        # Get all paid payment orders for this event (for reconciliation)
        from payments.models import PaymentOrder
        paid_orders = PaymentOrder.objects.filter(
            event=event,
            status__in=['paid', 'completed'],
            is_final=True,  # Only final payments, not retry attempts
        )
        
        payout = HostPayoutRequest.objects.create(
            bank_account=bank_account,
            event=event,
            host_name=financials["host_name"],
            event_name=financials["event_name"],
            event_date=financials["event_date"],
            event_location=financials["event_location"],
            total_capacity=financials["total_capacity"],
            base_ticket_fare=financials["base_ticket_fare"],
            final_ticket_fare=financials["final_ticket_fare"],
            total_tickets_sold=financials["total_tickets_sold"],
            attendees_details=financials["attendees_details"],
            platform_fee_amount=financials["platform_fee_amount"],
            final_earning=financials["final_earning"],
            status='pending',
        )
        
        # Link payment orders to payout for reconciliation
        payout.payment_orders.set(paid_orders)
        
        logger.info(
            f"Payout request created: {payout.id} for event {event.id}, "
            f"earning: {payout.final_earning} INR, "
            f"linked to {paid_orders.count()} payment orders"
        )
        return payout


@sync_to_async
def get_user_payout_requests(
    user: User,
    status_filter: Optional[str] = None,
    offset: int = 0,
    limit: int = 20
) -> tuple[List[HostPayoutRequest], int]:
    """Get payout requests for user's events"""
    queryset = HostPayoutRequest.objects.filter(
        bank_account__host=user
    ).select_related('bank_account', 'event').order_by('-created_at')
    
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    
    total = queryset.count()
    payout_requests = list(queryset[offset:offset + limit])
    
    return payout_requests, total


@sync_to_async
def get_payout_request_by_id(payout_id: int, user: User) -> HostPayoutRequest:
    """Get a specific payout request"""
    try:
        payout = HostPayoutRequest.objects.select_related('bank_account', 'event').get(id=payout_id)
        if payout.bank_account.host_id != user.id:
            raise AuthorizationError(
                "You don't have permission to access this payout request.",
                code="PERMISSION_DENIED"
            )
        return payout
    except HostPayoutRequest.DoesNotExist:
        raise NotFoundError(
            "Payout request not found.",
            code="PAYOUT_REQUEST_NOT_FOUND"
        )


# ============================================================================
# API Endpoints - Bank Accounts
# ============================================================================

@router.get("/bank-accounts", response_model=Dict[str, Any])
async def list_bank_accounts(user: User = Depends(get_current_user)):
    """
    List all bank accounts for the authenticated user.
    
    Returns a list of bank accounts with masked account numbers for security.
    """
    try:
        accounts = await get_user_bank_accounts(user)
        
        return {
            "success": True,
            "data": [
                {
                    "id": account.id,
                    "uuid": str(account.uuid),
                    "bank_name": account.bank_name,
                    "masked_account_number": account.masked_account_number,
                    "ifsc_code": account.ifsc_code,
                    "account_holder_name": account.account_holder_name,
                    "is_primary": account.is_primary,
                    "is_verified": account.is_verified,
                    "is_active": account.is_active,
                    "created_at": account.created_at.isoformat(),
                    "updated_at": account.updated_at.isoformat(),
                }
                for account in accounts
            ],
            "message": "Bank accounts retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error listing bank accounts: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving bank accounts"
        )


@router.post("/bank-accounts", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_bank_account(
    data: BankAccountCreate,
    user: User = Depends(get_current_user)
):
    """
    Create a new bank account for the authenticated user.
    
    - **bank_name**: Name of the bank (e.g., "State Bank of India")
    - **account_number**: Bank account number (8-30 digits)
    - **ifsc_code**: IFSC code (11 characters, format: AAAA0XXXXXX)
    - **account_holder_name**: Name as registered with bank
    - **is_primary**: Set as primary account (only one primary per user)
    """
    try:
        account = await _create_bank_account(user, data)
        
        return {
            "success": True,
            "message": "Bank account created successfully",
            "data": {
                "id": account.id,
                "uuid": str(account.uuid),
                "bank_name": account.bank_name,
                "masked_account_number": account.masked_account_number,
                "ifsc_code": account.ifsc_code,
                "account_holder_name": account.account_holder_name,
                "is_primary": account.is_primary,
                "is_verified": account.is_verified,
                "is_active": account.is_active,
                "created_at": account.created_at.isoformat(),
                "updated_at": account.updated_at.isoformat(),
            }
        }
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating bank account: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the bank account"
        )


@router.get("/bank-accounts/{account_id}", response_model=Dict[str, Any])
async def get_bank_account(
    account_id: int = Path(..., description="Bank account ID"),
    user: User = Depends(get_current_user)
):
    """Get details of a specific bank account"""
    try:
        account = await get_bank_account_by_id(account_id, user)
        
        return {
            "success": True,
            "data": {
                "id": account.id,
                "uuid": str(account.uuid),
                "bank_name": account.bank_name,
                "masked_account_number": account.masked_account_number,
                "ifsc_code": account.ifsc_code,
                "account_holder_name": account.account_holder_name,
                "is_primary": account.is_primary,
                "is_verified": account.is_verified,
                "is_active": account.is_active,
                "created_at": account.created_at.isoformat(),
                "updated_at": account.updated_at.isoformat(),
            },
            "message": "Bank account retrieved successfully"
        }
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error retrieving bank account: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the bank account"
        )


@router.put("/bank-accounts/{account_id}", response_model=Dict[str, Any])
async def update_bank_account(
    account_id: int = Path(..., description="Bank account ID"),
    data: BankAccountUpdate = ...,
    user: User = Depends(get_current_user)
):
    """Update a bank account"""
    try:
        account = await get_bank_account_by_id(account_id, user)
        account = await _update_bank_account(account, data)
        
        return {
            "success": True,
            "message": "Bank account updated successfully",
            "data": {
                "id": account.id,
                "uuid": str(account.uuid),
                "bank_name": account.bank_name,
                "masked_account_number": account.masked_account_number,
                "ifsc_code": account.ifsc_code,
                "account_holder_name": account.account_holder_name,
                "is_primary": account.is_primary,
                "is_verified": account.is_verified,
                "is_active": account.is_active,
                "created_at": account.created_at.isoformat(),
                "updated_at": account.updated_at.isoformat(),
            }
        }
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating bank account: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the bank account"
        )


@router.delete("/bank-accounts/{account_id}", response_model=Dict[str, Any])
async def delete_bank_account(
    account_id: int = Path(..., description="Bank account ID"),
    user: User = Depends(get_current_user)
):
    """Delete (deactivate) a bank account"""
    try:
        account = await get_bank_account_by_id(account_id, user)
        await _delete_bank_account(account)
        
        return {
            "success": True,
            "message": "Bank account deleted successfully"
        }
    except NotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error deleting bank account: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the bank account"
        )


# ============================================================================
# API Endpoints - Payout Requests
# ============================================================================

@router.post("/requests", response_model=Dict[str, Any], status_code=status.HTTP_201_CREATED)
async def create_payout_request_endpoint(
    data: PayoutRequestCreate,
    user: User = Depends(get_current_user)
):
    """
    Create a payout request for an event.
    
    This endpoint:
    1. Validates that the user is the host of the event
    2. Validates that the bank account belongs to the user
    3. Calculates all financial metrics (tickets sold, revenue, platform fee, final earning)
    4. Captures a snapshot of event and attendee details
    5. Creates the payout request with status 'pending'
    
    - **event_id**: ID of the event for payout
    - **bank_account_id**: ID of the bank account to receive payout
    """
    try:
        # Get and validate event
        event = await get_event_for_payout(data.event_id, user)
        
        # Get and validate bank account
        bank_account = await get_bank_account_by_id(data.bank_account_id, user)
        if not bank_account.is_active:
            raise ValidationError(
                "Cannot use an inactive bank account for payout",
                code="INACTIVE_BANK_ACCOUNT"
            )
        
        # Calculate financials
        financials = await calculate_event_financials(event)
        
        # Validate that there are tickets sold
        if financials["total_tickets_sold"] == 0:
            raise ValidationError(
                "Cannot create payout request for an event with no ticket sales",
                code="NO_TICKET_SALES"
            )
        
        # Check if payout request already exists for this event
        existing_request = await sync_to_async(HostPayoutRequest.objects.filter(
            event=event,
            status__in=['pending', 'approved', 'processing']
        ).exists)()
        
        if existing_request:
            raise ValidationError(
                "A payout request already exists for this event with status 'pending', 'approved', or 'processing'",
                code="PAYOUT_REQUEST_EXISTS"
            )
        
        # Create payout request
        payout = await create_payout_request(user, event, bank_account, financials)
        
        return {
            "success": True,
            "message": "Payout request created successfully",
            "data": {
                "id": payout.id,
                "uuid": str(payout.uuid),
                "event_id": event.id,
                "event_name": payout.event_name,
                "host_name": payout.host_name,
                "total_tickets_sold": payout.total_tickets_sold,
                "base_ticket_fare": float(payout.base_ticket_fare),
                "final_ticket_fare": float(payout.final_ticket_fare),
                "platform_fee_amount": float(payout.platform_fee_amount),
                "platform_fee_percentage": payout.platform_fee_percentage,
                "final_earning": float(payout.final_earning),
                "status": payout.status,
                "created_at": payout.created_at.isoformat(),
            }
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
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating payout request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the payout request"
        )


@router.get("/requests", response_model=Dict[str, Any])
async def list_payout_requests(
    status: Optional[str] = Query(None, description="Filter by status"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    limit: int = Query(20, ge=1, le=100, description="Results per page"),
    user: User = Depends(get_current_user)
):
    """
    List payout requests for the authenticated user's events.
    
    Filters and pagination available.
    """
    try:
        payouts, total = await get_user_payout_requests(user, status, offset, limit)
        
        return {
            "success": True,
            "data": [
                {
                    "id": payout.id,
                    "uuid": str(payout.uuid),
                    "event_id": payout.event.id,
                    "event_name": payout.event_name,
                    "host_name": payout.host_name,
                    "event_date": payout.event_date.isoformat(),
                    "total_tickets_sold": payout.total_tickets_sold,
                    "final_earning": float(payout.final_earning),
                    "status": payout.status,
                    "created_at": payout.created_at.isoformat(),
                }
                for payout in payouts
            ],
            "pagination": {
                "offset": offset,
                "limit": limit,
                "total": total,
            },
            "message": "Payout requests retrieved successfully"
        }
    except Exception as e:
        logger.error(f"Error listing payout requests: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving payout requests"
        )


@router.get("/requests/{payout_id}", response_model=Dict[str, Any])
async def get_payout_request(
    payout_id: int = Path(..., description="Payout request ID"),
    user: User = Depends(get_current_user)
):
    """
    Get detailed information about a specific payout request.
    
    Includes all event details, financial calculations, and attendee list.
    """
    try:
        payout = await get_payout_request_by_id(payout_id, user)
        
        # Convert attendees_details to proper format
        attendees = [
            AttendeeDetail(**attendee) for attendee in payout.attendees_details
        ]
        
        return {
            "success": True,
            "data": {
                "id": payout.id,
                "uuid": str(payout.uuid),
                "bank_account": {
                    "id": payout.bank_account.id,
                    "bank_name": payout.bank_account.bank_name,
                    "masked_account_number": payout.bank_account.masked_account_number,
                    "ifsc_code": payout.bank_account.ifsc_code,
                    "account_holder_name": payout.bank_account.account_holder_name,
                },
                "event_id": payout.event.id,
                "host_name": payout.host_name,
                "event_name": payout.event_name,
                "event_date": payout.event_date.isoformat(),
                "event_location": payout.event_location,
                "total_capacity": payout.total_capacity,
                "base_ticket_fare": float(payout.base_ticket_fare),
                "final_ticket_fare": float(payout.final_ticket_fare),
                "total_tickets_sold": payout.total_tickets_sold,
                "attendees_details": [{"name": a.name, "contact": a.contact} for a in attendees],
                "platform_fee_amount": float(payout.platform_fee_amount),
                "platform_fee_percentage": payout.platform_fee_percentage,
                "final_earning": float(payout.final_earning),
                "status": payout.status,
                "transaction_reference": payout.transaction_reference,
                "rejection_reason": payout.rejection_reason,
                "notes": payout.notes,
                "created_at": payout.created_at.isoformat(),
                "updated_at": payout.updated_at.isoformat(),
                "processed_at": payout.processed_at.isoformat() if payout.processed_at else None,
            },
            "message": "Payout request retrieved successfully"
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
        logger.error(f"Error retrieving payout request: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving the payout request"
        )

