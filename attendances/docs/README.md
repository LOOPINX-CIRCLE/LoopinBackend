# Attendances Module Documentation

## Overview
The Attendances module manages event check-in/check-out processes, ticket validation, and attendance tracking.

## Models

### AttendanceRecord
- **Purpose**: Tracks user attendance at events with check-in/check-out functionality
- **Key Fields**: event, user, status, ticket_secret, seats, checked_in_at, checked_out_at
- **Status Options**: going, not_going, checked_in, cancelled
- **Methods**: check_in(), check_out(), generate_ticket_secret()

### TicketSecret
- **Purpose**: Cryptographically secure ticket verification
- **Key Fields**: attendance_record, secret_hash, secret_salt, is_redeemed, redeemed_at
- **Security**: Hashed ticket secrets for secure validation

## Business Logic
- **Ticket Generation**: Unique ticket secrets for each attendance
- **Check-in Process**: Timestamp recording when user checks in
- **Check-out Process**: Event completion tracking
- **Capacity Management**: Seat allocation and tracking

## Security Features
- Unique ticket secrets per attendance
- Cryptographically hashed ticket secrets
- Ticket redemption tracking
- Audit trail for all attendance actions

## Integration Points
- **Events Module**: Links to Event model
- **Users Module**: Links to User model
- **Payments Module**: Validates payment status
- **Audit Module**: Logs all attendance actions
