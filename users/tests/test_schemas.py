"""
Comprehensive Test Suite for Pydantic Schemas
Tests all validation rules and edge cases
"""

from django.test import TestCase
from pydantic import ValidationError
from datetime import date, timedelta

from users.schemas import (
    PhoneNumberRequest,
    OTPVerificationRequest,
    CompleteProfileRequest,
    LoginRequest,
    AuthResponse,
    EventInterestResponse,
    UserProfileResponse
)


class TestPhoneNumberRequest(TestCase):
    """Test PhoneNumberRequest schema validation"""
    
    def test_valid_phone_number(self):
        """Test valid phone number formats"""
        valid_phones = [
            "+1234567890",
            "+12345678901",
            "+123456789012345",  # 15 digits (max)
            "12345678",  # 8 digits (min without +)
        ]
        
        for phone in valid_phones:
            request = PhoneNumberRequest(phone_number=phone)
            assert request.phone_number
    
    def test_phone_number_normalization(self):
        """Test phone number normalization (removes spaces, dashes, parentheses)"""
        request = PhoneNumberRequest(phone_number="+1 (234) 567-8900")
        assert request.phone_number == "+12345678900"
    
    def test_invalid_phone_number_too_short(self):
        """Test phone number too short"""
        with self.assertRaises(ValidationError):
            PhoneNumberRequest(phone_number="+123456")  # Only 6 digits
    
    def test_invalid_phone_number_too_long(self):
        """Test phone number too long"""
        with self.assertRaises(ValidationError):
            PhoneNumberRequest(phone_number="+1234567890123456")  # 16 digits
    
    def test_invalid_phone_number_starts_with_zero(self):
        """Test phone number starting with 0"""
        with self.assertRaises(ValidationError):
            PhoneNumberRequest(phone_number="+01234567890")
    
    def test_invalid_phone_number_letters(self):
        """Test phone number with letters"""
        with self.assertRaises(ValidationError):
            PhoneNumberRequest(phone_number="+123ABC7890")
    
    def test_missing_phone_number(self):
        """Test missing phone number"""
        with self.assertRaises(ValidationError):
            PhoneNumberRequest()


class TestOTPVerificationRequest(TestCase):
    """Test OTPVerificationRequest schema validation"""
    
    def test_valid_otp(self):
        """Test valid OTP code"""
        request = OTPVerificationRequest(
            phone_number="+1234567890",
            otp_code="1234"
        )
        assert request.otp_code == "1234"
    
    def test_otp_exactly_4_digits(self):
        """Test OTP must be exactly 4 digits"""
        with self.assertRaises(ValidationError):
            OTPVerificationRequest(phone_number="+1234567890", otp_code="123")  # Too short
        
        with self.assertRaises(ValidationError):
            OTPVerificationRequest(phone_number="+1234567890", otp_code="12345")  # Too long
    
    def test_otp_only_digits(self):
        """Test OTP must contain only digits"""
        with self.assertRaises(ValidationError):
            OTPVerificationRequest(phone_number="+1234567890", otp_code="12ab")
    
    def test_otp_no_spaces(self):
        """Test OTP cannot contain spaces"""
        with self.assertRaises(ValidationError):
            OTPVerificationRequest(phone_number="+1234567890", otp_code="12 34")


