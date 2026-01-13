"""
Production-grade slug generation for SEO-friendly URLs.

This module provides server-side slug generation with proper normalization,
collision handling, and versioning support.

Design Principles:
- Server-side only: Never accept user-provided slugs
- SEO-optimized: Lowercase, ASCII-only, dash-separated
- Collision-safe: Handles duplicates with versioning
- Immutable identity: Slug changes don't break canonical URLs
"""

import re
import unicodedata
from typing import Optional


# Maximum slug length (70 characters for SEO best practices)
MAX_SLUG_LENGTH = 70


def normalize_to_ascii(text: str) -> str:
    """
    Normalize Unicode text to ASCII by removing accents and special characters.
    
    Args:
        text: Input text (may contain Unicode)
        
    Returns:
        ASCII-normalized text
        
    Example:
        >>> normalize_to_ascii("Café")
        'Cafe'
        >>> normalize_to_ascii("São Paulo")
        'Sao Paulo'
    """
    # Normalize to NFD (decomposed form) to separate base characters from accents
    normalized = unicodedata.normalize('NFD', text)
    
    # Remove combining characters (accents, diacritics)
    ascii_text = ''.join(
        char for char in normalized
        if unicodedata.category(char) != 'Mn'
    )
    
    return ascii_text


def generate_slug(text: str, max_length: int = MAX_SLUG_LENGTH) -> str:
    """
    Generate a SEO-friendly slug from text.
    
    Rules:
    - Lowercase only
    - ASCII characters only (Unicode normalized)
    - Dash-separated words
    - No leading/trailing dashes
    - No consecutive dashes
    - Maximum 70 characters
    - Returns 'event' as fallback if normalization results in empty string
    
    Args:
        text: Source text (typically event title)
        max_length: Maximum slug length (default: 70)
        
    Returns:
        Generated slug string (never empty, defaults to 'event' if normalization fails)
        
    Example:
        >>> generate_slug("Tech Founder Meetup")
        'tech-founder-meetup'
        >>> generate_slug("São Paulo Tech Conference 2024")
        'sao-paulo-tech-conference-2024'
        >>> generate_slug("🎉🎊")  # Emoji-only title
        'event'
    """
    if not text:
        return "event"
    
    # Normalize to ASCII (remove accents)
    text = normalize_to_ascii(text)
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces and underscores with dashes
    text = re.sub(r'[\s_]+', '-', text)
    
    # Remove all non-alphanumeric characters except dashes
    text = re.sub(r'[^a-z0-9\-]', '', text)
    
    # Replace multiple consecutive dashes with single dash
    text = re.sub(r'-+', '-', text)
    
    # Remove leading and trailing dashes
    text = text.strip('-')
    
    # Truncate to max_length if needed
    if len(text) > max_length:
        # Truncate at word boundary (before last dash within limit)
        truncated = text[:max_length]
        last_dash = truncated.rfind('-')
        if last_dash > max_length * 0.8:  # If dash is in last 20%, use it
            text = truncated[:last_dash]
        else:
            text = truncated
    
    # Final cleanup: remove any trailing dashes after truncation
    text = text.rstrip('-')
    
    # Fallback: if slug is empty after normalization (e.g., emoji-only titles), use 'event'
    if not text:
        return "event"
    
    return text


def generate_unique_slug(base_slug: str, existing_slugs: set, max_attempts: int = 100) -> str:
    """
    Generate a unique slug by appending version numbers if needed.
    
    Args:
        base_slug: Base slug to make unique
        existing_slugs: Set of existing slugs to avoid collisions
        max_attempts: Maximum attempts to find unique slug
        
    Returns:
        Unique slug (may be base_slug or base_slug-N)
        
    Example:
        >>> existing = {'tech-meetup', 'tech-meetup-1'}
        >>> generate_unique_slug('tech-meetup', existing)
        'tech-meetup-2'
    """
    if base_slug not in existing_slugs:
        return base_slug
    
    # Try appending version numbers
    for i in range(1, max_attempts + 1):
        candidate = f"{base_slug}-{i}"
        if candidate not in existing_slugs:
            return candidate
    
    # Fallback: append timestamp if all attempts fail
    import time
    timestamp = int(time.time())
    return f"{base_slug}-{timestamp}"


def extract_canonical_id_from_url(url_path: str) -> Optional[str]:
    """
    Extract canonical_id from canonical URL format.
    
    Expected format: /{country_code}/{city_slug}/events/{slug}--{canonical_id}
    
    Args:
        url_path: URL path to parse
        
    Returns:
        Extracted canonical_id or None if format doesn't match
        
    Example:
        >>> extract_canonical_id_from_url('/in/bangalore/events/tech-meetup--a9x3k')
        'a9x3k'
        >>> extract_canonical_id_from_url('/invalid/path')
        None
    """
    # Pattern: /country/city/events/slug--canonical_id
    pattern = r'/[^/]+/[^/]+/events/[^/]+--([a-zA-Z0-9]{5,8})$'
    match = re.search(pattern, url_path)
    
    if match:
        return match.group(1)
    
    return None


def build_canonical_url(country_code: str, city_slug: str, slug: str, canonical_id: str) -> str:
    """
    Build canonical URL from components.
    
    Format: /{country_code}/{city_slug}/events/{slug}--{canonical_id}
    
    Args:
        country_code: ISO 3166-1 alpha-2 country code (e.g., 'in', 'us')
        city_slug: URL-safe city name slug
        slug: Event slug
        canonical_id: Event canonical ID
        
    Returns:
        Canonical URL path
        
    Example:
        >>> build_canonical_url('in', 'bangalore', 'tech-meetup', 'a9x3k')
        '/in/bangalore/events/tech-meetup--a9x3k'
    """
    return f"/{country_code}/{city_slug}/events/{slug}--{canonical_id}"
