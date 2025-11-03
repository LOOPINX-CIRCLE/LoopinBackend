# Attendances Module Documentation

## Overview
The Attendances module manages event check-in/check-out processes, ticket validation, and attendance tracking.

## Models

### AttendanceRecord
- **Purpose**: Tracks user attendance at events with check-in/check-out functionality
- **Key Fields**: event, user, status, ticket_secret, seats, checked_in_at, checked_out_at
- **Status Options**: going, not_going, checked_in, cancelled
- **Methods**: check_in(), check_out(), generate_ticket_secret()

### AttendanceOTP
- **Purpose**: OTP-based verification for event check-in
- **Key Fields**: attendance_record, otp_code, expires_at, is_verified
- **Security**: Time-limited OTP for secure check-in

## Business Logic
- **Ticket Generation**: Unique ticket secrets for each attendance
- **Check-in Process**: OTP verification and timestamp recording
- **Check-out Process**: Event completion tracking
- **Capacity Management**: Seat allocation and tracking

## Security Features
- Unique ticket secrets per attendance
- OTP-based check-in verification
- Time-limited access codes
- Audit trail for all attendance actions

## Integration Points
- **Events Module**: Links to Event model
- **Users Module**: Links to User model
- **Payments Module**: Validates payment status
- **Audit Module**: Logs all attendance actions
