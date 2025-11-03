# Users Module Documentation

## Overview
The Users module handles user authentication, profile management, and phone-based authentication with OTP verification.

## Models

### UserProfile
- **Purpose**: Extended user profile with comprehensive user information
- **Key Fields**: name, phone_number, bio, location, birth_date, gender, profile_pictures
- **Validation**: Age verification (16+), name length (2+ characters)
- **Features**: Profile picture management (1-6 images), location tracking

### PhoneOTP
- **Purpose**: OTP verification for phone-based authentication
- **Key Fields**: phone_number, otp_hash, otp_salt, is_verified, attempts, expires_at
- **Security**: Hashed OTP storage, attempt limiting, expiration handling

### EventInterest
- **Purpose**: Dynamic event interest management system
- **Key Fields**: name, slug, description, is_active
- **Features**: Dynamic interest creation, URL-friendly slugs

## Authentication System

### Phone Authentication Flow
1. **Signup/Login**: Unified endpoint for new and existing users
2. **OTP Generation**: 4-digit SMS OTP via Twilio
3. **OTP Verification**: Secure OTP validation with attempt limiting
4. **Profile Completion**: Comprehensive profile setup for new users
5. **JWT Token**: Secure token-based session management

### Security Features
- **OTP Hashing**: Secure OTP storage with salt
- **Attempt Limiting**: Maximum 3 OTP attempts per session
- **Expiration Handling**: 10-minute OTP validity
- **JWT Security**: Secure token-based authentication
- **Input Validation**: Comprehensive request validation

## API Endpoints

### Authentication Endpoints
- **POST /api/auth/signup**: Unified signup/login endpoint
- **POST /api/auth/verify-otp**: OTP verification
- **POST /api/auth/complete-profile**: Profile completion
- **GET /api/auth/profile**: User profile retrieval
- **GET /api/auth/event-interests**: Available event interests

### User Management
- **Profile Updates**: Comprehensive profile management
- **Interest Selection**: Dynamic event interest management
- **Picture Management**: Profile picture upload and management

## Services

### Twilio SMS Service
- **Purpose**: SMS OTP delivery via Twilio
- **Features**: Messaging Service SID support, error handling
- **Configuration**: Test mode and production mode support

## Documentation
- **📱 PHONE_AUTHENTICATION.md**: Complete authentication flow documentation
- **API Examples**: Detailed API usage examples and testing commands
- **Integration Guide**: Mobile app integration instructions

## Integration Points
- **Events Module**: User event participation and hosting
- **Payments Module**: User payment processing
- **Attendances Module**: User attendance tracking
- **Notifications Module**: User notification delivery
- **Audit Module**: User action logging
