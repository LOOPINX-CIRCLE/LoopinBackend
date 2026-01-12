# Loopin Backend - Complete Database ERD Documentation

**Production-Ready Event Hosting Platform Database Schema**

This document provides a comprehensive, self-explanatory Entity Relationship Diagram (ERD) of the Loopin backend database. All tables, fields, relationships, and business logic are documented to reflect the current implementation.

```mermaid
%%{init: {
  'theme': 'base',
  'themeVariables': {
    /* Canvas - all uniform white */
    'background': '#ffffff',
    'mainBkg': '#ffffff',
    'secondBkg': '#ffffff',
    'tertiaryBkg': '#ffffff',

    /* Table rows - ALL same light color (NO striping) */
    'primaryColor': '#ffffff',
    'primaryBorderColor': '#1e3a8a',
    'primaryTextColor': '#0f172a',

    /* Force all alternate row colors to white (prevent striping) */
    'secondaryColor': '#ffffff',
    'tertiaryColor': '#ffffff',
    'secondaryTextColor': '#0f172a',
    'tertiaryTextColor': '#0f172a',

    /* Lines & text */
    'lineColor': '#334155',
    'textColor': '#0f172a',

    /* Typography */
    'fontFamily': 'Inter, Arial, sans-serif',
    'fontSize': '14px'
  }
}}%%
erDiagram
    %% ==================== RELATIONSHIPS ====================
    
    %% Users Module Relationships
    AUTH_USER ||--o| USER_PROFILE : "has profile (optional, 1-to-1)"
    USER_PROFILE }o--o{ EVENT_INTEREST : "has interests (M-to-M)"
    USER_PROFILE ||--o{ USER_PHONE_OTP : "uses for authentication (by phone number)"
    
    %% Events Module Relationships
    USER_PROFILE ||--o{ EVENT : "hosts events"
    VENUE ||--o{ EVENT : "hosts events"
    EVENT }o--o{ EVENT_INTEREST : "categorized by (M-to-M)"
    EVENT ||--o{ EVENT_REQUEST : "receives requests"
    EVENT ||--o{ EVENT_INVITE : "sends invites"
    EVENT ||--o{ EVENT_ATTENDEE : "has attendees"
    EVENT ||--o{ CAPACITY_RESERVATION : "has reservations"
    EVENT ||--o{ EVENT_IMAGE : "has images"
    USER_PROFILE ||--o{ EVENT_REQUEST : "requests events"
    USER_PROFILE ||--o{ EVENT_INVITE : "sends invites (host)"
    USER_PROFILE ||--o{ EVENT_INVITE : "receives invites (invited user)"
    USER_PROFILE ||--o{ EVENT_ATTENDEE : "attends events"
    USER_PROFILE ||--o{ CAPACITY_RESERVATION : "reserves capacity"
    EVENT_REQUEST ||--o| EVENT_ATTENDEE : "converts to"
    
    %% Attendance Module Relationships
    EVENT ||--o{ ATTENDANCE_RECORD : "has attendance"
    USER_PROFILE ||--o{ ATTENDANCE_RECORD : "has attendance"
    ATTENDANCE_RECORD ||--|| TICKET_SECRET : "has secret"
    
    %% Core Configuration Relationships
    AUTH_USER ||--o{ PLATFORM_FEE_CONFIG : "updated by"
    
    %% Payment Module Relationships
    USER_PROFILE ||--o{ PAYMENT_ORDER : "places orders"
    EVENT ||--o{ PAYMENT_ORDER : "linked to"
    PAYMENT_ORDER ||--o{ PAYMENT_TRANSACTION : "has transactions"
    PAYMENT_ORDER ||--o{ PAYMENT_WEBHOOK : "receives webhooks"
    
    %% Payout Module Relationships
    USER_PROFILE ||--o{ BANK_ACCOUNT : "owns bank accounts (host)"
    BANK_ACCOUNT ||--o{ HOST_PAYOUT_REQUEST : "receives payouts"
    EVENT ||--o{ HOST_PAYOUT_REQUEST : "has payout requests"
    
    %% Host Lead Module Relationships
    AUTH_USER ||--o{ HOST_LEAD_WHATSAPP_MESSAGE : "sends messages"
    HOST_LEAD ||--o{ HOST_LEAD_WHATSAPP_MESSAGE : "receives messages"
    HOST_LEAD_WHATSAPP_TEMPLATE ||--o{ HOST_LEAD_WHATSAPP_MESSAGE : "used by"
    
    %% Notification & Audit Relationships
    USER_PROFILE ||--o{ USER_DEVICE : "has devices"
    USER_PROFILE ||--o{ NOTIFICATION : "receives notifications"
    USER_PROFILE ||--o{ NOTIFICATION : "sends notifications"
    AUTH_USER ||--o{ CAMPAIGN : "creates campaigns"
    AUTH_USER ||--o{ CAMPAIGN : "sends campaigns"
    AUTH_USER ||--o{ CAMPAIGN : "cancels campaigns"
    AUTH_USER ||--o{ NOTIFICATION_TEMPLATE : "creates templates"
    NOTIFICATION_TEMPLATE ||--o{ TEMPLATE_VARIABLE_HINT : "has variable hints"
    NOTIFICATION_TEMPLATE ||--o{ CAMPAIGN : "used by campaigns"
    CAMPAIGN ||--o{ NOTIFICATION : "triggers notifications"
    CAMPAIGN ||--o{ CAMPAIGN_EXECUTION : "has executions"
    NOTIFICATION ||--o| CAMPAIGN_EXECUTION : "tracked by"
    USER_PROFILE ||--o{ CAMPAIGN_EXECUTION : "receives campaign notifications"
    AUTH_USER ||--o{ AUDIT_LOG : "generates logs"
    AUTH_USER ||--o{ AUDIT_LOG_SUMMARY : "has summaries"

    %% ==================== TABLE DEFINITIONS ====================

    AUTH_USER {
        BIGINT id PK "Primary key, auto-increment"
        UUID uuid "Public unique identifier"
        STRING username "Phone number for authentication"
        STRING email "User email address"
        STRING password "Hashed password"
        STRING first_name "First name"
        STRING last_name "Last name"
        BOOLEAN is_active "Account active status"
        BOOLEAN is_staff "Staff access"
        BOOLEAN is_superuser "Admin access"
        DATETIME date_joined "Account creation timestamp"
        DATETIME last_login "Last login timestamp"
        DATETIME created_at "Record creation"
        DATETIME updated_at "Last update"
    }

    USER_PROFILE {
        BIGINT id PK "Primary key"
        BIGINT user_id FK "One-to-One with AUTH_USER"
        UUID uuid "Public unique identifier"
        STRING name "Full name (2-100 chars)"
        STRING phone_number "Contact number"
        TEXT bio "User biography (max 500)"
        STRING location "City/location (max 100)"
        DATE birth_date "Date of birth"
        STRING gender "male|female|other|prefer_not_to_say"
        JSONB profile_pictures "Array of 1-6 image URLs"
        JSONB metadata "Additional user data"
        BOOLEAN is_verified "Phone verified status"
        BOOLEAN is_active "Profile active (mirrors AUTH_USER.is_active)"
        DATETIME waitlist_started_at "When user first entered waitlist (nullable)"
        DATETIME waitlist_promote_at "Scheduled promotion time (1.10-1.35h window, nullable)"
        DATETIME created_at "Record creation"
        DATETIME updated_at "Last update"
    }

    USER_PHONE_OTP {
        BIGINT id PK "Primary key"
        STRING phone_number "Phone for OTP (links to USER_PROFILE.phone_number, used by normal users)"
        STRING otp_code "4-digit OTP"
        STRING otp_type "signup|login|password_reset|phone_verification|transaction"
        STRING status "pending|verified|expired|failed"
        BOOLEAN is_verified "OTP verified flag"
        INT attempts "Verification attempts"
        DATETIME expires_at "OTP expiration"
        DATETIME created_at "Creation time"
        DATETIME updated_at "Last update"
    }

    USER_DEVICE {
        BIGINT id PK "Primary key"
        BIGINT user_profile_id FK "User profile (USER_PROFILE)"
        STRING onesignal_player_id "OneSignal player ID (unique, indexed)"
        STRING platform "ios|android"
        BOOLEAN is_active "Device active status (indexed)"
        DATETIME last_seen_at "Last seen timestamp (nullable)"
        DATETIME created_at "Creation time"
        DATETIME updated_at "Last update"
    }
    
    BANK_ACCOUNT {
        BIGINT id PK "Primary key"
        UUID uuid "Public unique identifier"
        BIGINT host_id FK "Host user profile (USER_PROFILE)"
        STRING bank_name "Bank name (max 100)"
        STRING account_number "Account number (max 30)"
        STRING ifsc_code "IFSC code (11 chars)"
        STRING account_holder_name "Account holder name (max 100)"
        BOOLEAN is_primary "Primary account flag"
        BOOLEAN is_verified "Verification status"
        BOOLEAN is_active "Active status"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }
    
    HOST_PAYOUT_REQUEST {
        BIGINT id PK "Primary key"
        UUID uuid "Public unique identifier"
        BIGINT bank_account_id FK "Bank account (BANK_ACCOUNT)"
        BIGINT event_id FK "Event (EVENT)"
        STRING host_name "Host name snapshot"
        STRING event_name "Event name snapshot"
        DATETIME event_date "Event date snapshot"
        STRING event_location "Event location snapshot"
        INT total_capacity "Event capacity snapshot"
        DECIMAL base_ticket_fare "Base ticket price"
        DECIMAL final_ticket_fare "Final price (base + 10% fee)"
        INT total_tickets_sold "Tickets sold snapshot"
        JSONB attendees_details "Attendee names and contacts"
        DECIMAL platform_fee_amount "Total platform fee"
        DECIMAL final_earning "Host earnings (base × tickets)"
        STRING status "pending|approved|processing|completed|rejected|cancelled"
        DATETIME processed_at "Processing timestamp"
        STRING transaction_reference "Bank transaction ID"
        TEXT rejection_reason "Rejection details"
        TEXT notes "Internal notes"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    HOST_LEAD {
        BIGINT id PK "Primary key"
        STRING first_name "First name (max 100)"
        STRING last_name "Last name (max 100)"
        STRING phone_number "Phone number (unique, max 20)"
        TEXT message "Optional message from potential host"
        BOOLEAN is_contacted "Whether lead has been contacted"
        BOOLEAN is_converted "Whether lead became a host"
        TEXT notes "Internal notes about the lead"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    HOST_LEAD_WHATSAPP_TEMPLATE {
        BIGINT id PK "Primary key"
        STRING name "Template identifier (unique, max 120)"
        TEXT message "Pre-approved message copy"
    }

    HOST_LEAD_WHATSAPP_MESSAGE {
        BIGINT id PK "Primary key"
        BIGINT lead_id FK "Host lead recipient (HOST_LEAD)"
        BIGINT template_id FK "Template used (HOST_LEAD_WHATSAPP_TEMPLATE, nullable)"
        BIGINT sent_by_id FK "Admin user who sent (AUTH_USER, nullable)"
        STRING content_sid "Twilio Content Template SID (max 80)"
        JSONB variables "Content variables for Twilio"
        TEXT body_variable "Final text for variable {{2}}"
        STRING status "queued|sent|delivered|undelivered|failed|test-mode"
        STRING twilio_sid "Twilio message SID (max 64, nullable)"
        STRING error_code "Twilio error code (max 50, nullable)"
        TEXT error_message "Human-readable error message (nullable)"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    EVENT_INTEREST {
        BIGINT id PK "Primary key"
        STRING name "Interest name (unique, max 100)"
        STRING slug "URL-friendly slug (unique, auto-generated)"
        BOOLEAN is_active "Interest active (default: true)"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    VENUE {
        BIGINT id PK "Primary key"
        UUID uuid "Public unique identifier"
        STRING name "Venue name (max 150)"
        TEXT address "Full address"
        STRING city "City name (max 100)"
        STRING venue_type "indoor|outdoor|virtual|hybrid"
        INT capacity "Max capacity (0=unlimited)"
        DECIMAL latitude "Latitude (-90 to 90)"
        DECIMAL longitude "Longitude (-180 to 180)"
        JSONB metadata "Extra info (accessibility, hints)"
        BOOLEAN is_active "Venue active"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    EVENT {
        BIGINT id PK "Primary key"
        BIGINT host_id FK "Event host (USER_PROFILE)"
        BIGINT venue_id FK "Linked venue (nullable)"
        UUID uuid "Public unique identifier"
        STRING slug "URL-friendly slug"
        STRING title "Event title (3-200 chars)"
        TEXT description "Event details (min 10 chars)"
        STRING venue_text "Custom venue text (max 255)"
        DATETIME start_time "Event start"
        DATETIME end_time "Event end"
        INT max_capacity "Max attendees (0=unlimited)"
        INT going_count "Confirmed attendees"
        INT requests_count "Pending requests"
        BOOLEAN is_paid "Requires payment"
        DECIMAL ticket_price "Ticket price (0.00)"
        BOOLEAN allow_plus_one "Allow guests"
        STRING gst_number "Host GST number (max 50)"
        STRING allowed_genders "all|male|female|non_binary"
        JSONB cover_images "Array of 1-3 image URLs"
        STRING status "draft|published|cancelled|completed|postponed"
        BOOLEAN is_public "Public visibility"
        BOOLEAN is_active "Event active"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    EVENT_INTEREST_MAP {
        BIGINT id PK "Primary key"
        BIGINT event_id FK "Event"
        BIGINT eventinterest_id FK "Interest"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    EVENT_IMAGE {
        BIGINT id PK "Primary key"
        BIGINT event_id FK "Event"
        TEXT image_url "Image URL"
        INT position "Display order"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    EVENT_REQUEST {
        BIGINT id PK "Primary key"
        BIGINT event_id FK "Requested event"
        BIGINT requester_id FK "User profile requesting (USER_PROFILE)"
        UUID uuid "Public unique identifier"
        STRING status "pending|accepted|declined|cancelled|expired"
        TEXT message "Request message"
        TEXT host_message "Host response"
        INT seats_requested "Number of seats"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    EVENT_INVITE {
        BIGINT id PK "Primary key"
        BIGINT event_id FK "Event"
        BIGINT host_id FK "Inviting host (nullable)"
        BIGINT invited_user_id FK "Invited user"
        UUID uuid "Public unique identifier"
        STRING invite_type "direct|share_link"
        STRING status "pending|accepted|declined|expired"
        TEXT message "Invite message"
        DATETIME expires_at "Invite expiration"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    EVENT_ATTENDEE {
        BIGINT id PK "Primary key"
        BIGINT event_id FK "Event"
        BIGINT user_id FK "Attending user (UserProfile)"
        BIGINT request_id FK "Originating request (nullable)"
        BIGINT invite_id FK "Originating invite (nullable)"
        BIGINT payment_order_id FK "Payment order that fulfilled this (nullable)"
        UUID uuid "Public unique identifier"
        STRING ticket_type "standard|vip|early_bird|premium|general|group|couple|family|student|senior_citizen|disabled|other"
        INT seats "Number of seats"
        BOOLEAN is_paid "Payment status"
        DECIMAL price_paid "Amount paid"
        DECIMAL platform_fee "Platform fee"
        STRING status "going|not_going|maybe|checked_in|cancelled"
        DATETIME checked_in_at "Check-in time"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    CAPACITY_RESERVATION {
        BIGINT id PK "Primary key"
        BIGINT event_id FK "Event"
        BIGINT user_id FK "Reserving user profile (USER_PROFILE)"
        UUID reservation_key "Unique reservation token"
        INT seats_reserved "Seats held"
        BOOLEAN consumed "Reservation used"
        DATETIME expires_at "Reservation expiration"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    ATTENDANCE_RECORD {
        BIGINT id PK "Primary key"
        BIGINT event_id FK "Event"
        BIGINT user_id FK "Attending user profile (USER_PROFILE)"
        BIGINT payment_order_id FK "Payment order that fulfilled this (nullable)"
        STRING status "going|not_going|maybe|checked_in|cancelled"
        STRING payment_status "unpaid|paid|refunded"
        STRING ticket_secret "Unique ticket code"
        INT seats "Number of seats"
        DATETIME checked_in_at "Check-in timestamp"
        DATETIME checked_out_at "Check-out timestamp"
        TEXT notes "Additional notes"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    TICKET_SECRET {
        BIGINT id PK "Primary key"
        BIGINT attendance_record_id FK "Attendance record"
        TEXT secret_hash "Hashed secret"
        TEXT secret_salt "Hashing salt"
        BOOLEAN is_redeemed "Ticket used"
        DATETIME redeemed_at "Redemption time"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    PAYMENT_ORDER {
        BIGINT id PK "Primary key"
        BIGINT event_id FK "Event"
        BIGINT user_id FK "Paying user (UserProfile)"
        UUID uuid "Public unique identifier"
        STRING order_reference "Order reference ID"
        STRING order_id "Unique order ID"
        DECIMAL amount "Total amount (base + platform fee)"
        STRING currency "INR|USD|EUR|GBP"
        INT seats_count "Number of seats/tickets (default: 1)"
        DECIMAL base_price_per_seat "Base ticket price at payment time (immutable)"
        DECIMAL platform_fee_percentage "Platform fee % at payment time (immutable)"
        DECIMAL platform_fee_amount "Total platform fee at payment time (immutable)"
        DECIMAL host_earning_per_seat "Host earning per seat at payment time (immutable)"
        STRING status "created|pending|paid|completed|failed|cancelled|refunded|unpaid"
        STRING payment_provider "razorpay|stripe|paypal|paytm|phonepe|gpay|payu|cash|bank_transfer"
        STRING provider_payment_id "Provider payment ID"
        JSONB provider_response "Provider response"
        STRING payment_method "Payment method"
        STRING transaction_id "Transaction ID"
        TEXT failure_reason "Failure details"
        BIGINT parent_order_id FK "Parent order if retry attempt (nullable)"
        BOOLEAN is_final "True if final successful payment (not retry)"
        INDEX unique_final_per_user_event "(user_id, event_id) WHERE is_final = true (UNIQUE)"
        DECIMAL refund_amount "Refund amount"
        TEXT refund_reason "Refund reason"
        DATETIME refunded_at "Refund time"
        DATETIME expires_at "Order expiration"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    PAYMENT_TRANSACTION {
        BIGINT id PK "Primary key"
        BIGINT payment_order_id FK "Parent order"
        STRING transaction_type "payment|refund|chargeback"
        DECIMAL amount "Transaction amount"
        STRING provider_transaction_id "Provider ID"
        STRING status "pending|completed|failed"
        JSONB provider_response "Provider data"
        TEXT failure_reason "Failure details"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    PAYMENT_WEBHOOK {
        BIGINT id PK "Primary key"
        BIGINT payment_order_id FK "Parent order"
        STRING webhook_type "Webhook type"
        JSONB payload "Webhook data"
        STRING signature "Security signature"
        BOOLEAN processed "Processing status"
        TEXT processing_error "Error details"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    NOTIFICATION {
        BIGINT id PK "Primary key"
        BIGINT recipient_id FK "Receiving user (USER_PROFILE, normal user)"
        BIGINT sender_id FK "Sending user (USER_PROFILE, normal user, nullable)"
        BIGINT campaign_id FK "Parent campaign (CAMPAIGN, nullable)"
        UUID uuid "Public unique identifier"
        STRING type "event_request|event_invite|event_update|event_cancelled|payment_success|payment_failed|reminder|system|promotional"
        STRING title "Notification title (max 200)"
        TEXT message "Notification content"
        STRING reference_type "Related model type"
        BIGINT reference_id "Related object ID"
        BOOLEAN is_read "Read status"
        JSONB metadata "Additional data"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    NOTIFICATION_TEMPLATE {
        BIGINT id PK "Primary key"
        UUID uuid "Public unique identifier"
        STRING name "Template name (unique, max 255)"
        STRING key "Unique template key/slug (indexed, unique)"
        STRING title "Notification title with {{variable}} placeholders (max 200)"
        TEXT body "Notification message with {{variable}} placeholders"
        STRING target_screen "Mobile app screen to navigate to (default: home, max 100)"
        STRING notification_type "Type of notification (from NOTIFICATION_TYPE_CHOICES, default: system)"
        INT version "Template version number (default: 1, indexed)"
        BOOLEAN is_active "Whether template is available for use (default: true, indexed)"
        BIGINT created_by_id FK "Admin user who created (AUTH_USER, nullable)"
        DATETIME created_at "Creation (indexed)"
        DATETIME updated_at "Update"
    }

    TEMPLATE_VARIABLE_HINT {
        BIGINT id PK "Primary key"
        BIGINT template_id FK "Parent template (NOTIFICATION_TEMPLATE)"
        STRING variable_name "Variable name without braces (max 100)"
        TEXT help_text "Help text explaining what this variable is for"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    CAMPAIGN {
        BIGINT id PK "Primary key"
        UUID uuid "Public unique identifier"
        STRING name "Campaign name (max 255)"
        TEXT description "Campaign description (optional)"
        BIGINT template_id FK "Notification template (NOTIFICATION_TEMPLATE, nullable, indexed)"
        INT template_version "Immutable template version snapshot (nullable, indexed)"
        JSONB template_variables "Variable values for template rendering (auto-populated from UI)"
        JSONB audience_rules "Audience selection rules (auto-generated from UI fields)"
        STRING status "draft|previewed|scheduled|sending|sent|cancelled|failed (indexed)"
        INT preview_count "Number of users matching rules (nullable)"
        DATETIME preview_computed_at "When preview was computed (nullable)"
        DATETIME sent_at "When campaign was sent (nullable, indexed)"
        BIGINT sent_by_id FK "Admin user who sent (AUTH_USER, nullable)"
        INT total_sent "Notifications successfully sent (default: 0)"
        INT total_failed "Notifications failed (default: 0)"
        JSONB execution_metadata "Execution errors, warnings, batch info"
        BIGINT created_by_id FK "Admin user who created (AUTH_USER, nullable)"
        DATETIME cancelled_at "When cancelled (nullable)"
        BIGINT cancelled_by_id FK "Admin user who cancelled (AUTH_USER, nullable)"
        TEXT cancellation_reason "Reason for cancellation (optional)"
        DATETIME created_at "Creation (indexed)"
        DATETIME updated_at "Update"
    }

    CAMPAIGN_EXECUTION {
        BIGINT id PK "Primary key"
        BIGINT campaign_id FK "Parent campaign (CAMPAIGN)"
        BIGINT notification_id FK "Notification record (NOTIFICATION)"
        BIGINT user_profile_id FK "User who received (USER_PROFILE)"
        BOOLEAN sent_successfully "Delivery success status (indexed)"
        TEXT error_message "Error message if failed"
        JSONB onesignal_response "Raw OneSignal API response"
        DATETIME delivered_at "When delivered (nullable, indexed)"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    AUDIT_LOG {
        BIGINT id PK "Primary key"
        BIGINT actor_user_id FK "User who acted (nullable)"
        BIGINT user_id FK "Legacy user FK (nullable)"
        STRING action "create|update|delete|login|logout|password_change|profile_update"
        STRING object_type "Model type"
        BIGINT object_id "Object ID"
        STRING object_uuid "Object UUID"
        JSONB payload "Snapshot of changes"
        JSONB metadata "Legacy metadata"
        JSONB old_values "Legacy old values"
        JSONB new_values "Legacy new values"
        INET ip_address "User IP"
        TEXT user_agent "Browser info"
        STRING session_key "Session ID"
        STRING severity "low|medium|high|critical"
        BOOLEAN is_successful "Action success"
        TEXT error_message "Error details"
        DATETIME created_at "Log time"
        DATETIME updated_at "Update"
    }

    AUDIT_LOG_SUMMARY {
        BIGINT id PK "Primary key"
        DATE date "Summary date"
        BIGINT user_id FK "User (nullable)"
        STRING action "Action type"
        INT count "Total actions"
        INT successful_count "Successful"
        INT failed_count "Failed"
        DATETIME created_at "Creation"
        DATETIME updated_at "Update"
    }

    PLATFORM_FEE_CONFIG {
        INT id PK "Singleton identifier (always 1)"
        DECIMAL fee_percentage "Platform fee % (0.00-100.00, default: 10.00)"
        BOOLEAN is_active "Configuration active status"
        TEXT description "Optional description/notes"
        BIGINT updated_by FK "Admin who last updated (nullable)"
        DATETIME created_at "Creation"
        DATETIME updated_at "Last update"
    }

    %% Apply domain-level color discipline (pure white fills, strong borders, NO striping)
    %% All fills are #ffffff to prevent ANY row striping within tables
    classDef userTables fill:#ffffff,stroke:#1e3a8a,stroke-width:2px,color:#0f172a
    classDef eventTables fill:#ffffff,stroke:#155e75,stroke-width:2px,color:#0f172a
    classDef paymentTables fill:#ffffff,stroke:#9a3412,stroke-width:2px,color:#0f172a
    classDef attendanceTables fill:#ffffff,stroke:#a16207,stroke-width:2px,color:#0f172a
    classDef auditTables fill:#ffffff,stroke:#6b21a8,stroke-width:2px,color:#0f172a
    classDef notificationTables fill:#ffffff,stroke:#9f1239,stroke-width:2px,color:#020617
    classDef coreTables fill:#ffffff,stroke:#334155,stroke-width:2px,color:#020617

    %% Apply domain grouping
    class AUTH_USER,USER_PROFILE,USER_PHONE_OTP,BANK_ACCOUNT,HOST_LEAD,HOST_LEAD_WHATSAPP_TEMPLATE,HOST_LEAD_WHATSAPP_MESSAGE userTables
    class EVENT,EVENT_REQUEST,EVENT_INVITE,EVENT_ATTENDEE,VENUE,EVENT_INTEREST,EVENT_INTEREST_MAP,EVENT_IMAGE,CAPACITY_RESERVATION,HOST_PAYOUT_REQUEST eventTables
    class ATTENDANCE_RECORD,TICKET_SECRET attendanceTables
    class PAYMENT_ORDER,PAYMENT_TRANSACTION,PAYMENT_WEBHOOK paymentTables
    class USER_DEVICE,NOTIFICATION,NOTIFICATION_TEMPLATE,TEMPLATE_VARIABLE_HINT,CAMPAIGN,CAMPAIGN_EXECUTION notificationTables
    class AUDIT_LOG,AUDIT_LOG_SUMMARY auditTables
    class PLATFORM_FEE_CONFIG coreTables
```

