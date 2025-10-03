"""
Services for user authentication and OTP verification
"""

import os
from twilio.rest import Client
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class TwilioService:
    """Service for sending SMS via Twilio"""
    
    def __init__(self):
        self.account_sid = os.getenv('TWILIO_ACCOUNT_SID')
        self.auth_token = os.getenv('TWILIO_AUTH_TOKEN')
        self.verify_sid = os.getenv('TWILIO_VERIFY_SID')
        self.verify_secret = os.getenv('TWILIO_VERIFY_SECRET')
        
        try:
            self.client = Client(self.account_sid, self.auth_token)
        except Exception as e:
            logger.error(f"Failed to initialize Twilio client: {e}")
            self.client = None
    
    def send_otp_sms(self, phone_number, otp_code):
        """Send OTP via SMS"""
        try:
            # Check if we're in test mode
            test_mode = os.getenv('TWILIO_TEST_MODE', 'false').lower() == 'true'
            
            if test_mode:
                logger.info(f"TEST MODE: OTP {otp_code} would be sent to {phone_number}")
                return True, f"TEST MODE: OTP {otp_code} sent to {phone_number}"
            
            if not self.client:
                logger.error("Twilio client not initialized")
                return False, "SMS service unavailable"
            
            # Format phone number (ensure it starts with +)
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number.lstrip('+')
            
            # Use direct SMS method for better control over OTP codes
            try:
                # For trial accounts, you can use verified numbers or the trial number
                from_number = os.getenv('TWILIO_PHONE_NUMBER', '+15005550006')
                
                message = self.client.messages.create(
                    body=f"Your Loopin verification code is: {otp_code}. This code expires in 10 minutes.",
                    from_=from_number,
                    to=phone_number
                )
                
                logger.info(f"OTP sent successfully to {phone_number}. SID: {message.sid}")
                return True, "OTP sent successfully"
                
            except Exception as sms_error:
                logger.error(f"Failed to send SMS: {sms_error}")
                
                # If it's a trial account restriction, provide helpful error message
                if "trial" in str(sms_error).lower() or "verified" in str(sms_error).lower():
                    return False, "Trial account restriction: Please verify your phone number in Twilio console or upgrade to paid account"
                
                return False, f"Failed to send OTP: {str(sms_error)}"
            
        except Exception as e:
            logger.error(f"Failed to send OTP to {phone_number}: {e}")
            return False, f"Failed to send OTP: {str(e)}"
    
    def verify_otp(self, phone_number, otp_code):
        """Verify OTP using Twilio Verify service (alternative method)"""
        try:
            if not self.client:
                logger.error("Twilio client not initialized")
                return False, "Verification service unavailable"
            
            # Format phone number
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number.lstrip('+')
            
            verification_check = self.client.verify.v2.services(
                self.verify_sid
            ).verification_checks.create(
                to=phone_number,
                code=otp_code
            )
            
            if verification_check.status == 'approved':
                return True, "OTP verified successfully"
            else:
                return False, "Invalid OTP"
                
        except Exception as e:
            logger.error(f"Failed to verify OTP for {phone_number}: {e}")
            return False, f"Verification failed: {str(e)}"


# Global instance
twilio_service = TwilioService()
