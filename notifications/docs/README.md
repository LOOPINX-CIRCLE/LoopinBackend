# Notifications Module - Complete Documentation

## Overview

The Notifications module is a centralized system for managing all user communications within the Loopin platform. It handles transactional notifications, push notification delivery, device management, and maintains a complete audit trail of all notifications sent to users.

**Key Principles:**
- **Transactional Focus**: All notifications are triggered by deterministic backend events (payment completed, event cancelled, request approved, etc.)
- **Dual Delivery**: Notifications are delivered both as push notifications (via OneSignal) and stored as in-app notification records
- **Template-Driven**: All notification messages use centralized templates for consistency and stability
- **Never Blocks Business Logic**: Notification failures never interrupt core business operations
- **Complete Audit Trail**: Every notification attempt is logged in the database, regardless of delivery success

---

## Architecture

The notification system consists of five core components working together:

### 1. **Template Registry (messages.py)**
The single source of truth for all notification copy. Contains pre-defined templates with titles, messages, target screens, and required parameters. Templates use placeholders (like `{{event_name}}`) that are replaced with actual values at runtime. This ensures consistency across the platform and makes message updates controlled and reviewable.

### 2. **Push Notification Dispatcher (dispatcher.py)**
The central orchestrator for all notification delivery. When a notification needs to be sent, the dispatcher:
- Renders the template with provided context parameters
- Checks user notification preferences
- Resolves the user profile to their active device player IDs
- Sends push notifications via OneSignal
- Persists notification records in the database
- Handles failures gracefully without blocking business logic

This is the **only entry point** for sending notifications in the system.

### 3. **OneSignal Client (onesignal.py)**
Low-level HTTP client that communicates with the OneSignal REST API. Handles authentication, payload formatting, and error handling. Never raises fatal exceptions - always returns success/failure status with error details.

### 4. **Notification Preferences Service (preferences.py)**
Manages user opt-in/opt-out logic for different notification types. Currently, all transactional notifications are enabled by default, with marketing notifications disabled. Designed to support future preference expansion without refactoring.

### 5. **Device Management (models.py - UserDevice)**
Tracks user devices registered for push notifications. Maps user profiles to OneSignal player IDs, supports multiple devices per user (iOS and Android), and handles device lifecycle (registration, activation, deactivation).

---

## How It Works

### Complete Notification Flow

#### Step 1: Device Registration
When a user opens the mobile app, the app obtains a OneSignal player ID from the OneSignal SDK. The app then calls the backend API to register this device, associating the player ID with the user's profile. This registration can happen on app launch, after login, or when permissions are granted. One user can have multiple devices registered (for example, an iPhone and an iPad).

#### Step 2: Notification Trigger
A business event occurs that requires notification (e.g., payment succeeds, event is cancelled, request is approved). The business logic module (Events, Payments, etc.) calls the dispatcher service with a template key and context parameters.

#### Step 3: Template Rendering
The dispatcher looks up the template by key, validates that all required parameters are provided, and renders the template by replacing placeholders with actual values. If any required parameter is missing, the process fails immediately with a clear error - there are no silent fallbacks.

#### Step 4: Preference Check
Before sending, the dispatcher checks if the user has enabled notifications of this type. If disabled, the push notification is skipped, but the notification record is still saved in the database (for audit trail and in-app inbox).

#### Step 5: Device Resolution
The dispatcher queries the database for all active devices belonging to the recipient's user profile. It extracts the OneSignal player IDs from these devices and de-duplicates them (to handle race conditions where the same device might be registered twice).

#### Step 6: Push Delivery
If there are active devices and notifications are enabled, the dispatcher calls the OneSignal client to send the push notification to all registered devices. The OneSignal client handles HTTP communication, error responses, and extracts invalid player IDs if any devices have become invalid.

#### Step 7: Device Deactivation
If OneSignal returns any invalid player IDs, those devices are automatically deactivated in the database. This handles cases where users uninstall the app, reset their device, or player IDs rotate.

#### Step 8: Notification Record Persistence
Regardless of push delivery success or failure, a notification record is always created in the database. This serves two purposes:
- **Audit Trail**: Complete history of all notifications sent
- **In-App Inbox**: Users can see notifications even if push delivery failed or they missed the push

### Delivery Guarantees

**Push Notifications**: Best-effort delivery. If OneSignal is unavailable, devices are invalid, or network issues occur, the push may not be delivered. This never blocks business operations.

**Notification Records**: Always persisted. Every notification attempt creates a database record that users can access through the in-app notification inbox.

---

## Data Models

### Notification
The core model storing all notification records. Each record represents one notification sent to a user, whether push delivery succeeded or not.

