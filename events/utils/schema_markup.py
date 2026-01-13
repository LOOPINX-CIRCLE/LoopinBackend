"""
Production-grade Schema.org markup generation for SEO.

This module generates structured data (JSON-LD) for search engines,
enabling rich results in Google search and better discoverability.

Schema.org Types Used:
- Event: Event schema for event detail pages
- Organization: For host profiles
- BreadcrumbList: For navigation structure
"""

from typing import Dict, Any, Optional, List
from events.models import Event
from users.models import UserProfile
from datetime import datetime


def generate_event_schema(event: Event, base_url: str = "") -> Dict[str, Any]:
    """
    Generate Schema.org Event structured data (JSON-LD).
    
    Args:
        event: Event instance
        base_url: Base URL for absolute URLs (e.g., 'https://loopin.app')
        
    Returns:
        Dictionary with @context, @type, and event properties
        
    Example:
        {
            "@context": "https://schema.org",
            "@type": "Event",
            "name": "Tech Founder Meetup",
            "startDate": "2024-12-25T18:00:00Z",
            "endDate": "2024-12-25T21:00:00Z",
            "location": {
                "@type": "Place",
                "name": "Bangalore",
                "address": {...}
            },
            ...
        }
    """
    # Build canonical URL
    canonical_path = event.canonical_url or f"/events/{event.canonical_id}"
    canonical_url = f"{base_url}{canonical_path}" if base_url else canonical_path
    
    # Event schema
    schema = {
        "@context": "https://schema.org",
        "@type": "Event",
        "name": event.title,
        "description": event.description[:500] if event.description else f"Join us for {event.title}",
        "startDate": event.start_time.isoformat() if event.start_time else None,
        "endDate": event.end_time.isoformat() if event.end_time else None,
        "url": canonical_url,
        "image": event.cover_images[0] if event.cover_images else None,
    }
    
    # Location
    if event.venue:
        location = {
            "@type": "Place",
            "name": event.venue.name,
            "address": {
                "@type": "PostalAddress",
                "addressLocality": event.venue.city,
                "addressCountry": event.venue.country_code.upper() if event.venue.country_code else "IN",
                "streetAddress": event.venue.address,
            }
        }
        if event.venue.latitude and event.venue.longitude:
            location["geo"] = {
                "@type": "GeoCoordinates",
                "latitude": float(event.venue.latitude),
                "longitude": float(event.venue.longitude),
            }
        schema["location"] = location
    elif event.venue_text:
        schema["location"] = {
            "@type": "Place",
            "name": event.venue_text,
        }
    
    # Organizer (host)
    if event.host:
        schema["organizer"] = {
            "@type": "Organization",
            "name": event.host.name or event.host.username,
        }
    
    # Offers (pricing)
    if event.is_paid and event.ticket_price:
        schema["offers"] = {
            "@type": "Offer",
            "price": str(event.ticket_price),
            "priceCurrency": "INR",
            "availability": "https://schema.org/InStock" if event.going_count < event.max_capacity else "https://schema.org/SoldOut",
            "url": canonical_url,
        }
    else:
        schema["offers"] = {
            "@type": "Offer",
            "price": "0",
            "priceCurrency": "INR",
            "availability": "https://schema.org/InStock",
            "url": canonical_url,
        }
    
    # Event status
    if event.status == "cancelled":
        schema["eventStatus"] = "https://schema.org/EventCancelled"
    elif event.status == "postponed":
        schema["eventStatus"] = "https://schema.org/EventPostponed"
    elif event.status == "completed":
        schema["eventStatus"] = "https://schema.org/EventScheduled"
    else:
        schema["eventStatus"] = "https://schema.org/EventScheduled"
    
    # Event attendance mode
    if event.venue and event.venue.venue_type == "virtual":
        schema["eventAttendanceMode"] = "https://schema.org/OnlineEventAttendanceMode"
    elif event.venue and event.venue.venue_type == "hybrid":
        schema["eventAttendanceMode"] = "https://schema.org/MixedEventAttendanceMode"
    else:
        schema["eventAttendanceMode"] = "https://schema.org/OfflineEventAttendanceMode"
    
    # Remove None values
    schema = {k: v for k, v in schema.items() if v is not None}
    
    return schema


def generate_breadcrumb_schema(
    items: List[Dict[str, str]],
    base_url: str = ""
) -> Dict[str, Any]:
    """
    Generate Schema.org BreadcrumbList structured data.
    
    Args:
        items: List of {name, url} dictionaries
        base_url: Base URL for absolute URLs
        
    Returns:
        Dictionary with @context, @type, and breadcrumb items
        
    Example:
        {
            "@context": "https://schema.org",
            "@type": "BreadcrumbList",
            "itemListElement": [...]
        }
    """
    item_list_element = []
    for idx, item in enumerate(items, start=1):
        url = f"{base_url}{item['url']}" if base_url and item['url'].startswith('/') else item['url']
        item_list_element.append({
            "@type": "ListItem",
            "position": idx,
            "name": item['name'],
            "item": url,
        })
    
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": item_list_element,
    }


def generate_city_page_schema(
    city_name: str,
    country_code: str,
    events_count: int,
    base_url: str = ""
) -> Dict[str, Any]:
    """
    Generate Schema.org structured data for city events page.
    
    Args:
        city_name: City name (e.g., 'Bangalore')
        country_code: Country code (e.g., 'in')
        events_count: Number of events
        base_url: Base URL for absolute URLs
        
    Returns:
        Dictionary with local business/place schema
    """
    city_slug = city_name.lower().replace(' ', '-')
    city_url = f"{base_url}/in/{city_slug}/events" if base_url else f"/in/{city_slug}/events"
    
    return {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": f"Events in {city_name}",
        "description": f"Discover {events_count} events in {city_name}. Find meetups, workshops, and social gatherings.",
        "url": city_url,
        "about": {
            "@type": "City",
            "name": city_name,
            "addressCountry": country_code.upper(),
        }
    }
