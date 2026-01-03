# Payments Module Documentation

## Overview
The Payments module handles payment processing, order management, and transaction tracking for event tickets and services. It includes PayU integration, financial snapshot tracking, and payment enforcement for paid events.

## Models

### PaymentOrder
- **Purpose**: Payment orders for event tickets and services with financial snapshot and retry tracking
- **Key Fields**: 
  - `user` (UserProfile FK), `event` (Event FK), `amount`, `currency`, `status`, `payment_provider`
  - `seats_count` - Number of seats/tickets this payment covers
  - **Financial Snapshot (Immutable at payment time)**:
    - `base_price_per_seat` - Base ticket price per seat
    - `platform_fee_percentage` - Platform fee percentage (e.g., 10.00 for 10%)
    - `platform_fee_amount` - Total platform fee amount
    - `host_earning_per_seat` - Host earning per seat (equals base_price_per_seat)
  - **Retry Tracking**:
    - `parent_order` - Parent order if this is a retry attempt
    - `is_final` - True if this is the final successful payment (not a retry)
- **Status Options**: created, pending, paid, completed, failed, cancelled, refunded, unpaid
- **Providers**: razorpay, stripe, paypal, paytm, phonepe, gpay, **payu**, cash, bank_transfer
- **Relationships**:
  - Links to `EventAttendee` via `payment_order` FK (fulfilled_attendees)
  - Links to `AttendanceRecord` via `payment_order` FK (attendance_records)
  - Links to `HostPayoutRequest` via M2M (payment_orders)

### PaymentTransaction
- **Purpose**: Individual transaction records with provider details
- **Key Fields**: order, provider_transaction_id, amount, status, provider_response
- **Audit**: Complete transaction history and provider responses

### PaymentWebhook
- **Purpose**: Webhook handling for payment provider notifications
- **Key Fields**: provider, event_type, payload, processed, processed_at
- **Security**: Webhook signature verification

## Payment Flow (PayU Integration)
1. **Order Creation**: User initiates payment for event ticket
   - Creates `PAYMENT_ORDER` with `status='created'`
   - Requires valid `CAPACITY_RESERVATION` for paid events
   - Sets `seats_count` from reservation
2. **Hash Generation**: Backend generates PayU hash (SHA-512)
   - Hash includes: key|txnid|amount|productinfo|firstname|email|||||||||||salt
   - Never stored in database (security-first approach)
3. **Redirect Payload**: Backend returns PayU redirect payload to frontend
   - Frontend builds HTML form and auto-submits
   - User redirected to PayU payment page
4. **Payment Processing**: PayU handles payment
5. **Success/Failure Callback**: PayU redirects to success/failure URL
   - Backend verifies reverse hash
   - Updates `PAYMENT_ORDER.status` to 'paid' or 'failed'
   - Captures financial snapshot (immutable)
   - Marks order as `is_final=True`
   - Creates `PAYMENT_TRANSACTION`
6. **Webhook Handling**: PayU sends server-to-server webhook
   - Idempotent processing
   - Finalizes payment if redirect callback failed
7. **Order Finalization**: On success
   - Creates/updates `EVENT_ATTENDEE` with `payment_order` link
   - Creates/updates `ATTENDANCE_RECORD` with `payment_order` link
   - Consumes `CAPACITY_RESERVATION`
   - Updates event `going_count`

## Financial Snapshot (CFO Requirement)
- All financial fields are captured at payment time and never change retroactively
- Enables accurate reconciliation even if pricing rules change later
- Fields: `base_price_per_seat`, `platform_fee_percentage`, `platform_fee_amount`, `host_earning_per_seat`

## Retry Tracking (CTO Requirement)
- `parent_order` links retry attempts to original order
- `is_final` flag distinguishes final successful payment from retry attempts
- Only final payments (`is_final=True`) are used for reconciliation and payouts

## Payment Enforcement
- For paid events (`event.is_paid == True`), payment is required before:
  - Creating `EVENT_ATTENDEE` (request acceptance, invite acceptance)
  - Confirming attendance
  - Accessing tickets
  - Checking in to event
- Payment status source of truth: `PAYMENT_ORDER.status == 'paid'`

## Security Features
- **PayU Integration**:
  - All credentials from environment variables (PAYU_MERCHANT_KEY, PAYU_MERCHANT_SALT)
  - Backend-only hash generation (SHA-512)
  - Never persist salt or hashes in database
  - Hash verification on all PayU responses
- Webhook signature verification
- Encrypted sensitive payment data
- Audit trail for all transactions
- PCI compliance considerations

## API Endpoints
- `POST /api/payments/orders` - Create payment order and get PayU redirect payload
- `GET /api/payments/orders/{order_id}` - Get payment order details
- `POST /api/payments/payu/success` - PayU success callback handler
- `POST /api/payments/payu/failure` - PayU failure callback handler
- `POST /api/payments/payu/webhook` - PayU webhook handler

## Integration Points
- **Events Module**: Links to Event for ticket purchases, payment enforcement
- **Users Module**: Links to UserProfile for payment history
- **Attendances Module**: Validates payment before check-in, links to payment orders
- **Payouts Module**: Links payment orders to payout requests for reconciliation
- **Audit Module**: Logs all payment activities
