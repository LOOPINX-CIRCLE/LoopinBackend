# Flutter Integration Guide - Events & Payouts API

**For Android Developers Using Flutter (Dart)**

This guide explains how to integrate the Loopin Backend API into your Flutter mobile app. Follow this guide exactly. Do not invent fields or add business logic on the frontend.

---

## API Flow Charts

### Complete User Flow Overview

```mermaid
flowchart TD
    Start([User Opens App]) --> Auth{User Authenticated?}
    Auth -->|No| Login[Login/Signup Flow]
    Auth -->|Yes| Role{User Role?}
    
    Login --> Role
    
    Role -->|Attendee| AttendeeFlow[Attendee Flow]
    Role -->|Host| HostFlow[Host Flow]
    Role -->|Both| BothFlow[Can Access Both Flows]
    
    AttendeeFlow --> BrowseEvents[GET /events<br/>Browse Events]
    BrowseEvents --> ViewEvent[GET /events/{id}<br/>View Event Details]
    ViewEvent --> CheckRequest{Has Request?}
    
    CheckRequest -->|No| RequestJoin[POST /events/{id}/requests<br/>Request to Join]
    CheckRequest -->|Yes| CheckStatus[GET /events/{id}/my-request<br/>Check Request Status]
    
    RequestJoin --> CheckStatus
    CheckStatus --> Status{Status?}
    
    Status -->|Pending| WaitPending[Show: Request Pending]
    Status -->|Accepted| Confirm[POST /events/{id}/confirm-attendance<br/>Confirm Attendance]
    Status -->|Declined| ShowDeclined[Show: Request Declined]
    
    Confirm --> ViewTicket[GET /events/{id}/my-ticket<br/>View Ticket]
    ViewTicket --> AllTickets[GET /events/my-tickets<br/>View All Tickets]
    
    HostFlow --> CreateEvent[POST /events<br/>Create Event]
    CreateEvent --> ManageRequests[GET /events/{id}/requests<br/>View Requests]
    ManageRequests --> ProcessRequest{Process Request?}
    
    ProcessRequest -->|Accept| AcceptReq[PUT /events/{id}/requests/{req_id}/accept<br/>Accept Request]
    ProcessRequest -->|Decline| DeclineReq[PUT /events/{id}/requests/{req_id}/decline<br/>Decline Request]
    ProcessRequest -->|Bulk| BulkAction[POST /events/{id}/requests/bulk-action<br/>Bulk Accept/Decline]
    
    AcceptReq --> ManageRequests
    DeclineReq --> ManageRequests
    BulkAction --> ManageRequests
    
    HostFlow --> PayoutFlow[Payout Flow]
    PayoutFlow --> BankAccounts[GET /payouts/bank-accounts<br/>List Bank Accounts]
    BankAccounts --> BankAction{Action?}
    
    BankAction -->|Add| AddBank[POST /payouts/bank-accounts<br/>Add Bank Account]
    BankAction -->|Edit| EditBank[PUT /payouts/bank-accounts/{id}<br/>Update Bank Account]
    BankAction -->|Delete| DeleteBank[DELETE /payouts/bank-accounts/{id}<br/>Delete Bank Account]
    
    AddBank --> CreatePayout[POST /payouts/requests<br/>Create Payout Request]
    EditBank --> CreatePayout
    DeleteBank --> BankAccounts
    
    CreatePayout --> ListPayouts[GET /payouts/requests<br/>List Payout Requests]
    ListPayouts --> ViewPayout[GET /payouts/requests/{id}<br/>View Payout Details]
    
    BothFlow --> InvitationFlow[Invitation Flow]
    InvitationFlow --> MyInvites[GET /events/my-invitations<br/>View My Invitations]
    MyInvites --> RespondInvite{Respond?}
    
    RespondInvite -->|Accept| AcceptInvite[PUT /events/invitations/{id}/respond<br/>Accept Invitation]
    RespondInvite -->|Decline| DeclineInvite[PUT /events/invitations/{id}/respond<br/>Decline Invitation]
    
    AcceptInvite --> ViewTicket
    DeclineInvite --> MyInvites
    
    style AttendeeFlow fill:#e1f5ff
    style HostFlow fill:#fff4e1
    style PayoutFlow fill:#ffe1f5
    style InvitationFlow fill:#e1ffe1
```

### Attendee Flow (Step-by-Step)

```mermaid
flowchart LR
    A[1. GET /events<br/>Browse Events List] --> B[2. GET /events/{id}<br/>View Event Details]
    B --> C{User Action?}
    
    C -->|Request to Join| D[3. POST /events/{id}/requests<br/>Request to Join]
    C -->|Check Status| E[4. GET /events/{id}/my-request<br/>Check Request Status]
    
    D --> E
    E --> F{Request Status?}
    
    F -->|Pending| G[Show: Waiting for Host]
    F -->|Accepted| H[5. POST /events/{id}/confirm-attendance<br/>Confirm Attendance]
    F -->|Declined| I[Show: Request Declined]
    
    H --> J[6. GET /events/{id}/my-ticket<br/>View Ticket]
    J --> K[7. GET /events/my-tickets<br/>View All Tickets]
    
    style A fill:#e3f2fd
    style B fill:#e3f2fd
    style D fill:#fff3e0
    style E fill:#fff3e0
    style H fill:#e8f5e9
    style J fill:#e8f5e9
    style K fill:#e8f5e9
```

### Host Flow (Step-by-Step)

```mermaid
flowchart TD
    A[1. GET /events/venues<br/>List Venues] --> B{Create Venue?}
    
    B -->|Yes| C[2. POST /events/venues<br/>Create Venue]
    B -->|No| D[3. POST /events<br/>Create Event]
    C --> D
    
    D --> E[4. GET /events/{id}/requests<br/>View Event Requests]
    E --> F{Action on Request?}
    
    F -->|Accept Single| G[5. PUT /events/{id}/requests/{req_id}/accept<br/>Accept Request]
    F -->|Decline Single| H[6. PUT /events/{id}/requests/{req_id}/decline<br/>Decline Request]
    F -->|Bulk Action| I[7. POST /events/{id}/requests/bulk-action<br/>Bulk Accept/Decline]
    
    G --> E
    H --> E
    I --> E
    
    D --> J[8. POST /events/{id}/invitations<br/>Invite Users]
    J --> K[9. GET /events/{id}/invitations<br/>View Sent Invitations]
    
    D --> L[10. PUT /events/{id}<br/>Update Event]
    D --> M[11. DELETE /events/{id}<br/>Delete Event]
    
    style A fill:#e3f2fd
    style C fill:#fff3e0
    style D fill:#fff3e0
    style E fill:#e8f5e9
    style G fill:#c8e6c9
    style H fill:#ffcdd2
    style I fill:#e8f5e9
```

### Payout Flow (Host Only)

```mermaid
flowchart TD
    A[1. GET /payouts/bank-accounts<br/>List Bank Accounts] --> B{Has Bank Account?}
    
    B -->|No| C[2. POST /payouts/bank-accounts<br/>Add Bank Account]
    B -->|Yes| D{Action?}
    
    C --> D
    D -->|Edit| E[3. PUT /payouts/bank-accounts/{id}<br/>Update Bank Account]
    D -->|Delete| F[4. DELETE /payouts/bank-accounts/{id}<br/>Delete Bank Account]
    D -->|Create Payout| G[5. POST /payouts/requests<br/>Create Payout Request]
    
    E --> G
    F --> A
    
    G --> H[6. GET /payouts/requests<br/>List Payout Requests]
    H --> I[7. GET /payouts/requests/{id}<br/>View Payout Details]
    
    style A fill:#e3f2fd
    style C fill:#fff3e0
    style E fill:#fff3e0
    style F fill:#ffcdd2
    style G fill:#e8f5e9
    style H fill:#e3f2fd
    style I fill:#e3f2fd
```

