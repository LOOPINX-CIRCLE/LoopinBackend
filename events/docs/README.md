# Events Module Documentation

## Overview
The Events module handles event creation, management, and user interactions within the Loopin platform. The API uses FastAPI for modern, async REST endpoints with comprehensive validation and business logic.

---

## Architecture

### Project Structure
```
events/
├── admin.py              # Django admin configuration
├── apps.py               # App configuration
├── models.py             # Database models
├── schemas.py            # Pydantic validation schemas (FastAPI)
├── services.py           # Business logic services
├── serializers/          # DRF serializers (legacy, unused)
│   ├── __init__.py
│   └── event_serializers.py
├── views/                # Django REST views (legacy, unused)
│   ├── __init__.py
│   └── event_views.py
├── tests/                # Test suite
│   ├── __init__.py
│   ├── README.md
│   └── test_events.py
├── migrations/           # Database migrations
├── docs/                 # Documentation
│   └── README.md
└── __init__.py          # Package initialization
```

### API Architecture
- **Framework**: FastAPI with async/await support
- **Validation**: Pydantic v2 schemas
- **Database**: Django ORM with sync_to_async
- **Authentication**: JWT tokens via `/api/auth/login`
- **Router Location**: `api/routers/events.py`

---

## System Flow Diagrams

### Event Hosting Lifecycle

```mermaid
graph TD
    Start([User Wants to Host Event]) --> GetInterests[Fetch Event Interests<br/>GET /api/auth/event-interests]
    GetInterests --> GetVenues[Fetch Available Venues<br/>GET /api/events/venues]
    GetVenues --> CreateEvent[Fill Event Details<br/>POST /api/events]
    
    CreateEvent --> VenueDecision{Venue Option?}
    
    VenueDecision -->|Existing| VenueID[Use venue_id]
    VenueDecision -->|New| VenueCreate[Auto-create venue]
    VenueDecision -->|Custom| VenueText[Use venue_text]
    
    VenueID --> Validate[Validate All Fields]
    VenueCreate --> Validate
    VenueText --> Validate
    
    Validate --> CalcDuration[Calculate end_time<br/>from duration_hours]
    CalcDuration --> CreateDB[Create Event in DB<br/>Atomic Transaction]
    CreateDB --> LinkInterests[Link Event Interests<br/>via EventInterestMap]
    LinkInterests --> ReturnEvent[Return EventResponse<br/>with all relationships]
    
    ReturnEvent --> Published{Status?}
    Published -->|draft| DraftMode[Draft Saved<br/>Not Visible Publicly]
    Published -->|published| LiveMode[Event Live<br/>Visible to All]
    
    LiveMode --> EventManagement[Event Management<br/>Updates/Deletes/Bulk Ops]
    DraftMode --> EventManagement
    
    EventManagement --> End([Event Created])
    
    style Start fill:#e1f5fe
    style Validate fill:#fff3e0
    style CreateDB fill:#e8f5e9
    style LiveMode fill:#c8e6c9
    style DraftMode fill:#ffecb3
    style End fill:#e1f5fe
```

### Event Request Workflow

```mermaid
sequenceDiagram
    participant User
    participant API
    participant DB
    participant Host
    
    User->>API: POST /events/{id}/requests<br/>{event_id, message, seats}
    API->>API: Validate JWT Token
    API->>DB: Check if user has pending request
    DB-->>API: No existing request ✓
    
    API->>DB: Create EventRequest<br/>(status: pending)
    DB-->>API: Request created
    
    API->>DB: Increment event.requests_count
    DB-->>API: Count updated
    
    API-->>User: Return EventRequestResponse
    
    Note over Host: Host sees notification
    
    Host->>API: GET /events/{id}/requests
    API->>DB: Fetch all pending requests
    DB-->>API: List of requests
    API-->>Host: Request list
    
    Host->>API: PUT /events/{id}/requests/{req_id}<br/>{status: accepted/declined}
    API->>DB: Update request status
    DB-->>API: Updated
    
    alt Accepted
        API->>DB: Create EventAttendee<br/>(status: going)
        DB-->>API: Attendee created
        API->>DB: Increment event.going_count
        API->>DB: Decrement event.requests_count
    else Declined
        API->>DB: Decrement event.requests_count
    end
    
    API-->>Host: Response updated
    API->>User: Notification sent
```

