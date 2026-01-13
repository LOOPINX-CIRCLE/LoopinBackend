"""
Public API for single event URL resolution (SEO + GEO).

This module provides minimal, public endpoints for single event URL sharing.
No authentication required. Returns only fields needed for SEO-optimized web rendering.
"""

from typing import Dict, Any, Optional, Tuple
from fastapi import APIRouter, Path, status, Query
from fastapi.responses import RedirectResponse
from django.conf import settings
from asgiref.sync import sync_to_async
from core.exceptions import NotFoundError
from events.models import Event

router = APIRouter(prefix="/public/events", tags=["public-events"])


@sync_to_async
def get_event_by_canonical_id_for_seo(canonical_id: str) -> Optional[Event]:
    """
    Get public, published event by canonical_id.
    
    Returns event only if:
    - Event exists
    - Event is active
    - Event is public
    - Event status is published
    
    Returns None if event not found or not visible.
    """
    try:
        return Event.objects.select_related("venue", "host", "host__user").get(
            canonical_id=canonical_id,
            is_active=True,
            is_public=True,
            status="published"
        )
    except Event.DoesNotExist:
        return None


def validate_url_slug_and_city(
    event: Event,
    url_city_slug: Optional[str] = None,
    url_event_slug: Optional[str] = None
) -> Tuple[bool, Optional[str]]:
    """
    Validate URL slug and city slug against event database values.
    
    Args:
        event: Event instance
        url_city_slug: City slug from URL (optional)
        url_event_slug: Event slug from URL (optional)
    
    Returns:
        Tuple of (is_valid, canonical_url_if_mismatch)
        - If valid: (True, None)
        - If mismatch: (False, canonical_url_for_redirect)
    """
    # Get expected values from event
    expected_city_slug = None
    if event.venue and event.venue.city_slug:
        expected_city_slug = event.venue.city_slug
    elif event.venue_text:
        from core.utils.slug_generator import generate_slug
        expected_city_slug = generate_slug(event.venue_text, max_length=100)
    
    expected_event_slug = event.slug
    
    # Check if URL matches database values
    city_matches = (url_city_slug is None) or (url_city_slug == expected_city_slug)
    slug_matches = (url_event_slug is None) or (url_event_slug == expected_event_slug)
    
    if city_matches and slug_matches:
        return True, None
    
    # Mismatch detected - return canonical URL for redirect
    canonical_url = event.canonical_url or f"/in/{expected_city_slug or 'unknown'}/events/{expected_event_slug}--{event.canonical_id}"
    return False, canonical_url


@router.get("/{canonical_id}/seo")
async def get_single_event_seo(
    canonical_id: str = Path(..., description="Event canonical ID (Base62)"),
    url_city_slug: Optional[str] = Query(None, description="City slug from URL (for validation)"),
    url_event_slug: Optional[str] = Query(None, description="Event slug from URL (for validation)"),
) -> Dict[str, Any]:
    """
    Public API for single event URL resolution and SEO data.
    
    This endpoint is used by the web layer to render SEO-optimized event pages.
    
    **URL Format:** `http://loopinsocial.in/in/{city_slug}/events/{event_slug}--{canonical_id}`
    
    **Resolution Logic:**
    1. Extract canonical_id from URL
    2. Fetch event by canonical_id (must be public, published, active)
    3. Validate URL slug and city match database values
    4. If mismatch → Return 301 redirect to canonical URL
    5. If valid → Return minimal event data for SEO rendering
    
    **Response Fields (Minimal Set Only):**
    - event_title
    - about_event (description)
    - event_image_url
    - start_time
    - end_time
    - city
    - venue_or_location
    - canonical_url
    
    **Authentication:** None required (public endpoint)
    
    **Example:**
    ```
    GET /api/public/events/a9x3k/seo?url_city_slug=bangalore&url_event_slug=tech-meetup
    ```
    """
    # Fetch event by canonical_id
    event = await get_event_by_canonical_id_for_seo(canonical_id)
    
    if not event:
        raise NotFoundError(
            f"Event with canonical ID '{canonical_id}' not found or not publicly visible.",
            code="EVENT_NOT_FOUND"
        )
    
    # Validate URL slug and city (if provided)
    is_valid, redirect_url = validate_url_slug_and_city(event, url_city_slug, url_event_slug)
    
    if not is_valid and redirect_url:
        # Slug or city mismatch - return 301 redirect
        base_url = getattr(settings, 'SITE_URL', 'http://loopinsocial.in')
        full_redirect_url = f"{base_url}{redirect_url}"
        
        # Return 301 redirect response
        return RedirectResponse(url=full_redirect_url, status_code=status.HTTP_301_MOVED_PERMANENTLY)
    
    # Get base URL for canonical URL
    base_url = getattr(settings, 'SITE_URL', 'http://loopinsocial.in')
    canonical_url_path = event.canonical_url or f"/in/unknown/events/{event.slug}--{event.canonical_id}"
    full_canonical_url = f"{base_url}{canonical_url_path}"
    
    # Get city name
    city_name = event.venue.city if event.venue else (event.venue_text or "Unknown")
    
    # Get venue/location
    venue_or_location = event.venue.name if event.venue else event.venue_text or "Location TBD"
    
    # Get cover image (first image or empty)
    event_image_url = event.cover_images[0] if event.cover_images and len(event.cover_images) > 0 else ""
    
    # Return minimal response (only fields needed for SEO rendering)
    return {
        "event_title": event.title,
        "about_event": event.description or "",
        "event_image_url": event_image_url,
        "start_time": event.start_time.isoformat() if event.start_time else None,
        "end_time": event.end_time.isoformat() if event.end_time else None,
        "city": city_name,
        "venue_or_location": venue_or_location,
        "canonical_url": full_canonical_url,
    }