### Invitation Flow

```mermaid
flowchart LR
    A[1. GET /events/my-invitations<br/>View My Invitations] --> B{Invitation Status?}
    
    B -->|Pending| C{User Action?}
    B -->|Accepted| D[Already Accepted<br/>View Event/Ticket]
    B -->|Declined| E[Already Declined]
    B -->|Expired| F[Invitation Expired]
    
    C -->|Accept| G[2. PUT /events/invitations/{id}/respond<br/>Response: going]
    C -->|Decline| H[2. PUT /events/invitations/{id}/respond<br/>Response: not_going]
    
    G --> I{Event is Paid?}
    I -->|Yes| J[Navigate to Payment]
    I -->|No| K[View Ticket]
    
    H --> E
    J --> K
    
    style A fill:#e3f2fd
    style G fill:#c8e6c9
    style H fill:#ffcdd2
    style K fill:#e8f5e9
```

### API Call Decision Tree

```mermaid
flowchart TD
    Start([User Action]) --> Screen{Which Screen?}
    
    Screen -->|Events List| Browse[GET /events]
    Screen -->|Event Details| EventDetail{User Role?}
    
    EventDetail -->|Attendee| AttendeeActions{Action?}
    EventDetail -->|Host| HostActions{Action?}
    
    AttendeeActions -->|Request Join| Request[POST /events/{id}/requests]
    AttendeeActions -->|Check Status| CheckReq[GET /events/{id}/my-request]
    AttendeeActions -->|Confirm| Confirm[POST /events/{id}/confirm-attendance]
    AttendeeActions -->|View Ticket| Ticket[GET /events/{id}/my-ticket]
    
    HostActions -->|View Requests| ViewReq[GET /events/{id}/requests]
    HostActions -->|Accept Request| Accept[PUT /events/{id}/requests/{req_id}/accept]
    HostActions -->|Decline Request| Decline[PUT /events/{id}/requests/{req_id}/decline]
    HostActions -->|Edit Event| Edit[PUT /events/{id}]
    HostActions -->|Delete Event| Delete[DELETE /events/{id}]
    
    Screen -->|Payouts| PayoutScreen{Action?}
    PayoutScreen -->|List Accounts| ListBank[GET /payouts/bank-accounts]
    PayoutScreen -->|Add Account| AddBank[POST /payouts/bank-accounts]
    PayoutScreen -->|Create Payout| CreatePayout[POST /payouts/requests]
    PayoutScreen -->|List Payouts| ListPayout[GET /payouts/requests]
    
    Screen -->|Invitations| InviteScreen{Action?}
    InviteScreen -->|View Invites| MyInvites[GET /events/my-invitations]
    InviteScreen -->|Respond| Respond[PUT /events/invitations/{id}/respond]
    
    style Browse fill:#e3f2fd
    style Request fill:#fff3e0
    style Accept fill:#c8e6c9
    style Decline fill:#ffcdd2
    style CreatePayout fill:#e8f5e9
```

### When to Call Each API

**On Screen Load:**
- `GET /events` - When Events List screen opens
- `GET /events/{id}` - When Event Details screen opens
- `GET /events/{id}/my-request` - When Event Details opens (to check if user requested)
- `GET /events/{id}/requests` - When Host opens Event Requests screen
- `GET /payouts/bank-accounts` - When Host opens Bank Accounts screen
- `GET /payouts/requests` - When Host opens Payouts screen
- `GET /events/my-invitations` - When user opens Invitations screen
- `GET /events/my-tickets` - When user opens My Tickets screen

**On User Action:**
- `POST /events/{id}/requests` - When user taps "Request to Join"
- `POST /events/{id}/confirm-attendance` - When user taps "Confirm Attendance"
- `PUT /events/{id}/requests/{req_id}/accept` - When host taps "Accept"
- `PUT /events/{id}/requests/{req_id}/decline` - When host taps "Decline"
- `POST /events/{id}/requests/bulk-action` - When host taps "Accept All" or "Decline All"
- `POST /events` - When host taps "Create Event"
- `PUT /events/{id}` - When host taps "Save" on edit screen
- `DELETE /events/{id}` - When host taps "Delete Event" (after confirmation)
- `POST /payouts/bank-accounts` - When host taps "Add Bank Account"
- `PUT /payouts/bank-accounts/{id}` - When host taps "Save" on edit bank account
- `DELETE /payouts/bank-accounts/{id}` - When host taps "Delete" (after confirmation)
- `POST /payouts/requests` - When host taps "Request Payout"
- `PUT /events/invitations/{id}/respond` - When user taps "Accept" or "Decline" on invitation

**On Navigation:**
- `GET /events/{id}/my-ticket` - When user navigates to ticket screen
- `GET /payouts/requests/{id}` - When host taps on payout request from list
- `GET /events/{id}/invitations` - When host navigates to invitations screen

**Periodic/Polling (Optional):**
- `GET /events/{id}/my-request` - Poll every 30 seconds if status is "pending" (optional)
- `GET /events/my-invitations` - Refresh when user returns to invitations screen

---

## Important Rules

1. **Backend is source of truth** - Use only fields returned by the API
2. **Do not invent request/response fields** - Use exactly what Swagger shows
3. **Do not add business logic on frontend** - Backend handles all calculations
4. **Use Swagger UI as reference** - https://loopinbackend-g17e.onrender.com/api/docs
5. **Flutter models must match Swagger responses** - Field names and types must be exact
6. **Explain APIs from frontend usage only** - Do not explain backend implementation

---

## Section 1: How Frontend Should Use Swagger UI

### Step 1: Opening Swagger UI

1. Open your browser
2. Go to: https://loopinbackend-g17e.onrender.com/api/docs
3. You will see all available API endpoints listed

### Step 2: Understanding Swagger Interface

**Left Sidebar:**
- Shows all API groups (Events, Payouts, Auth, etc.)
- Click on a group to expand and see endpoints
- Each endpoint shows HTTP method (GET, POST, PUT, DELETE)

**Endpoint Details:**
- Click on any endpoint to see details
- Shows request parameters, body structure, and response structure
- Green "Try it out" button lets you test the API directly

### Step 3: Reading Request Body

When you click on an endpoint:

1. **Parameters Section:**
   - Shows query parameters (for GET requests)
   - Shows path parameters (like `{event_id}`)
   - Each parameter shows: name, required (yes/no), type, description

2. **Request Body Section (for POST/PUT):**
   - Shows exact JSON structure you must send
   - Required fields are marked
   - Optional fields are marked
   - Copy the structure exactly - do not add or remove fields

**Example:**
If Swagger shows:
```json
{
  "title": "string",
  "description": "string",
  "start_time": "2024-01-01T10:00:00Z"
}
```

Your Flutter model must have exactly these three fields with these exact names.

### Step 4: Reading Response Structure

1. Scroll down to "Responses" section
2. Click on response code (200, 201, 400, etc.)
3. See the exact JSON structure backend returns
4. Your Flutter model must match this structure exactly

