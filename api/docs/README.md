# API Module Documentation

## Overview
The API module provides FastAPI-based endpoints for mobile applications, offering high-performance API access to all platform features.

## Quick Links

- **[SDK Integration Guide](./SDK_INTEGRATION_GUIDE.md)** - Complete guide for frontend developers to generate and integrate API client SDKs
- **Interactive API Docs (Swagger UI):** `https://loopinbackend-g17e.onrender.com/api/docs`
- **OpenAPI JSON Spec:** `https://loopinbackend-g17e.onrender.com/api/openapi.json`
- **ReDoc Documentation:** `https://loopinbackend-g17e.onrender.com/api/redoc`

## Architecture
- **FastAPI Framework**: High-performance async API framework
- **Django Integration**: Seamless integration with Django ORM and models
- **JWT Authentication**: Secure token-based authentication
- **CORS Support**: Cross-origin resource sharing for mobile clients
- **OpenAPI 3.0**: Standard API specification for SDK generation

## Router Structure

### Authentication Router (`users/auth_router.py`)
- **Purpose**: Phone-based authentication with OTP
- **Endpoints**: Signup, OTP verification, profile completion
- **Status**: Primary authentication method

### Events Router (`api/routers/events.py`)
- **Purpose**: Event management and discovery
- **Endpoints**: List, create, update, delete events; venue management
- **Features**: Filtering, pagination, search, location-based queries

### Host Leads Router (`api/routers/hosts.py`)
- **Purpose**: Host lead submission and management
- **Endpoints**: Become a host, host leads management
- **Features**: WhatsApp notifications

### Users Router (`api/routers/users.py`)
- **Purpose**: User management endpoints
- **Endpoints**: User profiles, preferences, management

### Health Check (`api/health.py`)
- **Purpose**: System health monitoring
- **Endpoints**: Service status, database connectivity, Redis status

## API Features
- **Async Support**: Full async/await support for high performance
- **Automatic Documentation**: Swagger UI at `/api/docs`
- **Request Validation**: Pydantic-based request/response validation
- **Error Handling**: Comprehensive error handling and responses
- **Rate Limiting**: Built-in rate limiting for API protection
- **SDK Generation**: OpenAPI 3.0 spec for auto-generating client SDKs

## Authentication Flow
1. **Phone Authentication**: Primary authentication via phone + OTP
2. **JWT Tokens**: Secure token-based session management (30-day expiry)
3. **Token Refresh**: Re-authenticate to get new token
4. **Profile Completion**: Complete profile after initial signup

## SDK Generation

The API follows OpenAPI 3.0 specification, making it easy to generate type-safe client SDKs for:
- **iOS (Swift 5+)**: Using `openapi-generator` with `swift5` generator
- **Android (Kotlin)**: Using `openapi-generator` with `kotlin` generator
- **Android (Java)**: Using `openapi-generator` with `java` generator
- **Other platforms**: TypeScript, Python, Dart, etc.

**Quick Start:**
```bash
# Generate iOS SDK
openapi-generator generate \
  -i https://loopinbackend-g17e.onrender.com/api/openapi.json \
  -g swift5 \
  -o ./generated-ios-sdk

# Generate Android SDK (Kotlin)
openapi-generator generate \
  -i https://loopinbackend-g17e.onrender.com/api/openapi.json \
  -g kotlin \
  -o ./generated-android-sdk
```

For detailed SDK generation and integration instructions, see the **[SDK Integration Guide](./SDK_INTEGRATION_GUIDE.md)**.

## Integration Points
- **Django Models**: Direct integration with Django ORM
- **Users Module**: Phone authentication and user management
- **Events Module**: Event management and discovery
- **Attendances Module**: Event attendance and requests
- **All Modules**: API access to all platform features
- **Audit Module**: API request/response logging

## Example Workflows

### Signup Flow
1. **Send OTP**: `POST /api/auth/signup` with phone number
2. **Verify OTP**: `POST /api/auth/verify-otp` with phone number and OTP code
3. **Complete Profile**: `POST /api/auth/complete-profile` (if `needs_profile_completion: true`)

### Event Discovery
1. **List Events**: `GET /api/events` with filters (status, location, interests, etc.)
2. **Get Event Details**: `GET /api/events/{id}`
3. **Create Event**: `POST /api/events` (authenticated hosts only)

### Location-Based Queries
- Filter events by venue coordinates
- Client-side filtering for nearby events using Haversine formula

See the **[SDK Integration Guide](./SDK_INTEGRATION_GUIDE.md)** for complete code examples.
