"""
Permission utilities for the Loopin Backend application.
"""

from typing import Optional, List, Dict, Any
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.db import models
from core.exceptions import AuthorizationError


class PermissionChecker:
    """
    Utility class for checking permissions.
    """
    
    @staticmethod
    def check_user_permission(user: User, permission: str, obj: Optional[models.Model] = None) -> bool:
        """
        Check if user has specific permission.
        
        Args:
            user: User instance
            permission: Permission string
            obj: Optional object for object-level permissions
            
        Returns:
            True if user has permission, False otherwise
        """
        if obj:
            return user.has_perm(permission, obj)
        return user.has_perm(permission)
    
    @staticmethod
    def require_permission(user: User, permission: str, obj: Optional[models.Model] = None) -> None:
        """
        Require user to have specific permission.
        
        Args:
            user: User instance
            permission: Permission string
            obj: Optional object for object-level permissions
            
        Raises:
            AuthorizationError: If user doesn't have permission
        """
        if not PermissionChecker.check_user_permission(user, permission, obj):
            raise AuthorizationError(
                f"User {user.id} does not have permission '{permission}'",
                code="PERMISSION_DENIED"
            )
    
    @staticmethod
    def check_ownership(user: User, obj: models.Model, owner_field: str = "user") -> bool:
        """
        Check if user owns the object.
        
        Args:
            user: User instance
            obj: Model instance
            owner_field: Field name that contains the owner
            
        Returns:
            True if user owns the object, False otherwise
        """
        if not hasattr(obj, owner_field):
            return False
        
        owner = getattr(obj, owner_field)
        return owner == user
    
    @staticmethod
    def require_ownership(user: User, obj: models.Model, owner_field: str = "user") -> None:
        """
        Require user to own the object.
        
        Args:
            user: User instance
            obj: Model instance
            owner_field: Field name that contains the owner
            
        Raises:
            AuthorizationError: If user doesn't own the object
        """
        if not PermissionChecker.check_ownership(user, obj, owner_field):
            raise AuthorizationError(
                f"User {user.id} does not own {obj.__class__.__name__} {obj.pk}",
                code="OWNERSHIP_DENIED"
            )


class RoleBasedPermission:
    """
    Role-based permission system.
    """
    
    ROLES = {
        'admin': ['*'],  # Admin has all permissions
        'moderator': [
            'users.view_user',
            'users.change_user',
            'events.view_event',
            'events.change_event',
            'events.delete_event',
        ],
        'user': [
            'users.view_user',
            'users.change_user',
            'events.view_event',
            'events.add_event',
            'events.change_event',
        ],
        'guest': [
            'events.view_event',
        ]
    }
    
    @classmethod
    def get_user_permissions(cls, user: User) -> List[str]:
        """
        Get permissions for user based on their role.
        
        Args:
            user: User instance
            
        Returns:
            List of permission strings
        """
        if user.is_superuser:
            return ['*']
        
        if user.is_staff:
            return cls.ROLES.get('moderator', [])
        
        # Check user profile for custom role
        if hasattr(user, 'profile') and hasattr(user.profile, 'role'):
            return cls.ROLES.get(user.profile.role, cls.ROLES['user'])
        
        return cls.ROLES['user']
    
    @classmethod
    def has_permission(cls, user: User, permission: str) -> bool:
        """
        Check if user has permission based on their role.
        
        Args:
            user: User instance
            permission: Permission string
            
        Returns:
            True if user has permission, False otherwise
        """
        user_permissions = cls.get_user_permissions(user)
        
        # Check for wildcard permission
        if '*' in user_permissions:
            return True
        
        # Check for exact permission
        if permission in user_permissions:
            return True
        
        # Check for app-level permission
        app_permission = permission.split('.')[0] + '.*'
        if app_permission in user_permissions:
            return True
        
        return False


class ObjectLevelPermission:
    """
    Object-level permission system.
    """
    
    @staticmethod
    def can_view(user: User, obj: models.Model) -> bool:
        """
        Check if user can view object.
        
        Args:
            user: User instance
            obj: Model instance
            
        Returns:
            True if user can view, False otherwise
        """
        # Superusers can view everything
        if user.is_superuser:
            return True
        
        # Check ownership
        if hasattr(obj, 'user') and obj.user == user:
            return True
        
        # Check if object is public
        if hasattr(obj, 'is_public') and obj.is_public:
            return True
        
        return False
    
    @staticmethod
    def can_edit(user: User, obj: models.Model) -> bool:
        """
        Check if user can edit object.
        
        Args:
            user: User instance
            obj: Model instance
            
        Returns:
            True if user can edit, False otherwise
        """
        # Superusers can edit everything
        if user.is_superuser:
            return True
        
        # Check ownership
        if hasattr(obj, 'user') and obj.user == user:
            return True
        
        # Staff can edit if they have permission
        if user.is_staff and user.has_perm(f'{obj.__class__._meta.app_label}.change_{obj.__class__._meta.model_name}'):
            return True
        
        return False
    
    @staticmethod
    def can_delete(user: User, obj: models.Model) -> bool:
        """
        Check if user can delete object.
        
        Args:
            user: User instance
            obj: Model instance
            
        Returns:
            True if user can delete, False otherwise
        """
        # Superusers can delete everything
        if user.is_superuser:
            return True
        
        # Check ownership
        if hasattr(obj, 'user') and obj.user == user:
            return True
        
        # Staff can delete if they have permission
        if user.is_staff and user.has_perm(f'{obj.__class__._meta.app_label}.delete_{obj.__class__._meta.model_name}'):
            return True
        
        return False


def require_permission(permission: str, obj_field: Optional[str] = None):
    """
    Decorator to require permission for view functions.
    
    Args:
        permission: Permission string
        obj_field: Optional field name to get object from request
        
    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                raise AuthorizationError("Authentication required", code="AUTHENTICATION_REQUIRED")
            
            # Check object-level permission if obj_field is provided
            if obj_field and obj_field in kwargs:
                obj = kwargs[obj_field]
                if not ObjectLevelPermission.can_view(user, obj):
                    raise AuthorizationError("Permission denied", code="PERMISSION_DENIED")
            
            # Check general permission
            if not RoleBasedPermission.has_permission(user, permission):
                raise AuthorizationError("Permission denied", code="PERMISSION_DENIED")
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator


def require_ownership(owner_field: str = "user"):
    """
    Decorator to require ownership for view functions.
    
    Args:
        owner_field: Field name that contains the owner
        
    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(request, *args, **kwargs):
            user = request.user
            
            if not user.is_authenticated:
                raise AuthorizationError("Authentication required", code="AUTHENTICATION_REQUIRED")
            
            # Get object from kwargs (assuming it's the first argument after request)
            obj = None
            for key, value in kwargs.items():
                if hasattr(value, owner_field):
                    obj = value
                    break
            
            if obj and not PermissionChecker.check_ownership(user, obj, owner_field):
                raise AuthorizationError("Ownership required", code="OWNERSHIP_REQUIRED")
            
            return func(request, *args, **kwargs)
        
        return wrapper
    return decorator
