"""
Production-grade URL resolution for canonical event URLs.

This module handles:
- Extracting canonical_id from URL paths
- Resolving events by canonical_id
- Comparing URL slugs with DB slugs
- Generating 301 redirects for SEO when slugs mismatch
- Ensuring backward compatibility (old links never break)
"""

from typing import Optional, Tuple
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404
from events.models import Event
from core.utils.slug_generator import extract_canonical_id_from_url


def resolve_event_from_url(url_path: str) -> Tuple[Optional[Event], Optional[str]]:
    """
    Resolve event from canonical URL path.
    
    Process:
    1. Extract canonical_id from URL
    2. Fetch event by canonical_id
    3. Compare URL slug with DB slug
    4. Return event and redirect URL (if slug mismatch)
    
    Args:
        url_path: URL path (e.g., '/in/bangalore/events/tech-meetup--a9x3k')
        
    Returns:
        Tuple of (Event instance or None, redirect_url or None)
        - If slug matches: (event, None)
        - If slug mismatch: (event, canonical_url) for 301 redirect
        - If not found: (None, None)
    """
    # Extract canonical_id from URL
    canonical_id = extract_canonical_id_from_url(url_path)
    
    if not canonical_id:
        return None, None
    
    # Fetch event by canonical_id (immutable identifier)
    try:
        event = Event.objects.get(canonical_id=canonical_id, is_active=True, is_public=True)
    except Event.DoesNotExist:
        return None, None
    
    # Extract slug from URL path
    # Format: /{country_code}/{city_slug}/events/{slug}--{canonical_id}
    url_slug = None
    parts = url_path.split('/events/')
    if len(parts) == 2:
        slug_part = parts[1].split('--')[0]  # Get slug before '--'
        url_slug = slug_part
    
    # Compare URL slug with DB slug
    if url_slug and url_slug != event.slug:
        # Slug mismatch: return redirect URL
        return event, event.canonical_url
    
    # Slug matches: return event, no redirect
    return event, None


def get_event_by_canonical_id(canonical_id: str, include_private: bool = False) -> Optional[Event]:
    """
    Get event by canonical_id (for API use).
    
    Args:
        canonical_id: Base62 canonical identifier
        include_private: If True, includes private events (default: False, SEO/public only)
        
    Returns:
        Event instance or None if not found
    """
    try:
        queryset = Event.objects.filter(canonical_id=canonical_id, is_active=True)
        if not include_private:
            queryset = queryset.filter(is_public=True)
        return queryset.get()
    except Event.DoesNotExist:
        return None
