# Analytics Dashboard - Complete Documentation

Production-grade Analytics Dashboard for Django Admin providing CEO/Admin-level insights into platform KPIs.

**📚 Related Documentation:**
- [Complete Database ERD Documentation](../erd_doc_fixed.md) - Full database schema with all tables, fields, and relationships

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Access Control](#access-control)
4. [Model Reference & Field Names](#model-reference--field-names)
5. [Services Layer](#services-layer)
6. [API Endpoints](#api-endpoints)
7. [Data Structures](#data-structures)
8. [Business Logic & Calculations](#business-logic--calculations)
9. [Query Optimization](#query-optimization)
10. [Error Handling](#error-handling)
11. [Testing](#testing)
12. [Troubleshooting](#troubleshooting)
13. [Future Expansion](#future-expansion)

---

## Overview

The Analytics Dashboard is a comprehensive business intelligence tool integrated into Django Admin. It provides real-time insights into:

- **User Lifecycle**: Registration trends, active users, waitlist management
- **Host Metrics**: Host conversion rates, new hosts over time
- **Live Events**: Currently running events with revenue tracking
- **Completed Events**: Financial insights, attendance rates, payout status
- **Host Deep Analytics**: Individual host performance metrics with engagement scores

### Key Features

- ✅ Real-time metrics with time-series graphs
- ✅ Period filtering (Weekly/Monthly/Yearly)
- ✅ AJAX-powered updates without page reload
- ✅ Optimized database queries (no N+1)
- ✅ Financial precision using Decimal type
- ✅ Graceful error handling
- ✅ Production-ready architecture

---

## Architecture

### Directory Structure

```
analytics/
├── __init__.py
├── apps.py              # App configuration with auto-import
├── admin.py             # Django Admin views and API endpoints
├── services.py          # All business logic and aggregation
├── models.py            # (Currently empty, reserved for future)
├── views.py             # (Reserved for future use)
├── tests.py             # Unit tests
├── templates/
│   └── admin/
│       └── analytics/
│           └── dashboard.html  # Main dashboard template
├── migrations/
│   └── __init__.py
└── docs/
    └── README.md        # This file
```

### Component Overview

#### 1. Services Layer (`analytics/services.py`)

**Purpose**: All business logic and data aggregation lives here.

**Key Principles**:
- No direct queries in views
- All heavy computations in services
- Returns structured data ready for JSON serialization
- Designed for caching (Redis-ready)

**Functions**:
- `get_user_lifecycle_metrics(period)` - User registration and approval metrics
- `get_waitlist_metrics(period)` - Waitlist-specific analytics
- `get_host_metrics(period)` - Host conversion and trends
- `get_live_events_analytics(period)` - Currently running events
- `get_completed_events_analytics(paid_only, free_only)` - Completed events with financials
- `get_host_deep_analytics(host_id)` - Individual host performance

#### 2. Admin Views (`analytics/admin.py`)

**Purpose**: Django Admin integration and API endpoints.

**Views**:
- `analytics_dashboard_view` - Main dashboard HTML view
- `analytics_api_users` - User metrics JSON API
- `analytics_api_events` - Events metrics JSON API
- `analytics_api_hosts` - Host metrics JSON API
- `analytics_api_view` - Legacy unified API endpoint

**URL Routing**:
- Patches Django Admin site to add dashboard URLs
- Auto-registered when app is loaded

#### 3. Templates (`analytics/templates/admin/analytics/dashboard.html`)

**Purpose**: Dashboard UI with interactive charts.

**Features**:
- Extends Django Admin base template
- Uses Chart.js for interactive graphs
- Responsive grid layout
- Real-time period filtering
- AJAX data loading

---

## Access Control

### URL

```
http://localhost:8000/django/admin/dashboard/
```

### Requirements

- **Authentication**: User must be logged in
- **Authorization**: User must have `is_staff=True`
- **Response**: Non-staff users receive `403 Forbidden` (not redirect)

### Implementation

```python
@login_required
@staff_required
def analytics_dashboard_view(request):
    # Only accessible to staff users
    ...
```

The `@staff_required` decorator returns `HttpResponseForbidden` for non-staff users.

---

## Model Reference & Field Names

**⚠️ CRITICAL**: This section documents the exact field names, primary keys, foreign keys, and relationships used in analytics queries. Always reference this when writing queries to avoid bugs.

### Database Schema Reference

For complete database schema documentation, see: [Complete Database ERD Documentation](../erd_doc_fixed.md)

### Model Field Mappings

#### AUTH_USER (Django Built-in)

**Primary Key**: `id` (BIGINT)  
**Public Identifier**: `uuid` (UUID)  
**Timestamp Fields**: `date_joined` (DATETIME), `last_login` (DATETIME), `created_at` (DATETIME), `updated_at` (DATETIME)

**Key Fields Used in Analytics**:
- `id` - Primary key
- `is_active` - Boolean (False = waitlisted, True = approved)
- `date_joined` - Registration timestamp (used for time-series)
- `username` - Phone number for authentication

**Relationships**:
- `profile` (OneToOne) → `USER_PROFILE` (via `UserProfile.user`)
- Reverse: `hosted_events` → `EVENT` (via `Event.host`)

**Query Example**:
```python
User.objects.filter(is_active=True).select_related('profile')
```

---

#### USER_PROFILE

**Primary Key**: `id` (BIGINT)  
**Public Identifier**: `uuid` (UUID)  
**Foreign Key**: `user_id` → `AUTH_USER.id` (OneToOne)  
**Timestamp Fields**: `created_at` (DATETIME), `updated_at` (DATETIME)

**Key Fields Used in Analytics**:
- `id` - Primary key
- `user_id` - Foreign key to AUTH_USER
- `name` - Host/user name (fallback: `user.username`)
- `is_active` - Profile active status
- `is_verified` - Phone verification status

**Relationships**:
- `user` (ForeignKey) → `AUTH_USER` (OneToOne)
- Reverse: `hosted_events` → `EVENT` (via `Event.host`)

**Query Example**:
```python
UserProfile.objects.filter(hosted_events__isnull=False).select_related('user')
```

---

#### EVENT

**Primary Key**: `id` (BIGINT)  
**Public Identifier**: `uuid` (UUID)  
**Foreign Keys**: 
- `host_id` → `USER_PROFILE.id` (ManyToOne)
- `venue_id` → `VENUE.id` (ManyToOne, nullable)
**Timestamp Fields**: `created_at` (DATETIME), `updated_at` (DATETIME), `start_time` (DATETIME), `end_time` (DATETIME)

**Key Fields Used in Analytics**:
- `id` - Primary key
- `host_id` - Foreign key to USER_PROFILE
- `venue_id` - Foreign key to VENUE (nullable)
- `status` - Event status: `'draft'`, `'published'`, `'cancelled'`, `'completed'`, `'postponed'`
- `is_paid` - Boolean (paid vs free event)
- `ticket_price` - Decimal(10,2) - Base ticket fare
- `start_time` - Event start datetime
- `end_time` - Event end datetime
- `going_count` - Integer - Confirmed attendees count
- `requests_count` - Integer - Pending requests count
- `max_capacity` - Integer - Maximum attendees
- `venue_text` - String - Custom venue text (if venue_id is null)

**Relationships**:
- `host` (ForeignKey) → `USER_PROFILE` (ManyToOne)
- `venue` (ForeignKey) → `VENUE` (ManyToOne, nullable)
- Reverse: `attendance_records` → `ATTENDANCE_RECORD` (via `AttendanceRecord.event`)
- Reverse: `payment_orders` → `PAYMENT_ORDER` (via `PaymentOrder.event`)
- Reverse: `payout_requests` → `HOST_PAYOUT_REQUEST` (via `HostPayoutRequest.event`)

**Query Example**:
```python
Event.objects.filter(
    status='published',
    start_time__lte=now,
    end_time__gte=now
).select_related('host', 'venue').prefetch_related(
    'attendance_records',
    'payment_orders'
)
```

---

#### ATTENDANCE_RECORD

**Primary Key**: `id` (BIGINT)  
**Foreign Keys**: 
- `event_id` → `EVENT.id` (ManyToOne)
- `user_id` → `USER_PROFILE.id` (ManyToOne)
**Timestamp Fields**: `created_at` (DATETIME), `updated_at` (DATETIME), `checked_in_at` (DATETIME, nullable), `checked_out_at` (DATETIME, nullable)

**Key Fields Used in Analytics**:
- `id` - Primary key
- `event_id` - Foreign key to EVENT
- `user_id` - Foreign key to USER_PROFILE
- `status` - Attendance status: `'going'`, `'not_going'`, `'maybe'`, `'checked_in'`, `'cancelled'`
- `payment_status` - Payment status: `'unpaid'`, `'paid'`, `'refunded'`
- `seats` - Integer - Number of seats
- `checked_in_at` - Check-in timestamp (nullable)
- `checked_out_at` - Check-out timestamp (nullable)

**Relationships**:
- `event` (ForeignKey) → `EVENT` (ManyToOne)
- `user` (ForeignKey) → `USER_PROFILE` (ManyToOne)

**Query Example**:
```python
AttendanceRecord.objects.filter(
    event=event,
    status='going'
).select_related('user').aggregate(total=Sum('seats'))
```

---

#### PAYMENT_ORDER

**Primary Key**: `id` (BIGINT)  
**Public Identifier**: `uuid` (UUID)  
**Foreign Keys**: 
- `event_id` → `EVENT.id` (ManyToOne)
- `user_id` → `USER_PROFILE.id` (ManyToOne)
**Timestamp Fields**: `created_at` (DATETIME), `updated_at` (DATETIME), `expires_at` (DATETIME, nullable), `refunded_at` (DATETIME, nullable)

**Key Fields Used in Analytics**:
- `id` - Primary key
- `event_id` - Foreign key to EVENT
- `user_id` - Foreign key to USER_PROFILE
- `status` - Payment status: `'created'`, `'pending'`, `'paid'`, `'completed'`, `'failed'`, `'cancelled'`, `'refunded'`, `'unpaid'`
- `amount` - Decimal(10,2) - Payment amount
- `currency` - String - Currency code (default: 'INR')
- `order_id` - String - Unique order identifier
- `provider_payment_id` - String - Payment provider transaction ID

**Relationships**:
- `event` (ForeignKey) → `EVENT` (ManyToOne)
- `user` (ForeignKey) → `USER_PROFILE` (ManyToOne)

**Query Example**:
```python
PaymentOrder.objects.filter(
    event=event,
    status='completed'
).aggregate(total=Sum('amount'))
```

---

#### HOST_PAYOUT_REQUEST

**Primary Key**: `id` (BIGINT)  
**Public Identifier**: `uuid` (UUID)  
**Foreign Keys**: 
- `bank_account_id` → `BANK_ACCOUNT.id` (ManyToOne)
- `event_id` → `EVENT.id` (ManyToOne)
**Timestamp Fields**: `created_at` (DATETIME), `updated_at` (DATETIME), `processed_at` (DATETIME, nullable)

**Key Fields Used in Analytics**:
- `id` - Primary key
- `event_id` - Foreign key to EVENT
- `bank_account_id` - Foreign key to BANK_ACCOUNT
- `status` - Payout status: `'pending'`, `'approved'`, `'processing'`, `'completed'`, `'rejected'`, `'cancelled'`
- `base_ticket_fare` - Decimal(10,2) - Base ticket price (snapshot)
- `final_ticket_fare` - Decimal(10,2) - Final price with platform fee (snapshot)
- `total_tickets_sold` - Integer - Tickets sold (snapshot)
- `platform_fee_amount` - Decimal(10,2) - Total platform fee (snapshot)
- `final_earning` - Decimal(10,2) - Host earnings (snapshot)
- `host_name` - String - Host name (snapshot)
- `event_name` - String - Event name (snapshot)
- `event_date` - DATETIME - Event date (snapshot)
- `event_location` - String - Event location (snapshot)
- `attendees_details` - JSONB - Attendee list (snapshot)

**Relationships**:
- `event` (ForeignKey) → `EVENT` (ManyToOne, PROTECT)
- `bank_account` (ForeignKey) → `BANK_ACCOUNT` (ManyToOne, PROTECT)
- Reverse: `event__host` → `USER_PROFILE` (via Event.host)

**Query Example**:
```python
HostPayoutRequest.objects.filter(
    event__host=host
).select_related('event').aggregate(
    total=Sum('final_earning')
)
```

---

#### VENUE

**Primary Key**: `id` (BIGINT)  
**Public Identifier**: `uuid` (UUID)  
**Timestamp Fields**: `created_at` (DATETIME), `updated_at` (DATETIME)

**Key Fields Used in Analytics**:
- `id` - Primary key
- `name` - String - Venue name
- `city` - String - City name
- `address` - Text - Full address

**Relationships**:
- Reverse: `events` → `EVENT` (via `Event.venue`)

**Query Example**:
```python
Event.objects.select_related('venue')  # Joins VENUE table
```

---

### Join Relationships Summary

| Relationship | Join Type | Field Path | Usage |
|-------------|-----------|------------|-------|
| `User` → `UserProfile` | OneToOne | `user.profile` | `select_related('profile')` |
| `UserProfile` → `User` | OneToOne | `profile.user` | `select_related('user')` |
| `Event` → `UserProfile` (host) | ManyToOne | `event.host` | `select_related('host')` |
| `Event` → `Venue` | ManyToOne | `event.venue` | `select_related('venue')` |
| `Event` → `AttendanceRecord` | OneToMany | `event.attendance_records` | `prefetch_related('attendance_records')` |
| `Event` → `PaymentOrder` | OneToMany | `event.payment_orders` | `prefetch_related('payment_orders')` |
| `Event` → `HostPayoutRequest` | OneToMany | `event.payout_requests` | `prefetch_related('payout_requests')` |
| `AttendanceRecord` → `Event` | ManyToOne | `attendance.event` | `select_related('event')` |
| `AttendanceRecord` → `UserProfile` | ManyToOne | `attendance.user` | `select_related('user')` |
| `PaymentOrder` → `Event` | ManyToOne | `payment.event` | `select_related('event')` |
| `PaymentOrder` → `UserProfile` | ManyToOne | `payment.user` | `select_related('user')` |
| `HostPayoutRequest` → `Event` | ManyToOne | `payout.event` | `select_related('event')` |

---

## Services Layer

### Function Reference

#### `get_user_lifecycle_metrics(period: str) -> Dict[str, Any]`

**Purpose**: Get user lifecycle metrics with time-series data.

**Parameters**:
- `period` (str): Time period for grouping. Options: `'weekly'`, `'monthly'`, `'yearly'`. Default: `'monthly'`

**Returns**:
```python
{
    'total_users': int,           # Total registered users (cumulative)
    'active_users': int,          # Users with is_active=True
    'waitlisted_users': int,      # Users with is_active=False
    'approval_rate': float,       # Decimal (0.92 = 92%), active_users / total_users
    'trend': [                    # Time-series data
        {
            'period': str,        # ISO date string
            'total': int,         # Total registered in period
            'active': int,        # Active registered in period
            'waitlisted': int     # Waitlisted registered in period
        },
        ...
    ]
}
```

**Data Sources**:
- `django.contrib.auth.models.User` (AUTH_USER table)
  - Fields: `id` (PK), `is_active`, `date_joined`
  - Join: `select_related('profile')` → USER_PROFILE
- `users.models.UserProfile` (USER_PROFILE table)
  - Fields: `id` (PK), `user_id` (FK), `name`

**Exact Query**:
```python
User.objects.select_related('profile').filter(
    is_active=True  # Active users
).filter(
    is_active=False  # Waitlisted users
).annotate(
    period=TruncMonth('date_joined')  # Time grouping
).values('period').annotate(
    total_registered=Count('id'),
    active_registered=Count('id', filter=Q(is_active=True)),
    waitlisted_registered=Count('id', filter=Q(is_active=False))
)
```

**Definitions**:
- **Waitlisted**: `User.is_active = False`
- **Active**: `User.is_active = True`
- **Approval Rate**: `active_users / total_users` (as decimal)

**Query Optimization**:
- Uses `select_related('profile')` to avoid N+1 queries
- Uses `TruncWeek`, `TruncMonth`, or `TruncYear` for time grouping
- Aggregates at database level using `Count()` with filters

**Example**:
```python
metrics = get_user_lifecycle_metrics(period='monthly')
# Returns:
# {
#     'total_users': 3110,
#     'active_users': 2870,
#     'waitlisted_users': 240,
#     'approval_rate': 0.9228,
#     'trend': [...]
# }
```

---

#### `get_waitlist_metrics(period: str) -> Dict[str, Any]`

**Purpose**: Get waitlist-specific metrics and trends.

**Parameters**:
- `period` (str): Time period. Options: `'weekly'`, `'monthly'`, `'yearly'`. Default: `'monthly'`

**Returns**:
```python
{
    'total_waitlisted': int,      # Total users in waitlist
    'approval_rate': float,       # Overall approval rate (as percentage, not decimal)
    'trend': [                    # New waitlisted users per period
        {
            'period': str,        # ISO date string
            'count': int          # New waitlisted users in period
        },
        ...
    ]
}
```

**Data Sources**:
- `django.contrib.auth.models.User` where `is_active=False`

**Example**:
```python
metrics = get_waitlist_metrics(period='weekly')
# Returns:
# {
#     'total_waitlisted': 240,
#     'approval_rate': 92.28,
#     'trend': [...]
# }
```

---

#### `get_host_metrics(period: str) -> Dict[str, Any]`

**Purpose**: Get host-related metrics and conversion rates.

**Parameters**:
- `period` (str): Time period. Options: `'weekly'`, `'monthly'`, `'yearly'`. Default: `'monthly'`

**Returns**:
```python
{
    'total_hosts': int,           # Distinct hosts (users who created events)
    'conversion_rate': float,     # Decimal (0.046 = 4.6%), hosts / approved_users
    'new_hosts': [                # New hosts over time
        {
            'period': str,        # ISO date string
            'count': int          # New hosts in period
        },
        ...
    ]
}
```

**Business Logic**:
- **Host Definition**: User who has created at least one event (`Event.host_id`)
- **Conversion Rate**: `total_hosts / active_users` (as decimal)

**Data Sources**:
- `events.models.Event` (EVENT table)
  - Fields: `id` (PK), `host_id` (FK → USER_PROFILE.id), `created_at`
  - Join: `values('host').distinct()` for unique hosts
- `django.contrib.auth.models.User` (for active users count)
  - Fields: `id` (PK), `is_active`
  - Join: `profile__hosted_events` → EVENT via UserProfile

**Exact Query**:
```python
# Total hosts
Event.objects.values('host_id').distinct().count()

# New hosts trend
Event.objects.annotate(
    period=TruncMonth('created_at')
).values('period', 'host_id').distinct().values('period').annotate(
    count=Count('host_id', distinct=True)
)

# Conversion rate
active_users = User.objects.filter(is_active=True).count()
users_with_events = User.objects.filter(
    profile__hosted_events__isnull=False
).distinct().count()
```

**Query Optimization**:
- Uses `values('host').distinct()` for unique hosts
- Groups by period using date truncation functions

**Example**:
```python
metrics = get_host_metrics(period='yearly')
# Returns:
# {
#     'total_hosts': 133,
#     'conversion_rate': 0.0463,
#     'new_hosts': [...]
# }
```

---

#### `get_live_events_analytics(period: str) -> Dict[str, Any]`

**Purpose**: Get analytics for currently running/live events.

**Parameters**:
- `period` (str): Time period for trend. Options: `'weekly'`, `'monthly'`, `'yearly'`. Default: `'monthly'`

**Returns**:
```python
{
    'running_events': int,        # Total currently running events
    'events': [                   # Details for each running event
        {
            'event_id': int,
            'title': str,
            'host': str,          # Host name
            'venue': str,         # Venue name or venue_text
            'start_time': str,    # ISO datetime
            'end_time': str,      # ISO datetime
            'attendees': int,     # Current attendees count
            'revenue': float      # Total revenue from completed payments
        },
        ...
    ],
    'trend': [                   # Active events trend over time
        {
            'period': str,
            'count': int
        },
        ...
    ]
}
```

**Running Event Definition**:
- `status = 'published'`
- `start_time <= now <= end_time`

**Data Sources**:
- `events.models.Event` (filtered by status and time)
  - Fields: `id` (PK), `host_id` (FK), `venue_id` (FK, nullable), `status`, `start_time`, `end_time`, `title`
  - Joins: `select_related('host', 'venue')` → USER_PROFILE, VENUE
  - Reverse: `prefetch_related('attendance_records', 'payment_orders')`
- `attendances.models.AttendanceRecord` (for attendees count)
  - Fields: `id` (PK), `event_id` (FK), `user_id` (FK), `status`, `seats`
  - Filter: `status='going'`
- `payments.models.PaymentOrder` (for revenue, status='completed')
  - Fields: `id` (PK), `event_id` (FK), `status`, `amount`
  - Filter: `status='completed'`
  - Aggregate: `Sum('amount')`

**Exact Query**:
```python
Event.objects.filter(
    status='published',           # Exact field name
    start_time__lte=now,          # Exact field name
    end_time__gte=now             # Exact field name
).select_related('host', 'venue').prefetch_related(
    'attendance_records',         # Reverse FK relationship
    'payment_orders'              # Reverse FK relationship
)

# For each event:
event.attendance_records.filter(status='going').count()  # Exact field: status
PaymentOrder.objects.filter(
    event=event,
    status='completed'            # Exact field name
).aggregate(total=Sum('amount'))  # Exact field: amount
```

**Query Optimization**:
- Uses `select_related('host', 'venue')` for ForeignKey relationships
- Uses `prefetch_related('attendance_records', 'payment_orders')` for reverse relationships
- Aggregates revenue using `Sum()` at database level

**Example**:
```python
metrics = get_live_events_analytics(period='monthly')
# Returns:
# {
#     'running_events': 8,
#     'events': [
#         {
#             'event_id': 42,
#             'title': 'Sunday Yoga',
#             'host': 'John Doe',
#             'venue': 'Mumbai Park',
#             'attendees': 23,
#             'revenue': 5400.00
#         },
#         ...
#     ],
#     'trend': [...]
# }
```

---

#### `get_completed_events_analytics(paid_only: bool, free_only: bool) -> Dict[str, Any]`

**Purpose**: Get analytics for completed events with financial breakdown.

**Parameters**:
- `paid_only` (bool): Filter to only paid events (`is_paid=True`). Default: `False`
- `free_only` (bool): Filter to only free events (`is_paid=False`). Default: `False`

**Note**: If both are `False`, returns all completed events.

**Returns**:
```python
{
    'completed_events': [         # List of completed events
        {
            'event_id': int,
            'title': str,
            'host': str,          # Host name
            'event_date': str,    # ISO datetime
            'venue': str,         # Venue name or venue_text
            'is_paid': bool,
            'attendees': [        # List of attendees
                {
                    'name': str,
                    'phone': str,
                    'seats': int,
                    'checked_in': bool
                },
                ...
            ],
            'attendees_count': int,  # Total attendees count
            'seats_filled': int,     # Total seats filled
            'base_fare': float,      # Base ticket price
            'platform_fee': float,    # 10% platform fee
            'revenue': float,         # Gross revenue (what buyers paid)
            'host_earning': float,    # Host earnings (from payout snapshot)
            'payout_status': str,     # 'pending', 'approved', 'processing', 'completed', 'rejected', 'cancelled', 'no_request'
            'conversion_rate': float,  # Decimal (0.78 = 78%), approved_requests / total_requests
            'conversion_rate_display': float,  # For display (78.0)
            'no_show_rate': float,    # Decimal (0.11 = 11%), (going_count - checked_in_count) / going_count
            'no_show_rate_display': float  # For display (11.0)
        },
        ...
    ]
}
```

**Completed Event Definition**:
- `status = 'completed'`

**Financial Calculations**:
1. **If payout request exists** (preferred):
   - Uses snapshot data from `HostPayoutRequest`
   - `base_fare`: From payout request
   - `platform_fee`: From payout request
   - `revenue`: `final_ticket_fare * total_tickets_sold`
   - `host_earning`: From payout request

2. **If no payout request**:
   - Calculates from `PaymentOrder` records
   - `base_fare`: `Event.ticket_price`
   - `platform_fee`: `revenue * 0.10` (10%)
   - `revenue`: Sum of completed payment orders
   - `host_earning`: `revenue - platform_fee`

**Business Logic**:
- **Attendance Conversion Rate**: `approved_requests / total_requests`
- **No-Show Rate**: `(going_count - checked_in_count) / going_count`

**Data Sources**:
- `events.models.Event` (status='completed')
  - Fields: `id` (PK), `host_id` (FK), `venue_id` (FK, nullable), `status`, `is_paid`, `ticket_price`, `start_time`, `going_count`, `requests_count`, `venue_text`
  - Joins: `select_related('host', 'venue')` → USER_PROFILE, VENUE
  - Reverse: `prefetch_related('attendance_records__user', 'payment_orders', 'payout_requests')`
- `attendances.models.AttendanceRecord` (for attendees)
  - Fields: `id` (PK), `event_id` (FK), `user_id` (FK), `status`, `seats`, `checked_in_at`
  - Filter: `status='going'` or `status='checked_in'`
  - Join: `select_related('user')` → USER_PROFILE
- `payments.models.PaymentOrder` (for revenue)
  - Fields: `id` (PK), `event_id` (FK), `status`, `amount`
  - Filter: `status='completed'`
  - Aggregate: `Sum('amount')`
- `users.models.HostPayoutRequest` (for financial snapshot)
  - Fields: `id` (PK), `event_id` (FK), `base_ticket_fare`, `final_ticket_fare`, `total_tickets_sold`, `platform_fee_amount`, `final_earning`, `status`
  - Access: `event.payout_requests.first()` (reverse FK)

**Exact Query**:
```python
Event.objects.filter(
    status='completed'            # Exact field name
).select_related('host', 'venue').prefetch_related(
    'attendance_records__user',   # Reverse FK with nested join
    'payment_orders',             # Reverse FK
    'payout_requests'            # Reverse FK
)

# For each event:
attendees = event.attendance_records.filter(status='going').select_related('user')
seats_filled = sum(att.seats for att in attendees)  # Exact field: seats

completed_payments = event.payment_orders.filter(status='completed')  # Exact field: status
total_revenue = completed_payments.aggregate(total=Sum('amount'))['total']  # Exact field: amount

payout_request = event.payout_requests.first()  # Reverse FK access
if payout_request:
    base_fare = payout_request.base_ticket_fare  # Exact field name
    platform_fee = payout_request.platform_fee_amount  # Exact field name
    host_earnings = payout_request.final_earning  # Exact field name
```

**Query Optimization**:
- Uses `select_related('host', 'venue')`
- Uses `prefetch_related('attendance_records__user', 'payment_orders', 'payout_requests')`
- Aggregates seats and revenue at database level

**Example**:
```python
# Get all completed events
metrics = get_completed_events_analytics(paid_only=False, free_only=False)

# Get only paid events
metrics = get_completed_events_analytics(paid_only=True, free_only=False)

# Get only free events
metrics = get_completed_events_analytics(paid_only=False, free_only=True)
```

---

#### `get_host_deep_analytics(host_id: Optional[int]) -> Dict[str, Any]`

**Purpose**: Get deep analytics for a specific host or all hosts.

**Parameters**:
- `host_id` (Optional[int]): UserProfile ID to filter to one host. If `None`, returns all hosts. Default: `None`

**Returns**:
```python
{
    'hosts': [                    # List of host analytics
        {
            'host_id': int,       # UserProfile ID
            'name': str,          # Host name
            'events_hosted': int, # Total events created
            'breakdown': {        # Events by status
                'draft': int,
                'published': int,
                'cancelled': int,
                'completed': int
            },
            'lifetime_revenue': float,    # Total revenue from all events
            'lifetime_earnings': float,  # Total earnings from payout requests
            'platform_fees': float,      # Total platform fees generated
            'events_performance': [      # Performance per event
                {
                    'event_id': int,
                    'title': str,
                    'status': str,
                    'seats_sold': int,
                    'revenue': float,
                    'payment_success_rate': float,  # Percentage
                    'check_in_rate': float          # Percentage
                },
                ...
            ],
            'payout_requests_count': int,
            'payout_status_summary': {   # Payout requests by status
                'pending': int,
                'approved': int,
                ...
            },
            'engagement_score': float    # Composite score (0-100)
        },
        ...
    ],
    'total_hosts_analyzed': int
}
```

**Engagement Score Calculation**:

Formula: `(events_factor * 0.4) + (attendance_rate_factor * 0.3) + (revenue_factor * 0.3)`

**Components**:
1. **Events Factor** (0-40 points):
   - Normalized: `(total_events / 20.0) * 40`
   - Max 20 events = 40 points
   - Capped at 40

2. **Attendance Rate Factor** (0-30 points):
   - Average check-in rate across completed events
   - Formula: `(avg_attendance_rate / 100.0) * 30`
   - Max 100% attendance = 30 points

3. **Revenue Factor** (0-30 points):
   - Normalized: `(lifetime_revenue / 100000.0) * 30`
   - Max ₹100,000 = 30 points
   - Capped at 30

**Total Score**: 0-100 (sum of all factors)

**Data Sources**:
- `users.models.UserProfile` (hosts)
  - Fields: `id` (PK), `user_id` (FK), `name`
  - Join: `select_related('user')` → AUTH_USER
  - Reverse: `prefetch_related('hosted_events', ...)` → EVENT
- `events.models.Event` (hosted events)
  - Fields: `id` (PK), `host_id` (FK), `status`, `going_count`
  - Reverse: `hosted_events` → EVENT (via `Event.host`)
- `attendances.models.AttendanceRecord` (attendance)
  - Fields: `id` (PK), `event_id` (FK), `status`, `seats`
  - Filter: `status='going'` or `status='checked_in'`
  - Aggregate: `Sum('seats')`
- `payments.models.PaymentOrder` (revenue)
  - Fields: `id` (PK), `event_id` (FK), `status`, `amount`
  - Filter: `status='completed'`
  - Aggregate: `Sum('amount')`
- `users.models.HostPayoutRequest` (earnings)
  - Fields: `id` (PK), `event_id` (FK), `final_earning`, `platform_fee_amount`, `status`
  - Filter: `event__host=host` (via Event.host FK)
  - Aggregate: `Sum('final_earning')`, `Sum('platform_fee_amount')`

**Exact Query**:
```python
UserProfile.objects.filter(
    hosted_events__isnull=False  # Reverse FK filter
).distinct().select_related('user').prefetch_related(
    'hosted_events',                                    # Reverse FK
    'hosted_events__attendance_records',                # Nested reverse FK
    'hosted_events__payment_orders',                    # Nested reverse FK
    'hosted_events__payout_requests'                    # Nested reverse FK
)

# For each host:
events = host.hosted_events.all()  # Reverse FK access
event_summary = {
    'draft': events.filter(status='draft').count(),      # Exact field: status
    'published': events.filter(status='published').count(),
    'cancelled': events.filter(status='cancelled').count(),
    'completed': events.filter(status='completed').count()
}

# For each event:
seats_sold = event.attendance_records.filter(
    status='going'  # Exact field name
).aggregate(total=Sum('seats'))['total']  # Exact field: seats

event_revenue = event.payment_orders.filter(
    status='completed'  # Exact field name
).aggregate(total=Sum('amount'))['total']  # Exact field: amount

checked_in_count = event.attendance_records.filter(
    status='checked_in'  # Exact field name
).count()

# Payout requests:
HostPayoutRequest.objects.filter(
    event__host=host  # Via Event.host FK
).select_related('event').aggregate(
    total=Sum('final_earning')  # Exact field name
)
```

**Query Optimization**:
- Uses `select_related('user')` for host user
- Uses `prefetch_related('hosted_events', 'hosted_events__attendance_records', ...)` for all related data
- Aggregates at database level where possible

**Example**:
```python
# Get analytics for all hosts
all_hosts = get_host_deep_analytics(host_id=None)

# Get analytics for specific host
host_92 = get_host_deep_analytics(host_id=92)
```

---

## API Endpoints

### Base URL

All endpoints are under `/django/admin/dashboard/`

### Authentication

All endpoints require:
- User must be logged in
- User must have `is_staff=True`
- Returns `403 Forbidden` if unauthorized

---

### 1. Dashboard View

**Endpoint**: `GET /django/admin/dashboard/`

**Purpose**: Main dashboard HTML page.

**Query Parameters**:
- `period` (optional): `'weekly'`, `'monthly'`, or `'yearly'`. Default: `'monthly'`
- `paid_only` (optional): `'true'` or `'false'`. Filter completed events to paid only. Default: `'false'`
- `free_only` (optional): `'true'` or `'false'`. Filter completed events to free only. Default: `'false'`
- `host_id` (optional): Integer. Filter host analytics to specific host. Default: `None`

**Response**: HTML page with dashboard

**Example**:
```
GET /django/admin/dashboard/?period=monthly&paid_only=false
```

---

### 2. Users API

**Endpoint**: `GET /django/admin/dashboard/api/users`

**Purpose**: Get user lifecycle metrics as JSON.

**Query Parameters**:
- `period` (optional): `'weekly'`, `'monthly'`, or `'yearly'`. Default: `'monthly'`
- `limit` (optional): Integer. Maximum number of trend data points to return. Default: `100`. Max: `1000`
- `offset` (optional): Integer. Number of trend data points to skip. Default: `0`

**Response**:
```json
{
    "total_users": 3110,
    "active_users": 2870,
    "waitlisted_users": 240,
    "approval_rate": 0.9228,
    "trend": [
        {
            "period": "2025-01-01T00:00:00Z",
            "total": 41,
            "active": 38,
            "waitlisted": 3
        }
    ],
    "pagination": {
        "limit": 100,
        "offset": 0,
        "total": 150,
        "has_more": true
    }
}
```

**Pagination**:
- `limit`: Maximum items returned (default: 100, max: 1000)
- `offset`: Items skipped (default: 0)
- `total`: Total number of trend data points available
- `has_more`: Boolean indicating if more data is available

**Status Codes**:
- `200 OK`: Success
- `403 Forbidden`: User not staff
- `500 Internal Server Error`: Server error (includes error message)

**Example**:
```bash
curl -H "Cookie: sessionid=..." \
     "http://localhost:8000/django/admin/dashboard/api/users?period=monthly"
```

---

### 3. Events API

**Endpoint**: `GET /django/admin/dashboard/api/events`

**Purpose**: Get events analytics (live or completed) as JSON.

**Query Parameters**:
- `type` (required): `'live'` or `'completed'`
- `period` (optional): `'weekly'`, `'monthly'`, or `'yearly'`. Default: `'monthly'` (only for live events)
- `paid_only` (optional): `'true'` or `'false'`. Only for `type=completed`. Default: `'false'`
- `free_only` (optional): `'true'` or `'false'`. Only for `type=completed`. Default: `'false'`
- `limit` (optional): Integer. Maximum number of events to return. Default: `50`. Max: `500`
- `offset` (optional): Integer. Number of events to skip. Default: `0`

**Response for `type=live`**:
```json
{
    "running_events": 8,
    "events": [
        {
            "event_id": 42,
            "title": "Sunday Yoga",
            "host": "John Doe",
            "venue": "Mumbai Park",
            "start_time": "2025-01-15T10:00:00Z",
            "end_time": "2025-01-15T12:00:00Z",
            "attendees": 23,
            "revenue": 5400.00
        }
    ],
    "trend": [...],
    "pagination": {
        "limit": 50,
        "offset": 0,
        "total": 8,
        "has_more": false
    }
}
```

**Pagination**:
- `limit`: Maximum events returned (default: 50, max: 500)
- `offset`: Events skipped (default: 0)
- `total`: Total number of events matching criteria
- `has_more`: Boolean indicating if more events are available

**Response for `type=completed`**:
```json
{
    "completed_events": [
        {
            "event_id": 35,
            "title": "Music Night",
            "host": "John Doe",
            "event_date": "2025-01-10T19:00:00Z",
            "venue": "Mumbai Theater",
            "is_paid": true,
            "attendees": [...],
            "attendees_count": 89,
            "seats_filled": 89,
            "base_fare": 200.00,
            "platform_fee": 1800.00,
            "revenue": 17800.00,
            "host_earning": 16000.00,
            "payout_status": "completed",
            "conversion_rate": 0.78,
            "conversion_rate_display": 78.0,
            "no_show_rate": 0.11,
            "no_show_rate_display": 11.0
        }
    ],
    "pagination": {
        "limit": 50,
        "offset": 0,
        "total": 245,
        "has_more": true
    }
}
```

**Pagination**:
- `limit`: Maximum events returned (default: 50, max: 500)
- `offset`: Events skipped (default: 0)
- `total`: Total number of completed events matching filters
- `has_more`: Boolean indicating if more events are available

**Status Codes**:
- `200 OK`: Success
- `400 Bad Request`: Invalid `type` parameter
- `403 Forbidden`: User not staff
- `500 Internal Server Error`: Server error

**Example**:
```bash
# Get live events (first 50)
curl "http://localhost:8000/django/admin/dashboard/api/events?type=live&period=monthly"

# Get completed paid events with pagination
curl "http://localhost:8000/django/admin/dashboard/api/events?type=completed&paid_only=true&limit=100&offset=0"

# Get next page
curl "http://localhost:8000/django/admin/dashboard/api/events?type=completed&limit=100&offset=100"
```

---

### 4. Hosts API

**Endpoint**: `GET /django/admin/dashboard/api/hosts`

**Purpose**: Get host metrics and deep analytics as JSON.

**Query Parameters**:
- `period` (optional): `'weekly'`, `'monthly'`, or `'yearly'`. Default: `'monthly'`
- `host_id` (optional): Integer. Filter to specific host. Default: `None` (all hosts)
- `limit` (optional): Integer. Maximum number of hosts to return. Default: `50`. Max: `500`
- `offset` (optional): Integer. Number of hosts to skip. Default: `0`

**Response**:
```json
{
    "total_hosts": 133,
    "conversion_rate": 0.0463,
    "new_hosts": [...],
    "hosts": [
        {
            "host_id": 92,
            "name": "Amit Verma",
            "events_hosted": 14,
            "breakdown": {
                "draft": 2,
                "published": 8,
                "cancelled": 1,
                "completed": 3
            },
            "lifetime_revenue": 94000.00,
            "lifetime_earnings": 78000.00,
            "platform_fees": 16000.00,
            "events_performance": [...],
            "payout_requests_count": 3,
            "payout_status_summary": {
                "completed": 2,
                "pending": 1
            },
            "engagement_score": 78.4
        }
    ],
    "pagination": {
        "limit": 50,
        "offset": 0,
        "total": 133,
        "has_more": true
    }
}
```

**Pagination**:
- `limit`: Maximum hosts returned (default: 50, max: 500)
- `offset`: Hosts skipped (default: 0)
- `total`: Total number of hosts (or 1 if `host_id` specified)
- `has_more`: Boolean indicating if more hosts are available

**Status Codes**:
- `200 OK`: Success
- `403 Forbidden`: User not staff
- `500 Internal Server Error`: Server error

**Example**:
```bash
# Get all hosts (first 50)
curl "http://localhost:8000/django/admin/dashboard/api/hosts?period=monthly"

# Get specific host
curl "http://localhost:8000/django/admin/dashboard/api/hosts?host_id=92"

# Get hosts with pagination
curl "http://localhost:8000/django/admin/dashboard/api/hosts?limit=100&offset=50"
```

**Pagination Best Practices**:
- Use `limit` to control response size (default: 50)
- Use `offset` for pagination (increment by `limit` value)
- Check `has_more` to determine if more requests are needed
- Maximum `limit` is 500 to prevent performance issues
- For large datasets, implement cursor-based pagination (future enhancement)

---

### 5. Legacy Unified API

**Endpoint**: `GET /django/admin/dashboard/api/`

**Purpose**: Legacy endpoint for backward compatibility. Use specific endpoints instead.

**Query Parameters**:
- `metric_type` (required): `'user_lifecycle'`, `'waitlist'`, `'hosts'`, `'live_events'`, `'completed_events'`, or `'host_deep'`
- `period` (optional): `'weekly'`, `'monthly'`, or `'yearly'`. Default: `'monthly'`
- `paid_only` (optional): For `completed_events`. Default: `'false'`
- `free_only` (optional): For `completed_events`. Default: `'false'`
- `host_id` (optional): For `host_deep`. Default: `None`

**Response**: Same as specific endpoints based on `metric_type`

**Example**:
```bash
curl "http://localhost:8000/django/admin/dashboard/api/?metric_type=user_lifecycle&period=monthly"
```

---

## Data Structures

### User Lifecycle Metrics

```python
{
    'total_users': int,           # All registered users
    'active_users': int,          # is_active=True
    'waitlisted_users': int,      # is_active=False
    'approval_rate': float,       # Decimal (0.92 = 92%)
    'trend': [
        {
            'period': str,         # ISO date string
            'total': int,
            'active': int,
            'waitlisted': int
        }
    ]
}
```

### Waitlist Metrics

```python
{
    'total_waitlisted': int,
    'approval_rate': float,       # Percentage (92.28)
    'trend': [
        {
            'period': str,
            'count': int
        }
    ]
}
```

### Host Metrics

```python
{
    'total_hosts': int,
    'conversion_rate': float,     # Decimal (0.046 = 4.6%)
    'new_hosts': [
        {
            'period': str,
            'count': int
        }
    ]
}
```

### Live Events

```python
{
    'running_events': int,
    'events': [
        {
            'event_id': int,
            'title': str,
            'host': str,
            'venue': str,
            'start_time': str,    # ISO datetime
            'end_time': str,      # ISO datetime
            'attendees': int,
            'revenue': float
        }
    ],
    'trend': [...]
}
```

### Completed Events

```python
{
    'completed_events': [
        {
            'event_id': int,
            'title': str,
            'host': str,
            'event_date': str,    # ISO datetime
            'venue': str,
            'is_paid': bool,
            'attendees': [
                {
                    'name': str,
                    'phone': str,
                    'seats': int,
                    'checked_in': bool
                }
            ],
            'attendees_count': int,
            'seats_filled': int,
            'base_fare': float,
            'platform_fee': float,
            'revenue': float,
            'host_earning': float,
            'payout_status': str,
            'conversion_rate': float,      # Decimal
            'conversion_rate_display': float,  # Percentage
            'no_show_rate': float,         # Decimal
            'no_show_rate_display': float  # Percentage
        }
    ]
}
```

### Host Deep Analytics

```python
{
    'hosts': [
        {
            'host_id': int,
            'name': str,
            'events_hosted': int,
            'breakdown': {
                'draft': int,
                'published': int,
                'cancelled': int,
                'completed': int
            },
            'lifetime_revenue': float,
            'lifetime_earnings': float,
            'platform_fees': float,
            'events_performance': [
                {
                    'event_id': int,
                    'title': str,
                    'status': str,
                    'seats_sold': int,
                    'revenue': float,
                    'payment_success_rate': float,
                    'check_in_rate': float
                }
            ],
            'payout_requests_count': int,
            'payout_status_summary': {
                'pending': int,
                'approved': int,
                'processing': int,
                'completed': int,
                'rejected': int,
                'cancelled': int
            },
            'engagement_score': float  # 0-100
        }
    ],
    'total_hosts_analyzed': int
}
```

---

## Business Logic & Calculations

### User Lifecycle

**Waitlist → Approval Flow**:
1. User registers → `User` and `UserProfile` created
2. `User.is_active = False` (waitlist state)
3. Admin approves → `User.is_active = True` (active user)

**Approval Rate**:
```
approval_rate = active_users / total_users
```

**Example**: 2870 active / 3110 total = 0.9228 (92.28%)

---

### Host Conversion

**Host Definition**: User who has created at least one event.

**Conversion Rate**:
```
conversion_rate = total_hosts / active_users
```

**Example**: 133 hosts / 2870 active users = 0.0463 (4.63%)

---

### Financial Calculations

**Platform Fee Model**:
- Buyer pays: `Base ticket fare + 10% platform fee`
- Host earns: `Base ticket fare × Tickets sold` (no platform fee deduction)
- Platform fee: `Base ticket fare × 10% × Tickets sold` (collected from buyers)

**Example**:
- Base fare: ₹100
- Tickets sold: 50
- Final ticket fare (buyer pays): ₹110 per ticket
- Host earnings: ₹100 × 50 = ₹5,000
- Platform fee: ₹10 × 50 = ₹500
- Gross revenue: ₹110 × 50 = ₹5,500

**Revenue Calculation**:
- If payout request exists: Uses snapshot from `HostPayoutRequest`
- If no payout request: Calculates from `PaymentOrder` records

---

### Engagement Score

**Formula**: `(events_factor × 0.4) + (attendance_rate_factor × 0.3) + (revenue_factor × 0.3)`

**Components**:
1. **Events Factor** (0-40 points):
   ```
   events_factor = min((total_events / 20.0) * 40, 40)
   ```

2. **Attendance Rate Factor** (0-30 points):
   ```
   avg_attendance_rate = average(check_in_count / going_count) across completed events
   attendance_rate_factor = (avg_attendance_rate / 100.0) * 30
   ```

3. **Revenue Factor** (0-30 points):
   ```
   revenue_factor = min((lifetime_revenue / 100000.0) * 30, 30)
   ```

**Total**: 0-100 points

**Example**:
- 14 events → 28 points (14/20 * 40)
- 85% avg attendance → 25.5 points (85/100 * 30)
- ₹94,000 revenue → 28.2 points (94000/100000 * 30)
- **Total**: 81.7 engagement score

---

### Attendance Metrics

**Conversion Rate**:
```
conversion_rate = approved_requests / total_requests
```

**No-Show Rate**:
```
no_show_rate = (going_count - checked_in_count) / going_count
```

---

## Query Optimization

### Principles

1. **Use `select_related()`** for ForeignKey relationships
2. **Use `prefetch_related()`** for ManyToMany and reverse ForeignKey
3. **Aggregate at database level** using `Count()`, `Sum()`, `Avg()`
4. **Use date truncation functions** for time-series grouping
5. **Filter early** to reduce queryset size

### Examples

**Good** (Optimized):
```python
events = Event.objects.filter(
    status='published'
).select_related('host', 'venue').prefetch_related(
    'attendance_records',
    'payment_orders'
)
```

**Bad** (N+1 Queries):
```python
events = Event.objects.filter(status='published')
for event in events:
    host_name = event.host.name  # N+1 query!
    revenue = event.payment_orders.all()  # N+1 query!
```

### Performance Tips

- All services use optimized queries
- Consider Redis caching for expensive queries
- Monitor query count using Django Debug Toolbar
- Use database indexes on frequently filtered fields

---

## Error Handling

### Service Layer

All service functions are wrapped in try-except blocks in views. On error:
- Logs error with full traceback
- Returns empty/default metrics
- Never crashes the dashboard

### API Endpoints

**Status Codes**:
- `200 OK`: Success
- `400 Bad Request`: Invalid parameters
- `403 Forbidden`: Unauthorized (not staff)
- `500 Internal Server Error`: Server error

**Error Response Format**:
```json
{
    "error": "Error message here"
}
```

### Dashboard View

On error:
- Logs error
- Displays empty metrics
- Shows graceful fallback UI
- Never shows stack trace to user

---

## Testing

### Manual Testing Checklist

1. **Access Control**:
   - [ ] Staff user can access dashboard
   - [ ] Non-staff user receives 403 Forbidden
   - [ ] Unauthenticated user redirected to login

2. **Period Filters**:
   - [ ] Weekly filter works
   - [ ] Monthly filter works
   - [ ] Yearly filter works
   - [ ] Invalid period defaults to monthly

3. **User Lifecycle**:
   - [ ] Total users count correct
   - [ ] Active users count correct
   - [ ] Waitlisted users count correct
   - [ ] Approval rate calculation correct
   - [ ] Trend graph displays correctly

4. **Waitlist Metrics**:
   - [ ] Waitlist count correct
   - [ ] Approval rate correct
   - [ ] Trend graph displays

5. **Host Metrics**:
   - [ ] Total hosts count correct
   - [ ] Conversion rate correct
   - [ ] New hosts trend displays

6. **Live Events**:
   - [ ] Only running events shown
   - [ ] Attendees count correct
   - [ ] Revenue calculation correct
   - [ ] Trend graph displays

7. **Completed Events**:
   - [ ] Only completed events shown
   - [ ] Paid filter works
   - [ ] Free filter works
   - [ ] Financial calculations correct
   - [ ] Payout status correct
   - [ ] Conversion rate correct
   - [ ] No-show rate correct

8. **Host Deep Analytics**:
   - [ ] All hosts shown when host_id not provided
   - [ ] Specific host shown when host_id provided
   - [ ] Engagement score calculation correct
   - [ ] Financial metrics correct

9. **API Endpoints**:
   - [ ] `/api/users` returns correct data
   - [ ] `/api/events?type=live` returns correct data
   - [ ] `/api/events?type=completed` returns correct data
   - [ ] `/api/hosts` returns correct data
   - [ ] All endpoints require staff access

10. **Error Cases**:
    - [ ] Empty database shows zeros
    - [ ] No events shows empty lists
    - [ ] Invalid parameters handled gracefully
    - [ ] Server errors don't crash dashboard

### Automated Testing

Create unit tests in `analytics/tests.py`:

```python
from django.test import TestCase
from analytics.services import get_user_lifecycle_metrics

class AnalyticsServicesTest(TestCase):
    def test_user_lifecycle_metrics(self):
        # Create test data
        # Call service function
        # Assert expected results
        pass
```

---

## Troubleshooting

### Dashboard Not Loading

**Symptoms**: 404 or 500 error when accessing dashboard

**Solutions**:
1. Check `analytics` is in `INSTALLED_APPS`
2. Check `analytics/admin.py` is imported (check `apps.py`)
3. Check URL routing (should be patched automatically)
4. Check user has `is_staff=True`
5. Check Django logs for errors

### Metrics Showing Zero

**Symptoms**: All metrics show 0 or empty

**Solutions**:
1. Check database has data
2. Check user permissions (staff access)
3. Check Django logs for errors
4. Verify models are correct
5. Check date filters (period parameter)

### Slow Performance

**Symptoms**: Dashboard loads slowly

**Solutions**:
1. Check query count (use Django Debug Toolbar)
2. Verify `select_related` and `prefetch_related` are used
3. Add database indexes on filtered fields
4. Consider Redis caching for expensive queries
5. Optimize time-series queries

### Charts Not Displaying

**Symptoms**: Charts are blank or broken

**Solutions**:
1. Check Chart.js CDN is accessible
2. Check browser console for JavaScript errors
3. Verify JSON data is properly serialized
4. Check template rendering (view page source)
5. Verify data format matches Chart.js expectations

### API Returns 403

**Symptoms**: API endpoints return 403 Forbidden

**Solutions**:
1. Check user is logged in
2. Check user has `is_staff=True`
3. Verify authentication cookies are sent
4. Check `@staff_required` decorator is applied

### Financial Calculations Incorrect

**Symptoms**: Revenue, fees, or earnings are wrong

**Solutions**:
1. Verify `Decimal` type is used (not `float`)
2. Check platform fee calculation (10%)
3. Verify payout request snapshot data
4. Check payment order status filtering
5. Verify currency handling

---

## Future Expansion

### Reserved Panels

The dashboard includes placeholders for:

1. **Event Category Performance**:
   - Analytics by event interest/category
   - Popular categories
   - Revenue by category

2. **Revenue Forecasting** (ML-ready):
   - Predictive analytics
   - Revenue projections
   - Growth trends

3. **User Churn Prediction**:
   - Churn analysis
   - Retention metrics
   - Re-engagement opportunities

4. **Host Ranking Leaderboard**:
   - Top hosts by engagement
   - Top hosts by revenue
   - Top hosts by events hosted

### Implementation Guidelines

When adding new metrics:

1. **Add service function** in `analytics/services.py`
2. **Add API endpoint** in `analytics/admin.py`
3. **Add template section** in `dashboard.html`
4. **Update this documentation**
5. **Add tests** in `analytics/tests.py`

### Caching Strategy

For production, consider Redis caching:

```python
from django.core.cache import cache

def get_user_lifecycle_metrics(period='monthly'):
    cache_key = f'analytics:user_lifecycle:{period}'
    cached = cache.get(cache_key)
    if cached:
        return cached
    
    # Calculate metrics
    data = {...}
    
    # Cache for 5 minutes
    cache.set(cache_key, data, 300)
    return data
```

---

## Dependencies

### Required

- Django (built-in admin)
- Chart.js (loaded via CDN)
- Python `decimal` module (for financial precision)

### Optional

- Redis (for caching)
- Django Debug Toolbar (for development)

---

## Support & Maintenance

### Logging

All errors are logged using Python's `logging` module:
- Logger name: `analytics`
- Log level: `ERROR` for exceptions
- Includes full traceback

### Monitoring

Monitor:
- Dashboard load time
- API response times
- Query count per request
- Error rates

### Updates

When updating:
1. Test all metrics
2. Verify query optimization
3. Update documentation
4. Check backward compatibility

---

## Appendix: Field Name Quick Reference

### Critical Field Names (DO NOT GUESS)

| Model | Field | Type | Usage |
|-------|-------|------|-------|
| `User` | `id` | PK | Primary key |
| `User` | `is_active` | Boolean | Waitlist status (False=waitlisted, True=active) |
| `User` | `date_joined` | DATETIME | Time-series grouping |
| `UserProfile` | `id` | PK | Primary key |
| `UserProfile` | `user_id` | FK | → AUTH_USER.id |
| `UserProfile` | `name` | String | Host/user name |
| `Event` | `id` | PK | Primary key |
| `Event` | `host_id` | FK | → USER_PROFILE.id |
| `Event` | `venue_id` | FK | → VENUE.id (nullable) |
| `Event` | `status` | String | 'draft', 'published', 'cancelled', 'completed', 'postponed' |
| `Event` | `is_paid` | Boolean | Paid vs free event |
| `Event` | `ticket_price` | Decimal | Base ticket fare |
| `Event` | `start_time` | DATETIME | Event start |
| `Event` | `end_time` | DATETIME | Event end |
| `Event` | `going_count` | Integer | Confirmed attendees |
| `Event` | `requests_count` | Integer | Pending requests |
| `Event` | `venue_text` | String | Custom venue (if venue_id is null) |
| `AttendanceRecord` | `id` | PK | Primary key |
| `AttendanceRecord` | `event_id` | FK | → EVENT.id |
| `AttendanceRecord` | `user_id` | FK | → USER_PROFILE.id |
| `AttendanceRecord` | `status` | String | 'going', 'not_going', 'maybe', 'checked_in', 'cancelled' |
| `AttendanceRecord` | `seats` | Integer | Number of seats |
| `AttendanceRecord` | `checked_in_at` | DATETIME | Check-in timestamp |
| `PaymentOrder` | `id` | PK | Primary key |
| `PaymentOrder` | `event_id` | FK | → EVENT.id |
| `PaymentOrder` | `user_id` | FK | → USER_PROFILE.id |
| `PaymentOrder` | `status` | String | 'created', 'pending', 'paid', 'completed', 'failed', etc. |
| `PaymentOrder` | `amount` | Decimal | Payment amount |
| `HostPayoutRequest` | `id` | PK | Primary key |
| `HostPayoutRequest` | `event_id` | FK | → EVENT.id |
| `HostPayoutRequest` | `base_ticket_fare` | Decimal | Base ticket price (snapshot) |
| `HostPayoutRequest` | `final_ticket_fare` | Decimal | Final price with fee (snapshot) |
| `HostPayoutRequest` | `total_tickets_sold` | Integer | Tickets sold (snapshot) |
| `HostPayoutRequest` | `platform_fee_amount` | Decimal | Platform fee (snapshot) |
| `HostPayoutRequest` | `final_earning` | Decimal | Host earnings (snapshot) |
| `HostPayoutRequest` | `status` | String | 'pending', 'approved', 'processing', 'completed', etc. |

### Reverse Relationship Names

| Model | Reverse Relationship | Access Pattern |
|-------|---------------------|----------------|
| `Event` | `attendance_records` | `event.attendance_records.all()` |
| `Event` | `payment_orders` | `event.payment_orders.all()` |
| `Event` | `payout_requests` | `event.payout_requests.all()` |
| `UserProfile` | `hosted_events` | `host.hosted_events.all()` |
| `User` | `profile` | `user.profile` (OneToOne) |

**⚠️ IMPORTANT**: Always use exact field names from this reference. Guessing field names will cause bugs.

### Pagination Implementation Notes

**Current Status**: Pagination parameters are documented but not yet implemented in services layer.

**To Implement**:
1. Add `limit` and `offset` parameters to service functions
2. Apply `.limit()` and `.offset()` to querysets
3. Calculate `total` count before pagination
4. Return `has_more` boolean
5. Add pagination metadata to response

**Example Implementation**:
```python
def get_completed_events_analytics(
    paid_only: bool = False,
    free_only: bool = False,
    limit: int = 50,
    offset: int = 0
) -> Dict[str, Any]:
    # ... existing code ...
    
    # Apply pagination
    total_count = completed_events.count()
    paginated_events = completed_events[offset:offset + limit]
    
    # ... process events ...
    
    return {
        'completed_events': events_detail,
        'pagination': {
            'limit': limit,
            'offset': offset,
            'total': total_count,
            'has_more': (offset + limit) < total_count
        }
    }
```

---

**Last Updated**: 2025-01-XX
**Version**: 1.0.0
**Status**: Production Ready ✅
