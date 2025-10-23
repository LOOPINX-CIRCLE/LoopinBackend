# Event Hosting Backend Database Documentation

This markdown file includes the **Mermaid ERD** of the event hosting backend with all tables, fields, relationships, and descriptions. It can be rendered directly on GitHub or any markdown viewer that supports Mermaid.

```mermaid
erDiagram
    %% -------------------- USERS --------------------
    AUTH_USER ||--|| USER_PROFILE : "has"
    USER_PROFILE ||--o{ USER_PROFILE_EVENT_INTERESTS : "selects"
    USER_PROFILE_EVENT_INTERESTS }o--|| EVENT_INTEREST : "categorizes"
    USER_PHONE_OTP ||--o| AUTH_USER : "verifies"

    %% -------------------- EVENTS --------------------
    AUTH_USER ||--o{ EVENT : "hosts"
    EVENT ||--o{ EVENT_INTEREST_MAP : "categorized_by"
    EVENT_INTEREST ||--o{ EVENT_INTEREST_MAP : "categorizes"
    EVENT ||--o{ EVENT_REQUEST : "receives"
    AUTH_USER ||--o{ EVENT_REQUEST : "sends"
    EVENT ||--o{ EVENT_INVITE : "sends"
    AUTH_USER ||--o{ EVENT_INVITE : "receives"
    EVENT ||--o{ EVENT_ATTENDEE : "has"
    EVENT_ATTENDEE ||--|| TICKET_SECRET : "has"
    EVENT ||--o{ CAPACITY_RESERVATION : "reserves"
    AUTH_USER ||--o{ CAPACITY_RESERVATION : "holds"
    EVENT ||--o{ EVENT_IMAGE : "displays"
    VENUE ||--o{ EVENT : "hosts"

    %% -------------------- PAYMENTS --------------------
    AUTH_USER ||--o{ PAYMENT_ORDER : "places"
    EVENT ||--o{ PAYMENT_ORDER : "generates"

    %% -------------------- NOTIFICATIONS & AUDIT --------------------
    AUTH_USER ||--o{ NOTIFICATION : "receives"
    AUTH_USER ||--o{ AUDIT_LOG : "performs"

    %% -------------------- TABLE DEFINITIONS --------------------

    AUTH_USER {
        bigint id PK
        uuid uuid
        string username
        string password
        boolean is_active
        boolean is_staff
        boolean is_superuser
        datetime date_joined
        datetime last_login
        datetime created_at
        datetime updated_at
    }

    USER_PROFILE {
        bigint id PK
        bigint user_id FK
        uuid uuid
        string name
        string phone_number
        text bio
        string location
        date birth_date
        string gender
        jsonb profile_pictures
        boolean is_verified
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    USER_PHONE_OTP {
        bigint id PK
        string phone_number
        text otp_hash
        text otp_salt
        boolean is_verified
        int attempts
        datetime created_at
        datetime updated_at
        datetime expires_at
    }

    EVENT_INTEREST {
        bigint id PK
        string name
        string slug
        text description
        boolean is_active
        datetime created_at
        datetime updated_at
    }

    USER_PROFILE_EVENT_INTERESTS {
        bigint id PK
        bigint userprofile_id FK
        bigint eventinterest_id FK
        datetime created_at
        datetime updated_at
    }

    VENUE {
        bigint id PK
        uuid uuid
        string name
        text address
        numeric latitude
        numeric longitude
        jsonb metadata
        datetime created_at
        datetime updated_at
    }

    EVENT {
        bigint id PK
        uuid uuid
        bigint host_user_id FK
        string title
        string slug
        string mood
        text description
        bigint venue_id FK
        string venue_text
        date event_date
        time start_time
        string duration
        int capacity
        boolean is_paid
        numeric ticket_price
        string gst_number
        numeric gst_percent
        boolean allow_plus_one
        string allowed_genders
        jsonb cover_images
        boolean is_published
        boolean is_active
        int going_count
        int requests_count
        datetime created_at
        datetime updated_at
    }

    EVENT_INTEREST_MAP {
        bigint id PK
        bigint event_id FK
        bigint eventinterest_id FK
        datetime created_at
        datetime updated_at
    }

    EVENT_REQUEST {
        bigint id PK
        uuid uuid
        bigint event_id FK
        bigint requester_user_id FK
        text message
        string status
        text host_message
        int seats_requested
        datetime created_at
        datetime updated_at
    }

    EVENT_INVITE {
        bigint id PK
        uuid uuid
        bigint event_id FK
        bigint host_user_id FK
        bigint invited_user_id FK
        string status
        text message
        string invite_type
        datetime expires_at
        datetime created_at
        datetime updated_at
    }

    CAPACITY_RESERVATION {
        bigint id PK
        uuid reservation_key
        bigint event_id FK
        bigint user_id FK
        int seats_reserved
        boolean consumed
        datetime expires_at
        datetime created_at
        datetime updated_at
    }

    EVENT_ATTENDEE {
        bigint id PK
        uuid uuid
        bigint event_id FK
        bigint user_id FK
        bigint request_id FK
        string ticket_type
        int seats
        boolean is_paid
        numeric price_paid
        numeric platform_fee
        string status
        datetime checked_in_at
        datetime created_at
        datetime updated_at
    }

    TICKET_SECRET {
        bigint id PK
        bigint ticket_id FK
        text secret_hash
        text secret_salt
        boolean is_redeemed
        datetime redeemed_at
        datetime created_at
        datetime updated_at
    }

    PAYMENT_ORDER {
        bigint id PK
        uuid uuid
        string order_reference
        bigint user_id FK
        bigint event_id FK
        numeric amount
        string currency
        string payment_provider
        string provider_payment_id
        jsonb provider_response
        string status
        datetime created_at
        datetime updated_at
    }

    NOTIFICATION {
        bigint id PK
        uuid uuid
        bigint recipient_user_id FK
        bigint sender_user_id FK
        string type
        string title
        text message
        string reference_type
        bigint reference_id
        boolean is_read
        jsonb metadata
        datetime created_at
        datetime updated_at
    }

    AUDIT_LOG {
        bigint id PK
        bigint actor_user_id FK
        string object_type
        bigint object_id
        string action
        jsonb payload
        datetime created_at
        datetime updated_at
    }

    EVENT_IMAGE {
        bigint id PK
        bigint event_id FK
        text image_url
        int position
        datetime created_at
        datetime updated_at
    }
```