### Venue Management Flow

```mermaid
flowchart LR
    subgraph "Venue Discovery"
        A[User Opens Event Hosting Form] --> B[GET /api/events/venues]
        B --> C{Filter Venues?}
        C -->|By City| D[Query: city=Mumbai]
        C -->|By Type| E[Query: venue_type=indoor]
        C -->|No Filter| F[Get All Active Venues]
        D --> G[Display Venue List]
        E --> G
        F --> G
    end
    
    subgraph "Event Creation"
        G --> H{User Choice?}
        H -->|Select Existing| I[Use venue_id in EventCreate]
        H -->|Not in List| J[Provide venue_create details]
        H -->|Custom Location| K[Provide venue_text]
        
        I --> L[POST /api/events<br/>with venue_id]
        J --> M[POST /api/events<br/>with venue_create]
        K --> N[POST /api/events<br/>with venue_text]
    end
    
    subgraph "Venue Reference Creation"
        M --> O[Auto-create Venue Record<br/>Reference Data Only]
        O --> P[Link to Event via FK]
        P --> Q[Venue Available for<br/>Other Events Simultaneously]
    end
    
    L --> R[Event Created ✓<br/>No Booking Conflicts]
    P --> R
    N --> R
    
    style A fill:#e3f2fd
    style G fill:#fff3e0
    style O fill:#e8f5e9
    style R fill:#c8e6c9
    style Q fill:#fff9c4
```

**Note**: Venues are reference data only—the platform does not manage physical venue bookings. Multiple events can use the same venue simultaneously without conflicts. Event capacity is controlled by `Event.max_capacity`, not the venue's capacity field.

### Soft Delete & Visibility Rules

```mermaid
stateDiagram-v2
    [*] --> Active
    
    Active --> Published: Publish Event
    Active --> Draft: Save as Draft
    Draft --> Published: Publish
    Published --> Deleted: Host Deletes
    
    note right of Active
        Visible to:
        - Event host (always)
        - Public list (if published)
    end note
    
    note right of Deleted
        Visible ONLY to:
        - Event host
    end note
    
    note right of Published
        Visible to:
        - All authenticated users
        - Host (always)
    end note
```

### Authentication & Authorization Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant JWT
    participant DB
    participant Business Logic
    
    Note over Client,DB: READ Operations (GET)
    
    Client->>FastAPI: GET /api/events/{id}<br/>(No Auth)
    FastAPI->>JWT: Extract Token from Header
    JWT-->>FastAPI: Invalid/No Token
    FastAPI-->>Client: HTTP 403: Not authenticated
    
    Client->>FastAPI: GET /api/events/{id}<br/>(With JWT)
    FastAPI->>JWT: Verify Token
    JWT->>DB: Validate User Exists
    DB-->>JWT: User Valid ✓
    JWT-->>FastAPI: User Object
    
    FastAPI->>Business Logic: Check Permissions
    Business Logic->>DB: Fetch Event
    
    Business Logic->>Business Logic: Check Visibility<br/>(public/private/deleted)
    
    alt Public Event
        Business Logic-->>FastAPI: Return Event
        FastAPI-->>Client: HTTP 200 + EventResponse
    else Private Event & Not Host
        Business Logic-->>FastAPI: Access Denied
        FastAPI-->>Client: HTTP 403: No permission
    else Deleted Event & Not Host
        Business Logic-->>FastAPI: Not Found
        FastAPI-->>Client: HTTP 404: Event not found
    end
