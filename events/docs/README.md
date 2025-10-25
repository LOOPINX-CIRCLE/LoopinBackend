# Events Module Documentation

## Overview
The Events module handles event creation, management, and user interactions within the Loopin platform.

## Models

### Event
- **Purpose**: Core event model with venue, capacity, pricing, and status tracking
- **Key Fields**: title, description, start_time, venue, capacity, is_paid, ticket_price
- **Relationships**: One-to-many with EventRequest, EventInvite, AttendanceRecord

### Venue
- **Purpose**: Physical locations where events are hosted
- **Key Fields**: name, address, city, capacity, latitude, longitude
- **Relationships**: One-to-many with Event

### EventRequest
- **Purpose**: User requests to join events with approval workflow
- **Key Fields**: event, requester, status, message, seats_requested
- **Status Options**: pending, accepted, declined, cancelled

### EventInvite
- **Purpose**: Host invitations to users with expiration handling
- **Key Fields**: event, host, invited_user, status, message, expires_at
- **Status Options**: pending, accepted, declined

## API Endpoints
*To be implemented in FastAPI routers*

## Admin Interface
- Event management with filtering and search
- Venue management
- Request approval workflow
- Invitation management

## Business Logic
- Event capacity management
- Pricing and payment integration
- Approval workflow for requests
- Invitation expiration handling