class TestCompleteProfileRequest(TestCase):
    """Test CompleteProfileRequest schema validation"""
    
    def test_valid_profile(self):
        """Test valid profile data"""
        birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
        request = CompleteProfileRequest(
            phone_number="+1234567890",
            name="John Doe",
            birth_date=birth_date,
            gender="male",
            event_interests=[1, 2],
            profile_pictures=["http://example.com/pic.jpg"],
            bio="Test bio",
            location="NYC"
        )
        assert request.name == "John Doe"
        assert request.gender == "male"
    
    def test_name_validation_minimum_length(self):
        """Test name must be at least 3 characters"""
        birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
        
        with self.assertRaises(ValidationError):
            CompleteProfileRequest(
                phone_number="+1234567890",
                name="AB",  # Too short
                birth_date=birth_date,
                gender="male",
                event_interests=[1],
                profile_pictures=["http://example.com/pic.jpg"]
            )
    
    def test_name_validation_valid_characters(self):
        """Test name with valid special characters"""
        birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
        
        valid_names = [
            "John O'Brien",  # Apostrophe
            "Mary-Jane",     # Hyphen
            "Jean Paul",     # Space
        ]
        
        for name in valid_names:
            request = CompleteProfileRequest(
                phone_number="+1234567890",
                name=name,
                birth_date=birth_date,
                gender="male",
                event_interests=[1],
                profile_pictures=["http://example.com/pic.jpg"]
            )
            assert request.name == name
    
    def test_name_validation_invalid_characters(self):
        """Test name with invalid characters"""
        birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
        
        invalid_names = [
            "John123",   # Numbers
            "John@Doe",  # Special char
            "John_Doe",  # Underscore
        ]
        
        for name in invalid_names:
            with self.assertRaises(ValidationError):
                CompleteProfileRequest(
                    phone_number="+1234567890",
                    name=name,
                    birth_date=birth_date,
                    gender="male",
                    event_interests=[1],
                    profile_pictures=["http://example.com/pic.jpg"]
                )
    
    def test_name_strips_whitespace(self):
        """Test name strips leading/trailing whitespace"""
        birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
        request = CompleteProfileRequest(
            phone_number="+1234567890",
            name="  John Doe  ",
            birth_date=birth_date,
            gender="male",
            event_interests=[1],
            profile_pictures=["http://example.com/pic.jpg"]
        )
        assert request.name == "John Doe"
    
    def test_birth_date_age_18_validation(self):
        """Test birth date must result in age >= 18"""
        # Exactly 18 years old (should pass)
        birth_date_18 = (date.today() - timedelta(days=365*18)).strftime('%Y-%m-%d')
        request = CompleteProfileRequest(
            phone_number="+1234567890",
            name="John Doe",
            birth_date=birth_date_18,
            gender="male",
            event_interests=[1],
            profile_pictures=["http://example.com/pic.jpg"]
        )
        assert request.birth_date == birth_date_18
        
        # 17 years old (should fail)
        birth_date_17 = (date.today() - timedelta(days=365*17)).strftime('%Y-%m-%d')
        with self.assertRaises(ValidationError) as exc:
            CompleteProfileRequest(
                phone_number="+1234567890",
                name="John Doe",
                birth_date=birth_date_17,
                gender="male",
                event_interests=[1],
                profile_pictures=["http://example.com/pic.jpg"]
            )
        assert "18 years or older" in str(exc.value)
    
    def test_birth_date_format_validation(self):
        """Test birth date format must be YYYY-MM-DD"""
        with self.assertRaises(ValidationError) as exc:
            CompleteProfileRequest(
                phone_number="+1234567890",
                name="John Doe",
                birth_date="2000/01/01",  # Wrong format
                gender="male",
                event_interests=[1],
                profile_pictures=["http://example.com/pic.jpg"]
            )
        assert "YYYY-MM-DD" in str(exc.value)
    
    def test_gender_validation(self):
        """Test gender must be male, female, or other"""
        birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
        
        valid_genders = ["male", "female", "other", "MALE", "Female"]  # Case insensitive
        
        for gender in valid_genders:
            request = CompleteProfileRequest(
                phone_number="+1234567890",
                name="John Doe",
                birth_date=birth_date,
                gender=gender,
                event_interests=[1],
                profile_pictures=["http://example.com/pic.jpg"]
            )
            assert request.gender in ["male", "female", "other"]
        
        # Invalid gender
        with self.assertRaises(ValidationError):
            CompleteProfileRequest(
                phone_number="+1234567890",
                name="John Doe",
                birth_date=birth_date,
                gender="unknown",
                event_interests=[1],
                profile_pictures=["http://example.com/pic.jpg"]
            )
    
    def test_event_interests_count_validation(self):
        """Test event interests must be 1-5"""
        birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
        
        # Minimum 1
        request = CompleteProfileRequest(
            phone_number="+1234567890",
            name="John Doe",
            birth_date=birth_date,
            gender="male",
            event_interests=[1],
            profile_pictures=["http://example.com/pic.jpg"]
        )
        assert len(request.event_interests) == 1
        
        # Maximum 5
        request = CompleteProfileRequest(
            phone_number="+1234567890",
            name="John Doe",
            birth_date=birth_date,
            gender="male",
            event_interests=[1, 2, 3, 4, 5],
            profile_pictures=["http://example.com/pic.jpg"]
        )
        assert len(request.event_interests) == 5
        
        # Zero (should fail)
        with self.assertRaises(ValidationError):
            CompleteProfileRequest(
                phone_number="+1234567890",
                name="John Doe",
                birth_date=birth_date,
                gender="male",
                event_interests=[],
                profile_pictures=["http://example.com/pic.jpg"]
            )
        
        # More than 5 (should fail)
        with self.assertRaises(ValidationError):
            CompleteProfileRequest(
                phone_number="+1234567890",
                name="John Doe",
                birth_date=birth_date,
                gender="male",
                event_interests=[1, 2, 3, 4, 5, 6],
                profile_pictures=["http://example.com/pic.jpg"]
            )
    
    def test_profile_pictures_count_validation(self):
        """Test profile pictures must be 1-6"""
        birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
        
        # Minimum 1
        request = CompleteProfileRequest(
            phone_number="+1234567890",
            name="John Doe",
            birth_date=birth_date,
            gender="male",
            event_interests=[1],
            profile_pictures=["http://example.com/pic1.jpg"]
        )
        assert len(request.profile_pictures) == 1
        
        # Maximum 6
        pics = [f"http://example.com/pic{i}.jpg" for i in range(1, 7)]
        request = CompleteProfileRequest(
            phone_number="+1234567890",
            name="John Doe",
            birth_date=birth_date,
            gender="male",
            event_interests=[1],
            profile_pictures=pics
        )
        assert len(request.profile_pictures) == 6
        
        # Zero (should fail)
        with self.assertRaises(ValidationError):
            CompleteProfileRequest(
                phone_number="+1234567890",
                name="John Doe",
                birth_date=birth_date,
                gender="male",
                event_interests=[1],
                profile_pictures=[]
            )
        
        # More than 6 (should fail)
        pics = [f"http://example.com/pic{i}.jpg" for i in range(1, 8)]
        with self.assertRaises(ValidationError):
            CompleteProfileRequest(
                phone_number="+1234567890",
                name="John Doe",
                birth_date=birth_date,
                gender="male",
                event_interests=[1],
                profile_pictures=pics
            )
    
    def test_profile_pictures_url_validation(self):
        """Test profile picture URLs must be valid"""
        birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
        
        valid_urls = [
            "http://example.com/pic.jpg",
            "https://example.com/pic.jpg",
            "http://192.168.1.1/pic.jpg",
            "http://localhost:8000/pic.jpg",
        ]
        
        for url in valid_urls:
            request = CompleteProfileRequest(
                phone_number="+1234567890",
                name="John Doe",
                birth_date=birth_date,
                gender="male",
                event_interests=[1],
                profile_pictures=[url]
            )
            assert request.profile_pictures[0] == url
        
        # Invalid URLs
        invalid_urls = [
            "not-a-url",
            "ftp://example.com/pic.jpg",  # Wrong protocol
            "example.com/pic.jpg",  # Missing protocol
        ]
        
        for url in invalid_urls:
            with self.assertRaises(ValidationError):
                CompleteProfileRequest(
                    phone_number="+1234567890",
                    name="John Doe",
                    birth_date=birth_date,
                    gender="male",
                    event_interests=[1],
                    profile_pictures=[url]
                )
    
    def test_bio_max_length(self):
        """Test bio maximum length is 500 characters"""
        birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
        
        # Exactly 500 chars (should pass)
        bio = "a" * 500
        request = CompleteProfileRequest(
            phone_number="+1234567890",
            name="John Doe",
            birth_date=birth_date,
            gender="male",
            event_interests=[1],
            profile_pictures=["http://example.com/pic.jpg"],
            bio=bio
        )
        assert len(request.bio) == 500
        
        # 501 chars (should fail)
        with self.assertRaises(ValidationError):
            CompleteProfileRequest(
                phone_number="+1234567890",
                name="John Doe",
                birth_date=birth_date,
                gender="male",
                event_interests=[1],
                profile_pictures=["http://example.com/pic.jpg"],
                bio="a" * 501
            )
    
    def test_optional_fields(self):
        """Test bio and location are optional"""
        birth_date = (date.today() - timedelta(days=365*20)).strftime('%Y-%m-%d')
        
        request = CompleteProfileRequest(
            phone_number="+1234567890",
            name="John Doe",
            birth_date=birth_date,
            gender="male",
            event_interests=[1],
            profile_pictures=["http://example.com/pic.jpg"]
            # bio and location omitted
        )
        assert request.bio is None
        assert request.location is None


