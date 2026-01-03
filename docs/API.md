# Events API Documentation

## Overview
Production-ready, high-performance CRUD API for events using FastAPI, Django ORM, and JWT authentication.

**Base URL**: `/api/events`

## Endpoints

### List Events
`GET /api/events`

List all events with filtering, pagination, and search.

**Query Parameters**:
- `host_id` (optional): Filter by host user ID
- `status` (optional): Filter by status (draft, published, cancelled, completed, postponed)
- `is_public` (optional): Filter by public/private events
- `is_upcoming` (optional): Filter upcoming/past events
- `search` (optional): Search in title and description
- `offset` (optional, default: 0): Pagination offset
- `limit` (optional, default: 20, max: 100): Results per page

**Authentication**: Optional

**Response**:
```json
{
  "total": 10,
  "offset": 0,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "title": "Django Meetup",
      "description": "Monthly Django developers meetup",
      "start_time": "2025-12-15T18:00:00Z",
      "end_time": "2025-12-15T21:00:00Z",
      "status": "published",
      "is_public": true,
      "going_count": 0,
      "max_capacity": 100,
      "cover_images": ["https://example.com/image1.jpg"],
      "is_active": true,
      "host": {
        "id": 1,
        "username": "admin",
        "email": "admin@loopin.com"
      },
      "venue": null,
      "created_at": "2025-10-30T19:00:56.484739Z",
      "updated_at": "2025-10-30T19:00:56.484780Z"
    }
  ]
}
```

**Example**:
```bash
curl http://localhost:8000/api/events?status=published&search=Django&limit=10
```

---

### Get Event Details
`GET /api/events/{event_id}`

Get detailed information about a specific event.

**Authentication**: Optional (required for private events)

**Response**:
```json
{
  "id": 1,
  "title": "Django Meetup",
  "description": "Monthly Django developers meetup",
  "start_time": "2025-12-15T18:00:00Z",
  "end_time": "2025-12-15T21:00:00Z",
  "status": "published",
  "is_public": true,
  "going_count": 0,
  "max_capacity": 100,
  "cover_images": ["https://example.com/image1.jpg"],
  "is_active": true,
  "host": {
    "id": 1,
    "username": "admin",
    "email": "admin@loopin.com"
  },
  "venue": null,
  "created_at": "2025-10-30T19:00:56.484739Z",
  "updated_at": "2025-10-30T19:00:56.484780Z"
}
```

**Example**:
```bash
curl http://localhost:8000/api/events/1
```

---

### Create Event
`POST /api/events`

Create a new event.

**Authentication**: Required (JWT)

**Request Body**:
```json
{
  "title": "Django Meetup",
  "description": "Monthly Django developers meetup",
  "start_time": "2025-12-15T18:00:00Z",
  "end_time": "2025-12-15T21:00:00Z",
  "venue_id": 1,
  "status": "draft",
  "is_public": true,
  "max_capacity": 100,
  "cover_images": ["https://example.com/image1.jpg"]
}
```

**Validation Rules**:
- `title`: 3-200 characters
- `description`: Optional, max 20000 characters
- `start_time`: ISO 8601 format
- `end_time`: Must be after start_time
- `status`: draft, published, cancelled, completed, postponed
- `max_capacity`: Non-negative integer (0 = unlimited)
- `cover_images`: Max 10 images with valid URLs

**Response**: Event detail object (201 Created)

**Example**:
```bash
curl -X POST http://localhost:8000/api/events \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Django Meetup",
    "description": "Monthly meetup",
    "start_time": "2025-12-15T18:00:00Z",
    "end_time": "2025-12-15T21:00:00Z",
    "status": "published"
  }'
```

---

### Update Event
`PUT /api/events/{event_id}`

Update an existing event.

**Authentication**: Required (JWT)
**Permission**: Event host or admin only

**Request Body**: All fields optional
```json
{
  "title": "Updated Title",
  "description": "Updated description",
  "status": "published",
  "max_capacity": 150
}
```

**Response**: Updated event detail object (200 OK)

**Example**:
```bash
curl -X PUT http://localhost:8000/api/events/1 \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title": "Updated Title"}'
```

---

### Delete Event
`DELETE /api/events/{event_id}`

Soft delete an event (sets is_active=False).

**Authentication**: Required (JWT)
**Permission**: Event host or admin only

**Response**: 204 No Content