---
## 📚 **Complete Database Schema Documentation**

### **Overview**

The Loopin Backend database is designed for a production-ready event hosting platform with:
- **Phone-based authentication** with OTP verification
- **Comprehensive event management** with hosting, requests, invites, and attendance
- **Multi-provider payment system** with transaction tracking
- **Advanced attendance management** with check-in/check-out and secure ticketing
- **Host payout management** with bank account management and financial calculations
- **Configurable platform fee system** with admin-controlled fee percentage
- **Automatic waitlist promotion** with 1.10-1.35 hour randomized window
- **Complete audit trail** for security and compliance
- **Push notification system** with device registration and OneSignal integration
- **Flexible in-app notification system** for user engagement
- **Admin-driven notification campaigns** with rule-based audience selection
- **Host lead management system** with WhatsApp integration for lead communication

**Database:** PostgreSQL 15+  
**ORM:** Django ORM  
**API:** FastAPI with ASGI

---

## **1. USERS MODULE** 🎫

### **1.1 AUTH_USER** (Django Built-in) 🔐
**Purpose:** Core authentication and authorization for **Internal Platform Operators Only**

**🔒 CRITICAL IDENTITY SEPARATION:**

**AUTH_USER = Internal Platform Operators**
- Platform administrators (`is_staff=True`, `is_superuser=True`)
- Finance/Ops team members
- Internal staff (CEO, CFO, Admins)
- **NEVER** used for customer actions (payments, attendance, hosting)

