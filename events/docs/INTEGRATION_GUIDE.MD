# Events API Integration Guide for Mobile Developers

## Overview

This guide is designed for Android and iOS developers who need to integrate the Events API into their mobile applications. It provides step-by-step instructions, explains when to call each API, how to handle responses, and what to do next based on different scenarios.

**Important Notes:**
- All API calls require authentication using a JWT token in the Authorization header
- Base URL: `https://loopinbackend-g17e.onrender.com/api`
- All requests should include: `Authorization: Bearer YOUR_JWT_TOKEN`
- All responses are in JSON format
- Use appropriate HTTP methods (GET, POST, PUT, DELETE) as specified

---

## Table of Contents

1. [Authentication Setup](#authentication-setup)
2. [Event Discovery Flow](#event-discovery-flow)
3. [Event Creation Flow](#event-creation-flow)
4. [User Request Flow](#user-request-flow)
5. [Host Management Flow](#host-management-flow)
6. [Invitation Flow](#invitation-flow)
7. [Ticket Management Flow](#ticket-management-flow)
8. [Error Handling Guide](#error-handling-guide)
9. [Complete User Journey Examples](#complete-user-journey-examples)

---

## Authentication Setup

### Before Making Any API Calls

Every API endpoint requires authentication. You must:

1. First, authenticate the user using the phone authentication API (separate from events API)
2. Receive a JWT token in the response
3. Store this token securely on the device
4. Include this token in every Events API request header as: `Authorization: Bearer YOUR_TOKEN_HERE`

**If authentication fails:**
- The API will return a 401 status code
- Show a message: "Your session has expired. Please log in again."
- Redirect the user to the login screen
- Clear the stored token

---

## Event Discovery Flow

### When to Use: User Browsing Events

This flow is used when users want to see available events in the app.

### Step 1: List Events

**Endpoint:** GET `/events`

**When to Call:**
- When the user opens the events list screen
- When the user applies filters (by date, category, paid/free, etc.)
- When the user refreshes the events list
- When pagination is needed (scrolling to load more events)

**Request Details:**
- Method: GET
- Headers: Include Authorization header with JWT token
- Query Parameters (all optional):
  
  **Filter Parameters:**
  - `host_id`: Integer, filter events by a specific host's user ID (shows only events created by that host)
  - `venue_id`: Integer, filter events at a specific venue ID (shows only events at that venue location)
  - `status`: String, filter by event status (options: "draft", "published", "cancelled", "completed", "postponed")
    - Use "published" to show only live events
    - Use "draft" to show only unpublished events (usually only visible to the host)
  - `is_public`: Boolean (true/false), filter public or private events
    - Use true to show only public events visible to everyone
    - Use false to show only private events (usually only visible to host)
  - `is_paid`: Boolean (true/false), filter paid or free events
    - Use true to show only paid events
    - Use false to show only free events
  - `allowed_genders`: String, filter by gender restrictions (options: "all", "male", "female", "non_binary")
    - Use "all" to show events open to all genders
    - Use specific gender to show events restricted to that gender
  - `event_interest_id`: Integer, filter by event category/interest ID
    - Use this to show events in a specific category (e.g., Music, Sports, Food)
    - Get valid interest IDs from the event interests list endpoint
  - `start_date`: String, filter events starting from this date and time (ISO 8601 format, example: "2024-12-25T00:00:00Z")
    - Shows only events that start on or after this date
    - Useful for showing upcoming events
  - `end_date`: String, filter events ending before this date and time (ISO 8601 format, example: "2024-12-31T23:59:59Z")
    - Shows only events that end before this date
    - Useful for showing past events or events within a date range
  - `search`: String, search text to find in event titles and descriptions
    - Searches both title and description fields
    - Case-insensitive partial matching (e.g., "music" will find "Music Festival")
    - Can be combined with other filters
  
  **Pagination Parameters:**
  - `offset`: Integer, number of events to skip before returning results (default: 0, minimum: 0)
    - Use 0 for the first page
    - Use 20 for the second page (if limit is 20)
    - Use 40 for the third page, and so on
    - Formula: offset = (page_number - 1) × limit
  - `limit`: Integer, number of events to return per page (default: 20, minimum: 1, maximum: 100)
    - Use 20 for standard pagination
    - Use 50-100 for loading more events at once
    - Don't exceed 100 as it's the maximum allowed

**Examples of Query Parameter Combinations:**

**Example 1: Get all published, free events**
- Query: `?status=published&is_paid=false`
- Use case: Show all free events that are live
- **Complete Endpoint Example:**
  - `GET /api/events?status=published&is_paid=false`
  - Returns: First 20 free, published events

**Example 2: Get upcoming events in a specific category**
- Query: `?status=published&event_interest_id=5&start_date=2024-12-25T00:00:00Z`
- Use case: Show upcoming music events (if interest ID 5 is Music)
- **Complete Endpoint Example:**
  - `GET /api/events?status=published&event_interest_id=5&start_date=2024-12-25T00:00:00Z`
  - Returns: Events in category 5 starting from December 25, 2024

**Example 3: Search for events with pagination**
- Query: `?search=workshop&offset=0&limit=20`
- Use case: First page of workshop events
- **Complete Endpoint Example:**
  - `GET /api/events?search=workshop&offset=0&limit=20`
  - Returns: First 20 events matching "workshop" in title or description

**Example 4: Get events in a date range**
- Query: `?start_date=2024-12-01T00:00:00Z&end_date=2024-12-31T23:59:59Z`
- Use case: Show all events in December 2024
- **Complete Endpoint Example:**
  - `GET /api/events?start_date=2024-12-01T00:00:00Z&end_date=2024-12-31T23:59:59Z`
  - Returns: All events happening in December 2024

**Example 5: Get events by a specific host with pagination**
- Query: `?host_id=123&offset=20&limit=20`
- Use case: Second page of events created by user ID 123
- **Complete Endpoint Example:**
  - `GET /api/events?host_id=123&offset=20&limit=20`
  - Returns: Second page (events 21-40) of events created by host ID 123

**Example 6: Combine multiple filters**
- Query: `?status=published&is_paid=false&allowed_genders=all&event_interest_id=3&limit=50`
- Use case: Show first 50 published, free events in category 3, open to all genders
- **Complete Endpoint Example:**
  - `GET /api/events?status=published&is_paid=false&allowed_genders=all&event_interest_id=3&limit=50`
  - Returns: First 50 published, free events in category 3, open to all genders

**Success Response (200):**
- Contains a JSON object with:
  - `total`: Total number of events matching the filters
  - `offset`: Current offset value
  - `limit`: Current limit value
  - `data`: Array of event objects, each containing:
    - Event ID, title, description
    - Host information (ID and name)
    - Venue details (name, address, city) or custom venue text
    - Start and end times
    - Maximum capacity and current attendee count
    - Pricing information (is_paid, ticket_price)
    - Event status and visibility settings
    - Cover images (array of image URLs)
    - Event interests/categories
    - Request count and going count

**What to Do Next:**
- Display the events in a list or grid view
- Show event title, cover image, date/time, location, and price
- Show how many people are going
- Show if the event is paid or free
- Implement pagination using the response data:
  - If `total` is greater than `limit`, show "Load More" button or implement infinite scroll
  - Calculate total pages: total_pages = ceil(total / limit)
  - Calculate current page: current_page = (offset / limit) + 1
  - For "Load More": Next offset = current offset + limit
  - For "Previous Page": Previous offset = current offset - limit (minimum 0)
  - Show pagination info: "Showing X-Y of Z events" or "Page X of Y"
- Make each event clickable to view details
- If `data` array is empty, show "No events found" message
- If filters are applied, show active filters and allow user to clear them
- Show loading indicator while fetching events
- Cache events list locally for offline viewing

**Error Handling:**
- If you get 400: Invalid query parameter format (e.g., invalid date format, invalid status value)
  - Check the error message for specific field that's invalid
  - Common errors: "Invalid date format" (use ISO 8601 format), "Invalid status" (use valid status options)
- If you get 401: User needs to log in again
- If you get 403: User doesn't have permission (rare for listing)
- If you get 500: Server error, show "Unable to load events. Please try again."

**Pagination Best Practices:**
- Always check if `total > limit` before showing pagination controls
- For mobile apps, prefer infinite scroll over "Next/Previous" buttons
- Load next page when user scrolls near the bottom (e.g., 80% scrolled)
- Show loading indicator while fetching next page
- Don't fetch more than needed - use limit of 20-50 for mobile
- Cache paginated results to avoid re-fetching when user scrolls back up
- Reset pagination when filters change (go back to offset=0)

**Filter Best Practices:**
- Allow users to combine multiple filters
- Show active filters as chips/tags that can be removed
- Provide "Clear All Filters" option
- Remember user's filter preferences locally
- For date filters, use date pickers for better UX
- For search, implement debouncing (wait 300-500ms after user stops typing)
- Validate filter values before sending request

### Step 2: Get Single Event Details

**Endpoint:** GET `/events/{event_id}`

**When to Call:**
- When user taps on an event from the list
- When user opens event details screen
- When refreshing event details

**Request Details:**
- Method: GET
- Headers: Include Authorization header with JWT token
- Path Parameter: Replace `{event_id}` with the actual event ID number

**Success Response (200):**
- Contains complete event information including all fields from the list, plus:
  - Full description
  - All cover images
  - Complete venue information with coordinates
  - All event interests/categories
  - Detailed pricing information
  - GST number (if applicable)
  - Gender restrictions
  - Whether plus-one is allowed

**What to Do Next:**
- Display full event details screen
- Show all images in a carousel
- Show map if venue coordinates are available
- Show action buttons based on user role:
  - If user is host: Show "Edit Event" and "Manage Requests" buttons
  - If user is not host: Show "Request to Join" button (if not already requested)
  - If user has pending request: Show "View Request Status" button
  - If user is accepted: Show "Confirm Attendance" button
  - If user has ticket: Show "View Ticket" button

**Error Handling:**
- If you get 404: Event doesn't exist or was removed, show "This event is no longer available" and go back
- If you get 403: Event is private and user is not the host, show "This is a private event" and go back
- If you get 401: User needs to log in again

---

## Event Creation Flow

### When to Use: Host Creating an Event

This flow is used when a user wants to host/create a new event.

### Step 1: Get Event Interests (Categories)

**Endpoint:** GET `/api/auth/event-interests`

**Note:** This endpoint is in the authentication API, not the events API. It requires authentication.

**When to Call:**
- When user opens event creation form
- Before user starts creating an event
- To show available event categories/interests for selection
- When user needs to select event categories during profile setup
- When displaying event categories in filters

**Request Details:**
- Method: GET
- Headers: Include Authorization header with JWT token (required)
- Query Parameters: None (this endpoint returns all active event interests)

**Success Response (200):**
- Returns object containing:
  - `success`: Boolean, always true for successful requests
  - `message`: String, confirmation message
  - `data`: Array of event interest objects, each containing:
    - `id`: Integer, unique interest ID (use this in event_interest_ids when creating events)
    - `name`: String, interest name (e.g., "Music & Concerts", "Sports & Fitness")

**What to Do Next:**
- Display list of event interests as selectable options
- Show interest name
- Allow user to select multiple interests (for event creation)
- Store interest IDs to use when creating events
- Show interests as chips/tags in the UI
- Use interest IDs in the `event_interest_ids` array when creating events

**Complete Endpoint Example:**
- `GET /api/auth/event-interests`
- Headers: `Authorization: Bearer YOUR_JWT_TOKEN`
- Returns: All active event interests/categories

**Error Handling:**
- If you get 401: User needs to log in again - show "Please log in to view event categories"
- If you get 403: User is inactive - show "Account inactive. Please contact support"
- If you get empty array in data: Show "No categories available" message

### Step 2: List Venues (Optional)

**Endpoint:** GET `/events/venues`

**When to Call:**
- When user is filling the venue section in event creation form
- To show available venues user can select from

**Request Details:**
- Method: GET
- Headers: Include Authorization header with JWT token
- Query Parameters (all optional):
  
  **Filter Parameters:**
  - `city`: String, filter venues by city name (case-insensitive partial matching)
    - Example: "Mumbai" will find venues in "Mumbai", "Mumbai Suburbs", etc.
    - Can be combined with other filters
  - `venue_type`: String, filter by venue type (options: "indoor", "outdoor", "virtual", "hybrid")
    - Use "indoor" to show only indoor venues
    - Use "outdoor" to show only outdoor venues
    - Use "virtual" to show only virtual/online venues
    - Use "hybrid" to show only hybrid venues
    - Can be combined with city filter
  
  **Pagination Parameters:**
  - `offset`: Integer, number of venues to skip before returning results (default: 0, minimum: 0)
    - Use 0 for the first page
    - Use 20 for the second page (if limit is 20)
    - Formula: offset = (page_number - 1) × limit
  - `limit`: Integer, number of venues to return per page (default: 20, minimum: 1, maximum: 100)
    - Use 20 for standard pagination
    - Use 50-100 for loading more venues at once
    - Don't exceed 100 as it's the maximum allowed

**Examples of Query Parameter Combinations:**

**Example 1: Get all venues in a specific city**
- Query: `?city=Mumbai`
- Use case: Show venues in Mumbai
- **Complete Endpoint Example:**
  - `GET /api/events/venues?city=Mumbai`
  - Returns: First 20 venues in Mumbai

**Example 2: Get outdoor venues in a city**
- Query: `?city=Mumbai&venue_type=outdoor`
- Use case: Show outdoor venues in Mumbai
- **Complete Endpoint Example:**
  - `GET /api/events/venues?city=Mumbai&venue_type=outdoor`
  - Returns: First 20 outdoor venues in Mumbai

**Example 3: Get venues with pagination**
- Query: `?offset=0&limit=20`
- Use case: First page of venues
- **Complete Endpoint Example:**
  - `GET /api/events/venues?offset=0&limit=20`
  - Returns: First 20 venues from all cities

**Example 4: Search venues in a city with pagination**
- Query: `?city=Delhi&offset=20&limit=20`
- Use case: Second page of venues in Delhi
- **Complete Endpoint Example:**
  - `GET /api/events/venues?city=Delhi&offset=20&limit=20`
  - Returns: Second page (venues 21-40) of venues in Delhi

**Success Response (200):**
- Contains:
  - `total`: Total number of venues
  - `data`: Array of venue objects with:
    - Venue ID, name, address, city
    - Venue type
    - Capacity (informational only)
    - Coordinates (latitude, longitude)

**What to Do Next:**
- Show list of venues for user to select
- Allow user to search/filter by city
- Provide option to create new venue or use custom venue text

### Step 3: Create Event

**Endpoint:** POST `/events`

**When to Call:**
- When user submits the event creation form
- After validating all required fields on the client side

**Request Details:**
- Method: POST
- Headers: Include Authorization header with JWT token
- Content-Type: `multipart/form-data` (required for file uploads)
- Body: Form data with file uploads containing:
  - `title`: Event title (required, 3-200 characters)
  - `description`: Event description (optional, max 20000 characters)
  - `start_time`: String, event start date and time (required, ISO 8601 format, example: "2024-12-25T18:00:00Z")
  - `duration_hours`: Decimal number, event duration in hours (required, must be greater than 0, can be decimal like 2.5 for 2 hours 30 minutes)
  - `event_interest_ids`: String, JSON string array of event interest/category IDs (required, e.g., `"[1,2,3]"`, must be valid interest IDs from the event interests list)
  - Venue option (choose exactly ONE of the following):
    - `venue_id`: Integer ID of existing venue (optional, if user selected from venues list)
    - `venue_text`: String, custom venue text (optional, if not using venue from list, max 255 characters)
  - `max_capacity`: Integer, maximum number of attendees (optional, default: 0 = unlimited, must be 0 or positive)
  - `is_paid`: Boolean, whether event requires payment (optional, true or false as string, default: false)
  - `ticket_price`: Decimal number, price per ticket (optional, required if is_paid is true, must be 0 or greater, example: 500.00)
  - `allow_plus_one`: Boolean, whether attendees can bring a guest (optional, true or false as string, default: true)
  - `gst_number`: String, GST number for paid events (optional, max 50 characters, only needed if is_paid is true)
  - `allowed_genders`: String, gender restrictions (optional, options: "all", "male", "female", "non_binary", default: "all")
  - `cover_images`: File array (optional, 0-3 image files, jpg/jpeg/png/webp formats, max 5MB each)
    - Files are uploaded to Supabase Storage `event-images` bucket
    - Public URLs are automatically generated and stored in the event record
    - Backend validates file type, size, and count
  - `status`: String, event status (optional, options: "draft" or "published", default: "draft")
  - `is_public`: Boolean, whether event is public (optional, true or false as string, default: true)

**Success Response (201):**
- Contains complete event object with all details
- Includes generated event ID and slug
- Includes calculated end_time based on start_time and duration_hours

**What to Do Next:**
- Show success message: "Event created successfully!"
- If status is "draft": Show "Event saved as draft. Publish it to make it visible to others."
- If status is "published": Show "Event is now live and visible to all users!"
- Navigate to event details screen
- Show "Edit Event" and "Manage Requests" options

**Error Handling:**
- If you get 400: Validation error, check the error message and highlight the problematic field
  - Common errors: "Title must be between 3 and 200 characters", "Duration must be greater than 0", "Please provide exactly one venue option", "Maximum 3 cover images allowed", "File size exceeds 5MB", "Invalid file type"
- If you get 401: User needs to log in again
- If you get 422: Unprocessable Entity - usually means invalid form data or file upload issues
- If you get 500: Server error, show "Unable to create event. Please try again."

**Important Notes:**
- Use `multipart/form-data` content type when sending files
- `cover_images` must be actual image files from device, not URLs
- `event_interest_ids` must be a JSON string (e.g., `"[1,2,3]"`), not a raw array
- Boolean fields (`is_paid`, `is_public`, `allow_plus_one`) should be sent as strings ("true"/"false") or actual booleans depending on your HTTP client library
- Backend automatically uploads images to Supabase Storage and stores the public URLs
- `duration_hours` must be greater than 0 (backend enforces this validation)

### Step 4: Update Event (Optional)

**Endpoint:** PUT `/events/{event_id}`

**When to Call:**
- When host wants to edit event details
- When host wants to change event status from draft to published

**Request Details:**
- Method: PUT
- Path Parameter: Replace `{event_id}` with the actual event ID
- Body: JSON object with only the fields you want to update (all fields optional)
  - You can include any of the fields from create event endpoint
  - Only include fields you want to change
  - Same field names, types, and constraints as create event
  - Examples:
    - To update title only: `{"title": "New Event Title"}`
    - To change status to published: `{"status": "published"}`
    - To update capacity: `{"max_capacity": 100}`

**Success Response (200):**
- Contains updated event object

**What to Do Next:**
- Show success message: "Event updated successfully!"
- Refresh the event details screen
- If status changed to published, show "Event is now live!"

**Error Handling:**
- If you get 403: User is not the event host, show "Only the event host can edit this event"
- If you get 404: Event doesn't exist, show "Event not found" and go back
- If you get 400: Validation error, show the error message

### Step 5: Delete Event

**Endpoint:** DELETE `/events/{event_id}`

**When to Call:**
- When host wants to delete/cancel their event
- After user confirms deletion in a confirmation dialog

**Request Details:**
- Method: DELETE
- Path Parameter: Replace `{event_id}` with the actual event ID

**Success Response (204):**
- No content in response body (just success status)

**What to Do Next:**
- Show success message: "Event deleted successfully"
- Navigate back to events list or host dashboard
- Remove event from local cache/lists

**Error Handling:**
- If you get 403: User is not the event host, show "Only the event host can delete this event"
- If you get 404: Event doesn't exist, show "Event not found"

---

## User Request Flow

### When to Use: User Wants to Join an Event

This flow is used when a regular user wants to request to attend an event.

### Step 1: Submit Request to Join

**Endpoint:** POST `/events/{event_id}/requests`

**When to Call:**
- When user taps "Request to Join" button on event details screen
- After user fills the request form (message and number of seats)

**Request Details:**
- Method: POST
- Path Parameter: Replace `{event_id}` with the actual event ID
- Body: JSON object containing:
  - `message`: String, optional message to the host (optional, max 500 characters)
  - `seats_requested`: Integer, number of seats needed (required, minimum 1, maximum 10)

**Success Response (201):**
- Contains request object with:
  - Request ID and UUID
  - Event ID and title
  - Status (will be "pending")
  - Message and seats requested
  - Created and updated timestamps

**What to Do Next:**
- Show success message: "Your request has been submitted! The host will review it soon."
- Change button to "View Request Status"
- Optionally send a push notification to the host
- Update UI to show request is pending

**Error Handling:**
- If you get 400: Check error message
  - "You already have a pending request": Show "You already have a pending request. Please wait for the host's response."
  - "You have already been accepted": Show "You're already accepted! Please confirm your attendance."
  - "Event is at capacity": Show "This event is full. Cannot submit request."
- If you get 404: Event doesn't exist, show "Event not found"
- If you get 401: User needs to log in again

### Step 2: Check Request Status

**Endpoint:** GET `/events/{event_id}/my-request`

**When to Call:**
- When user opens event details screen (to check if they have a request)
- When user taps "View Request Status" button
- Periodically to check for status updates (polling or push notification)

**Request Details:**
- Method: GET
- Path Parameter: Replace `{event_id}` with the actual event ID

**Success Response (200):**
- Contains request object with current status:
  - Status can be: "pending", "accepted", "declined", "cancelled", "expired"
  - Includes message, host_message (if any), seats requested
  - `can_confirm`: Boolean indicating if user can confirm attendance (true if accepted and not yet confirmed)

**What to Do Next:**
- Display request status prominently on event details screen
- If status is "pending": Show "Waiting for host's response" with a loading indicator
- If status is "accepted": 
  - Show "Request Accepted!" message
  - Show host's message if provided
  - Show "Confirm Attendance" button (if can_confirm is true)
- If status is "declined": 
  - Show "Request Declined" message
  - Show host's message if provided
  - Optionally allow user to submit a new request
- If status is "cancelled" or "expired": Show appropriate message

**Error Handling:**
- If you get 404: User hasn't submitted a request yet, show "Request to Join" button instead
- If you get 401: User needs to log in again

### Step 3: View All My Requests

**Endpoint:** GET `/events/my-requests`

**When to Call:**
- When user opens "My Requests" screen
- To show all requests user has submitted across all events

**Request Details:**
- Method: GET
- Headers: Include Authorization header with JWT token
- Query Parameters (all optional):
  
  **Filter Parameters:**
  - `status_filter`: String, filter requests by status (options: "pending", "accepted", "declined", "cancelled")
    - Use "pending" to show only requests waiting for host response
    - Use "accepted" to show only accepted requests (user can confirm attendance)
    - Use "declined" to show only declined requests
    - Use "cancelled" to show only cancelled requests
    - If not provided, returns all requests regardless of status

**Examples of Query Parameter Usage:**

**Example 1: Get all pending requests**
- Query: `?status_filter=pending`
- Use case: Show only requests waiting for host response
- **Complete Endpoint Example:**
  - `GET /api/events/my-requests?status_filter=pending`
  - Returns: All pending requests user has submitted

**Example 2: Get all accepted requests**
- Query: `?status_filter=accepted`
- Use case: Show requests user can confirm attendance for
- **Complete Endpoint Example:**
  - `GET /api/events/my-requests?status_filter=accepted`
  - Returns: All accepted requests user can confirm attendance for

**Example 3: Get all requests (no filter)**
- Query: (no parameters)
- Use case: Show all requests across all statuses
- **Complete Endpoint Example:**
  - `GET /api/events/my-requests`
  - Returns: All requests user has submitted regardless of status

**Success Response (200):**
- Array of request objects, each containing:
  - Request ID, event ID, event title
  - Status, message, host_message
  - Seats requested
  - Created and updated timestamps
  - `can_confirm`: Boolean for each request

**What to Do Next:**
- Display list of requests grouped by status
- Show event title, date, and request status for each
- Make each request clickable to view event details
- Show action buttons based on status:
  - Pending: "View Status"
  - Accepted: "Confirm Attendance" (if can_confirm is true)
  - Declined: "View Details" or "Request Again"

**Error Handling:**
- If you get 401: User needs to log in again
- If array is empty: Show "You haven't submitted any requests yet"

### Step 4: Confirm Attendance (After Request Accepted)

**Endpoint:** POST `/events/{event_id}/confirm-attendance`

**When to Call:**
- When user taps "Confirm Attendance" button after their request is accepted
- After user selects number of seats to confirm

**Request Details:**
- Method: POST
- Path Parameter: Replace `{event_id}` with the actual event ID
- Body: JSON object containing:
  - `seats`: Integer, number of seats to confirm (required, minimum 1, maximum 10)

**Success Response (200):**
- Contains ticket object with:
  - Ticket ID, event ID, event title
  - Event start and end times
  - Ticket secret code (unique identifier)
  - Number of seats
  - Payment status (will be "unpaid" for free events)
  - Status (will be "going")
  - QR code data (string that can be converted to QR code)
  - Created timestamp

**What to Do Next:**
- Show success message: "Attendance confirmed! Your ticket has been generated."
- Display ticket details screen with:
  - Event information
  - Ticket secret code (prominently displayed)
  - QR code (generate QR code from qr_code_data)
  - Instructions: "Show this ticket at the event entrance"
- Add "View Ticket" option to event details screen
- Optionally save ticket to device (for offline access)

**Error Handling:**
- If you get 400: Check error message
  - "You need to have an accepted request": Show "Please wait for the host to accept your request first."
  - "You have already confirmed attendance": Show "You've already confirmed your attendance. View your ticket."
  - "The event is at full capacity": Show "Event is full. Cannot confirm attendance."
- If you get 404: Event doesn't exist
- If you get 401: User needs to log in again

---

## Host Management Flow

### When to Use: Host Managing Event Requests

This flow is used when an event host wants to manage requests from users who want to attend their event.

### Step 1: View All Requests for Event

**Endpoint:** GET `/events/{event_id}/requests`

**When to Call:**
- When host opens "Manage Requests" screen for their event
- When host wants to see all pending requests
- To refresh the requests list

**Request Details:**
- Method: GET
- Headers: Include Authorization header with JWT token
- Path Parameter: Replace `{event_id}` with the actual event ID
- Query Parameters: None (this endpoint returns all requests for the event)

**Note:** This endpoint returns all requests regardless of status. You can filter the results on the client side by the `status` field in each request object.

**Success Response (200):**
- Returns array of request objects, each containing:
  - `id`: Request ID
  - `uuid`: Unique request identifier
  - `requester_id`: ID of the user who made the request
  - `requester_name`: Username of the requester
  - `status`: Current status (pending, accepted, declined, cancelled, expired)
  - `message`: Message from requester
  - `host_message`: Optional message from host (if any)
  - `seats_requested`: Number of seats requested
  - `created_at`: When request was created (ISO format)
  - `updated_at`: When request was last updated (ISO format)

**What to Do Next:**
- Display list of requests, preferably grouped by status (pending, accepted, declined)
- Show requester name, message, and seats requested
- For pending requests, show "Accept" and "Decline" buttons
- For accepted requests, show "Accepted" badge
- For declined requests, show "Declined" badge
- Make each request clickable to view requester profile
- Show request count badge (number of pending requests)
- Filter requests by status on the client side if needed:
  - Filter for `status === "pending"` to show only pending requests
  - Filter for `status === "accepted"` to show accepted requests
  - Filter for `status === "declined"` to show declined requests

**Error Handling:**
- If you get 403: User is not the event host, show "Only the event host can view requests"
- If you get 404: Event doesn't exist
- If you get 401: User needs to log in again
- If array is empty: Show "No requests yet"

### Step 2: View Requester Profile

**Endpoint:** GET `/events/{event_id}/requests/{request_id}/profile`

**When to Call:**
- When host taps on a request to see more details about the requester
- To help host make a decision about accepting/declining

**Request Details:**
- Method: GET
- Path Parameters: Replace `{event_id}` and `{request_id}` with actual IDs

**Success Response (200):**
- Contains user profile summary with:
  - User ID and name
  - Phone number (if available)
  - Bio/description
  - Gender
  - Location
  - Profile pictures (array of image URLs)
  - Event interests (categories user is interested in)
  - Verification status

**What to Do Next:**
- Display requester profile screen with all information
- Show profile pictures in a carousel
- Show event interests as tags
- Provide "Accept" and "Decline" buttons
- Allow host to go back to requests list

**Error Handling:**
- If you get 403: User is not the event host
- If you get 404: Request doesn't exist
- If you get 401: User needs to log in again

### Step 3: Accept Single Request

**Endpoint:** PUT `/events/{event_id}/requests/{request_id}/accept`

**When to Call:**
- When host taps "Accept" button on a request
- After host optionally adds a message to the requester

**Request Details:**
- Method: PUT
- Path Parameters: Replace `{event_id}` and `{request_id}` with actual IDs
- Body: JSON object (optional, can be empty):
  - `host_message`: String, optional message to the requester (optional, max 500 characters)

**Success Response (200):**
- Contains updated request object with status "accepted"
- Includes host_message if provided
- Includes `can_confirm`: true (indicating requester can now confirm attendance)

**What to Do Next:**
- Show success message: "Request accepted! User has been notified."
- Update request status in the list to "accepted"
- Remove from pending requests list
- Send push notification to requester (if implemented)
- Update event going_count display
- Optionally show confirmation dialog before accepting

**Error Handling:**
- If you get 400: Check error message
  - "The event has reached its capacity": Show "Cannot accept request. Event is full. Only X seats available."
  - Show available seats count to help host make decisions
- If you get 403: User is not the event host
- If you get 404: Request doesn't exist or already processed
- If you get 401: User needs to log in again

### Step 4: Decline Single Request

**Endpoint:** PUT `/events/{event_id}/requests/{request_id}/decline`

**When to Call:**
- When host taps "Decline" button on a request
- After host optionally adds a message explaining why

**Request Details:**
- Method: PUT
- Path Parameters: Replace `{event_id}` and `{request_id}` with actual IDs
- Body: JSON object (optional, can be empty):
  - `host_message`: String, optional message to the requester (optional, max 500 characters)

**Success Response (200):**
- Contains updated request object with status "declined"
- Includes host_message if provided

**What to Do Next:**
- Show success message: "Request declined. User has been notified."
- Update request status in the list to "declined"
- Remove from pending requests list
- Send push notification to requester (if implemented)
- Update event requests_count display
- Optionally show confirmation dialog before declining

**Error Handling:**
- If you get 403: User is not the event host
- If you get 404: Request doesn't exist or already processed
- If you get 401: User needs to log in again

### Step 5: Bulk Accept/Decline Requests

**Endpoint:** POST `/events/{event_id}/requests/bulk-action`

**When to Call:**
- When host wants to accept or decline multiple requests at once
- When host selects multiple requests and chooses an action

**Request Details:**
- Method: POST
- Path Parameter: Replace `{event_id}` with the actual event ID
- Body: JSON object containing:
  - `request_ids`: Array of integers, list of request IDs to process (required, minimum 1, maximum 100 request IDs)
  - `action`: String, action to perform (required, must be exactly "accept" or "decline")
  - `host_message`: String, optional message to be sent to all requesters (optional, max 500 characters, will be applied to all accepted/declined requests)

**Success Response (200):**
- Contains summary object with:
  - `success`: Boolean indicating if all requests were processed successfully
  - `processed_count`: Total number of requests processed
  - `accepted_count`: Number of requests accepted (if action was accept)
  - `declined_count`: Number of requests declined (if action was decline)
  - `errors`: Array of any errors that occurred (if any)

**What to Do Next:**
- Show success message: "X requests processed successfully"
- If there are errors, show: "X requests processed, Y failed. Check details."
- Update the requests list to reflect new statuses
- Remove processed requests from pending list
- Update event counts (going_count, requests_count)
- Send push notifications to all affected requesters (if implemented)
- If capacity exceeded during bulk accept, show which requests failed and why

**Error Handling:**
- If you get 400: Check error message
  - "No pending requests found": Show "Selected requests have already been processed"
  - "Cannot accept all requests. The event has reached its capacity": Show detailed message with available seats
- If you get 403: User is not the event host
- If you get 404: Event doesn't exist
- If you get 401: User needs to log in again
- If `errors` array is not empty: Show which specific requests failed and why

---

## Invitation Flow

### When to Use: Host Inviting Users or User Responding to Invitations

This flow covers both sides: hosts inviting users and users responding to invitations.

### Part A: Host Inviting Users

### Step 1: Invite Users to Event

**Endpoint:** POST `/events/{event_id}/invitations`

**When to Call:**
- When host wants to invite specific users to their event
- After host selects users from their contacts/friends list
- When host wants to send personalized invitations

**Request Details:**
- Method: POST
- Path Parameter: Replace `{event_id}` with the actual event ID
- Body: JSON object containing:
  - `user_ids`: Array of integers, list of user IDs to invite (required, minimum 1, maximum 50 user IDs)
  - `message`: String, optional personal message for all invitations (optional, max 500 characters, will be included in all invitations)
  - `expires_at`: String, optional expiration date and time for invitations (optional, ISO 8601 format, example: "2024-12-30T23:59:59Z", if not provided, invitations don't expire)

**Success Response (200):**
- Contains summary object with:
  - `success`: Boolean indicating if all invitations were created successfully
  - `created_count`: Number of invitations created
  - `skipped_count`: Number of users skipped (if they already have an invitation)
  - `errors`: Array of any errors that occurred
  - `invites`: Array of created invitation objects with:
    - Invite ID, user ID, user name
    - Status (will be "pending")
    - Message

**What to Do Next:**
- Show success message: "X invitations sent successfully"
- If some were skipped: Show "X invitations sent, Y users already invited"
- If there are errors: Show which users couldn't be invited and why
- Send push notifications to invited users (if implemented)
- Update invitations list for the event
- Optionally show confirmation: "Invitations sent! Users will be notified."

**Error Handling:**
- If you get 400: Check error message
  - "Some of the user IDs you provided are invalid": Show list of invalid IDs
- If you get 403: User is not the event host
- If you get 404: Event doesn't exist
- If you get 401: User needs to log in again

### Step 2: View Event Invitations

**Endpoint:** GET `/events/{event_id}/invitations`

**When to Call:**
- When host wants to see all invitations sent for their event
- To check invitation statuses (pending, accepted, declined, expired)

**Request Details:**
- Method: GET
- Headers: Include Authorization header with JWT token
- Path Parameter: Replace `{event_id}` with the actual event ID
- Query Parameters (all optional):
  
  **Filter Parameters:**
  - `status_filter`: String, filter invitations by status (options: "pending", "accepted", "declined", "expired")
    - Use "pending" to show only invitations waiting for user response
    - Use "accepted" to show only invitations that have been accepted
    - Use "declined" to show only invitations that have been declined
    - Use "expired" to show only expired invitations
    - If not provided, returns all invitations for the event regardless of status

**Examples of Query Parameter Usage:**

**Example 1: Get all pending invitations for event**
- Query: `?status_filter=pending`
- Use case: Show only invitations waiting for user response
- **Complete Endpoint Example:**
  - `GET /api/events/123/invitations?status_filter=pending`
  - Returns: All pending invitations for event ID 123

**Example 2: Get all accepted invitations for event**
- Query: `?status_filter=accepted`
- Use case: Show which users have accepted the invitation
- **Complete Endpoint Example:**
  - `GET /api/events/123/invitations?status_filter=accepted`
  - Returns: All accepted invitations for event ID 123

**Example 3: Get all invitations for event (no filter)**
- Query: (no parameters)
- Use case: Show all invitations for the event across all statuses
- **Complete Endpoint Example:**
  - `GET /api/events/123/invitations`
  - Returns: All invitations for event ID 123 regardless of status

**Success Response (200):**
- Returns array of invitation objects, each containing:
  - `invite_id`: Unique invitation ID
  - `user_id`: ID of the invited user
  - `user_name`: Username of the invited user
  - `status`: Current status (pending, accepted, declined, expired)
  - `message`: Personal message sent with invitation

**What to Do Next:**
- Display list of invitations with user names and statuses
- Show status badges (pending, accepted, declined, expired)
- Allow host to see who has responded
- If status is "pending": Show "Waiting for response"
- If status is "accepted": Show "User is going"
- If status is "declined": Show "User declined"
- If status is "expired": Show "Invitation expired"

**Error Handling:**
- If you get 403: User is not the event host - show "Only event host can view invitations"
- If you get 404: Event doesn't exist - show "Event not found"
- If you get 401: User needs to log in again

---

### Part B: User Responding to Invitations

### Step 3: View My Invitations

**Endpoint:** GET `/events/my-invitations`

**When to Call:**
- When user opens their invitations screen
- When user wants to see all invitations they've received
- To check status of invitations (pending, accepted, declined, expired)
- On app startup or when navigating to invitations tab

**Request Details:**
- Method: GET
- Headers: Include Authorization header with JWT token
- Query Parameters (all optional):
  
  **Filter Parameters:**
  - `status_filter`: String, filter invitations by status (options: "pending", "accepted", "declined", "expired")
    - Use "pending" to show only invitations waiting for user response
    - Use "accepted" to show only invitations user has accepted
    - Use "declined" to show only invitations user has declined
    - Use "expired" to show only expired invitations
    - If not provided, returns all invitations regardless of status

**Examples of Query Parameter Usage:**

**Example 1: Get all pending invitations**
- Query: `?status_filter=pending`
- Use case: Show only invitations waiting for user response
- **Complete Endpoint Example:**
  - `GET /api/events/my-invitations?status_filter=pending`
  - Returns: All pending invitations waiting for user response

**Example 2: Get all accepted invitations**
- Query: `?status_filter=accepted`
- Use case: Show invitations user has accepted
- **Complete Endpoint Example:**
  - `GET /api/events/my-invitations?status_filter=accepted`
  - Returns: All invitations user has accepted

**Example 3: Get all invitations (no filter)**
- Query: (no parameters)
- Use case: Show all invitations across all statuses
- **Complete Endpoint Example:**
  - `GET /api/events/my-invitations`
  - Returns: All invitations user has received regardless of status

**Success Response (200):**
- Returns array of invitation objects, each containing:
  - `invite_id`: Unique invitation ID
  - `event_id`: ID of the event
  - `event_title`: Title of the event
  - `event_start_time`: When the event starts (ISO format)
  - `host_name`: Username of the event host
  - `status`: Current status (pending, accepted, declined, expired)
  - `message`: Personal message from host
  - `created_at`: When invitation was created (ISO format)

**What to Do Next:**
- Display list of invitations with event details
- Show event title, host name, and start time
- Show status badge for each invitation
- If status is "pending": Show "Respond" button
- If status is "accepted": Show "You're Going" badge
- If status is "declined": Show "You Declined" badge
- If status is "expired": Show "Expired" badge with grayed out appearance
- Sort by most recent first (created_at descending)
- Allow user to tap invitation to see full event details

**Error Handling:**
- If you get 401: User needs to log in again
- If you get empty array: Show "No invitations yet" message

---

### Step 4: Respond to Invitation

**Endpoint:** PUT `/events/invitations/{invite_id}/respond`

**When to Call:**
- When user taps "Going" or "Not Going" button on an invitation
- After user views invitation details and decides to respond
- When user wants to accept or decline an invitation

**Request Details:**
- Method: PUT
- Path Parameter: Replace `{invite_id}` with the actual invitation ID
- Body: JSON object containing:
  - `response`: String, user's response (required, must be exactly "going" or "not_going")
  - `message`: String, optional response message to host (optional, max 200 characters)

**Success Response (200):**
- Returns object containing:
  - `invite_id`: The invitation ID
  - `status`: Updated status (accepted or declined)
  - `event_id`: ID of the event
  - `event_title`: Title of the event
  - `is_paid`: Whether event requires payment
  - `requires_payment`: Whether user needs to pay (true if going to paid event)

**What to Do Next:**
- If response is "going":
  - If event is free: Show success message "You're going! Your ticket has been generated."
  - If event is paid: Show message "You're going! Please complete payment to get your ticket."
  - Navigate to ticket screen or payment screen accordingly
  - Update invitation status to "accepted" in the list
  - Show ticket details if available
- If response is "not_going":
  - Show confirmation message "You've declined the invitation."
  - Update invitation status to "declined" in the list
  - Optionally allow user to change their mind later
- Send notification to event host about the response
- Refresh invitations list to show updated status

**Error Handling:**
- If you get 400: Check error message
  - "This invitation has expired": Show "Invitation expired. Contact host for new invitation."
  - "The event is at full capacity": Show "Event is full. Cannot accept invitation."
- If you get 404: Invitation not found or already responded - show "Invitation not found or already processed"
- If you get 401: User needs to log in again

---

## Ticket Management Flow

### When to Use: User Viewing Their Tickets

This flow covers users viewing and managing their event tickets.

### Step 1: View All My Tickets

**Endpoint:** GET `/events/my-tickets`

**When to Call:**
- When user opens their tickets screen
- When user wants to see all tickets they have
- On app startup or when navigating to tickets tab
- After confirming attendance or accepting invitation

**Request Details:**
- Method: GET
- Headers: Include Authorization header with JWT token
- Query Parameters (all optional):
  
  **Filter Parameters:**
  - `event_id`: Integer, filter tickets by specific event ID
    - Use this to show ticket for a specific event only
    - If not provided, returns all tickets for the user
    - Useful when user wants to check if they have a ticket for a specific event

**Examples of Query Parameter Usage:**

**Example 1: Get all tickets**
- Query: (no parameters)
- Use case: Show all tickets user has for all events
- **Complete Endpoint Example:**
  - `GET /api/events/my-tickets`
  - Returns: All tickets user has for all events

**Example 2: Get ticket for specific event**
- Query: `?event_id=123`
- Use case: Check if user has a ticket for event ID 123
- **Complete Endpoint Example:**
  - `GET /api/events/my-tickets?event_id=123`
  - Returns: Tickets user has for event ID 123 (if any)

**Note:** This endpoint returns an array. If you want a single ticket for a specific event, use GET `/api/events/{event_id}/my-ticket` instead.

**Success Response (200):**
- Returns array of ticket objects, each containing:
  - `ticket_id`: Unique ticket ID
  - `event_id`: ID of the event
  - `event_title`: Title of the event
  - `event_start_time`: When the event starts (ISO format)
  - `event_end_time`: When the event ends (ISO format)
  - `ticket_secret`: Unique secret code for ticket verification
  - `seats`: Number of seats (usually 1)
  - `is_paid`: Whether event requires payment
  - `payment_status`: Payment status (unpaid, paid, pending)
  - `status`: Ticket status (going, checked_in, cancelled)
  - `created_at`: When ticket was created (ISO format)
  - `qr_code_data`: QR code data string for scanning

**What to Do Next:**
- Display list of tickets with event details
- Show event title, date, and time
- Show ticket status badge (going, checked_in, cancelled)
- Show payment status if event is paid (paid, unpaid, pending)
- Display QR code for each ticket using `qr_code_data`
- Allow user to tap ticket to see full details
- Sort by event start time (upcoming events first)
- Show "No tickets yet" message if array is empty
- For upcoming events: Show countdown or "Event in X days"
- For past events: Show "Event completed" badge

**Error Handling:**
- If you get 401: User needs to log in again
- If you get empty array: Show "No tickets yet" message with helpful text

---

### Step 2: Get Ticket for Specific Event

**Endpoint:** GET `/events/{event_id}/my-ticket`

**When to Call:**
- When user views event details and wants to see their ticket
- When user taps "View Ticket" button on event screen
- When user needs to show ticket at event entrance
- Before event starts to prepare for check-in

**Request Details:**
- Method: GET
- Path Parameter: Replace `{event_id}` with the actual event ID

**Success Response (200):**
- Returns ticket object containing:
  - `ticket_id`: Unique ticket ID
  - `event_id`: ID of the event
  - `event_title`: Title of the event
  - `event_start_time`: When the event starts (ISO format)
  - `event_end_time`: When the event ends (ISO format)
  - `ticket_secret`: Unique secret code for ticket verification
  - `seats`: Number of seats
  - `is_paid`: Whether event requires payment
  - `payment_status`: Payment status (unpaid, paid, pending)
  - `status`: Ticket status (going, checked_in, cancelled)
  - `created_at`: When ticket was created (ISO format)
  - `qr_code_data`: QR code data string for scanning

**What to Do Next:**
- Display ticket details screen with:
  - Event title and date/time prominently displayed
  - Large QR code generated from `qr_code_data`
  - Ticket secret code (for manual verification if needed)
  - Payment status if event is paid
  - Ticket status badge
- Allow user to share ticket (if needed)
- Show "Ready for check-in" message if event is upcoming
- Show "Already checked in" if status is "checked_in"
- If payment is pending: Show "Complete payment to activate ticket"
- If payment is unpaid: Show "Payment required" with payment button

**Error Handling:**
- If you get 404: No ticket found - show "You don't have a ticket for this event. Please confirm your attendance first."
- If you get 401: User needs to log in again
- If you get 403: User doesn't have permission - show appropriate message

---

## Venue Management Flow

### When to Use: Host Creating or Viewing Venues

This flow covers venue-related operations for event hosts.

### Step 1: Get Single Venue Details

**Endpoint:** GET `/events/venues/{venue_id}`

**When to Call:**
- When host selects a venue from the venues list
- When viewing venue details before creating event
- When editing event and needs to see venue information
- When displaying venue information on event details screen

**Request Details:**
- Method: GET
- Path Parameter: Replace `{venue_id}` with the actual venue ID

**Success Response (200):**
- Returns venue object containing:
  - `id`: Venue ID
  - `uuid`: Unique venue identifier
  - `name`: Venue name
  - `address`: Full address
  - `city`: City name
  - `venue_type`: Type of venue (indoor, outdoor, virtual, hybrid)
  - `capacity`: Venue capacity (informational only, 0 means unlimited)
  - `latitude`: Latitude coordinate (if available)
  - `longitude`: Longitude coordinate (if available)
  - `metadata`: Additional venue information (JSON object)
  - `is_active`: Whether venue is active
  - `created_at`: When venue was created (ISO format)
  - `updated_at`: When venue was last updated (ISO format)

**What to Do Next:**
- Display venue details with:
  - Venue name and address prominently
  - City and venue type
  - Show on map if latitude/longitude are available
  - Display capacity information (note: this is informational, event capacity is separate)
  - Show any additional metadata if available
- Allow host to use this venue when creating event
- Show "Use this venue" button if viewing before event creation
- Display venue on map if coordinates are available

**Error Handling:**
- If you get 404: Venue not found - show "Venue not found or has been removed"
- If you get 401: User needs to log in again

---

### Step 2: Create New Venue

**Endpoint:** POST `/events/venues`

**When to Call:**
- When host wants to create a new venue that doesn't exist in the list
- When host is creating an event and venue is not in the venues list
- When host wants to add a custom venue location

**Request Details:**
- Method: POST
- Body: JSON object containing:
  - `name`: String, venue name (required, 1-150 characters)
  - `address`: String, full address including street address (required)
  - `city`: String, city name (required, 1-100 characters)
  - `venue_type`: String, type of venue (optional, default: "indoor", options: "indoor", "outdoor", "virtual", "hybrid")
  - `capacity`: Integer, venue capacity hint (optional, default: 0 for unlimited, informational only, must be 0 or positive)
  - `latitude`: Decimal number, latitude coordinate (optional, between -90 and 90, for map display)
  - `longitude`: Decimal number, longitude coordinate (optional, between -180 and 180, for map display)
  - `metadata`: Object, additional venue information as JSON object (optional, can contain accessibility info, amenities, etc.)
  - `is_active`: Boolean, whether venue is active (optional, true or false, default: true)

**Success Response (201):**
- Returns created venue object with all fields including:
  - `id`: Newly created venue ID (use this when creating event)
  - `uuid`: Unique venue identifier
  - All other venue fields as described in GET venue endpoint

**What to Do Next:**
- Show success message: "Venue created successfully"
- Store the venue ID for use in event creation
- If creating event: Pre-fill venue_id with the new venue ID
- Optionally navigate back to event creation form
- Add venue to local venues list for future use
- Show confirmation: "Venue saved! You can now use it for your event."

**Error Handling:**
- If you get 400: Check error message
  - Validation errors: Show specific field errors (e.g., "Name is required", "City must be between 1-100 characters")
  - "Unable to create the venue": Show "Please check your input and try again"
- If you get 401: User needs to log in again
- If you get 422: Invalid data format - show "Please check all required fields"

---

## Complete User Journey Examples

### Example 1: User Joining a Free Event

**Step-by-Step Flow:**

1. **Browse Events**
   - User opens app and sees event list (GET `/events`)
   - User taps on an interesting event
   - App shows event details (GET `/events/{event_id}`)

2. **Request to Join**
   - User taps "Request to Join" button
   - App sends request (POST `/events/{event_id}/requests`)
   - App shows "Request sent! Waiting for host approval."

3. **Check Request Status**
   - User can check status anytime (GET `/events/{event_id}/my-request`)
   - Status shows "pending" initially
   - User receives notification when host accepts

4. **Confirm Attendance**
   - When status becomes "accepted", user sees "Confirm Attendance" button
   - User taps button and confirms (POST `/events/{event_id}/confirm-attendance`)
   - App shows "Attendance confirmed! Your ticket has been generated."

5. **View Ticket**
   - User can view ticket anytime (GET `/events/{event_id}/my-ticket`)
   - App displays QR code and ticket details
   - User shows ticket at event entrance

---

### Example 2: Host Managing Event Requests

**Step-by-Step Flow:**

1. **View Requests**
   - Host opens their event
   - Host taps "View Requests" (GET `/events/{event_id}/requests`)
   - App shows list of pending requests

2. **Review Requester Profile**
   - Host taps on a request
   - Host views requester profile (GET `/events/{event_id}/requests/{request_id}/profile`)
   - App shows user's bio, interests, profile pictures

3. **Accept or Decline**
   - Host decides to accept request
   - Host taps "Accept" (PUT `/events/{event_id}/requests/{request_id}/accept`)
   - App shows "Request accepted! User has been notified."
   - Or host can decline (PUT `/events/{event_id}/requests/{request_id}/decline`)

4. **Bulk Actions (Optional)**
   - Host selects multiple requests
   - Host chooses "Accept All" or "Decline All" (POST `/events/{event_id}/requests/bulk-action`)
   - App shows summary: "X requests accepted, Y declined"

---

### Example 3: User Responding to Invitation

**Step-by-Step Flow:**

1. **Receive Invitation**
   - User receives push notification about invitation
   - User opens invitations screen (GET `/events/my-invitations`)
   - App shows list of invitations

2. **View Invitation**
   - User taps on an invitation
   - App shows event details and host's message

3. **Respond to Invitation**
   - User decides to go
   - User taps "Going" (PUT `/events/invitations/{invite_id}/respond`)
   - If free event: App shows "You're going! Ticket generated."
   - If paid event: App shows "You're going! Please complete payment."

4. **View Ticket**
   - User views ticket (GET `/events/{event_id}/my-ticket`)
   - App displays QR code for event check-in

---

## Error Handling Best Practices

### Common Error Scenarios

**1. Network Failures**
- **What to Do:**
  - Show user-friendly message: "Unable to connect. Please check your internet connection."
  - Allow user to retry the request
  - Implement automatic retry with exponential backoff
  - Show loading indicator while retrying

**2. Authentication Errors (401)**
- **What to Do:**
  - Show message: "Your session has expired. Please log in again."
  - Clear stored authentication token
  - Redirect user to login screen
  - Don't show technical error details to user

**3. Validation Errors (400)**
- **What to Do:**
  - Check the `error` field in response for user-friendly message
  - Display error message clearly to user
  - Highlight fields that have errors
  - Show specific field errors if available in `details` object
  - Allow user to correct and resubmit

**4. Permission Errors (403)**
- **What to Do:**
  - Show message from `error` field (e.g., "Only the event host can perform this action")
  - Hide or disable the action button
  - Don't allow user to retry (permission won't change)
  - Optionally show "Contact event host" message

**5. Not Found Errors (404)**
- **What to Do:**
  - Show message from `error` field (e.g., "Event not found or has been removed")
  - Navigate user back to previous screen
  - Refresh the list if applicable
  - Don't show technical details like event ID

**6. Capacity Errors**
- **What to Do:**
  - Show message: "Event is at full capacity. Only X seats available."
  - Display available seats count from `details.available_seats`
  - Allow user to request fewer seats if applicable
  - Show "Event Full" badge on event card

**7. Duplicate Request Errors**
- **What to Do:**
  - Show message: "You already have a pending request for this event."
  - Show current request status instead
  - Allow user to view their existing request
  - Don't allow duplicate submissions

**8. Server Errors (500)**
- **What to Do:**
  - Show generic message: "Something went wrong. Please try again later."
  - Log error details for debugging (don't show to user)
  - Allow user to retry after a delay
  - Provide "Contact Support" option if error persists

---

## Response Format Guidelines

### Success Response Structure

All successful API responses follow this structure:

**For Single Object:**
- Direct object with fields (e.g., event object, ticket object)

**For Lists:**
- Array of objects (e.g., array of events, array of tickets)

**For Paginated Lists:**
- Object containing:
  - `total`: Total number of items
  - `offset`: Current offset
  - `limit`: Items per page
  - `data`: Array of items

### Error Response Structure

All error responses follow this structure:

- `success`: Always `false`
- `error`: User-friendly error message (display this to user)
- `error_code`: Technical error code (for debugging, don't show to user)
- `details`: Additional error details (optional, may contain field-specific errors)

### Status Code Reference

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **204 No Content**: Resource deleted successfully
- **400 Bad Request**: Validation error or bad input
- **401 Unauthorized**: Authentication required or token expired
- **403 Forbidden**: User doesn't have permission
- **404 Not Found**: Resource doesn't exist
- **409 Conflict**: Resource conflict (e.g., duplicate request)
- **422 Unprocessable Entity**: Invalid data format
- **500 Internal Server Error**: Server error

---

## Testing Checklist

Before releasing your app, test these scenarios:

**Authentication:**
- [ ] Login with valid credentials
- [ ] Handle expired token gracefully
- [ ] Handle invalid token gracefully
- [ ] Logout and verify token is cleared

**Event Discovery:**
- [ ] List events with filters
- [ ] View single event details
- [ ] Handle empty event list
- [ ] Handle event not found

**Event Creation:**
- [ ] Create event with all required fields
- [ ] Create event with existing venue
- [ ] Create event with new venue
- [ ] Create event with custom venue text
- [ ] Handle validation errors
- [ ] Update event successfully
- [ ] Delete event successfully

**Request Flow:**
- [ ] Submit request to join event
- [ ] Check request status
- [ ] View all my requests
- [ ] Handle duplicate request error
- [ ] Confirm attendance after acceptance
- [ ] Handle capacity exceeded error

**Host Management:**
- [ ] View all requests for event
- [ ] View requester profile
- [ ] Accept single request
- [ ] Decline single request
- [ ] Bulk accept requests
- [ ] Bulk decline requests
- [ ] Handle permission errors

**Invitation Flow:**
- [ ] Host invites users
- [ ] View event invitations (host)
- [ ] View my invitations (user)
- [ ] Respond to invitation (going)
- [ ] Respond to invitation (not going)
- [ ] Handle expired invitation

**Ticket Management:**
- [ ] View all my tickets
- [ ] View ticket for specific event
- [ ] Display QR code correctly
- [ ] Handle ticket not found

**Error Handling:**
- [ ] Network failure scenarios
- [ ] Authentication errors
- [ ] Validation errors
- [ ] Permission errors
- [ ] Not found errors
- [ ] Server errors

---

## Additional Tips

1. **Always Include Authorization Header**
   - Every API call (except login/signup) requires: `Authorization: Bearer {token}`
   - Store token securely in device storage
   - Refresh token before it expires

2. **Handle Loading States**
   - Show loading indicators during API calls
   - Disable buttons while request is in progress
   - Prevent duplicate submissions

3. **Cache When Appropriate**
   - Cache event lists for offline viewing
   - Cache user's tickets locally
   - Refresh cache when user performs actions

4. **User Feedback**
   - Always show success/error messages
   - Use toast notifications for quick feedback
   - Show confirmation dialogs for destructive actions

5. **Offline Handling**
   - Detect network connectivity
   - Queue requests when offline
   - Show "No internet connection" message
   - Sync when connection is restored

6. **Pagination**
   - Implement infinite scroll or "Load More" button
   - Default limit is 20 items per page
   - Maximum limit is 100 items per page

7. **Date/Time Formatting**
   - All dates are in ISO 8601 format (e.g., "2024-12-25T18:00:00Z")
   - Convert to local timezone for display
   - Show relative time (e.g., "in 2 days", "yesterday")

8. **Image Handling**
   - Event cover images are uploaded as files via `multipart/form-data`
   - Files are uploaded to Supabase Storage and URLs are returned in response
   - Supported formats: jpg, jpeg, png, webp
   - Max file size: 5MB per image
   - Max images: 3 per event
   - For displaying images: Use URLs from event response (already uploaded to Supabase)
   - Load images asynchronously
   - Show placeholder while loading
   - Handle image load failures gracefully

---

This completes the API integration guide. All endpoints are documented with clear instructions for mobile developers. If you have any questions during integration, refer to the error messages returned by the API - they are designed to be user-friendly and actionable.