```

---

## Models

### Venue
- **Purpose**: Reference data for physical locations to avoid duplicating location details
- **Key Fields**: uuid, name, address, city, venue_type, capacity, latitude, longitude, metadata
- **Relationships**: One-to-many with Event
- **Soft Delete**: is_active flag
- **Important Notes**:
  - The platform does **not** create or manage physical venues—venues are reference data only
  - The `capacity` field in Venue is informational only; the actual capacity for an event is stored in `Event.max_capacity`
  - Multiple events can use the same venue simultaneously—there are no booking restrictions or conflicts
  - The venue table exists solely to avoid duplicating location details when multiple events share the same physical location

### Event
- **Purpose**: Core event model with comprehensive hosting features
- **Key Fields**: 
  - Identity: uuid, slug, title, description
  - Scheduling: start_time, end_time (derived from duration_hours)
  - Venue: venue (FK) or venue_text
  - Capacity & Pricing: max_capacity, going_count, requests_count, is_paid, ticket_price, gst_number
  - Restrictions: allowed_genders, allow_plus_one
  - Media: cover_images (1-3 URLs)
  - Status: status, is_public, is_active
- **Status Options**: draft, published, cancelled, completed, postponed
- **Gender Options**: all, male, female, non_binary
- **Relationships**: 
  - Many-to-one with User (host)
  - Many-to-one with Venue
  - Many-to-many with EventInterest (via EventInterestMap)
  - One-to-many with EventRequest, EventInvite, EventAttendee

### EventInterestMap
- **Purpose**: Many-to-many mapping between events and interests
- **Key Fields**: event, event_interest, created_at, updated_at
- **Note**: Timestamps on M2M for analytics tracking

### EventRequest
- **Purpose**: User requests to join events with approval workflow
- **Key Fields**: uuid, event, requester, status, message, host_message, seats_requested
- **Status Options**: pending, accepted, declined, cancelled, expired
- **Business Rules**: One pending request per user per event

### EventInvite
- **Purpose**: Host invitations to users with expiration handling
- **Key Fields**: uuid, event, host, invited_user, status, invite_type, message, expires_at
- **Status Options**: pending, accepted, declined, expired
- **Invite Types**: direct, share_link

### EventAttendee
- **Purpose**: Tracking event attendees and their payment/check-in status
- **Key Fields**: uuid, event, user, request, status, ticket_type, seats, is_paid, price_paid, platform_fee, checked_in_at
- **Ticket Types**: standard, vip, early_bird, premium, general, group, couple, family, student, senior_citizen, disabled, other (default: general)
- **Status Options**: going, not_going, maybe, checked_in, cancelled

### CapacityReservation
- **Purpose**: Temporary holds on event seats during payment process
- **Key Fields**: reservation_key, event, user, seats_reserved, consumed, expires_at

---

## FastAPI Endpoints

### Event Operations

**POST** `/api/events`
- Create new event with all ERD fields
- **Auth**: Required (JWT)
- **Venue Options**:
  - `venue_id`: Use existing venue
  - `venue_create`: Auto-create venue inline
  - `venue_text`: Custom venue text
- **Duration**: Uses `duration_hours` (float) - automatically calculates end_time
- **Returns**: EventResponse with all relationships

**GET** `/api/events`
- List events with filtering, search, and pagination
- **Query Params**: host_id, venue_id, status, is_public, is_paid, allowed_genders, event_interest_id, search, offset, limit
- **Auth**: Required (JWT)
- **Returns**: Paginated list with total count

**GET** `/api/events/{event_id}`
- Get event details by ID
- **Auth**: Required (JWT)
- **Permissions**: Public events visible to all, private to host only
- **Returns**: EventResponse with all fields

**PUT** `/api/events/{event_id}`
- Update event fields
- **Auth**: Required (JWT)
- **Permission**: Event host or admin only
- **Returns**: Updated EventResponse

**DELETE** `/api/events/{event_id}`
- Soft delete event (sets is_active=False)
- **Auth**: Required (JWT)
- **Permission**: Event host or admin only
- **Returns**: HTTP 204 No Content

### Venue Operations

**GET** `/api/events/venues`
- List venues with filtering
- **Query Params**: city, venue_type, offset, limit
- **Auth**: Required (JWT)
- **Returns**: Paginated venue list

**POST** `/api/events/venues`
- Create new venue (admin/host only)
- **Auth**: Required (JWT)
- **Returns**: VenueResponse

**GET** `/api/events/venues/{venue_id}`
- Get venue by ID
- **Auth**: Required (JWT)
- **Returns**: VenueResponse

### Request Operations

**GET** `/api/events/{event_id}/requests`
- List requests for an event (host only)
- **Auth**: Required (JWT)
- **Permission**: Event host only
- **Returns**: List of EventRequestResponse

**POST** `/api/events/{event_id}/requests`
- Submit request to join event
- **Auth**: Required (JWT)
- **Returns**: EventRequestResponse

**PUT** `/api/events/{event_id}/requests/{request_id}`
- Approve/decline request
- **Auth**: Required (JWT)
- **Permission**: Event host only
- **Returns**: EventRequestResponse

---

## Event Creation Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Pydantic as Pydantic Validator
    participant Business as Business Logic
    participant DB as PostgreSQL
    participant Redis
    
    Client->>FastAPI: POST /api/events<br/>(JWT + EventCreate)
    
    FastAPI->>FastAPI: Verify JWT Token
    FastAPI->>Pydantic: Validate EventCreate Schema
    
    Pydantic->>Pydantic: Validate duration_hours > 0
    Pydantic->>Pydantic: Validate only ONE venue option
    Pydantic->>Pydantic: Validate cover_images count
    
    alt Validation Fails
        Pydantic-->>Client: 422 ValidationError
    else Validation Passes
        Pydantic-->>FastAPI: Valid EventCreate
    end
    
    FastAPI->>FastAPI: Calculate end_time<br/>start + duration_hours
    
    alt Venue Auto-Creation
        FastAPI->>Business: create_venue(venue_create)
        Business->>DB: INSERT INTO venues
        DB-->>Business: Venue created (ID)
        Business-->>FastAPI: Venue Object
    else Existing Venue
        FastAPI->>DB: Verify venue_id exists
        DB-->>FastAPI: Venue found ✓
    end
    
    FastAPI->>Business: create_event_with_relationships()
    
    Business->>DB: BEGIN TRANSACTION
    
    Business->>DB: INSERT INTO events<br/>(all fields + calculated end_time)
    DB-->>Business: Event created (ID)
    
    loop For each event_interest_id
        Business->>DB: INSERT INTO event_interest_map<br/>(event_id, interest_id)
    end
    
    Business->>DB: COMMIT TRANSACTION
    
    DB-->>Business: Transaction completed
    Business-->>FastAPI: Event Object
    
    FastAPI->>Redis: Cache event (optional)
    
    FastAPI->>FastAPI: Refresh with relationships<br/>(prefetch interests)
    
    FastAPI->>FastAPI: EventResponse.from_orm()<br/>(use _prefetched_objects_cache)
    
    FastAPI-->>Client: HTTP 201 + EventResponse<br/>(all fields + relationships)
```

