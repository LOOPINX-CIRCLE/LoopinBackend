"""
User activity signals for the Loopin Backend application.

This module contains Django signals for tracking user activities
and triggering related actions.
"""

import logging
from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.contrib.auth.signals import user_logged_in, user_logged_out

from core.utils.logger import get_logger
from core.exceptions import BusinessLogicError


logger = get_logger(__name__)


@receiver(user_logged_in)
def user_login_handler(sender, request, user, **kwargs):
    """Handle user login events."""
    
    logger.info(
        f"User logged in: {user.id}",
        extra={
            'user_id': user.id,
            'username': user.username,
            'ip_address': get_client_ip(request),
            'user_agent': request.META.get('HTTP_USER_AGENT', ''),
        }
    )
    
    # Update last login time
    try:
        user.last_login = timezone.now()
        user.save(update_fields=['last_login'])
    except Exception as e:
        logger.error(f"Failed to update last login for user {user.id}: {str(e)}")


@receiver(user_logged_out)
def user_logout_handler(sender, request, user, **kwargs):
    """Handle user logout events."""
    
    logger.info(
        f"User logged out: {user.id}",
        extra={
            'user_id': user.id,
            'username': user.username,
            'ip_address': get_client_ip(request),
        }
    )


@receiver(post_save, sender=User)
def user_created_handler(sender, instance, created, **kwargs):
    """Handle user creation events."""
    
    if created:
        logger.info(
            f"New user created: {instance.id}",
            extra={
                'user_id': instance.id,
                'username': instance.username,
                'email': instance.email,
                'is_active': instance.is_active,
            }
        )
        
        # Create user profile if it doesn't exist
        try:
            from users.models import UserProfile
            if not hasattr(instance, 'profile'):
                UserProfile.objects.create(user=instance)
                logger.info(f"User profile created for user {instance.id}")
        except Exception as e:
            logger.error(f"Failed to create profile for user {instance.id}: {str(e)}")


@receiver(pre_save, sender=User)
def user_pre_save_handler(sender, instance, **kwargs):
    """Handle user pre-save events."""
    
    # Log user updates
    if instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            
            # Check for changes
            changes = {}
            for field in ['username', 'email', 'first_name', 'last_name', 'is_active']:
                old_value = getattr(old_instance, field)
                new_value = getattr(instance, field)
                if old_value != new_value:
                    changes[field] = {'old': old_value, 'new': new_value}
            
            if changes:
                logger.info(
                    f"User updated: {instance.id}",
                    extra={
                        'user_id': instance.id,
                        'changes': changes,
                    }
                )
        except User.DoesNotExist:
            pass


@receiver(post_delete, sender=User)
def user_deleted_handler(sender, instance, **kwargs):
    """Handle user deletion events."""
    
    logger.info(
        f"User deleted: {instance.id}",
        extra={
            'user_id': instance.id,
            'username': instance.username,
            'email': instance.email,
        }
    )


def get_client_ip(request):
    """Get client IP address from request."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
