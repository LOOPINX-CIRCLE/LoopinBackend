"""
User management router for FastAPI.
Handles user CRUD operations and profile management.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from datetime import datetime
from asgiref.sync import sync_to_async
from .auth import get_current_user, UserResponse
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Pydantic models
class UserUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    
    class Config:
        schema_extra = {
            "example": {
                "first_name": "John",
                "last_name": "Doe",
                "email": "john.doe@example.com"
            }
        }

class UserList(BaseModel):
    users: List[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

# User endpoints
@router.get("/", response_model=UserList)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user)
):
    """List all users with pagination and search"""
    # Only allow staff users to list all users
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    # Build queryset
    queryset = User.objects.all().order_by('-date_joined')
    
    # Apply search filter
    if search:
        queryset = queryset.filter(
            username__icontains=search
        ) | queryset.filter(
            email__icontains=search
        ) | queryset.filter(
            first_name__icontains=search
        ) | queryset.filter(
            last_name__icontains=search
        )
    
    # Paginate
    paginator = Paginator(queryset, per_page)
    page_obj = paginator.get_page(page)
    
    # Convert to response format
    users = [
        UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            date_joined=user.date_joined
        )
        for user in page_obj
    ]
    
    return UserList(
        users=users,
        total=paginator.count,
        page=page,
        per_page=per_page,
        total_pages=paginator.num_pages
    )

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Get user by ID"""
    # Users can only view their own profile unless they're staff
    if user_id != current_user.id and not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        user = User.objects.get(id=user_id)
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            date_joined=user.date_joined
        )
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update user information"""
    # Users can only update their own profile unless they're staff
    if user_id != current_user.id and not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        user = User.objects.get(id=user_id)
        
        # Update fields if provided
        if user_data.first_name is not None:
            user.first_name = user_data.first_name
        if user_data.last_name is not None:
            user.last_name = user_data.last_name
        if user_data.email is not None:
            # Check if email is already taken by another user
            if User.objects.filter(email=user_data.email).exclude(id=user.id).exists():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            user.email = user_data.email
        
        user.save()
        
        return UserResponse(
            id=user.id,
            username=user.username,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
            date_joined=user.date_joined
        )
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Delete user (soft delete by deactivating)"""
    # Only staff can delete users, and users can delete their own account
    if user_id != current_user.id and not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        user = User.objects.get(id=user_id)
        
        # Soft delete by deactivating
        user.is_active = False
        user.save()
        
        return {"message": "User deactivated successfully"}
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

@router.post("/{user_id}/activate")
async def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_user)
):
    """Activate a deactivated user (staff only)"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    try:
        user = User.objects.get(id=user_id)
        user.is_active = True
        user.save()
        
        return {"message": "User activated successfully"}
    except User.DoesNotExist:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