---

## Pydantic Schemas

All schemas are in `events/schemas.py`:

### Request Schemas
- `EventCreate`: Create event with duration_hours, venue options, all ERD fields
- `EventUpdate`: Partial event updates
- `VenueCreate`: Venue creation
- `VenueUpdate`: Venue updates
- `EventRequestSubmit`: Submit request to event
- `EventInviteCreate`: Create invitation

### Response Schemas
- `EventResponse`: Full event with all relationships
- `VenueResponse`: Venue details
- `EventRequestResponse`: Request details
- `EventInviteResponse`: Invite details
- `EventAttendeeResponse`: Attendee details
- `PaginatedResponse`: Generic pagination wrapper

### Validation Features
- `model_validator`: Cross-field validation (venue options)
- `field_validator`: Individual field validation
- `from_orm`: ORM-to-Pydantic conversion with prefetch support

---

## Business Logic

### Event Creation Workflow
```mermaid
flowchart TD
    Start[User Submits Event Details] --> Validate[Validate Duration > 0]
    Validate --> CalcEnd[Calculate end_time<br/>start + duration_hours]
    
    CalcEnd --> VenueCheck{Venue Option?}
    
    VenueCheck -->|venue_id| VerifyVenue[Verify Venue Exists]
    VenueCheck -->|venue_create| CreateVenue[Auto-Create Venue]
    VenueCheck -->|venue_text| SetText[Set venue_text]
    
    VerifyVenue --> Begin[Begin Atomic Transaction]
    CreateVenue --> Begin
    SetText --> Begin
    
    Begin --> CreateEvent[INSERT INTO events]
    CreateEvent --> LinkInterests{Has Interests?}
    
    LinkInterests -->|Yes| LoopInterests[Loop: Link Each Interest<br/>INSERT INTO event_interest_map]
    LinkInterests -->|No| CommitTrans[COMMIT Transaction]
    
    LoopInterests --> CommitTrans
    CommitTrans --> Refresh[Refresh Event with Relationships]
    Refresh --> Prefetch[Prefetch Interests Cache]
    Prefetch --> Serialize[EventResponse.from_orm]
    Serialize --> Return[Return to Client]
    
    style Start fill:#e3f2fd
    style Validate fill:#fff3e0
    style Begin fill:#ffebee
    style CommitTrans fill:#e8f5e9
    style Return fill:#c8e6c9
```

