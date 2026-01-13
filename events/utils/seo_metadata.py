"""
Production-grade SEO metadata generation for event pages.

This module generates server-side SEO metadata including:
- Page titles
- Meta descriptions
- OpenGraph tags
- Twitter Card tags
- Canonical URLs

All metadata is generated server-side (not in JavaScript) for proper
search engine crawling and social media sharing.
"""

from typing import Dict, Optional
from events.models import Event
from django.conf import settings


def generate_event_seo_metadata(event: Event, base_url: Optional[str] = None) -> Dict[str, str]:
    """
    Generate comprehensive SEO metadata for an event page.
    
    Args:
        event: Event instance
        base_url: Base URL for absolute canonical URLs (e.g., 'https://loopin.app')
                 If None, uses settings.SITE_URL or defaults to relative URLs
        
    Returns:
        Dictionary of SEO metadata tags
        
    Example:
        {
            'title': 'Tech Founder Meetup in Bangalore | Loopin',
            'description': 'Join us for an exciting tech meetup...',
            'canonical_url': 'https://loopin.app/in/bangalore/events/tech-meetup--a9x3k',
            'og_title': 'Tech Founder Meetup',
            'og_description': 'Join us for an exciting tech meetup...',
            'og_image': 'https://example.com/cover.jpg',
            'og_url': 'https://loopin.app/in/bangalore/events/tech-meetup--a9x3k',
            'og_type': 'website',
            'twitter_card': 'summary_large_image',
            ...
        }
    """
    # Get base URL
    if not base_url:
        base_url = getattr(settings, 'SITE_URL', '')
    
    # Generate title
    city_name = event.venue.city if event.venue else (event.venue_text or 'Unknown')
    title = f"{event.title} in {city_name} | Loopin"
    
    # Generate description from event description
    description = event.description[:160] if event.description else f"Join us for {event.title} in {city_name}"
    if len(description) > 160:
        description = description[:157] + "..."
    
    # Get canonical URL
    canonical_path = event.canonical_url or f"/events/{event.canonical_id}"
    canonical_url = f"{base_url}{canonical_path}" if base_url else canonical_path
    
    # Get cover image (first image from cover_images array)
    og_image = ""
    if event.cover_images and len(event.cover_images) > 0:
        og_image = event.cover_images[0]
    elif hasattr(settings, 'DEFAULT_EVENT_IMAGE'):
        og_image = settings.DEFAULT_EVENT_IMAGE
    
    # Build metadata dictionary
    metadata = {
        # Basic SEO
        'title': title,
        'description': description,
        'canonical_url': canonical_url,
        
        # OpenGraph tags
        'og_title': event.title,
        'og_description': description,
        'og_image': og_image,
        'og_url': canonical_url,
        'og_type': 'website',
        'og_site_name': 'Loopin',
        
        # Twitter Card tags
        'twitter_card': 'summary_large_image',
        'twitter_title': event.title,
        'twitter_description': description,
        'twitter_image': og_image,
        
        # Additional metadata
        'event_id': event.canonical_id,
        'event_slug': event.slug,
        'event_start_time': event.start_time.isoformat() if event.start_time else None,
        'event_end_time': event.end_time.isoformat() if event.end_time else None,
        'event_location': event.venue.name if event.venue else event.venue_text,
    }
    
    return metadata


def generate_event_meta_tags_html(event: Event, base_url: Optional[str] = None) -> str:
    """
    Generate HTML meta tags string for embedding in page <head>.
    
    Args:
        event: Event instance
        base_url: Base URL for absolute canonical URLs
        
    Returns:
        HTML string with all meta tags
    """
    metadata = generate_event_seo_metadata(event, base_url)
    
    tags = []
    
    # Basic meta tags
    tags.append(f'<title>{metadata["title"]}</title>')
    tags.append(f'<meta name="description" content="{metadata["description"]}">')
    tags.append(f'<link rel="canonical" href="{metadata["canonical_url"]}">')
    
    # OpenGraph tags
    tags.append(f'<meta property="og:title" content="{metadata["og_title"]}">')
    tags.append(f'<meta property="og:description" content="{metadata["og_description"]}">')
    tags.append(f'<meta property="og:image" content="{metadata["og_image"]}">')
    tags.append(f'<meta property="og:url" content="{metadata["og_url"]}">')
    tags.append(f'<meta property="og:type" content="{metadata["og_type"]}">')
    tags.append(f'<meta property="og:site_name" content="{metadata["og_site_name"]}">')
    
    # Twitter Card tags
    tags.append(f'<meta name="twitter:card" content="{metadata["twitter_card"]}">')
    tags.append(f'<meta name="twitter:title" content="{metadata["twitter_title"]}">')
    tags.append(f'<meta name="twitter:description" content="{metadata["twitter_description"]}">')
    if metadata["twitter_image"]:
        tags.append(f'<meta name="twitter:image" content="{metadata["twitter_image"]}">')
    
    return '\n'.join(tags)
