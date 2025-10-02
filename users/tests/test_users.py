"""
Tests for user models, views, and serializers.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse

from users.models import UserProfile
from users.serializers.user_serializers import UserSerializer, UserCreateSerializer


class UserModelTest(TestCase):
    """Test cases for User and UserProfile models."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_user_creation(self):
        """Test user creation."""
        self.assertEqual(self.user.username, 'testuser')
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertTrue(self.user.check_password('testpass123'))

    def test_user_profile_creation(self):
        """Test user profile creation."""
        profile = UserProfile.objects.create(
            user=self.user,
            bio='Test bio',
            location='Test City'
        )
        self.assertEqual(profile.user, self.user)
        self.assertEqual(profile.bio, 'Test bio')
        self.assertEqual(profile.location, 'Test City')

    def test_user_profile_string_representation(self):
        """Test UserProfile string representation."""
        profile = UserProfile.objects.create(user=self.user)
        self.assertEqual(str(profile), "testuser's profile")


class UserSerializerTest(TestCase):
    """Test cases for user serializers."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123',
            first_name='Test',
            last_name='User'
        )

    def test_user_serializer(self):
        """Test UserSerializer."""
        serializer = UserSerializer(self.user)
        expected_fields = ['id', 'username', 'email', 'first_name', 'last_name', 'is_active', 'date_joined']
        self.assertEqual(set(serializer.data.keys()), set(expected_fields))

    def test_user_create_serializer_valid_data(self):
        """Test UserCreateSerializer with valid data."""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'password_confirm': 'newpass123',
            'first_name': 'New',
            'last_name': 'User'
        }
        serializer = UserCreateSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_user_create_serializer_password_mismatch(self):
        """Test UserCreateSerializer with password mismatch."""
        data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'newpass123',
            'password_confirm': 'differentpass',
            'first_name': 'New',
            'last_name': 'User'
        }
        serializer = UserCreateSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('non_field_errors', serializer.errors)


class UserAPITest(APITestCase):
    """Test cases for user API endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.admin_user = User.objects.create_superuser(
            username='admin',
            email='admin@example.com',
            password='adminpass123'
        )

    def test_current_user_endpoint_authenticated(self):
        """Test current user endpoint with authenticated user."""
        self.client.force_authenticate(user=self.user)
        url = reverse('users:current-user')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['username'], 'testuser')

    def test_current_user_endpoint_unauthenticated(self):
        """Test current user endpoint without authentication."""
        url = reverse('users:current-user')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_list_admin_access(self):
        """Test user list endpoint with admin access."""
        self.client.force_authenticate(user=self.admin_user)
        url = reverse('users:user-list-create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIsInstance(response.data, list)

    def test_user_list_regular_user_access(self):
        """Test user list endpoint with regular user access."""
        self.client.force_authenticate(user=self.user)
        url = reverse('users:user-list-create')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_change_password_valid(self):
        """Test password change with valid data."""
        self.client.force_authenticate(user=self.user)
        url = reverse('users:change-password')
        data = {
            'old_password': 'testpass123',
            'new_password': 'newtestpass123'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        
        # Verify password was changed
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password('newtestpass123'))

    def test_change_password_invalid_old_password(self):
        """Test password change with invalid old password."""
        self.client.force_authenticate(user=self.user)
        url = reverse('users:change-password')
        data = {
            'old_password': 'wrongpassword',
            'new_password': 'newtestpass123'
        }
        response = self.client.post(url, data)
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)