**Key Fields:**
- `recipient`: Links to USER_PROFILE (the user receiving the notification)
- `sender`: Optional link to USER_PROFILE (the user who triggered the notification, if applicable)
- `type`: Classification of the notification (payment_success, event_invite, etc.)
- `title` and `message`: The rendered notification content
- `reference_type` and `reference_id`: Links to the related business object (e.g., Event, PaymentOrder)
- `metadata`: JSON field for additional context data needed by the mobile app
- `is_read`: Tracks whether the user has viewed the notification

**Important**: Notifications are only for normal users (USER_PROFILE), never for admin users (AUTH_USER).

### UserDevice
Maps user profiles to their registered push notification devices. Enables one user to receive notifications on multiple devices.

**Key Fields:**
- `user_profile`: Links to the USER_PROFILE owning this device
- `onesignal_player_id`: The unique identifier from OneSignal for this device
- `platform`: Device platform (iOS or Android)
- `is_active`: Whether this device is currently active (false if player ID becomes invalid)
- `last_seen_at`: Timestamp of when this device was last registered/updated

**Lifecycle:**
- Device is registered when app calls the registration endpoint
- Device is automatically deactivated if OneSignal reports the player ID as invalid
- Old devices are preserved (not deleted) for audit purposes, just marked inactive
- One user can have multiple active devices simultaneously

---

## Notification Templates (IDEA-1)

All transactional notifications use centralized templates defined in the template registry. This ensures consistency, makes updates controlled, and prevents message drift across the platform.

### Template Structure

Each template defines:
- **Title Template**: The notification title with placeholders (e.g., "Booking Confirmed!")
- **Body Template**: The notification message with placeholders (e.g., "Your spot at {{event_name}} is locked.")
- **Target Screen**: The mobile app screen to navigate to when notification is tapped
- **Notification Type**: Categorizes the notification (payment_success, event_invite, etc.)
- **Required Parameters**: List of parameters that must be provided when rendering

### Template Rendering

When a notification is triggered, the system:
1. Looks up the template by its enum key
2. Validates that all required parameters are provided
3. Replaces placeholders ({{param_name}}) with actual values
4. Verifies no unreplaced placeholders remain
5. Returns the rendered title, body, target screen, and type

If any step fails (missing parameters, invalid template, unreplaced placeholders), the process fails immediately with a clear error message. There are no silent fallbacks or default values.

### Template Change Policy

Templates are designed to be stable and rarely change. Changes must:
- Go through product review
- Be tested in QA
- Be limited to once per month maximum
- Only happen for critical bugs or significant product requirements

This policy ensures notification copy doesn't change unexpectedly and maintains user trust.

---

## Notification Types

The system supports several categories of transactional notifications:

### Payment & Booking Notifications
- **Booking Confirmed**: Sent when a user successfully books tickets for an event
- **Payment Success**: Confirmation that a payment has been processed successfully
- **Payment Failed**: Alert when a payment attempt fails and needs retry

### Event Notifications
- **Event Live**: Notifies users when an event matching their interests is published
- **Event Cancelled**: Alerts attendees when an event is cancelled
- **Event Created**: Confirmation to hosts that their event was successfully created

### Request & Invite Notifications
- **Event Invite**: Notification to a user when they receive a direct invitation to an event
- **Invite Accepted**: Notification to host when an invited user accepts the invitation
- **Invite Declined**: Notification to host when an invited user declines
- **Request Approved**: Notification to requester when their event join request is approved
- **Request Declined**: Notification to requester when their event join request is declined
- **New Join Request**: Notification to host when a new user requests to join their event

### Attendance & Check-in
- **Ticket Confirmed**: Confirmation that an attendance record has been created and ticket is ready
- **Check-in Started**: Notification to host when an event starts and check-in should begin

### System Notifications
- **Profile Completed**: Confirmation when a user completes their profile setup

---

## Integration Points

### Events Module
The Events module triggers notifications for:
- Event publication (notifies users matching event interests)
- Event cancellation (notifies all paid attendees)
- Event creation confirmation (notifies host)
- Request approval/decline (notifies requester)
- New request received (notifies host)
- Invite sent (notifies invited user)
- Invite accepted/declined (notifies host)

Notifications are sent through Django signals and service methods, always using the dispatcher service.

### Payments Module
The Payments module triggers notifications for:
- Payment completion (booking success notification)
- Payment failure (requires retry notification)

Notifications are sent through Django signals when payment status changes, using the dispatcher service with appropriate templates.

### Users Module
The Users module triggers notifications for:
- Profile completion confirmation

Notifications are sent through Django signals when profile completion status changes.

---

## Notification Preferences

The system supports user preferences for different notification types. Currently, all transactional notifications are enabled by default, and marketing notifications are disabled.

**Current Behavior:**
- Transactional notifications (payments, events, requests, etc.): Always enabled
- Marketing notifications: Disabled (out of scope)

**Future Expansion:**
The preference service is designed to support per-user, per-type preferences without requiring refactoring. When preferences are expanded, users will be able to opt in or out of specific notification types.

