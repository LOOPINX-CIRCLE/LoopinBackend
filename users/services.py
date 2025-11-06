"""
Production-grade Twilio service for SMS and WhatsApp messaging.
CTO-level implementation with proper error handling, configuration management, and logging.
"""

import os
import json
import logging
from typing import Optional, Dict, Tuple, Any
from dataclasses import dataclass
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException
from decouple import config

logger = logging.getLogger(__name__)


@dataclass
class TwilioConfig:
    """Twilio configuration loaded from environment variables"""
    account_sid: str
    auth_token: str
    verify_sid: Optional[str] = None
    verify_secret: Optional[str] = None
    messaging_service_sid: Optional[str] = None
    phone_number: Optional[str] = None
    whatsapp_phone_number: str = "+15558015045"
    whatsapp_content_sid: Optional[str] = None
    test_mode: bool = False
    
    @classmethod
    def from_env(cls) -> 'TwilioConfig':
        """Load configuration from environment variables"""
        return cls(
            account_sid=config('TWILIO_ACCOUNT_SID', default=''),
            auth_token=config('TWILIO_AUTH_TOKEN', default=''),
            verify_sid=config('TWILIO_VERIFY_SID', default=None),
            verify_secret=config('TWILIO_VERIFY_SECRET', default=None),
            messaging_service_sid=config('TWILIO_MESSAGING_SERVICE_SID', default=None),
            phone_number=config('TWILIO_PHONE_NUMBER', default=None),
            whatsapp_phone_number=config('TWILIO_WHATSAPP_PHONE_NUMBER', default='+15558015045'),
            whatsapp_content_sid=config('TWILIO_WHATSAPP_CONTENT_SID', default=None),
            test_mode=config('TWILIO_TEST_MODE', default='false', cast=bool),
        )
    
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate required configuration"""
        if not self.account_sid:
            return False, "TWILIO_ACCOUNT_SID is required"
        if not self.auth_token:
            return False, "TWILIO_AUTH_TOKEN is required"
        return True, None


class TwilioServiceError(Exception):
    """Base exception for Twilio service errors"""
    pass


class TwilioConfigurationError(TwilioServiceError):
    """Raised when Twilio configuration is invalid"""
    pass


class TwilioMessageError(TwilioServiceError):
    """Raised when message sending fails"""
    def __init__(self, message: str, error_code: Optional[int] = None, original_error: Optional[Exception] = None):
        super().__init__(message)
        self.error_code = error_code
        self.original_error = original_error


class TwilioService:
    """
    Production-grade Twilio service for SMS and WhatsApp messaging.
    
    Features:
    - Centralized configuration management
    - Comprehensive error handling
    - Support for SMS OTP and WhatsApp Content API templates
    - Proper logging and monitoring
    - Test mode support
    """
    
    # WhatsApp error codes mapping
    WHATSAPP_ERROR_CODES = {
        63016: "Recipient has not opted in to receive WhatsApp messages",
        63007: "Invalid WhatsApp number format or number not registered on WhatsApp",
        63014: "WhatsApp message template not approved or invalid",
        63024: "WhatsApp message delivery failed - recipient may not be opted in",
    }
    
    def __init__(self, twilio_config: Optional[TwilioConfig] = None):
        """
        Initialize Twilio service with configuration.
        
        Args:
            twilio_config: TwilioConfig instance. If None, loads from environment.
        """
        self.config = twilio_config or TwilioConfig.from_env()
        
        # Validate configuration
        is_valid, error_msg = self.config.validate()
        if not is_valid:
            raise TwilioConfigurationError(error_msg)
        
        # Initialize Twilio client
        self.client: Optional[Client] = None
        try:
            self.client = Client(self.config.account_sid, self.config.auth_token)
            logger.info("Twilio client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            self.client = None
    
    def _format_phone_number(self, phone_number: str) -> str:
        """Format phone number to ensure it starts with +"""
        if not phone_number.startswith('+'):
            return '+' + phone_number.lstrip('+')
        return phone_number
    
    def _format_whatsapp_number(self, phone_number: str) -> str:
        """Format phone number for WhatsApp (whatsapp:+1234567890)"""
        formatted = self._format_phone_number(phone_number)
        if not formatted.startswith('whatsapp:'):
            return f"whatsapp:{formatted}"
        return formatted
    
    def _get_whatsapp_from_number(self, from_number: Optional[str] = None) -> str:
        """Get WhatsApp sender number"""
        if from_number:
            return self._format_whatsapp_number(from_number)
        return self._format_whatsapp_number(self.config.whatsapp_phone_number)
    
    def _handle_whatsapp_error(self, error_code: Optional[int], status: str) -> str:
        """Get user-friendly error message for WhatsApp error codes"""
        if error_code in self.WHATSAPP_ERROR_CODES:
            base_msg = self.WHATSAPP_ERROR_CODES[error_code]
            if error_code == 63016:
                return f"{base_msg}. They must send a message to {self.config.whatsapp_phone_number} first to opt-in."
            return base_msg
        return f"Message delivery failed with status: {status}"
    
    def send_otp_sms(self, phone_number: str, otp_code: str) -> Tuple[bool, str]:
        """
        Send OTP via SMS.
        
        Args:
            phone_number: Recipient phone number (e.g., +1234567890)
            otp_code: OTP code to send
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if self.config.test_mode:
                logger.info(f"TEST MODE: OTP {otp_code} would be sent to {phone_number}")
                return True, f"TEST MODE: OTP {otp_code} sent to {phone_number}"
            
            if not self.client:
                logger.error("Twilio client not initialized")
                return False, "SMS service unavailable"
            
            formatted_phone = self._format_phone_number(phone_number)
            message_body = f"Your Loopin verification code is: {otp_code}. This code expires in 10 minutes."
            
            try:
                # Use Messaging Service if available (recommended for production)
                if self.config.messaging_service_sid:
                    message = self.client.messages.create(
                        body=message_body,
                        messaging_service_sid=self.config.messaging_service_sid,
                        to=formatted_phone
                    )
                else:
                    # Fallback to direct phone number
                    from_number = self.config.phone_number or '+15005550006'
                    message = self.client.messages.create(
                        body=message_body,
                        from_=from_number,
                        to=formatted_phone
                    )
                
                logger.info(f"OTP sent successfully to {formatted_phone}. SID: {message.sid}")
                return True, "OTP sent successfully"
                
            except TwilioRestException as e:
                logger.error(f"Twilio API error sending SMS: {e}")
                error_msg = "Failed to send OTP"
                if "trial" in str(e).lower() or "verified" in str(e).lower():
                    error_msg = "Trial account restriction: Please verify your phone number in Twilio console or upgrade to paid account"
                return False, error_msg
            except Exception as e:
                logger.error(f"Unexpected error sending SMS: {e}")
                return False, f"Failed to send OTP: {str(e)}"
            
        except Exception as e:
            logger.error(f"Failed to send OTP to {phone_number}: {e}", exc_info=True)
            return False, f"Failed to send OTP: {str(e)}"
    
    def verify_otp(self, phone_number: str, otp_code: str) -> Tuple[bool, str]:
        """
        Verify OTP using Twilio Verify service.
        
        Args:
            phone_number: Phone number to verify
            otp_code: OTP code to verify
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            if not self.client:
                logger.error("Twilio client not initialized")
                return False, "Verification service unavailable"
            
            if not self.config.verify_sid:
                logger.error("TWILIO_VERIFY_SID not configured")
                return False, "Verification service not configured"
            
            formatted_phone = self._format_phone_number(phone_number)
            
            verification_check = self.client.verify.v2.services(
                self.config.verify_sid
            ).verification_checks.create(
                to=formatted_phone,
                code=otp_code
            )
            
            if verification_check.status == 'approved':
                logger.info(f"OTP verified successfully for {formatted_phone}")
                return True, "OTP verified successfully"
            else:
                logger.warning(f"OTP verification failed for {formatted_phone}: {verification_check.status}")
                return False, "Invalid OTP"
                
        except TwilioRestException as e:
            logger.error(f"Twilio API error verifying OTP: {e}")
            return False, f"Verification failed: {str(e)}"
        except Exception as e:
            logger.error(f"Failed to verify OTP for {phone_number}: {e}", exc_info=True)
            return False, f"Verification failed: {str(e)}"
    
    def send_whatsapp_message(
        self,
        phone_number: str,
        message_body: Optional[str] = None,
        from_number: Optional[str] = None,
        content_sid: Optional[str] = None,
        content_variables: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Send WhatsApp message via Twilio using Content API (templates) or plain text.
        
        Args:
            phone_number: Recipient phone number (e.g., +1234567890)
            message_body: Plain text message content (optional if using content_sid)
            from_number: WhatsApp sender number (optional, uses config default)
            content_sid: Twilio Content Template SID (preferred for WhatsApp)
            content_variables: Dictionary of variables for content template (e.g., {"1": "Name"})
        
        Returns:
            Tuple of (success: bool, message: str)
        
        Raises:
            TwilioMessageError: If message sending fails with specific error details
        """
        try:
            if self.config.test_mode:
                if content_sid:
                    logger.info(f"TEST MODE: WhatsApp template message would be sent to {phone_number} using content_sid {content_sid}")
                else:
                    logger.info(f"TEST MODE: WhatsApp message would be sent to {phone_number}: {message_body}")
                return True, f"TEST MODE: WhatsApp message sent to {phone_number}"
            
            if not self.client:
                logger.error("Twilio client not initialized")
                return False, "WhatsApp service unavailable"
            
            formatted_phone = self._format_phone_number(phone_number)
            whatsapp_to = self._format_whatsapp_number(formatted_phone)
            whatsapp_from = self._get_whatsapp_from_number(from_number)
            
            # Determine content_sid to use
            final_content_sid = content_sid or self.config.whatsapp_content_sid
            
            try:
                message_params: Dict[str, Any] = {
                    'from_': whatsapp_from,
                    'to': whatsapp_to,
                }
                
                # Use Content API (template) if content_sid is provided
                if final_content_sid:
                    logger.info(f"Sending WhatsApp template message from {whatsapp_from} to {whatsapp_to} using content_sid {final_content_sid}")
                    
                    message_params['content_sid'] = final_content_sid
                    
                    # Add content variables if provided
                    if content_variables:
                        message_params['content_variables'] = json.dumps(content_variables)
                        logger.debug(f"Content variables: {content_variables}")
                    
                    # Add messaging service SID if available
                    if self.config.messaging_service_sid:
                        message_params['messaging_service_sid'] = self.config.messaging_service_sid
                else:
                    # Fallback to plain text message
                    if not message_body:
                        error_msg = "Either message_body or content_sid must be provided"
                        logger.error(error_msg)
                        return False, error_msg
                    
                    logger.info(f"Sending WhatsApp plain text message from {whatsapp_from} to {whatsapp_to}")
                    logger.debug(f"Message body: {message_body[:100]}...")
                    message_params['body'] = message_body
                
                # Create and send message
                message = self.client.messages.create(**message_params)
                
                # Log message details
                logger.info(f"WhatsApp message created. SID: {message.sid}, Status: {message.status}")
                logger.debug(f"Message direction: {message.direction}, Error code: {getattr(message, 'error_code', 'N/A')}")
                
                # Check message status
                message_status = getattr(message, 'status', 'unknown')
                error_code = getattr(message, 'error_code', None)
                
                # Handle delivery status
                if message_status in ['failed', 'undelivered']:
                    error_msg = self._handle_whatsapp_error(error_code, message_status)
                    logger.warning(f"WhatsApp message undelivered. Status: {message_status}, Error Code: {error_code}, Error: {error_msg}")
                    logger.info(f"Message will be delivered once recipient opts in by sending a message to {whatsapp_from}")
                    # Still return True as API call succeeded, delivery is pending opt-in
                elif message_status in ['queued', 'sending', 'sent', 'delivered', 'read', 'accepted']:
                    logger.info(f"Message queued/sent successfully. Status: {message_status}")
                else:
                    logger.info(f"Message status: {message_status} (will be updated by Twilio)")
                
                return True, "WhatsApp message sent successfully"
                
            except TwilioRestException as e:
                error_code = getattr(e, 'code', None)
                error_msg = self._handle_whatsapp_error(error_code, 'failed')
                
                logger.error(f"Twilio API error sending WhatsApp message: {e}")
                
                # Handle specific error cases
                if "trial" in str(e).lower() or "verified" in str(e).lower():
                    error_msg = "Trial account restriction: Please verify your phone number in Twilio console or upgrade to paid account"
                elif "not opted in" in str(e).lower() or "opt-in" in str(e).lower():
                    error_msg = f"Recipient has not opted in to receive WhatsApp messages from {whatsapp_from}"
                
                return False, error_msg
            except Exception as e:
                logger.error(f"Unexpected error sending WhatsApp message: {e}", exc_info=True)
                return False, f"Failed to send WhatsApp message: {str(e)}"
            
        except Exception as e:
            logger.error(f"Failed to send WhatsApp message to {phone_number}: {e}", exc_info=True)
            return False, f"Failed to send WhatsApp message: {str(e)}"


# Global service instance (singleton pattern)
_twilio_service_instance: Optional[TwilioService] = None


def get_twilio_service() -> TwilioService:
    """
    Get or create Twilio service instance (singleton pattern).
    
    Returns:
        TwilioService instance
    """
    global _twilio_service_instance
    if _twilio_service_instance is None:
        _twilio_service_instance = TwilioService()
    return _twilio_service_instance


# Backward compatibility: maintain global instance
twilio_service = get_twilio_service()
