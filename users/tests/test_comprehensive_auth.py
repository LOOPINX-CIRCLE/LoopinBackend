"""
Comprehensive Test Suite for User Authentication System
Tests every single possibility and edge case
"""

from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta, date, datetime
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import jwt

from users.models import UserProfile, PhoneOTP, EventInterest
from users.auth_router import router, create_jwt_token, verify_jwt_token
from loopin_backend import settings

client = TestClient(router)


class PhoneOTPModelTests(TestCase):
    """Test PhoneOTP model functionality"""
    
    def setUp(self):
        self.phone = "+1234567890"
    
    def test_create_otp_with_auto_expiration(self):
        """Test OTP creation with automatic expiration"""
        otp = PhoneOTP.objects.create(phone_number=self.phone, otp_code="1234")
        self.assertIsNotNone(otp.expires_at)
        self.assertFalse(otp.is_expired())
    
    def test_generate_otp_creates_4_digit_code(self):
        """Test OTP generation creates 4-digit code"""
        otp = PhoneOTP.objects.create(phone_number=self.phone, otp_code="1234")
        otp.generate_otp()
        self.assertEqual(len(otp.otp_code), 4)
        self.assertTrue(otp.otp_code.isdigit())
    
    def test_generate_otp_resets_attempts(self):
        """Test OTP generation resets attempt counter"""
        otp = PhoneOTP.objects.create(phone_number=self.phone, otp_code="1234", attempts=3)
        otp.generate_otp()
        self.assertEqual(otp.attempts, 0)
    
    def test_generate_otp_sets_verification_false(self):
        """Test OTP generation sets is_verified to False"""
        otp = PhoneOTP.objects.create(phone_number=self.phone, otp_code="1234", is_verified=True)
        otp.generate_otp()
        self.assertFalse(otp.is_verified)
    
    def test_verify_otp_success(self):
        """Test successful OTP verification"""
        otp = PhoneOTP.objects.create(phone_number=self.phone, otp_code="1234")
        is_valid, message = otp.verify_otp("1234")
        self.assertTrue(is_valid)
        self.assertEqual(message, "OTP verified successfully")
        self.assertTrue(otp.is_verified)
    
    def test_verify_otp_invalid_code(self):
        """Test OTP verification with invalid code"""
        otp = PhoneOTP.objects.create(phone_number=self.phone, otp_code="1234")
        is_valid, message = otp.verify_otp("5678")
        self.assertFalse(is_valid)
        self.assertIn("Invalid OTP", message)
        self.assertEqual(otp.attempts, 1)
    
    def test_verify_otp_expired(self):
        """Test OTP verification with expired code"""
        otp = PhoneOTP.objects.create(
            phone_number=self.phone,
            otp_code="1234",
            expires_at=timezone.now() - timedelta(minutes=1)
        )
        is_valid, message = otp.verify_otp("1234")
        self.assertFalse(is_valid)
        self.assertEqual(message, "OTP has expired")
    
    def test_verify_otp_max_attempts_reached(self):
        """Test OTP verification when max attempts reached"""
        otp = PhoneOTP.objects.create(phone_number=self.phone, otp_code="1234", attempts=3)
        is_valid, message = otp.verify_otp("1234")
        self.assertFalse(is_valid)
        self.assertEqual(message, "Too many attempts. Please request a new OTP")
    
    def test_verify_otp_attempts_increment(self):
        """Test OTP attempts increment on wrong code"""
        otp = PhoneOTP.objects.create(phone_number=self.phone, otp_code="1234")
        otp.verify_otp("0000")
        self.assertEqual(otp.attempts, 1)
        otp.verify_otp("0000")
        self.assertEqual(otp.attempts, 2)
        otp.verify_otp("0000")
        self.assertEqual(otp.attempts, 3)
    
    def test_verify_otp_remaining_attempts_message(self):
        """Test remaining attempts message"""
        otp = PhoneOTP.objects.create(phone_number=self.phone, otp_code="1234")
        _, msg1 = otp.verify_otp("0000")
        self.assertIn("2 attempts remaining", msg1)
        _, msg2 = otp.verify_otp("0000")
        self.assertIn("1 attempts remaining", msg2)
    
    def test_otp_unique_phone_number(self):
        """Test phone number uniqueness constraint"""
        PhoneOTP.objects.create(phone_number=self.phone, otp_code="1234")
        with self.assertRaises(Exception):
            PhoneOTP.objects.create(phone_number=self.phone, otp_code="5678")


