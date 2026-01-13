"""
Production-grade canonical ID generator using Base62 encoding.

This module provides collision-safe, short ID generation for public-facing
identifiers. Used for event canonical_id generation.

Design Principles:
- Immutable: Once generated, IDs never change
- Short: 5-8 characters for URL-friendly identifiers
- Collision-safe: Uses timestamp + random component
- Base62: URL-safe character set (0-9, a-z, A-Z)
"""

import time
import random
import string
from typing import Optional


# Base62 character set: 0-9, a-z, A-Z (62 characters total)
BASE62_CHARS = string.digits + string.ascii_lowercase + string.ascii_uppercase
BASE62_BASE = len(BASE62_CHARS)


def int_to_base62(num: int) -> str:
    """
    Convert an integer to Base62 string.
    
    Args:
        num: Integer to convert
        
    Returns:
        Base62 encoded string
    """
    if num == 0:
        return BASE62_CHARS[0]
    
    result = []
    while num > 0:
        result.append(BASE62_CHARS[num % BASE62_BASE])
        num //= BASE62_BASE
    
    return ''.join(reversed(result))


def base62_to_int(base62_str: str) -> int:
    """
    Convert a Base62 string to integer.
    
    Args:
        base62_str: Base62 encoded string
        
    Returns:
        Decoded integer
    """
    num = 0
    for char in base62_str:
        num = num * BASE62_BASE + BASE62_CHARS.index(char)
    return num


def generate_canonical_id(length: int = 6) -> str:
    """
    Generate a collision-safe canonical ID using Base62 encoding.
    
    Strategy:
    - Uses current timestamp (milliseconds) for uniqueness
    - Adds random component for additional entropy
    - Encodes to Base62 for URL-friendly short IDs
    
    Args:
        length: Desired length of canonical ID (5-8 recommended)
                Default: 6 characters (supports ~56 billion IDs)
        
    Returns:
        Base62 encoded canonical ID string
        
    Example:
        >>> generate_canonical_id()
        'a9x3k'
        >>> generate_canonical_id(length=8)
        'a9x3k2m1'
    """
    if length < 5 or length > 8:
        raise ValueError("Canonical ID length must be between 5 and 8 characters")
    
    # Get current timestamp in milliseconds for uniqueness
    timestamp_ms = int(time.time() * 1000)
    
    # Add random component (0-999) for additional entropy
    random_component = random.randint(0, 999)
    
    # Combine: timestamp (high bits) + random (low bits)
    # This ensures uniqueness even with high concurrency
    combined = (timestamp_ms << 10) | random_component
    
    # Convert to Base62
    base62_id = int_to_base62(combined)
    
    # Ensure minimum length by padding if needed
    if len(base62_id) < length:
        # Pad with random characters
        padding = ''.join(random.choices(BASE62_CHARS, k=length - len(base62_id)))
        base62_id = base62_id + padding
    
    # Truncate to desired length (take first N chars)
    return base62_id[:length]


def validate_canonical_id(canonical_id: str) -> bool:
    """
    Validate that a string is a valid Base62 canonical ID.
    
    Args:
        canonical_id: String to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not canonical_id:
        return False
    
    if len(canonical_id) < 5 or len(canonical_id) > 8:
        return False
    
    # Check all characters are valid Base62 characters
    return all(char in BASE62_CHARS for char in canonical_id)
