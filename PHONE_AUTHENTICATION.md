# 📱 Phone Authentication System Documentation

## 📋 Table of Contents
- [Quick Reference](#quick-reference)
- [Overview](#overview)
- [Unified Authentication Flow](#unified-authentication-flow)
- [API Endpoints](#api-endpoints)
- [Database Models](#database-models)
- [Configuration](#configuration)
- [Testing](#testing)
- [Troubleshooting](#troubleshooting)
- [Deployment](#deployment)

## 🚀 Quick Reference

### 🔗 Essential URLs
- **Production API**: https://loopinbackend-g17e.onrender.com/api/
- **API Docs**: https://loopinbackend-g17e.onrender.com/api/docs
- **Django Admin**: https://loopinbackend-g17e.onrender.com/django/admin/
- **Local Dev**: http://localhost:8000/api/

### 📱 Unified Authentication Flow (Mobile App)

#### Single Flow for Both New and Existing Users
```bash
# Step 1: Send OTP (works for both signup and login)
curl -X POST "https://loopinbackend-g17e.onrender.com/api/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890"}'

# Step 2: Verify OTP (creates account if new, logs in if existing)
curl -X POST "https://loopinbackend-g17e.onrender.com/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890", "otp_code": "1234"}'

# Response includes: token + needs_profile_completion flag

# Step 3a: If needs_profile_completion = true, complete profile
curl -X POST "https://loopinbackend-g17e.onrender.com/api/auth/complete-profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "phone_number": "+1234567890",
    "name": "John Doe",
    "birth_date": "1995-01-01",
    "gender": "male",
    "event_interests": [1, 2, 3],
    "profile_pictures": ["https://example.com/pic1.jpg"],
    "bio": "Love music and events",
    "location": "New York, USA"
  }'

# Step 3b: If needs_profile_completion = false, user is logged in ✅
```

#### Get Event Interests (for profile completion)
```bash
curl -X GET "https://loopinbackend-g17e.onrender.com/api/auth/event-interests"
```

### ⚙️ Configuration

#### Production Mode (Current on Render)
```bash
TWILIO_TEST_MODE=false  # Real SMS delivery
DEBUG=False             # Production settings
```

#### Test Mode (Local Development)
```bash
TWILIO_TEST_MODE=true   # OTP visible in logs
DEBUG=True              # Development settings
```

### 🔧 Quick Debug Commands

#### Check OTP (Local Development)
```bash
docker-compose logs web | grep "OTP" | tail -5
```

#### Test Complete Flow
```bash
# 1. Send OTP
curl -X POST "http://localhost:8000/api/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890"}'

# 2. Check logs for OTP
docker-compose logs web | grep "TEST MODE: OTP"

# 3. Verify OTP
curl -X POST "http://localhost:8000/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890", "otp_code": "XXXX"}'
```

---

## 🎯 Overview

The LoopinBackend implements a **unified phone number-based authentication system** that combines signup and login into a single seamless flow. This approach simplifies the mobile app integration and improves user experience.

### Key Features
- ✅ **Unified Entry Point**: Single `/signup` endpoint for all users
- ✅ **Automatic User Detection**: Backend identifies new vs existing users
- ✅ **4-digit SMS OTP**: Sent via Twilio for verification
- ✅ **JWT Token Authentication**: Secure, stateless sessions
- ✅ **Profile Completion Flag**: Tells app if profile needs completing
- ✅ **Comprehensive Validation**: All fields validated with clear error messages
- ✅ **Lead Tracking**: Unverified OTP requests stored for business analytics
- ✅ **Event Interests**: Dynamic interest categories (12 available)
- ✅ **Profile Pictures**: 1-6 images required with URL validation
- ✅ **Age Verification**: 16+ requirement
- ✅ **Gender Selection**: male/female/other validation
- ✅ **100% Error Handling**: Every edge case covered

### What's Different from Traditional Auth?
| Traditional | Unified (LoopinBackend) |
|-------------|-------------------------|
| Separate /signup and /login endpoints | Single /signup endpoint |
| App decides which flow to use | Backend auto-detects user status |
| Complex state management in app | Simple 3-step flow |
| Confusing for users | Seamless user experience |

---

## 🔄 Unified Authentication Flow

### Complete Flow Architecture

```mermaid
graph TD
    A[Mobile App] --> B[User enters phone number]
    B --> C[POST /api/auth/signup]
    C --> D{User exists in DB?}
    
    D -->|No - New User| E[Generate 4-digit OTP]
    D -->|Yes - Existing User| F{Profile complete?}
    
    F -->|Yes - Complete| E
    F -->|No - Incomplete| E
    
    E --> G[Store OTP in PhoneOTP table]
    G --> H[Mark is_verified = false]
    H --> I[Send SMS via Twilio]
    I --> J{SMS sent successfully?}
    
    J -->|No| K[Return: Failed to send OTP]
    J -->|Yes| L[Return: OTP sent successfully]
    
    L --> M[User receives OTP via SMS]
    M --> N[User enters OTP in app]
    N --> O[POST /api/auth/verify-otp]
    
    O --> P{OTP valid?}
    P -->|No - Wrong OTP| Q[Increment attempts]
    P -->|No - Expired| R[Return: OTP expired]
    P -->|No - Max attempts| S[Return: Too many attempts]
    P -->|Yes - Valid OTP| T[Mark is_verified = true]
    
    Q --> U{Attempts < 3?}
    U -->|Yes| V[Return: Invalid OTP X attempts remaining]
    U -->|No| S
    
    T --> W{User account exists?}
    W -->|No| X[Create new User account]
    W -->|Yes| Y[Get existing User account]
    
    X --> Z[Create UserProfile]
    Y --> AA{UserProfile exists?}
    
    AA -->|No| Z
    AA -->|Yes| AB[Get existing UserProfile]
    
    Z --> AC[Set is_verified = true]
    AB --> AC
    
    AC --> AD[Generate JWT token]
    AD --> AE{Profile complete?}
    
    AE -->|Check: name AND profile_pictures| AF{Has both?}
    AF -->|No| AG[needs_profile_completion = true]
    AF -->|Yes| AH[needs_profile_completion = false]
    
    AG --> AI[Return: Token + Please complete profile]
    AH --> AJ[Return: Token + Logged in]
    
    AI --> AK[Mobile App: Show profile completion screen]
    AJ --> AL[Mobile App: Navigate to home screen]
    
    AK --> AM[GET /api/auth/event-interests]
    AM --> AN[User fills profile form]
    AN --> AO[POST /api/auth/complete-profile]
    
    AO --> AP{All validations pass?}
    AP -->|No| AQ[Return: Validation errors]
    AP -->|Yes| AR[Save profile data]
    
    AR --> AS[Set event_interests ManyToMany]
    AS --> AT[Return: Profile completed]
    AT --> AL
    
    AQ --> AN
    
    style H fill:#ffebee
    style K fill:#ffebee
    style R fill:#ffebee
    style S fill:#ffebee
    style V fill:#fff3e0
    style T fill:#e8f5e9
    style AC fill:#e8f5e9
    style AG fill:#fff3e0
    style AH fill:#e8f5e9
    style AT fill:#e8f5e9
    style G fill:#e1f5fe
```

### Detailed Step-by-Step Flow

#### Step 1: Send OTP (Universal Entry Point)

```mermaid
sequenceDiagram
    participant User
    participant Mobile App
    participant API
    participant Database
    participant Twilio
    
    User->>Mobile App: Enters phone number
    Mobile App->>API: POST /signup {phone_number}
    
    API->>Database: Check if User exists
    alt User is New
        Database-->>API: No user found
        Note over API: user_status = "new"
    else User Exists (Complete Profile)
        Database-->>API: User found with complete profile
        Note over API: user_status = "existing"
    else User Exists (Incomplete Profile)
        Database-->>API: User found with incomplete profile
        Note over API: user_status = "existing"
    end
    
    API->>Database: Create/Update PhoneOTP record
    Database->>API: OTP record created
    Note over Database: is_verified = false
    
    API->>API: Generate 4-digit OTP
    API->>Twilio: Send SMS with OTP
    
    alt SMS Success
        Twilio-->>API: Message sent
        API-->>Mobile App: {success: true, otp_sent: true}
        Mobile App-->>User: OTP sent! Check your phone
    else SMS Failure
        Twilio-->>API: Send failed
        API-->>Mobile App: {success: false, message: "Failed to send OTP"}
        Mobile App-->>User: Error: Please try again
    end
```

**What Happens:**
1. User provides phone number
2. Backend checks if user exists
3. Generates 4-digit OTP regardless of user status
4. Stores OTP in database with `is_verified = false` (Lead tracking!)
5. Sends SMS via Twilio
6. Returns success/failure

**Response for New User:**
```json
{
  "success": true,
  "message": "OTP sent successfully to your phone number. Please verify to complete signup.",
  "data": {
    "phone_number": "+1234567890",
    "user_status": "new",
    "otp_sent": true
  }
}
```

**Response for Existing User:**
```json
{
  "success": true,
  "message": "OTP sent successfully to your phone number. Please verify to login.",
  "data": {
    "phone_number": "+1234567890",
    "user_status": "existing",
    "otp_sent": true
  }
}
```

#### Step 2: Verify OTP (Creates Account or Logs In)

```mermaid
sequenceDiagram
    participant User
    participant Mobile App
    participant API
    participant Database
    
    User->>Mobile App: Enters 4-digit OTP
    Mobile App->>API: POST /verify-otp {phone, otp_code}
    
    API->>Database: Get PhoneOTP record
    
    alt OTP Not Found
        Database-->>API: No record
        API-->>Mobile App: {success: false, message: "No OTP found"}
    else OTP Found
        Database-->>API: OTP record
        
        API->>API: Verify OTP
        
        alt OTP Expired
            API-->>Mobile App: {success: false, message: "OTP has expired"}
        else Too Many Attempts
            API-->>Mobile App: {success: false, message: "Too many attempts"}
        else Wrong OTP
            API->>Database: Increment attempts
            API-->>Mobile App: {success: false, message: "Invalid OTP. X attempts remaining"}
        else Correct OTP
            API->>Database: Set is_verified = true
            
            API->>Database: Check if User exists
            
            alt New User
                API->>Database: Create User account
                API->>Database: Create UserProfile
                Note over Database: New signup!
            else Existing User
                API->>Database: Get User & Profile
                Note over Database: Login!
            end
            
            API->>API: Generate JWT token
            API->>API: Check profile completion
            
            alt Profile Incomplete
                Note over API: name OR profile_pictures missing
                API-->>Mobile App: {success: true, needs_profile_completion: true, token}
                Mobile App-->>User: Please complete your profile
            else Profile Complete
                Note over API: name AND profile_pictures exist
                API-->>Mobile App: {success: true, needs_profile_completion: false, token}
                Mobile App-->>User: Welcome back! (Navigate to home)
            end
        end
    end
```

**What Happens:**
1. User enters OTP received via SMS
2. Backend validates OTP (checks expiry, attempts, correctness)
3. If valid:
   - For new users: Creates User account + UserProfile
   - For existing users: Authenticates user
4. Generates JWT token
5. Checks if profile is complete
6. Returns token + `needs_profile_completion` flag

**Success Response (Profile Incomplete):**
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

**Success Response (Profile Complete):**
```json
{
  "success": true,
  "message": "OTP verified successfully. You are logged in.",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "data": {
    "user_id": 123,
    "phone_number": "+1234567890",
    "needs_profile_completion": false,
    "is_verified": true
  }
}
```

#### Step 3: Complete Profile (Only if needed)

```mermaid
sequenceDiagram
    participant User
    participant Mobile App
    participant API
    participant Database
    
    Note over Mobile App: Only if needs_profile_completion = true
    
    Mobile App->>API: GET /event-interests
    API->>Database: Get active EventInterests
    Database-->>API: List of interests
    API-->>Mobile App: {data: [...interests]}
    Mobile App-->>User: Show profile form with interests
    
    User->>Mobile App: Fills profile form
    Note over User: Name, DOB, Gender, Interests, Pictures
    
    Mobile App->>API: POST /complete-profile + JWT token
    
    API->>API: Verify JWT token
    
    alt Token Invalid/Expired
        API-->>Mobile App: {success: false, message: "Token expired"}
    else Token Valid
        API->>API: Validate all fields
        
        alt Name Invalid
            API-->>Mobile App: {success: false, message: "Name too short"}
        else Age < 18
            API-->>Mobile App: {success: false, message: "Must be 16+"}
        else Invalid Gender
            API-->>Mobile App: {success: false, message: "Invalid gender"}
        else Invalid Interests
            API-->>Mobile App: {success: false, message: "Select 1-5 interests"}
        else Invalid Pictures
            API-->>Mobile App: {success: false, message: "1-6 pictures required"}
        else All Valid
            API->>Database: Update UserProfile
            API->>Database: Set event_interests (ManyToMany)
            Database-->>API: Profile saved
            API-->>Mobile App: {success: true, profile_complete: true}
            Mobile App-->>User: Profile completed! (Navigate to home)
        end
    end
```

**What Happens:**
1. App fetches available event interests
2. User fills profile form
3. App sends profile data with JWT token
4. Backend validates every field:
   - Name: 2+ characters, letters only
   - Birth date: Must be 16+
   - Gender: male/female/other
   - Event interests: 1-5 valid IDs
   - Profile pictures: 1-6 valid URLs
5. Saves profile data
6. Returns success

**Request:**
```json
{
  "phone_number": "+1234567890",
  "name": "John Doe",
  "birth_date": "1995-01-15",
  "gender": "male",
  "event_interests": [1, 3, 5, 7],
  "profile_pictures": [
    "https://example.com/pic1.jpg",
    "https://example.com/pic2.jpg"
  ],
  "bio": "Love music and traveling",
  "location": "New York, USA"
}
```

**Success Response:**
```json
{
  "success": true,
  "message": "Profile completed successfully. You can now use the app!",
  "data": {
    "user_id": 123,
    "profile_id": 456,
    "name": "John Doe",
    "phone_number": "+1234567890",
    "gender": "male",
    "event_interests_count": 4,
    "profile_pictures_count": 2,
    "profile_complete": true
  }
}
```

### Lead Tracking Flow

```mermaid
graph TD
    A[User requests OTP] --> B[PhoneOTP record created]
    B --> C[is_verified = false]
    C --> D[Lead stored in database]
    D --> E[Admin can view in Django Admin]
    E --> F{User verifies OTP?}
    
    F -->|Yes - Within 10 minutes| G[is_verified = true]
    F -->|No - Never verifies| H[Lead remains unverified]
    F -->|No - OTP expires| H
    
    G --> I[Lead converted to User]
    I --> J[Full signup/login completed]
    
    H --> K[Business analytics available]
    K --> L[Marketing team can analyze]
    L --> M[Follow-up campaigns possible]
    M --> N[Re-engagement strategies]
    
    style C fill:#ffebee
    style D fill:#e1f5fe
    style G fill:#e8f5e9
    style H fill:#fff3e0
    style K fill:#fff3e0
```

**Why Lead Tracking Matters:**
- **Business Intelligence**: See how many users start but don't complete signup
- **Marketing Data**: Phone numbers of interested users
- **Re-engagement**: Target users who didn't complete signup
- **Analytics**: Calculate conversion rates
- **Admin Access**: View all leads in Django Admin under "Phone OTP" section

---

## 🌐 API Endpoints

### Base URLs
- **Production**: `https://loopinbackend-g17e.onrender.com/api/`
- **Local Dev**: `http://localhost:8000/api/`

### Complete API Reference

#### 1. Unified Signup/Login - Send OTP

**Endpoint:** `POST /api/auth/signup`

**Description:** Universal entry point for both new and existing users. Sends 4-digit OTP via SMS.

**Request:**
```json
{
  "phone_number": "+1234567890"
}
```

**Validation:**
- Phone number must include country code (e.g., `+1` for USA)
- Format: `+[country_code][number]` (E.164 format)
- Example valid formats:
  - `+1234567890`
  - `+1 (234) 567-8900`
  - `+1-234-567-8900`

**Success Response (New User):**
```json
{
  "success": true,
  "message": "OTP sent successfully to your phone number. Please verify to complete signup.",
  "data": {
    "phone_number": "+1234567890",
    "user_status": "new",
    "otp_sent": true
  },
  "token": null
}
```

**Success Response (Existing User - Complete Profile):**
```json
{
  "success": true,
  "message": "OTP sent successfully to your phone number. Please verify to login.",
  "data": {
    "phone_number": "+1234567890",
    "user_status": "existing",
    "otp_sent": true
  },
  "token": null
}
```

**Success Response (Existing User - Incomplete Profile):**
```json
{
  "success": true,
  "message": "OTP sent successfully. Please verify to complete your registration.",
  "data": {
    "phone_number": "+1234567890",
    "user_status": "existing",
    "otp_sent": true
  },
  "token": null
}
```

**Error Responses:**
```json
// Invalid phone format
{
  "success": false,
  "message": "Invalid phone number format"
}

// SMS send failure
{
  "success": false,
  "message": "Failed to send OTP. Please try again later."
}

// Server error
{
  "success": false,
  "message": "An unexpected error occurred. Please try again later."
}
```

---

#### 2. Verify OTP - Create Account or Login

**Endpoint:** `POST /api/auth/verify-otp`

**Description:** Verifies the 4-digit OTP. Creates new account for new users, logs in existing users.

**Request:**
```json
{
  "phone_number": "+1234567890",
  "otp_code": "1234"
}
```

**Validation:**
- OTP must be exactly 4 digits
- Only numeric characters
- Case-sensitive (though OTP is always numeric)
- OTP valid for 10 minutes
- Maximum 3 verification attempts

**Success Response (Profile Incomplete):**
```json
{
  "success": true,
  "message": "OTP verified successfully. Please complete your profile to continue.",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjMsInBob25lX251bWJlciI6IisxMjM0NTY3ODkwIiwiZXhwIjoxNzM1Njg5NjAwLCJpYXQiOjE3MzMwOTc2MDB9...",
  "data": {
    "user_id": 123,
    "phone_number": "+1234567890",
    "needs_profile_completion": true,
    "is_verified": true
  }
}
```

**Success Response (Profile Complete - Logged In):**
```json
{
  "success": true,
  "message": "OTP verified successfully. You are logged in.",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "data": {
    "user_id": 123,
    "phone_number": "+1234567890",
    "needs_profile_completion": false,
    "is_verified": true
  }
}
```

**Error Responses:**
```json
// No phone number
{
  "success": false,
  "message": "Phone number is required"
}

// No OTP code
{
  "success": false,
  "message": "OTP code is required"
}

// No OTP found
{
  "success": false,
  "message": "No OTP found for this phone number. Please request a new OTP."
}

// Invalid OTP (Wrong code)
{
  "success": false,
  "message": "Invalid OTP. 2 attempts remaining"
}

// Expired OTP
{
  "success": false,
  "message": "OTP has expired. Please request a new OTP."
}

// Too many attempts
{
  "success": false,
  "message": "Too many attempts. Please request a new OTP"
}

// Account creation error
{
  "success": false,
  "message": "An error occurred while creating your account. Please try again."
}

// Token generation error
{
  "success": false,
  "message": "Authentication successful but token generation failed. Please try again."
}
```

---

#### 3. Complete Profile

**Endpoint:** `POST /api/auth/complete-profile`

**Description:** Completes user profile with name, birth date, gender, interests, and pictures. Requires JWT token from `/verify-otp`.

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**Request:**
```json
{
  "phone_number": "+1234567890",
  "name": "John Doe",
  "birth_date": "1995-01-15",
  "gender": "male",
  "event_interests": [1, 3, 5],
  "profile_pictures": [
    "https://example.com/pic1.jpg",
    "https://example.com/pic2.jpg"
  ],
  "bio": "Love music and traveling",
  "location": "New York, USA"
}
```

**Field Requirements:**

| Field | Required | Validation | Example |
|-------|----------|------------|---------|
| `phone_number` | ✅ | Valid phone format | `"+1234567890"` |
| `name` | ✅ | 2-100 chars, letters/spaces/hyphens | `"John Doe"` |
| `birth_date` | ✅ | YYYY-MM-DD, must be 16+ | `"2007-01-15"` |
| `gender` | ✅ | male/female/other | `"male"` |
| `event_interests` | ✅ | Array of 1-5 valid IDs | `[1, 2, 3]` |
| `profile_pictures` | ✅ | Array of 1-6 valid URLs | `["https://..."]` |
| `bio` | ❌ | Max 500 characters | `"Backend dev"` |
| `location` | ❌ | Max 100 characters | `"New York"` |

**Validation Details:**
- **Name**: Must contain only letters, spaces, hyphens, apostrophes
- **Age**: Calculated from birth_date, must be 18 or older
- **Gender**: Case-insensitive, converted to lowercase
- **Event Interests**: Must be active interests from database
- **Picture URLs**: Must be valid HTTP/HTTPS URLs
- **Bio**: Optional, truncated if > 500 chars
- **Location**: Optional, truncated if > 100 chars

**Success Response:**
```json
{
  "success": true,
  "message": "Profile completed successfully. You can now use the app!",
  "data": {
    "user_id": 123,
    "profile_id": 456,
    "name": "John Doe",
    "phone_number": "+1234567890",
    "gender": "male",
    "event_interests_count": 3,
    "profile_pictures_count": 2,
    "profile_complete": true
  },
  "token": null
}
```

**Error Responses:**
```json
// Invalid/Expired token
{
  "success": false,
  "message": "Token has expired"
}

// Missing name
{
  "success": false,
  "message": "Name is required"
}

// Name too short
{
  "success": false,
  "message": "String should have at least 2 characters"
}

// Invalid name characters
{
  "success": false,
  "message": "Name contains invalid characters"
}

// Missing birth date
{
  "success": false,
  "message": "Birth date is required"
}

// Invalid date format
{
  "success": false,
  "message": "Invalid date format. Use YYYY-MM-DD"
}

// Age under 16
{
  "success": false,
  "message": "User must be 16 years or older"
}

// Invalid gender
{
  "success": false,
  "message": "Gender must be one of: male, female, other"
}

// No event interests
{
  "success": false,
  "message": "At least one event interest is required"
}

// Too many interests
{
  "success": false,
  "message": "List should have at most 5 items after validation"
}

// Invalid interest IDs
{
  "success": false,
  "message": "One or more selected event interests (1) are invalid or inactive. Please select from available interests."
}

// No profile pictures
{
  "success": false,
  "message": "At least one profile picture is required"
}

// Too many pictures
{
  "success": false,
  "message": "Maximum 6 profile pictures allowed"
}

// Invalid picture URL
{
  "success": false,
  "message": "Invalid URL format for profile picture 1"
}

// Bio too long
{
  "success": false,
  "message": "String should have at most 500 characters"
}
```

---

#### 4. Get Event Interests

**Endpoint:** `GET /api/auth/event-interests`

**Description:** Returns list of all active event interests available for selection during profile completion.

**Request:** No body required

**Success Response:**
```json
{
  "success": true,
  "message": "Event interests retrieved successfully",
  "data": [
    {
      "id": 1,
      "name": "Music & Concerts",
      "description": "Live music, concerts, and musical events"
    },
    {
      "id": 2,
      "name": "Sports & Fitness",
      "description": "Sports events, fitness activities, and competitions"
    },
    {
      "id": 3,
      "name": "Food & Dining",
      "description": "Food festivals, cooking classes, and dining experiences"
    },
    {
      "id": 4,
      "name": "Art & Culture",
      "description": "Art exhibitions, cultural events, and museum visits"
    },
    {
      "id": 5,
      "name": "Technology",
      "description": "Tech meetups, conferences, and innovation events"
    },
    {
      "id": 6,
      "name": "Travel & Adventure",
      "description": "Travel experiences, adventure activities, and exploration"
    },
    {
      "id": 7,
      "name": "Business & Networking",
      "description": "Professional networking, business events, and conferences"
    },
    {
      "id": 8,
      "name": "Health & Wellness",
      "description": "Wellness retreats, health seminars, and mindfulness events"
    },
    {
      "id": 9,
      "name": "Education & Learning",
      "description": "Workshops, seminars, and educational events"
    },
    {
      "id": 10,
      "name": "Entertainment",
      "description": "Movies, shows, gaming, and entertainment events"
    }
  ]
}
```

**Error Response:**
```json
{
  "success": false,
  "message": "An error occurred while fetching event interests"
}
```

---

#### 5. Get User Profile

**Endpoint:** `GET /api/auth/profile`

**Description:** Returns complete user profile information. Requires JWT token.

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Success Response:**
```json
{
  "id": 456,
  "name": "John Doe",
  "phone_number": "+1234567890",
  "gender": "male",
  "bio": "Love music and traveling",
  "location": "New York, USA",
  "birth_date": "1995-01-15",
  "event_interests": [
    {
      "id": 1,
      "name": "Music & Concerts",
      "description": "Live music, concerts, and musical events",
      "is_active": true,
      "created_at": "2025-10-01T00:00:00Z",
      "updated_at": "2025-10-01T00:00:00Z"
    }
  ],
  "profile_pictures": [
    "https://example.com/pic1.jpg",
    "https://example.com/pic2.jpg"
  ],
  "is_verified": true,
  "is_active": true,
  "created_at": "2025-10-11T10:15:23.435393+00:00",
  "updated_at": "2025-10-11T10:17:32.077460+00:00"
}
```

**Error Responses:**
```json
// Invalid token
{
  "detail": "Invalid token"
}

// Expired token
{
  "detail": "Token has expired"
}

// User not found
{
  "detail": "User not found"
}

// Profile not found
{
  "detail": "User profile not found"
}
```

---

#### 6. Logout

**Endpoint:** `POST /api/auth/logout`

**Description:** Logs out the current user. (Token-based, so client should discard token)

**Success Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

---

## 🗄️ Database Models

### UserProfile Model
```python
class UserProfile(models.Model):
    """Extended user profile model for normal users"""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    
    # Basic profile information
    name = models.CharField(max_length=100, blank=True, help_text="Full name of the user")
    phone_number = models.CharField(max_length=15, blank=True, help_text="Contact phone number")
    
    # Additional profile details
    bio = models.TextField(max_length=500, blank=True, help_text="User biography")
    location = models.CharField(max_length=100, blank=True, help_text="User location")
    birth_date = models.DateField(null=True, blank=True, help_text="Date of birth")
    
    # New required fields
    gender = models.CharField(
        max_length=10, 
        choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')],
        blank=True, 
        help_text="User gender"
    )
    event_interests = models.ManyToManyField(
        'EventInterest', 
        blank=True, 
        help_text="User's event interests (1-5 selections required)"
    )
    profile_pictures = models.JSONField(
        default=list, 
        blank=True, 
        help_text="List of profile picture URLs (1-6 pictures required)"
    )
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Profile status
    is_verified = models.BooleanField(default=False, help_text="Whether the user profile is verified")
    is_active = models.BooleanField(default=True, help_text="Whether the user profile is active")
    
    def __str__(self):
        return f"{self.name} ({self.phone_number})"
```

### PhoneOTP Model (Lead Tracking)
```python
class PhoneOTP(models.Model):
    """Model for storing phone number OTP verification"""
    phone_number = models.CharField(max_length=15, unique=True)
    otp_code = models.CharField(max_length=4)  # 4-digit OTP
    is_verified = models.BooleanField(default=False)  # Lead tracking
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    attempts = models.IntegerField(default=0)
    
    def generate_otp(self):
        """Generate a 4-digit OTP"""
        import random, string
        from django.utils import timezone
        from datetime import timedelta
        
        self.otp_code = ''.join(random.choices(string.digits, k=4))
        self.expires_at = timezone.now() + timedelta(minutes=10)
        self.attempts = 0
        self.is_verified = False
    
    def verify_otp(self, code):
        """Verify OTP code"""
        if self.attempts >= 3:
            return False, "Too many attempts. Please request a new OTP"
        
        if timezone.now() > self.expires_at:
            return False, "OTP has expired. Please request a new OTP."
        
        if self.otp_code != code:
            self.attempts += 1
            self.save()
            remaining = 3 - self.attempts
            return False, f"Invalid OTP. {remaining} attempts remaining"
        
        self.is_verified = True
        self.save()
        return True, "OTP verified successfully"
    
    def is_expired(self):
        return timezone.now() > self.expires_at
```

### EventInterest Model
```python
class EventInterest(models.Model):
    """Model for event interests/categories"""
    name = models.CharField(max_length=100, unique=True, help_text="Name of the event interest")
    description = models.TextField(blank=True, help_text="Description of the event interest")
    is_active = models.BooleanField(default=True, help_text="Whether this interest is active")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name = "Event Interest"
        verbose_name_plural = "Event Interests"
        ordering = ['name']
```

---

## ⚙️ Configuration

### Environment Variables (.env)
```bash
# Django Settings
SECRET_KEY="your-secret-key-here"
DEBUG=False  # True for development
DJANGO_SETTINGS_MODULE=loopin_backend.settings.prod

# Database Configuration (Supabase)
DATABASE_URL="postgresql://postgres.PROJECT_REF:PASSWORD@aws-1-us-east-2.pooler.supabase.com:6543/postgres"

# JWT Settings
JWT_SECRET_KEY="your-jwt-secret-key"
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Twilio Configuration
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+15005550006
TWILIO_TEST_MODE=false  # true for development

# Deployment
ALLOWED_HOSTS=*
CORS_ALLOW_ALL_ORIGINS=true
```

---

## 🧪 Testing

### Local Development Testing

```bash
# 1. Start Docker containers
docker-compose up -d

# 2. Check logs for OTP (if TWILIO_TEST_MODE=true)
docker-compose logs web -f | grep "TEST MODE"

# 3. Test unified flow
# Send OTP
curl -X POST "http://localhost:8000/api/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890"}'

# Get OTP from logs
# TEST MODE: OTP 1234 would be sent to +1234567890

# Verify OTP
curl -X POST "http://localhost:8000/api/auth/verify-otp" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890", "otp_code": "1234"}'

# Response will include token and needs_profile_completion flag

# If needs_profile_completion = true:
curl -X POST "http://localhost:8000/api/auth/complete-profile" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "phone_number": "+1234567890",
    "name": "John Doe",
    "birth_date": "1995-01-01",
    "gender": "male",
    "event_interests": [1, 2, 3],
    "profile_pictures": ["https://example.com/pic1.jpg"]
  }'
```

### Production Testing (Render)

```bash
# Same flow but use production URL
curl -X POST "https://loopinbackend-g17e.onrender.com/api/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890"}'

# OTP will be sent via real SMS
# Check your phone for the 4-digit code
```

---

## 🛠️ Troubleshooting

### Common Issues

#### 1. "Failed to send OTP"
**Cause:** Twilio service error or invalid credentials
**Solution:**
- Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN
- Verify Twilio account is active
- Check phone number is verified (for trial accounts)

#### 2. "Invalid OTP"
**Cause:** Wrong OTP entered or OTP expired
**Solution:**
- Request new OTP
- Check OTP in SMS (or logs if test mode)
- Enter exact 4-digit code

#### 3. "Token has expired"
**Cause:** JWT token older than 30 days
**Solution:**
- Login again to get new token
- Tokens expire after 30 days for security

#### 4. "User must be 16 years or older"
**Cause:** Birth date indicates user is under 16
**Solution:**
- Provide valid birth date
- Must be born before October 11, 2009

#### 5. "needs_profile_completion = true" but don't see form
**Cause:** Mobile app not handling flag
**Solution:**
- Check `needs_profile_completion` field in response
- If true, show profile completion screen
- If false, navigate to home screen

---

## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG=False`
- [ ] Set `TWILIO_TEST_MODE=false`
- [ ] Use production Twilio credentials
- [ ] Configure proper DATABASE_URL (Supabase)
- [ ] Set strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Test complete flow on production




## 📚 Additional Resources

### Technology Stack
- **FastAPI**: REST API endpoints with automatic documentation
- **Django**: Database models, admin interface, ORM
- **PostgreSQL**: Database (Supabase cloud)
- **Twilio**: SMS OTP delivery
- **JWT**: Authentication tokens
- **Pydantic**: Request/response validation
- **Docker**: Containerization
- **ASGI**: Async web server (Gunicorn + Uvicorn)

### Useful Links
- **Production API**: https://loopinbackend-g17e.onrender.com/api/
- **API Docs**: https://loopinbackend-g17e.onrender.com/api/docs
- **Admin Panel**: https://loopinbackend-g17e.onrender.com/django/admin/