class EventInterestModelTests(TestCase):
    """Test EventInterest model"""
    
    def test_create_event_interest(self):
        """Test creating event interest"""
        interest = EventInterest.objects.create(
            name="Music",
            description="Music events",
            is_active=True
        )
        self.assertEqual(str(interest), "Music")
        self.assertTrue(interest.is_active)
    
    def test_event_interest_unique_name(self):
        """Test event interest name uniqueness"""
        EventInterest.objects.create(name="Music")
        with self.assertRaises(Exception):
            EventInterest.objects.create(name="Music")
    
    def test_event_interest_ordering(self):
        """Test event interests are ordered by name"""
        EventInterest.objects.create(name="Zebra")
        EventInterest.objects.create(name="Apple")
        interests = list(EventInterest.objects.all())
        self.assertEqual(interests[0].name, "Apple")


class UserProfileModelTests(TestCase):
    """Test UserProfile model"""
    
    def setUp(self):
        self.user = User.objects.create_user(username="+1234567890", password="test123")
    
    def test_create_user_profile(self):
        """Test creating user profile"""
        profile = UserProfile.objects.create(
            user=self.user,
            name="Test User",
            phone_number="+1234567890"
        )
        self.assertEqual(str(profile), "Test User (+1234567890)")
    
    def test_user_profile_defaults(self):
        """Test user profile default values"""
        profile = UserProfile.objects.create(user=self.user)
        self.assertFalse(profile.is_verified)
        self.assertTrue(profile.is_active)
        self.assertEqual(profile.profile_pictures, [])
    
    def test_user_profile_with_interests(self):
        """Test user profile with event interests"""
        interest1 = EventInterest.objects.create(name="Music")
        interest2 = EventInterest.objects.create(name="Sports")
        profile = UserProfile.objects.create(user=self.user)
        profile.event_interests.add(interest1, interest2)
        self.assertEqual(profile.event_interests.count(), 2)
    
    def test_user_profile_gender_choices(self):
        """Test user profile gender choices"""
        profile = UserProfile.objects.create(
            user=self.user,
            gender='male'
        )
        self.assertEqual(profile.gender, 'male')


class SignupAPITests(TestCase):
    """Test signup endpoint - /auth/signup"""
    
    @patch('users.auth_router.twilio_service.send_otp_sms')
    def test_signup_new_user_success(self, mock_send):
        """Test successful signup for new user"""
        mock_send.return_value = (True, "OTP sent")
        
        response = client.post("/auth/signup", json={
            "phone_number": "+1234567890"
        })
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("OTP sent successfully", data["message"])
        self.assertEqual(data["data"]["phone_number"], "+1234567890")
    
    @patch('users.auth_router.twilio_service.send_otp_sms')
    def test_signup_existing_complete_user(self, mock_send):
        """Test signup for existing user with complete profile"""
        # Create existing user with complete profile
        user = User.objects.create_user(username="+1234567890", password="test")
        UserProfile.objects.create(
            user=user,
            phone_number="+1234567890",
            name="Test User",
            profile_pictures=["http://example.com/pic.jpg"]
        )
        
        response = client.post("/auth/signup", json={
            "phone_number": "+1234567890"
        })
        
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("already exists", data["message"].lower())
    
    @patch('users.auth_router.twilio_service.send_otp_sms')
    def test_signup_existing_incomplete_user(self, mock_send):
        """Test signup for existing user with incomplete profile"""
        mock_send.return_value = (True, "OTP sent")
        user = User.objects.create_user(username="+1234567890", password="test")
        UserProfile.objects.create(user=user, phone_number="+1234567890")
        
        response = client.post("/auth/signup", json={
            "phone_number": "+1234567890"
        })
        
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("complete your registration", data["message"])
    
    def test_signup_invalid_phone_format(self):
        """Test signup with invalid phone format"""
        response = client.post("/auth/signup", json={
            "phone_number": "123"  # Too short
        })
        self.assertEqual(response.status_code, 422)
    
    def test_signup_phone_with_spaces(self):
        """Test signup with phone containing spaces"""
        with patch('users.auth_router.twilio_service.send_otp_sms') as mock:
            mock.return_value = (True, "OTP sent")
            response = client.post("/auth/signup", json={
                "phone_number": "+1 (234) 567-8900"
            })
            data = response.json()
            # Should normalize to +12345678900
            self.assertTrue(data["success"])
    
    @patch('users.auth_router.twilio_service.send_otp_sms')
    def test_signup_twilio_failure(self, mock_send):
        """Test signup when Twilio SMS fails"""
        mock_send.return_value = (False, "Twilio error")
        
        response = client.post("/auth/signup", json={
            "phone_number": "+1234567890"
        })
        
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Failed to send OTP", data["message"])
    
    @patch('users.auth_router.twilio_service.send_otp_sms')
    def test_signup_creates_otp_record(self, mock_send):
        """Test signup creates OTP record in database"""
        mock_send.return_value = (True, "OTP sent")
        
        client.post("/auth/signup", json={
            "phone_number": "+1234567890"
        })
        
        otp = PhoneOTP.objects.get(phone_number="+1234567890")
        self.assertIsNotNone(otp)
        self.assertEqual(len(otp.otp_code), 4)