**Important:**
- Field names must match exactly (case-sensitive)
- Field types must match (String, int, bool, List, etc.)
- Nested objects must be modeled as separate Dart classes

### Step 5: Converting Swagger Response to Dart Model

**Process:**
1. Look at Swagger response structure
2. Create Dart class with same field names
3. Use correct Dart types:
   - `string` → `String`
   - `integer` → `int`
   - `number` → `double`
   - `boolean` → `bool`
   - `array` → `List<Type>`
   - `object` → Separate Dart class

**Example:**
Swagger shows:
```json
{
  "id": 1,
  "title": "Music Festival",
  "is_paid": true,
  "ticket_price": 100.50
}
```

Your Dart model:
```dart
class Event {
  int id;
  String title;
  bool isPaid;  // WRONG - field name must match
  double ticketPrice;  // WRONG - field name must match
}
```

**Correct Dart model:**
```dart
class Event {
  int id;
  String title;
  bool is_paid;  // Correct - matches Swagger
  double ticket_price;  // Correct - matches Swagger
}
```

### Step 6: Common Mistakes Beginners Make

**Mistake 1: Changing Field Names**
- Wrong: Converting `is_paid` to `isPaid` (camelCase)
- Correct: Keep exact field name `is_paid` (snake_case)

**Mistake 2: Adding Fields Not in Swagger**
- Wrong: Adding `isFavorite` field that backend doesn't return
- Correct: Only use fields shown in Swagger response

**Mistake 3: Guessing Field Types**
- Wrong: Assuming `ticket_price` is `int` when Swagger shows `number`
- Correct: Check Swagger - if it shows `number`, use `double` in Dart

**Mistake 4: Ignoring Nested Objects**
- Wrong: Flattening nested objects into parent class
- Correct: Create separate Dart class for nested objects

**Mistake 5: Not Checking Required Fields**
- Wrong: Sending request without required fields
- Correct: Check Swagger - required fields are marked with red asterisk (*)

**Mistake 6: Using Old Swagger Structure**
- Wrong: Using cached/old API structure
- Correct: Always check latest Swagger before coding

---

## Section 2: High-Level User Roles

### Attendee (Normal User)

**What Attendee Can Do:**
- Browse public events
- View event details
- Request to join events
- Confirm attendance after request accepted
- View their tickets
- View their event requests status
- Respond to invitations

**What Attendee Cannot Do:**
- Create events
- Manage event requests (accept/decline)
- Create payout requests
- Manage bank accounts
- Invite other users to events

**API Endpoints Attendee Uses:**
- GET /events (browse events)
- GET /events/{event_id} (view event details)
- POST /events/{event_id}/requests (request to join)
- GET /events/{event_id}/my-request (check request status)
- POST /events/{event_id}/confirm-attendance (confirm after acceptance)
- GET /events/{event_id}/my-ticket (view ticket)
- GET /events/my-tickets (view all tickets)
- GET /events/my-invitations (view invitations)
- PUT /events/invitations/{invite_id}/respond (respond to invitation)

### Host (Event Creator)

**What Host Can Do:**
- Everything Attendee can do
- Create events
- Update their events
- Delete their events
- View requests for their events
- Accept/decline requests
- Bulk accept/decline requests
- Invite users to their events
- View invitations sent for their events
- Create venues
- Manage bank accounts
- Create payout requests
- View payout requests

**What Host Cannot Do:**
- Accept requests for events they don't host
- Create payout requests for events they don't host
- View other hosts' payout requests

**API Endpoints Host Uses:**
- All Attendee endpoints
- GET /events/venues (list venues)
- POST /events/venues (create venue)
- POST /events (create event)
- PUT /events/{event_id} (update event)
- DELETE /events/{event_id} (delete event)
- GET /events/{event_id}/requests (view requests)
- PUT /events/{event_id}/requests/{request_id}/accept (accept request)
- PUT /events/{event_id}/requests/{request_id}/decline (decline request)
- POST /events/{event_id}/requests/bulk-action (bulk accept/decline)
- POST /events/{event_id}/invitations (invite users)
- GET /events/{event_id}/invitations (view sent invitations)
- GET /payouts/bank-accounts (list bank accounts)
- POST /payouts/bank-accounts (create bank account)
- PUT /payouts/bank-accounts/{account_id} (update bank account)
- DELETE /payouts/bank-accounts/{account_id} (delete bank account)
- POST /payouts/requests (create payout request)
- GET /payouts/requests (list payout requests)
- GET /payouts/requests/{payout_id} (view payout details)

### Invited User

**What Invited User Can Do:**
- View invitations received
- Accept invitation (going)
- Decline invitation (not going)
- After accepting, same as Attendee flow

**What Invited User Cannot Do:**
- Request to join if already invited (use invitation response instead)
- Accept expired invitations

**API Endpoints Invited User Uses:**
- GET /events/my-invitations (view invitations)
- PUT /events/invitations/{invite_id}/respond (respond to invitation)
- After accepting invitation, use Attendee endpoints

---

## Section 3: Events Module – Correct API Flow

### 3.1 Attendee Flow (Joining Events)

This flow explains how a normal user joins an event. Follow this order exactly.

#### Step 1: Browse Events

**API:** GET /events

**When to Call:**
- When user opens events list screen
- When user applies filters (date, category, paid/free)
- When user refreshes list
- When loading more events (pagination)

**Screen:** Events List Screen

**Request:**
- Method: GET
- Headers: Authorization: Bearer {token}
- Query Parameters (all optional):
  - `status`: "published" (to show only live events)
  - `is_paid`: true/false (filter paid or free)
  - `event_interest_id`: int (filter by category)
  - `start_date`: ISO datetime string (filter upcoming events)
  - `search`: string (search in title/description)
  - `offset`: int (for pagination, default: 0)
  - `limit`: int (items per page, default: 20, max: 100)

**Response Structure (check Swagger for exact fields):**
- `total`: int (total events matching filter)
- `offset`: int
- `limit`: int
- `data`: List of event objects

**What to Do:**
1. Display events from `data` array
2. Show event title, date, location, price
3. Handle pagination using `offset` and `limit`
4. Show loading state while fetching
5. Handle empty list (no events found)

**UI State:**
- Loading: Show loading indicator
- Success: Display events list
- Empty: Show "No events found" message
- Error: Show error message, allow retry

#### Step 2: View Event Details

**API:** GET /events/{event_id}

**When to Call:**
- When user taps on an event from list
- When user navigates to event details screen

**Screen:** Event Details Screen

**Request:**
- Method: GET
- Headers: Authorization: Bearer {token}
- Path Parameter: `event_id` (int)

**Response Structure (check Swagger for exact fields):**
- Event object with all details (title, description, date, venue, price, capacity, etc.)

**What to Do:**
1. Display all event information
2. Show "Request to Join" button if user hasn't requested
3. Show request status if user already requested
4. Show "Confirm Attendance" button if request was accepted
5. Show ticket if user already confirmed attendance

**UI State:**
- Loading: Show loading indicator
- Success: Display event details
- Error: Show error message, allow retry

#### Step 3: Request to Join Event

**API:** POST /events/{event_id}/requests

**When to Call:**
- When user taps "Request to Join" button on event details screen
- Only if user hasn't requested before

**Screen:** Event Details Screen