**Example**:
```bash
curl -X DELETE http://localhost:8000/api/events/1 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

### List Event Requests
`GET /api/events/{event_id}/requests`

List all requests for an event (host only).

**Authentication**: Required (JWT)
**Permission**: Event host or admin only

**Response**:
```json
[
  {
    "id": 1,
    "event_id": 1,
    "requester_id": 2,
    "requester_name": "johndoe",
    "status": "pending",
    "message": "I'd like to attend",
    "seats_requested": 1,
    "created_at": "2025-10-30T19:00:00Z",
    "updated_at": "2025-10-30T19:00:00Z"
  }
]
```

---

## Authentication

All protected endpoints require JWT authentication.

**Get Token**:
```bash
POST /api/auth/login
{
  "username": "admin",
  "password": "password"
}
```

**Use Token**:
```bash
Authorization: Bearer YOUR_JWT_TOKEN
```

---

## Performance Features

### Query Optimization
- **select_related**: Reduces N+1 queries for ForeignKey relationships
- **prefetch_related**: Optimizes many-to-many and reverse FK queries
- **Only**: Fetches only required fields
- **Database indexes**: On status, start_time, is_public, is_active

### Pagination
- Default: 20 items per page
- Maximum: 100 items per page
- Efficient COUNT queries
- Offset-based pagination

### Caching
- Query result caching (Redis recommended)
- HTTP caching headers
- Database query cache

### Async Operations
- All DB operations use sync_to_async
- Non-blocking I/O
- Concurrent request handling

---

## Error Responses

### 400 Bad Request
```json
{
  "detail": "Validation error message"
}
```

### 401 Unauthorized
```json
{
  "detail": "Not authenticated"
}
```

### 403 Forbidden
```json
{
  "detail": "Permission denied"
}
```

### 404 Not Found
```json
{
  "detail": "Event not found"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Internal server error"
}
```

---

## Security

### Authentication
- JWT-based authentication
- Token expiration
- Secure password hashing (bcrypt)

### Authorization
- Role-based access control (RBAC)
- Object-level permissions
- Event ownership checks

### Validation
- Pydantic request validation
- SQL injection protection (Django ORM)
- XSS protection
- CSRF protection

### Rate Limiting
- Per-user rate limits (recommended)
- Per-IP rate limits
- Throttling on sensitive operations

---

## Testing

Run tests:
```bash
# Unit tests
docker-compose exec web python manage.py test events

# API integration tests
docker-compose exec web pytest api/tests/test_events_api.py -v
```

---

## Monitoring

### Logging
- Request/response logging
- Error tracking
- Performance metrics
- Query duration logs

### Metrics
- Request rate
- Response times
- Error rates
- Database query performance

---

## Docker Deployment

Build and run:
```bash
docker-compose build
docker-compose up -d
```

Check logs:
```bash
docker-compose logs web -f
```

---

## Examples

### Complete Event Lifecycle

```bash
# 1. Login
TOKEN=$(curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}' | jq -r '.access_token')

# 2. Create event
EVENT_ID=$(curl -X POST http://localhost:8000/api/events \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Python Conference",
    "description": "Annual Python developers conference",
    "start_time": "2026-01-10T09:00:00Z",
    "end_time": "2026-01-10T18:00:00Z",
    "status": "published",
    "max_capacity": 500
  }' | jq -r '.id')

# 3. Get event
curl http://localhost:8000/api/events/$EVENT_ID

# 4. Update event
curl -X PUT http://localhost:8000/api/events/$EVENT_ID \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"status": "published"}'

# 5. Delete event (soft delete)
curl -X DELETE http://localhost:8000/api/events/$EVENT_ID \
  -H "Authorization: Bearer $TOKEN"
```

---

## Payments API

### Create Payment Order
`POST /api/payments/orders`

Create a payment order for an event and get PayU redirect payload.

**Authentication**: Required (JWT)

**Request Body**:
```json
{
  "event_id": 1,
  "amount": 110.00,
  "reservation_key": "uuid-string" // Optional, required for paid events
}
```

**Response** (201 Created):
```json
{
  "payu_url": "https://secure.payu.in/_payment",
  "payload": {
    "key": "merchant_key",
    "txnid": "order_id",
    "amount": "110.00",
    "productinfo": "Event Ticket",
    "firstname": "John",
    "email": "john@example.com",
    "phone": "9876543210",
    "surl": "https://api.example.com/payments/payu/success",
    "furl": "https://api.example.com/payments/payu/failure",
    "hash": "sha512_hash"
  }
}
```

**Business Rules**:
- Only for paid events (`event.is_paid == True`)
- Requires valid capacity reservation for paid events
- Amount must match calculated total (base price + platform fee) × seats
- Order expires in 10 minutes

### Get Payment Order
`GET /api/payments/orders/{order_id}`

Get payment order details.

**Authentication**: Required (JWT)

**Response** (200 OK):
```json
{
  "id": 1,
  "order_id": "ORD_20251227120000_1_abc123",
  "event_id": 1,
  "amount": "110.00",
  "currency": "INR",
  "status": "paid",
  "payment_provider": "payu",
  "seats_count": 1,
  "base_price_per_seat": "100.00",
  "platform_fee_percentage": "10.00",
  "platform_fee_amount": "10.00",
  "host_earning_per_seat": "100.00",
  "is_final": true,
  "expires_at": "2025-12-27T12:10:00Z",
  "created_at": "2025-12-27T12:00:00Z"
}
```

### PayU Success Callback
`POST /api/payments/payu/success`

Handle PayU success callback (redirect from PayU).

**Authentication**: Not required (PayU callback)

**Request**: PayU form data with hash verification

**Response**: Redirects to frontend success page

### PayU Failure Callback
`POST /api/payments/payu/failure`

Handle PayU failure callback (redirect from PayU).

**Authentication**: Not required (PayU callback)

**Request**: PayU form data with hash verification

**Response**: Redirects to frontend failure page

### PayU Webhook
`POST /api/payments/payu/webhook`

Handle PayU webhook (server-to-server notification).

**Authentication**: Not required (PayU webhook)

**Request**: PayU webhook payload with signature

**Response**: 200 OK (idempotent processing)

---

## API Docs

Interactive API documentation available at:
- **Swagger UI**: `/api/docs`
- **ReDoc**: `/api/redoc`
- **OpenAPI JSON**: `/api/openapi.json`