### Venue Management Pattern
```mermaid
graph LR
    subgraph "Venue Options (Mutually Exclusive)"
        A[venue_id] --> B[Use Existing Reference]
        C[venue_create] --> D[Create New Reference]
        E[venue_text] --> F[Custom Text Only]
    end
    
    subgraph "Validator Logic"
        G[Model Validator] --> H{Count Provided?}
        H -->|0| I[Error: No venue]
        H -->|1| J[✓ Proceed]
        H -->|2+| K[Error: Multiple venues]
    end
    
    subgraph "Database"
        B --> L[(VENUE TABLE<br/>Reference Data Only)]
        D --> M[INSERT INTO venues<br/>No Physical Booking]
        M --> L
        F --> N[Event record only<br/>No venue reference]
    end
    
    subgraph "Important Notes"
        O[Multiple Events<br/>Can Use Same Venue]
        P[No Booking Conflicts]
        Q[Event.max_capacity<br/>Controls Capacity]
    end
    
    L --> O
    O --> P
    P --> Q
    
    style I fill:#ffcdd2
    style K fill:#ffcdd2
    style J fill:#c8e6c9
    style L fill:#e1f5fe
    style O fill:#fff9c4
    style P fill:#fff9c4
    style Q fill:#fff9c4
```

**Key Points**:
- Venues are **reference data only**—the platform does not create or manage physical venues
- The venue table exists to avoid duplicating location details when multiple events share the same location
- Multiple events can reference the same venue simultaneously without any booking restrictions
- Event capacity is controlled by `Event.max_capacity`, not `Venue.capacity` (which is informational only)

### Soft Delete Behavior
```mermaid
stateDiagram-v2
    [*] --> Active: Event Created
    Active --> Published: Host Publishes
    Active --> Draft: Host Saves Draft
    Published --> Deleted: Host Soft Deletes
    
    note right of Active
        is_active = True
        Visible: Host + Public List
    end note
    
    note right of Published
        is_active = True
        status = 'published'
        Visible: All Auth Users
    end note
    
    note right of Deleted
        is_active = False
        Visible: Host ONLY
        Others get 404
    end note
```

### Duration Calculation Logic

```mermaid
flowchart TD
    Input[User Input:<br/>duration_hours = 1.5] --> Validate[Validator: gt > 0]
    Validate --> Parse[Parse as float]
    Parse --> Calc[Calculate:<br/>end_time = start + timedelta<br/>hours=duration_hours]
    
    Calc --> Example1{Example 1:<br/>start: 10:00<br/>duration: 3hr}
    Calc --> Example2{Example 2:<br/>start: 09:00<br/>duration: 8hr}
    Calc --> Example3{Example 3:<br/>start: 14:00<br/>duration: 1.5hr}
    
    Example1 --> Result1[end_time: 13:00<br/>3 hours later]
    Example2 --> Result2[end_time: 17:00<br/>8 hours later]
    Example3 --> Result3[end_time: 15:30<br/>1.5 hours later]
    
    Result1 --> Store[(Database Stores<br/>start_time + end_time)]
    Result2 --> Store
    Result3 --> Store
    
    style Input fill:#e3f2fd
    style Validate fill:#fff3e0
    style Calc fill:#e8f5e9
    style Store fill:#c8e6c9
```

---

## Admin Interface

Comprehensive Django admin configuration in `admin.py`:

### EventAdmin
- **List Display**: title, host, venue, start_time, status, capacity, price, is_active
- **Filters**: status, is_active, is_public, is_paid, allowed_genders, start_time, created_at
- **Fieldsets**: Organized by Basic Info, Venue, Schedule, Capacity & Pricing, GST, Restrictions, Media, Status, Statistics
- **Readonly Fields**: uuid, slug, going_count, requests_count, duration_display
- **Inlines**: Interests, Images, Attendees, Requests, Invites, Reservations
- **Actions**: Bulk publish, cancel, activate, deactivate, complete
- **Features**: 
  - Duration display (calculated from start/end)
  - Capacity percentage with color coding
  - Revenue tracking
  - Status badges
  - Host/venue clickable links

### Key Admin Features
- Duration calculated automatically: shows "X hr" or "X.X hr" format
- Capacity info with fill percentage and color coding
- Revenue tracking aggregated from attendees
- Bulk operations for status management
- Inline editing of relationships
- Comprehensive filtering and search

---

## Validation & Security

### Authentication Flow Diagram

```mermaid
sequenceDiagram
    participant User
    participant Client App
    participant FastAPI
    participant JWT Verifier
    participant DB
    
    Note over User,DB: JWT Authentication Flow
    
    User->>Client App: Enter Phone Number
    Client App->>FastAPI: POST /api/auth/login<br/>{phone_number}
    FastAPI->>FastAPI: Generate OTP
    FastAPI->>User: Send OTP via SMS
    User->>Client App: Enter OTP
    Client App->>FastAPI: POST /api/auth/verify<br/>{phone_number, otp}
    FastAPI->>FastAPI: Verify OTP
    FastAPI-->>Client App: JWT Token
    
    Client App->>Client App: Store JWT Token
    
    Note over User,DB: Protected Endpoint Access
    
    Client App->>FastAPI: GET /api/events<br/>Header: Authorization Bearer {JWT}
    FastAPI->>JWT Verifier: Extract & Decode Token
    JWT Verifier->>JWT Verifier: Verify Signature
    JWT Verifier->>DB: Check User Exists
    
    alt Token Invalid
        DB-->>JWT Verifier: User Not Found
        JWT Verifier-->>FastAPI: 403 Not Authenticated
        FastAPI-->>Client App: HTTP 403
    else Token Valid
        DB-->>JWT Verifier: User Found ✓
        JWT Verifier-->>FastAPI: User Object
        FastAPI->>DB: Execute Query
        DB-->>FastAPI: Data
        FastAPI-->>Client App: HTTP 200 + Response
    end
```

### Authorization Matrix

```mermaid
graph TD
    subgraph "Event Visibility Rules"
        A[Request: GET /events/{id}] --> B{User Authenticated?}
        B -->|No| C[HTTP 403: Not Authenticated]
        B -->|Yes| D{Event Status?}
        
        D -->|is_active = False| E{Is Host?}
        E -->|Yes| F[HTTP 200: Return Event]
        E -->|No| G[HTTP 404: Not Found]
        
        D -->|is_active = True| H{is_public?}
        H -->|Yes| F
        H -->|No| I{Is Host?}
        I -->|Yes| F
        I -->|No| J[HTTP 403: No Permission]
    end
    
    subgraph "Event Modification Rules"
        K[Request: PUT/DELETE /events/{id}] --> L{JWT Valid?}
        L -->|No| C
        L -->|Yes| M{Is Host?}
        M -->|Yes| N[HTTP 200/204: Success]
        M -->|No| J
    end
    
    style C fill:#ffcdd2
    style G fill:#ffcdd2
    style J fill:#ffcdd2
    style F fill:#c8e6c9
    style N fill:#c8e6c9
```

### Input Validation Rules

```mermaid
flowchart TD
    Input[EventCreate Input] --> Validate1{title<br/>3-200 chars?}
    Validate1 -->|No| Err1[Error: Invalid title]
    Validate1 -->|Yes| Validate2{duration_hours<br/>> 0?}
    
    Validate2 -->|No| Err2[Error: Duration must be > 0]
    Validate2 -->|Yes| Validate3{Exactly ONE<br/>venue option?}
    
    Validate3 -->|No| Err3[Error: Provide ONE venue option]
    Validate3 -->|Yes| Validate4{cover_images<br/>&lt;= 3?}
    
    Validate4 -->|No| Err4[Error: Max 3 images]
    Validate4 -->|Yes| Validate5{status in<br/>valid choices?}
    
    Validate5 -->|No| Err5[Error: Invalid status]
    Validate5 -->|Yes| Validate6{allowed_genders<br/>in choices?}
    
    Validate6 -->|No| Err6[Error: Invalid gender]
    Validate6 -->|Yes| Success[All Validations Pass ✓]
    
    Err1 --> Reject[Reject Request]
    Err2 --> Reject
    Err3 --> Reject
    Err4 --> Reject
    Err5 --> Reject
    Err6 --> Reject
    
    Success --> Process[Process Request]
    
    style Success fill:#c8e6c9
    style Process fill:#c8e6c9
    style Reject fill:#ffcdd2
```

