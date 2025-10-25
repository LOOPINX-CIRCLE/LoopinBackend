"""
Database utilities for handling IPv4/IPv6 connection issues with cloud providers.

This module provides utilities to force IPv4 connections when deploying to platforms
like Render that have IPv6 outbound restrictions with services like Supabase.
"""

import socket
import os
from urllib.parse import urlparse, urlunparse
import logging

logger = logging.getLogger(__name__)


def force_ipv4_database_url(database_url):
    """
    Force IPv4 resolution for database connections.
    
    IMPORTANT: For Supabase connection pooler URLs (containing 'pooler.supabase.com'),
    we DON'T resolve to IP because the pooler requires the original hostname for
    SSL/TLS verification and tenant authentication.
    
    Args:
        database_url (str): The original database URL
        
    Returns:
        str: Modified database URL with IPv4 host resolution (or original if Supabase pooler)
    """
    if not database_url or database_url.startswith('sqlite'):
        return database_url
    
    try:
        # Parse the database URL
        parsed = urlparse(database_url)
        
        # Extract the hostname
        hostname = parsed.hostname
        
        if not hostname:
            return database_url
        
        # CRITICAL: Don't resolve Supabase pooler hostnames to IP
        # The pooler needs the original hostname for authentication
        if 'pooler.supabase.com' in hostname or 'supabase.co' in hostname:
            logger.info(f"Supabase pooler detected ({hostname}). Using original URL without IPv4 resolution.")
            return database_url
        
        # Try to resolve to IPv4 address for non-pooler connections
        try:
            # Get IPv4 address only (AF_INET = IPv4)
            ipv4_address = socket.getaddrinfo(
                hostname, 
                None, 
                socket.AF_INET,  # Force IPv4
                socket.SOCK_STREAM
            )[0][4][0]
            
            logger.info(f"Resolved {hostname} to IPv4: {ipv4_address}")
            
            # Replace hostname with IPv4 address in netloc
            if parsed.port:
                new_netloc = f"{parsed.username}:{parsed.password}@{ipv4_address}:{parsed.port}"
            else:
                new_netloc = f"{parsed.username}:{parsed.password}@{ipv4_address}"
            
            # Reconstruct the URL
            new_url = urlunparse((
                parsed.scheme,
                new_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
            
            logger.info(f"Modified database URL to use IPv4: {new_url.split('@')[0]}@...")
            return new_url
            
        except socket.gaierror as e:
            logger.warning(f"Could not resolve {hostname} to IPv4: {e}. Using original URL.")
            return database_url
        except IndexError as e:
            logger.warning(f"No IPv4 address found for {hostname}: {e}. Using original URL.")
            return database_url
            
    except Exception as e:
        logger.error(f"Error processing database URL: {e}. Using original URL.")
        return database_url


def get_database_config(database_url=None):
    """
    Get database configuration with IPv4 enforcement for cloud deployments.
    
    Args:
        database_url (str, optional): Database URL. If not provided, reads from DATABASE_URL env var.
        
    Returns:
        dict: Database configuration suitable for Django DATABASES setting
    """
    import dj_database_url
    
    if database_url is None:
        database_url = os.environ.get('DATABASE_URL', 'sqlite:///db.sqlite3')
    
    # Check if we're running on Render (or similar platforms with IPv6 restrictions)
    is_render = os.environ.get('RENDER', False) or os.environ.get('IS_RENDER', False)
    force_ipv4 = os.environ.get('FORCE_IPV4_DB', 'false').lower() == 'true'
    
    # Force IPv4 resolution if on Render or explicitly requested
    if is_render or force_ipv4:
        logger.info("Forcing IPv4 database connection for cloud deployment")
        database_url = force_ipv4_database_url(database_url)
    
    # Parse and return the database configuration
    return dj_database_url.parse(database_url)