**USER_PROFILE = External Platform Customers**
- Hosts (event creators)
- Attendees (event participants)
- All customer-facing actions belong here
- Payments, attendance, events, tickets — ALL customer data

**⚠️ Strict Enforcement Rules:**

1. **Payments MUST belong to USER_PROFILE only**
   - `PAYMENT_ORDER.user_id` → `USER_PROFILE` ✅
   - `EVENT_ATTENDEE.user_id` → `USER_PROFILE` ✅
   - `ATTENDANCE_RECORD.user_id` → `USER_PROFILE` ✅
   - ❌ An AUTH_USER must NEVER pay, attend, host, or check in

2. **Admin actions must never impersonate USER_PROFILE**
   - Admin (AUTH_USER) can: View, Audit, Approve payouts, Configure fees, Cancel events
   - Admin must NOT: Create PAYMENT_ORDER, Create EVENT_ATTENDEE, Trigger check-ins, Generate ticket secrets
   - **Service-Level Guards**: Explicit checks in `PaymentFlowService.create_payment_order()`, `EventService.create_event()`, `EventRequestService.create_request()`, `EventInviteService.create_invite()` prevent admin accounts from performing customer actions.

3. **Audit log records BOTH identities**
   - `AUDIT_LOG.actor_user_id` → `AUTH_USER` (who performed admin action)
   - `AUDIT_LOG.object_id` → `USER_PROFILE`-owned objects (what was acted upon)

**Relationship to USER_PROFILE:**
- Optional 1-to-1 relationship: `AUTH_USER` ↔ `USER_PROFILE`
- Not all AUTH_USER records have USER_PROFILE (admin accounts may not need one)
- Not all USER_PROFILE records need admin access (customers don't need `is_staff=True`)
- **This separation is intentional and must be enforced at service boundaries**

**Django Admin Access:**
- **Admin-level users** (`is_staff=True` or `is_superuser=True`) see:
  - ✅ **Users** (AUTH_USER) - Admin interface for managing authentication accounts
  - ✅ **Groups** - Permission groups for admin users
  - ✅ All other models (full access)

**Key Features:**
- Phone-based authentication (username = phone number)
- JWT token generation for API access
- Role-based access control:
  - `is_staff` - Django admin access
  - `is_superuser` - Full admin privileges
  - `is_active` - Account activation status
- Permission management via Groups and Permissions

**Relationships:**
- 1-to-1 → `USER_PROFILE` (optional - only created for customers, not admins)
- 1-to-many → `PLATFORM_FEE_CONFIG.updated_by` (admin configuration updates)
- 1-to-many → `AUDIT_LOG.actor_user_id` (admin actions logged)

**⚠️ AUTH_USER does NOT directly relate to customer actions:**
- Events, payments, attendance, tickets → All belong to `USER_PROFILE`
- Notifications → Belong to `USER_PROFILE` (normal users receive/send notifications)
- Phone OTP → Used by `USER_PROFILE` (normal users authenticate via phone)
- Admin actions are logged via `AUDIT_LOG`, not direct relationships

**Business Logic:**
- Username is typically the phone number (e.g., +916205829376)
- Active users can authenticate via OTP or password
- UUID provides public identifier for APIs
- Staff/superuser accounts are for **internal platform administration ONLY**
- Customer accounts link to USER_PROFILE for extended data and all customer actions
- **Never use AUTH_USER for customer-facing features** (payments, events, attendance)

**Admin Interface:**
- Custom `UserAdmin` extends Django's `BaseUserAdmin`
- Shows profile status inline (if USER_PROFILE exists)
- Displays profile completion status
- Filters by staff status, superuser status, and profile verification

---

### **1.2 USER_PROFILE** 👤
**Purpose:** Customer profile data for **External Platform Customers Only**

**🔒 CRITICAL IDENTITY SEPARATION:**

**USER_PROFILE = External Platform Customers**
- All hosts (event creators)
- All attendees (event participants)
- All customer-facing actions belong here
- **Source of truth for all customer data**

**⚠️ Customer Actions MUST use USER_PROFILE:**
- ✅ `EVENT.host_id` → `USER_PROFILE` (hosts create events)
- ✅ `PAYMENT_ORDER.user_id` → `USER_PROFILE` (customers pay)
- ✅ `EVENT_ATTENDEE.user_id` → `USER_PROFILE` (customers attend)
- ✅ `ATTENDANCE_RECORD.user_id` → `USER_PROFILE` (customers check in)
- ✅ `EVENT_REQUEST.requester_id` → `USER_PROFILE` (customers request to join)
- ✅ `BANK_ACCOUNT.host_id` → `USER_PROFILE` (hosts receive payouts)
- ✅ `CAPACITY_RESERVATION.user_id` → `USER_PROFILE` (customers reserve seats)
- ✅ `USER_DEVICE.user_profile` → `USER_PROFILE` (customers register devices for push)
- ✅ `NOTIFICATION.recipient` → `USER_PROFILE` (normal users receive notifications)
- ✅ `NOTIFICATION.sender` → `USER_PROFILE` (normal users send notifications)
- ✅ `CAMPAIGN_EXECUTION.user_profile` → `USER_PROFILE` (customers receive campaign notifications)
- ✅ `USER_PHONE_OTP` → Used by normal users (phone-based authentication)

**Never use AUTH_USER for these actions** — enforce at service boundaries.

**Relationship to AUTH_USER:**
- Optional 1-to-1 relationship: `USER_PROFILE` ↔ `AUTH_USER`
- Customer accounts link to AUTH_USER for authentication only
- All customer actions use USER_PROFILE, not AUTH_USER
- Admin accounts (AUTH_USER with `is_staff=True`) may not have USER_PROFILE

**Django Admin Access:**
- **Normal users/customers** see in admin (if they have access):
  - ✅ **User Profiles** - Customer profile management
  - ✅ **Bank Accounts** - Host bank account details
  - ✅ **Event Interests** - Event category preferences
  - ✅ **Host Leads** - Host lead generation records
  - ✅ **Host Lead WhatsApp Messages** - WhatsApp communication logs
  - ✅ **Host Lead WhatsApp Templates** - Message templates
  - ✅ **Host Payout Requests** - Payout request management
  - ✅ **Phone OTPs** - OTP verification records

**Key Features:**
- Customer-facing profile information
- Profile completion workflow
- Event interest preferences (1-5 selections)
- Profile pictures (1-6 URLs)
- Gender and personal information
- Location and bio data

**Required Fields (After Signup):**
- `name` (minimum 2 characters, letters only)
- `gender` (male/female/other/prefer_not_to_say)
- `profile_pictures` (1-6 URLs)
- `event_interests` (1-5 selections)

**Optional Fields:**
- `bio` (max 500 characters)
- `location`
- `birth_date`
- `metadata` (JSON for extensibility)

**Business Logic:**
- Profile must be completed before full app access
- Event interests enable personalized recommendations
- Phone verification required for security (`is_verified` flag)
- `uuid` used in public APIs
- One profile per AUTH_USER (1-to-1 relationship)
- Profile can exist without admin-level AUTH_USER permissions

**Validation Rules:**
- Minimum 1, maximum 6 profile pictures
- Minimum 1, maximum 5 event interests
- Name: 2-100 characters, letters only
- Phone number validation (format: +XXXXXXXXXXX)

**Waitlist Lifecycle (Automatic Promotion System):**
- New users who complete their profile for the first time are immediately placed into a **waitlist state**:
  - Django `AUTH_USER.is_active = False`
  - `USER_PROFILE.is_active = False`
  - `waitlist_started_at` set to the profile completion time
  - `waitlist_promote_at` set to a randomized timestamp between **1.10 and 1.35 hours** (70-81 minutes) in the future
- **Waitlist Promotion Window**: Random delay between 1.10-1.35 hours from profile completion
  - Minimum wait: 1.10 hours (70 minutes)
  - Maximum wait: 1.35 hours (81 minutes)
  - Each user gets a random delay within this window
- **Waitlist Access Restrictions**: While on waitlist (`is_active = false`), users can only access:
  - `GET /api/auth/profile` - View profile
  - `PUT /api/auth/profile` - Update profile
  - All other endpoints return 403 with waitlist message
- **Promotion Notification**: When promoted from waitlist, users receive a push notification welcoming them to the platform
- While `is_active = False`, all endpoints and features that depend on this flag must treat the account as **restricted/waitlisted** and deny core actions.
- **Automatic Promotion**: During normal API traffic (no Celery/cron required), the backend checks `waitlist_promote_at` and **atomically promotes** the user to active when `now >= waitlist_promote_at`:
  - `AUTH_USER.is_active = True`
  - `USER_PROFILE.is_active = True`
  - `waitlist_started_at` and `waitlist_promote_at` cleared (set to NULL)
- Clients should use the `/api/auth/profile` endpoint and read the `is_active` field to distinguish **waitlisted** vs **active** users.
- **No Admin Approval Required**: Promotion happens automatically based on scheduled time, ensuring consistent user experience.

**Admin Interface:**
- `UserProfileAdmin` - Separate admin interface for customer profiles
- Shows profile completion status, verification status
- Filters by verification, active status, gender, location
- Search by name, phone number, location, bio
- Horizontal filter for event interests selection

**Business Rules - Identity Separation:**
- All customer actions (payments, events, attendance, notifications) MUST use `USER_PROFILE`
- All customer authentication (phone OTP) is used by `USER_PROFILE` (normal users)
- `AUTH_USER` is ONLY for authentication and admin operations
- Admin actions are logged via `AUDIT_LOG` with `actor_user_id` → `AUTH_USER`
- Customer data objects link to `USER_PROFILE`, never directly to `AUTH_USER`
- This separation enables:
  - ✅ Cleaner permission logic
  - ✅ Safer admin operations
  - ✅ Easier audit trails
  - ✅ No accidental admin↔customer overlap

---

### **1.3 USER_PHONE_OTP** 📱
**Purpose:** Secure phone-based authentication for **normal users (customers)**

**⚠️ IMPORTANT:** This is used by `USER_PROFILE` (normal users), NOT admin users.

**Usage:**
- Normal users (customers) use phone OTP for signup and login
- Phone number links to `USER_PROFILE.phone_number`
- No direct ForeignKey relationship - linked via phone number
- Admin users (`AUTH_USER` with `is_staff=True`) typically don't use phone OTP

**OTP Configuration:**
- Length: **4 digits**
- Validity: **10 minutes**
- Max attempts: **3**

**OTP Types:**
- `signup` - New user registration (normal users)
- `login` - Existing user authentication (normal users)
- `password_reset` - Password recovery (normal users)
- `phone_verification` - Verify phone number (normal users)
- `transaction` - Secure transactions (normal users)

**Status Flow:**
```
pending → verified (success) OR failed|expired (failure)
```

**Security Features:**
- Single OTP per phone number
- Automatic expiration
- Attempt limiting prevents brute force
- Verified flag prevents reuse

---

### **1.4 USER_DEVICE** 📱
**Purpose:** Map user profiles to OneSignal player IDs for push notifications

**Key Features:**
- One user profile can have multiple devices (iOS, Android)
- Tracks OneSignal player IDs for push notification delivery
- Supports device deactivation (soft-delete pattern) when player IDs become invalid
- Last seen tracking for device activity monitoring

**Fields:**
- `user_profile` - Foreign key to USER_PROFILE (the device owner)
- `onesignal_player_id` - OneSignal player ID (unique, indexed, max 255 chars)
- `platform` - Device platform: `ios` or `android`
- `is_active` - Whether device is active (indexed, default: true)
  - Set to false when OneSignal returns invalid player ID
  - Allows soft-delete pattern (devices preserved for audit)
- `last_seen_at` - Last time device was used (nullable, indexed)
- `created_at` / `updated_at` - Timestamps (inherited from TimeStampedModel)

**Indexes:**
- `user_profile` + `is_active` (composite index for querying active devices per user)
- `onesignal_player_id` (unique index for fast lookup)
- `is_active` + `last_seen_at` (composite index for cleanup queries)

**Unique Constraints:**
- `(user_profile, onesignal_player_id)` - Prevents duplicate device registrations

**Business Logic:**
- Devices are registered via `/api/notifications/devices/register` endpoint
- OneSignal player IDs may rotate - old devices are deactivated, not deleted
- Only USER_PROFILE (normal users) can register devices (AUTH_USER blocked)
- Invalid player IDs detected via OneSignal API response trigger automatic deactivation
- `deactivate()` and `reactivate()` helper methods for device lifecycle management

**Use Cases:**
- Mobile apps register devices on app launch
- Push notifications sent to all active devices per user
- Device rotation handled gracefully (old devices deactivated, new ones registered)
- Device activity monitoring via last_seen_at timestamp

**Security:**
- Only USER_PROFILE (customers) can register devices
- Admin users (AUTH_USER) are blocked from device registration
- Device deactivation preserves audit trail

---

### **1.5 EVENT_INTEREST** 🎨
**Purpose:** Event categorization and personalization

**Features:**
- Master list of event categories (Music, Travel, Sports, etc.)
- Slug for URL-friendly navigation
- Many-to-many with users and events
- Active/inactive status

**Examples:** Music, Sports, Travel, Food & Drinks, Culture, Workshop, etc.

**Note:** Bank account and payout request models are documented in detail in **Section 4.5 (Payout Module)** below.

---

## **2. EVENTS MODULE** 🎉

### **2.1 VENUE** 📍
**Purpose:** Physical and virtual event locations

**Venue Types:**
- `indoor` - Indoor venues
- `outdoor` - Outdoor locations
- `virtual` - Online events
- `hybrid` - Combined format

**Location Data:**
- `latitude` / `longitude` - Decimal(9,6) for precision
- `address` - Full text address
- `metadata` - Additional info (accessibility, parking, etc.)

**Business Logic:**
- Capacity of 0 = unlimited
- Inactive venues hidden from selections
- UUID for public API references

---

### **2.2 EVENT** 🎊
**Purpose:** Central event entity with complete lifecycle management

**Event Lifecycle:**
```
draft → published → completed
         ↓
     cancelled/postponed
```

**Pricing & Payment:**
- `is_paid` - Free or paid event
- `ticket_price` - Decimal(10,2) in local currency
- `gst_number` - Host's GST registration (India)
- `allow_plus_one` - Guest permissions

**Capacity Management:**
- `max_capacity` - 0 = unlimited
- `going_count` - Confirmed attendees (optimized counter)
- `requests_count` - Pending requests (optimized counter)

**Access Control:**
- `allowed_genders` - all/male/female/non_binary
- `is_public` - Public or private events

**Media:**
- `cover_images` - Array of 1-3 image URLs
- Related `EVENT_IMAGE` table for additional images

**Search & Discovery:**
- `title` - 3-200 characters
- `slug` - Auto-generated, URL-friendly
- `description` - Rich text, minimum 10 characters
- Links to `EVENT_INTEREST` via `EVENT_INTEREST_MAP`

**Venue Options:**
1. Link to existing `VENUE` (`venue_id`)
2. Custom text venue (`venue_text`)
3. Both null (virtual/online)

**Business Rules:**
- `end_time` must be after `start_time`
- Slug auto-generated from title
- UUID for public API access
- Published events visible to users
- Cancelled events soft-deleted

---

### **2.3 EVENT_INTEREST_MAP** 🔗
**Purpose:** Many-to-many mapping between events and interests

**Business Logic:**
- Enables event categorization
- Supports multiple categories per event
- Used for search, filtering, and recommendations

---

### **2.4 EVENT_IMAGE** 📸
**Purpose:** Store multiple images per event with ordering

**Features:**
- `position` - Display order (0, 1, 2, ...)
- `image_url` - Full image URL
- Ordered display in galleries

**Use Cases:**
- Event galleries
- Multiple cover images
- Progressive image loading

---

### **2.5 EVENT_REQUEST** 🙋
**Purpose:** Users request to join events

**Request Flow:**
```
pending → accepted (creates EVENT_ATTENDEE)
       ↓
    declined/cancelled/expired
```

**Key Fields:**
- `message` - User's request note
- `host_message` - Host's response
- `seats_requested` - Number of seats

**Business Rules:**
- One pending request per user per event
- Approved requests convert to `EVENT_ATTENDEE`
- `requests_count` updated on request creation/approval

---

### **2.6 EVENT_INVITE** ✉️
**Purpose:** Hosts directly invite users

**Invite Types:**
- `direct` - Personal invitation
- `share_link` - Shareable invite link

**Features:**
- `expires_at` - Invite validity period
- `host` - Inviting user (optional, defaults to event host)
- `message` - Personal invite note

**Business Rules:**
- One invite per user per event
- Expired invites auto-marked
- Accepted invites create `EVENT_ATTENDEE`

---

### **2.7 EVENT_ATTENDEE** ✅
**Purpose:** Confirmed event participants

**Ticket Types:**
- `standard`, `vip`, `early_bird`, `premium`
- `general`, `group`, `couple`, `family`
- `student`, `senior_citizen`, `disabled`, `other`

**Payment Tracking:**
- `is_paid` - Payment status
- `price_paid` - Amount paid
- `platform_fee` - Platform fee

**Attendance Status:**
- `going` - Confirmed
- `maybe` - Tentative
- `not_going` - Cancelled
- `checked_in` - At event

**Business Logic:**
- Links to originating `EVENT_REQUEST` if applicable
- Multiple seats per attendee supported
- Check-in tracking for paid events
- UUID for public API access

---

### **2.8 CAPACITY_RESERVATION** 🔒
**Purpose:** Temporary seat holds during payment

**Business Logic:**
- Prevents overbooking
- Expires after payment timeout
- Converted to `EVENT_ATTENDEE` after payment
- `reservation_key` - Unique reservation identifier

**Use Case:**
```
User selects seats → Reservation created → Payment → Attendee record
                    ↓ (expires)
                 Reservation cancelled
```

---

## **3. ATTENDANCE MODULE** 🎫

### **3.1 ATTENDANCE_RECORD** 📝
**Purpose:** Comprehensive attendance tracking

**Key Change:**
- **Foreign Key Updated**: `user` field now references `USER_PROFILE` instead of `AUTH_USER`
- This ensures data consistency and proper relationship with user profiles
- Migration `0002_fix_orphaned_and_alter_user_fk.py` handles the FK change and creates missing profiles

**Features:**
- `ticket_secret` - Unique 32-character ticket code
- `payment_status` - unpaid/paid/refunded
- `checked_in_at` / `checked_out_at` - Duration tracking
- `notes` - Additional information

**Business Logic:**
- Unique ticket secret per attendance
- Check-in/check-out tracking
- Duration calculation property
- Links to `USER_PROFILE` for proper user relationship

**SECURITY ENFORCEMENT - Ticket Secret Validation:**
- **MANDATORY RULE**: `ticket_secret` can be validated for check-in ONLY IF:
  - `event.is_paid == False` (free event), OR
  - `payment_order.status == "paid"` (verified payment)
- **Protection**: Even if `EVENT_ATTENDEE` and `ATTENDANCE_RECORD` exist, unpaid users cannot check in to paid events.
- **Validation Method**: `validate_ticket_secret_for_checkin()` enforces payment verification before allowing check-in.
- **Payment Order Link**: `payment_order_id` FK enables direct verification of payment status from `PAYMENT_ORDER`.

---

### **3.2 TICKET_SECRET** 🎫
**Purpose:** Cryptographically secure ticket verification

**Security Model:**
- `secret_hash` - Hashed ticket secret
- `secret_salt` - Unique salt per ticket
- `is_redeemed` - Prevents reuse

**Business Logic:**
- One per `ATTENDANCE_RECORD`
- Prevents ticket forgery
- Redemption timestamp

---

## **4. PAYMENT MODULE** 💳

### **4.1 PAYMENT_ORDER** 💰
**Purpose:** Central payment order management with financial snapshot and retry tracking

**Payment Providers:**
- `razorpay`, `stripe`, `paypal`
- `paytm`, `phonepe`, `gpay`, `payu`
- `cash`, `bank_transfer`

**Status Flow:**
```
created → pending → paid/completed OR failed/cancelled
                    ↓
                  refunded
```

**Key Fields:**
- `order_reference` - Human-readable ID
- `order_id` - Unique system ID
- `amount` - Total amount (base price + platform fee)
- `currency` - INR/USD/EUR/GBP
- `seats_count` - Number of seats/tickets (default: 1)
- `base_price_per_seat` - Base ticket price at payment time (immutable snapshot)
- `platform_fee_percentage` - Platform fee % at payment time (immutable snapshot)
- `platform_fee_amount` - Total platform fee at payment time (immutable snapshot)
- `host_earning_per_seat` - Host earning per seat at payment time (immutable snapshot)
- `parent_order` - Parent order if this is a retry attempt (nullable)
- `is_final` - True if this is the final successful payment (not a retry)
- `provider_response` - Complete provider data
- `refund_amount` - Partial/full refunds

**Financial Snapshot (CFO Requirement):**
- All financial fields (`base_price_per_seat`, `platform_fee_percentage`, `platform_fee_amount`, `host_earning_per_seat`) are captured at payment time
- These values are immutable and never change retroactively
- Enables accurate financial reconciliation even if pricing rules change later

**Retry Tracking (CTO Requirement):**
- `parent_order` links retry attempts to original order
- `is_final` flag distinguishes final successful payment from retry attempts
- Only final payments (`is_final=True`) are used for reconciliation and payouts

**Business Rules:**
- `order_reference` auto-generated if not provided
- Expires after 10 minutes (configurable) if unpaid
- Refunds tracked with reason
- Financial snapshot captured when payment succeeds
- Previous orders marked as non-final when new payment succeeds

**SECURITY ENFORCEMENT:**
- **Identity Model**: Only `USER_PROFILE` (customers) can create payment orders. `AUTH_USER` (admin/staff) accounts are blocked from creating payments via service-level guards.
- **DB-Level Unique Constraint**: Partial unique index `(user_id, event_id) WHERE is_final = true` ensures only ONE final payment per user per event (prevents race conditions).
- **Race Condition Protection**: Application-level double-check prevents duplicate final payments even under concurrent requests.
- **Transactional Guarantees**: All payment finalization operations (order update, transaction creation, attendee fulfillment, reservation consumption) are atomic via `@transaction.atomic`.

---

### **4.2 PAYMENT_TRANSACTION** 💸
**Purpose:** Individual transaction tracking

**Transaction Types:**
- `payment` - Initial payment
- `refund` - Refund processing
- `chargeback` - Dispute handling

**Features:**
- Links to `PAYMENT_ORDER`
- Provider-specific transaction IDs
- Complete response logging

---

### **4.3 PAYMENT_WEBHOOK** 📡
**Purpose:** Webhook logging and processing

**Features:**
- `signature` - Security verification
- `payload` - Complete webhook data
- `processed` - Processing status
- Error tracking

**SECURITY HARDENING:**
- **IP Address Verification**: Client IP verified against PayU IP ranges (configurable via `PAYU_IP_RANGES` environment variable).
- **Rate Limiting**: Basic in-memory rate limiting; production should use Redis or nginx rate limiting.
- **Strict Signature Verification**: Hash verification is mandatory (handled by `PayUService.verify_reverse_hash()`).
- **Idempotent Processing**: Safe to retry webhooks; duplicate processing prevented via `processed` flag.
- **Configuration**: `PAYU_STRICT_IP_CHECK` environment variable controls IP verification strictness.

**Use Cases:**
- Payment confirmations
- Refund notifications
- Dispute alerts

---

## **4.5 PAYOUT MODULE** 💸

### **4.5.1 BANK_ACCOUNT** 💳
**Purpose:** Store bank account details for hosts to receive payouts

**Key Features:**
- Multiple bank accounts per host (1-to-many relationship)
- Single primary account designation (enforced via save() method)
- Security-first design with masked account numbers
- Verification workflow for compliance
- Active/inactive status for account lifecycle management

**Fields:**
- `uuid` - Public unique identifier for API access
- `host` - Foreign key to AUTH_USER (the host who owns the account)
- `bank_name` - Name of the bank (e.g., "State Bank of India", "HDFC Bank")
- `account_number` - Full account number (stored securely, displayed masked)
- `ifsc_code` - 11-character IFSC code (Indian Financial System Code)
  - Format: AAAA0XXXXXX (4 letters, 0, 6 alphanumeric)
- `account_holder_name` - Name as registered with the bank
- `is_primary` - Boolean flag (only one primary account per host)
- `is_verified` - Verification status (for compliance workflows)
- `is_active` - Soft delete flag (deactivate instead of hard delete)

**Security Features:**
- Account numbers automatically masked in API responses (format: `****XXXX`)
- Masked display in admin panel and list views
- UUID for public API access (no ID exposure)

**Business Logic:**
- Primary account enforcement: When a bank account is marked as `is_primary=True`,
  all other bank accounts for the same host are automatically set to `is_primary=False`
- This ensures only one primary account exists per host at any time
- Indexed on `host`, `is_primary`, and `is_active` for efficient queries

**Validation Rules:**
- IFSC code must be exactly 11 characters, format: AAAA0XXXXXX
- Account number must contain only digits
- Bank name and account holder name: minimum 2 characters, trimmed

**Use Cases:**
- Host adds bank account for receiving payouts
- Host designates primary account for automatic payouts
- Admin verifies bank account details
- Host deactivates old bank accounts

---

### **4.5.2 HOST_PAYOUT_REQUEST** 💰
**Purpose:** Immutable financial snapshot for host payout requests from event earnings with payment reconciliation

**Key Concept:** This model captures a complete, immutable snapshot of event and financial data at the time a payout is requested. This ensures accurate audit trails even if event details change later.

**Financial Snapshot Fields (Immutable):**
- `host_name` - Host's name at the time of request
- `event_name` - Event title at the time of request
- `event_date` - Event start time (start_time) at request time
- `event_location` - Venue name + city, or custom venue_text
- `total_capacity` - Event maximum capacity at request time
- `base_ticket_fare` - Base ticket price set by host
- `final_ticket_fare` - Final price buyers pay (base + 10% platform fee)
- `total_tickets_sold` - Count of paid attendance records
- `attendees_details` - JSON array with attendee information:
  ```json
  [
    {"name": "John Doe", "contact": "+1234567890"},
    {"name": "Jane Smith", "contact": "jane@example.com"}
  ]
  ```
- `platform_fee_amount` - Total platform fee (platform fee % of base × tickets sold)
- `final_earning` - Host earnings (base ticket fare × tickets sold)
- `payment_orders` - Many-to-Many relationship to PaymentOrder records that funded this payout (for reconciliation)

**Business Logic - Platform Fee Model:**

The platform uses an **additive fee model** (not deductive) with **configurable platform fee**:

```
Example (assuming 10% platform fee):
- Base ticket fare: ₹100 (set by host)
- Platform fee: 10% (configurable via admin panel, default: 10%)
- Final ticket fare: ₹110 (paid by buyer = base + 10%)
- Tickets sold: 50

Revenue Flow:
- Total collected from buyers: ₹110 × 50 = ₹5,500
- Host earnings: ₹100 × 50 = ₹5,000 (no deduction)
- Platform fee: ₹10 × 50 = ₹500 (collected from buyers)

Host receives: ₹5,000 (full base fare)
Platform receives: ₹500 (10% fee)
Buyers paid: ₹5,500 (₹100 base + ₹10 fee per ticket)
```

**Key Points:**
- Host earns the **full base ticket fare** (no platform fee deduction)
- Platform fee is **added on top** and paid by buyers
- Platform fee is **configurable** via Django Admin (see `PLATFORM_FEE_CONFIG` model)
- Default platform fee: 10% (can be changed by superusers)
- Host earnings = Base ticket fare × Tickets sold
- Platform fee = Base ticket fare × Platform fee % × Tickets sold (from config)

**Payout Status Workflow:**
```
pending → approved → processing → completed
    ↓
rejected/cancelled
```

**Status Fields:**
- `status` - Current payout request status
  - `pending` - Awaiting admin review
  - `approved` - Approved, ready for processing
  - `processing` - Payout being processed
  - `completed` - Payout successfully completed
  - `rejected` - Rejected by admin
  - `cancelled` - Cancelled by host or system
- `processed_at` - Timestamp when payout was actually processed
- `transaction_reference` - Bank transaction reference number (after completion)
- `rejection_reason` - Admin-provided reason if status is rejected
- `notes` - Internal administrative notes

**Data Integrity:**
- Foreign keys use `PROTECT` instead of `CASCADE` to prevent accidental deletion
  - Bank accounts cannot be deleted if they have payout requests
  - Events cannot be deleted if they have payout requests
- All financial snapshot fields are immutable after creation
- Indexed on `event`, `bank_account`, `status`, and `event_date` for efficient queries
- UUID for public API access

**Business Rules:**
- Only the event host can create a payout request for their event
- Only one active payout request per event allowed (status: pending/approved/processing)
- Requires paid ticket sales (cannot request payout for events with no ticket sales)
- Bank account must be active and belong to the requesting host
- Financial calculations done server-side at request time for accuracy

**Calculation Source:**
- `total_tickets_sold` - Counted from `ATTENDANCE_RECORD` where:
  - `payment_status` IN ('paid', 'completed')
  - `status` IN ('going', 'checked_in')
  - Sum of `seats` field
- Revenue calculated from `PAYMENT_ORDER` where:
  - `status` = 'completed'
- Platform fee calculated as: Base ticket fare × Platform fee % × Tickets sold (from `PLATFORM_FEE_CONFIG`)
- Host earnings calculated as: Base ticket fare × Tickets sold

**Audit Trail:**
- Complete event state captured at request time
- Attendee details stored for compliance
- All financial metrics frozen at creation
- Status changes tracked with timestamps

---

## **4.6 HOST LEAD MODULE** 📋

### **4.6.1 HOST_LEAD** 📝
**Purpose:** Store "Become a Host" lead information from potential hosts who want to host events

**Key Features:**
- Lead generation and tracking system
- Contact status tracking (contacted/not contacted)
- Conversion tracking (converted to actual host/not converted)
- Internal notes for lead management

**Fields:**
- `first_name` - First name of the potential host (max 100 chars)
- `last_name` - Last name of the potential host (max 100 chars)
- `phone_number` - Phone number (unique, max 20 chars, indexed)
- `message` - Optional message from the potential host
- `is_contacted` - Whether the lead has been contacted by admin team (default: false)
- `is_converted` - Whether the lead became an actual host (default: false)
- `notes` - Internal administrative notes about the lead
- `created_at` / `updated_at` - Timestamps (auto-managed)

**Business Logic:**
- Leads submitted via `/api/hosts/become-a-host` endpoint
- Leads are stored regardless of contact status (full audit trail)
- Conversion status updated when lead creates their first event
- Phone number must be unique (prevents duplicate leads)
- Ordered by creation date (newest first)

**Use Cases:**
- Capture interest from potential hosts
- Track lead generation funnel
- Manage host onboarding process
- Monitor conversion rates

**Admin Interface:**
- Accessible via Django Admin at `/django/admin/users/hostlead/`
- Admin users can mark leads as contacted/converted
- Add internal notes for team collaboration
- Filter and search by name, phone number, status

---

### **4.6.2 HOST_LEAD_WHATSAPP_TEMPLATE** 📱
**Purpose:** Pre-approved WhatsApp message templates for communicating with host leads

**Key Features:**
- Centralized template management
- Pre-approved message copy for consistency
- Admin-managed templates only

**Fields:**
- `name` - Short identifier for the template (unique, max 120 chars)
  - Example: "Intro Message", "Follow-up", "Welcome Template"
- `message` - Pre-approved message text
  - This text is injected into Twilio template variable {{2}}
  - Must be approved before use (prevents inconsistent messaging)

**Business Logic:**
- Templates are read-only at runtime (admin-only creation/editing)
- Templates used when sending WhatsApp messages to leads via admin panel
- Template name used in admin UI for selection
- Message content stored for audit trail

**Use Cases:**
- Standardize host lead communication
- Ensure consistent messaging across team
- Pre-approved copy for compliance
- Quick template selection in admin panel

**Admin Interface:**
- Accessible via Django Admin at `/django/admin/users/hostleadwhatsapptemplate/`
- Admin users can create/edit/delete templates
- Templates appear in dropdown when sending messages to leads

---

### **4.6.3 HOST_LEAD_WHATSAPP_MESSAGE** 💬
**Purpose:** Audit log of WhatsApp messages sent to host leads through admin panel

**Key Features:**
- Complete message delivery tracking
- Twilio integration logging
- Status tracking (queued, sent, delivered, failed, etc.)
- Error logging for debugging

**Fields:**
- `lead` - Foreign key to HOST_LEAD (required)
- `template` - Foreign key to HOST_LEAD_WHATSAPP_TEMPLATE (optional)
- `sent_by` - Foreign key to AUTH_USER (admin who sent, nullable)
- `content_sid` - Twilio Content Template SID (max 80 chars)
- `variables` - JSON object of variables sent to Twilio
  - Example: `{'1': 'John Doe', '2': 'Welcome message...'}`
- `body_variable` - Final text value used for template variable {{2}}
- `status` - Delivery status:
  - `queued` - Queued / Sending
  - `sent` - Sent successfully
  - `delivered` - Delivered to recipient
  - `undelivered` - Delivery failed
  - `failed` - Send failed
  - `test-mode` - Test mode (not actually sent)
- `twilio_sid` - Twilio message SID for tracking (max 64 chars, nullable)
- `error_code` - Twilio error code if failed (max 50 chars, nullable)
- `error_message` - Human-readable error message (nullable)
- `created_at` / `updated_at` - Timestamps

**Business Logic:**
- Messages sent via Django Admin panel only (admin users)
- All message attempts logged regardless of success/failure
- Status updated based on Twilio webhook callbacks
- Complete audit trail for compliance and debugging
- Links to lead and template for full context

**Use Cases:**
- Track communication with host leads
- Debug delivery issues
- Monitor message delivery rates
- Compliance and audit requirements
- Analyze conversion funnel effectiveness

**Relationships:**
- Many-to-One → `HOST_LEAD` (one lead receives many messages)
- Many-to-One → `HOST_LEAD_WHATSAPP_TEMPLATE` (one template used by many messages)
- Many-to-One → `AUTH_USER` (one admin sends many messages)

**Admin Interface:**
- Accessible via Django Admin at `/django/admin/users/hostleadwhatsappmessage/`
- Shows all messages sent to leads
- Filter by lead, status, date
- View Twilio delivery status and errors

---

## **5. NOTIFICATION MODULE** 🔔

### **5.1 USER_DEVICE** 📱
**Purpose:** Device registration for push notifications

**See Section 1.4 USER_DEVICE for complete documentation.**

**Key Points:**
- Maps USER_PROFILE to OneSignal player IDs
- Supports multiple devices per user (iOS, Android)
- Enables push notification delivery via OneSignal
- Devices deactivated (soft-delete) when player IDs become invalid

---

### **5.2 NOTIFICATION** 📬
**Purpose:** In-app user notifications for **normal users (customers)**

**⚠️ IMPORTANT:** Notifications are linked to `USER_PROFILE` (normal users), NOT admin users.

**Relationships:**
- `recipient` → `USER_PROFILE` (normal user receiving notification)
- `sender` → `USER_PROFILE` (normal user sending notification, optional)

**Notification Types:**
- `event_request` - Request received/approved
- `event_invite` - Invitation received
- `event_update` - Event changed
- `event_cancelled` - Event cancelled
- `payment_success` - Payment completed
- `payment_failed` - Payment failed
- `reminder` - Event reminder
- `system` - System notifications
- `promotional` - Marketing messages

**Features:**
- `reference_type` / `reference_id` - Link to object
- `metadata` - Additional context
- `is_read` - Read/unread status
- UUID for API access

**Business Logic:**
- Push notifications sent via OneSignal using USER_DEVICE player IDs
- Notification records persisted regardless of push success (audit trail)
- In-app notifications available even if push delivery fails
- 30-day retention
- Batch processing for campaigns
- Read status tracking
- All notifications are for normal users (`USER_PROFILE`), not admin users

**Push Notification Flow:**
1. Notification created → `NOTIFICATION` record saved (always)
2. `USER_DEVICE` queried for active devices per recipient
3. Push sent via OneSignal to all active devices
4. Invalid player IDs trigger device deactivation
5. Notification record persisted for in-app inbox regardless of push result

**Campaign Tracking:**
- Optional `campaign` foreign key links notifications to admin-driven campaigns
- Campaign-driven notifications are tracked for audit and reporting
- Transactional notifications (payments, events) typically have `campaign=None`

---

### **5.3 CAMPAIGN** 🎯
**Purpose:** Admin-driven notification campaign system

**Key Concept:** Campaigns allow administrators to send targeted notifications to specific user segments without code changes. This is separate from transactional notifications (which are automatic and event-driven).

**Campaign Lifecycle:**
```
draft → previewed → scheduled/sending → sent
                  ↓
              cancelled/failed
```

**Template Integration:**
- Campaigns use dynamic templates from `NOTIFICATION_TEMPLATE` table (created by admins/marketing team)
- Templates define message format, target screen, and required parameters
- Each template has a `version` field for versioning (campaigns store immutable `template_version` snapshot)
- Templates become immutable (locked) once used in any campaign to preserve historical accuracy
- Template variables are edited via UI (no JSON required)
- Variable hints stored in `TEMPLATE_VARIABLE_HINT` table (UI-based, one hint per variable)

**Audience Selection:**
- `audience_rules` - JSON structure auto-generated from UI fields (not directly edited)
- UI-based form fields replace JSON editing (marketing-friendly)
- Logic: ALL filters use AND (user must match all conditions), Event interests use OR (user must have ANY selected interest)
- Rules use field-based queries (location, interests, profile completion, verification status, etc.)
- Negative filters supported (e.g., "No - Only users with incomplete profiles")
- Rule engine safely translates UI selections to Django ORM queries
- Preview functionality shows matching user count before sending

**Status Management:**
- `draft` - Campaign created but not previewed
- `previewed` - Audience previewed, ready to send
- `scheduled` - Scheduled for future execution (future feature)
- `sending` - Currently being executed
- `sent` - Successfully completed (immutable)
- `cancelled` - Cancelled before sending (immutable)
- `failed` - Execution failed (immutable)

**Execution Tracking:**
- `total_sent` - Count of successfully delivered notifications
- `total_failed` - Count of failed deliveries
- `execution_metadata` - Errors, warnings, batch processing info
- All executions logged in `CAMPAIGN_EXECUTION` table

**Versioning & Immutability:**
- `template_version` - Immutable snapshot of template version at campaign creation
- Ensures campaigns always reference the exact template they were created with
- Enables analytics, rollbacks, and historical traceability
- Templates locked once used (content fields cannot be changed)
- Template version auto-captured on campaign creation

**Security & Audit:**
- Only AUTH_USER with `is_staff=True` can create/send campaigns
- Campaigns immutable after sending (cannot modify sent campaigns)
- Campaign execution is idempotent (atomic status transition, prevents duplicate sends)
- All actions logged in `AUDIT_LOG` (campaign_create, campaign_preview, campaign_execute, campaign_cancel)
- Kill switch via `DISABLE_CAMPAIGN_SYSTEM` environment variable

**Business Rules:**
- Mandatory preview before sending (prevents "send to everyone" mistakes)
- Campaign can only be executed once (idempotency enforced at database level)
- Rate limiting: Max users per campaign configurable (default: 10,000)
- Batch processing for large audiences (default: 100 per batch)
- Only users with active devices receive push notifications
- Campaigns are immutable once sent (audit trail protection)
- Audience logic: ALL filters = AND, Event interests = OR (explicitly documented)

**Use Cases:**
- Profile completion reminders for incomplete profiles
- Event recommendations based on user interests
- Location-based event alerts
- Engagement campaigns for inactive users
- Educational notifications about platform features

---

### **5.4 NOTIFICATION_TEMPLATE** 📝
**Purpose:** Dynamic notification templates created by admins/marketing team

**Key Concept:** Templates allow marketing team to create and manage notification message formats without code changes. This is IDEA-2 (Campaign System). IDEA-1 (Automated System Notifications) uses templates in `notifications/services/messages.py` and works independently.

**Key Features:**
- Dynamic template creation via Django Admin (no code required)
- Versioning for audit trail and analytics (`version` field, unique per `key`)
- Immutability protection (templates lock once used in campaigns)
- Variable placeholders (e.g., `{{event_name}}`, `{{user_name}}`)
- UI-based variable hints (stored in `TEMPLATE_VARIABLE_HINT` table)

**Fields:**
- `name` - Template name (unique, e.g., 'Profile Completion Reminder')
- `key` - Unique template key/slug (unique, indexed, e.g., 'profile_completion_reminder')
- `title` - Notification title with `{{variable}}` placeholders (max 200)
- `body` - Notification message with `{{variable}}` placeholders
- `target_screen` - Mobile app screen to navigate to (default: 'home')
- `notification_type` - Type of notification (from NOTIFICATION_TYPE_CHOICES)
- `version` - Template version number (default: 1, indexed, unique per key)
- `is_active` - Whether template is available for use (default: true, indexed)
- `created_by` - Admin user who created (nullable)

**Immutability Rules:**
- Templates become immutable (locked) once used in at least one campaign
- Content fields (`title`, `body`, `target_screen`, `notification_type`) cannot be edited when locked
- `is_immutable` property checks if template is used in any campaign
- Ensures historical campaigns always reference the exact template they were created with
- Admins must create a new template if they need different content (versioning)

**Versioning:**
- Version starts at 1 for new templates
- Version increments on meaningful content changes (if not locked)
- Each version is unique per key (`unique_together: ['key', 'version']`)
- Campaigns store immutable `template_version` snapshot for audit trail
- Enables analytics, rollbacks, A/B testing, and historical traceability

**Relationships:**
- Many-to-One → `AUTH_USER` (one admin creates templates)
- One-to-Many → `CAMPAIGN` (one template used by many campaigns)
- One-to-Many → `TEMPLATE_VARIABLE_HINT` (one template has many variable hints)

**Use Cases:**
- Marketing campaigns with custom messaging
- Seasonal promotions
- User engagement notifications
- Educational content

---

### **5.5 TEMPLATE_VARIABLE_HINT** 💡
**Purpose:** Help text for template variables (UI-based, no JSON!)

**Key Features:**
- Each variable gets its own record with clear help text
- Marketing team can easily understand and edit these
- Replaces JSON-based variable hints with database records

**Fields:**
- `template` - Parent template (required, FK to NOTIFICATION_TEMPLATE)
- `variable_name` - Variable name without braces (e.g., 'event_name')
- `help_text` - Help text explaining what this variable is for (e.g., 'Name of the event')
- Unique constraint: `['template', 'variable_name']` (one hint per variable per template)

**Business Logic:**
- Variables are auto-extracted from template `title` and `body` fields
- Each `{{variable}}` placeholder gets a hint record
- Help text shown in campaign admin when filling template variables
- Makes campaign creation user-friendly for non-technical users

**Relationships:**
- Many-to-One → `NOTIFICATION_TEMPLATE` (one template has many variable hints)

---

### **5.6 CAMPAIGN_EXECUTION** 📊
**Purpose:** Individual notification delivery tracking for campaigns

**Key Features:**
- Links each notification sent in a campaign to the campaign record
- Tracks delivery success/failure for each user
- Stores OneSignal API responses for debugging
- Enables campaign performance analysis and error investigation

**Fields:**
- `campaign` - Parent campaign (required)
- `notification` - Notification record created (required)
- `user_profile` - User who received notification (required)
- `sent_successfully` - Whether push notification was delivered (boolean, indexed)
- `error_message` - Error details if delivery failed
- `onesignal_response` - Raw OneSignal API response (for debugging)
- `delivered_at` - Timestamp when notification was delivered (nullable, indexed)

**Business Logic:**
- One execution record per notification per campaign
- Execution records created during campaign execution
- Success/failure determined by OneSignal API response
- Error messages captured for failed deliveries
- Enables campaign analytics and debugging

**Use Cases:**
- Campaign performance analysis (success rate, failure rate)
- Debugging delivery issues (specific user failures)
- Audit trail for compliance
- User-specific delivery history

**Relationships:**
- Many-to-One → `CAMPAIGN` (one campaign has many executions)
- One-to-One → `NOTIFICATION` (one execution tracks one notification)
- Many-to-One → `USER_PROFILE` (one user can receive multiple campaign notifications)

---

## **5.5 CORE CONFIGURATION MODULE** ⚙️

### **5.5.1 PLATFORM_FEE_CONFIG** 💰
**Purpose:** Singleton model for system-wide platform fee configuration

**Key Features:**
- **Singleton Pattern**: Only one instance exists (id=1, enforced at database level)
- **Admin Configurable**: Superusers can modify platform fee via Django Admin
- **Cached for Performance**: 1-hour cache TTL with automatic invalidation
- **Security**: Password confirmation required for changes, superuser-only access

**Fields:**
- `id` - Always 1 (singleton identifier)
- `fee_percentage` - Platform fee percentage (0.00-100.00, default: 10.00)
- `is_active` - Whether this configuration is currently active
- `description` - Optional notes about the fee configuration
- `updated_by` - Admin user who last updated (nullable)
- `created_at` / `updated_at` - Timestamps

**Business Logic:**
- Platform fee is a percentage (0-100) of the base ticket fare
- Fee is **added on top** of base fare (buyer pays: base + fee)
- Host earns **full base fare** (no deduction)
- Platform collects the fee from buyers
- Used by all financial calculations:
  - Payout requests (`HOST_PAYOUT_REQUEST`)
  - Payment orders (`PAYMENT_ORDER`)
  - Analytics calculations
  - Event revenue calculations

**Admin Interface:**
- Accessible only to superusers
- Password confirmation required for changes
- Clear UI showing fee percentage and decimal multiplier
- Automatic cache invalidation on updates

**Caching Strategy:**
- Three-tier cache: `platform_fee_config`, `platform_fee_percentage`, `platform_fee_decimal`
- 1-hour TTL (3600 seconds)
- Automatic cache invalidation on configuration updates
- Cache-aside pattern with fallback to database

**Example Usage:**
```python
from core.models import PlatformFeeConfig

# Get current fee percentage
fee_percentage = PlatformFeeConfig.get_fee_percentage()  # Decimal('10.00')

# Get fee as decimal multiplier
fee_decimal = PlatformFeeConfig.get_fee_decimal()  # Decimal('0.10')

# Calculate platform fee for 5 tickets at ₹100 base fare
platform_fee = PlatformFeeConfig.calculate_platform_fee(
    base_fare=Decimal('100.00'),
    quantity=5
)  # Decimal('50.00')

# Calculate final price buyer pays
final_price = PlatformFeeConfig.calculate_final_price(
    base_fare=Decimal('100.00')
)  # Decimal('110.00')
```

---

## **6. AUDIT MODULE** 🔍

### **6.1 AUDIT_LOG** 📊
**Purpose:** Comprehensive audit trail

**Actions Logged:**
- `create`, `update`, `delete`
- `login`, `logout`
- `password_change`
- `profile_update`

**Security Data:**
- `ip_address` - User IP
- `user_agent` - Browser/client
- `session_key` - Session ID
- `payload` - Data snapshot

**Severity Levels:**
- `low` - Routine actions
- `medium` - Standard changes
- `high` - Sensitive operations
- `critical` - Security events

**Business Logic:**
- Tracks success/failure
- Stores old/new values
- Links to objects via ID/UUID
- Immutable history

---

### **6.2 AUDIT_LOG_SUMMARY** 📈
**Purpose:** Daily audit statistics

**Metrics:**
- `count` - Total actions
- `successful_count` - Successful
- `failed_count` - Failed

**Features:**
- Daily aggregation
- Per-user summaries
- Per-action statistics

**Use Cases:**
- Compliance reporting
- Security monitoring
- Analytics

---

## **7. RELATIONSHIP SUMMARY**

| Relationship | Tables | Description |
|-------------|--------|-------------|
| **1-to-1** | `AUTH_USER` ↔ `USER_PROFILE` | Every user has one profile |
| **1-to-1** | `USER_PHONE_OTP` → Phone | One active OTP per phone |
| **1-to-1** | `ATTENDANCE_RECORD` ↔ `TICKET_SECRET` | One secret per attendance |
| **1-to-Many** | `USER_PROFILE` → `ATTENDANCE_RECORD` | User profile has many attendance records |
| **1-to-Many** | `AUTH_USER` → `PLATFORM_FEE_CONFIG` | Admin updates platform fee config |
| **1-to-Many** | `USER_PROFILE` → `USER_DEVICE` | User profile has many devices |
| **1-to-Many** | `USER_PROFILE` → `EVENT` | Host creates many events |
| **1-to-Many** | `VENUE` → `EVENT` | Venue hosts many events |
| **1-to-Many** | `EVENT` → `EVENT_REQUEST/INVITE/ATTENDEE` | Event has many interactions |
| **1-to-Many** | `EVENT_REQUEST` → `EVENT_ATTENDEE` | Request converts to attendee |
| **1-to-Many** | `PAYMENT_ORDER` → Transactions/Webhooks | Order has many records |
| **1-to-Many** | `AUTH_USER` → `CAMPAIGN` | Admin creates/sends campaigns |
| **1-to-Many** | `AUTH_USER` → `NOTIFICATION_TEMPLATE` | Admin creates templates |
| **1-to-Many** | `NOTIFICATION_TEMPLATE` → `CAMPAIGN` | Template used by campaigns |
| **1-to-Many** | `NOTIFICATION_TEMPLATE` → `TEMPLATE_VARIABLE_HINT` | Template has variable hints |
| **1-to-Many** | `CAMPAIGN` → `NOTIFICATION` | Campaign triggers notifications |
| **1-to-Many** | `CAMPAIGN` → `CAMPAIGN_EXECUTION` | Campaign has many execution records |
| **1-to-Many** | `NOTIFICATION` → `CAMPAIGN_EXECUTION` | Notification tracked by execution |
| **1-to-Many** | `AUTH_USER` → `HOST_LEAD_WHATSAPP_MESSAGE` | Admin sends WhatsApp messages to leads |
| **1-to-Many** | `HOST_LEAD` → `HOST_LEAD_WHATSAPP_MESSAGE` | Lead receives many WhatsApp messages |
| **1-to-Many** | `HOST_LEAD_WHATSAPP_TEMPLATE` → `HOST_LEAD_WHATSAPP_MESSAGE` | Template used by many messages |

| **Many-to-Many** | `USER_PROFILE` ↔ `EVENT_INTEREST` | Users have many interests |
| **Many-to-Many** | `EVENT` ↔ `EVENT_INTEREST` | Events in many categories |

---

## **8. BUSINESS LOGIC & FLOWS**

### **8.1 User Onboarding Flow**
```
1. User enters phone → `USER_PHONE_OTP` created
2. User receives 4-digit OTP via SMS
3. Verify OTP → `AUTH_USER` + `USER_PROFILE` created
4. Complete profile (name, gender, interests, pictures)
5. Profile marked as verified
```

### **8.2 Event Creation Flow**
```
1. Host creates event (draft status)
2. Add details (title, description, venue, pricing)
3. Select event interests
4. Upload cover images
5. Publish event (status: published)
```

### **8.3 Event Attendance Flow (Free)**
```
1. User requests to join → `EVENT_REQUEST` created
2. Host reviews request
3. Approve → `EVENT_ATTENDEE` created
4. Event `going_count` incremented
```

### **8.4 Event Attendance Flow (Paid)**
```
1. User requests to join → `EVENT_REQUEST` created
2. Host approves → `CAPACITY_RESERVATION` created (seats reserved)
3. User initiates payment → `PAYMENT_ORDER` created (status='created')
4. Backend generates PayU hash → Returns redirect payload
5. Frontend redirects to PayU → User completes payment
6. PayU redirects to success/failure URL → Backend verifies hash
7. PayU sends webhook → Backend finalizes payment (idempotent)
8. Payment success → Financial snapshot captured (immutable):
   - base_price_per_seat, platform_fee_percentage, platform_fee_amount, host_earning_per_seat
9. Payment success → `PAYMENT_ORDER.status='paid'`, `is_final=True`
10. Payment success → `EVENT_ATTENDEE` created with `payment_order` link
11. Payment success → `ATTENDANCE_RECORD` created with `payment_order` link + `TICKET_SECRET` generated
12. Payment success → `CAPACITY_RESERVATION` consumed, event `going_count` updated
13. User receives notification
14. At event → Check-in using ticket secret (payment verified)
```

### **8.5 Event Check-in Flow**
```
1. Attendee arrives at event
2. Verify ticket secret from their `ATTENDANCE_RECORD`
3. Mark as checked-in → Update `checked_in_at`
4. Status changes: going → checked_in
5. Optional: Check-out with `checked_out_at`
```

### **8.6 Host Payout Request Flow**
```
1. Host creates event and sells tickets
2. Event completes with paid attendance records
3. Host adds bank account details (via API or admin)
4. Host creates payout request → `HOST_PAYOUT_REQUEST` created
   - System calculates: tickets sold, revenue, platform fee, host earnings
   - Captures immutable snapshot of event and financial data
5. Admin reviews payout request (status: pending)
6. Admin approves → status: approved
7. Finance team processes → status: processing
8. Payout completed → status: completed
   - Transaction reference added
   - processed_at timestamp set
```

**Business Rules:**
- Only event host can create payout request for their event
- Only one active payout request per event (pending/approved/processing status)
- Financial calculations done at request time (immutable snapshot)
- Bank account must be active and belong to requesting host
- Requires paid ticket sales (cannot request payout for event with no sales)

---

## **9. SECURITY & PERFORMANCE**

### **9.1 Security Features**
- ✅ **Phone-based authentication** with OTP
- ✅ **JWT tokens** for API access
- ✅ **UUID public identifiers** (no ID exposure)
- ✅ **Hashed ticket secrets** (cryptographic security)
- ✅ **OTP attempt limiting** (prevents brute force)
- ✅ **Audit logging** (all actions tracked)
- ✅ **Payment webhook verification** (signature checks)
- ✅ **Soft deletes** (data retention)

### **9.2 Performance Optimizations**
- 📊 **Counter fields** (`going_count`, `requests_count`) for fast reads
- 📊 **Database indexes** on all foreign keys and search fields
- 📊 **select_related** / **prefetch_related** for query optimization
- 📊 **JSONB fields** for flexible metadata
- 📊 **UUIDs** for distributed systems
- 📊 **Pagination** on all list endpoints

### **9.3 Scalability Features**
- 🚀 **JSONB metadata** for extensibility
- 🚀 **Audit summaries** for reporting
- 🚀 **Webhook logging** for async processing
- 🚀 **Multiple payment providers** for reliability
- 🚀 **Event interest categorization** for discovery
- 🚀 **Capacity reservations** for paid events

---

## **10. DATA VALIDATION RULES**

| Field | Rule | Reason |
|-------|------|--------|
| `profile.name` | 2-100 chars, letters only | Valid names |
| `profile.profile_pictures` | 1-6 URLs | Appropriate photos |
| `profile.event_interests` | 1-5 selections | Personalization |
| `event.title` | 3-200 chars | Meaningful titles |
| `event.description` | min 10 chars | Sufficient detail |
| `event.end_time` | > start_time | Logical timing |
| `venue.latitude` | -90 to 90 | Valid coordinates |
| `venue.longitude` | -180 to 180 | Valid coordinates |
| `otp.attempts` | max 3 | Security |
| `otp.expires_at` | 10 min from creation | Security |
| `payment.amount` | min 0.01 | Valid amount |

---

## **11. API ENDPOINTS OVERVIEW**

### **Authentication** (`/api/auth/`)
- `POST /signup` - Request OTP for signup
- `POST /verify-otp` - Verify OTP
- `POST /complete-profile` - Complete user profile
- `GET /profile` - Get user profile

### **Events** (`/api/events/`)
- `GET /` - List events (filter, search, paginate)
- `POST /` - Create event
- `GET /{id}` - Get event details
- `PUT /{id}` - Update event
- `DELETE /{id}` - Soft delete event
- `GET /{id}/requests` - List requests

### **Venues** (`/api/venues/`)
- `GET /` - List venues
- `POST /` - Create venue
- `PUT /{id}` - Update venue
- `DELETE /{id}` - Delete venue

### **Payouts** (`/api/payouts/`)
- **Bank Accounts:**
  - `GET /bank-accounts` - List user's bank accounts
  - `POST /bank-accounts` - Create bank account (with IFSC validation)
  - `GET /bank-accounts/{id}` - Get bank account details
  - `PUT /bank-accounts/{id}` - Update bank account
  - `DELETE /bank-accounts/{id}` - Deactivate bank account

- **Payout Requests:**
  - `POST /requests` - Create payout request (auto-calculates financials)
  - `GET /requests` - List payout requests (with pagination and status filter)
  - `GET /requests/{id}` - Get detailed payout request with full breakdown

**Features:**
- Automatic financial calculation (tickets sold, platform fee, earnings)
- Host ownership validation
- Duplicate request prevention
- Immutable financial snapshots for audit trail

### **Notifications** (`/api/notifications/`)
- **Device Registration:**
  - `POST /devices/register` - Register device for push notifications
  - `DELETE /devices/{player_id}` - Deactivate device

**Features:**
- Register devices with OneSignal player IDs
- Support for iOS and Android platforms
- Multiple devices per user supported
- Automatic device deactivation on invalid player IDs
- Only USER_PROFILE (customers) can register devices (AUTH_USER blocked)

**Note:** 
- Campaign management is available via Django Admin interface (`/django/admin/notifications/campaign/`). Campaign APIs are intentionally not exposed to external clients for security reasons. Only staff users can manage campaigns.
- Template management is available via Django Admin interface (`/django/admin/notifications/notificationtemplate/`). Marketing team can create and manage templates here.
- Templates are immutable once used in any campaign (locked). This ensures historical campaigns always reference the exact template they were created with.
- Campaigns store immutable `template_version` snapshot for audit trail and analytics.
- Campaign execution is idempotent (can only be executed once, prevents duplicate sends).

---

## **12. DJANGO ADMIN STRUCTURE** 🔐

### **12.1 Admin Access Levels**

**Admin-Level Users** (`is_staff=True` or `is_superuser=True`):
- Full access to all models
- Can manage:
  - **Users** (AUTH_USER) - Authentication accounts and admin users
  - **Groups** - Permission groups for access control
  - All customer-facing models (USER_PROFILE, Bank Accounts, Events, etc.)

**Normal Users/Customers:**
- Limited admin access (if granted)
- Can manage customer-facing models:
  - **User Profiles** - Their own profile and customer profiles
  - **Bank Accounts** - Host bank account management
  - **Event Interests** - Event category management
  - **Host Leads** - Host lead generation records
  - **Host Lead WhatsApp Messages** - WhatsApp communication logs
  - **Host Lead WhatsApp Templates** - Message template management
  - **Host Payout Requests** - Payout request tracking
  - **Phone OTPs** - OTP verification records

### **12.2 Key Distinctions**

| Aspect | AUTH_USER (Users) | USER_PROFILE (User Profiles) |
|--------|------------------|------------------------------|
| **Purpose** | Authentication & Admin Access | Customer/End-User Data |
| **Admin Section** | Authentication and Authorization | User Management |
| **Access Level** | Admin-only (staff/superuser) | Customer-facing |
| **Visibility** | Internal platform management | Customer profiles |
| **Relationship** | Can exist without USER_PROFILE | Requires AUTH_USER (1-to-1) |
| **Use Case** | Admin accounts, platform staff | End users, customers, hosts |

**Important Notes:**
- **AUTH_USER** = Authentication account (Django built-in)
  - Used for login credentials
  - Manages admin/staff permissions
  - Not all AUTH_USER records have USER_PROFILE
  
- **USER_PROFILE** = Customer profile data
  - Represents actual platform users/customers
  - Contains customer-facing information
  - Extends AUTH_USER with business-specific data

---

## **13. DEPLOYMENT & MIGRATION STATUS**

✅ **All Migrations Applied**
✅ **All Models Created**
✅ **All Relationships Configured**
✅ **All Indexes Created**
✅ **Production Ready**

---

This documentation is **complete, self-explanatory, and production-ready**. It serves as the single source of truth for the Loopin Backend database schema.