---

## Performance Optimizations

### Query Optimization Strategy

```mermaid
graph TD
    Request[API Request] --> Check{Operation Type?}
    
    Check -->|GET Single| SingleQuery[Optimize Single Query]
    Check -->|GET List| ListQuery[Optimize List Query]
    Check -->|POST/PUT| WriteOps[Write Operations]
    
    SingleQuery --> SelectRel[select_related:<br/>host, venue<br/>Single JOIN]
    SingleQuery --> PrefetchRel[prefetch_related:<br/>interests, attendees<br/>Batch Queries]
    SelectRel --> PrefetchRel
    PrefetchRel --> Cache[_prefetched_objects_cache<br/>Reuse in Pydantic]
    
    ListQuery --> Pagination[Pagination:<br/>LIMIT + OFFSET]
    ListQuery --> Filters[Index-Based Filters:<br/>status, is_active]
    Pagination --> Filters
    Filters --> Count[Separate COUNT Query]
    
    WriteOps --> Atomic[Atomic Transaction<br/>BEGIN...COMMIT]
    Atomic --> Constraints[Unique Constraints<br/>Prevent Duplicates]
    
    style SingleQuery fill:#e3f2fd
    style ListQuery fill:#fff3e0
    style WriteOps fill:#e8f5e9
    style Cache fill:#c8e6c9
```

---

## Testing

### API Testing Results
All CRUD operations tested via curl:
- ✅ Create: paid/free events, all venue options, duration_hours
- ✅ Read: list, single, with filters and search
- ✅ Update: partial updates, field validation
- ✅ Delete: soft delete with permission checks
- ✅ Venue operations: list, create, filter by city
- ✅ Validation: error messages, edge cases

### Test Coverage
- Model creation and validation
- Permission checks
- Business logic validation
- Edge cases and error handling

---

## Usage Examples

### Create Event

```bash
curl -X POST http://localhost:8000/api/events \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "title": "Workshop",
    "description": "Learn something",
    "event_interest_ids": [1, 2],
    "venue_create": {
      "name": "New Venue",
      "address": "123 Main St",
      "city": "Mumbai",
      "venue_type": "indoor",
      "capacity": 50
    },
    "start_time": "2025-12-30T10:00:00Z",
    "duration_hours": 3.5,
    "max_capacity": 50,
    "is_paid": true,
    "ticket_price": 500.00,
    "allowed_genders": "all"
  }'
```

### List Events

```bash
curl -X GET "http://localhost:8000/api/events?status=published&is_paid=true&limit=10" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Update Event

```bash
curl -X PUT http://localhost:8000/api/events/1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{"title": "Updated Title", "max_capacity": 100}'
```

### Delete Event

```bash
curl -X DELETE http://localhost:8000/api/events/1 \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

---

## Migration Notes

**Important**: Event creation API changed from `end_time` to `duration_hours`
- Old API required explicit `end_time` datetime
- New API uses `duration_hours` (float) - more intuitive
- Database still stores both `start_time` and `end_time`
- Update operations still support `end_time` for precision

---

## Architecture Decisions

### Why duration_hours in API but end_time in DB?
- **UX**: Users think in duration (2 hours), not end time
- **DB**: Queries/filters work better with explicit start/end
- **Separation**: API UX vs database schema concerns
- **Compatibility**: Admin and reports use start/end_time

### Why EventInterestMap with timestamps?
- Tech debt: Should be simple ManyToManyField
- Currently allows analytics on when interests are added
- Can refactor to ManyToManyField later without DB changes

### Why three venue options?
- Existing venue: reuse and standardization
- Auto-create: convenience for new venues
- Custom text: flexibility for temporary locations
- Validator ensures only one option used

