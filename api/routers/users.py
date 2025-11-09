"""
User management router for FastAPI.
Handles user profiles, preferences, and user-related operations.
"""

from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr
from django.contrib.auth.models import User
from django.conf import settings
from asgiref.sync import sync_to_async
import logging

from core.utils.logger import get_logger
from core.permissions import PermissionChecker, RoleBasedPermission
from core.exceptions import AuthorizationError, NotFoundError

logger = get_logger(__name__)
router = APIRouter()

# JWT token scheme
security = HTTPBearer()


# Pydantic models
class UserProfileResponse(BaseModel):
    id: int
    username: str
    email: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    is_active: bool
    date_joined: datetime
    last_login: Optional[datetime]


class UserProfileUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None


class UserPreferences(BaseModel):
    notifications_enabled: bool = True
    email_notifications: bool = True
    sms_notifications: bool = False
    privacy_level: str = "public"  # public, friends, private


class UserPreferencesUpdate(BaseModel):
    notifications_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    sms_notifications: Optional[bool] = None
    privacy_level: Optional[str] = None


# Dependency to get current user
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """
    Get current authenticated user from JWT token.
    
    Args:
        credentials: JWT token credentials
        
    Returns:
        Authenticated user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    try:
        # Decode JWT token
        payload = jwt.decode(
            credentials.credentials,
            settings.SECRET_KEY,
            algorithms=["HS256"]
        )
        user_id = payload.get("user_id")
        
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Get user from database
        user = await sync_to_async(User.objects.get)(id=user_id)
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User account is disabled"
            )
        
        return user
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token"
        )
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


# API Endpoints
@router.get("/profile", response_model=UserProfileResponse)
async def get_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get current user's profile information.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User profile information
    """
    logger.info(f"Getting profile for user {current_user.id}")
    
    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        date_joined=current_user.date_joined,
        last_login=current_user.last_login
    )


@router.put("/profile", response_model=UserProfileResponse)
async def update_user_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update current user's profile information.
    
    Args:
        profile_data: Profile data to update
        current_user: Current authenticated user
        
    Returns:
        Updated user profile information
    """
    logger.info(f"Updating profile for user {current_user.id}")
    
    # Update user fields
    if profile_data.first_name is not None:
        current_user.first_name = profile_data.first_name
    if profile_data.last_name is not None:
        current_user.last_name = profile_data.last_name
    if profile_data.email is not None:
        current_user.email = profile_data.email
    
    # Save user
    await sync_to_async(current_user.save)()
    
    return UserProfileResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        date_joined=current_user.date_joined,
        last_login=current_user.last_login
    )


@router.get("/preferences", response_model=UserPreferences)
async def get_user_preferences(current_user: User = Depends(get_current_user)):
    """
    Get current user's preferences.
    
    Args:
        current_user: Current authenticated user
        
    Returns:
        User preferences
    """
    logger.info(f"Getting preferences for user {current_user.id}")
    
    # Get user preferences from profile or return defaults
    try:
        profile = await sync_to_async(lambda: current_user.profile)()
        return UserPreferences(
            notifications_enabled=getattr(profile, 'notifications_enabled', True),
            email_notifications=getattr(profile, 'email_notifications', True),
            sms_notifications=getattr(profile, 'sms_notifications', False),
            privacy_level=getattr(profile, 'privacy_level', 'public')
        )
    except AttributeError:
        # Return default preferences if profile doesn't exist
        return UserPreferences()


@router.put("/preferences", response_model=UserPreferences)
async def update_user_preferences(
    preferences_data: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user)
):
    """
    Update current user's preferences.
    
    Args:
        preferences_data: Preferences data to update
        current_user: Current authenticated user
        
    Returns:
        Updated user preferences
    """
    logger.info(f"Updating preferences for user {current_user.id}")
    
    # Get or create user profile
    try:
        profile = await sync_to_async(lambda: current_user.profile)()
    except AttributeError:
        # Create profile if it doesn't exist
        from users.models import UserProfile
        profile = await sync_to_async(UserProfile.objects.create)(
            user=current_user
        )
    
    # Update preferences
    if preferences_data.notifications_enabled is not None:
        profile.notifications_enabled = preferences_data.notifications_enabled
    if preferences_data.email_notifications is not None:
        profile.email_notifications = preferences_data.email_notifications
    if preferences_data.sms_notifications is not None:
        profile.sms_notifications = preferences_data.sms_notifications
    if preferences_data.privacy_level is not None:
        profile.privacy_level = preferences_data.privacy_level
    
    # Save profile
    await sync_to_async(profile.save)()
    
    return UserPreferences(
        notifications_enabled=profile.notifications_enabled,
        email_notifications=profile.email_notifications,
        sms_notifications=profile.sms_notifications,
        privacy_level=profile.privacy_level
    )


@router.get("/{user_id}", response_model=UserProfileResponse)
async def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Get user profile by ID (if user has permission).
    
    Args:
        user_id: User ID to get
        current_user: Current authenticated user
        
    Returns:
        User profile information
        
    Raises:
        HTTPException: If user not found or permission denied
    """
    logger.info(f"Getting user {user_id} by user {current_user.id}")
    
    # Check if user can view other users
    if not RoleBasedPermission.has_permission(current_user, "users.view_user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    try:
        user = await sync_to_async(User.objects.get)(id=user_id)
        
        return UserProfileResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            date_joined=user.date_joined,
            last_login=user.last_login
        )
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )


@router.get("/", response_model=List[UserProfileResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user)
):
    """
    List users (admin only).
    
    Args:
        skip: Number of users to skip
        limit: Maximum number of users to return
        current_user: Current authenticated user
        
    Returns:
        List of user profiles
        
    Raises:
        HTTPException: If permission denied
    """
    logger.info(f"Listing users by user {current_user.id}")
    
    # Check if user can view all users
    if not RoleBasedPermission.has_permission(current_user, "users.view_user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    # Get users from database
    users = await sync_to_async(list)(
        User.objects.all()[skip:skip + limit]
    )
    
    return [
        UserProfileResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            date_joined=user.date_joined,
            last_login=user.last_login
        )
        for user in users
    ]


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """
    Delete user (admin only).
    
    Args:
        user_id: User ID to delete
        current_user: Current authenticated user
        
    Returns:
        Success message
        
    Raises:
        HTTPException: If user not found or permission denied
    """
    logger.info(f"Deleting user {user_id} by user {current_user.id}")
    
    # Check if user can delete users
    if not RoleBasedPermission.has_permission(current_user, "users.delete_user"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied"
        )
    
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    try:
        user = await sync_to_async(User.objects.get)(id=user_id)
        await sync_to_async(user.delete)()
        
        return {"message": "User deleted successfully"}
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )