# Events Module Documentation

## Overview
The Events module handles event creation, management, and user interactions within the Loopin platform. The API uses FastAPI for modern, async REST endpoints with comprehensive validation and business logic.

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

## Models

### Venue
- **Purpose**: Physical locations where events are hosted
- **Key Fields**: uuid, name, address, city, venue_type, capacity, latitude, longitude, metadata
- **Relationships**: One-to-many with Event
- **Soft Delete**: is_active flag

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
- **Auth**: Optional
- **Returns**: Paginated list with total count

**GET** `/api/events/{event_id}`
- Get event details by ID
- **Auth**: Optional
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
- **Auth**: Not required (public)
- **Returns**: Paginated venue list

**POST** `/api/events/venues`
- Create new venue (admin/host only)
- **Auth**: Required (JWT)
- **Returns**: VenueResponse

**GET** `/api/events/venues/{venue_id}`
- Get venue by ID
- **Auth**: Not required (public)
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

## Business Logic

### Event Creation Workflow
1. Validate duration_hours > 0
2. Calculate end_time = start_time + duration_hours
3. Create venue if venue_create provided
4. Create event with all relationships
5. Link event interests via EventInterestMap
6. Return complete event with all relationships

### Venue Management
- **Fetch Pattern**: Users fetch available venues via GET /venues
- **Auto-Creation**: Venues created during event hosting if new venue specified
- **Options**: Three options (id, create, text) - validator ensures only one provided

### Soft Delete Behavior
- Deletes set `is_active=False`
- Hosts can view their deleted events
- Public list only shows active events
- Soft-deleted events return 404 for non-hosts

### Duration Calculation
- API uses `duration_hours` (float) for user input
- Database stores `start_time` and `end_time` (datetime)
- Conversion: `end_time = start_time + timedelta(hours=duration_hours)`
- Supports decimals: 1.5 hours, 7.5 hours, etc.

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

## Validation & Security

### Input Validation
- Duration must be > 0 hours
- Title: 3-200 characters
- Description: max 20,000 characters
- Max 3 cover images
- Only one venue option allowed
- Status and gender values validated against choices

### Authentication & Authorization
- JWT required for create/update/delete operations
- Host verification for event modifications
- Soft delete visibility: hosts only
- Public read access for published events

### Data Integrity
- Atomic transactions for event creation
- Unique constraints on event-interest, event-user (attendee)
- Soft deletes preserve data
- UUIDs for public-facing APIs

## Performance Optimizations

### Database Queries
- `select_related`: host, venue (single JOIN)
- `prefetch_related`: interests, attendees, requests, invites
- `_prefetched_objects_cache`: Pydantic uses cached results
- Proper indexing on foreign keys, status, timestamps

### Pagination
- Efficient offset/limit queries
- Total count calculated once per request
- Default limit prevents excessive data transfer

## Testing

### API Testing
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
curl "http://localhost:8000/api/events?status=published&is_paid=true&limit=10"
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

## Migration Notes

**Important**: Event creation API changed from `end_time` to `duration_hours`
- Old API required explicit `end_time` datetime
- New API uses `duration_hours` (float) - more intuitive
- Database still stores both `start_time` and `end_time`
- Update operations still support `end_time` for precision

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