---

## Complete Event Lifecycle Diagram

```mermaid
stateDiagram-v2
    [*] --> Draft: Host Creates Event
    
    Draft --> Published: Host Publishes
    Draft --> Cancelled: Host Cancels
    Published --> Cancelled: Host Cancels
    Published --> Completed: Event Ends
    Published --> Postponed: Event Postponed
    Postponed --> Published: Host Republishes
    
    Draft --> [*]: Host Soft Deletes
    Cancelled --> [*]: Host Soft Deletes
    Completed --> [*]: Auto-Archive (optional)
    
    note right of Draft
        Visibility: Host Only
        Can Edit: Yes
        Accept Requests: No
    end note
    
    note right of Published
        Visibility: All Users
        Can Edit: Yes
        Accept Requests: Yes
    end note
    
    note right of Cancelled
        Visibility: All (marked cancelled)
        Can Edit: No
        Accept Requests: No
    end note
```

---

## Error Handling Flow

```mermaid
sequenceDiagram
    participant Client
    participant FastAPI
    participant Validator
    participant Business
    participant DB
    
    Client->>FastAPI: POST /api/events
    FastAPI->>Validator: Validate Input
    
    alt Validation Error
        Validator-->>Client: HTTP 422<br/>ValidationError details
    end
    
    FastAPI->>Business: Process Request
    Business->>DB: Execute Query
    
    alt Not Found
        DB-->>Business: DoesNotExist
        Business-->>FastAPI: NotFoundError
        FastAPI-->>Client: HTTP 404<br/>Event not found
    end
    
    alt Permission Denied
        Business->>Business: Check Permissions
        Business-->>FastAPI: AuthorizationError
        FastAPI-->>Client: HTTP 403<br/>No permission
    end
    
    alt Database Error
        DB-->>Business: IntegrityError
        Business-->>FastAPI: ValidationError
        FastAPI-->>Client: HTTP 400<br/>Bad request
    end
    
    alt Success
        DB-->>Business: Data
        Business-->>FastAPI: Success
        FastAPI-->>Client: HTTP 201/200<br/>Response data
    end
```

---

## Complete API Reference

### Event Endpoints Summary

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| POST | `/api/events` | ✅ Required | Create event with duration_hours |
| GET | `/api/events` | ✅ Required | List events with filters |
| GET | `/api/events/{id}` | ✅ Required | Get single event |
| PUT | `/api/events/{id}` | ✅ Required | Update event (host only) |
| DELETE | `/api/events/{id}` | ✅ Required | Soft delete (host only) |

### Venue Endpoints Summary

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/events/venues` | ✅ Required | List venues with filters |
| POST | `/api/events/venues` | ✅ Required | Create venue |
| GET | `/api/events/venues/{id}` | ✅ Required | Get single venue |

### Request Endpoints Summary

| Method | Endpoint | Auth | Purpose |
|--------|----------|------|---------|
| GET | `/api/events/{id}/requests` | ✅ Required | List requests (host only) |
| POST | `/api/events/{id}/requests` | ✅ Required | Submit request |
| PUT | `/api/events/{id}/requests/{req_id}` | ✅ Required | Approve/decline (host only) |

---

## Development Notes

### Key Implementation Details
- All async operations use `sync_to_async` wrapper for Django ORM
- Pydantic v2 uses `model_dump()` instead of `.dict()`
- Prefetch optimization via `_prefetched_objects_cache`
- UUID conversion handled by `@field_validator`
- Duration calculation: `end_time = start_time + timedelta(hours=duration_hours)`

### Testing Strategy
- Manual curl testing for all CRUD operations
- Verify authentication and authorization on every endpoint
- Test validation errors with invalid inputs
- Confirm soft delete visibility rules
- Validate venue auto-creation workflow

---

## Future Enhancements

### Potential Improvements
- Refactor EventInterestMap to simple ManyToManyField
- Add batch operations for bulk updates
- Implement event duplication/cloning
- Add recurring event support
- Enhance filtering with date ranges
- Add popularity/trending algorithms

### Performance Optimizations
- Redis caching for frequently accessed events
- Elasticsearch for advanced search
- Database read replicas for scaling
- CDN for cover images
- GraphQL API layer option