class TestLoginRequest(TestCase):
    """Test LoginRequest schema validation"""
    
    def test_valid_login_request(self):
        """Test valid login request"""
        request = LoginRequest(
            phone_number="+1234567890",
            otp_code="1234"
        )
        assert request.phone_number == "+1234567890"
        assert request.otp_code == "1234"
    
    def test_otp_validation(self):
        """Test OTP validation in login request"""
        # Same rules as OTPVerificationRequest
        with self.assertRaises(ValidationError):
            LoginRequest(phone_number="+1234567890", otp_code="123")  # Too short
        
        with self.assertRaises(ValidationError):
            LoginRequest(phone_number="+1234567890", otp_code="abcd")  # Not digits


class TestAuthResponse(TestCase):
    """Test AuthResponse schema"""
    
    def test_auth_response_success(self):
        """Test successful auth response"""
        response = AuthResponse(
            success=True,
            message="Success",
            data={"user_id": 1},
            token="jwt_token_here"
        )
        assert response.success
        assert response.token == "jwt_token_here"
    
    def test_auth_response_failure(self):
        """Test failure auth response"""
        response = AuthResponse(
            success=False,
            message="Error occurred"
        )
        assert not response.success
        assert response.data is None
        assert response.token is None


class TestEventInterestResponse(TestCase):
    """Test EventInterestResponse schema"""
    
    def test_event_interest_response(self):
        """Test event interest response"""
        response = EventInterestResponse(
            id=1,
            name="Music",
            is_active=True,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00"
        )
        assert response.id == 1
        assert response.name == "Music"


class TestUserProfileResponse(TestCase):
    """Test UserProfileResponse schema"""
    
    def test_user_profile_response(self):
        """Test user profile response"""
        response = UserProfileResponse(
            id=1,
            name="John Doe",
            phone_number="+1234567890",
            gender="male",
            bio="Test bio",
            location="NYC",
            birth_date="2000-01-01",
            event_interests=[],
            profile_pictures=["http://example.com/pic.jpg"],
            is_verified=True,
            is_active=True,
            created_at="2025-01-01T00:00:00",
            updated_at="2025-01-01T00:00:00"
        )
        assert response.name == "John Doe"
        assert response.is_verified