class OTPVerificationAPITests(TestCase):
    """Test OTP verification endpoint - /auth/verify-otp"""
    
    def setUp(self):
        self.phone = "+1234567890"
        self.otp = PhoneOTP.objects.create(phone_number=self.phone, otp_code="1234")
    
    def test_verify_otp_success_new_user(self):
        """Test successful OTP verification for new user"""
        response = client.post("/auth/verify-otp", json={
            "phone_number": self.phone,
            "otp_code": "1234"
        })
        
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIsNotNone(data["token"])
        self.assertTrue(data["data"]["needs_profile_completion"])
    
    def test_verify_otp_creates_user_and_profile(self):
        """Test OTP verification creates user and profile"""
        client.post("/auth/verify-otp", json={
            "phone_number": self.phone,
            "otp_code": "1234"
        })
        
        user = User.objects.get(username=self.phone)
        self.assertIsNotNone(user)
        self.assertTrue(hasattr(user, 'profile'))
        self.assertTrue(user.profile.is_verified)
    
    def test_verify_otp_invalid_code(self):
        """Test OTP verification with invalid code"""
        response = client.post("/auth/verify-otp", json={
            "phone_number": self.phone,
            "otp_code": "0000"
        })
        
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Invalid OTP", data["message"])
    
    def test_verify_otp_expired(self):
        """Test OTP verification with expired OTP"""
        self.otp.expires_at = timezone.now() - timedelta(minutes=1)
        self.otp.save()
        
        response = client.post("/auth/verify-otp", json={
            "phone_number": self.phone,
            "otp_code": "1234"
        })
        
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("expired", data["message"].lower())
    
    def test_verify_otp_max_attempts(self):
        """Test OTP verification after max attempts"""
        self.otp.attempts = 3
        self.otp.save()
        
        response = client.post("/auth/verify-otp", json={
            "phone_number": self.phone,
            "otp_code": "1234"
        })
        
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Too many attempts", data["message"])
    
    def test_verify_otp_no_otp_record(self):
        """Test OTP verification when no OTP record exists"""
        response = client.post("/auth/verify-otp", json={
            "phone_number": "+9999999999",
            "otp_code": "1234"
        })
        
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("No OTP found", data["message"])
    
    def test_verify_otp_invalid_format(self):
        """Test OTP verification with invalid OTP format"""
        response = client.post("/auth/verify-otp", json={
            "phone_number": self.phone,
            "otp_code": "12"  # Too short
        })
        self.assertEqual(response.status_code, 422)
    
    def test_verify_otp_non_digit_code(self):
        """Test OTP verification with non-digit code"""
        response = client.post("/auth/verify-otp", json={
            "phone_number": self.phone,
            "otp_code": "abcd"
        })
        self.assertEqual(response.status_code, 422)
    
    def test_verify_otp_existing_user_with_profile(self):
        """Test OTP verification for existing user with profile"""
        user = User.objects.create_user(username=self.phone, password="test")
        UserProfile.objects.create(user=user, phone_number=self.phone)
        
        response = client.post("/auth/verify-otp", json={
            "phone_number": self.phone,
            "otp_code": "1234"
        })
        
        data = response.json()
        self.assertTrue(data["success"])
        # Profile should be updated to verified
        user.profile.refresh_from_db()
        self.assertTrue(user.profile.is_verified)


