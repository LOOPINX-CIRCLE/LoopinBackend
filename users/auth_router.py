"""
FastAPI router for user authentication with phone number and OTP
"""

from fastapi import APIRouter, HTTPException, Depends, status, Form, File, UploadFile
from fastapi.security import HTTPBearer
from django.contrib.auth.models import User
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from asgiref.sync import sync_to_async
import jwt
from datetime import datetime, timedelta
import logging
import random
from typing import List, Optional
from datetime import datetime, date
import re

from .models import UserProfile, PhoneOTP, EventInterest
from .schemas import (
    PhoneNumberRequest, 
    OTPVerificationRequest, 
    CompleteProfileRequest,
    LoginRequest,
    AuthResponse,
    UserProfileResponse,
    EventInterestResponse
)
from .services import twilio_service
from core.services.storage import get_storage_service
from core.exceptions import ValidationError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth")
security = HTTPBearer()


def maybe_promote_user_from_waitlist_sync(user_id: int) -> bool:
    """
    Check if a waitlisted user should be promoted to active based on waitlist_promote_at.
    This runs in a DB transaction to ensure atomic promotion and field clearing.
    Returns True if a promotion happened.
    """
    now = timezone.now()

    with transaction.atomic():
        locked_user = User.objects.select_for_update().get(id=user_id)
        profile = UserProfile.objects.select_for_update().get(user=locked_user)

        # If already active, nothing to do
        if locked_user.is_active:
            return False

        # If no promotion time is set or it's still in the future, remain on waitlist
        promote_at = profile.waitlist_promote_at
        if not promote_at or now < promote_at:
            return False

        # Promote to active and clear waitlist fields
        locked_user.is_active = True
        profile.is_active = True
        profile.waitlist_started_at = None
        profile.waitlist_promote_at = None

        locked_user.save(update_fields=["is_active"])
        profile.save(update_fields=["is_active", "waitlist_started_at", "waitlist_promote_at", "updated_at"])

        logger.info(f"User {locked_user.id} promoted from waitlist to active.")
        # TODO: Trigger user notification on promotion (out of scope for current implementation)
        return True


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
    Unified Authentication: Send OTP for both new users and existing users
    
    This endpoint handles both signup and login in a single flow:
    - For new users: Initiates signup process
    - For existing users: Initiates login process
    - Both receive a 4-digit OTP via SMS
    
    Flow:
    1. Validate phone number format
    2. Check if user exists
    3. Generate and send 4-digit OTP
    4. Return success with appropriate message
    """
    try:
        # Validate phone number is provided
        if not request.phone_number:
            return AuthResponse(
                success=False,
                message="Phone number is required"
            )
        
        phone_number = request.phone_number
        
        # Check if user already exists
        existing_user = await sync_to_async(lambda: User.objects.filter(username=phone_number).first())()
        
        # Determine if this is a new user or existing user
        is_new_user = existing_user is None
        user_status = "new" if is_new_user else "existing"
        
        # For existing users, check profile completion status
        has_complete_profile = False
        if existing_user:
            try:
                profile = await sync_to_async(lambda: existing_user.profile)()
                has_complete_profile = bool(profile and profile.name and profile.profile_pictures)
                logger.info(f"Existing user {phone_number} - Profile complete: {has_complete_profile}")
            except Exception as e:
                logger.info(f"User {phone_number} exists but no profile found: {e}")
                has_complete_profile = False
        
        # Get or create OTP record (works for both signup and login)
        otp_record, created = await sync_to_async(lambda: PhoneOTP.objects.get_or_create(
            phone_number=phone_number
        ))()
        
        # Generate new OTP (4 digits)
        await sync_to_async(lambda: otp_record.generate_otp())()
        await sync_to_async(lambda: otp_record.save())()
        
        # Send OTP via SMS
        try:
            success, sms_message, sms_details = await sync_to_async(
                lambda: twilio_service.send_otp_sms(phone_number, otp_record.otp_code)
            )()
        except Exception as sms_error:
            logger.error(f"SMS sending error for {phone_number}: {sms_error}")
            return AuthResponse(
                success=False,
                message="Failed to send OTP. Please try again later."
            )
        
        if success:
            # Create appropriate message based on user status
            if is_new_user:
                message_text = "OTP sent successfully to your phone number. Please verify to complete signup."
            elif has_complete_profile:
                message_text = "OTP sent successfully to your phone number. Please verify to login."
            else:
                message_text = "OTP sent successfully. Please verify to complete your registration."
            
            return AuthResponse(
                success=True,
                message=message_text,
                data={
                    "phone_number": phone_number,
                    "user_status": user_status,
                    "otp_sent": True
                }
            )
        else:
            # SMS failed to send
            logger.error(f"Failed to send OTP to {phone_number}: {sms_message}")
            return AuthResponse(
                success=False,
                message=f"Failed to send OTP. {sms_message}. Please try again."
            )
            
    except ValueError as ve:
        # Validation errors from phone number validator
        logger.error(f"Validation error in signup: {ve}")
        return AuthResponse(
            success=False,
            message=str(ve)
        )
    except Exception as e:
        # Catch-all for any unexpected errors
        import traceback
        error_trace = traceback.format_exc()
        logger.error(f"Unexpected error in signup for {request.phone_number if request.phone_number else 'N/A'}: {e}\n{error_trace}")
        return AuthResponse(
            success=False,
            message=f"An error occurred: {str(e)}. Please check logs for details."
        )


@router.post("/verify-otp", response_model=AuthResponse)
async def verify_signup_otp(request: OTPVerificationRequest):
    """
    Unified OTP Verification: Verify OTP for both signup and login
    
    This endpoint handles OTP verification for:
    - New users (signup): Creates user account and profile
    - Existing users (login): Authenticates and returns token
    - Incomplete profiles: Returns token with needs_profile_completion flag
    
    Flow:
    1. Validate phone number and OTP format
    2. Check if OTP exists and is valid
    3. Verify OTP (checks expiry, attempts, correctness)
    4. Create/authenticate user
    5. Generate JWT token
    6. Return token with profile completion status
    """
    try:
        # Validate required fields
        if not request.phone_number:
            return AuthResponse(
                success=False,
                message="Phone number is required"
            )
        
        if not request.otp_code:
            return AuthResponse(
                success=False,
                message="OTP code is required"
            )
        
        phone_number = request.phone_number
        otp_code = request.otp_code
        
        # Get OTP record
        otp_record = await sync_to_async(lambda: PhoneOTP.objects.filter(phone_number=phone_number).first())()
        
        if not otp_record:
            return AuthResponse(
                success=False,
                message="No OTP found for this phone number. Please request a new OTP."
            )
        
        # Verify OTP (this checks expiry, attempts, and code correctness)
        try:
            is_valid, validation_message = await sync_to_async(lambda: otp_record.verify_otp(otp_code))()
        except Exception as verify_error:
            logger.error(f"OTP verification logic error for {phone_number}: {verify_error}")
            return AuthResponse(
                success=False,
                message="An error occurred while verifying OTP. Please try again."
            )
        
        if not is_valid:
            # OTP verification failed (wrong code, expired, or too many attempts)
            return AuthResponse(
                success=False,
                message=validation_message
            )
        
        # OTP is valid - proceed with user authentication/creation
        try:
            # Check if user already exists
            existing_user = await sync_to_async(lambda: User.objects.filter(username=phone_number).first())()
            
            if existing_user:
                # Existing user - handle login flow
                user = existing_user
                try:
                    # Check if profile exists
                    profile = await sync_to_async(lambda: existing_user.profile)()
                    if not profile:
                        # Create missing profile for existing user
                        profile = await sync_to_async(lambda: UserProfile.objects.create(
                            user=user,
                            phone_number=phone_number,
                            is_verified=True
                        ))()
                        logger.info(f"Created missing profile for existing user {phone_number}")
                    else:
                        # Update verification status
                        profile.is_verified = True
                        await sync_to_async(lambda: profile.save())()
                except Exception as profile_error:
                    # Profile doesn't exist, create it
                    logger.warning(f"Profile access error for {phone_number}: {profile_error}")
                    profile = await sync_to_async(lambda: UserProfile.objects.create(
                        user=user,
                        phone_number=phone_number,
                        is_verified=True
                    ))()
            else:
                # New user - handle signup flow
                try:
                    # Create new user account
                    user = await sync_to_async(lambda: User.objects.create_user(
                        username=phone_number,
                        password=phone_number,  # Password set to phone for simplicity
                        is_active=True,
                        is_staff=False,
                        is_superuser=False
                    ))()
                    logger.info(f"Created new user account for {phone_number}")
                    
                    # Create user profile
                    profile = await sync_to_async(lambda: UserProfile.objects.create(
                        user=user,
                        phone_number=phone_number,
                        is_verified=True
                    ))()
                    logger.info(f"Created new profile for {phone_number}")
                except Exception as creation_error:
                    logger.error(f"Error creating user/profile for {phone_number}: {creation_error}")
                    return AuthResponse(
                        success=False,
                        message="An error occurred while creating your account. Please try again."
                    )
            
            # Generate JWT authentication token
            try:
                token = create_jwt_token(user.id, phone_number)
            except Exception as token_error:
                logger.error(f"Error generating token for user {user.id}: {token_error}")
                return AuthResponse(
                    success=False,
                    message="Authentication successful but token generation failed. Please try again."
                )
            
            # Check if profile needs completion
            # Profile is complete if it has name and at least one profile picture
            needs_completion = not (profile.name and profile.profile_pictures)
            
            # Create appropriate success message
            if needs_completion:
                message_text = "OTP verified successfully. Please complete your profile to continue."
            else:
                message_text = "OTP verified successfully. You are logged in."
            
            return AuthResponse(
                success=True,
                message=message_text,
                token=token,
                data={
                    "user_id": user.id,
                    "phone_number": phone_number,
                    "needs_profile_completion": needs_completion,
                    "is_verified": True
                }
            )
            
        except User.DoesNotExist:
            logger.error(f"User not found during verification for {phone_number}")
            return AuthResponse(
                success=False,
                message="User account error. Please try signing up again."
            )
            
    except ValueError as ve:
        # Validation errors from request model
        logger.error(f"Validation error in verify-otp: {ve}")
        return AuthResponse(
            success=False,
            message=str(ve)
        )
    except Exception as e:
        # Catch-all for any unexpected errors
        logger.error(f"Unexpected error in verify-otp for {request.phone_number if request.phone_number else 'N/A'}: {e}")
        return AuthResponse(
            success=False,
            message="An unexpected error occurred during verification. Please try again later."
        )


@router.post("/complete-profile", response_model=AuthResponse)
async def complete_user_profile(
    # Form fields
    name: str = Form(...),
    birth_date: str = Form(...),
    gender: str = Form(...),
    event_interests: str = Form(...),  # JSON string of list
    phone_number: str = Form(...),
    bio: Optional[str] = Form(None),
    location: Optional[str] = Form(None),
    # File uploads
    profile_pictures: List[UploadFile] = File(...),
    # Authentication
    token: str = Depends(security)
):
    """
    Complete User Profile: Add additional profile information after OTP verification
    
    This endpoint handles profile completion for users who have verified their phone:
    - Requires valid JWT token from /verify-otp endpoint
    - Accepts multipart/form-data with actual image files
    - Uploads profile pictures to Supabase Storage (user-profiles bucket)
    - Validates all profile data (name, age, gender, interests, pictures)
    - Updates user profile with complete information
    
    Required fields (multipart/form-data):
    - name (2-100 characters, letters only)
    - birth_date (YYYY-MM-DD, must be 16+)
    - gender (male/female/other)
    - event_interests (JSON string array of 1-5 interest IDs, e.g. "[1,2,3]")
    - phone_number (must match authenticated user)
    - profile_pictures (1-6 image files: jpg, jpeg, png, webp, max 5MB each)
    
    Optional fields:
    - bio (max 500 characters)
    - location (max 100 characters)
    """
    try:
        # Verify JWT token
        try:
            payload = verify_jwt_token(token.credentials)
            user_id = payload.get('user_id')
            token_phone = payload.get('phone_number')
            
            if not user_id or not token_phone:
                return AuthResponse(
                    success=False,
                    message="Invalid authentication token. Please login again."
                )
        except HTTPException as he:
            return AuthResponse(
                success=False,
                message=he.detail
            )
        except Exception as token_error:
            logger.error(f"Token verification error: {token_error}")
            return AuthResponse(
                success=False,
                message="Authentication token is invalid or expired. Please login again."
            )
        
        # Validate phone number matches token
        if phone_number != token_phone:
            return AuthResponse(
                success=False,
                message="Phone number does not match authenticated user."
            )
        
        # Validate name
        if not name or not name.strip():
            return AuthResponse(
                success=False,
                message="Name cannot be empty"
            )
        name_trimmed = name.strip()
        if len(name_trimmed) < 2:
            return AuthResponse(
                success=False,
                message="Name must be at least 2 characters long"
            )
        # Check for valid characters (letters, spaces, hyphens, apostrophes)
        if not re.match(r"^[a-zA-Z\s\-\']+$", name_trimmed):
            return AuthResponse(
                success=False,
                message="Name contains invalid characters. Only letters, spaces, hyphens, and apostrophes are allowed"
            )
        
        # Validate birth_date format and age
        try:
            birth_date_obj = datetime.strptime(birth_date, '%Y-%m-%d').date()
            today = date.today()
            age = today.year - birth_date_obj.year - ((today.month, today.day) < (birth_date_obj.month, birth_date_obj.day))
            if age < 16:
            return AuthResponse(
                success=False,
                    message="User must be 16 years or older"
            )
        except ValueError as e:
            if 'time data' in str(e):
                return AuthResponse(
                    success=False,
                    message="Invalid date format. Use YYYY-MM-DD"
                )
            return AuthResponse(
                success=False,
                message=f"Invalid birth date: {str(e)}"
            )
        
        # Validate gender
        valid_genders = ['male', 'female', 'other']
        gender_lower = gender.lower()
        if gender_lower not in valid_genders:
            return AuthResponse(
                success=False,
                message=f"Gender must be one of: {', '.join(valid_genders)}"
            )
        
        # Validate profile pictures count
        if not profile_pictures or len(profile_pictures) == 0:
            return AuthResponse(
                success=False,
                message="At least one profile picture is required"
            )
        
        if len(profile_pictures) > 6:
            return AuthResponse(
                success=False,
                message="Maximum 6 profile pictures allowed"
            )
        
        # Parse event interests from JSON string
        import json
        try:
            event_interest_ids = json.loads(event_interests)
            if not isinstance(event_interest_ids, list):
                raise ValueError("event_interests must be a JSON array")
            if len(event_interest_ids) == 0:
                return AuthResponse(
                    success=False,
                    message="At least one event interest is required"
                )
            if len(event_interest_ids) > 5:
                return AuthResponse(
                    success=False,
                    message="Maximum 5 event interests allowed"
                )
        except (json.JSONDecodeError, ValueError) as e:
            return AuthResponse(
                success=False,
                message=f"Invalid event_interests format: {str(e)}. Expected JSON array."
            )
        
        # Get user and profile
        try:
            user = await sync_to_async(lambda: User.objects.get(id=user_id))()
        except User.DoesNotExist:
            return AuthResponse(
                success=False,
                message="User account not found. Please signup again."
            )
        
        try:
            profile = await sync_to_async(lambda: UserProfile.objects.get(user=user))()
        except UserProfile.DoesNotExist:
            return AuthResponse(
                success=False,
                message="User profile not found. Please contact support."
            )

        # Determine if this call is completing the profile for the first time
        was_incomplete_before = not (profile.name and profile.profile_pictures)
        
        # Validate event interests exist and are active
        try:
            event_interests = await sync_to_async(lambda: list(EventInterest.objects.filter(
                id__in=event_interest_ids, 
                is_active=True
            )))()
        except Exception as interest_error:
            logger.error(f"Error fetching event interests: {interest_error}")
            return AuthResponse(
                success=False,
                message="An error occurred while validating event interests. Please try again."
            )
        
        # Check if all requested interests were found and are active
        if len(event_interests) != len(event_interest_ids):
            missing_count = len(event_interest_ids) - len(event_interests)
            return AuthResponse(
                success=False,
                message=f"One or more selected event interests ({missing_count}) are invalid or inactive. Please select from available interests."
            )
        
        # Upload profile pictures to Supabase Storage
        try:
            storage_service = get_storage_service()
            uploaded_urls = await storage_service.upload_multiple_files(
                files=profile_pictures,
                bucket="user-profiles",
                user_id=profile.id,  # Use UserProfile.id (normal user ID, not admin User.id)
                folder=None
            )
            
            if not uploaded_urls or len(uploaded_urls) == 0:
                return AuthResponse(
                    success=False,
                    message="Failed to upload profile pictures. Please try again."
                )
            
            logger.info(f"Uploaded {len(uploaded_urls)} profile pictures for user {user_id}")
            
        except ValidationError as ve:
            return AuthResponse(
                success=False,
                message=ve.message
            )
        except Exception as upload_error:
            logger.error(f"Error uploading profile pictures: {upload_error}", exc_info=True)
            return AuthResponse(
                success=False,
                message="An error occurred while uploading profile pictures. Please check file formats and sizes."
            )
        
        # Update profile information
        try:
            profile.name = name_trimmed  # Already validated and trimmed above
            profile.birth_date = birth_date_obj  # Already validated and parsed above
            profile.gender = gender_lower  # Already validated above
            profile.profile_pictures = uploaded_urls  # Use uploaded URLs
            profile.bio = bio.strip() if bio else ""
            profile.location = location.strip() if location else ""
            
            # Save profile first
            await sync_to_async(lambda: profile.save())()
            logger.info(f"Profile updated for user {user_id}")
            
            # Set event interests (ManyToMany relationship)
            await sync_to_async(lambda: profile.event_interests.set(event_interests))()
            logger.info(f"Event interests set for user {user_id}: {len(event_interests)} interests")
            
        except Exception as save_error:
            logger.error(f"Error saving profile for user {user_id}: {save_error}")
            return AuthResponse(
                success=False,
                message="An error occurred while saving your profile. Please try again."
            )
        
        # If this was the first time the profile became complete, place user into waitlist
        # by marking the Django User as inactive and scheduling a promotion time.
        if was_incomplete_before:
            now = timezone.now()
            # Random delay between 3.5 and 4 hours (210–240 minutes)
            delay_minutes = random.randint(210, 240)
            promote_at = now + timedelta(minutes=delay_minutes)

            # Mark auth user as inactive for waitlist duration
            user.is_active = False
            await sync_to_async(lambda: user.save(update_fields=["is_active"]))()

            # Mirror waitlist state on profile for analytics/inspection
            profile.is_active = False
            profile.waitlist_started_at = now
            profile.waitlist_promote_at = promote_at
            await sync_to_async(
                lambda: profile.save(
                    update_fields=["is_active", "waitlist_started_at", "waitlist_promote_at", "updated_at"]
                )
            )()

            logger.info(
                f"User {user.id} placed on waitlist after first profile completion. "
                f"Promotion scheduled at {promote_at.isoformat()}."
            )
        
        # Return success with profile details
        return AuthResponse(
            success=True,
            message="Profile completed successfully. You can now use the app!",
            data={
                "user_id": user.id,
                "profile_id": profile.id,
                "name": profile.name,
                "phone_number": profile.phone_number,
                "gender": profile.gender,
                "event_interests_count": len(event_interests),
                "profile_pictures_count": len(profile.profile_pictures),
                "profile_complete": True
            }
        )
        
    except ValueError as ve:
        # Validation errors from request model validators
        logger.error(f"Validation error in complete-profile: {ve}")
        return AuthResponse(
            success=False,
            message=str(ve)
        )
    except Exception as e:
        # Catch-all for any unexpected errors
        logger.error(f"Unexpected error in complete-profile for user {user_id if 'user_id' in locals() else 'N/A'}: {e}")
        return AuthResponse(
            success=False,
            message="An unexpected error occurred while completing your profile. Please try again later."
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
        success, message, sms_details = await sync_to_async(lambda: twilio_service.send_otp_sms(phone_number, otp_record.otp_code))()
        
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
        otp_record = await sync_to_async(lambda: PhoneOTP.objects.filter(phone_number=phone_number).first())()
        if not otp_record:
            return AuthResponse(
                success=False,
                message="No OTP found for this phone number. Please request a new OTP."
            )
        
        # Verify OTP
        is_valid, message = await sync_to_async(lambda: otp_record.verify_otp(otp_code))()
        
        if is_valid:
            # Get user
            user = await sync_to_async(lambda: User.objects.get(username=phone_number))()
            profile = await sync_to_async(lambda: UserProfile.objects.get(user=user))()
            
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
        user = await sync_to_async(lambda: User.objects.get(id=user_id))()
        profile = await sync_to_async(lambda: UserProfile.objects.get(user=user))()

        # Automatic waitlist promotion check based on waitlist_promote_at.
        # This allows users to be promoted during normal request flow without background workers.
        try:
            promoted = await sync_to_async(maybe_promote_user_from_waitlist_sync)(user_id)
            if promoted:
                # Refresh instances to reflect new active state
                user = await sync_to_async(lambda: User.objects.get(id=user_id))()
                profile = await sync_to_async(lambda: UserProfile.objects.get(user=user))()
        except Exception as promote_error:
            logger.error(f"Waitlist promotion check failed for user {user_id}: {promote_error}")
        
        # Fetch event interests
        event_interests_qs = await sync_to_async(lambda: list(profile.event_interests.filter(is_active=True).order_by('name')))()
        event_interests_data = [
            EventInterestResponse(
                id=interest.id,
                name=interest.name,
                is_active=interest.is_active,
                created_at=interest.created_at.isoformat(),
                updated_at=interest.updated_at.isoformat()
            ) for interest in event_interests_qs
        ]
        
        return UserProfileResponse(
            id=profile.id,
            name=profile.name,
            phone_number=profile.phone_number,
            gender=profile.gender,
            bio=profile.bio,
            location=profile.location,
            birth_date=profile.birth_date.isoformat() if profile.birth_date else None,
            event_interests=event_interests_data,
            profile_pictures=profile.profile_pictures,
            is_verified=profile.is_verified,
            # Expose Django User.is_active so clients can distinguish waitlisted vs active accounts
            is_active=user.is_active,
            created_at=profile.created_at.isoformat(),
            updated_at=profile.updated_at.isoformat()
        )
        
    except User.DoesNotExist:
        raise HTTPException(status_code=404, detail="User not found")
    except UserProfile.DoesNotExist:
        raise HTTPException(status_code=404, detail="User profile not found")
    except Exception as e:
        logger.error(f"Profile retrieval error: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while retrieving profile")


@router.get("/event-interests", response_model=dict)
async def get_event_interests(token: str = Depends(security)):
    """
    Get all active event interests for profile completion.
    
    **Authentication Required**: JWT token must be provided.
    """
    try:
        # Verify JWT token
        payload = verify_jwt_token(token.credentials)
        user_id = payload['user_id']
        
        # Verify user exists and is active
        user = await sync_to_async(lambda: User.objects.get(id=user_id))()
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inactive user"
            )
        
        event_interests = await sync_to_async(lambda: list(EventInterest.objects.filter(is_active=True).order_by('name')))()
        
        interests_data = [
            {
                "id": interest.id,
                "name": interest.name
            }
            for interest in event_interests
        ]
        
        return {
            "success": True,
            "message": "Event interests retrieved successfully",
            "data": interests_data
        }
        
    except HTTPException:
        raise
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    except Exception as e:
        logger.error(f"Error fetching event interests: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve event interests"
        )


@router.post("/logout", response_model=AuthResponse)
async def logout():
    """
    Logout user (client should discard token)
    """
    return AuthResponse(
        success=True,
        message="Logged out successfully"
    )
