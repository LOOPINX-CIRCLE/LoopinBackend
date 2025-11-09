# Payments Module Documentation

## Overview
The Payments module handles payment processing, order management, and transaction tracking for event tickets and services.

## Models

### PaymentOrder
- **Purpose**: Payment orders for event tickets and services
- **Key Fields**: user, event, amount, currency, status, payment_provider
- **Status Options**: created, paid, failed, refunded
- **Providers**: razorpay, stripe, paypal (configurable)

### PaymentTransaction
- **Purpose**: Individual transaction records with provider details
- **Key Fields**: order, provider_transaction_id, amount, status, provider_response
- **Audit**: Complete transaction history and provider responses

### PaymentWebhook
- **Purpose**: Webhook handling for payment provider notifications
- **Key Fields**: provider, event_type, payload, processed, processed_at
- **Security**: Webhook signature verification

## Payment Flow
1. **Order Creation**: User initiates payment for event ticket
2. **Provider Integration**: Payment request sent to provider (Razorpay/Stripe)
3. **Transaction Processing**: Provider handles payment processing
4. **Webhook Handling**: Provider sends status updates via webhooks
5. **Order Completion**: Order status updated based on payment result

## Security Features
- Webhook signature verification
- Encrypted sensitive payment data
- Audit trail for all transactions
- PCI compliance considerations

## Integration Points
- **Events Module**: Links to Event for ticket purchases
- **Users Module**: Links to User for payment history
- **Attendances Module**: Validates payment before check-in
- **Audit Module**: Logs all payment activities
