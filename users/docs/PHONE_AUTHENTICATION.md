# 📱 Phone Authentication System Documentation

## 📋 Table of Contents
- [🚀 Quick Reference](#-quick-reference)
- [🎯 Overview](#-overview)
- [🔄 Unified Authentication Flow](#-unified-authentication-flow)
- [🌐 API Endpoints](#-api-endpoints)
- [🗄️ Database Models](#️-database-models)
- [⚙️ Configuration](#️-configuration)
- [🧪 Testing](#-testing)
- [📱 Mobile App Integration Guide](#-mobile-app-integration-guide)
- [🛠️ Troubleshooting](#️-troubleshooting)
- [🚀 Deployment](#-deployment)
- [📚 Additional Resources](#-additional-resources)

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
# ⚠️ Security: ONLY phone_number is accepted - other fields are ignored
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
ENABLE_WHATSAPP_NOTIFICATIONS=true  # Real WhatsApp messages
```

#### Test Mode (Local Development)
```bash
TWILIO_TEST_MODE=true   # OTP visible in logs
DEBUG=True              # Development settings
ENABLE_WHATSAPP_NOTIFICATIONS=true  # WhatsApp messages logged only
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
- ✅ **Automatic Waitlist System**: New users placed on waitlist after first profile completion
- ✅ **Waitlist Promotion**: Automatic activation after 1.10-1.35 hours (no manual approval needed)
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
    A[📱 Mobile App] --> B[👤 User enters phone number]
    B --> C[🚀 POST /api/auth/signup]
    C --> D{🔍 User exists in DB?}
    
    D -->|🆕 No - New User| E[🎲 Generate 4-digit OTP]
    D -->|✅ Yes - Existing User| F{📋 Profile complete?}
    
    F -->|✅ Yes - Complete| E
    F -->|⚠️ No - Incomplete| E
    
    E --> G[💾 Store OTP in PhoneOTP table]
    G --> H[🔴 Mark is_verified = false]
    H --> I[📨 Send SMS via Twilio]
    I --> J{📤 SMS sent successfully?}
    
    J -->|❌ No| K[⚠️ Return: Failed to send OTP]
    J -->|✅ Yes| L[🎉 Return: OTP sent successfully]
    
    L --> M[📱 User receives OTP via SMS]
    M --> N[👤 User enters OTP in app]
    N --> O[🔐 POST /api/auth/verify-otp]
    
    O --> P{✅ OTP valid?}
    P -->|❌ No - Wrong OTP| Q[📈 Increment attempts]
    P -->|⏰ No - Expired| R[⚠️ Return: OTP expired]
    P -->|🚫 No - Max attempts| S[❌ Return: Too many attempts]
    P -->|✅ Yes - Valid OTP| T[🟢 Mark is_verified = true]
    
    Q --> U{🔢 Attempts < 3?}
    U -->|✅ Yes| V[⚠️ Return: Invalid OTP<br/>X attempts remaining]
    U -->|❌ No| S
    
    T --> W{🔍 User account exists?}
    W -->|🆕 No| X[✨ Create new User account]
    W -->|✅ Yes| Y[🔄 Get existing User account]
    
    X --> Z[📝 Create UserProfile]
    Y --> AA{📋 UserProfile exists?}
    
    AA -->|❌ No| Z
    AA -->|✅ Yes| AB[📄 Get existing UserProfile]
    
    Z --> AC[🟢 Set is_verified = true]
    AB --> AC
    
    AC --> AD[🔐 Generate JWT token<br/>⏰ Valid: 30 days]
    AD --> AE{🔍 Profile complete?}
    
    AE -->|Check: name AND profile_pictures| AF{✅ Has both?}
    AF -->|❌ No| AG[⚠️ needs_profile_completion = true]
    AF -->|✅ Yes| AH[🎉 needs_profile_completion = false]
    
    AG --> AI[📤 Return: Token +<br/>Please complete profile]
    AH --> AJ[📤 Return: Token +<br/>Logged in]
    
    AI --> AK[📱 Mobile App:<br/>Show profile completion screen]
    AJ --> AL[🏠 Mobile App:<br/>Navigate to home screen]
    
    AK --> AM[🎯 GET /api/auth/event-interests]
    AM --> AN[📝 User fills profile form<br/>Name, DOB, Gender, Interests, Pictures]
    AN --> AO[📤 POST /api/auth/complete-profile]
    
    AO --> AP{✅ All validations pass?}
    AP -->|❌ No| AQ[⚠️ Return: Validation errors<br/>Name/Age/Gender/Interests/Pictures]
    AP -->|✅ Yes| AR[💾 Save profile data]
    
    AR --> AS[🔗 Set event_interests<br/>ManyToMany relationship]
    AS --> AT[🎉 Return: Profile completed]
    AT --> AL
    
    AQ --> AN
    
    style H fill:#ffebee,stroke:#d32f2f,stroke-width:3px
    style K fill:#ffebee,stroke:#d32f2f,stroke-width:3px
    style R fill:#ffebee,stroke:#d32f2f,stroke-width:3px
    style S fill:#ffebee,stroke:#d32f2f,stroke-width:3px
    style V fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style T fill:#e8f5e9,stroke:#388e3c,stroke-width:3px
    style AC fill:#e8f5e9,stroke:#388e3c,stroke-width:3px
    style AG fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style AH fill:#e8f5e9,stroke:#388e3c,stroke-width:3px
    style AT fill:#e8f5e9,stroke:#388e3c,stroke-width:3px
    style G fill:#e1f5fe,stroke:#0288d1,stroke-width:2px
    style X fill:#c8e6c9,stroke:#388e3c,stroke-width:2px
    style Z fill:#c8e6c9,stroke:#388e3c,stroke-width:2px
    style AL fill:#81c784,stroke:#388e3c,stroke-width:4px
    style AQ fill:#ffccbc,stroke:#d32f2f,stroke-width:2px
```

### Detailed Step-by-Step Flow

#### Step 1: Send OTP (Universal Entry Point)

```mermaid
%%{init: {'theme':'base', 'themeVariables': { 'primaryColor':'#e3f2fd','primaryTextColor':'#1565c0','primaryBorderColor':'#1976d2','lineColor':'#42a5f5','secondaryColor':'#f3e5f5','tertiaryColor':'#e8f5e9'}}}%%
sequenceDiagram
    autonumber
    participant U as 👤 User
    participant M as 📱 Mobile App
    participant A as 🚀 API Server
    participant D as 💾 Database
    participant T as 📨 Twilio SMS
    
    Note over U,M: 📥 STEP 1: User Input
    U->>M: Enters phone number<br/>+1234567890
    
    Note over M,A: 🚀 STEP 2: API Request
    M->>A: POST /api/auth/signup<br/>{phone_number: "+1234567890"}
    
    Note over A,D: 🔍 STEP 3: User Detection
    A->>D: SELECT * FROM User<br/>WHERE username = phone
    alt 🆕 User is New
        D-->>A: ❌ No user found
        Note right of A: ✨ user_status = "new"<br/>🎯 Signup flow
    else ✅ User Exists (Complete Profile)
        D-->>A: ✅ User found<br/>Profile: Complete
        Note right of A: 🔄 user_status = "existing"<br/>🎯 Login flow
    else ⚠️ User Exists (Incomplete Profile)
        D-->>A: ⚠️ User found<br/>Profile: Incomplete
        Note right of A: 🔄 user_status = "existing"<br/>🎯 Resume signup
    end
    
    Note over A,D: 🎲 STEP 4: OTP Generation
    A->>D: INSERT/UPDATE PhoneOTP<br/>SET is_verified = false
    D-->>A: ✅ OTP record created
    Note right of D: 🔴 Lead tracked!<br/>is_verified = false
    A->>A: 🎲 Generate 4-digit OTP<br/>Code: 1234
    
    Note over A,T: 📨 STEP 5: SMS Delivery
    A->>T: Send SMS<br/>To: +1234567890<br/>Message: "Your OTP is 1234"
    
    alt ✅ SMS Success
        T-->>A: 📤 Message sent successfully
        A-->>M: 🎉 {success: true,<br/>otp_sent: true,<br/>user_status: "new"}
        M-->>U: ✅ OTP sent!<br/>Check your phone 📱
    else ❌ SMS Failure
        T-->>A: ⚠️ Send failed
        A-->>M: ❌ {success: false,<br/>message: "Failed to send OTP"}
        M-->>U: ⚠️ Error: Please try again
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
%%{init: {'theme':'base', 'themeVariables': { 'primaryColor':'#e3f2fd','primaryTextColor':'#1565c0','primaryBorderColor':'#1976d2','lineColor':'#42a5f5','secondaryColor':'#f3e5f5','tertiaryColor':'#e8f5e9'}}}%%
sequenceDiagram
    autonumber
    participant U as 👤 User
    participant M as 📱 Mobile App
    participant A as 🚀 API Server
    participant D as 💾 Database
    participant T as 📨 Twilio SMS
    
    Note over U,M: 📥 STEP 1: User Input
    U->>M: Enters 4-digit OTP<br/>Code: 1234
    
    Note over M,A: 🚀 STEP 2: Verification Request
    M->>A: POST /api/auth/verify-otp<br/>{phone: "+1234567890", otp_code: "1234"}
    
    Note over A,D: 🔍 STEP 3: OTP Lookup
    A->>D: SELECT * FROM PhoneOTP<br/>WHERE phone_number = phone
    
    alt ❌ OTP Not Found
        D-->>A: No record
        A-->>M: ❌ {success: false, message: "No OTP found"}
        M-->>U: ⚠️ Please request new OTP
    else ✅ OTP Found
        D-->>A: OTP record returned
        
        Note over A: 🔍 STEP 4: OTP Validation
        A->>A: Verify OTP code
        
        alt ⏰ OTP Expired (>10 min)
            A-->>M: ❌ {success: false, message: "OTP has expired"}
            M-->>U: ⚠️ Request new OTP
        else 🚫 Too Many Attempts (≥3)
            A-->>M: ❌ {success: false, message: "Too many attempts"}
            M-->>U: ⚠️ Request new OTP
        else ❌ Wrong OTP Code
            A->>D: UPDATE attempts = attempts + 1
            A-->>M: ❌ {success: false, message: "Invalid OTP. X attempts remaining"}
            M-->>U: ⚠️ Try again
        else ✅ Correct OTP
            
            Note over A,D: 🟢 STEP 5: Mark Verified
            A->>D: UPDATE PhoneOTP SET is_verified = true
            D-->>A: ✅ Lead converted!
            Note right of D: 🟢 is_verified = true<br/>✨ Lead → User
            
            Note over A,D: 👤 STEP 6: User Account
            A->>D: SELECT * FROM User WHERE username = phone
            
            alt 🆕 New User (Signup)
                D-->>A: ❌ No user found
                A->>D: INSERT INTO User - CREATE account
                D-->>A: ✅ User created
                A->>D: INSERT INTO UserProfile - SET is_verified = true
                D-->>A: ✅ Profile created
                Note right of D: 🎉 New account!<br/>User ID: 123
            else 🔄 Existing User (Login)
                D-->>A: ✅ User found
                A->>D: SELECT * FROM UserProfile
                D-->>A: Profile returned
                Note right of D: 🔓 Login successful!<br/>User ID: 123
            end
            
            Note over A: 🔐 STEP 7: Generate Token
            A->>A: Generate JWT token<br/>Expiry: 30 days
            
            Note over A: 📋 STEP 8: Check Profile
            A->>A: Check profile completion<br/>Has name AND pictures?
            
            alt ⚠️ Profile Incomplete
                Note right of A: ❌ Missing: name OR pictures<br/>🎯 Needs completion
                A-->>M: 🎉 {success: true, needs_profile_completion: true, token: "eyJ..."}
                M-->>U: ✅ Verified!<br/>📝 Complete your profile
            else ✅ Profile Complete
                Note right of A: ✅ Has: name AND pictures<br/>🎯 Ready to use
                A-->>M: 🎉 {success: true, needs_profile_completion: false, token: "eyJ..."}
                M-->>U: 🎊 Welcome back!<br/>🏠 Navigate to home
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
%%{init: {'theme':'base', 'themeVariables': { 'primaryColor':'#e3f2fd','primaryTextColor':'#1565c0','primaryBorderColor':'#1976d2','lineColor':'#42a5f5','secondaryColor':'#f3e5f5','tertiaryColor':'#e8f5e9'}}}%%
sequenceDiagram
    autonumber
    participant U as 👤 User
    participant M as 📱 Mobile App
    participant A as 🚀 API Server
    participant D as 💾 Database
    
    Note over M: ⚠️ ONLY IF needs_profile_completion = true
    
    Note over M,A: 🎯 STEP 1: Fetch Event Interests
    M->>A: GET /api/auth/event-interests
    A->>D: SELECT * FROM EventInterest WHERE is_active = true
    D-->>A: 📋 12 active interests
    A-->>M: {data: [Music, Sports, Food, Art, Tech...]}
    M-->>U: 📝 Show profile form with interest options
    
    Note over U,M: 📝 STEP 2: User Fills Form
    U->>M: Enters profile data:<br/>• Name: "John Doe" (2+ chars)<br/>• DOB: "2007-01-15" (16+)<br/>• Gender: "male"<br/>• Interests: [1,2,3]<br/>• Pictures: [url1, url2]<br/>• Bio: "Love events"
    
    Note over M,A: 📤 STEP 3: Submit Profile
    M->>A: POST /api/auth/complete-profile<br/>Authorization: Bearer token<br/>{...profile data}
    
    Note over A: 🔐 STEP 4: Token Verification
    A->>A: Verify JWT token
    
    alt ❌ Token Invalid/Expired
        A-->>M: ❌ {success: false, message: "Token expired"}
        M-->>U: ⚠️ Please login again
    else ✅ Token Valid
        
        Note over A: 🔍 STEP 5: Field Validation
        A->>A: Validate all fields
        
        alt ❌ Name Too Short (<2 chars)
            A-->>M: ❌ {success: false, message: "Name too short"}
            M-->>U: ⚠️ Name must be 2+ chars
        else ❌ Age Under 16
            A-->>M: ❌ {success: false, message: "Must be 16+"}
            M-->>U: ⚠️ Must be 16 or older
        else ❌ Invalid Gender
            A-->>M: ❌ {success: false, message: "Invalid gender"}
            M-->>U: ⚠️ Choose male/female/other
        else ❌ Invalid Interests (0 or >5)
            A-->>M: ❌ {success: false, message: "Select 1-5 interests"}
            M-->>U: ⚠️ Pick 1 to 5 interests
        else ❌ Invalid Pictures (0 or >6)
            A-->>M: ❌ {success: false, message: "1-6 pictures required"}
            M-->>U: ⚠️ Upload 1 to 6 photos
        else ✅ All Fields Valid
            
            Note over A,D: 💾 STEP 6: Save Profile
            A->>D: UPDATE UserProfile SET<br/>name, birth_date, gender,<br/>profile_pictures, bio, location
            D-->>A: ✅ Profile updated
            
            A->>D: INSERT INTO UserProfile_EventInterest<br/>SET event_interests
            D-->>A: ✅ Interests linked
            Note right of D: 🎉 Profile complete!<br/>✨ User ready
            
            Note over A,M: 🎊 STEP 7: Success Response
            A-->>M: {success: true, profile_complete: true,<br/>message: "You can now use the app!"}
            M-->>U: 🎉 Profile completed!<br/>🏠 Navigate to home
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
6. **Waitlist Placement (First-Time Profile Completion Only):**
   - If this is the user's first time completing their profile, the backend automatically places them on a waitlist
   - Sets `User.is_active = False` and `UserProfile.is_active = False`
   - Schedules automatic promotion: `waitlist_promote_at = now + random(66-81 minutes)`
   - User can only access profile endpoints until promotion
   - Promotion happens automatically during normal API requests (no background workers needed)
7. Returns success response

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

**⚠️ Important Waitlist Note:**
- After first-time profile completion, users are automatically placed on a waitlist
- The user's account will have `is_active = false` until automatic promotion (1.10-1.35 hours later)
- Users can only access profile endpoints (`GET /api/auth/profile`, `PUT /api/auth/profile`) while on waitlist
- All other endpoints will return `403 FORBIDDEN` with message: "Your account is on the waitlist. You can only access your profile. Please wait 1.10-1.35 hours for activation."
- Check `is_active` field in `GET /api/auth/profile` response to determine waitlist status
- Promotion happens automatically during normal API requests - no manual action required

### Lead Tracking Flow (Business Intelligence)

```mermaid
graph TD
    A[👤 User requests OTP] --> B[📝 PhoneOTP record created]
    B --> C[🔴 is_verified = false]
    C --> D[💼 Lead stored in database]
    D --> E[👨‍💼 Admin can view in Django Admin]
    E --> F{⏰ User verifies OTP?}
    
    F -->|✅ Yes - Within 10 minutes| G[🟢 is_verified = true]
    F -->|❌ No - Never verifies| H[⚠️ Lead remains unverified]
    F -->|⏰ No - OTP expires| H
    
    G --> I[✨ Lead converted to User]
    I --> J[🎉 Full signup/login completed]
    J --> K[🏠 User active in system]
    
    H --> L[📊 Business analytics available]
    L --> M[📈 Marketing team can analyze:<br/>• Conversion rate<br/>• Drop-off points<br/>• User behavior]
    M --> N[📧 Follow-up campaigns:<br/>• SMS reminders<br/>• Special offers<br/>• Re-engagement]
    N --> O[🎯 Re-engagement strategies:<br/>• Personalized messages<br/>• Incentives<br/>• Support outreach]
    O --> P[💰 Revenue opportunities]
    
    style C fill:#ffebee,stroke:#d32f2f,stroke-width:3px
    style D fill:#e1f5fe,stroke:#0288d1,stroke-width:3px
    style G fill:#e8f5e9,stroke:#388e3c,stroke-width:3px
    style H fill:#fff3e0,stroke:#f57c00,stroke-width:3px
    style I fill:#c8e6c9,stroke:#388e3c,stroke-width:3px
    style J fill:#a5d6a7,stroke:#388e3c,stroke-width:3px
    style K fill:#81c784,stroke:#388e3c,stroke-width:3px
    style L fill:#fff9c4,stroke:#f57c00,stroke-width:2px
    style M fill:#ffe082,stroke:#f57c00,stroke-width:2px
    style N fill:#ffd54f,stroke:#f57c00,stroke-width:2px
    style O fill:#ffca28,stroke:#f57c00,stroke-width:2px
    style P fill:#ffc107,stroke:#f57c00,stroke-width:3px
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

**⚠️ Security Note:** 
- **ONLY** `phone_number` is accepted in the signup request
- Any additional fields (name, email, etc.) are **ignored** for security reasons
- Profile information is collected later after OTP verification in the `complete-profile` endpoint
- This prevents unauthorized data injection and ensures proper authentication flow

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

**Description:** Completes user profile with name, birth date, gender, interests, and pictures. Requires JWT token from `/verify-otp`. Accepts actual image files (multipart/form-data) which are uploaded to Supabase Storage.

**⚠️ Waitlist Note:** After first-time profile completion, users are automatically placed on a waitlist for 1.10-1.35 hours. During this time, `is_active` will be `false` and users can only access profile endpoints. Check `GET /api/auth/profile` to determine waitlist status.

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: multipart/form-data
```

**Request (multipart/form-data):**
```
name: "John Doe"
birth_date: "1995-01-15"
gender: "male"
event_interests: "[1,3,5]"  (JSON string array)
phone_number: "+1234567890"
bio: "Love music and traveling"  (optional)
location: "New York, USA"  (optional)
profile_pictures: [file1.jpg, file2.jpg]  (actual image files)
```

**Field Requirements:**

| Field | Required | Type | Validation | Example |
|-------|----------|------|------------|---------|
| `phone_number` | ✅ | Form field | Valid phone format, must match authenticated user | `"+1234567890"` |
| `name` | ✅ | Form field | 2-100 chars, letters/spaces/hyphens | `"John Doe"` |
| `birth_date` | ✅ | Form field | YYYY-MM-DD, must be 16+ | `"2007-01-15"` |
| `gender` | ✅ | Form field | male/female/other | `"male"` |
| `event_interests` | ✅ | Form field (JSON string) | JSON array of 1-5 valid IDs | `"[1,2,3]"` |
| `profile_pictures` | ✅ | File upload | 1-6 image files (jpg/jpeg/png/webp, max 5MB each) | `[file1.jpg, file2.jpg]` |
| `bio` | ❌ | Form field | Max 500 characters | `"Backend dev"` |
| `location` | ❌ | Form field | Max 100 characters | `"New York"` |

**Validation Details:**
- **Name**: Must contain only letters, spaces, hyphens, apostrophes
- **Age**: Calculated from birth_date, must be 16 or older
- **Gender**: Case-insensitive, converted to lowercase
- **Event Interests**: JSON string array (e.g., `"[1,2,3]"`), must be 1-5 active interest IDs from database
- **Profile Pictures**: Actual image files (not URLs), uploaded to Supabase Storage `user-profiles` bucket
  - Allowed formats: jpg, jpeg, png, webp
  - Max file size: 5MB per file
  - Min files: 1, Max files: 6
  - Files are automatically uploaded and public URLs are stored
- **Bio**: Optional, truncated if > 500 chars
- **Location**: Optional, truncated if > 100 chars

**Example cURL Request:**
```bash
curl -X POST "http://localhost:8000/api/auth/complete-profile" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "name=John Doe" \
  -F "birth_date=1995-01-15" \
  -F "gender=male" \
  -F "event_interests=[1,3,5]" \
  -F "phone_number=+1234567890" \
  -F "bio=Love music and traveling" \
  -F "location=New York, USA" \
  -F "profile_pictures=@/path/to/image1.jpg" \
  -F "profile_pictures=@/path/to/image2.jpg"
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
    "event_interests_count": 3,
    "profile_pictures_count": 2,
    "profile_complete": true
  },
  "token": null
}
```

**⚠️ Waitlist Status Check Required:**
After successful profile completion, immediately call `GET /api/auth/profile` to check the `is_active` field:
- **`is_active = false`**: User is on waitlist (1.10-1.35 hours until automatic activation)
  - Show waitlist screen in your app
  - Allow profile editing only
  - Block access to events, payments, and other core features
- **`is_active = true`**: User is fully active (already promoted or not on waitlist)
  - Enable all app features
  - Navigate to home screen

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

// Invalid file format
{
  "success": false,
  "message": "Invalid file type. Allowed: jpg, jpeg, png, webp"
}

// File too large
{
  "success": false,
  "message": "File size exceeds 5MB limit"
}

// Upload failed
{
  "success": false,
  "message": "An error occurred while uploading profile pictures. Please check file formats and sizes."
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
      "name": "Music & Concerts"
    },
    {
      "id": 2,
      "name": "Sports & Fitness"
    },
    {
      "id": 3,
      "name": "Food & Dining"
    },
    {
      "id": 4,
      "name": "Art & Culture"
    },
    {
      "id": 5,
      "name": "Technology"
    },
    {
      "id": 6,
      "name": "Travel & Adventure"
    },
    {
      "id": 7,
      "name": "Business & Networking"
    },
    {
      "id": 8,
      "name": "Health & Wellness"
    },
    {
      "id": 9,
      "name": "Education & Learning"
    },
    {
      "id": 10,
      "name": "Entertainment"
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
This endpoint is also the primary way for clients to determine whether a user is **waitlisted** or **fully active** by inspecting the `is_active` flag.

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
```

**Success Response:**
```json
{
  "id": 456, // ← Profile ID (don't use for token validation)
  "user_id": 123,  // ← User ID (use this for token validation)
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

#### 6. Update User Profile

**Endpoint:** `PUT /api/auth/profile`

**Description:** Update current user's profile information. All fields are optional for partial updates. Only provided fields will be updated. Waitlisted users can also access this endpoint.

**Headers:**
```
Authorization: Bearer <JWT_TOKEN>
Content-Type: application/json
```

**Request Body (all fields optional):**
```json
{
  "name": "John Doe Updated",
  "bio": "Updated bio text",
  "location": "San Francisco, USA",
  "birth_date": "1995-01-15",
  "gender": "male",
  "event_interests": [1, 3, 5],
  "profile_pictures": [
    "https://example.com/pic1.jpg",
    "https://example.com/pic2.jpg"
  ]
}
```

**Success Response:**
Returns the same structure as `GET /api/auth/profile` with updated fields.

**Error Responses:**
```json
// Validation error
{
  "detail": "Name must be at least 2 characters long"
}

// Invalid event interest IDs
{
  "detail": "One or more event interest IDs are invalid or inactive"
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

#### 7. Logout

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

## ⏳ Waitlist System

### Overview

The Loopin Backend implements an **automatic waitlist system** for new users who complete their profile for the first time. This system ensures a smooth onboarding experience while managing platform growth.

### How It Works

#### 1. Waitlist Placement

**When:** Immediately after a user completes their profile for the **first time**

**What Happens:**
- User's account is placed on waitlist: `User.is_active = False` and `UserProfile.is_active = False`
- Waitlist timestamps are set:
  - `waitlist_started_at`: Current timestamp
  - `waitlist_promote_at`: Current timestamp + random(66-81 minutes)
- User can only access profile endpoints while on waitlist
- All other endpoints return `403 FORBIDDEN` with waitlist message

#### 2. Waitlist Duration

**Promotion Window:** Random delay between **1.10-1.35 hours** (66-81 minutes)
- Each user gets a unique random delay within this window
- Prevents predictable patterns and system load spikes
- Example: User A might wait 70 minutes, User B might wait 78 minutes

#### 3. Automatic Promotion

**No Manual Approval Required:**
- Promotion happens automatically based on scheduled time
- No background workers, cron jobs, or Celery tasks needed
- Promotion check occurs during normal API requests

**How Promotion Works:**
1. User makes any API request (e.g., `GET /api/auth/profile`)
2. Backend checks if `waitlist_promote_at` exists and `now >= waitlist_promote_at`
3. If conditions met:
   - Sets `User.is_active = True` and `UserProfile.is_active = True`
   - Clears `waitlist_started_at` and `waitlist_promote_at` (sets to NULL)
   - Sends push notification: "Welcome to Loopin! Your account is now active."
   - User can now access all app features

**Promotion is Atomic:**
- Uses database transactions with row-level locking
- Prevents race conditions and ensures data consistency
- Multiple simultaneous requests won't cause duplicate promotions

#### 4. Access Restrictions

**While on Waitlist (`is_active = false`):**

**✅ Allowed Endpoints:**
- `GET /api/auth/profile` - View profile
- `PUT /api/auth/profile` - Update profile

**❌ Blocked Endpoints:**
- All event endpoints (`/api/events/*`)
- All payment endpoints (`/api/payments/*`)
- All payout endpoints (`/api/payouts/*`)
- All attendance endpoints (`/api/events-attendance/*`)
- All other authenticated endpoints

**Error Response for Blocked Endpoints:**
```json
{
  "detail": "Your account is on the waitlist. You can only access your profile. Please wait 1.10-1.35 hours for activation."
}
```
Status Code: `403 FORBIDDEN`

#### 5. Client-Side Detection

**Primary Method:** Check `is_active` field in `GET /api/auth/profile` response

**Response When on Waitlist:**
```json
{
  "id": 456,
  "user_id": 123,
  "name": "John Doe",
  "is_active": false,  // ← User is on waitlist
  ...
}
```

**Response When Active:**
```json
{
  "id": 456, // ← Profile ID (don't use for token validation)
  "user_id": 123, // ← User ID (use this for token validation)
  "name": "John Doe",
  "is_active": true,  // ← User is fully active
  ...
}
```

**Client Implementation:**
1. After profile completion, call `GET /api/auth/profile`
2. Check `is_active` field
3. If `false`: Show waitlist screen, allow profile editing only
4. If `true`: Enable all app features, navigate to home
5. Periodically check `is_active` status (every 5-10 minutes) to detect promotion

#### 6. Promotion Notification

When a user is automatically promoted from waitlist, they receive a push notification:

**Notification Details:**
- **Title:** "Welcome to Loopin!"
- **Message:** "Your account is now active. Start exploring events and connecting with your community!"
- **Type:** System notification
- **Data:** Includes `target_screen: 'home'` and `type: 'account_activated'`

**Note:** Notification is non-blocking. Promotion succeeds even if notification fails.

### Waitlist Flow Diagram

```mermaid
graph TD
    A[User completes profile] --> B{First time?}
    B -->|Yes| C[Place on waitlist]
    B -->|No| D[Profile update only]
    
    C --> E[Set is_active = false]
    E --> F[Set waitlist_started_at = now]
    F --> G[Set waitlist_promote_at = now + random 66-81 min]
    G --> H[User can only access profile endpoints]
    
    H --> I[User makes API request]
    I --> J{waitlist_promote_at <= now?}
    J -->|No| K[Return 403 for blocked endpoints]
    J -->|Yes| L[Promote to active]
    
    L --> M[Set is_active = true]
    M --> N[Clear waitlist fields]
    N --> O[Send welcome notification]
    O --> P[User can access all features]
    
    K --> I
    
    style C fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style E fill:#ffebee,stroke:#d32f2f,stroke-width:2px
    style L fill:#e8f5e9,stroke:#388e3c,stroke-width:3px
    style P fill:#c8e6c9,stroke:#388e3c,stroke-width:3px
```

### Best Practices for Mobile Apps

#### 1. Waitlist Screen Design

**Show:**
- Clear message: "Your account is being activated. This usually takes 1-2 hours."
- Progress indicator or estimated time remaining
- Option to edit profile
- Periodic status check indicator

**Don't Show:**
- Exact promotion time (it's randomized)
- Confusing error messages
- Blocked features without explanation

#### 2. Status Checking

**Recommended Frequency:**
- Every 5-10 minutes while app is active
- On app foreground/background transitions
- When user navigates to profile screen
- After profile updates

**Implementation:**
```javascript
// Pseudo-code example
function checkWaitlistStatus() {
  const profile = await getProfile();
  if (!profile.is_active) {
    showWaitlistScreen();
    // Check again in 5 minutes
    setTimeout(checkWaitlistStatus, 5 * 60 * 1000);
  } else {
    hideWaitlistScreen();
    enableAllFeatures();
  }
}
```

#### 3. User Experience

**Do:**
- Allow profile editing during waitlist
- Show clear messaging about what they can/can't do
- Celebrate when account becomes active

**Don't:**
- Block profile editing
- Show technical error messages
- Make users feel like they did something wrong
- Require manual refresh to check status

### Waitlist Metrics (Admin)

Admins can view waitlist metrics in the Django admin panel:
- Total waitlisted users
- Users scheduled for promotion
- Average waitlist duration
- Promotion trends over time

Access via: Django Admin → Analytics → Waitlist Metrics

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
    slug = models.SlugField(max_length=100, unique=True, blank=True, help_text="URL-friendly slug")
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
TWILIO_MESSAGING_SERVICE_SID_SMS=your-sms-messaging-service-sid
TWILIO_MESSAGING_SERVICE_SID_WHATSAPP=your-whatsapp-messaging-service-sid
TWILIO_PHONE_NUMBER=+15005550006
TWILIO_TEST_MODE=false  # true for development

# WhatsApp Configuration (for host leads notifications)
TWILIO_WHATSAPP_PHONE_NUMBER=+15558015045
TWILIO_WHATSAPP_CONTENT_SID=your-content-template-sid
ENABLE_WHATSAPP_NOTIFICATIONS=true

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

## 📱 Mobile App Integration Guide

### Overview for iOS and Android Developers

This section provides a comprehensive guide for integrating the Loopin Backend authentication system into your iOS (Swift/SwiftUI) or Android (Kotlin/Java) mobile applications. The integration follows a simple 3-step process that works identically for both platforms.

---

### 🎯 Integration Architecture

**Base URL:** `https://loopinbackend-g17e.onrender.com/api/`

**Authentication Flow:**
1. **Send OTP** → User enters phone number
2. **Verify OTP** → User enters 4-digit code
3. **Complete Profile** → User fills profile (if needed)

**Key Concept:** The backend handles all business logic. Your app only needs to:
- Collect user input
- Make HTTP requests
- Handle responses
- Navigate based on flags

---

### 📋 Step-by-Step Integration

#### **STEP 1: Send OTP (Universal Entry Point)**

**Purpose:** Send a 4-digit OTP to the user's phone number. Works for both new users (signup) and existing users (login).

**When to Call:** When user enters their phone number on the login/signup screen.

**Endpoint:** `POST /api/auth/signup`

**Request Details:**
- **Method:** POST
- **Content-Type:** application/json
- **Authentication:** Not required (public endpoint)

**Request Payload:**
```json
{
  "phone_number": "+1234567890"
}
```

**⚠️ Security Warning:**
- **ONLY** `phone_number` field is accepted by the backend
- Any additional fields (name, email, etc.) in the request payload are **completely ignored**
- This is a security feature to prevent data injection before authentication
- Profile information is collected **after** OTP verification in a separate endpoint

**Payload Fields:**
- `phone_number` (string, required): User's phone number with country code
  - Format: E.164 international format (e.g., +1 for USA, +91 for India)
  - Must include the `+` prefix
  - Can include spaces, dashes, or parentheses (backend normalizes)
  - Examples: `+1234567890`, `+1 (234) 567-8900`, `+1-234-567-8900`

**Success Response (HTTP 200):**
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

**Response Fields Explained:**
- `success` (boolean): Always check this first - `true` means operation succeeded
- `message` (string): User-friendly message to display in your app
- `data.phone_number` (string): Normalized phone number (use this for next step)
- `data.user_status` (string): Either `"new"` (signup) or `"existing"` (login)
- `data.otp_sent` (boolean): Confirms OTP was sent via SMS
- `token` (null): No token at this stage

**Error Responses (HTTP 200 with success: false):**

**Invalid Phone Format:**
```json
{
  "success": false,
  "message": "Invalid phone number format",
  "data": null,
  "token": null
}
```

**SMS Send Failure:**
```json
{
  "success": false,
  "message": "Failed to send OTP. Please try again later.",
  "data": null,
  "token": null
}
```

**Server Error:**
```json
{
  "success": false,
  "message": "An unexpected error occurred. Please try again later.",
  "data": null,
  "token": null
}
```

**App Implementation Steps:**
1. Validate phone number format in your app (basic check)
2. Show loading indicator
3. Make POST request to `/api/auth/signup`
4. Parse JSON response
5. Check `success` field:
   - If `true`: Navigate to OTP verification screen, show success message
   - If `false`: Show error message from `message` field, keep user on same screen
6. Store `phone_number` from response for next step
7. Start 10-minute countdown timer (OTP expires in 10 minutes)

**UI/UX Recommendations:**
- Show "Sending OTP..." loading state
- Display success message: "OTP sent! Check your phone"
- Show countdown timer: "OTP expires in 09:45"
- Provide "Resend OTP" button (calls same endpoint again)
- Handle network errors gracefully

---

#### **STEP 2: Verify OTP (Authentication)**

**Purpose:** Verify the 4-digit OTP code sent to user's phone. Creates account for new users, logs in existing users.

**When to Call:** When user enters the 4-digit OTP code received via SMS.

**Endpoint:** `POST /api/auth/verify-otp`

**Request Details:**
- **Method:** POST
- **Content-Type:** application/json
- **Authentication:** Not required (public endpoint)

**Request Payload:**
```json
{
  "phone_number": "+1234567890",
  "otp_code": "1234"
}
```

**Payload Fields:**
- `phone_number` (string, required): Same phone number from Step 1
- `otp_code` (string, required): 4-digit OTP code entered by user
  - Must be exactly 4 digits
  - Only numeric characters (0-9)
  - Case-sensitive (though always numeric)

**Success Response - Profile Incomplete (HTTP 200):**
```json
{
  "success": true,
  "message": "OTP verified successfully. Please complete your profile to continue.",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoxMjMsInBob25lX251bWJlciI6IisxMjM0NTY3ODkwIiwiZXhwIjoxNzM1Njg5NjAwLCJpYXQiOjE3MzMwOTc2MDB9.signature",
  "data": {
    "user_id": 123,
    "phone_number": "+1234567890",
    "needs_profile_completion": true,
    "is_verified": true
  }
}
```

**Success Response - Profile Complete (HTTP 200):**
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

**Response Fields Explained:**
- `success` (boolean): `true` means OTP verified successfully
- `message` (string): Display this to user
- `token` (string): **CRITICAL** - JWT authentication token, store securely
  - Valid for 30 days
  - Required for all authenticated endpoints
  - Store in secure storage (Keychain for iOS, EncryptedSharedPreferences for Android)
- `data.user_id` (integer): Unique user identifier
- `data.phone_number` (string): Verified phone number
- `data.needs_profile_completion` (boolean): **CRITICAL DECISION FLAG**
  - `true`: Navigate to profile completion screen
  - `false`: Navigate to home screen (user is fully authenticated)
- `data.is_verified` (boolean): Confirms phone verification status

**Error Responses:**

**No Phone Number:**
```json
{
  "success": false,
  "message": "Phone number is required",
  "data": null,
  "token": null
}
```

**No OTP Code:**
```json
{
  "success": false,
  "message": "OTP code is required",
  "data": null,
  "token": null
}
```

**OTP Not Found:**
```json
{
  "success": false,
  "message": "No OTP found for this phone number. Please request a new OTP.",
  "data": null,
  "token": null
}
```

**Invalid OTP (Wrong Code):**
```json
{
  "success": false,
  "message": "Invalid OTP. 2 attempts remaining",
  "data": null,
  "token": null
}
```

**OTP Expired:**
```json
{
  "success": false,
  "message": "OTP has expired. Please request a new OTP.",
  "data": null,
  "token": null
}
```

**Too Many Attempts:**
```json
{
  "success": false,
  "message": "Too many attempts. Please request a new OTP",
  "data": null,
  "token": null
}
```

**App Implementation Steps:**
1. Collect 4-digit OTP from user input
2. Validate OTP format locally (4 digits, numeric only)
3. Show loading indicator
4. Make POST request to `/api/auth/verify-otp`
5. Parse JSON response
6. Check `success` field:
   - If `false`: Show error message, allow retry (unless "too many attempts")
   - If `true`: Proceed to step 7
7. **Store JWT token securely** (Keychain/EncryptedSharedPreferences)
8. Check `needs_profile_completion` flag:
   - If `true`: Navigate to profile completion screen
   - If `false`: Navigate to home screen (user is logged in)
9. Store `user_id` for future use

**Security Best Practices:**
- Store JWT token in secure storage (never in UserDefaults/SharedPreferences)
- iOS: Use Keychain Services
- Android: Use EncryptedSharedPreferences
- Never log the token
- Clear token on logout

**UI/UX Recommendations:**
- Show "Verifying..." loading state
- Disable submit button during verification
- Show remaining attempts on error
- Auto-navigate on success
- Provide "Resend OTP" option on errors

---

#### **STEP 3: Get Event Interests (Optional but Recommended)**

**Purpose:** Fetch list of available event interest categories for user selection during profile completion.

**When to Call:** 
- When showing profile completion screen
- Before user starts filling the profile form
- Can be called in background while user reads instructions

**Endpoint:** `GET /api/auth/event-interests`

**Request Details:**
- **Method:** GET
- **Content-Type:** Not required (GET request)
- **Authentication:** Not required (public endpoint)
- **Body:** No request body needed

**Success Response (HTTP 200):**
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

**Response Fields Explained:**
- `success` (boolean): Always `true` for successful fetch
- `message` (string): Confirmation message
- `data` (array): List of event interest objects
  - `id` (integer): Unique identifier (use this in profile completion)
  - `name` (string): Display name for the interest
  - `description` (string): Detailed description (optional to show)

**Error Response (Rare):**
```json
{
  "success": false,
  "message": "An error occurred while fetching event interests",
  "data": null
}
```

**App Implementation Steps:**
1. Make GET request when profile completion screen loads
2. Parse JSON response
3. Check `success` field
4. Extract `data` array
5. Display interests as selectable items (checkboxes, chips, or cards)
6. Allow user to select 1-5 interests
7. Store selected interest IDs for Step 4
8. Show validation: "Select at least 1 interest" if none selected
9. Show validation: "Maximum 5 interests allowed" if more than 5 selected

**UI/UX Recommendations:**
- Display as grid of cards with icons
- Show interest name and description
- Use multi-select UI (checkboxes or toggle buttons)
- Highlight selected interests
- Show counter: "3 of 5 selected"
- Disable selection when 5 are selected
- Cache this data (rarely changes)

---

#### **STEP 4: Complete Profile (Required for New Users)**

**Purpose:** Complete user profile with personal information, interests, and pictures.

**When to Call:** 
- Only if `needs_profile_completion = true` from Step 2
- After user fills the profile completion form
- Before allowing access to main app features

**Endpoint:** `POST /api/auth/complete-profile`

**Request Details:**
- **Method:** POST
- **Content-Type:** multipart/form-data
- **Authentication:** **REQUIRED** - Bearer token from Step 2
- **Headers:** 
  - `Authorization: Bearer <JWT_TOKEN>`
  - `Content-Type: multipart/form-data` (set automatically by client)

**Request Format:**
This endpoint accepts `multipart/form-data` with actual image files. Images are uploaded to Supabase Storage automatically.

**Form Fields:**

**Required Fields:**
- `phone_number` (string): Same phone number from previous steps (must match authenticated user)
- `name` (string): User's full name
  - Minimum: 2 characters
  - Maximum: 100 characters
  - Allowed: Letters, spaces, hyphens, apostrophes only
  - Examples: "Jo Li", "Mary-Jane", "O'Connor"
  
- `birth_date` (string): Date of birth in YYYY-MM-DD format
  - Format: ISO 8601 date format
  - Validation: User must be 16 years or older
  - Example: "2007-01-15" (for someone born January 15, 2007)
  - Calculation: Age calculated from current date
  
- `gender` (string): User's gender
  - Allowed values: `"male"`, `"female"`, `"other"`
  - Case-insensitive (backend converts to lowercase)
  - Display as dropdown or radio buttons
  
- `event_interests` (string): JSON string array of selected event interest IDs
  - Format: JSON string (e.g., `"[1,3,5]"`)
  - Minimum: 1 interest
  - Maximum: 5 interests
  - Must be valid IDs from Step 3 (event-interests endpoint)
  - Backend validates each ID exists and is active
  - Example: `"[1, 3, 5]"` means Music, Food, Technology
  
- `profile_pictures` (file[]): Actual image files (not URLs)
  - Minimum: 1 picture
  - Maximum: 6 pictures
  - Allowed formats: jpg, jpeg, png, webp
  - Max file size: 5MB per file
  - Files are uploaded to Supabase Storage `user-profiles` bucket
  - Public URLs are automatically generated and stored
  - Example: Upload `image1.jpg`, `image2.png` from device

**Optional Fields:**
- `bio` (string): User's biography or description
  - Maximum: 500 characters
  - Can be empty string or omitted
  - Display as multiline text field
  
- `location` (string): User's location or city
  - Maximum: 100 characters
  - Can be empty string or omitted
  - Example: "New York, USA" or "Mumbai, India"

**Example Request (cURL):**
```bash
curl -X POST "http://localhost:8000/api/auth/complete-profile" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -F "name=John Doe" \
  -F "birth_date=2007-01-15" \
  -F "gender=male" \
  -F "event_interests=[1,3,5,7]" \
  -F "phone_number=+1234567890" \
  -F "bio=Love music and traveling. Always up for new adventures!" \
  -F "location=New York, USA" \
  -F "profile_pictures=@/path/to/image1.jpg" \
  -F "profile_pictures=@/path/to/image2.jpg"
```

**Example Request (JavaScript/Fetch):**
```javascript
const formData = new FormData();
formData.append('name', 'John Doe');
formData.append('birth_date', '2007-01-15');
formData.append('gender', 'male');
formData.append('event_interests', '[1,3,5,7]');  // JSON string
formData.append('phone_number', '+1234567890');
formData.append('bio', 'Love music and traveling');
formData.append('location', 'New York, USA');
formData.append('profile_pictures', file1);  // File object
formData.append('profile_pictures', file2);  // File object

fetch('http://localhost:8000/api/auth/complete-profile', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_JWT_TOKEN'
    // Don't set Content-Type - browser sets it automatically with boundary
  },
  body: formData
});
```

**Success Response (HTTP 200):**
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
  },
  "token": null
}
```

**Response Fields Explained:**
- `success` (boolean): `true` means profile saved successfully
- `message` (string): Success message to display
- `data.user_id` (integer): User's unique ID
- `data.profile_id` (integer): Profile's unique ID
- `data.name` (string): Saved name (confirmation)
- `data.phone_number` (string): User's phone number
- `data.gender` (string): Saved gender
- `data.event_interests_count` (integer): Number of interests saved
- `data.profile_pictures_count` (integer): Number of pictures saved
- `data.profile_complete` (boolean): Always `true` on success

**Error Responses:**

**Token Expired:**
```json
{
  "success": false,
  "message": "Token has expired",
  "data": null,
  "token": null
}
```
**Action:** Navigate user back to login screen

**Invalid Token:**
```json
{
  "success": false,
  "message": "Authentication token is invalid or expired. Please login again.",
  "data": null,
  "token": null
}
```
**Action:** Clear stored token, navigate to login

**Name Too Short:**
```json
{
  "success": false,
  "message": "String should have at least 2 characters",
  "data": null,
  "token": null
}
```
**Action:** Highlight name field, show inline error

**Name Invalid Characters:**
```json
{
  "success": false,
  "message": "Name contains invalid characters",
  "data": null,
  "token": null
}
```
**Action:** Show error: "Name can only contain letters, spaces, hyphens, and apostrophes"

**Age Under 16:**
```json
{
  "success": false,
  "message": "User must be 16 years or older",
  "data": null,
  "token": null
}
```
**Action:** Highlight birth date field, show error message

**Invalid Date Format:**
```json
{
  "success": false,
  "message": "Invalid date format. Use YYYY-MM-DD",
  "data": null,
  "token": null
}
```
**Action:** Show date picker or format example

**Invalid Gender:**
```json
{
  "success": false,
  "message": "Gender must be one of: male, female, other",
  "data": null,
  "token": null
}
```
**Action:** Ensure dropdown/radio buttons only allow valid values

**No Event Interests:**
```json
{
  "success": false,
  "message": "At least one event interest is required",
  "data": null,
  "token": null
}
```
**Action:** Highlight interests section, show error

**Too Many Interests:**
```json
{
  "success": false,
  "message": "List should have at most 5 items after validation",
  "data": null,
  "token": null
}
```
**Action:** Disable selection after 5 interests chosen

**Invalid Interest IDs:**
```json
{
  "success": false,
  "message": "One or more selected event interests (1) are invalid or inactive. Please select from available interests.",
  "data": null,
  "token": null
}
```
**Action:** Refresh interests list from Step 3

**No Profile Pictures:**
```json
{
  "success": false,
  "message": "At least one profile picture is required",
  "data": null,
  "token": null
}
```
**Action:** Highlight picture upload section

**Too Many Pictures:**
```json
{
  "success": false,
  "message": "Maximum 6 profile pictures allowed",
  "data": null,
  "token": null
}
```
**Action:** Disable picture upload after 6 pictures

**Invalid Picture URL:**
```json
{
  "success": false,
  "message": "Invalid URL format for profile picture 1",
  "data": null,
  "token": null
}
```
**Action:** Re-upload the problematic picture

**Bio Too Long:**
```json
{
  "success": false,
  "message": "String should have at most 500 characters",
  "data": null,
  "token": null
}
```
**Action:** Show character counter, trim to 500 characters

**App Implementation Steps:**
1. Retrieve JWT token from secure storage (saved in Step 2)
2. Validate all fields locally before submission:
   - Name: 2-100 characters, letters only
   - Birth date: Calculate age, must be 16+
   - Gender: One of three options
   - Interests: 1-5 selected
   - Pictures: 1-6 uploaded
3. Upload profile pictures to your image storage first
4. Get picture URLs from your storage
5. Build request payload with all data
6. Add Authorization header with Bearer token
7. Make POST request to `/api/auth/complete-profile`
8. Parse JSON response
9. Check `success` field:
   - If `false`: Show specific error message, highlight problematic field
   - If `true`: Proceed to step 10
10. **After successful profile completion:**
    - Call `GET /api/auth/profile` to check waitlist status
    - Check `is_active` field in response:
      - If `false`: User is on waitlist → Show waitlist screen with message: "Your account is being activated. This usually takes 1-2 hours. You can update your profile in the meantime."
      - If `true`: User is active → Navigate to home screen
    - Store `is_active` status in app state
    - Set up periodic check (every 5-10 minutes) to detect automatic promotion
11. Update local user state with profile data

**Image Upload Flow:**
1. User selects pictures from gallery/camera
2. Upload each picture to your image storage (S3, Cloudinary, Firebase Storage)
3. Get public URL for each uploaded picture
4. Store URLs in array
5. Send URLs array in `profile_pictures` field
6. Backend validates URL format but doesn't download images

**UI/UX Recommendations:**
- Show "Completing profile..." loading state
- Validate fields as user types (real-time validation)
- Show character counters (name, bio)
- Show age as user selects birth date
- Disable submit until all required fields valid
- Show progress indicator: "Step 3 of 3"
- Celebrate completion with animation

---

#### **STEP 5: Get User Profile (Authenticated Endpoint)**

**Purpose:** Retrieve complete user profile information after authentication and determine whether the user is currently in the **waitlist** or **active** state.

**When to Call:**
- After successful login (when `needs_profile_completion = false`)
- When user navigates to profile screen
- To refresh profile data
- After profile updates

**Endpoint:** `GET /api/auth/profile`

**Request Details:**
- **Method:** GET
- **Content-Type:** Not required (GET request)
- **Authentication:** **REQUIRED** - Bearer token
- **Headers:** `Authorization: Bearer <JWT_TOKEN>`

**Success Response (HTTP 200):**
```json
{
  "id": 456,
  "user_id": 123,
  "name": "John Doe",
  "phone_number": "+1234567890",
  "gender": "male",
  "bio": "Love music and traveling",
  "location": "New York, USA",
  "birth_date": "2007-01-15",
  "event_interests": [
    {
      "id": 1,
      "name": "Music & Concerts",
      "description": "Live music, concerts, and musical events",
      "is_active": true,
      "created_at": "2025-10-01T00:00:00Z",
      "updated_at": "2025-10-01T00:00:00Z"
    },
    {
      "id": 3,
      "name": "Food & Dining",
      "description": "Food festivals, cooking classes, and dining experiences",
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

**Response Fields Explained:**
- `id` (integer): Profile unique ID (UserProfile.id)
- `user_id` (integer): **User ID (Django User.id) - matches token user_id for validation**
- `name` (string): User's full name
- `phone_number` (string): Verified phone number
- `gender` (string): User's gender
- `bio` (string): User biography (can be empty)
- `location` (string): User location (can be empty)
- `birth_date` (string): ISO format date
- `event_interests` (array): Full interest objects with details
- `profile_pictures` (array): List of picture URLs
- `is_verified` (boolean): Phone verification status
- `is_active` (boolean): **Account active status - CRITICAL for waitlist detection**  
  - **`false`** → User is on **waitlist** (placed after first-time profile completion)
    - User can only access profile endpoints (`GET /api/auth/profile`, `PUT /api/auth/profile`)
    - All other endpoints return `403 FORBIDDEN` with waitlist message
    - Automatic promotion scheduled for 1.10-1.35 hours after profile completion
    - Promotion happens automatically during normal API requests (no background workers)
    - Check this field on app launch and before allowing access to core features
  - **`true`** → User is **fully active** and can use all app features
    - User has been automatically promoted from waitlist
    - Full access to events, payments, attendance, and all other endpoints
    - User received push notification: "Welcome to Loopin! Your account is now active."
- `created_at` (string): Account creation timestamp
- `updated_at` (string): Last update timestamp

**Waitlist Promotion Details:**
- **Promotion Window**: Random delay between 1.10-1.35 hours (66-81 minutes) from profile completion
- **Automatic Promotion**: No manual approval or background workers needed
- **Promotion Trigger**: Happens automatically when user makes any API request after `waitlist_promote_at` time has passed
- **Promotion Check**: Backend checks `waitlist_promote_at` timestamp during normal request flow
- **Notification**: User receives push notification when promoted: "Welcome to Loopin! Your account is now active. Start exploring events and connecting with your community!"
- **Client Action**: Always check `is_active` field before allowing access to core features

**Error Responses:**

**Invalid Token:**
```json
{
  "detail": "Invalid token"
}
```

**Expired Token:**
```json
{
  "detail": "Token has expired"
}
```

**User Not Found:**
```json
{
  "detail": "User not found"
}
```

**Profile Not Found:**
```json
{
  "detail": "User profile not found"
}
```

**App Implementation Steps:**
1. Retrieve JWT token from secure storage
2. Add Authorization header
3. Make GET request to `/api/auth/profile`
4. Parse JSON response
5. Handle errors (401/404):
   - If token expired: Navigate to login
   - If user not found: Clear data, navigate to signup
6. On success: Check `is_active` field
7. **Waitlist Status Handling:**
   - If `is_active = false`: User is on waitlist
     - Show waitlist screen/banner: "Your account is being activated. This usually takes 1-2 hours."
     - Allow access to profile editing only
     - Block access to events, payments, and other core features
     - Set up periodic refresh (every 5-10 minutes) to check for promotion
     - When `is_active` becomes `true`, show success message and enable all features
   - If `is_active = true`: User is fully active
     - Enable all app features
     - Navigate to home screen if coming from waitlist
8. Update local user state with profile data and `is_active` status
9. Display profile data in UI
10. Cache profile data locally
11. Refresh periodically or on pull-to-refresh

---

#### **STEP 6: Logout (Optional)**

**Purpose:** Log out the current user (client-side token removal).

**When to Call:** When user taps logout button.

**Endpoint:** `POST /api/auth/logout`

**Request Details:**
- **Method:** POST
- **Content-Type:** application/json
- **Authentication:** Not strictly required (stateless JWT)

**Success Response (HTTP 200):**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

**App Implementation Steps:**
1. Make POST request to `/api/auth/logout` (optional)
2. **Delete JWT token from secure storage** (required)
3. Clear all user data from memory
4. Clear any cached profile data
5. Reset app state
6. Navigate to login/welcome screen
7. Show "Logged out successfully" message

**Important Note:** Since JWT tokens are stateless, the actual logout happens client-side by deleting the token. The backend endpoint is provided for consistency and future server-side logout logic.

---

### 🔐 Token Management

#### Storing JWT Token

**iOS (Swift):**
- Use Keychain Services
- Store with service identifier: `com.loopin.authToken`
- Access group for app extensions if needed
- Set accessibility: `kSecAttrAccessibleAfterFirstUnlock`

**Android (Kotlin/Java):**
- Use EncryptedSharedPreferences
- Key: `auth_token`
- Master key: Use AndroidKeyStore
- Never store in plain SharedPreferences

#### Using JWT Token

**For All Authenticated Requests:**
1. Retrieve token from secure storage
2. Add to request header: `Authorization: Bearer <token>`
3. Handle 401 errors (token expired):
   - Clear token
   - Navigate to login
   - Show "Session expired" message

**Token Lifecycle:**
- **Issued:** After successful OTP verification (Step 2)
- **Validity:** 30 days from issuance
- **Expiry:** Automatically expires after 30 days
- **Renewal:** User must login again (no refresh tokens)

#### Token Payload (For Reference)

The JWT token contains:
```json
{
  "user_id": 123,
  "phone_number": "+1234567890",
  "exp": 1735689600,
  "iat": 1733097600
}
```

**Fields:**
- `user_id`: User's database ID
- `phone_number`: Verified phone number
- `exp`: Expiration timestamp (Unix epoch)
- `iat`: Issued at timestamp (Unix epoch)

**Note:** You don't need to decode the token in your app. Just store and send it.

---

### 🔄 Complete Integration Flow Summary

#### For New Users (Signup):

**Screen 1: Phone Number Entry**
- User enters phone number
- Call: `POST /api/auth/signup`
- Response: `success: true, otp_sent: true, user_status: "new"`
- Navigate to: OTP verification screen

**Screen 2: OTP Verification**
- User enters 4-digit OTP
- Call: `POST /api/auth/verify-otp`
- Response: `success: true, needs_profile_completion: true, token: "..."`
- Store: JWT token securely
- Navigate to: Profile completion screen

**Screen 3: Event Interests (Background)**
- Call: `GET /api/auth/event-interests`
- Response: Array of 12 interests
- Display: As selectable cards/chips

**Screen 4: Profile Completion**
- User fills form (name, DOB, gender, interests, pictures, bio, location)
- Upload pictures to your storage first
- Call: `POST /api/auth/complete-profile` with Bearer token
- Response: `success: true, profile_complete: true`
- **Check Waitlist Status:**
  - Call: `GET /api/auth/profile` to check `is_active` field
  - If `is_active = false`: Show waitlist screen (user on waitlist)
  - If `is_active = true`: Navigate to home screen (user fully active)
- **Waitlist Handling:**
  - Show message: "Your account is being activated. This usually takes 1-2 hours."
  - Allow profile editing only
  - Periodically check `is_active` status (every 5-10 minutes)
  - When `is_active = true`, show success and navigate to home

#### For Existing Users (Login):

**Screen 1: Phone Number Entry**
- User enters phone number
- Call: `POST /api/auth/signup` (same endpoint!)
- Response: `success: true, otp_sent: true, user_status: "existing"`
- Navigate to: OTP verification screen

**Screen 2: OTP Verification**
- User enters 4-digit OTP
- Call: `POST /api/auth/verify-otp`
- Response: `success: true, needs_profile_completion: false, token: "..."`
- Store: JWT token securely
- Navigate to: Home screen (user is logged in, skip profile completion)

---

### ⚠️ Error Handling Best Practices

#### Network Errors

**No Internet Connection:**
- Detect before making request
- Show: "No internet connection. Please check your network."
- Provide: Retry button

**Timeout:**
- Set timeout: 30 seconds for API calls
- Show: "Request timed out. Please try again."
- Provide: Retry button

**Server Error (500):**
- Show: "Server error. Please try again later."
- Log error for debugging
- Provide: Contact support option

#### Validation Errors

**Client-Side Validation (Before API Call):**
- Phone number: Check format locally
- OTP: Must be 4 digits
- Name: 2-100 characters
- Birth date: Calculate age, must be 16+
- Gender: One of three options
- Interests: 1-5 selected
- Pictures: 1-6 uploaded

**Server-Side Validation (From API Response):**
- Always check `success` field first
- If `false`: Display `message` field to user
- Highlight the problematic field
- Allow user to correct and retry

#### User Experience

**Loading States:**
- Show spinner or progress indicator
- Disable submit buttons during API calls
- Show descriptive text: "Sending OTP...", "Verifying...", "Saving profile..."

**Success States:**
- Show success message briefly
- Use animations for positive feedback
- Auto-navigate after 1-2 seconds
- Provide skip option for impatient users

**Error States:**
- Show error message clearly
- Use red color for errors
- Keep user on same screen
- Allow immediate retry
- Provide help text or examples

---

### 📊 State Management

#### App States to Track

**Authentication State:**
- `NOT_AUTHENTICATED`: No token, show login
- `AUTHENTICATED_INCOMPLETE`: Has token, needs profile
- `AUTHENTICATED_WAITLISTED`: Has token, profile complete, but `is_active = false` (on waitlist)
- `AUTHENTICATED_ACTIVE`: Has token, profile complete, `is_active = true` (fully active)

**User Data State:**
- `user_id`: Store after Step 2
- `phone_number`: Store after Step 1
- `jwt_token`: Store after Step 2 (secure storage)
- `profile_complete`: Boolean flag
- `is_active`: Boolean flag (CRITICAL - determines waitlist vs active status)
- `profile_data`: Full profile object (after Step 5)

#### Navigation Logic

**On App Launch:**
1. Check if JWT token exists in secure storage
2. If no token: Navigate to login screen
3. If token exists:
   - Validate token (check expiry locally if possible)
   - Call `GET /api/auth/profile`
   - If success: Navigate to home screen
   - If 401 error: Clear token, navigate to login

**After OTP Verification:**
1. Check `needs_profile_completion` flag
2. If `true`: Navigate to profile completion
3. If `false`: Navigate to home screen

**After Profile Completion:**
1. Call `GET /api/auth/profile` to check `is_active` status
2. If `is_active = false`: Show waitlist screen, allow profile editing only
3. If `is_active = true`: Navigate to home screen, enable all features
4. Set up periodic check for waitlist promotion (every 5-10 minutes)
5. When `is_active` becomes `true`, show success message and enable all features

---

### 🧪 Testing Your Integration

#### Test Scenarios

**Scenario 1: New User Signup**
1. Enter phone: `+1234567890`
2. Receive OTP via SMS (or check logs if test mode)
3. Enter OTP: `1234`
4. See profile completion screen
5. Fill all fields
6. Submit profile
7. See home screen

**Scenario 2: Existing User Login**
1. Enter phone: `+1234567890` (already registered)
2. Receive OTP via SMS
3. Enter OTP: `1234`
4. Directly see home screen (no profile completion)

**Scenario 3: Invalid OTP**
1. Enter phone: `+1234567890`
2. Enter wrong OTP: `0000`
3. See error: "Invalid OTP. 2 attempts remaining"
4. Try again with correct OTP

**Scenario 4: Profile Validation**
1. Complete Steps 1-2
2. Enter name: "A" (too short)
3. See error: "Name must be at least 2 characters"
4. Correct to: "Jo"
5. Submit successfully

#### Test Mode vs Production

**Test Mode (Development):**
- Set `TWILIO_TEST_MODE=true` in backend
- OTP codes visible in server logs
- No actual SMS sent
- Use for development and testing
- OTP is always: Check logs

**Production Mode:**
- Set `TWILIO_TEST_MODE=false` in backend
- Real SMS sent via Twilio
- OTP codes not in logs
- Use for staging and production
- OTP received on actual phone

---

### 💡 Implementation Tips

#### iOS-Specific Considerations

**Phone Number Input:**
- Use `UITextField` with `keyboardType = .phonePad`
- Format as user types: `+1 (234) 567-8900`
- Store normalized version: `+1234567890`

**OTP Input:**
- Use 4 separate `UITextField` for each digit
- Auto-advance to next field
- Auto-submit when all 4 digits entered
- Use `keyboardType = .numberPad`

**Date Picker:**
- Use `UIDatePicker` with `datePickerMode = .date`
- Set `maximumDate` to 16 years ago
- Format to YYYY-MM-DD before sending

**Image Upload:**
- Use `UIImagePickerController` or `PHPickerViewController`
- Compress images before upload
- Show upload progress
- Handle permissions (camera, photo library)

#### Android-Specific Considerations

**Phone Number Input:**
- Use `EditText` with `inputType="phone"`
- Use `PhoneNumberFormattingTextWatcher` for formatting
- Store normalized version for API

**OTP Input:**
- Use 4 separate `EditText` with `inputType="number"`
- Implement `TextWatcher` for auto-advance
- Use `maxLength="1"` for each field
- Consider SMS auto-read with SMS Retriever API

**Date Picker:**
- Use `DatePickerDialog`
- Set `maxDate` to 16 years ago
- Format using `SimpleDateFormat("yyyy-MM-dd")`

**Image Upload:**
- Use `Intent.ACTION_PICK` or `Intent.ACTION_GET_CONTENT`
- Handle runtime permissions (READ_EXTERNAL_STORAGE)
- Compress images using Bitmap
- Show upload progress with ProgressBar

---

### 🔧 Common Integration Issues

#### Issue 1: Token Not Persisting

**Symptom:** User logged out after app restart

**Solution:**
- Ensure token stored in secure storage, not memory
- iOS: Use Keychain, not UserDefaults
- Android: Use EncryptedSharedPreferences, not SharedPreferences
- Verify token retrieval on app launch

#### Issue 2: Profile Pictures Not Uploading

**Symptom:** "Invalid URL format" error

**Solution:**
- Upload images to your storage service first (S3, Cloudinary, Firebase)
- Get public HTTPS URLs
- Validate URLs are accessible
- Ensure URLs start with `https://`
- Test URLs in browser before sending

#### Issue 3: Age Validation Failing

**Symptom:** "User must be 16 years or older" error

**Solution:**
- Calculate age correctly (account for leap years)
- Use current date for calculation
- Format date as YYYY-MM-DD
- Example: Born Oct 11, 2009 → Age 16 (valid)
- Example: Born Oct 12, 2009 → Age 15 (invalid)

#### Issue 4: OTP Not Received

**Symptom:** User doesn't receive SMS

**Solution:**
- Check if backend is in test mode (TWILIO_TEST_MODE)
- Verify phone number format includes country code
- Check Twilio account status (trial vs paid)
- Verify phone number in Twilio console (for trial accounts)
- Check SMS logs in Twilio dashboard

#### Issue 5: "needs_profile_completion" Always True

**Symptom:** User always sees profile screen even after completing

**Solution:**
- Profile is complete only if BOTH `name` AND `profile_pictures` exist
- Verify profile completion API was called successfully
- Check if pictures array is not empty
- Call `GET /api/auth/profile` to verify profile state

#### 6. User Stuck on Waitlist Screen

**Symptom:** User sees waitlist message but `is_active` never becomes `true`

**Solution:**
- Waitlist promotion happens automatically after 1.10-1.35 hours
- Promotion is triggered during normal API requests (no background workers)
- Ensure app periodically calls `GET /api/auth/profile` to check status
- Check `is_active` field in profile response, not just waitlist message
- If more than 2 hours have passed, user should be automatically promoted
- Verify user is making API requests (promotion check happens during requests)

---

### 📱 Platform-Specific Libraries

#### iOS Recommended Libraries

**Networking:**
- Alamofire (HTTP requests)
- URLSession (native, no dependencies)

**JSON Parsing:**
- Codable (native Swift)
- SwiftyJSON (optional)

**Secure Storage:**
- KeychainAccess (wrapper for Keychain)
- Native Keychain Services

**Image Upload:**
- Kingfisher (image loading/caching)
- SDWebImage (alternative)

#### Android Recommended Libraries

**Networking:**
- Retrofit (REST API client)
- OkHttp (HTTP client)
- Volley (alternative)

**JSON Parsing:**
- Gson (Google's JSON library)
- Moshi (modern alternative)
- Kotlin Serialization (for Kotlin)

**Secure Storage:**
- EncryptedSharedPreferences (Jetpack Security)
- AndroidKeyStore (native)

**Image Upload:**
- Glide (image loading/caching)
- Picasso (alternative)
- Coil (Kotlin-first)

---

### ✅ Integration Checklist

#### Before Starting Development

- [ ] Understand the unified flow (signup = login entry point)
- [ ] Review all API endpoints and responses
- [ ] Set up secure token storage
- [ ] Plan image upload strategy
- [ ] Design UI screens (phone entry, OTP, profile completion, home)

#### During Development

- [ ] Implement phone number input with validation
- [ ] Implement OTP input (4 digits)
- [ ] Implement secure token storage
- [ ] Implement image upload to your storage
- [ ] Implement profile form with all validations
- [ ] Handle all error responses
- [ ] Implement loading states
- [ ] Test with test mode backend

#### Before Production

- [ ] Test complete flow end-to-end
- [ ] Test error scenarios (wrong OTP, invalid data)
- [ ] Test token expiry handling
- [ ] Test network error handling
- [ ] Test with real SMS (backend test mode off)
- [ ] Verify secure storage implementation
- [ ] Test logout and re-login flow
- [ ] Performance test (image upload, API calls)

---

### 📞 Support and Resources

**API Documentation:** https://loopinbackend-g17e.onrender.com/api/docs  
**Interactive Testing:** Use Swagger UI at `/api/docs`  
**Backend Status:** https://loopinbackend-g17e.onrender.com/api/health

**For Integration Questions:**
- Review this documentation thoroughly
- Test endpoints using Postman or cURL first
- Check error messages carefully (they're user-friendly)
- Verify request payloads match examples exactly
- Ensure Authorization header format is correct

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
- [ ] Configure WhatsApp Content Template SID
- [ ] Set `ENABLE_WHATSAPP_NOTIFICATIONS=true`
- [ ] Configure proper DATABASE_URL (Supabase)
- [ ] Set strong SECRET_KEY and JWT_SECRET_KEY
- [ ] Run migrations: `python manage.py migrate`
- [ ] Create superuser: `python manage.py createsuperuser`
- [ ] Test complete flow on production

---

## 💬 WhatsApp Notifications for Host Leads

### Overview

The system includes WhatsApp notifications for host lead submissions using Twilio's Content API. When a user submits a host lead via `/api/hosts/become-a-host`, they automatically receive a personalized WhatsApp confirmation message.

### Features

- **Template-Based Messages**: Uses Twilio Content API templates for reliable delivery
- **Personalization**: Messages include the user's first name
- **Fire-and-Forget**: API doesn't fail if WhatsApp message fails
- **Configurable**: Can be disabled via `ENABLE_WHATSAPP_NOTIFICATIONS=false`
- **Opt-in Handling**: System logs opt-in errors gracefully without breaking the API

### Configuration

**Environment Variables:**
```bash
# WhatsApp Configuration
TWILIO_WHATSAPP_PHONE_NUMBER=+15558015045
TWILIO_WHATSAPP_CONTENT_SID=HXda2c524cbbefc8ba4930da8cc4a35350
ENABLE_WHATSAPP_NOTIFICATIONS=true
```

**Template Details:**
- **Content SID**: Configured via `TWILIO_WHATSAPP_CONTENT_SID`
- **Template Message**: "Hello {{1}}, Your LoopinX Circle account setup is complete ✅ To confirm you received this message, please reply with "YES"."
- **Variable 1**: User's first name (auto-populated)

### API Endpoint

**Submit Host Lead:**
```bash
POST /api/hosts/become-a-host
Content-Type: application/json

{
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890",
  "message": "I would like to host events"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Thank you! We'll contact you soon!",
  "data": {
    "lead_id": 1,
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "status": "pending"
  }
}
```

**Note**: WhatsApp message is sent automatically in the background. The API response is returned immediately regardless of WhatsApp delivery status.

### Error Handling

**Common WhatsApp Error Codes:**
- **63016**: Recipient has not opted in to receive WhatsApp messages
- **63007**: Invalid WhatsApp number format or number not registered on WhatsApp
- **63014**: WhatsApp message template not approved or invalid

**Important**: These errors are logged but do not affect the API response. The host lead is still saved successfully.

### Testing

**Local Development:**
```bash
# WhatsApp notifications are disabled in test mode
# Messages are logged but not sent
TWILIO_TEST_MODE=true
ENABLE_WHATSAPP_NOTIFICATIONS=true
```

**Production:**
```bash
# Real WhatsApp messages are sent
TWILIO_TEST_MODE=false
ENABLE_WHATSAPP_NOTIFICATIONS=true
```

---




## 📚 Additional Resources

### Technology Stack
- **FastAPI**: REST API endpoints with automatic documentation
- **Django**: Database models, admin interface, ORM
- **PostgreSQL**: Database (Supabase cloud)
- **Twilio**: SMS OTP delivery and WhatsApp notifications
- **JWT**: Authentication tokens
- **Pydantic**: Request/response validation
- **Docker**: Containerization
- **ASGI**: Async web server (Gunicorn + Uvicorn)

### Useful Links
- **Production API**: https://loopinbackend-g17e.onrender.com/api/
- **API Docs**: https://loopinbackend-g17e.onrender.com/api/docs
- **Admin Panel**: https://loopinbackend-g17e.onrender.com/django/admin/

