# events/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
from loopin_backend.base_models import TimeStampedModel
from loopin_backend.choices import (
    EVENT_STATUS_CHOICES,
    ATTENDANCE_STATUS_CHOICES,
    REQUEST_STATUS_CHOICES,
    INVITE_STATUS_CHOICES,
    VENUE_TYPE_CHOICES,
    MIN_EVENT_TITLE_LENGTH,
    MAX_EVENT_TITLE_LENGTH,
    MIN_EVENT_DESCRIPTION_LENGTH,
    MAX_EVENT_DESCRIPTION_LENGTH,
)


class Venue(TimeStampedModel):
    """Venue model for event locations"""
    name = models.CharField(max_length=150)
    address = models.CharField(max_length=255)
    city = models.CharField(max_length=100)
    venue_type = models.CharField(max_length=20, choices=VENUE_TYPE_CHOICES, default='indoor')
    capacity = models.PositiveIntegerField(default=0)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["city"]),
            models.Index(fields=["venue_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}"


class Event(TimeStampedModel):
    """Event model for hosting events"""
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="hosted_events"
    )
    title = models.CharField(
        max_length=MAX_EVENT_TITLE_LENGTH,
        validators=[MinValueValidator(MIN_EVENT_TITLE_LENGTH)]
    )
    description = models.TextField(
        blank=True,
        validators=[MinValueValidator(MIN_EVENT_DESCRIPTION_LENGTH)]
    )
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    venue = models.ForeignKey(
        Venue, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="events"
    )
    status = models.CharField(
        max_length=20,
        choices=EVENT_STATUS_CHOICES,
        default='draft'
    )
    is_public = models.BooleanField(default=True)
    max_capacity = models.PositiveIntegerField(default=0)
    going_count = models.PositiveIntegerField(default=0)
    cover_images = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["start_time"]),
            models.Index(fields=["status"]),
            models.Index(fields=["is_public"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["host"]),
        ]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        """Override save to track event creation analytics"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Track event creation analytics
        if is_new:
            try:
                from analytics.tracker import AnalyticsTracker
                AnalyticsTracker.track_event_creation(self.host, self, self.venue)
            except ImportError:
                pass  # Analytics module not available

    @property
    def is_past(self):
        """Check if event has already ended"""
        from django.utils import timezone
        return self.end_time < timezone.now()

    @property
    def is_full(self):
        """Check if event is at capacity"""
        return self.going_count >= self.max_capacity


class EventRequest(TimeStampedModel):
    """Model for users requesting to join events"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="requests")
    requester = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="event_requests"
    )
    status = models.CharField(
        max_length=20,
        choices=REQUEST_STATUS_CHOICES,
        default='pending'
    )
    message = models.TextField(blank=True)
    seats_requested = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("event", "requester")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["event", "requester"]),
        ]

    def __str__(self):
        return f"{self.requester} requests to join {self.event.title}"

    def save(self, *args, **kwargs):
        """Override save to track event request analytics"""
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        # Track event request analytics
        if is_new:
            try:
                from analytics.tracker import AnalyticsTracker
                AnalyticsTracker.track_event_request(self.requester, self.event, self.seats_requested, self.message)
            except ImportError:
                pass  # Analytics module not available


class EventInvite(TimeStampedModel):
    """Model for inviting users to events"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="invites")
    invited_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="event_invites"
    )
    status = models.CharField(
        max_length=20,
        choices=INVITE_STATUS_CHOICES,
        default='pending'
    )
    message = models.TextField(blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("event", "invited_user")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["event", "invited_user"]),
            models.Index(fields=["expires_at"]),
        ]

    def __str__(self):
        return f"Invite for {self.invited_user} to {self.event.title}"


class EventAttendee(TimeStampedModel):
    """Model for tracking event attendees"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attendees")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="event_attendances"
    )
    status = models.CharField(
        max_length=20,
        choices=ATTENDANCE_STATUS_CHOICES,
        default='going'
    )
    checked_in_at = models.DateTimeField(null=True, blank=True)
    seats = models.PositiveIntegerField(default=1)

    class Meta:
        unique_together = ("event", "user")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["event", "user"]),
        ]

    def __str__(self):
        return f"{self.user} attending {self.event.title}"