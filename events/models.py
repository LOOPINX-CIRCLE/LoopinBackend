# events/models.py
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator
import uuid
from core.base_models import TimeStampedModel
from core.choices import (
    EVENT_STATUS_CHOICES,
    ALLOWED_GENDER_CHOICES,
    ATTENDANCE_STATUS_CHOICES,
    REQUEST_STATUS_CHOICES,
    INVITE_STATUS_CHOICES,
    INVITE_TYPE_CHOICES,
    TICKET_TYPE_CHOICES,
    VENUE_TYPE_CHOICES,
    MIN_EVENT_TITLE_LENGTH,
    MAX_EVENT_TITLE_LENGTH,
    MIN_EVENT_DESCRIPTION_LENGTH,
    MAX_EVENT_DESCRIPTION_LENGTH,
)
from django.core.validators import MinValueValidator, MaxValueValidator


class Venue(TimeStampedModel):
    """Venue model for event locations"""
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Public UUID")
    name = models.CharField(max_length=150)
    address = models.TextField()
    city = models.CharField(max_length=100)
    venue_type = models.CharField(max_length=20, choices=VENUE_TYPE_CHOICES, default='indoor')
    capacity = models.PositiveIntegerField(default=0)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True, help_text="Extra info, accessibility, capacity hints")
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
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Public UUID")
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE, 
        related_name="hosted_events"
    )
    title = models.CharField(
        max_length=MAX_EVENT_TITLE_LENGTH,
        validators=[MinValueValidator(MIN_EVENT_TITLE_LENGTH)]
    )
    slug = models.SlugField(max_length=MAX_EVENT_TITLE_LENGTH, unique=True, blank=True, help_text="URL-friendly slug")
    description = models.TextField(
        blank=True,
        validators=[MinValueValidator(MIN_EVENT_DESCRIPTION_LENGTH)]
    )
    
    # Venue fields
    venue = models.ForeignKey(
        Venue, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name="events"
    )
    venue_text = models.CharField(max_length=255, blank=True, help_text="Custom venue if not in VENUE table")
    
    # Date and time fields - using existing start_time/end_time approach
    start_time = models.DateTimeField(help_text="Event start date and time")
    end_time = models.DateTimeField(help_text="Event end date and time")
    
    # Capacity and pricing
    max_capacity = models.PositiveIntegerField(default=0, help_text="Maximum attendees")
    is_paid = models.BooleanField(default=False, help_text="Whether event requires payment")
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Ticket price")
    allow_plus_one = models.BooleanField(default=True, help_text="Allow bringing a guest")
    
    # GST fields
    gst_number = models.CharField(max_length=50, blank=True, help_text="Host GST number")
    
    # Gender restrictions
    allowed_genders = models.CharField(max_length=20, choices=ALLOWED_GENDER_CHOICES, default='all', help_text="Gender restrictions")
    
    # Images
    cover_images = models.JSONField(default=list, blank=True, help_text="Array of 1-3 cover image URLs")
    
    # Status and tracking
    status = models.CharField(max_length=20, choices=EVENT_STATUS_CHOICES, default='draft', help_text="Event status")
    is_public = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)
    going_count = models.PositiveIntegerField(default=0, help_text="Number of confirmed attendees")
    requests_count = models.PositiveIntegerField(default=0, help_text="Number of pending requests")
    
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
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
            # Ensure unique slug
            original_slug = self.slug
            count = 1
            while Event.objects.filter(slug=self.slug).exclude(pk=self.pk if self.pk is not None else None).exists():
                self.slug = f"{original_slug}-{count}"
                count += 1
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
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
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
    host_message = models.TextField(blank=True, help_text="Host's response message")
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
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="invites")
    host = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_event_invites",
        null=True,
        blank=True,
        help_text="Event host (optional, can be derived from event.host)"
    )
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
    invite_type = models.CharField(max_length=20, choices=INVITE_TYPE_CHOICES, default='direct')
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
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attendees")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        related_name="event_attendances"
    )
    request = models.ForeignKey(
        'EventRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendees"
    )
    ticket_type = models.CharField(max_length=20, choices=TICKET_TYPE_CHOICES, default='standard')
    seats = models.PositiveIntegerField(default=1)
    is_paid = models.BooleanField(default=False)
    price_paid = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=ATTENDANCE_STATUS_CHOICES, default='going')
    checked_in_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ("event", "user")
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["event", "user"]),
        ]

    def __str__(self):
        return f"{self.user} attending {self.event.title}"


class EventInterestMap(TimeStampedModel):
    """Many-to-many mapping between events and interests"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="interest_maps")
    event_interest = models.ForeignKey(
        'users.EventInterest',
        on_delete=models.CASCADE,
        related_name="event_maps"
    )

    class Meta:
        unique_together = ("event", "event_interest")
        indexes = [
            models.Index(fields=["event", "event_interest"]),
        ]

    def __str__(self):
        return f"{self.event.title} - {self.event_interest.name}"


class CapacityReservation(TimeStampedModel):
    """Temporary holds on event seats before payment confirmation"""
    reservation_key = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="capacity_reservations")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="capacity_reservations"
    )
    seats_reserved = models.PositiveIntegerField(default=1)
    consumed = models.BooleanField(default=False)
    expires_at = models.DateTimeField()

    class Meta:
        indexes = [
            models.Index(fields=["expires_at"]),
            models.Index(fields=["consumed"]),
            models.Index(fields=["event", "user"]),
        ]

    def __str__(self):
        return f"Reservation {self.reservation_key} for {self.user}"


class EventImage(TimeStampedModel):
    """Store multiple images for events"""
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="event_images")
    image_url = models.TextField(help_text="Image URL")
    position = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['position']
        indexes = [
            models.Index(fields=["event", "position"]),
        ]

    def __str__(self):
        return f"Image {self.position} for {self.event.title}"