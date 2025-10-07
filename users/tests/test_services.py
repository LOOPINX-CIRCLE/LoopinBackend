"""
Comprehensive Test Suite for Twilio Services
Tests all service functionality and edge cases
"""

from django.test import TestCase
from unittest.mock import patch, MagicMock
from users.services import TwilioService, twilio_service


class TwilioServiceTests(TestCase):
    """Test Twilio service functionality"""
    
    def setUp(self):
        self.service = TwilioService()
        self.phone = "+1234567890"
        self.otp = "1234"
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'TWILIO_PHONE_NUMBER': '+15005550006'
    })
    @patch('users.services.Client')
    def test_send_otp_sms_success(self, mock_client):
        """Test successful OTP SMS sending"""
        # Mock Twilio client
        mock_message = MagicMock()
        mock_message.sid = 'test_sid_123'
        mock_client.return_value.messages.create.return_value = mock_message
        
        service = TwilioService()
        success, message = service.send_otp_sms(self.phone, self.otp)
        
        self.assertTrue(success)
        self.assertEqual(message, "OTP sent successfully")
    
    @patch.dict('os.environ', {'TWILIO_TEST_MODE': 'true'})
    def test_send_otp_test_mode(self):
        """Test OTP sending in test mode"""
        service = TwilioService()
        success, message = service.send_otp_sms(self.phone, self.otp)
        
        self.assertTrue(success)
        self.assertIn("TEST MODE", message)
        self.assertIn(self.otp, message)
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'TWILIO_PHONE_NUMBER': '+15005550006'
    })
    @patch('users.services.Client')
    def test_send_otp_sms_failure(self, mock_client):
        """Test OTP SMS sending failure"""
        mock_client.return_value.messages.create.side_effect = Exception("Twilio error")
        
        service = TwilioService()
        success, message = service.send_otp_sms(self.phone, self.otp)
        
        self.assertFalse(success)
        self.assertIn("Failed to send OTP", message)
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'TWILIO_PHONE_NUMBER': '+15005550006'
    })
    @patch('users.services.Client')
    def test_send_otp_trial_account_restriction(self, mock_client):
        """Test OTP sending with trial account restriction"""
        mock_client.return_value.messages.create.side_effect = Exception(
            "Trial account restriction: Please verify your phone number"
        )
        
        service = TwilioService()
        success, message = service.send_otp_sms(self.phone, self.otp)
        
        self.assertFalse(success)
        self.assertIn("trial account restriction", message.lower())
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token'
    })
    @patch('users.services.Client')
    def test_send_otp_phone_number_normalization(self, mock_client):
        """Test phone number is normalized to include +"""
        mock_message = MagicMock()
        mock_message.sid = 'test_sid'
        mock_client.return_value.messages.create.return_value = mock_message
        
        service = TwilioService()
        # Phone without +
        service.send_otp_sms("1234567890", self.otp)
        
        # Verify it was called with +
        args = mock_client.return_value.messages.create.call_args
        self.assertTrue(args[1]['to'].startswith('+'))
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': '',
        'TWILIO_AUTH_TOKEN': ''
    })
    def test_send_otp_without_credentials(self):
        """Test OTP sending without Twilio credentials"""
        service = TwilioService()
        success, message = service.send_otp_sms(self.phone, self.otp)
        
        self.assertFalse(success)
        self.assertIn("unavailable", message.lower())
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'TWILIO_VERIFY_SID': 'verify_sid'
    })
    @patch('users.services.Client')
    def test_verify_otp_using_verify_service(self, mock_client):
        """Test OTP verification using Twilio Verify service"""
        mock_check = MagicMock()
        mock_check.status = 'approved'
        mock_client.return_value.verify.v2.services.return_value.verification_checks.create.return_value = mock_check
        
        service = TwilioService()
        success, message = service.verify_otp(self.phone, self.otp)
        
        self.assertTrue(success)
        self.assertEqual(message, "OTP verified successfully")
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'TWILIO_VERIFY_SID': 'verify_sid'
    })
    @patch('users.services.Client')
    def test_verify_otp_failed(self, mock_client):
        """Test failed OTP verification"""
        mock_check = MagicMock()
        mock_check.status = 'pending'
        mock_client.return_value.verify.v2.services.return_value.verification_checks.create.return_value = mock_check
        
        service = TwilioService()
        success, message = service.verify_otp(self.phone, self.otp)
        
        self.assertFalse(success)
        self.assertEqual(message, "Invalid OTP")
    
    def test_global_twilio_service_instance(self):
        """Test global twilio_service instance exists"""
        self.assertIsInstance(twilio_service, TwilioService)


