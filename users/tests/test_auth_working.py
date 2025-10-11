"""
Working Test Suite for User Authentication
Simplified tests that properly handle Django + FastAPI integration
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date
from fastapi.testclient import TestClient
from fastapi import HTTPException
from unittest.mock import patch
import hashlib

from users.models import UserProfile, PhoneOTP, EventInterest
from users.auth_router import router, create_jwt_token, verify_jwt_token
from loopin_backend import settings

client = TestClient(router)


def get_unique_phone(test_name):
    """Generate unique phone number for each test"""
    # Convert hash to numeric only
    hash_val = int(hashlib.md5(test_name.encode()).hexdigest()[:8], 16)
    # Ensure it's 10 digits (valid phone number)
    phone_num = str(hash_val % 9000000000 + 1000000000)  # Range: 1000000000-9999999999
    return f"+{phone_num}"


class PhoneOTPModelWorkingTests(TestCase):
    """Working tests for PhoneOTP model"""
    
    def test_otp_generation(self):
        """Test OTP generation"""
        phone = get_unique_phone("test_otp_gen")
        otp = PhoneOTP.objects.create(phone_number=phone, otp_code="1234")
        otp.generate_otp()
        self.assertEqual(len(otp.otp_code), 4)
        self.assertTrue(otp.otp_code.isdigit())
        self.assertEqual(otp.attempts, 0)
        self.assertFalse(otp.is_verified)
    
    def test_otp_verification_success(self):
        """Test successful OTP verification"""
        phone = get_unique_phone("test_otp_verify")
        otp = PhoneOTP.objects.create(phone_number=phone, otp_code="1234")
        is_valid, message = otp.verify_otp("1234")
        self.assertTrue(is_valid)
        self.assertTrue(otp.is_verified)
    
    def test_otp_verification_invalid(self):
        """Test invalid OTP verification"""
        phone = get_unique_phone("test_otp_invalid")
        otp = PhoneOTP.objects.create(phone_number=phone, otp_code="1234")
        is_valid, message = otp.verify_otp("9999")
        self.assertFalse(is_valid)
        self.assertEqual(otp.attempts, 1)
    
    def test_otp_expiration(self):
        """Test OTP expiration"""
        phone = get_unique_phone("test_otp_expire")
        otp = PhoneOTP.objects.create(
            phone_number=phone,
            otp_code="1234",
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        is_valid, message = otp.verify_otp("1234")
        self.assertFalse(is_valid)
        self.assertIn("expired", message.lower())


class EventInterestModelWorkingTests(TestCase):
    """Working tests for EventInterest model"""
    
    def test_create_interest(self):
        """Test creating event interest"""
        name = f"TestInterest-{get_unique_phone('create_int')}"
        interest = EventInterest.objects.create(name=name, is_active=True)
        self.assertEqual(str(interest), name)
        self.assertTrue(interest.is_active)


class UserProfileModelWorkingTests(TestCase):
    """Working tests for UserProfile model"""
    
    def test_create_profile(self):
        """Test creating user profile"""
        phone = get_unique_phone("test_profile")
        user = User.objects.create_user(username=phone, password="test")
        profile = UserProfile.objects.create(
            user=user,
            name="Test User",
            phone_number=phone
        )
        self.assertEqual(str(profile), f"Test User ({phone})")
    
    def test_profile_defaults(self):
        """Test profile default values"""
        phone = get_unique_phone("test_defaults")
        user = User.objects.create_user(username=phone, password="test")
        profile = UserProfile.objects.create(user=user, phone_number=phone)
        self.assertFalse(profile.is_verified)
        self.assertTrue(profile.is_active)
        self.assertEqual(profile.profile_pictures, [])


class SignupAPIWorkingTests(TestCase):
    """Working tests for signup API"""
    
    @patch('users.auth_router.twilio_service.send_otp_sms')
    def test_signup_new_user(self, mock_send):
        """Test signup for new user"""
        mock_send.return_value = (True, "OTP sent")
        phone = get_unique_phone("test_signup_new")
        
        response = client.post("/auth/signup", json={"phone_number": phone})
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertIn("OTP sent", data["message"])
    
    def test_signup_invalid_phone(self):
        """Test signup with invalid phone"""
        response = client.post("/auth/signup", json={"phone_number": "123"})
        self.assertEqual(response.status_code, 422)


class OTPVerificationWorkingTests(TestCase):
    """Working tests for OTP verification"""
    
    def test_verify_otp_creates_user(self):
        """Test OTP verification creates user"""
        phone = get_unique_phone("test_verify_creates")
        otp = PhoneOTP.objects.create(phone_number=phone, otp_code="1234")
        
        response = client.post("/auth/verify-otp", json={
            "phone_number": phone,
            "otp_code": "1234"
        })
        data = response.json()
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(data["success"])
        self.assertIsNotNone(data["token"])
        self.assertTrue(User.objects.filter(username=phone).exists())
    
    def test_verify_otp_invalid(self):
        """Test OTP verification with invalid code"""
        phone = get_unique_phone("test_verify_invalid")
        PhoneOTP.objects.create(phone_number=phone, otp_code="1234")
        
        response = client.post("/auth/verify-otp", json={
            "phone_number": phone,
            "otp_code": "9999"
        })
        data = response.json()
        
        self.assertFalse(data["success"])


class CompleteProfileWorkingTests(TestCase):
    """Working tests for profile completion"""
    
    def test_complete_profile_success(self):
        """Test successful profile completion"""
        phone = get_unique_phone("test_complete")
        user = User.objects.create_user(username=phone, password="test")
        UserProfile.objects.create(user=user, phone_number=phone, is_verified=True)
        token = create_jwt_token(user.id, phone)
        
        interest = EventInterest.objects.create(
            name=f"Music-{phone}",
            is_active=True
        )
        birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
        
        response = client.post(
            "/auth/complete-profile",
            json={
                "phone_number": phone,
                "name": "John Doe",
                "birth_date": birth_date,
                "gender": "male",
                "event_interests": [interest.id],
                "profile_pictures": ["http://example.com/pic.jpg"]
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])


class LoginWorkingTests(TestCase):
    """Working tests for login"""
    
    @patch('users.auth_router.twilio_service.send_otp_sms')
    def test_login_existing_user(self, mock_send):
        """Test login for existing user"""
        mock_send.return_value = (True, "OTP sent")
        phone = get_unique_phone("test_login_exist")
        user = User.objects.create_user(username=phone, password="test")
        UserProfile.objects.create(user=user, phone_number=phone, name="Test")
        
        response = client.post("/auth/login", json={"phone_number": phone})
        data = response.json()
        
        self.assertTrue(data["success"])
    
    def test_login_non_existing_user(self):
        """Test login for non-existing user"""
        phone = get_unique_phone("test_login_noexist")
        response = client.post("/auth/login", json={"phone_number": phone})
        data = response.json()
        
        self.assertFalse(data["success"])
        self.assertIn("not found", data["message"].lower())


class JWTWorkingTests(TestCase):
    """Working tests for JWT tokens"""
    
    def test_create_and_verify_token(self):
        """Test JWT token creation and verification"""
        token = create_jwt_token(1, "+1234567890")
        payload = verify_jwt_token(token)
        self.assertEqual(payload['user_id'], 1)
    
    def test_invalid_token(self):
        """Test invalid token raises exception"""
        with self.assertRaises(HTTPException):
            verify_jwt_token("invalid")


class GetEventInterestsWorkingTests(TestCase):
    """Working tests for event interests endpoint"""
    
    def test_get_interests(self):
        """Test getting event interests"""
        hash1 = get_unique_phone("int1")
        hash2 = get_unique_phone("int2")
        EventInterest.objects.create(name=f"Music-{hash1}", is_active=True)
        EventInterest.objects.create(name=f"Sports-{hash2}", is_active=True)
        
        response = client.get("/auth/event-interests")
        data = response.json()
        
        self.assertTrue(data["success"])
        self.assertGreaterEqual(len(data["data"]), 2)
    
    def test_get_interests_filters_inactive(self):
        """Test that inactive interests are filtered out"""
        hash1 = get_unique_phone("filt1")
        EventInterest.objects.create(name=f"Active-{hash1}", is_active=True)
        EventInterest.objects.create(name=f"Inactive-{hash1}", is_active=False)
        
        response = client.get("/auth/event-interests")
        data = response.json()
        
        # Check inactive is not in results
        names = [interest["name"] for interest in data["data"]]
        self.assertNotIn(f"Inactive-{hash1}", names)


class LogoutWorkingTests(TestCase):
    """Working tests for logout"""
    
    def test_logout(self):
        """Test logout"""
        response = client.post("/auth/logout")
        data = response.json()
        self.assertTrue(data["success"])

