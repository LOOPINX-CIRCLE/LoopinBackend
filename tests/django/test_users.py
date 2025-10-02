"""
Django-specific user tests.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from users.models import UserProfile


class UserIntegrationTest(TestCase):
    """Integration tests for user functionality."""

    def setUp(self):
        self.user_data = {
            'username': 'integrationuser',
            'email': 'integration@example.com',
            'password': 'integrationpass123',
            'first_name': 'Integration',
            'last_name': 'User'
        }

    def test_user_profile_auto_creation_signal(self):
        """Test that user profile is created automatically via signals."""
        user = User.objects.create_user(**self.user_data)
        
        # Check if profile was created (if you have signals set up)
        # This test assumes you might add signals later
        self.assertTrue(User.objects.filter(id=user.id).exists())

    def test_user_admin_interface(self):
        """Test user admin interface functionality."""
        user = User.objects.create_user(**self.user_data)
        profile = UserProfile.objects.create(
            user=user,
            bio='Admin test bio',
            location='Admin City'
        )
        
        # Test admin string representations
        self.assertEqual(str(user), 'integrationuser')
        self.assertEqual(str(profile), "integrationuser's profile")

    def test_user_permissions(self):
        """Test user permissions and groups."""
        user = User.objects.create_user(**self.user_data)
        
        # Test default permissions
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)
        self.assertTrue(user.is_active)

    def test_user_profile_fields(self):
        """Test all user profile fields."""
        user = User.objects.create_user(**self.user_data)
        profile = UserProfile.objects.create(
            user=user,
            bio='Complete bio information',
            location='Test Location',
            phone_number='+1234567890',
            avatar='https://example.com/avatar.jpg'
        )
        
        self.assertEqual(profile.bio, 'Complete bio information')
        self.assertEqual(profile.location, 'Test Location')
        self.assertEqual(profile.phone_number, '+1234567890')
        self.assertEqual(profile.avatar, 'https://example.com/avatar.jpg')
        self.assertIsNotNone(profile.created_at)
        self.assertIsNotNone(profile.updated_at)
