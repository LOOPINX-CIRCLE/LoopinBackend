# Notifications Module Documentation

## Overview
The Notifications module manages user notifications, messaging, and communication within the Loopin platform.

## Models

### Notification
- **Purpose**: User notification management with read status tracking for **normal users (customers)**
- **Key Fields**: recipient (USER_PROFILE), sender (USER_PROFILE), type, title, message, reference_type, reference_id
- **Relationships**: 
  - `recipient` → `ForeignKey('users.UserProfile')` - Normal user receiving notification
  - `sender` → `ForeignKey('users.UserProfile')` - Normal user sending notification (optional)
- **Types**: event_request, event_invite, payment_update, system_alert
- **Status**: read, unread, archived
- **Note**: Notifications are for normal users (`USER_PROFILE`), not admin users

## Notification Types

### Event-Related Notifications
- **Event Request**: Notifications for event join requests
- **Event Invite**: Invitations to events from hosts
- **Event Updates**: Changes to event details or status
- **Event Reminders**: Upcoming event notifications

### Payment Notifications
- **Payment Success**: Confirmation of successful payments
- **Payment Failure**: Failed payment notifications
- **Refund Updates**: Refund processing notifications

### System Notifications
- **Account Updates**: Profile changes, verification status
- **Security Alerts**: Login attempts, password changes
- **Maintenance**: System maintenance notifications

## Delivery Methods
- **In-App**: Real-time notifications within the application
- **Push Notifications**: Mobile push notifications
- **Email**: Email notifications for important updates
- **SMS**: Critical notifications via SMS

## Business Logic
- **Notification Preferences**: User-configurable notification settings
- **Batch Processing**: Efficient notification delivery
- **Retry Logic**: Failed notification retry mechanisms
- **Rate Limiting**: Prevent notification spam

## Integration Points
- **Events Module**: Event-related notifications
- **Payments Module**: Payment status notifications
- **Users Module**: User preference management
- **Audit Module**: Notification delivery tracking