**Request:**
- Method: POST
- Headers: Authorization: Bearer {token}
- Path Parameter: `event_id` (int)
- Body (check Swagger for exact structure):
  - `message`: string (optional, user's message to host)
  - `seats_requested`: int (required, 1-10)

**Response Structure (check Swagger for exact fields):**
- Request object with status "pending"

**What to Do:**
1. Show success message: "Request submitted. Waiting for host approval."
2. Update UI to show "Request Pending" status
3. Disable "Request to Join" button
4. Call GET /events/{event_id}/my-request to get updated status

**UI State:**
- Before request: Show "Request to Join" button
- After request: Show "Request Pending" status
- Error: Show error message from backend

#### Step 4: Check Request Status

**API:** GET /events/{event_id}/my-request

**When to Call:**
- After submitting request (to get updated status)
- When user opens event details screen (to check if they have a request)
- Periodically if request is pending (optional polling)

**Screen:** Event Details Screen

**Request:**
- Method: GET
- Headers: Authorization: Bearer {token}
- Path Parameter: `event_id` (int)

**Response Structure (check Swagger for exact fields):**
- Request object with:
  - `status`: "pending" | "accepted" | "declined" | "cancelled"
  - `can_confirm`: bool (true if status is "accepted" and not yet confirmed)
  - Other request details

**What to Do:**
1. If `status` is "pending": Show "Request Pending" message
2. If `status` is "accepted" and `can_confirm` is true: Show "Confirm Attendance" button
3. If `status` is "declined": Show "Request Declined" message with host message
4. If `status` is "cancelled": Show "Request Cancelled" message

**UI State:**
- Pending: Show pending indicator
- Accepted: Show "Confirm Attendance" button
- Declined: Show declined message
- Error (404): User hasn't requested (show "Request to Join" button)

#### Step 5: Confirm Attendance

**API:** POST /events/{event_id}/confirm-attendance

**When to Call:**
- When user taps "Confirm Attendance" button
- Only if request status is "accepted" and `can_confirm` is true

**Screen:** Event Details Screen

**Request:**
- Method: POST
- Headers: Authorization: Bearer {token}
- Path Parameter: `event_id` (int)
- Body (check Swagger for exact structure):
  - `seats`: int (required, 1-10)

**Response Structure (check Swagger for exact fields):**
- Ticket object with:
  - `ticket_secret`: string (unique ticket code)
  - `event_id`: int
  - `event_title`: string
  - `seats`: int
  - `payment_status`: string
  - `qr_code_data`: string (for QR code generation)

**What to Do:**
1. Show success message: "Attendance confirmed! Your ticket is ready."
2. Navigate to ticket screen or show ticket details
3. Generate QR code using `qr_code_data` field
4. Update UI to show ticket instead of "Confirm Attendance" button

**UI State:**
- Before confirmation: Show "Confirm Attendance" button
- After confirmation: Show ticket with QR code
- Error: Show error message from backend

#### Step 6: View Ticket for Specific Event

**API:** GET /events/{event_id}/my-ticket

**When to Call:**
- When user opens ticket screen for a specific event
- After confirming attendance
- When user taps "View Ticket" button

**Screen:** Ticket Screen

**Request:**
- Method: GET
- Headers: Authorization: Bearer {token}
- Path Parameter: `event_id` (int)

**Response Structure (check Swagger for exact fields):**
- Ticket object with all ticket details

**What to Do:**
1. Display ticket information
2. Show QR code using `qr_code_data` field
3. Show ticket secret (for manual verification)
4. Show event details
5. Show payment status if paid event

**UI State:**
- Success: Display ticket
- Error (404): No ticket found (show appropriate message)

#### Step 7: View All Tickets

**API:** GET /events/my-tickets

**When to Call:**
- When user opens "My Tickets" screen
- When user wants to see all their tickets

**Screen:** My Tickets Screen

**Request:**
- Method: GET
- Headers: Authorization: Bearer {token}
- Query Parameters (optional):
  - `event_id`: int (filter by specific event)

**Response Structure (check Swagger for exact fields):**
- List of ticket objects

**What to Do:**
1. Display list of all tickets
2. Show event name, date, ticket status for each
3. Allow user to tap on ticket to view details
4. Handle empty list (no tickets)

**UI State:**
- Loading: Show loading indicator
- Success: Display tickets list
- Empty: Show "No tickets found" message
- Error: Show error message

---

### 3.2 Host Flow (Creating & Managing Events)

This flow explains how a host creates and manages events. Only users who create events are hosts.

#### Step 1: List Venues

**API:** GET /events/venues

**When to Call:**
- When host opens "Create Event" screen
- When host needs to select a venue
- When host wants to create a new venue

**Screen:** Create Event Screen (venue selection)

**Request:**
- Method: GET
- Headers: Authorization: Bearer {token}
- Query Parameters (optional):
  - `city`: string (filter by city)
  - `venue_type`: string (filter by type)
  - `offset`: int (pagination)
  - `limit`: int (pagination)

**Response Structure (check Swagger for exact fields):**
- Paginated list of venue objects

**What to Do:**
1. Display list of venues for selection
2. Show "Create New Venue" option
3. Allow host to select existing venue or create new one

**UI State:**
- Loading: Show loading indicator
- Success: Display venues list
- Error: Show error message

#### Step 2: Create Venue (Optional)

**API:** POST /events/venues

**When to Call:**
- When host taps "Create New Venue" button
- Only if host wants to add a new venue

**Screen:** Create Venue Screen

**Request:**
- Method: POST
- Headers: Authorization: Bearer {token}
- Body (check Swagger for exact structure):
  - `name`: string (required)
  - `address`: string (required)
  - `city`: string (required)
  - `venue_type`: string (required, options from Swagger)
  - `capacity`: int (optional)
  - `latitude`: double (optional)
  - `longitude`: double (optional)
  - `metadata`: object (optional)

**Response Structure (check Swagger for exact fields):**
- Venue object with created venue details

**What to Do:**
1. Show success message
2. Return to create event screen with new venue selected
3. Or allow host to continue creating event

**UI State:**
- Success: Venue created, return to event creation
- Error: Show validation errors from backend

#### Step 3: Create Event

**API:** POST /events

**When to Call:**
- When host fills event form and taps "Create Event" button
- Only after host has completed event details form

**Screen:** Create Event Screen

**Request:**
- Method: POST
- Headers: Authorization: Bearer {token}
- Body (check Swagger for exact structure - do not invent fields):
  - `title`: string (required)
  - `description`: string (required)
  - `start_time`: ISO datetime string (required)
  - `duration_hours`: double (required)
  - `venue_id`: int (optional, if using existing venue)
  - `venue_text`: string (optional, if custom venue text)
  - `venue_create`: object (optional, if creating venue inline)
  - `status`: string (default: "draft", options from Swagger)
  - `is_public`: bool (required)
  - `max_capacity`: int (required, 0 = unlimited)
  - `is_paid`: bool (required)
  - `ticket_price`: double (required if is_paid is true)
  - `allow_plus_one`: bool (required)
  - `gst_number`: string (optional)
  - `allowed_genders`: string (required, options from Swagger)
  - `cover_images`: List<string> (required, 1-3 image URLs)
  - `event_interest_ids`: List<int> (required, 1-5 interest IDs)

**Response Structure (check Swagger for exact fields):**
- Event object with created event details

**What to Do:**
1. Show success message: "Event created successfully"
2. Navigate to event details screen
3. If status is "draft", show option to publish later
4. If status is "published", event is live

**UI State:**
- Loading: Show loading indicator, disable submit button
- Success: Navigate to event details
- Error: Show validation errors from backend, keep form data

**Important:**
- Do not calculate `end_time` on frontend - backend calculates it from `start_time` + `duration_hours`
- Do not validate business rules on frontend - backend handles all validation
- Send exactly the fields shown in Swagger - no more, no less

#### Step 4: Update Event

**API:** PUT /events/{event_id}

**When to Call:**
- When host taps "Edit Event" button
- When host saves changes to event

**Screen:** Edit Event Screen

**Request:**
- Method: PUT
- Headers: Authorization: Bearer {token}
- Path Parameter: `event_id` (int)
- Body (check Swagger for exact structure):
  - Same fields as create event, but all optional (only send changed fields)

**Response Structure (check Swagger for exact fields):**
- Updated event object

**What to Do:**
1. Show success message: "Event updated successfully"
2. Refresh event details screen
3. Update UI with new event data

**UI State:**
- Loading: Show loading indicator
- Success: Show updated event
- Error: Show error message from backend

**Permission Check:**
- Only event host can update
- Backend returns 403 if user is not host
- Frontend should disable edit button if user is not host

#### Step 5: View Event Requests

**API:** GET /events/{event_id}/requests

**When to Call:**
- When host opens "Event Requests" screen
- When host wants to see who requested to join their event

**Screen:** Event Requests Screen

**Request:**
- Method: GET
- Headers: Authorization: Bearer {token}
- Path Parameter: `event_id` (int)

**Response Structure (check Swagger for exact fields):**
- List of request objects with:
  - `id`: int
  - `requester_id`: int
  - `requester_name`: string
  - `status`: string
  - `message`: string
  - `host_message`: string
  - `seats_requested`: int
  - `created_at`: datetime

**What to Do:**
1. Display list of requests
2. Show requester name, message, seats requested
3. Show status (pending, accepted, declined)
4. Show "Accept" and "Decline" buttons for pending requests
5. Show host message if request was processed

**UI State:**
- Loading: Show loading indicator
- Success: Display requests list
- Empty: Show "No requests yet" message
- Error: Show error message

**Permission Check:**
- Only event host can view requests
- Backend returns 403 if user is not host
- Frontend should not show this screen to non-hosts

#### Step 6: Accept Single Request

**API:** PUT /events/{event_id}/requests/{request_id}/accept

**When to Call:**
- When host taps "Accept" button on a request
- Only for requests with status "pending"

**Screen:** Event Requests Screen

**Request:**
- Method: PUT
- Headers: Authorization: Bearer {token}
- Path Parameters: `event_id` (int), `request_id` (int)
- Body (optional, check Swagger):
  - `host_message`: string (optional message to requester)

**Response Structure (check Swagger for exact fields):**
- Updated request object with status "accepted"

**What to Do:**
1. Show success message: "Request accepted"
2. Update request status in UI to "accepted"
3. Remove "Accept/Decline" buttons
4. Show host message if provided
5. Backend sends notification to requester automatically

**UI State:**
- Before: Show "Accept" and "Decline" buttons
- After: Show "Accepted" status
- Error: Show error message from backend

**Important:**
- Backend checks event capacity automatically
- If capacity full, backend returns error - frontend just shows error message
- Do not check capacity on frontend

#### Step 7: Decline Single Request

**API:** PUT /events/{event_id}/requests/{request_id}/decline

**When to Call:**
- When host taps "Decline" button on a request
- Only for requests with status "pending"

**Screen:** Event Requests Screen

**Request:**
- Method: PUT
- Headers: Authorization: Bearer {token}
- Path Parameters: `event_id` (int), `request_id` (int)
- Body (optional, check Swagger):
  - `host_message`: string (optional message to requester)

**Response Structure (check Swagger for exact fields):**
- Updated request object with status "declined"

**What to Do:**
1. Show success message: "Request declined"
2. Update request status in UI to "declined"
3. Remove "Accept/Decline" buttons
4. Show host message if provided
5. Backend sends notification to requester automatically

**UI State:**
- Before: Show "Accept" and "Decline" buttons
- After: Show "Declined" status
- Error: Show error message from backend

#### Step 8: Bulk Accept/Decline Requests

**API:** POST /events/{event_id}/requests/bulk-action

**When to Call:**
- When host selects multiple requests and taps "Accept All" or "Decline All"
- For processing multiple requests at once

**Screen:** Event Requests Screen

**Request:**
- Method: POST
- Headers: Authorization: Bearer {token}
- Path Parameter: `event_id` (int)
- Body (check Swagger for exact structure):
  - `request_ids`: List<int> (required, 1-100 request IDs)
  - `action`: string (required, "accept" or "decline")
  - `host_message`: string (optional, message for all requests)

**Response Structure (check Swagger for exact fields):**
- Summary object with:
  - `success`: bool
  - `processed_count`: int
  - `accepted_count`: int
  - `declined_count`: int
  - `errors`: List of errors (if any)

**What to Do:**
1. Show success message with counts: "X requests accepted, Y declined"
2. Update all processed requests in UI
3. If errors exist, show which requests failed
4. Refresh requests list

**UI State:**
- Loading: Show loading indicator
- Success: Update all processed requests
- Partial success: Show success + error details
- Error: Show error message

**Important:**
- Backend processes all requests in transaction
- If capacity exceeded, backend returns error for entire bulk action
- Frontend just shows error - do not process partial accepts

#### Step 9: Invite Users to Event

**API:** POST /events/{event_id}/invitations

**When to Call:**
- When host taps "Invite Users" button
- When host selects users and sends invitations

**Screen:** Invite Users Screen

**Request:**
- Method: POST
- Headers: Authorization: Bearer {token}
- Path Parameter: `event_id` (int)
- Body (check Swagger for exact structure):
  - `user_ids`: List<int> (required, 1-50 user IDs)
  - `message`: string (optional, personal message)
  - `expires_at`: ISO datetime string (optional, invitation expiration)

**Response Structure (check Swagger for exact fields):**
- Summary object with:
  - `success`: bool
  - `created_count`: int
  - `skipped_count`: int (if user already invited)
  - `errors`: List of errors

**What to Do:**
1. Show success message: "X invitations sent"
2. If skipped, show: "Y users already invited"
3. If errors, show which users failed
4. Navigate back to event details

**UI State:**
- Loading: Show loading indicator
- Success: Show invitation summary
- Error: Show error message

**Important:**
- Backend sends notifications to invited users automatically
- Frontend does not need to handle notifications

#### Step 10: View Event Invitations

**API:** GET /events/{event_id}/invitations

**When to Call:**
- When host opens "Event Invitations" screen
- When host wants to see who they invited

**Screen:** Event Invitations Screen

**Request:**
- Method: GET
- Headers: Authorization: Bearer {token}
- Path Parameter: `event_id` (int)
- Query Parameters (optional):
  - `status_filter`: string (filter by status: pending, accepted, declined, expired)

**Response Structure (check Swagger for exact fields):**
- List of invitation objects with user details and status

**What to Do:**
1. Display list of invitations
2. Show invited user name, status, message
3. Show status badges (pending, accepted, declined, expired)
4. Handle empty list

**UI State:**
- Loading: Show loading indicator
- Success: Display invitations list
- Empty: Show "No invitations sent" message
- Error: Show error message

#### Step 11: Delete Event

**API:** DELETE /events/{event_id}

**When to Call:**
- When host taps "Delete Event" button
- After host confirms deletion

**Screen:** Event Details Screen (host view)

**Request:**
- Method: DELETE
- Headers: Authorization: Bearer {token}
- Path Parameter: `event_id` (int)

**Response:**
- 204 No Content (success)
- Or error response

**What to Do:**
1. Show success message: "Event deleted"
2. Navigate back to events list
3. Remove event from local cache/list

**UI State:**
- Before: Show "Delete Event" button (with confirmation)
- After: Navigate away from event
- Error: Show error message

**Important:**
- Backend does soft delete (event marked as inactive)
- Event still exists in database but not visible to users
- Only host can delete their own events

---

### 3.3 Invitation Flow

This flow explains how users respond to invitations they received.

#### Step 1: View My Invitations

**API:** GET /events/my-invitations

**When to Call:**
- When user opens "My Invitations" screen
- When user wants to see invitations they received

**Screen:** My Invitations Screen

**Request:**
- Method: GET
- Headers: Authorization: Bearer {token}
- Query Parameters (optional):
  - `status_filter`: string (filter by status)

**Response Structure (check Swagger for exact fields):**
- List of invitation objects with:
  - `invite_id`: int
  - `event_id`: int
  - `event_title`: string
  - `event_start_time`: datetime
  - `host_name`: string
  - `status`: string (pending, accepted, declined, expired)
  - `message`: string
  - `created_at`: datetime

**What to Do:**
1. Display list of invitations
2. Show event title, date, host name
3. Show status (pending, accepted, declined, expired)
4. For pending invitations, show "Accept" and "Decline" buttons
5. Handle empty list

**UI State:**
- Loading: Show loading indicator
- Success: Display invitations list
- Empty: Show "No invitations" message
- Error: Show error message

#### Step 2: Respond to Invitation

**API:** PUT /events/invitations/{invite_id}/respond

**When to Call:**
- When user taps "Accept" or "Decline" button on invitation
- Only for invitations with status "pending"

**Screen:** My Invitations Screen or Invitation Details Screen

**Request:**
- Method: PUT
- Headers: Authorization: Bearer {token}
- Path Parameter: `invite_id` (int)
- Body (check Swagger for exact structure):
  - `response`: string (required, "going" or "not_going")
  - `message`: string (optional, response message to host)

**Response Structure (check Swagger for exact fields):**
- Updated invitation object with:
  - `invite_id`: int
  - `status`: string (accepted or declined)
  - `event_id`: int
  - `event_title`: string
  - `is_paid`: bool
  - `requires_payment`: bool (true if going and event is paid)

**What to Do:**
1. If response is "going":
   - Show success message: "Invitation accepted"
   - If `requires_payment` is true, navigate to payment screen
   - If `requires_payment` is false, show ticket or navigate to event
   - Update invitation status to "accepted"
2. If response is "not_going":
   - Show success message: "Invitation declined"
   - Update invitation status to "declined"
3. Backend automatically creates attendee record and ticket (for free events)
4. Backend sends notification to host automatically

**UI State:**
- Before: Show "Accept" and "Decline" buttons
- After: Show updated status
- If requires payment: Navigate to payment flow
- Error: Show error message from backend

**Important:**
- Backend handles all logic (creating attendee, generating ticket, etc.)
- Frontend just shows result and navigates accordingly
- Do not create attendee records on frontend

---

## Section 4: Payouts Module (Host Only)

**Important:** Payouts are ONLY for hosts. Regular users (attendees) cannot access payout endpoints.

### Overview

Hosts can request payouts for their events after tickets are sold. Frontend must NEVER calculate payout amounts - backend does all calculations.

### Step 1: List Bank Accounts

**API:** GET /payouts/bank-accounts

**When to Call:**
- When host opens "Bank Accounts" screen
- When host wants to manage bank accounts
- Before creating payout request (to select bank account)

**Screen:** Bank Accounts Screen

**Request:**
- Method: GET
- Headers: Authorization: Bearer {token}

**Response Structure (check Swagger for exact fields):**
- List of bank account objects with:
  - `id`: int
  - `uuid`: string
  - `bank_name`: string
  - `masked_account_number`: string (account number is masked for security)
  - `ifsc_code`: string
  - `account_holder_name`: string
  - `is_primary`: bool
  - `is_verified`: bool
  - `is_active`: bool

**What to Do:**
1. Display list of bank accounts
2. Show masked account number (backend masks it automatically)
3. Show primary account indicator
4. Show "Add Bank Account" button
5. Handle empty list (no bank accounts)

**UI State:**
- Loading: Show loading indicator
- Success: Display bank accounts list
- Empty: Show "No bank accounts. Add one to receive payouts."
- Error: Show error message

**Security Note:**
- Backend never returns full account number
- Frontend should never store or display full account number
- Use `masked_account_number` field from response

### Step 2: Create Bank Account

**API:** POST /payouts/bank-accounts

**When to Call:**
- When host taps "Add Bank Account" button
- When host fills bank account form and submits

**Screen:** Add Bank Account Screen

**Request:**
- Method: POST
- Headers: Authorization: Bearer {token}
- Body (check Swagger for exact structure):
  - `bank_name`: string (required)
  - `account_number`: string (required, 8-30 digits)
  - `ifsc_code`: string (required, 11 characters, format: AAAA0XXXXXX)
  - `account_holder_name`: string (required)
  - `is_primary`: bool (required, set as primary account)

**Response Structure (check Swagger for exact fields):**
- Bank account object with created account details (masked account number)

**What to Do:**
1. Show success message: "Bank account added successfully"
2. Navigate back to bank accounts list
3. Refresh bank accounts list
4. If set as primary, other accounts automatically become non-primary (backend handles this)

**UI State:**
- Loading: Show loading indicator, disable submit button
- Success: Navigate back, refresh list
- Error: Show validation errors from backend

**Validation:**
- Backend validates IFSC code format
- Backend validates account number format
- Frontend should show backend validation errors
- Do not add custom validation on frontend

### Step 3: Update Bank Account

**API:** PUT /payouts/bank-accounts/{account_id}

**When to Call:**
- When host taps "Edit" button on a bank account
- When host saves changes to bank account

**Screen:** Edit Bank Account Screen

**Request:**
- Method: PUT
- Headers: Authorization: Bearer {token}
- Path Parameter: `account_id` (int)
- Body (check Swagger for exact structure):
  - All fields optional (only send changed fields)
  - Same fields as create bank account

**Response Structure (check Swagger for exact fields):**
- Updated bank account object

**What to Do:**
1. Show success message: "Bank account updated"
2. Navigate back to bank accounts list
3. Refresh bank accounts list

**UI State:**
- Loading: Show loading indicator, disable submit button
- Success: Navigate back, refresh list
- Error: Show validation errors from backend

**Important Notes:**
- Only send fields that user changed
- If user changes `is_primary` to true, backend automatically sets other accounts to false
- Backend validates all fields - show backend error messages

### Step 4: Delete Bank Account

**API:** DELETE /payouts/bank-accounts/{account_id}

**When to Call:**
- When host taps "Delete" button on a bank account
- After user confirms deletion

**Screen:** Bank Accounts List Screen or Bank Account Detail Screen

**Request:**
- Method: DELETE
- Headers: Authorization: Bearer {token}
- Path Parameter: `account_id` (int)

**Response Structure (check Swagger for exact fields):**
- Success message object

**What to Do:**
1. Show confirmation dialog before calling API
2. After successful deletion, show message: "Bank account deleted"
3. Remove account from list immediately
4. Refresh bank accounts list

**UI State:**
- Loading: Show loading indicator on delete button
- Success: Remove from list, show success message
- Error: Show error message from backend

**Important Notes:**
- Always confirm before deleting
- Backend prevents deletion if account has payout requests
- If deletion fails, show backend error message
- Do not delete from UI until backend confirms success

---

## Payout Requests (Host Only)

**Important:** Only hosts can create payout requests. Attendees cannot access these APIs.

**What is Payout Request:**
- Host requests money from event ticket sales
- Backend calculates everything automatically
- Frontend only displays what backend returns
- Never calculate money amounts on frontend

### Step 1: Create Payout Request

**API:** POST /payouts/requests

**When to Call:**
- When host taps "Request Payout" button on completed event
- Only for events with paid ticket sales
- Only after event has ended

**Screen:** Event Detail Screen (Host View) or Payouts Screen

**Request:**
- Method: POST
- Headers: Authorization: Bearer {token}
- Body (check Swagger for exact structure):
  - `event_id`: int (required, ID of event)
  - `bank_account_id`: int (required, ID of bank account to receive payout)

**Response Structure (check Swagger for exact fields):**
- Payout request object with:
  - `id`: int
  - `uuid`: string
  - `event_id`: int
  - `event_name`: string
  - `host_name`: string
  - `total_tickets_sold`: int
  - `base_ticket_fare`: float
  - `final_ticket_fare`: float
  - `platform_fee_amount`: float
  - `platform_fee_percentage`: float
  - `final_earning`: float
  - `status`: string (will be "pending")
  - `created_at`: string (ISO datetime)

**What to Do:**
1. Show success message: "Payout request created successfully"
2. Navigate to payout request detail screen
3. Display all financial details from backend response
4. Do not calculate or modify any money amounts

**UI State:**
- Loading: Show loading indicator, disable button
- Success: Navigate to detail screen, show success message
- Error: Show backend error message

**Important Notes:**
- Backend calculates all money amounts automatically
- Backend validates that user is event host
- Backend validates that bank account belongs to user
- Backend validates that event has paid ticket sales
- Frontend must display exact amounts from backend response
- Never calculate `final_earning` or `platform_fee` on frontend
- Status will always be "pending" when created

**Common Mistakes:**
- Do not calculate `final_earning = total_tickets_sold * base_ticket_fare` on frontend
- Do not calculate `platform_fee = final_earning * 0.10` on frontend
- Do not modify any money amounts before displaying
- Use exact values from backend response

### Step 2: List Payout Requests

**API:** GET /payouts/requests

**When to Call:**
- When host opens "My Payouts" screen
- When host navigates to payouts section
- After creating new payout request

**Screen:** Payouts List Screen

**Request:**
- Method: GET
- Headers: Authorization: Bearer {token}
- Query Parameters (all optional):
  - `status`: string (filter by status: "pending", "approved", "processing", "completed", "rejected", "cancelled")
  - `offset`: int (default: 0, for pagination)
  - `limit`: int (default: 20, max: 100)

**Response Structure (check Swagger for exact fields):**
- List of payout request objects (summary view)
- Each object contains:
  - `id`: int
  - `uuid`: string
  - `event_id`: int
  - `event_name`: string
  - `host_name`: string
  - `event_date`: string (ISO datetime)
  - `total_tickets_sold`: int
  - `final_earning`: float
  - `status`: string
  - `created_at`: string (ISO datetime)
- Pagination object:
  - `offset`: int
  - `limit`: int
  - `total`: int

**What to Do:**
1. Display list of payout requests
2. Show status badge for each request
3. Show event name, date, tickets sold, and earnings
4. Implement pagination using offset and limit
5. Allow filtering by status using query parameter

**UI State:**
- Loading: Show loading indicator
- Success: Display list of payout requests
- Empty: Show "No payout requests found"
- Error: Show error message

**Status Display:**
- Use exact status string from backend
- Do not translate or modify status values
- Common statuses: "pending", "approved", "processing", "completed", "rejected", "cancelled"
- Show appropriate color badge based on status

**Pagination:**
- Use `offset` and `limit` for pagination
- Load more when user scrolls to bottom
- Show total count from pagination object
- Do not implement infinite scroll without pagination

**Filtering:**
- Allow user to filter by status
- Send `status` query parameter to backend
- Backend returns filtered results
- Do not filter on frontend

### Step 3: Get Payout Request Detail

**API:** GET /payouts/requests/{payout_id}

**When to Call:**
- When host taps on a payout request from list
- When host opens payout request detail screen
- After creating payout request

**Screen:** Payout Request Detail Screen

**Request:**
- Method: GET
- Headers: Authorization: Bearer {token}
- Path Parameter: `payout_id` (int)

**Response Structure (check Swagger for exact fields):**
- Complete payout request object with all details:
  - `id`: int
  - `uuid`: string
  - `bank_account`: object (masked account details)
  - `event_id`: int
  - `host_name`: string
  - `event_name`: string
  - `event_date`: string (ISO datetime)
  - `event_location`: string
  - `total_capacity`: int
  - `base_ticket_fare`: float
  - `final_ticket_fare`: float
  - `total_tickets_sold`: int
  - `attendees_details`: array of objects (name, contact)
  - `platform_fee_amount`: float
  - `platform_fee_percentage`: float
  - `final_earning`: float
  - `status`: string
  - `processed_at`: string (ISO datetime, nullable)
  - `transaction_reference`: string (nullable)
  - `rejection_reason`: string (nullable)
  - `notes`: string (nullable)
  - `created_at`: string (ISO datetime)
  - `updated_at`: string (ISO datetime)

**What to Do:**
1. Display all payout request details
2. Show financial breakdown clearly
3. Show attendee list if available
4. Show status and related information
5. Show bank account details (masked)
6. Display all fields exactly as backend returns

**UI State:**
- Loading: Show loading indicator
- Success: Display all details
- Error: Show error message

**Financial Display:**
- Show `base_ticket_fare` as "Base Ticket Price"
- Show `final_ticket_fare` as "Final Ticket Price (Buyer Pays)"
- Show `platform_fee_amount` as "Platform Fee"
- Show `platform_fee_percentage` as "Platform Fee Percentage"
- Show `final_earning` as "Your Earnings"
- Show `total_tickets_sold` as "Tickets Sold"
- Use exact values from backend - do not calculate

**Status-Specific Display:**
- If status is "rejected", show `rejection_reason`
- If status is "completed", show `transaction_reference` and `processed_at`
- If status is "pending", show waiting message
- If status is "processing", show processing message

**Important Notes:**
- All money amounts are calculated by backend
- Display exact values from response
- Do not calculate or modify any amounts
- Attendee details are snapshot from time of request creation
- Bank account number is always masked
- Status changes are handled by backend/admin, not frontend

**Common Mistakes:**
- Do not calculate earnings on frontend
- Do not calculate platform fee on frontend
- Do not modify status values
- Do not show full account number (use masked version)
- Do not calculate totals or summaries on frontend

---

## Section 5: Authorization & Error Handling

### How to Attach Bearer Token

**For All API Calls:**
1. Get JWT token from authentication response
2. Store token securely (use secure storage, not plain text)
3. Attach token to every API request header

**Header Format:**
```
Authorization: Bearer {your_jwt_token}
```

**Example:**
If your token is "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
Then header should be:
```
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Important:**
- Include space after "Bearer"
- Do not add quotes around token
- Token expires after time set by backend (check JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
- Refresh token when it expires

### Error Status Codes

**401 Unauthorized:**
- Meaning: Token is missing, invalid, or expired
- What to Do:
  1. Clear stored token
  2. Clear user session
  3. Navigate to login screen
  4. Show message: "Session expired. Please login again."
- Do not retry request automatically
- Force user to login again

**403 Forbidden:**
- Meaning: User does not have permission for this action
- What to Do:
  1. Show error message from backend
  2. Do not allow user to retry
  3. Navigate back or show appropriate message
- Example: Attendee trying to access host-only endpoint

**400 Bad Request:**
- Meaning: Request data is invalid
- What to Do:
  1. Show validation errors from backend response
  2. Highlight fields with errors
  3. Allow user to fix and retry
- Backend returns specific field errors - display them

**404 Not Found:**
- Meaning: Resource does not exist or user cannot access it
- What to Do:
  1. Show error message from backend
  2. Navigate back to previous screen
  3. Refresh list if needed

**500 Internal Server Error:**
- Meaning: Backend error (not frontend fault)
- What to Do:
  1. Show generic error message: "Something went wrong. Please try again."
  2. Log error for debugging
  3. Allow user to retry
  4. Do not show technical error details to user

### How to Show Backend Error Messages

**Error Response Structure:**
Backend returns errors in this format (check Swagger for exact structure):
```json
{
  "detail": "Error message here"
}
```

Or for validation errors:
```json
{
  "detail": [
    {
      "loc": ["body", "field_name"],
      "msg": "Error message",
      "type": "error_type"
    }
  ]
}
```

**What to Do:**
1. Extract error message from `detail` field
2. Display message to user
3. For validation errors, show field-specific errors
4. Do not show technical details or stack traces

**Example:**
If backend returns:
```json
{
  "detail": "Event not found"
}
```
Show: "Event not found"

If backend returns validation errors:
```json
{
  "detail": [
    {
      "loc": ["body", "title"],
      "msg": "Title is required"
    }
  ]
}
```
Show: "Title is required" next to title field

### When to Force Logout

**Force logout in these cases:**
1. 401 error on any API call
2. Token refresh fails
3. User explicitly logs out
4. Account is deactivated (if backend returns this)

**Logout Process:**
1. Clear JWT token from storage
2. Clear user session data
3. Clear all cached API responses
4. Navigate to login screen
5. Show message: "Logged out successfully" or "Session expired"

**Do not force logout for:**
- 400 errors (validation errors)
- 403 errors (permission errors - just show message)
- 404 errors (not found - just show message)
- 500 errors (server errors - allow retry)

---

## Section 6: Common Frontend Mistakes (Explicit Warnings)

### Mistake 1: Hardcoding Status Values

**Wrong:**
- Hardcoding status strings like "pending", "completed" in code
- Assuming status values never change

**Why Wrong:**
- Backend may add new statuses
- Status values may change
- You must use exact status from backend response

**Correct:**
- Always use status value from API response
- Do not hardcode status strings
- Create enum or constants from backend response

### Mistake 2: Guessing Request Payloads

**Wrong:**
- Looking at other similar APIs and guessing fields
- Adding fields that Swagger does not show
- Removing fields that Swagger shows as required

**Why Wrong:**
- Backend validates exact structure
- Extra fields may be ignored or cause errors
- Missing required fields will cause 400 error

**Correct:**
- Always check Swagger for exact request structure
- Use only fields shown in Swagger
- Send fields in exact format shown

### Mistake 3: Ignoring Swagger Changes

**Wrong:**
- Not checking Swagger after backend updates
- Using old response structure
- Assuming API structure never changes

**Why Wrong:**
- Backend may add new fields
- Backend may change field types
- Backend may remove deprecated fields

**Correct:**
- Check Swagger regularly
- Update Flutter models when Swagger changes
- Test API calls after backend updates

### Mistake 4: Calculating Money on Frontend

**Wrong:**
- Calculating earnings = tickets_sold * ticket_price
- Calculating platform_fee = earnings * 0.10
- Calculating final_earning = earnings - platform_fee

**Why Wrong:**
- Backend calculates exact amounts
- Platform fee percentage may change
- Calculations may have rounding differences
- Business logic belongs on backend

**Correct:**
- Use exact values from backend response
- Display `final_earning` from API
- Display `platform_fee_amount` from API
- Never calculate money amounts

### Mistake 5: Not Handling Null Values

**Wrong:**
- Assuming all fields are always present
- Not checking for null before using
- Crashes when backend returns null

**Why Wrong:**
- Backend may return null for optional fields
- Some fields are nullable by design
- Response structure may vary

**Correct:**
- Make fields nullable in Dart models
- Check for null before displaying
- Use null-safe operators (?., ??)
- Provide default values for display

### Mistake 6: Storing Sensitive Data

**Wrong:**
- Storing full account numbers
- Storing JWT tokens in plain text
- Logging sensitive data

**Why Wrong:**
- Security risk
- Data can be accessed by other apps
- Violates security best practices

**Correct:**
- Use secure storage for tokens
- Never store full account numbers
- Use masked values from backend
- Do not log sensitive data

### Mistake 7: Not Implementing Pagination

**Wrong:**
- Loading all data at once
- Not using offset and limit
- Assuming small dataset

**Why Wrong:**
- Large datasets will be slow
- May cause memory issues
- Backend enforces pagination limits

**Correct:**
- Always implement pagination
- Use offset and limit parameters
- Load more data on scroll
- Show total count from backend

### Mistake 8: Not Validating on Frontend (Basic Validation)

**Wrong:**
- Sending empty required fields
- Sending invalid formats
- Not checking basic requirements

**Why Wrong:**
- Wastes API calls
- Poor user experience
- Backend will reject anyway

**Correct:**
- Do basic validation (required fields, format)
- Show errors before API call
- But always trust backend validation
- Show backend errors even if frontend validation passes

**Note:** This is different from business logic validation. Basic format validation (like email format, required fields) is okay. But do not validate business rules (like "event must have at least 10 attendees" - that is backend's job).

### Mistake 9: Modifying Backend Response Data

**Wrong:**
- Changing field names before storing
- Modifying values before displaying
- Adding calculated fields to response

**Why Wrong:**
- Breaks data consistency
- May cause bugs
- Makes debugging difficult

**Correct:**
- Store response data as-is
- Create separate display models if needed
- Keep original response intact

### Mistake 10: Not Handling Network Errors

**Wrong:**
- Not checking internet connection
- Not handling timeout errors
- Assuming API always succeeds

**Why Wrong:**
- Network can fail
- API can be slow
- User experience suffers

**Correct:**
- Check internet connection before API calls
- Handle timeout errors
- Show appropriate messages
- Allow retry on network errors
- Show loading states

---

## Final Reminders

1. **Backend is always correct** - If frontend and backend disagree, backend wins
2. **Swagger is your reference** - Check it for every API
3. **Do not invent fields** - Use only what Swagger shows
4. **Do not calculate money** - Use backend values
5. **Handle errors properly** - Show backend error messages
6. **Secure sensitive data** - Use secure storage
7. **Test with real API** - Do not assume it works
8. **Update when Swagger changes** - Keep models in sync
9. **Follow exact field names** - Case-sensitive matching
10. **Ask backend team if confused** - Do not guess

---

**End of Integration Guide**