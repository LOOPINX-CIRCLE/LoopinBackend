"""
City metadata utilities for GEO-first SEO.

This module provides city-specific metadata for SEO optimization,
including static content, structured data, and GEO targeting.
"""

from typing import Dict, Optional


# Static city metadata for SEO (India-focused)
CITY_METADATA = {
    'bangalore': {
        'name': 'Bangalore',
        'display_name': 'Bangalore',
        'country_code': 'in',
        'country': 'India',
        'seo_title': 'Events in Bangalore Today & This Week | Loopin',
        'seo_description': 'Discover the best events in Bangalore. Find meetups, workshops, networking events, and social gatherings happening this week.',
        'static_content': 'Bangalore, India\'s tech capital, is home to vibrant events and meetups. Discover networking opportunities, tech talks, workshops, and social gatherings happening around you.',
    },
    'mumbai': {
        'name': 'Mumbai',
        'display_name': 'Mumbai',
        'country_code': 'in',
        'country': 'India',
        'seo_title': 'Events in Mumbai Today & This Week | Loopin',
        'seo_description': 'Find exciting events in Mumbai. Discover meetups, workshops, networking events, and social gatherings happening this week.',
        'static_content': 'Mumbai, the financial capital of India, offers diverse events and meetups. Explore networking opportunities, cultural events, workshops, and social gatherings.',
    },
    'delhi': {
        'name': 'Delhi',
        'display_name': 'Delhi',
        'country_code': 'in',
        'country': 'India',
        'seo_title': 'Events in Delhi Today & This Week | Loopin',
        'seo_description': 'Explore events in Delhi. Find meetups, workshops, networking events, and social gatherings happening this week.',
        'static_content': 'Delhi, India\'s capital, hosts a variety of events and meetups. Discover networking opportunities, cultural events, workshops, and social gatherings.',
    },
    'hyderabad': {
        'name': 'Hyderabad',
        'display_name': 'Hyderabad',
        'country_code': 'in',
        'country': 'India',
        'seo_title': 'Events in Hyderabad Today & This Week | Loopin',
        'seo_description': 'Discover events in Hyderabad. Find meetups, workshops, networking events, and social gatherings happening this week.',
        'static_content': 'Hyderabad offers diverse events and meetups. Explore networking opportunities, tech events, workshops, and social gatherings.',
    },
    'chennai': {
        'name': 'Chennai',
        'display_name': 'Chennai',
        'country_code': 'in',
        'country': 'India',
        'seo_title': 'Events in Chennai Today & This Week | Loopin',
        'seo_description': 'Find events in Chennai. Discover meetups, workshops, networking events, and social gatherings happening this week.',
        'static_content': 'Chennai hosts vibrant events and meetups. Discover networking opportunities, cultural events, workshops, and social gatherings.',
    },
    'pune': {
        'name': 'Pune',
        'display_name': 'Pune',
        'country_code': 'in',
        'country': 'India',
        'seo_title': 'Events in Pune Today & This Week | Loopin',
        'seo_description': 'Explore events in Pune. Find meetups, workshops, networking events, and social gatherings happening this week.',
        'static_content': 'Pune offers diverse events and meetups. Explore networking opportunities, tech events, workshops, and social gatherings.',
    },
}


def get_city_metadata(city_slug: str) -> Optional[Dict[str, str]]:
    """
    Get city metadata for SEO.
    
    Args:
        city_slug: URL-safe city slug (e.g., 'bangalore')
        
    Returns:
        City metadata dictionary or None if not found
    """
    return CITY_METADATA.get(city_slug.lower())


def generate_city_seo_metadata(
    city_slug: str,
    events_count: int = 0,
    base_url: str = ""
) -> Dict[str, Any]:
    """
    Generate comprehensive SEO metadata for city events page.
    
    Args:
        city_slug: URL-safe city slug
        events_count: Number of events (for dynamic content)
        base_url: Base URL for absolute URLs
        
    Returns:
        Dictionary with SEO metadata (title, description, etc.)
    """
    metadata = get_city_metadata(city_slug)
    
    if not metadata:
        # Fallback for unknown cities
        city_name = city_slug.replace('-', ' ').title()
        return {
            'title': f'Events in {city_name} | Loopin',
            'description': f'Discover events in {city_name}. Find meetups, workshops, and social gatherings.',
            'h1': f'Events in {city_name}',
            'static_content': f'Find the best events and meetups in {city_name}.',
            'city_name': city_name,
            'city_slug': city_slug,
            'country_code': 'in',
        }
    
    # Update title/description with dynamic count if available
    title = metadata['seo_title']
    description = metadata['seo_description']
    
    if events_count > 0:
        description = f'Discover {events_count} events in {metadata["display_name"]}. {metadata["seo_description"].split(".", 1)[-1]}'
    
    return {
        'title': title,
        'description': description,
        'h1': f'Events in {metadata["display_name"]}',
        'static_content': metadata['static_content'],
        'city_name': metadata['display_name'],
        'city_slug': city_slug,
        'country_code': metadata['country_code'],
        'country': metadata['country'],
        'canonical_url': f"{base_url}/in/{city_slug}/events" if base_url else f"/in/{city_slug}/events",
    }