class TwilioServiceEdgeCasesTests(TestCase):
    """Test edge cases for Twilio service"""
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'TWILIO_PHONE_NUMBER': '+15005550006'
    })
    @patch('users.services.Client')
    def test_send_otp_with_special_characters(self, mock_client):
        """Test OTP sending with special characters in phone"""
        mock_message = MagicMock()
        mock_message.sid = 'test_sid'
        mock_client.return_value.messages.create.return_value = mock_message
        
        service = TwilioService()
        phones = [
            "+1 (234) 567-8900",
            "+1-234-567-8900",
            "+1.234.567.8900"
        ]
        
        for phone in phones:
            success, _ = service.send_otp_sms(phone, "1234")
            # Should succeed after normalization
            self.assertTrue(success)
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'TWILIO_PHONE_NUMBER': '+15005550006'
    })
    @patch('users.services.Client')
    def test_send_otp_message_format(self, mock_client):
        """Test OTP SMS message format"""
        mock_message = MagicMock()
        mock_message.sid = 'test_sid'
        mock_client.return_value.messages.create.return_value = mock_message
        
        service = TwilioService()
        service.send_otp_sms("+1234567890", "1234")
        
        # Verify message content
        call_args = mock_client.return_value.messages.create.call_args
        message_body = call_args[1]['body']
        
        self.assertIn("1234", message_body)  # OTP code
        self.assertIn("Loopin", message_body)  # Brand name
        self.assertIn("10 minutes", message_body)  # Expiration time
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token'
    })
    @patch('users.services.Client')
    def test_send_otp_network_timeout(self, mock_client):
        """Test OTP sending with network timeout"""
        import socket
        mock_client.return_value.messages.create.side_effect = socket.timeout("Network timeout")
        
        service = TwilioService()
        success, message = service.send_otp_sms("+1234567890", "1234")
        
        self.assertFalse(success)
        self.assertIn("Failed to send OTP", message)
    
    @patch.dict('os.environ', {'TWILIO_TEST_MODE': 'TRUE'})  # Case insensitive
    def test_test_mode_case_insensitive(self):
        """Test that test mode works with different cases"""
        service = TwilioService()
        success, message = service.send_otp_sms("+1234567890", "1234")
        
        self.assertTrue(success)
        self.assertIn("TEST MODE", message)
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'TWILIO_PHONE_NUMBER': '+15005550006'
    })
    @patch('users.services.Client')
    def test_send_otp_empty_phone_number(self, mock_client):
        """Test OTP sending with empty phone number"""
        service = TwilioService()
        success, message = service.send_otp_sms("", "1234")
        
        # Should handle gracefully
        self.assertFalse(success)
    
    @patch.dict('os.environ', {
        'TWILIO_ACCOUNT_SID': 'test_sid',
        'TWILIO_AUTH_TOKEN': 'test_token',
        'TWILIO_PHONE_NUMBER': '+15005550006'
    })
    @patch('users.services.Client')
    def test_send_otp_rate_limit_error(self, mock_client):
        """Test OTP sending with rate limit error"""
        from twilio.base.exceptions import TwilioRestException
        
        mock_client.return_value.messages.create.side_effect = TwilioRestException(
            status=429,
            uri="/Messages",
            msg="Rate limit exceeded"
        )
        
        service = TwilioService()
        success, message = service.send_otp_sms("+1234567890", "1234")
        
        self.assertFalse(success)

