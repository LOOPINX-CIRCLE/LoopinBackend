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
    """
    Venue model for event location references.
    
    Note: This is reference data only—the platform does not create or manage physical venues.
    The venue table exists to avoid duplicating location details when multiple events share
    the same location. Multiple events can reference the same venue simultaneously without
    any booking restrictions or conflicts.
    
    The `capacity` field is informational only; actual event capacity is controlled by
    `Event.max_capacity`, not this field.
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Public UUID")
    name = models.CharField(max_length=150)
    address = models.TextField()
    city = models.CharField(max_length=100)
    country_code = models.CharField(
        max_length=2,
        default='in',
        help_text="ISO 3166-1 alpha-2 country code (e.g., 'in', 'us') for GEO SEO"
    )
    city_slug = models.CharField(
        max_length=100,
        blank=True,
        help_text="URL-safe city name slug for canonical URLs (auto-generated from city)"
    )
    venue_type = models.CharField(max_length=20, choices=VENUE_TYPE_CHOICES, default='indoor')
    capacity = models.PositiveIntegerField(default=0, help_text="Informational capacity hint only—actual capacity controlled by Event.max_capacity")
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True, help_text="Extra info, accessibility, capacity hints")
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [
            models.Index(fields=["city"]),
            models.Index(fields=["country_code", "city_slug"]),
            models.Index(fields=["venue_type"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.name} - {self.city}"
    
    def save(self, *args, **kwargs):
        """Override save to auto-generate city_slug from city name"""
        if not self.city_slug and self.city:
            from core.utils.slug_generator import generate_slug
            self.city_slug = generate_slug(self.city, max_length=100)
        super().save(*args, **kwargs)


class Event(TimeStampedModel):
    """
    Event model for hosting events.
    
    Canonical URL System:
    - canonical_id: Immutable Base62 identifier (5-8 chars), generated once at creation
    - slug: SEO-friendly human-readable slug, can change (max 70 chars)
    - slug_version: Increments on every slug change for cache busting
    - canonical_url: Full canonical URL path: /{country_code}/{city_slug}/events/{slug}--{canonical_id}
    
    URL Resolution:
    - All public event URLs must include canonical_id
    - Slug is SEO-only and can change without breaking links
    - Backend resolves by canonical_id and redirects if slug mismatch
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="Public UUID")
    host = models.ForeignKey(
        'users.UserProfile', 
        on_delete=models.CASCADE, 
        related_name="hosted_events",
        help_text="Host user profile who owns this event"
    )
    title = models.CharField(
        max_length=MAX_EVENT_TITLE_LENGTH,
        validators=[MinValueValidator(MIN_EVENT_TITLE_LENGTH)]
    )
    # Canonical URL system fields
    canonical_id = models.CharField(
        max_length=10,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Immutable Base62 identifier for canonical URLs (generated at creation)"
    )
    slug = models.CharField(
        max_length=70,
        blank=True,
        help_text="SEO-friendly slug (max 70 chars, can change, not unique)"
    )
    slug_version = models.PositiveIntegerField(
        default=1,
        help_text="Increments on every slug change for cache busting"
    )
    canonical_url = models.TextField(
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="Full canonical URL path: /{country_code}/{city_slug}/events/{slug}--{canonical_id}"
    )
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
            models.Index(fields=["canonical_id"]),
            models.Index(fields=["canonical_url"]),
        ]

    def __str__(self):
        return self.title
    
    def _get_country_code(self) -> str:
        """Get country code from venue or default to 'in'"""
        if self.venue and self.venue.country_code:
            return self.venue.country_code
        return 'in'  # Default to India
    
    def _get_city_slug(self) -> str:
        """Get city slug from venue or generate from venue_text"""
        if self.venue and self.venue.city_slug:
            return self.venue.city_slug
        if self.venue_text:
            from core.utils.slug_generator import generate_slug
            return generate_slug(self.venue_text, max_length=100)
        return 'unknown'  # Fallback
    
    def _update_canonical_url(self):
        """Update canonical_url from current slug, country_code, and city_slug"""
        if not self.canonical_id:
            return
        
        country_code = self._get_country_code()
        city_slug = self._get_city_slug()
        
        from core.utils.slug_generator import build_canonical_url
        self.canonical_url = build_canonical_url(
            country_code=country_code,
            city_slug=city_slug,
            slug=self.slug,
            canonical_id=self.canonical_id
        )

    def save(self, *args, **kwargs):
        """
        Override save to:
        1. Generate canonical_id on creation (immutable)
        2. Generate/update slug from title
        3. Handle slug versioning on changes
        4. Update canonical_url
        5. Track event creation analytics
        """
        is_new = self.pk is None
        title_changed = False
        slug_changed = False
        
        # Track if title changed (to detect slug update needs)
        if not is_new:
            try:
                old_instance = Event.objects.get(pk=self.pk)
                title_changed = old_instance.title != self.title
                slug_changed = old_instance.slug != self.slug
            except Event.DoesNotExist:
                pass
        
        # Generate canonical_id on creation (immutable, never regenerated)
        if is_new and not self.canonical_id:
            from core.utils.canonical_id import generate_canonical_id
            self.canonical_id = generate_canonical_id(length=6)
        
        # Generate/update slug from title
        if is_new or title_changed:
            from core.utils.slug_generator import generate_slug, generate_unique_slug
            
            # Generate base slug from title
            base_slug = generate_slug(self.title, max_length=70)
            
            # For new events, ensure uniqueness (though slug uniqueness is not required)
            # We still check to avoid obvious collisions
            if is_new:
                existing_slugs = set(
                    Event.objects.values_list('slug', flat=True)
                    .exclude(slug='')
                )
                self.slug = generate_unique_slug(base_slug, existing_slugs)
            else:
                # For existing events, update slug and increment version
                self.slug = base_slug
                self.slug_version += 1
                slug_changed = True
        
        # Update canonical_url if slug, venue, or canonical_id changed
        if is_new or slug_changed or not self.canonical_url:
            self._update_canonical_url()
        
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
        if not self.end_time:
            return False  # NULL-safe: no end_time means event is not past
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
        'users.UserProfile', 
        on_delete=models.CASCADE,
        related_name="event_requests",
        help_text="User profile requesting to join event"
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
        'users.UserProfile',
        on_delete=models.CASCADE,
        related_name="sent_event_invites",
        null=True,
        blank=True,
        help_text="Host user profile (optional, can be derived from event.host)"
    )
    invited_user = models.ForeignKey(
        'users.UserProfile', 
        on_delete=models.CASCADE,
        related_name="event_invites",
        help_text="Invited user profile"
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
    """
    Model for tracking event attendees.
    
    Financial Linkage (CFO):
    - Direct link to PaymentOrder that fulfilled this attendee
    - Enables traceability: payment → attendee → payout
    """
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="attendees")
    user = models.ForeignKey(
        'users.UserProfile', 
        on_delete=models.CASCADE,
        related_name="event_attendances",
        help_text="Attending user profile"
    )
    request = models.ForeignKey(
        'EventRequest',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendees",
        help_text="Originating request if applicable"
    )
    invite = models.ForeignKey(
        'EventInvite',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="attendees",
        help_text="Originating invitation if applicable"
    )
    payment_order = models.ForeignKey(
        'payments.PaymentOrder',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="fulfilled_attendees",
        help_text="Payment order that fulfilled this attendee (for paid events)"
    )
    ticket_type = models.CharField(max_length=20, choices=TICKET_TYPE_CHOICES, default='general')
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
            models.Index(fields=["request"]),
            models.Index(fields=["invite"]),
            models.Index(fields=["payment_order"]),  # For tracing payment → attendee
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
        'users.UserProfile',
        on_delete=models.CASCADE,
        related_name="capacity_reservations",
        help_text="User profile reserving capacity"
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