**Important**: Even if a user has disabled push notifications for a type, the notification record is still saved in the database. Preferences only affect push delivery, not the in-app notification inbox.

---

## Device Registration Flow

### Registration Process
1. Mobile app initializes OneSignal SDK
2. OneSignal SDK generates or retrieves player ID for the device
3. App calls backend registration endpoint with player ID and platform
4. Backend validates user authentication and profile existence
5. Backend creates or updates UserDevice record
6. Device is marked as active and last_seen_at is updated

### Update Process
If the same player ID is registered again (e.g., user reinstalls app or updates app), the existing device record is updated rather than creating a duplicate. The device is reactivated if it was previously deactivated, and the last_seen_at timestamp is refreshed.

### Deactivation Process
Devices are deactivated (not deleted) when:
- OneSignal reports the player ID as invalid (app uninstalled, device reset, etc.)
- User explicitly unregisters the device via API
- The system detects invalid player IDs from OneSignal API responses

Deactivated devices remain in the database for audit purposes but are excluded from notification delivery.

---

## Error Handling & Resilience

### Push Notification Failures
If push notification delivery fails (OneSignal API errors, network issues, invalid devices), the error is logged but never raises exceptions. The notification record is still saved, and business logic continues normally.

### Template Rendering Failures
If template rendering fails (missing parameters, invalid template key), the error is logged and returned in the result dictionary. The notification record is still attempted to be saved with error details, ensuring the failure is tracked.

### Invalid Device Handling
When OneSignal reports invalid player IDs, those devices are automatically deactivated. This prevents future delivery attempts to invalid devices and keeps the device registry clean.

### Graceful Degradation
The system is designed to never block business operations. If the entire notification system is unavailable, core business logic (payments, event creation, etc.) continues to function normally. Notifications simply won't be sent, but all operations complete successfully.

---

## Performance Considerations

### Database Queries
- Device lookups use indexed queries on (user_profile, is_active) for fast retrieval
- Notification records use multiple indexes for efficient filtering (by recipient, type, read status, etc.)
- De-duplication of player IDs happens in memory to avoid duplicate database queries

### Push Delivery
- Push notifications are sent asynchronously (non-blocking)
- Multiple devices for the same user are batched into a single OneSignal API call
- OneSignal handles rate limiting and delivery retries on their end

### Scalability
- The system can handle thousands of notifications per minute
- Device registry supports unlimited devices per user
- Notification records are designed for high write throughput
- Indexes ensure queries remain fast as data grows

---

## Security Considerations

### User Isolation
- Users can only register devices for their own profile
- Admin users (AUTH_USER) cannot register devices
- Device deactivation endpoints validate device ownership
- Notifications are only sent to USER_PROFILE, never AUTH_USER

### Authentication
- All device registration endpoints require JWT authentication
- Only authenticated users can register or manage their devices
- Device management operations are restricted to device owners

### Data Privacy
- Player IDs are stored securely in the database
- Invalid player IDs are deactivated but not deleted (audit trail)
- Notification records are linked to user profiles with proper access controls

---

## Future Enhancements

### Scheduled Notifications (Reminders)
The system includes stub services for time-based notifications (event reminders, check-in alerts, payout reminders). These are placeholders for future scheduler integration (Celery, cron jobs, etc.) and will trigger notifications based on time events rather than immediate business events.

### Notification Preferences UI
Future work will include user-facing preference management, allowing users to customize which notification types they receive via push.

### Notification History & Analytics
Future enhancements may include analytics on notification delivery rates, user engagement, and notification effectiveness.

### Multi-Channel Delivery
Currently, the system focuses on push notifications and in-app notifications. Future expansion may include email and SMS delivery channels, all orchestrated through the same dispatcher service.

---

## Developer Guidelines

### Triggering Notifications
Always use the dispatcher service to send notifications. Never call OneSignal directly or create Notification records manually. Use templates from the template registry - never hardcode notification messages.

### Adding New Notification Types
1. Add the notification type to the template registry with a new enum key
2. Define the template with title, body, target screen, type, and required parameters
3. Use the template when triggering notifications in business logic
4. Update this documentation

### Testing Notifications
- Test with both active and inactive devices
- Test with missing parameters (should fail loudly)
- Test with notification preferences disabled (should skip push, save record)
- Test with no registered devices (should skip push, save record)
- Verify notification records are always created regardless of push success

### Debugging
- Check notification records in the database to see delivery attempts
- Check UserDevice records to see registered devices
- Check OneSignal dashboard for push delivery status
- Review logs for template rendering errors or dispatcher failures

---

## Related Documentation

- **Database ERD**: See `docs/erd_doc_fixed.md` for complete database schema
- **API Endpoints**: See `api/routers/notifications.py` for device registration endpoints
- **Integration Guide**: See other module documentation for how they integrate with notifications
- **OneSignal Setup**: Requires ONESIGNAL_APP_ID and ONESIGNAL_REST_API_KEY environment variables
