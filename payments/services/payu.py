"""
PayU Payment Gateway Integration Service

This module handles all PayU-specific operations:
- Hash generation for payment requests
- Hash verification for callbacks and webhooks
- Payload construction for redirects
- Security: Never stores salt or hashes in database

SECURITY RULES:
- All credentials from environment variables
- Hash generation is backend-only
- Never persist salt or hash values
- Fail loudly on hash mismatches
"""

import hashlib
import os
from typing import Dict, Any, Optional
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from decouple import config
from core.utils.logger import get_logger
from core.exceptions import ValidationError, ExternalServiceError

logger = get_logger(__name__)


class PayUService:
    """
    PayU payment gateway service.
    
    Handles:
    - Payment hash generation
    - Reverse hash verification
    - Redirect payload creation
    - Webhook signature verification
    """
    
    # PayU configuration from environment
    MERCHANT_KEY = config('PAYU_MERCHANT_KEY', default='')
    MERCHANT_SALT = config('PAYU_MERCHANT_SALT', default='')
    PAYMENT_URL = config('PAYU_PAYMENT_URL', default='https://secure.payu.in/_payment')
    SUCCESS_URL = config('PAYU_SUCCESS_URL', default='/payments/payu/success')
    FAILURE_URL = config('PAYU_FAILURE_URL', default='/payments/payu/failure')
    
    @classmethod
    def _validate_config(cls):
        """Validate PayU configuration is present"""
        if not cls.MERCHANT_KEY:
            raise ExternalServiceError(
                "PayU merchant key not configured. Set PAYU_MERCHANT_KEY environment variable.",
                code="PAYU_CONFIG_MISSING"
            )
        if not cls.MERCHANT_SALT:
            raise ExternalServiceError(
                "PayU merchant salt not configured. Set PAYU_MERCHANT_SALT environment variable.",
                code="PAYU_CONFIG_MISSING"
            )
    
    @classmethod
    def generate_hash(cls, hash_string: str) -> str:
        """
        Generate SHA-512 hash for PayU.
        
        Args:
            hash_string: String to hash (pipe-separated values)
            
        Returns:
            str: SHA-512 hash in lowercase hex
        """
        cls._validate_config()
        
        try:
            hash_obj = hashlib.sha512(hash_string.encode('utf-8'))
            return hash_obj.hexdigest().lower()
        except Exception as e:
            logger.error(f"PayU hash generation failed: {e}")
            raise ExternalServiceError(
                f"Failed to generate payment hash: {str(e)}",
                code="PAYU_HASH_GENERATION_FAILED"
            )
    
    @classmethod
    def generate_payment_hash(
        cls,
        txnid: str,
        amount: Decimal,
        productinfo: str,
        firstname: str,
        email: str,
    ) -> str:
        """
        Generate PayU payment hash for redirect.
        
        Hash format: key|txnid|amount|productinfo|firstname|email|||||||||||salt
        
        Args:
            txnid: Transaction ID (order_id)
            amount: Payment amount
            productinfo: Product description
            firstname: Customer first name
            email: Customer email
            
        Returns:
            str: SHA-512 hash
        """
        cls._validate_config()
        
        # Format amount to 2 decimal places
        amount_str = f"{float(amount):.2f}"
        
        # Build hash string: key|txnid|amount|productinfo|firstname|email|||||||||||salt
        hash_string = (
            f"{cls.MERCHANT_KEY}|{txnid}|{amount_str}|{productinfo}|"
            f"{firstname}|{email}|||||||||||{cls.MERCHANT_SALT}"
        )
        
        logger.debug(f"PayU hash string (without salt): {hash_string.split('|')[:-1]}")
        hash_value = cls.generate_hash(hash_string)
        logger.info(f"PayU payment hash generated for txnid: {txnid}")
        
        return hash_value
    
    @classmethod
    def verify_reverse_hash(
        cls,
        status: str,
        email: str,
        firstname: str,
        productinfo: str,
        amount: str,
        txnid: str,
        received_hash: str,
    ) -> bool:
        """
        Verify PayU reverse hash from callback.
        
        Reverse hash format: salt|status|||||||||||email|firstname|productinfo|amount|txnid|key
        
        Args:
            status: Payment status from PayU
            email: Customer email
            firstname: Customer first name
            productinfo: Product description
            amount: Payment amount (string)
            txnid: Transaction ID
            received_hash: Hash received from PayU
            
        Returns:
            bool: True if hash matches, False otherwise
        """
        cls._validate_config()
        
        try:
            # Build reverse hash string: salt|status|||||||||||email|firstname|productinfo|amount|txnid|key
            hash_string = (
                f"{cls.MERCHANT_SALT}|{status}|||||||||||{email}|{firstname}|"
                f"{productinfo}|{amount}|{txnid}|{cls.MERCHANT_KEY}"
            )
            
            calculated_hash = cls.generate_hash(hash_string)
            
            # Compare hashes (case-insensitive)
            is_valid = calculated_hash.lower() == received_hash.lower()
            
            if not is_valid:
                logger.warning(
                    f"PayU hash verification failed for txnid: {txnid}. "
                    f"Expected: {calculated_hash}, Received: {received_hash}"
                )
            else:
                logger.info(f"PayU hash verified successfully for txnid: {txnid}")
            
            return is_valid
            
        except Exception as e:
            logger.error(f"PayU reverse hash verification error: {e}")
            return False
    
    @classmethod
    def create_redirect_payload(
        cls,
        order_id: str,
        amount: Decimal,
        productinfo: str,
        firstname: str,
        email: str,
        phone: str,
        base_url: str,
    ) -> Dict[str, Any]:
        """
        Create PayU redirect payload for frontend.
        
        Args:
            order_id: Payment order ID (used as txnid)
            amount: Payment amount
            productinfo: Product description
            firstname: Customer first name
            email: Customer email
            phone: Customer phone number
            base_url: Base URL for success/failure callbacks
            
        Returns:
            dict: PayU redirect payload with hash
        """
        cls._validate_config()
        
        # Generate payment hash
        hash_value = cls.generate_payment_hash(
            txnid=order_id,
            amount=amount,
            productinfo=productinfo,
            firstname=firstname,
            email=email,
        )
        
        # Format amount to 2 decimal places
        amount_str = f"{float(amount):.2f}"
        
        # Build success and failure URLs
        success_url = f"{base_url.rstrip('/')}{cls.SUCCESS_URL}"
        failure_url = f"{base_url.rstrip('/')}{cls.FAILURE_URL}"
        
        payload = {
            "key": cls.MERCHANT_KEY,
            "txnid": order_id,
            "amount": amount_str,
            "productinfo": productinfo,
            "firstname": firstname,
            "email": email,
            "phone": phone,
            "surl": success_url,
            "furl": failure_url,
            "hash": hash_value,
        }
        
        logger.info(f"PayU redirect payload created for order: {order_id}")
        return payload
    
    @classmethod
    def extract_callback_data(cls, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract and validate callback data from PayU response.
        
        Args:
            request_data: Request data from PayU callback
            
        Returns:
            dict: Extracted callback data
            
        Raises:
            ValidationError: If required fields are missing
        """
        required_fields = ['status', 'txnid', 'amount', 'productinfo', 'firstname', 'email', 'hash']
        
        missing_fields = [field for field in required_fields if field not in request_data]
        if missing_fields:
            raise ValidationError(
                f"Missing required PayU callback fields: {', '.join(missing_fields)}",
                code="PAYU_CALLBACK_INCOMPLETE"
            )
        
        return {
            'status': request_data.get('status'),
            'txnid': request_data.get('txnid'),
            'amount': request_data.get('amount'),
            'productinfo': request_data.get('productinfo'),
            'firstname': request_data.get('firstname'),
            'email': request_data.get('email'),
            'hash': request_data.get('hash'),
            'phone': request_data.get('phone', ''),
            'mihpayid': request_data.get('mihpayid', ''),
            'bank_ref_num': request_data.get('bank_ref_num', ''),
            'bankcode': request_data.get('bankcode', ''),
            'error': request_data.get('error', ''),
            'error_Message': request_data.get('error_Message', ''),
        }