class CompleteProfileAPITests(TestCase):
    """Test complete profile endpoint - /auth/complete-profile"""
    
    def setUp(self):
        self.phone = "+1234567890"
        self.user = User.objects.create_user(username=self.phone, password="test")
        self.profile = UserProfile.objects.create(
            user=self.user,
            phone_number=self.phone,
            is_verified=True
        )
        self.token = create_jwt_token(self.user.id, self.phone)
        self.interest1 = EventInterest.objects.create(name="Music", is_active=True)
        self.interest2 = EventInterest.objects.create(name="Sports", is_active=True)
        
        # Birth date for 20-year-old
        birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
        
        self.valid_profile_data = {
            "phone_number": self.phone,
            "name": "John Doe",
            "birth_date": birth_date,
            "gender": "male",
            "event_interests": [self.interest1.id, self.interest2.id],
            "profile_pictures": ["http://example.com/pic1.jpg"],
            "bio": "Test bio",
            "location": "New York"
        }
    
    def test_complete_profile_success(self):
        """Test successful profile completion"""
        response = client.post(
            "/auth/complete-profile",
            json=self.valid_profile_data,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(data["data"]["name"], "John Doe")
        
        # Verify database
        self.profile.refresh_from_db()
        self.assertEqual(self.profile.name, "John Doe")
        self.assertEqual(self.profile.gender, "male")
    
    def test_complete_profile_invalid_token(self):
        """Test profile completion with invalid token"""
        response = client.post(
            "/auth/complete-profile",
            json=self.valid_profile_data,
            headers={"Authorization": "Bearer invalid_token"}
        )
        self.assertEqual(response.status_code, 401)
    
    def test_complete_profile_expired_token(self):
        """Test profile completion with expired token"""
        # Create expired token
        payload = {
            'user_id': self.user.id,
            'phone_number': self.phone,
            'exp': datetime.utcnow() - timedelta(days=1),
            'iat': datetime.utcnow()
        }
        expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        
        response = client.post(
            "/auth/complete-profile",
            json=self.valid_profile_data,
            headers={"Authorization": f"Bearer {expired_token}"}
        )
        self.assertEqual(response.status_code, 401)
    
    def test_complete_profile_name_too_short(self):
        """Test profile completion with name too short"""
        data = self.valid_profile_data.copy()
        data["name"] = "Ab"  # Only 2 characters
        
        response = client.post(
            "/auth/complete-profile",
            json=data,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 422)
    
    def test_complete_profile_name_with_numbers(self):
        """Test profile completion with numbers in name"""
        data = self.valid_profile_data.copy()
        data["name"] = "John123"
        
        response = client.post(
            "/auth/complete-profile",
            json=data,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 422)
    
    def test_complete_profile_age_under_18(self):
        """Test profile completion with age under 18"""
        data = self.valid_profile_data.copy()
        # 17 years old
        data["birth_date"] = (date.today() - timedelta(days=365*17)).strftime('%Y-%m-%d')
        
        response = client.post(
            "/auth/complete-profile",
            json=data,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 422)
    
    def test_complete_profile_invalid_date_format(self):
        """Test profile completion with invalid date format"""
        data = self.valid_profile_data.copy()
        data["birth_date"] = "2000/01/01"  # Wrong format
        
        response = client.post(
            "/auth/complete-profile",
            json=data,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 422)
    
    def test_complete_profile_invalid_gender(self):
        """Test profile completion with invalid gender"""
        data = self.valid_profile_data.copy()
        data["gender"] = "unknown"
        
        response = client.post(
            "/auth/complete-profile",
            json=data,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 422)
    
    def test_complete_profile_no_interests(self):
        """Test profile completion without event interests"""
        data = self.valid_profile_data.copy()
        data["event_interests"] = []
        
        response = client.post(
            "/auth/complete-profile",
            json=data,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 422)
    
    def test_complete_profile_too_many_interests(self):
        """Test profile completion with too many interests"""
        interests = [EventInterest.objects.create(name=f"Interest{i}", is_active=True).id for i in range(6)]
        data = self.valid_profile_data.copy()
        data["event_interests"] = interests
        
        response = client.post(
            "/auth/complete-profile",
            json=data,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 422)
    
    def test_complete_profile_inactive_interest(self):
        """Test profile completion with inactive event interest"""
        inactive_interest = EventInterest.objects.create(name="Inactive", is_active=False)
        data = self.valid_profile_data.copy()
        data["event_interests"] = [inactive_interest.id]
        
        response = client.post(
            "/auth/complete-profile",
            json=data,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        
        data_response = response.json()
        self.assertFalse(data_response["success"])
        self.assertIn("invalid or inactive", data_response["message"].lower())
    
    def test_complete_profile_no_pictures(self):
        """Test profile completion without pictures"""
        data = self.valid_profile_data.copy()
        data["profile_pictures"] = []
        
        response = client.post(
            "/auth/complete-profile",
            json=data,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 422)
    
    def test_complete_profile_too_many_pictures(self):
        """Test profile completion with too many pictures"""
        data = self.valid_profile_data.copy()
        data["profile_pictures"] = [f"http://example.com/pic{i}.jpg" for i in range(7)]
        
        response = client.post(
            "/auth/complete-profile",
            json=data,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 422)
    
    def test_complete_profile_invalid_picture_url(self):
        """Test profile completion with invalid picture URL"""
        data = self.valid_profile_data.copy()
        data["profile_pictures"] = ["not-a-url"]
        
        response = client.post(
            "/auth/complete-profile",
            json=data,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 422)
    
    def test_complete_profile_bio_too_long(self):
        """Test profile completion with bio exceeding max length"""
        data = self.valid_profile_data.copy()
        data["bio"] = "a" * 501  # Exceeds 500 char limit
        
        response = client.post(
            "/auth/complete-profile",
            json=data,
            headers={"Authorization": f"Bearer {self.token}"}
        )
        self.assertEqual(response.status_code, 422)


class LoginAPITests(TestCase):
    """Test login endpoint - /auth/login"""
    
    def setUp(self):
        self.phone = "+1234567890"
        self.user = User.objects.create_user(username=self.phone, password="test")
        self.profile = UserProfile.objects.create(
            user=self.user,
            phone_number=self.phone,
            name="Test User"
        )
    
    @patch('users.auth_router.twilio_service.send_otp_sms')
    def test_login_existing_user_success(self, mock_send):
        """Test successful login for existing user"""
        mock_send.return_value = (True, "OTP sent")
        
        response = client.post("/auth/login", json={
            "phone_number": self.phone
        })
        
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("OTP sent successfully", data["message"])
    
    def test_login_non_existing_user(self):
        """Test login for non-existing user"""
        response = client.post("/auth/login", json={
            "phone_number": "+9999999999"
        })
        
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("not found", data["message"].lower())
    
    @patch('users.auth_router.twilio_service.send_otp_sms')
    def test_login_twilio_failure(self, mock_send):
        """Test login when Twilio fails"""
        mock_send.return_value = (False, "SMS failed")
        
        response = client.post("/auth/login", json={
            "phone_number": self.phone
        })
        
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Failed to send OTP", data["message"])
    
    def test_login_invalid_phone_format(self):
        """Test login with invalid phone format"""
        response = client.post("/auth/login", json={
            "phone_number": "invalid"
        })
        self.assertEqual(response.status_code, 422)


class VerifyLoginAPITests(TestCase):
    """Test verify login endpoint - /auth/verify-login"""
    
    def setUp(self):
        self.phone = "+1234567890"
        self.user = User.objects.create_user(username=self.phone, password="test")
        self.profile = UserProfile.objects.create(
            user=self.user,
            phone_number=self.phone,
            name="Test User",
            is_verified=True
        )
        self.otp = PhoneOTP.objects.create(phone_number=self.phone, otp_code="1234")
    
    def test_verify_login_success(self):
        """Test successful login verification"""
        response = client.post("/auth/verify-login", json={
            "phone_number": self.phone,
            "otp_code": "1234"
        })
        
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIsNotNone(data["token"])
        self.assertEqual(data["data"]["name"], "Test User")
    
    def test_verify_login_invalid_otp(self):
        """Test login verification with invalid OTP"""
        response = client.post("/auth/verify-login", json={
            "phone_number": self.phone,
            "otp_code": "0000"
        })
        
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("Invalid OTP", data["message"])
    
    def test_verify_login_expired_otp(self):
        """Test login verification with expired OTP"""
        self.otp.expires_at = timezone.now() - timedelta(minutes=1)
        self.otp.save()
        
        response = client.post("/auth/verify-login", json={
            "phone_number": self.phone,
            "otp_code": "1234"
        })
        
        data = response.json()
        self.assertFalse(data["success"])
    
    def test_verify_login_no_otp_record(self):
        """Test login verification without OTP record"""
        response = client.post("/auth/verify-login", json={
            "phone_number": "+9999999999",
            "otp_code": "1234"
        })
        
        data = response.json()
        self.assertFalse(data["success"])
        self.assertIn("No OTP found", data["message"])


class GetProfileAPITests(TestCase):
    """Test get profile endpoint - /auth/profile"""
    
    def setUp(self):
        self.phone = "+1234567890"
        self.user = User.objects.create_user(username=self.phone, password="test")
        self.interest = EventInterest.objects.create(name="Music", is_active=True)
        self.profile = UserProfile.objects.create(
            user=self.user,
            phone_number=self.phone,
            name="Test User",
            gender="male",
            bio="Test bio",
            location="NYC",
            birth_date=date(2000, 1, 1),
            is_verified=True
        )
        self.profile.event_interests.add(self.interest)
        self.token = create_jwt_token(self.user.id, self.phone)
    
    def test_get_profile_success(self):
        """Test successful profile retrieval"""
        response = client.get(
            "/auth/profile",
            headers={"Authorization": f"Bearer {self.token}"}
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["name"], "Test User")
        self.assertEqual(data["phone_number"], self.phone)
    
    def test_get_profile_invalid_token(self):
        """Test profile retrieval with invalid token"""
        response = client.get(
            "/auth/profile",
            headers={"Authorization": "Bearer invalid"}
        )
        self.assertEqual(response.status_code, 401)
    
    def test_get_profile_no_token(self):
        """Test profile retrieval without token"""
        response = client.get("/auth/profile")
        self.assertEqual(response.status_code, 403)


class GetEventInterestsAPITests(TestCase):
    """Test get event interests endpoint - /auth/event-interests"""
    
    def test_get_event_interests_success(self):
        """Test successful retrieval of event interests"""
        EventInterest.objects.create(name="Music", description="Music events", is_active=True)
        EventInterest.objects.create(name="Sports", description="Sports events", is_active=True)
        EventInterest.objects.create(name="Inactive", is_active=False)
        
        response = client.get("/auth/event-interests")
        
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 2)  # Only active interests
    
    def test_get_event_interests_empty(self):
        """Test retrieval when no event interests exist"""
        response = client.get("/auth/event-interests")
        
        data = response.json()
        self.assertTrue(data["success"])
        self.assertEqual(len(data["data"]), 0)
    
    def test_get_event_interests_ordering(self):
        """Test event interests are ordered by name"""
        EventInterest.objects.create(name="Zebra", is_active=True)
        EventInterest.objects.create(name="Apple", is_active=True)
        
        response = client.get("/auth/event-interests")
        
        data = response.json()
        self.assertEqual(data["data"][0]["name"], "Apple")
        self.assertEqual(data["data"][1]["name"], "Zebra")


class LogoutAPITests(TestCase):
    """Test logout endpoint - /auth/logout"""
    
    def test_logout_success(self):
        """Test successful logout"""
        response = client.post("/auth/logout")
        
        data = response.json()
        self.assertTrue(data["success"])
        self.assertIn("Logged out successfully", data["message"])


class JWTTokenTests(TestCase):
    """Test JWT token creation and verification"""
    
    def test_create_jwt_token(self):
        """Test JWT token creation"""
        token = create_jwt_token(1, "+1234567890")
        self.assertIsNotNone(token)
        
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        self.assertEqual(payload['user_id'], 1)
        self.assertEqual(payload['phone_number'], "+1234567890")
    
    def test_verify_jwt_token_success(self):
        """Test JWT token verification success"""
        token = create_jwt_token(1, "+1234567890")
        payload = verify_jwt_token(token)
        
        self.assertEqual(payload['user_id'], 1)
        self.assertEqual(payload['phone_number'], "+1234567890")
    
    def test_verify_jwt_token_expired(self):
        """Test JWT token verification with expired token"""
        payload = {
            'user_id': 1,
            'phone_number': "+1234567890",
            'exp': datetime.utcnow() - timedelta(days=1),
            'iat': datetime.utcnow()
        }
        expired_token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
        
        with self.assertRaises(HTTPException) as context:
            verify_jwt_token(expired_token)
        self.assertEqual(context.exception.status_code, 401)
    
    def test_verify_jwt_token_invalid(self):
        """Test JWT token verification with invalid token"""
        with self.assertRaises(HTTPException) as context:
            verify_jwt_token("invalid_token")
        self.assertEqual(context.exception.status_code, 401)


class EdgeCaseTests(TestCase):
    """Test edge cases and boundary conditions"""
    
    def test_phone_number_international_formats(self):
        """Test various international phone number formats"""
        test_cases = [
            "+1234567890",      # US format
            "+441234567890",    # UK format
            "+919876543210",    # India format
            "+861234567890",    # China format
        ]
        
        for phone in test_cases:
            with patch('users.auth_router.twilio_service.send_otp_sms') as mock:
                mock.return_value = (True, "OTP sent")
                response = client.post("/auth/signup", json={"phone_number": phone})
                self.assertEqual(response.status_code, 200)
    
    def test_concurrent_otp_requests(self):
        """Test handling of concurrent OTP requests for same phone"""
        phone = "+1234567890"
        otp1 = PhoneOTP.objects.create(phone_number=phone, otp_code="1234")
        
        # Generate new OTP (simulates concurrent request)
        otp1.generate_otp()
        otp1.save()
        
        # Old OTP should be invalid
        is_valid, _ = otp1.verify_otp("1234")
        self.assertFalse(is_valid)
    
    def test_profile_completion_boundary_values(self):
        """Test profile completion with boundary values"""
        user = User.objects.create_user(username="+1234567890", password="test")
        UserProfile.objects.create(user=user, phone_number="+1234567890", is_verified=True)
        token = create_jwt_token(user.id, "+1234567890")
        
        # Test with minimum values
        interests = [EventInterest.objects.create(name="Test", is_active=True).id]
        birth_date = (date.today() - timedelta(days=365*18)).strftime('%Y-%m-%d')
        
        response = client.post(
            "/auth/complete-profile",
            json={
                "phone_number": "+1234567890",
                "name": "ABC",  # Minimum 3 chars
                "birth_date": birth_date,  # Exactly 18 years
                "gender": "male",
                "event_interests": interests,  # Minimum 1
                "profile_pictures": ["http://example.com/1.jpg"]  # Minimum 1
            },
            headers={"Authorization": f"Bearer {token}"}
        )
        
        self.assertEqual(response.status_code, 200)
    
    def test_special_characters_in_name(self):
        """Test name validation with special characters"""
        test_cases = [
            ("John O'Brien", True),      # Apostrophe - valid
            ("Mary-Jane", True),         # Hyphen - valid
            ("Jean Paul", True),         # Space - valid
            ("John@Doe", False),         # @ symbol - invalid
            ("John123", False),          # Numbers - invalid
            ("John_Doe", False),         # Underscore - invalid
        ]
        
        for name, should_pass in test_cases:
            user = User.objects.create_user(username=f"+123456789{len(test_cases)}", password="test")
            UserProfile.objects.create(user=user, phone_number=user.username, is_verified=True)
            token = create_jwt_token(user.id, user.username)
            
            interest = EventInterest.objects.create(name=f"Interest{len(test_cases)}", is_active=True)
            birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
            
            response = client.post(
                "/auth/complete-profile",
                json={
                    "phone_number": user.username,
                    "name": name,
                    "birth_date": birth_date,
                    "gender": "male",
                    "event_interests": [interest.id],
                    "profile_pictures": ["http://example.com/pic.jpg"]
                },
                headers={"Authorization": f"Bearer {token}"}
            )
            
            if should_pass:
                self.assertEqual(response.status_code, 200, f"Failed for name: {name}")
            else:
                self.assertEqual(response.status_code, 422, f"Should fail for name: {name}")

