# Events Module Documentation

## Overview
The Events module handles event creation, management, and user interactions within the Loopin platform. 

## Architecture

### Project Structure
```
events/
├── admin.py              # Django admin configuration
├── apps.py               # App configuration
├── models.py             # Database models
├── schemas.py            # Pydantic validation schemas
├── services.py           # Business logic services
├── serializers/          # DRF serializers
│   ├── __init__.py
│   └── event_serializers.py
├── views/                # Django REST views
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

## Models

### Venue
- **Purpose**: Physical locations where events are hosted
- **Key Fields**: name, address, city, venue_type, capacity, latitude, longitude
- **Relationships**: One-to-many with Event

### Event
- **Purpose**: Core event model with venue, capacity, and status tracking
- **Key Fields**: host, title, description, start_time, end_time, venue, status, max_capacity, going_count
- **Status Options**: draft, published, cancelled, completed, postponed
- **Relationships**: 
  - Many-to-one with User (host)
  - Many-to-one with Venue
  - One-to-many with EventRequest, EventInvite, EventAttendee

### EventRequest
- **Purpose**: User requests to join events with approval workflow
- **Key Fields**: event, requester, status, message, seats_requested
- **Status Options**: pending, accepted, declined, cancelled, expired

### EventInvite
- **Purpose**: Host invitations to users with expiration handling
- **Key Fields**: event, invited_user, status, message, expires_at
- **Status Options**: pending, accepted, declined, expired

### EventAttendee
- **Purpose**: Tracking event attendees and their status
- **Key Fields**: event, user, status, checked_in_at, seats
- **Status Options**: going, not_going, maybe, checked_in, cancelled

## Serializers

All serializers are located in `serializers/event_serializers.py`:
- `VenueSerializer` - Full venue details
- `VenueListSerializer` - Simplified venue list
- `EventSerializer` - Full event details
- `EventListSerializer` - Simplified event list
- `EventCreateSerializer` - Event creation with validation
- `EventUpdateSerializer` - Event updates
- `EventRequestSerializer` - Request details
- `EventRequestCreateSerializer` - Request creation
- `EventInviteSerializer` - Invite details
- `EventInviteCreateSerializer` - Invite creation
- `EventAttendeeSerializer` - Attendee details

## Views

All views are located in `views/event_views.py`:
- `VenueListCreateView` - List/create venues
- `VenueRetrieveUpdateDestroyView` - Venue CRUD operations
- `EventListCreateView` - List/create events
- `EventRetrieveUpdateDestroyView` - Event CRUD operations
- `EventRequestListCreateView` - List/create requests
- `EventRequestRetrieveUpdateDestroyView` - Request CRUD operations
- `EventInviteListCreateView` - List/create invites
- `EventInviteRetrieveUpdateDestroyView` - Invite CRUD operations
- `EventAttendeeListCreateView` - List/create attendees
- `EventAttendeeRetrieveUpdateDestroyView` - Attendee CRUD operations
- `check_in_attendee_view` - Check-in functionality
- `my_events_view` - Get user's events

## Services

Business logic is encapsulated in `services.py`:

### EventService
- `create_event()` - Create event with validation
- `update_event_status()` - Update event status
- `cancel_event()` - Cancel an event

### EventRequestService
- `create_request()` - Create event request
- `accept_request()` - Accept request and create attendee
- `decline_request()` - Decline request

### EventInviteService
- `create_invite()` - Create event invite
- `accept_invite()` - Accept invite and create attendee
- `decline_invite()` - Decline invite

### AttendanceService
- `check_in_attendee()` - Check in attendee
- `update_attendance_status()` - Update attendance

## Schemas

Pydantic schemas in `schemas.py` for API validation:
- Request models for all operations
- Response models for API responses
- Validation for all fields

## Admin Interface

Comprehensive Django admin configuration in `admin.py`:
- Venue management with filtering
- Event management with status badges
- Request approval workflow
- Invitation management
- Attendance tracking

## Business Logic

- Event capacity management
- Request approval workflow
- Invitation expiration handling
- Check-in functionality
- Status tracking and updates

## Testing

Tests are located in `tests/test_events.py`:
- Model creation and validation
- Serializer functionality
- API endpoint behavior
- Permission checks
- Business logic validation

## Usage

See individual file documentation for detailed usage examples.
