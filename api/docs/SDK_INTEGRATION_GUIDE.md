# Loopin Backend API - SDK Integration Guide

**Version:** 1.0.0  
**Last Updated:** November 2025  
**Base URL:** `https://loopinbackend-g17e.onrender.com/api`

## 📚 Table of Contents

1. [Overview](#overview)
2. [OpenAPI Specification](#openapi-specification)
3. [SDK Generation Setup](#sdk-generation-setup)
4. [Supported Client SDKs](#supported-client-sdks)
5. [Example Workflows](#example-workflows)
6. [Project-Specific Conventions](#project-specific-conventions)
7. [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

This guide helps frontend developers generate, integrate, and use API client SDKs for the Loopin Backend. The API follows the OpenAPI 3.0 specification, making it easy to generate type-safe client libraries for iOS (Swift), Android (Kotlin/Java), and other platforms.

### Key Features

- **OpenAPI 3.0 Compliant**: Standard specification for easy SDK generation
- **Type-Safe Clients**: Auto-generated models and API clients
- **JWT Authentication**: Secure token-based authentication
- **Comprehensive Documentation**: Inline API documentation and examples
- **Error Handling**: Structured error responses with codes and messages

### API Documentation URLs

- **Interactive Docs (Swagger UI):** `https://loopinbackend-g17e.onrender.com/api/docs`
- **OpenAPI JSON Spec:** `https://loopinbackend-g17e.onrender.com/api/openapi.json`
- **ReDoc Documentation:** `https://loopinbackend-g17e.onrender.com/api/redoc`

---

## 📖 OpenAPI Specification

### Fetching the OpenAPI Specification

The OpenAPI 3.0 specification is available at:

```bash
# Production
https://loopinbackend-g17e.onrender.com/api/openapi.json

# Local Development (if running locally)
http://localhost:8000/api/openapi.json
```

### Download the Spec

**Using curl:**
```bash
# Save to file
curl -o loopin-api-spec.json https://loopinbackend-g17e.onrender.com/api/openapi.json

# View in terminal
curl https://loopinbackend-g17e.onrender.com/api/openapi.json | python3 -m json.tool
```

**Using wget:**
```bash
wget -O loopin-api-spec.json https://loopinbackend-g17e.onrender.com/api/openapi.json
```

**Using browser:**
Simply visit `https://loopinbackend-g17e.onrender.com/api/openapi.json` and save the JSON file.

### Validate the Spec

**Using openapi-generator:**
```bash
# Validate the spec
openapi-generator validate -i loopin-api-spec.json
```

**Using swagger-codegen:**
```bash
# Validate the spec
swagger-codegen validate -i loopin-api-spec.json
```

---

## 🛠️ SDK Generation Setup

### macOS Setup

#### Install OpenAPI Generator

**Using Homebrew (Recommended):**
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install OpenAPI Generator
brew install openapi-generator

# Verify installation
openapi-generator version
```

**Using npm:**
```bash
npm install -g @openapitools/openapi-generator-cli

# Verify installation
openapi-generator-cli version
```

**Manual Installation:**
```bash
# Download latest release
curl -L https://github.com/OpenAPITools/openapi-generator/releases/download/v7.2.0/openapi-generator-cli-7.2.0.jar -o openapi-generator-cli.jar

# Make executable
chmod +x openapi-generator-cli.jar

# Use with Java
java -jar openapi-generator-cli.jar version
```

#### Install Swagger Codegen (Alternative)

```bash
# Install via Homebrew
brew install swagger-codegen

# Verify installation
swagger-codegen version
```

### Windows Setup

#### Install OpenAPI Generator

**Using Chocolatey:**
```powershell
# Install Chocolatey (if not already installed)
# Run PowerShell as Administrator
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# Install OpenAPI Generator
choco install openapi-generator

# Verify installation
openapi-generator version
```

**Using npm:**
```powershell
npm install -g @openapitools/openapi-generator-cli

# Verify installation
openapi-generator-cli version
```

**Manual Installation:**
```powershell
# Download latest release
Invoke-WebRequest -Uri "https://github.com/OpenAPITools/openapi-generator/releases/download/v7.2.0/openapi-generator-cli-7.2.0.jar" -OutFile "openapi-generator-cli.jar"

# Use with Java (requires Java 8+)
java -jar openapi-generator-cli.jar version
```

#### Install Java (Required)

```powershell
# Using Chocolatey
choco install openjdk

# Or download from: https://adoptium.net/
```

---

## 📱 Supported Client SDKs

### iOS (Swift 5+)

**Generate Swift SDK:**
```bash
# Using openapi-generator
openapi-generator generate \
  -i https://loopinbackend-g17e.onrender.com/api/openapi.json \
  -g swift5 \
  -o ./generated-ios-sdk \
  --additional-properties=projectName=LoopinAPI,responseAs=AsyncAwait

# Or from local file
openapi-generator generate \
  -i loopin-api-spec.json \
  -g swift5 \
  -o ./generated-ios-sdk \
  --additional-properties=projectName=LoopinAPI,responseAs=AsyncAwait
```

**Features:**
- Async/Await support
- Codable models
- URLSession-based networking
- Type-safe request/response handling

**Integration:**
```swift
// Add to your Xcode project
// 1. Drag the generated folder into Xcode
// 2. Add to target dependencies
// 3. Import the module

import LoopinAPI

// Initialize API client
let apiClient = LoopinAPI.APIClient(
    baseURL: URL(string: "https://loopinbackend-g17e.onrender.com/api")!
)
```

### Android (Kotlin)

**Generate Kotlin SDK:**
```bash
# Using openapi-generator
openapi-generator generate \
  -i https://loopinbackend-g17e.onrender.com/api/openapi.json \
  -g kotlin \
  -o ./generated-android-sdk \
  --additional-properties=library=ktor,serializationLibrary=kotlinx_serialization

# Or with Retrofit (alternative)
openapi-generator generate \
  -i https://loopinbackend-g17e.onrender.com/api/openapi.json \
  -g kotlin \
  -o ./generated-android-sdk \
  --additional-properties=library=jvm-retrofit2,serializationLibrary=gson
```

**Features:**
- Kotlin coroutines support
- Kotlinx serialization or Gson
- Ktor or Retrofit2 networking
- Type-safe models

**Integration:**
```kotlin
// Add to build.gradle.kts
dependencies {
    implementation(project(":generated-android-sdk"))
    // Add required dependencies (Ktor/Retrofit, serialization, etc.)
}

// Initialize API client
val apiClient = LoopinAPI.APIClient(
    baseUrl = "https://loopinbackend-g17e.onrender.com/api"
)
```

### Android (Java)

**Generate Java SDK:**
```bash
# Using openapi-generator
openapi-generator generate \
  -i https://loopinbackend-g17e.onrender.com/api/openapi.json \
  -g java \
  -o ./generated-java-sdk \
  --additional-properties=library=retrofit2,serializationLibrary=gson

# Or using swagger-codegen
swagger-codegen generate \
  -i https://loopinbackend-g17e.onrender.com/api/openapi.json \
  -l java \
  -o ./generated-java-sdk \
  --library retrofit2
```

**Features:**
- Retrofit2 networking
- Gson serialization
- RxJava or Callback support
- Type-safe models

**Integration:**
```java
// Add to build.gradle
dependencies {
    implementation project(':generated-java-sdk')
    // Add Retrofit2, Gson, OkHttp dependencies
}

// Initialize API client
LoopinAPI apiClient = new LoopinAPI.Builder()
    .baseUrl("https://loopinbackend-g17e.onrender.com/api")
    .build();
```

### Other Supported Languages

**TypeScript/JavaScript:**
```bash
openapi-generator generate \
  -i https://loopinbackend-g17e.onrender.com/api/openapi.json \
  -g typescript-axios \
  -o ./generated-ts-sdk
```

**Python:**
```bash
openapi-generator generate \
  -i https://loopinbackend-g17e.onrender.com/api/openapi.json \
  -g python \
  -o ./generated-python-sdk
```

**Dart (Flutter):**
```bash
openapi-generator generate \
  -i https://loopinbackend-g17e.onrender.com/api/openapi.json \
  -g dart \
  -o ./generated-dart-sdk
```

---

## 🚀 Example Workflows

### 1. Signup Flow

The signup flow consists of two API calls:
1. **Send OTP** - Request OTP code
2. **Verify OTP** - Verify code and get JWT token

#### Step 1: Send OTP

**Endpoint:** `POST /api/auth/signup`

**Request:**
```json
{
  "phone_number": "+1234567890"
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP sent successfully to your phone number",
  "data": {
    "phone_number": "+1234567890",
    "user_status": "new",
    "otp_sent": true
  },
  "token": null
}
```

**Swift Example:**
```swift
import LoopinAPI

func sendOTP(phoneNumber: String) async throws {
    let request = SignupRequest(phoneNumber: phoneNumber)
    let response = try await apiClient.authAPI.signup(signupRequest: request)
    
    if response.success {
        print("OTP sent successfully")
        // Navigate to OTP verification screen
    } else {
        throw APIError.signupFailed(response.message ?? "Unknown error")
    }
}
```

**Kotlin Example:**
```kotlin
import com.loopin.api.*

suspend fun sendOTP(phoneNumber: String): Result<SignupResponse> {
    return try {
        val request = SignupRequest(phoneNumber = phoneNumber)
        val response = apiClient.authAPI.signup(request)
        if (response.success == true) {
            Result.success(response)
        } else {
            Result.failure(APIException(response.message ?: "Unknown error"))
        }
    } catch (e: Exception) {
        Result.failure(e)
    }
}
```

**Java Example:**
```java
import com.loopin.api.*;

public void sendOTP(String phoneNumber) {
    SignupRequest request = new SignupRequest()
        .phoneNumber(phoneNumber);
    
    apiClient.getAuthAPI().signup(request)
        .enqueue(new Callback<SignupResponse>() {
            @Override
            public void onResponse(Call<SignupResponse> call, Response<SignupResponse> response) {
                if (response.isSuccessful() && response.body().getSuccess()) {
                    // Navigate to OTP verification screen
                }
            }
            
            @Override
            public void onFailure(Call<SignupResponse> call, Throwable t) {
                // Handle error
            }
        });
}
```

#### Step 2: Verify OTP

**Endpoint:** `POST /api/auth/verify-otp`

**Request:**
```json
{
  "phone_number": "+1234567890",
  "otp_code": "1234"
}
```

**Response:**
```json
{
  "success": true,
  "message": "OTP verified successfully. Please complete your profile to continue.",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "data": {
    "user_id": 123,
    "phone_number": "+1234567890",
    "needs_profile_completion": true,
    "is_verified": true
  }
}
```

**Swift Example:**
```swift
func verifyOTP(phoneNumber: String, otpCode: String) async throws -> String {
    let request = VerifyOTPRequest(
        phoneNumber: phoneNumber,
        otpCode: otpCode
    )
    let response = try await apiClient.authAPI.verifyOTP(verifyOTPRequest: request)
    
    guard response.success, let token = response.token else {
        throw APIError.verificationFailed(response.message ?? "Unknown error")
    }
    
    // Save token securely
    KeychainHelper.save(token: token, for: "auth_token")
    
    // Check if profile needs completion
    if response.data?.needsProfileCompletion == true {
        // Navigate to profile completion screen
    } else {
        // Navigate to home screen
    }
    
    return token
}
```

**Kotlin Example:**
```kotlin
suspend fun verifyOTP(phoneNumber: String, otpCode: String): Result<String> {
    return try {
        val request = VerifyOTPRequest(
            phoneNumber = phoneNumber,
            otpCode = otpCode
        )
        val response = apiClient.authAPI.verifyOTP(request)
        
        if (response.success == true && response.token != null) {
            // Save token securely
            TokenManager.saveToken(response.token!!)
            
            // Check profile completion
            if (response.data?.needsProfileCompletion == true) {
                // Navigate to profile completion
            } else {
                // Navigate to home
            }
            
            Result.success(response.token!!)
        } else {
            Result.failure(APIException(response.message ?: "Unknown error"))
        }
    } catch (e: Exception) {
        Result.failure(e)
    }
}
```

**Java Example:**
```java
public void verifyOTP(String phoneNumber, String otpCode) {
    VerifyOTPRequest request = new VerifyOTPRequest()
        .phoneNumber(phoneNumber)
        .otpCode(otpCode);
    
    apiClient.getAuthAPI().verifyOTP(request)
        .enqueue(new Callback<VerifyOTPResponse>() {
            @Override
            public void onResponse(Call<VerifyOTPResponse> call, Response<VerifyOTPResponse> response) {
                if (response.isSuccessful() && response.body().getSuccess()) {
                    String token = response.body().getToken();
                    // Save token securely
                    TokenManager.saveToken(token);
                    
                    // Check profile completion
                    if (response.body().getData().getNeedsProfileCompletion()) {
                        // Navigate to profile completion
                    } else {
                        // Navigate to home
                    }
                }
            }
            
            @Override
            public void onFailure(Call<VerifyOTPResponse> call, Throwable t) {
                // Handle error
            }
        });
}
```

### 2. Event-Related APIs

#### List Events

**Endpoint:** `GET /api/events`

**Query Parameters:**
- `offset` (int, default: 0): Pagination offset
- `limit` (int, default: 20, max: 100): Results per page
- `host_id` (int, optional): Filter by host user ID
- `status` (string, optional): Filter by status (draft, published, cancelled, completed, postponed)
- `is_public` (bool, optional): Filter by public/private events
- `is_paid` (bool, optional): Filter by paid/free events
- `event_interest_id` (int, optional): Filter by event interest ID
- `search` (string, optional): Search in title and description
- `start_date` (datetime, optional): Filter events starting after this date
- `end_date` (datetime, optional): Filter events ending before this date

**Response:**
```json
{
  "total": 50,
  "offset": 0,
  "limit": 20,
  "data": [
    {
      "id": 1,
      "title": "Summer Music Festival",
      "description": "Annual summer music festival",
      "start_time": "2025-07-15T18:00:00Z",
      "end_time": "2025-07-15T23:00:00Z",
      "status": "published",
      "is_public": true,
      "is_paid": true,
      "max_capacity": 500,
      "going_count": 123,
      "cover_images": ["https://example.com/image1.jpg"],
      "host": {
        "id": 1,
        "username": "john_doe",
        "email": "john@example.com"
      },
      "venue": {
        "id": 1,
        "name": "Central Park",
        "address": "123 Main St",
        "city": "New York",
        "latitude": 40.785091,
        "longitude": -73.968285
      }
    }
  ]
}
```

**Swift Example:**
```swift
func fetchEvents(offset: Int = 0, limit: Int = 20) async throws -> [Event] {
    // Set authorization header
    apiClient.requestBuilderFactory = RequestBuilderFactory(
        defaultHeaders: [
            "Authorization": "Bearer \(TokenManager.getToken() ?? "")"
        ]
    )
    
    let response = try await apiClient.eventsAPI.listEvents(
        offset: offset,
        limit: limit,
        isPublic: true,
        status: "published"
    )
    
    return response.data ?? []
}
```

**Kotlin Example:**
```kotlin
suspend fun fetchEvents(offset: Int = 0, limit: Int = 20): List<Event> {
    // Set authorization header
    apiClient.setBearerToken(TokenManager.getToken() ?: "")
    
    val response = apiClient.eventsAPI.listEvents(
        offset = offset,
        limit = limit,
        isPublic = true,
        status = "published"
    )
    
    return response.data ?: emptyList()
}
```

**Java Example:**
```java
public void fetchEvents(int offset, int limit) {
    // Set authorization header
    String token = TokenManager.getToken();
    apiClient.setBearerToken(token);
    
    apiClient.getEventsAPI().listEvents(offset, limit, true, "published")
        .enqueue(new Callback<EventListResponse>() {
            @Override
            public void onResponse(Call<EventListResponse> call, Response<EventListResponse> response) {
                if (response.isSuccessful()) {
                    List<Event> events = response.body().getData();
                    // Update UI with events
                }
            }
            
            @Override
            public void onFailure(Call<EventListResponse> call, Throwable t) {
                // Handle error
            }
        });
}
```

#### Get Event Details

**Endpoint:** `GET /api/events/{event_id}`

**Swift Example:**
```swift
func fetchEventDetails(eventId: Int) async throws -> Event {
    let event = try await apiClient.eventsAPI.getEvent(eventId: eventId)
    return event
}
```

**Kotlin Example:**
```kotlin
suspend fun fetchEventDetails(eventId: Int): Event {
    return apiClient.eventsAPI.getEvent(eventId)
}
```

#### Create Event

**Endpoint:** `POST /api/events`

**Request:**
```json
{
  "title": "New Event",
  "description": "Event description",
  "start_time": "2025-12-15T18:00:00Z",
  "end_time": "2025-12-15T21:00:00Z",
  "is_public": true,
  "is_paid": false,
  "max_capacity": 100,
  "venue_id": 1,
  "event_interests": [1, 2, 3]
}
```

**Swift Example:**
```swift
func createEvent(eventData: EventCreate) async throws -> Event {
    let event = try await apiClient.eventsAPI.createEvent(eventCreate: eventData)
    return event
}
```

**Kotlin Example:**
```kotlin
suspend fun createEvent(eventData: EventCreate): Event {
    return apiClient.eventsAPI.createEvent(eventData)
}
```

### 3. Location-Based Query API

**Endpoint:** `GET /api/events`

The events list endpoint supports location-based filtering through venue coordinates. While there isn't a dedicated "nearby events" endpoint, you can filter events by venue coordinates or use client-side filtering.

**Approach 1: Filter by Venue ID**
```swift
// If you know the venue ID
let events = try await apiClient.eventsAPI.listEvents(venueId: venueId)
```

**Approach 2: Fetch All Events and Filter Client-Side**
```swift
func fetchNearbyEvents(
    latitude: Double,
    longitude: Double,
    radiusKm: Double = 10.0
) async throws -> [Event] {
    // Fetch all public events
    let response = try await apiClient.eventsAPI.listEvents(
        isPublic: true,
        limit: 100
    )
    
    // Filter by distance
    let nearbyEvents = response.data?.filter { event in
        guard let venue = event.venue,
              let lat = venue.latitude,
              let lon = venue.longitude else {
            return false
        }
        
        let distance = calculateDistance(
            lat1: latitude,
            lon1: longitude,
            lat2: lat,
            lon2: lon
        )
        
        return distance <= radiusKm
    }
    
    return nearbyEvents ?? []
}

func calculateDistance(lat1: Double, lon1: Double, lat2: Double, lon2: Double) -> Double {
    // Haversine formula
    let R = 6371.0 // Earth's radius in kilometers
    let dLat = (lat2 - lat1) * .pi / 180
    let dLon = (lon2 - lon1) * .pi / 180
    let a = sin(dLat/2) * sin(dLat/2) +
            cos(lat1 * .pi / 180) * cos(lat2 * .pi / 180) *
            sin(dLon/2) * sin(dLon/2)
    let c = 2 * atan2(sqrt(a), sqrt(1-a))
    return R * c
}
```

**Kotlin Example:**
```kotlin
suspend fun fetchNearbyEvents(
    latitude: Double,
    longitude: Double,
    radiusKm: Double = 10.0
): List<Event> {
    val response = apiClient.eventsAPI.listEvents(
        isPublic = true,
        limit = 100
    )
    
    return response.data?.filter { event ->
        val venue = event.venue
        if (venue?.latitude == null || venue.longitude == null) {
            return@filter false
        }
        
        val distance = calculateDistance(
            latitude, longitude,
            venue.latitude!!, venue.longitude!!
        )
        
        distance <= radiusKm
    } ?: emptyList()
}

fun calculateDistance(lat1: Double, lon1: Double, lat2: Double, lon2: Double): Double {
    val R = 6371.0 // Earth's radius in kilometers
    val dLat = Math.toRadians(lat2 - lat1)
    val dLon = Math.toRadians(lon2 - lon1)
    val a = sin(dLat / 2) * sin(dLat / 2) +
            cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) *
            sin(dLon / 2) * sin(dLon / 2)
    val c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c
}
```

---

## 🔧 Project-Specific Conventions

### Authentication

**JWT Token Format:**
- **Header:** `Authorization: Bearer <token>`
- **Token Expiry:** 30 days from issuance
- **Token Storage:** Store securely (Keychain on iOS, EncryptedSharedPreferences on Android)

**Setting Authorization Header:**

**Swift:**
```swift
apiClient.requestBuilderFactory = RequestBuilderFactory(
    defaultHeaders: [
        "Authorization": "Bearer \(token)"
    ]
)
```

**Kotlin:**
```kotlin
apiClient.setBearerToken(token)
```

**Java:**
```java
apiClient.setBearerToken(token);
```

### Error Handling

**Error Response Format:**
```json
{
  "success": false,
  "error": "User-friendly error message",
  "error_code": "ERROR_CODE",
  "details": {
    "field": "additional error details"
  }
}
```

**Common Error Codes:**
- `VALIDATION_ERROR` (400): Request validation failed
- `AUTHENTICATION_ERROR` (401): Invalid or missing token
- `AUTHORIZATION_ERROR` (403): Insufficient permissions
- `NOT_FOUND` (404): Resource not found
- `CONFLICT_ERROR` (409): Resource conflict (e.g., duplicate entry)
- `RATE_LIMIT_ERROR` (429): Too many requests
- `INTERNAL_SERVER_ERROR` (500): Server error

**Swift Error Handling:**
```swift
do {
    let response = try await apiClient.eventsAPI.getEvent(eventId: eventId)
    // Handle success
} catch let error as APIError {
    switch error {
    case .unauthorized:
        // Refresh token or redirect to login
    case .notFound:
        // Show "Event not found" message
    case .validationError(let message):
        // Show validation error
    default:
        // Show generic error
    }
}
```

**Kotlin Error Handling:**
```kotlin
try {
    val event = apiClient.eventsAPI.getEvent(eventId)
    // Handle success
} catch (e: APIException) {
    when (e.code) {
        "AUTHENTICATION_ERROR" -> {
            // Refresh token or redirect to login
        }
        "NOT_FOUND" -> {
            // Show "Event not found" message
        }
        else -> {
            // Show generic error
        }
    }
}
```

### Pagination

**Standard Pagination:**
- **Offset-based:** Use `offset` and `limit` parameters
- **Default Limit:** 20 items per page
- **Maximum Limit:** 100 items per page

**Response Format:**
```json
{
  "total": 150,
  "offset": 0,
  "limit": 20,
  "data": [...]
}
```

**Implementing Pagination:**

**Swift:**
```swift
func loadMoreEvents(currentCount: Int) async throws -> [Event] {
    let response = try await apiClient.eventsAPI.listEvents(
        offset: currentCount,
        limit: 20
    )
    return response.data ?? []
}
```

**Kotlin:**
```kotlin
suspend fun loadMoreEvents(currentCount: Int): List<Event> {
    val response = apiClient.eventsAPI.listEvents(
        offset = currentCount,
        limit = 20
    )
    return response.data ?: emptyList()
}
```

### Date/Time Format

**ISO 8601 Format:**
- **Format:** `YYYY-MM-DDTHH:mm:ssZ`
- **Example:** `2025-12-15T18:00:00Z`
- **Timezone:** UTC (Z suffix)

**Swift Date Handling:**
```swift
let formatter = ISO8601DateFormatter()
formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]

let date = formatter.date(from: "2025-12-15T18:00:00.000Z")
let dateString = formatter.string(from: Date())
```

**Kotlin Date Handling:**
```kotlin
import java.time.Instant
import java.time.format.DateTimeFormatter

val formatter = DateTimeFormatter.ISO_INSTANT
val date = Instant.parse("2025-12-15T18:00:00.000Z")
val dateString = formatter.format(Instant.now())
```

### Phone Number Format

**E.164 Format:**
- **Format:** `+<country_code><number>`
- **Example:** `+1234567890`, `+916205829376`
- **Required:** Must include country code with `+` prefix

**Validation:**
- Minimum length: 10 characters (including country code)
- Maximum length: 20 characters
- Must start with `+`

### Image URLs

**Format:**
- **Protocol:** HTTPS only
- **Format:** Full URL to image
- **Example:** `https://example.com/image.jpg`

**Validation:**
- Must be valid HTTPS URL
- Images should be accessible publicly
- Recommended: Use CDN or cloud storage (S3, Cloudinary, etc.)

---

## 🔍 Troubleshooting

### Common Issues

#### 1. SDK Generation Fails

**Problem:** OpenAPI generator fails with validation errors

**Solution:**
```bash
# Validate the spec first
openapi-generator validate -i https://loopinbackend-g17e.onrender.com/api/openapi.json

# If validation fails, check the error messages
# Common issues:
# - Invalid schema definitions
# - Missing required fields
# - Unsupported features
```

#### 2. Authentication Errors

**Problem:** Getting 401 Unauthorized errors

**Solution:**
- Verify token is set correctly in authorization header
- Check token expiry (tokens expire after 30 days)
- Ensure token format: `Bearer <token>`
- Refresh token if expired

#### 3. Model Mismatches

**Problem:** Generated models don't match API responses

**Solution:**
- Regenerate SDK after API updates
- Check OpenAPI spec version
- Verify model definitions in spec

#### 4. Network Timeouts

**Problem:** Requests timing out

**Solution:**
- Increase timeout values in SDK configuration
- Check network connectivity
- Verify API server is accessible

**Swift:**
```swift
let configuration = URLSessionConfiguration.default
configuration.timeoutIntervalForRequest = 30.0
configuration.timeoutIntervalForResource = 60.0
```

**Kotlin:**
```kotlin
val client = HttpClient(CIO) {
    engine {
        requestTimeout = 30000 // 30 seconds
    }
}
```

### Getting Help

**Resources:**
- **API Documentation:** `https://loopinbackend-g17e.onrender.com/api/docs`
- **OpenAPI Spec:** `https://loopinbackend-g17e.onrender.com/api/openapi.json`
- **OpenAPI Generator Docs:** https://openapi-generator.tech/

**Support:**
- Check API status: `https://loopinbackend-g17e.onrender.com/api/health`
- Review error messages in API responses
- Contact backend team for API-specific issues

---

## 📝 Quick Reference

### Base URL
```
https://loopinbackend-g17e.onrender.com/api
```

### OpenAPI Spec URL
```
https://loopinbackend-g17e.onrender.com/api/openapi.json
```

### Key Endpoints
- **Signup:** `POST /api/auth/signup`
- **Verify OTP:** `POST /api/auth/verify-otp`
- **List Events:** `GET /api/events`
- **Get Event:** `GET /api/events/{id}`
- **Create Event:** `POST /api/events`

### SDK Generation Commands

**iOS (Swift):**
```bash
openapi-generator generate \
  -i https://loopinbackend-g17e.onrender.com/api/openapi.json \
  -g swift5 \
  -o ./generated-ios-sdk
```

**Android (Kotlin):**
```bash
openapi-generator generate \
  -i https://loopinbackend-g17e.onrender.com/api/openapi.json \
  -g kotlin \
  -o ./generated-android-sdk
```

**Android (Java):**
```bash
openapi-generator generate \
  -i https://loopinbackend-g17e.onrender.com/api/openapi.json \
  -g java \
  -o ./generated-java-sdk
```

---

**Last Updated:** November 2025  
**API Version:** 1.0.0  
**Maintained by:** Loopin Backend Team

