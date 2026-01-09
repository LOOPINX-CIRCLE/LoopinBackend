"""
Push notification device registration endpoints.

Handles:
- Device registration (register OneSignal player ID)
- Device deactivation
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from django.contrib.auth.models import User

from .auth import get_current_user
from asgiref.sync import sync_to_async
from notifications.models import UserDevice

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/notifications", tags=["notifications"])


class DeviceRegistrationRequest(BaseModel):
    """Request model for device registration"""
    onesignal_player_id: str = Field(..., min_length=1, max_length=255, description="OneSignal player ID")
    platform: str = Field(..., description="Device platform: 'ios' or 'android'")


class DeviceRegistrationResponse(BaseModel):
    """Response model for device registration"""
    success: bool
    message: str
    device_id: Optional[int] = None


@router.post("/devices/register", response_model=DeviceRegistrationResponse)
async def register_device(
    request: DeviceRegistrationRequest,
    user: User = Depends(get_current_user),
):
    """
    Register a device for push notifications.
    
    Associates a OneSignal player ID with the user's USER_PROFILE.
    One user can have multiple devices (iOS, Android).
    
    Args:
        request: Device registration data (player_id, platform)
        user: Authenticated user (from JWT)
        
    Returns:
        Device registration response
        
    Security:
    - Requires authentication (JWT)
    - Only registers devices for USER_PROFILE (normal users)
    - Admin users (AUTH_USER) are rejected
    """
    try:
        # SECURITY: Only allow USER_PROFILE, reject AUTH_USER (admins)
        if not hasattr(user, 'profile'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device registration is only available for customer accounts. Admin accounts cannot register devices."
            )
        
        user_profile = await sync_to_async(lambda: user.profile)()
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found. Please complete your profile first."
            )
        
        # Validate platform
        if request.platform not in ['ios', 'android']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Platform must be 'ios' or 'android'"
            )
        
        @sync_to_async
        def register_device_sync():
            """Register or update device"""
            from django.utils import timezone
            
            # Get or create device
            device, created = UserDevice.objects.get_or_create(
                onesignal_player_id=request.onesignal_player_id,
                defaults={
                    'user_profile': user_profile,
                    'platform': request.platform,
                    'is_active': True,
                    'last_seen_at': timezone.now(),
                }
            )
            
            if not created:
                # Update existing device (reactivate if needed, update last_seen)
                device.user_profile = user_profile  # Update in case user changed
                device.platform = request.platform
                device.is_active = True
                device.last_seen_at = timezone.now()
                device.save(update_fields=['user_profile', 'platform', 'is_active', 'last_seen_at', 'updated_at'])
            
            return device, created
        
        device, created = await register_device_sync()
        
        action = "registered" if created else "updated"
        logger.info(
            f"Device {action} for user {user_profile.id}: "
            f"player_id={request.onesignal_player_id[:8]}..., platform={request.platform}"
        )
        
        return DeviceRegistrationResponse(
            success=True,
            message=f"Device {action} successfully",
            device_id=device.id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering device: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to register device"
        )


@router.delete("/devices/{player_id}", response_model=DeviceRegistrationResponse)
async def unregister_device(
    player_id: str,
    user: User = Depends(get_current_user),
):
    """
    Deactivate a device for push notifications.
    
    Marks the device as inactive (soft delete).
    Device records are preserved for audit purposes.
    
    Args:
        player_id: OneSignal player ID to deactivate
        user: Authenticated user (from JWT)
        
    Returns:
        Device deactivation response
        
    Security:
    - Requires authentication (JWT)
    - Users can only deactivate their own devices
    """
    try:
        # SECURITY: Only allow USER_PROFILE, reject AUTH_USER (admins)
        if not hasattr(user, 'profile'):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Device management is only available for customer accounts."
            )
        
        user_profile = await sync_to_async(lambda: user.profile)()
        
        if not user_profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User profile not found."
            )
        
        @sync_to_async
        def deactivate_device_sync():
            """Deactivate device"""
            try:
                device = UserDevice.objects.get(
                    onesignal_player_id=player_id,
                    user_profile=user_profile,
                )
                device.deactivate()
                return device
            except UserDevice.DoesNotExist:
                return None
        
        device = await deactivate_device_sync()
        
        if not device:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Device not found or does not belong to this user"
            )
        
        logger.info(
            f"Device deactivated for user {user_profile.id}: "
            f"player_id={player_id[:8]}..."
        )
        
        return DeviceRegistrationResponse(
            success=True,
            message="Device deactivated successfully",
            device_id=device.id,
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating device: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deactivate device"
        )

