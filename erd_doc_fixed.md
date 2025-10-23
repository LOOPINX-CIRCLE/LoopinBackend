# Event Hosting Backend Database Documentation

This markdown file includes the **Mermaid ERD** of the event hosting backend with all tables, fields, relationships, and descriptions. It can be rendered directly on GitHub or any markdown viewer that supports Mermaid.

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'primaryColor':'#e3f2fd','primaryTextColor':'#1565c0','primaryBorderColor':'#1976d2','lineColor':'#42a5f5','secondaryColor':'#f3e5f5','tertiaryColor':'#e8f5e9','background':'#ffffff','mainBkg':'#ffffff','secondBkg':'#f5f5f5','tertiaryBkg':'#ffffff'}}}%%
erDiagram
    %% -------------------- USERS (Blue Theme) --------------------
    AUTH_USER ||--|| USER_PROFILE : "1-to-1 has profile"
    USER_PROFILE ||--o{ USER_PROFILE_EVENT_INTERESTS : "1-to-many user interests"
    USER_PROFILE_EVENT_INTERESTS ||--|| EVENT_INTEREST : "many-to-many interest mapping"
    USER_PHONE_OTP ||--|| AUTH_USER : "1-to-1 OTP verification"

    %% -------------------- EVENTS (Green Theme) --------------------
    AUTH_USER ||--o{ EVENT : "1 host can create many events"
    EVENT ||--o{ EVENT_INTEREST_MAP : "event categorized by multiple interests"
    EVENT_INTEREST ||--o{ EVENT_INTEREST_MAP : "many-to-many mapping"
    EVENT ||--o{ EVENT_REQUEST : "users send requests to join event"
    AUTH_USER ||--o{ EVENT_REQUEST : "1 user can request many events"
    EVENT ||--o{ EVENT_INVITE : "host can invite multiple users"
    AUTH_USER ||--o{ EVENT_INVITE : "users can receive many invites"
    EVENT ||--o{ EVENT_ATTENDEE : "event has attendees after approval/payment"
    EVENT_ATTENDEE ||--|| TICKET_SECRET : "each attendee has one secret ticket"
    EVENT ||--o{ CAPACITY_RESERVATION : "temporary holds for paid/free events"
    AUTH_USER ||--o{ CAPACITY_RESERVATION : "user can have multiple reservations"
    EVENT ||--o{ EVENT_IMAGE : "event can have multiple images"
    VENUE ||--o{ EVENT : "venue hosts multiple events"

    %% -------------------- PAYMENTS (Orange Theme) --------------------
    AUTH_USER ||--o{ PAYMENT_ORDER : "user can have many orders"
    EVENT ||--o{ PAYMENT_ORDER : "orders can be tied to events"

    %% -------------------- NOTIFICATIONS & AUDIT (Purple Theme) --------------------
    AUTH_USER ||--o{ NOTIFICATION : "user receives many notifications"
    AUTH_USER ||--o{ AUDIT_LOG : "user can be actor of many logs"

    %% -------------------- TABLE DEFINITIONS --------------------
    %% All tables include created_at and updated_at

    %% Color Definitions for Table Categories
    classDef userTables fill:#e3f2fd,stroke:#1976d2,stroke-width:2px,color:#1565c0
    classDef eventTables fill:#e8f5e9,stroke:#388e3c,stroke-width:2px,color:#2e7d32
    classDef paymentTables fill:#fff3e0,stroke:#f57c00,stroke-width:2px,color:#e65100
    classDef systemTables fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#6a1b9a
    classDef junctionTables fill:#f5f5f5,stroke:#616161,stroke-width:2px,color:#424242

    AUTH_USER {
        BIGINT id PK "Primary key"
        UUID uuid "Public UUID"
        STRING username "Phone number used for login"
        STRING password "Hashed password"
        BOOLEAN is_active
        BOOLEAN is_staff
        BOOLEAN is_superuser
        DATETIME date_joined
        DATETIME last_login
        DATETIME created_at
        DATETIME updated_at
    }

    USER_PROFILE {
        BIGINT id PK
        BIGINT user_id FK "FK to AUTH_USER.id"
        UUID uuid "Public UUID"
        STRING name "Full name"
        STRING phone_number "Copy of auth_user.username"
        TEXT bio "User biography"
        STRING location "City/location"
        DATE birth_date
        STRING gender
        JSONB profile_pictures "Array of 1-6 picture URLs"
        BOOLEAN is_verified
        BOOLEAN is_active
        DATETIME created_at
        DATETIME updated_at
    }

    USER_PHONE_OTP {
        BIGINT id PK
        STRING phone_number "Phone number for OTP"
        TEXT otp_hash "Hashed OTP"
        TEXT otp_salt "Salt for hashing"
        BOOLEAN is_verified
        INT attempts
        DATETIME created_at
        DATETIME updated_at
        DATETIME expires_at
    }

    EVENT_INTEREST {
        BIGINT id PK
        STRING name "Interest name (e.g., Music, Travel)"
        STRING slug "URL-friendly slug"
        TEXT description
        BOOLEAN is_active
        DATETIME created_at
        DATETIME updated_at
    }

    USER_PROFILE_EVENT_INTERESTS {
        BIGINT id PK
        BIGINT userprofile_id FK "FK to USER_PROFILE"
        BIGINT eventinterest_id FK "FK to EVENT_INTEREST"
        DATETIME created_at
        DATETIME updated_at
    }

    VENUE {
        BIGINT id PK
        UUID uuid
        STRING name
        TEXT address
        NUMERIC latitude
        NUMERIC longitude
        JSONB metadata "Extra info, accessibility, capacity hints"
        DATETIME created_at
        DATETIME updated_at
    }

    EVENT {
        BIGINT id PK
        UUID uuid
        BIGINT host_user_id FK
        STRING title
        STRING slug
        STRING mood "Party, Picnic, Travel etc."
        TEXT description
        BIGINT venue_id FK
        STRING venue_text "Custom venue if not in VENUE table"
        DATE event_date
        TIME start_time
        STRING duration
        INT capacity
        BOOLEAN is_paid
        NUMERIC ticket_price
        STRING gst_number
        NUMERIC gst_percent
        BOOLEAN allow_plus_one
        STRING allowed_genders "all, male, female, non-binary"
        JSONB cover_images "Array of 1-3 URLs"
        BOOLEAN is_published
        BOOLEAN is_active
        INT going_count
        INT requests_count
        DATETIME created_at
        DATETIME updated_at
    }

    EVENT_INTEREST_MAP {
        BIGINT id PK
        BIGINT event_id FK
        BIGINT eventinterest_id FK
        DATETIME created_at
        DATETIME updated_at
    }

    EVENT_REQUEST {
        BIGINT id PK
        UUID uuid
        BIGINT event_id FK
        BIGINT requester_user_id FK
        TEXT message
        STRING status "pending, accepted, declined, cancelled"
        TEXT host_message
        INT seats_requested
        DATETIME created_at
        DATETIME updated_at
    }

    EVENT_INVITE {
        BIGINT id PK
        UUID uuid
        BIGINT event_id FK
        BIGINT host_user_id FK
        BIGINT invited_user_id FK
        STRING status "pending, accepted, declined"
        TEXT message
        STRING invite_type "direct, share_link"
        DATETIME expires_at
        DATETIME created_at
        DATETIME updated_at
    }

    CAPACITY_RESERVATION {
        BIGINT id PK
        UUID reservation_key
        BIGINT event_id FK
        BIGINT user_id FK
        INT seats_reserved
        BOOLEAN consumed
        DATETIME expires_at
        DATETIME created_at
        DATETIME updated_at
    }

    EVENT_ATTENDEE {
        BIGINT id PK
        UUID uuid
        BIGINT event_id FK
        BIGINT user_id FK
        BIGINT request_id FK
        STRING ticket_type "standard, VIP etc."
        INT seats
        BOOLEAN is_paid
        NUMERIC price_paid
        NUMERIC platform_fee
        STRING status "going, not_going, checked_in, cancelled"
        DATETIME checked_in_at
        DATETIME created_at
        DATETIME updated_at
    }

    TICKET_SECRET {
        BIGINT id PK
        BIGINT ticket_id FK
        TEXT secret_hash
        TEXT secret_salt
        BOOLEAN is_redeemed
        DATETIME redeemed_at
        DATETIME created_at
        DATETIME updated_at
    }

    PAYMENT_ORDER {
        BIGINT id PK
        UUID uuid
        STRING order_reference
        BIGINT user_id FK
        BIGINT event_id FK
        NUMERIC amount
        STRING currency
        STRING payment_provider
        STRING provider_payment_id
        JSONB provider_response
        STRING status "created, paid, failed, refunded"
        DATETIME created_at
        DATETIME updated_at
    }

    NOTIFICATION {
        BIGINT id PK
        UUID uuid
        BIGINT recipient_user_id FK
        BIGINT sender_user_id FK
        STRING type "event_request, event_invite, system"
        STRING title
        TEXT message
        STRING reference_type
        BIGINT reference_id
        BOOLEAN is_read
        JSONB metadata
        DATETIME created_at
        DATETIME updated_at
    }

    AUDIT_LOG {
        BIGINT id PK
        BIGINT actor_user_id FK
        STRING object_type
        BIGINT object_id
        STRING action "create, update, delete"
        JSONB payload "Snapshot of data changed"
        DATETIME created_at
        DATETIME updated_at
    }

    EVENT_IMAGE {
        BIGINT id PK
        BIGINT event_id FK
        TEXT image_url
        INT position
        DATETIME created_at
        DATETIME updated_at
    }

    %% Apply Color Classes to Tables
    class AUTH_USER,USER_PROFILE,USER_PHONE_OTP userTables
    class EVENT,EVENT_INTEREST,EVENT_REQUEST,EVENT_INVITE,EVENT_ATTENDEE,EVENT_IMAGE,VENUE eventTables
    class PAYMENT_ORDER,TICKET_SECRET,CAPACITY_RESERVATION paymentTables
    class NOTIFICATION,AUDIT_LOG systemTables
    class USER_PROFILE_EVENT_INTERESTS,EVENT_INTEREST_MAP junctionTables
```

---

## 📚 **Event Hosting Backend Database Documentation**

### **1. Overview**

This database is designed to power a phone application for hosting and attending events. It supports:

- **User registration and verification** via phone/OTP
- **Detailed user profiles** with interests and preferences
- **Event hosting** with rich information (mood, type, location, capacity, paid/free, etc.)
- **Event attendance workflow**: requests, invites, approvals, reservations, payments, ticketing
- **Notifications and audit tracking**
- **Scalable, secure, maintainable, normalized schema** with extendability for future features

The database is implemented in **PostgreSQL** and designed to work seamlessly with **Django ORM** for model management and **FastAPI** for REST API endpoints.

---

### **2. Core Entities**

#### **2.1 Users**
**Tables:** `AUTH_USER`, `USER_PROFILE`, `USER_PHONE_OTP`, `USER_PROFILE_EVENT_INTERESTS`

##### **2.1.1 AUTH_USER**
- **Purpose:** Core authentication table (Django built-in)
- **Logic:** Stores user credentials and basic status flags. Every user has a record here
- **Key fields:**
  - `id`: Internal primary key
  - `uuid`: Public UUID for external references
  - `username`: Phone number used to login (unique)
  - `password`: Hashed password (not used for OTP-only users)
  - `is_active`, `is_staff`, `is_superuser`: User status flags
  - `date_joined`, `last_login`, `created_at`, `updated_at`: For auditing and tracking activity
- **Relationships:**
  - 1-to-1 with `USER_PROFILE` (every user has exactly one profile)
  - 1-to-many with `EVENT` (user can host multiple events)
  - 1-to-many with `EVENT_REQUEST`, `EVENT_INVITE`, `PAYMENT_ORDER`, `NOTIFICATION` (user actions and system communications)

##### **2.1.2 USER_PROFILE**
- **Purpose:** Extended profile information beyond authentication
- **Logic:** Separates personal info from credentials for security and modularity
- **Key fields:**
  - `name`, `phone_number`, `bio`, `location`, `birth_date`, `gender`
  - `profile_pictures`: JSON array of 1–6 pictures
  - `is_verified`: Indicates OTP verification success
  - `is_active`: Profile active status
  - `metadata`: Flexible JSON for future extensibility
  - `created_at`, `updated_at`: Track profile lifecycle
- **Relationships:**
  - 1-to-1 with `AUTH_USER`
  - M-to-M with `EVENT_INTEREST` via `USER_PROFILE_EVENT_INTERESTS` (users can have multiple interests)

##### **2.1.3 USER_PHONE_OTP**
- **Purpose:** OTP verification system for secure phone-based login
- **Logic:** Stores hashed OTPs and their expiry
- **Key fields:**
  - `otp_hash`, `otp_salt`: Securely store OTP
  - `is_verified`, `attempts`: Track success/failure and prevent brute force
  - `expires_at`: Ensures time-limited verification
- **Relationships:**
  - 1-to-1 with `AUTH_USER` (each OTP is tied to a phone/user)

##### **2.1.4 USER_PROFILE_EVENT_INTERESTS**
- **Purpose:** Map user profiles to their interests
- **Logic:** Many-to-many mapping so a user can have multiple interests (Music, Travel, Parties) and each interest can be associated with multiple users
- **Key fields:** `userprofile_id`, `eventinterest_id`
- **Relationships:**
  - M-to-M between `USER_PROFILE` and `EVENT_INTEREST`

#### **2.2 Event Interests**
**Table:** `EVENT_INTEREST`
- **Purpose:** Master list of event types or categories
- **Logic:** Standardizes event tagging; supports filtering and recommendations
- **Key fields:**
  - `name`, `slug`, `description`, `is_active`
  - `created_at`, `updated_at`: Track changes to interests
- **Relationships:**
  - M-to-M with `USER_PROFILE` via `USER_PROFILE_EVENT_INTERESTS`
  - M-to-M with `EVENT` via `EVENT_INTEREST_MAP`

#### **2.3 Venues**
**Table:** `VENUE`
- **Purpose:** Stores physical locations for events
- **Logic:** Centralized venue info allows multiple events at the same venue
- **Key fields:**
  - `name`, `address`, `latitude`, `longitude`
  - `metadata`: Extra info (accessibility, indoor/outdoor, hints)
  - `created_at`, `updated_at`
- **Relationships:**
  - 1-to-many with `EVENT` (a venue can host multiple events)

#### **2.4 Events**
**Table:** `EVENT`
- **Purpose:** Central table representing events hosted by users
- **Logic:** Contains everything a host provides: title, description, type, date/time, capacity, pricing, images, guest rules
- **Key fields:**
  - `host_user_id`: Links to host
  - `title`, `slug`, `mood`, `description`
  - `venue_id` / `venue_text`
  - `event_date`, `start_time`, `duration`
  - `capacity`, `allow_plus_one`, `allowed_genders`
  - `is_paid`, `ticket_price`, `gst_number`, `gst_percent`
  - `cover_images` (JSON array)
  - `is_published`, `is_active`
  - **Counters:** `going_count`, `requests_count` (performance optimization for quick reads)
  - `created_at`, `updated_at`
- **Relationships:**
  - 1-to-many: `EVENT_IMAGE`, `EVENT_REQUEST`, `EVENT_INVITE`, `EVENT_ATTENDEE`, `CAPACITY_RESERVATION`, `PAYMENT_ORDER`
  - M-to-M: `EVENT_INTEREST_MAP` (event can belong to multiple interests)
  - Many-to-one: `VENUE`

#### **2.5 Event Interests Mapping**
**Table:** `EVENT_INTEREST_MAP`
- **Purpose:** Connect events to multiple categories
- **Logic:** Enables searching/filtering by interest type
- **Fields:** `event_id`, `eventinterest_id`, `created_at`, `updated_at`
- **Relationships:**
  - M-to-M between `EVENT` and `EVENT_INTEREST`

#### **2.6 Event Requests**
**Table:** `EVENT_REQUEST`
- **Purpose:** Users request to join an event
- **Logic:** Host reviews request; allows approval/decline
- **Fields:** `event_id`, `requester_user_id`, `message`, `status`, `host_message`, `seats_requested`, `created_at`, `updated_at`
- **Relationships:**
  - Many-to-one: `EVENT` and `AUTH_USER`
  - 1-to-1 optional: `EVENT_ATTENDEE` if request converts to attendance

#### **2.7 Event Invites**
**Table:** `EVENT_INVITE`
- **Purpose:** Hosts can directly invite users
- **Logic:** Supports multiple invite types: direct, shareable link
- **Fields:** `host_user_id`, `invited_user_id`, `status`, `message`, `invite_type`, `expires_at`, `created_at`, `updated_at`
- **Relationships:**
  - Many-to-one: `EVENT`, `AUTH_USER`
  - 1-to-many: Users can receive multiple invites

#### **2.8 Capacity Reservations**
**Table:** `CAPACITY_RESERVATION`
- **Purpose:** Temporary holds on event seats before payment confirmation
- **Logic:** Prevents overbooking for paid events
- **Fields:** `reservation_key`, `event_id`, `user_id`, `seats_reserved`, `consumed`, `expires_at`, `created_at`, `updated_at`
- **Relationships:**
  - Many-to-one: `EVENT`, `AUTH_USER`
  - Converts to `EVENT_ATTENDEE` after payment or approval

#### **2.9 Event Attendees**
**Table:** `EVENT_ATTENDEE`
- **Purpose:** Records final confirmed participants
- **Logic:** Tracks seat count, payment status, and attendance
- **Fields:** `event_id`, `user_id`, `request_id`, `ticket_type`, `seats`, `is_paid`, `price_paid`, `platform_fee`, `status`, `checked_in_at`, `created_at`, `updated_at`
- **Relationships:**
  - Many-to-one: `EVENT`, `AUTH_USER`
  - 1-to-1: `TICKET_SECRET`

#### **2.10 Ticket Secrets**
**Table:** `TICKET_SECRET`
- **Purpose:** Each attendee has a cryptographically secure ticket code
- **Logic:** Ensures ticket redemption cannot be forged
- **Fields:** `ticket_id`, `secret_hash`, `secret_salt`, `is_redeemed`, `redeemed_at`, `created_at`, `updated_at`
- **Relationships:**
  - 1-to-1 with `EVENT_ATTENDEE`

#### **2.11 Payments**
**Table:** `PAYMENT_ORDER`
- **Purpose:** Tracks all payment transactions
- **Logic:** Supports multiple payment providers and refunds
- **Fields:** `uuid`, `order_reference`, `user_id`, `event_id`, `amount`, `currency`, `payment_provider`, `provider_payment_id`, `provider_response`, `status`, `created_at`, `updated_at`
- **Relationships:**
  - Many-to-one: `AUTH_USER` (payer), `EVENT` (optional)

#### **2.12 Notifications**
**Table:** `NOTIFICATION`
- **Purpose:** In-app notifications for users
- **Logic:** Supports system messages, invites, requests, and reminders
- **Fields:** `recipient_user_id`, `sender_user_id`, `type`, `title`, `message`, `reference_type`, `reference_id`, `is_read`, `metadata`, `created_at`, `updated_at`

#### **2.13 Event Images**
**Table:** `EVENT_IMAGE`
- **Purpose:** Store multiple images for events
- **Fields:** `event_id`, `image_url`, `position`, `created_at`, `updated_at`
- **Relationships:**
  - Many-to-one: `EVENT`

#### **2.14 Audit Log**
**Table:** `AUDIT_LOG`
- **Purpose:** Immutable log of all changes for security, troubleshooting, and compliance
- **Fields:** `actor_user_id`, `object_type`, `object_id`, `action`, `payload`, `created_at`, `updated_at`
- **Logic:** Captures who did what, when, and what data changed
- **Relationships:** Actor links to `AUTH_USER`

---

### **3. Real-World Logic Behind Design**

#### **Separation of Authentication and Profile:**
- Credentials are sensitive; profile info may be public
- Supports flexible future login methods (social, OTP, passwordless)

#### **Normalization & Junction Tables:**
- `USER_PROFILE_EVENT_INTERESTS` and `EVENT_INTEREST_MAP` prevent duplication and allow many-to-many mappings efficiently

#### **Event Lifecycle:**
Host creates event → users request/are invited → host approves → capacity reserved → payment processed → attendee confirmed → ticket generated → check-in tracked

#### **Scalability:**
- JSONB fields (`cover_images`, `metadata`) support dynamic properties without schema changes
- Counters (`going_count`, `requests_count`) support fast read-heavy queries

#### **Security & Audit:**
- OTP verification, hashed ticket secrets, audit log for all actions

#### **Payment & Reservations:**
- Supports free and paid events
- Platform fees tracked separately for revenue reporting

---

### **4. Relationship Summary**

| Relationship Type | Tables Involved | Description |
|------------------|-----------------|-------------|
| **1-to-1** | `AUTH_USER` → `USER_PROFILE` | Each user has one profile |
| **1-to-many** | `AUTH_USER` → `EVENT` | Host can create multiple events |
| **1-to-many** | `EVENT` → `EVENT_REQUEST` | Event receives multiple join requests |
| **1-to-many** | `EVENT` → `EVENT_INVITE` | Host can invite multiple users |
| **1-to-many** | `EVENT` → `EVENT_ATTENDEE` | Tracks confirmed participants |
| **1-to-many** | `EVENT` → `CAPACITY_RESERVATION` | Temporary holds for seat reservation |
| **M-to-M** | `USER_PROFILE` ↔ `EVENT_INTEREST` | Users have multiple interests |
| **M-to-M** | `EVENT` ↔ `EVENT_INTEREST` | Events can belong to multiple categories |
| **1-to-1** | `EVENT_ATTENDEE` → `TICKET_SECRET` | Each ticket has a unique secret |

---

This documentation can be presented to both technical and non-technical audiences, as it explains:
- The purpose of each table and field
- The logic behind business flows (requests, payments, attendance, ticketing)
- The relationships between entities
- Security, scalability, and auditability considerations
