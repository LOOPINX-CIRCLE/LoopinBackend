"""
FastAPI router for user authentication with phone number and OTP
"""

from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.security import HTTPBearer
from django.contrib.auth.models import User
from django.conf import settings
from asgiref.sync import sync_to_async
import jwt
from datetime import datetime, timedelta
import logging

from .models import UserProfile, PhoneOTP
from .schemas import (
    PhoneNumberRequest, 
    OTPVerificationRequest, 
    CompleteProfileRequest,
    LoginRequest,
    AuthResponse,
    UserProfileResponse
)
from .services import twilio_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["Authentication"])
security = HTTPBearer()


def create_jwt_token(user_id: int, phone_number: str) -> str:
    """Create JWT token for authenticated user"""
    payload = {
        'user_id': user_id,
        'phone_number': phone_number,
        'exp': datetime.utcnow() + timedelta(days=30),
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def verify_jwt_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


@router.post("/signup", response_model=AuthResponse)
async def signup_with_phone(request: PhoneNumberRequest):
    """
    Step 1: Send OTP to phone number for signup
    """
    try:
        phone_number = request.phone_number
        
        # Check if user already exists (fully registered user)
        existing_user = await sync_to_async(lambda: User.objects.filter(username=phone_number).first())()
        if existing_user:
            # Check if user has completed profile
            try:
                profile = await sync_to_async(lambda: existing_user.profile)()
                if profile and profile.name and profile.email:
                    return AuthResponse(
                        success=False,
                        message="User already exists. Please login instead."
                    )
                else:
                    # User exists but profile is incomplete - continue from where they left off
                    logger.info(f"User {phone_number} exists but profile incomplete, continuing signup process")
            except:
                # User exists but no profile - continue signup process
                logger.info(f"User {phone_number} exists but no profile, continuing signup process")
        
        # Get or create OTP record
        otp_record, created = await sync_to_async(lambda: PhoneOTP.objects.get_or_create(
            phone_number=phone_number
        ))()
        
        # Generate new OTP
        await sync_to_async(lambda: otp_record.generate_otp())()
        await sync_to_async(lambda: otp_record.save())()
        
        # Send OTP via SMS
        success, message = await sync_to_async(lambda: twilio_service.send_otp_sms(phone_number, otp_record.otp_code))()
        
        if success:
            # Check if this is a resume of incomplete signup
            if existing_user:
                message_text = "OTP sent successfully. Please verify to complete your registration."
            else:
                message_text = "OTP sent successfully to your phone number"
                
            return AuthResponse(
                success=True,
                message=message_text,
                data={"phone_number": phone_number}
            )
        else:
            return AuthResponse(
                success=False,
                message=f"Failed to send OTP: {message}"
            )
            
    except Exception as e:
        logger.error(f"Signup error: {e}")
        return AuthResponse(
            success=False,
            message="An error occurred during signup"
        )


@router.post("/verify-otp", response_model=AuthResponse)
async def verify_signup_otp(request: OTPVerificationRequest):
    """
    Step 2: Verify OTP and create user account
    """
    try:
        phone_number = request.phone_number
        otp_code = request.otp_code
        
        # Get OTP record
        otp_record = await sync_to_async(lambda: PhoneOTP.objects.filter(phone_number=phone_number).first())()
        if not otp_record:
            return AuthResponse(
                success=False,
                message="No OTP found for this phone number. Please request a new OTP."
            )
        
        # Verify OTP
        is_valid, message = await sync_to_async(lambda: otp_record.verify_otp(otp_code))()
        
        if is_valid:
            # Check if user already exists (for incomplete signup resume)
            existing_user = await sync_to_async(lambda: User.objects.filter(username=phone_number).first())()
            
            if existing_user:
                # User exists but profile might be incomplete - update existing user
                user = existing_user
                try:
                    # Check if profile exists
                    profile = await sync_to_async(lambda: existing_user.profile)()
                    if not profile:
                        # Create missing profile
                        profile = await sync_to_async(lambda: UserProfile.objects.create(
                            user=user,
                            phone_number=phone_number,
                            is_verified=True
                        ))()
                    else:
                        # Update existing profile verification status
                        profile.is_verified = True
                        await sync_to_async(lambda: profile.save())()
                except:
                    # Profile doesn't exist, create it
                    profile = await sync_to_async(lambda: UserProfile.objects.create(
                        user=user,
                        phone_number=phone_number,
                        is_verified=True
                    ))()
            else:
                # Create new user account
                user = await sync_to_async(lambda: User.objects.create_user(
                    username=phone_number,
                    password=phone_number,  # Simple password, can be improved
                    is_active=True,
                    is_staff=False,
                    is_superuser=False
                ))()
                
                # Create user profile
                profile = await sync_to_async(lambda: UserProfile.objects.create(
                    user=user,
                    phone_number=phone_number,
                    is_verified=True
                ))()
            
            # Generate JWT token
            token = create_jwt_token(user.id, phone_number)
            
            # Check if profile needs completion
            needs_completion = not (profile.name and profile.email)
            
            return AuthResponse(
                success=True,
                message="OTP verified successfully. Please complete your profile." if needs_completion else "OTP verified successfully. You are logged in.",
                token=token,
                data={
                    "user_id": user.id,
                    "phone_number": phone_number,
                    "needs_profile_completion": needs_completion
                }
            )
        else:
            return AuthResponse(
                success=False,
                message=message
            )
            
    except Exception as e:
        logger.error(f"OTP verification error: {e}")
        return AuthResponse(
            success=False,
            message="An error occurred during OTP verification"
        )


@router.post("/complete-profile", response_model=AuthResponse)
async def complete_user_profile(request: CompleteProfileRequest, token: str = Depends(security)):
    """
    Step 3: Complete user profile with additional information
    """
    try:
        # Verify JWT token
        payload = verify_jwt_token(token.credentials)
        user_id = payload['user_id']
        phone_number = payload['phone_number']
        
        # Get user and profile
        user = await sync_to_async(lambda: User.objects.get(id=user_id))()
        profile = await sync_to_async(lambda: UserProfile.objects.get(user=user))()
        
        # Update profile information
        profile.name = request.name
        profile.email = request.email
        profile.bio = request.bio or ""
        profile.location = request.location or ""
        profile.birth_date = request.birth_date
        profile.avatar = request.avatar or ""
        await sync_to_async(lambda: profile.save())()
        
        return AuthResponse(
            success=True,
            message="Profile completed successfully",
            data={
                "user_id": user.id,
                "profile_id": profile.id,
                "name": profile.name,
                "email": profile.email,
                "phone_number": profile.phone_number
            }
        )
        
    except User.DoesNotExist:
        return AuthResponse(
            success=False,
            message="User not found"
        )
    except Exception as e:
        logger.error(f"Profile completion error: {e}")
        return AuthResponse(
            success=False,
            message="An error occurred while completing profile"
        )


@router.post("/login", response_model=AuthResponse)
async def login_with_phone(request: PhoneNumberRequest):
    """
    Login: Send OTP to existing user's phone number
    """
    try:
        phone_number = request.phone_number
        
        # Check if user exists
        user = await sync_to_async(lambda: User.objects.filter(username=phone_number).first())()
        if not user:
            return AuthResponse(
                success=False,
                message="User not found. Please signup first."
            )
        
        # Get or create OTP record
        otp_record, created = await sync_to_async(lambda: PhoneOTP.objects.get_or_create(
            phone_number=phone_number
        ))()
        
        # Generate new OTP
        await sync_to_async(lambda: otp_record.generate_otp())()
        await sync_to_async(lambda: otp_record.save())()
        
        # Send OTP via SMS
        success, message = await sync_to_async(lambda: twilio_service.send_otp_sms(phone_number, otp_record.otp_code))()
        
        if success:
            return AuthResponse(
                success=True,
                message="OTP sent successfully to your phone number",
                data={"phone_number": phone_number}
            )
        else:
            return AuthResponse(
                success=False,
                message=f"Failed to send OTP: {message}"
            )
            
    except Exception as e:
        logger.error(f"Login error: {e}")
        return AuthResponse(
            success=False,
            message="An error occurred during login"
        )


@router.post("/verify-login", response_model=AuthResponse)
async def verify_login_otp(request: LoginRequest):
    """
    Verify login OTP and return JWT token
    """
    try:
        phone_number = request.phone_number
        otp_code = request.otp_code
        
        # Get OTP record
        otp_record = PhoneOTP.objects.filter(phone_number=phone_number).first()
        if not otp_record:
            return AuthResponse(
                success=False,
                message="No OTP found for this phone number. Please request a new OTP."
            )
        
        # Verify OTP
        is_valid, message = otp_record.verify_otp(otp_code)
        
        if is_valid:
            # Get user
            user = User.objects.get(username=phone_number)
            profile = UserProfile.objects.get(user=user)
            
            # Generate JWT token
            token = create_jwt_token(user.id, phone_number)
            
            return AuthResponse(
                success=True,
                message="Login successful",
                token=token,
                data={
                    "user_id": user.id,
                    "phone_number": phone_number,
                    "name": profile.name,
                    "email": profile.email,
                    "is_verified": profile.is_verified
                }
            )
        else:
            return AuthResponse(
                success=False,
                message=message
            )
            
    except User.DoesNotExist:
        return AuthResponse(
            success=False,
            message="User not found"
        )
    except Exception as e:
        logger.error(f"Login verification error: {e}")
        return AuthResponse(
            success=False,
            message="An error occurred during login verification"
        )


@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(token: str = Depends(security)):
    """
    Get current user's profile
    """
    try:
        # Verify JWT token
        payload = verify_jwt_token(token.credentials)
        user_id = payload['user_id']
        
        # Get user and profile
        user = User.objects.get(id=user_id)
        profile = UserProfile.objects.get(user=user)
        
        return UserProfileResponse(
            id=profile.id,
            name=profile.name,
            email=profile.email,
            phone_number=profile.phone_number,
            bio=profile.bio,
            location=profile.location,
            birth_date=profile.birth_date,
            avatar=profile.avatar,
            is_verified=profile.is_verified,
            is_active=profile.is_active,
            created_at=profile.created_at.isoformat(),
            updated_at=profile.updated_at.isoformat()
        )
        
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except Exception as e:
        logger.error(f"Profile retrieval error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving profile")


@router.post("/logout", response_model=AuthResponse)
async def logout():
    """
    Logout user (client should discard token)
    """
    return AuthResponse(
        success=True,
        message="Logged out successfully"
    )
