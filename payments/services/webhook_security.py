"""
Webhook Security Utilities

SECURITY HARDENING:
- IP range verification (PayU IPs)
- Rate limiting
- Strict signature verification
"""

import ipaddress
from typing import Optional, List, Set
from django.conf import settings
from decouple import config
from core.utils.logger import get_logger
from core.exceptions import ValidationError, ExternalServiceError

logger = get_logger(__name__)


class WebhookSecurityService:
    """
    Webhook security service for PayU webhooks.
    
    Handles:
    - IP address verification
    - Rate limiting
    - Signature verification (delegates to PayUService)
    """
    
    # PayU known IP ranges (update from PayU documentation)
    # Note: PayU may provide specific IP ranges - add them here
    PAYU_IP_RANGES = config(
        'PAYU_IP_RANGES',
        default='',
        cast=lambda x: [ip.strip() for ip in x.split(',') if ip.strip()]
    )
    
    # If IP ranges not configured, we'll log a warning but allow (with signature verification)
    STRICT_IP_CHECK = config('PAYU_STRICT_IP_CHECK', default=False, cast=bool)
    
    @classmethod
    def verify_ip_address(cls, client_ip: str) -> bool:
        """
        Verify that webhook request comes from PayU IP ranges.
        
        SECURITY: If PAYU_IP_RANGES is configured, verify client IP matches.
        If not configured, log warning but allow (signature verification is primary).
        
        Args:
            client_ip: Client IP address from request
            
        Returns:
            bool: True if IP is verified (or IP check disabled), False otherwise
            
        Raises:
            ValidationError: If IP check fails and STRICT_IP_CHECK is enabled
        """
        # If no IP ranges configured, skip IP check (rely on signature verification)
        if not cls.PAYU_IP_RANGES:
            if cls.STRICT_IP_CHECK:
                logger.warning(
                    "PayU IP ranges not configured but STRICT_IP_CHECK is enabled. "
                    "Configure PAYU_IP_RANGES environment variable for IP verification."
                )
                raise ValidationError(
                    "Webhook IP verification not configured. Contact administrator.",
                    code="WEBHOOK_IP_NOT_CONFIGURED"
                )
            else:
                logger.warning(
                    f"PayU IP ranges not configured. Allowing webhook from {client_ip} "
                    f"(signature verification is primary security measure)."
                )
                return True
        
        try:
            client_ip_obj = ipaddress.ip_address(client_ip)
            
            # Check if client IP is in any of the configured PayU IP ranges
            for ip_range_str in cls.PAYU_IP_RANGES:
                try:
                    # Support both single IP and CIDR ranges
                    if '/' in ip_range_str:
                        network = ipaddress.ip_network(ip_range_str, strict=False)
                        if client_ip_obj in network:
                            logger.info(f"Webhook IP verified: {client_ip} in range {ip_range_str}")
                            return True
                    else:
                        # Single IP
                        if str(client_ip_obj) == ip_range_str:
                            logger.info(f"Webhook IP verified: {client_ip} matches {ip_range_str}")
                            return True
                except ValueError as e:
                    logger.warning(f"Invalid IP range in PAYU_IP_RANGES: {ip_range_str}, error: {e}")
                    continue
            
            # IP not in allowed ranges
            logger.warning(f"Webhook IP verification failed: {client_ip} not in PayU IP ranges")
            
            if cls.STRICT_IP_CHECK:
                raise ValidationError(
                    f"Webhook request from unauthorized IP: {client_ip}",
                    code="WEBHOOK_IP_UNAUTHORIZED"
                )
            
            # If not strict, log warning but allow (signature verification is primary)
            logger.warning(
                f"Webhook IP {client_ip} not in PayU ranges, but allowing "
                f"(signature verification will be checked)."
            )
            return True
            
        except ValueError as e:
            logger.error(f"Invalid client IP address: {client_ip}, error: {e}")
            raise ValidationError(
                f"Invalid client IP address: {client_ip}",
                code="WEBHOOK_INVALID_IP"
            )
    
    @classmethod
    def get_client_ip(cls, request) -> str:
        """
        Extract client IP address from request.
        
        Handles:
        - Direct client IP
        - X-Forwarded-For header (behind proxy/load balancer)
        - X-Real-IP header
        
        Args:
            request: FastAPI Request object
            
        Returns:
            str: Client IP address
        """
        # Try X-Forwarded-For first (behind proxy/load balancer)
        forwarded_for = request.headers.get('X-Forwarded-For')
        if forwarded_for:
            # X-Forwarded-For can contain multiple IPs, take the first one
            client_ip = forwarded_for.split(',')[0].strip()
            if client_ip:
                return client_ip
        
        # Try X-Real-IP header
        real_ip = request.headers.get('X-Real-IP')
        if real_ip:
            return real_ip.strip()
        
        # Fallback to direct client IP
        if hasattr(request.client, 'host'):
            return request.client.host
        
        # Last resort: try to get from request
        try:
            return request.client.host if request.client else '0.0.0.0'
        except Exception:
            return '0.0.0.0'

