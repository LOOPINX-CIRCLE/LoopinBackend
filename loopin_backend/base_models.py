"""
Base model classes for the LoopinBackend project.

This module provides abstract base models that can be inherited by other models
to provide common functionality like timestamps and soft deletion.
"""

from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """
    Abstract base model for created/updated timestamps.
    
    Provides:
    - created_at: Automatically set when record is created
    - updated_at: Automatically updated when record is modified
    - Both fields are indexed for better query performance
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True, db_index=True)

    class Meta:
        abstract = True


class SoftDeleteModel(models.Model):
    """
    Abstract model for soft deletion (non-destructive deletes).
    
    Instead of permanently deleting records, marks them as deleted.
    This preserves data integrity and allows for recovery.
    """
    is_deleted = models.BooleanField(default=False, db_index=True)

    def delete(self, using=None, keep_parents=False):
        """
        Override delete to perform soft deletion instead of hard deletion.
        """
        self.is_deleted = True
        self.save(update_fields=["is_deleted", "updated_at"])

    class Meta:
        abstract = True


class BaseModel(TimeStampedModel, SoftDeleteModel):
    """
    Unified base model combining timestamps and soft deletion.
    
    Use this as the base class for most models in the application.
    Provides both created/updated timestamps and soft deletion capabilities.
    """
    class Meta:
        abstract = True
