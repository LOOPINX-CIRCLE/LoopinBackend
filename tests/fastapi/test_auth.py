"""
FastAPI authentication tests.
"""

import pytest
from fastapi.testclient import TestClient
from django.contrib.auth.models import User
from django.test import TestCase, override_settings
import os
import django
from unittest.mock import patch

# Setup Django for testing
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loopin_backend.settings.dev')
django.setup()


class FastAPIAuthTest(TestCase):
    """Test FastAPI authentication endpoints."""

    def setUp(self):
        """Set up test client and test data."""
        # Import here to ensure Django is set up
        from loopin_backend.asgi import app
        from fastapi.testclient import TestClient
        
        self.client = TestClient(app)
        self.test_user_data = {
            "username": "fastapiuser",
            "email": "fastapi@example.com",
            "password": "fastapipass123",
            "first_name": "FastAPI",
            "last_name": "User"
        }

    def test_health_endpoint(self):
        """Test API health endpoint."""
        response = self.client.get("/api/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "loopin-backend")

    def test_root_endpoint(self):
        """Test API root endpoint."""
        response = self.client.get("/api/")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("message", data)
        self.assertIn("version", data)

    def test_register_user_success(self):
        """Test successful user registration."""
        response = self.client.post("/api/auth/register", json=self.test_user_data)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["username"], self.test_user_data["username"])
        self.assertEqual(data["email"], self.test_user_data["email"])
        self.assertEqual(data["first_name"], self.test_user_data["first_name"])
        self.assertTrue(data["is_active"])

    def test_register_user_duplicate_username(self):
        """Test registration with duplicate username."""
        # Create first user
        self.client.post("/api/auth/register", json=self.test_user_data)
        
        # Try to create duplicate
        response = self.client.post("/api/auth/register", json=self.test_user_data)
        self.assertEqual(response.status_code, 400)
        
        data = response.json()
        self.assertIn("already registered", data["detail"])

    def test_login_success(self):
        """Test successful login."""
        # Register user first
        self.client.post("/api/auth/register", json=self.test_user_data)
        
        # Login
        login_data = {
            "username": self.test_user_data["username"],
            "password": self.test_user_data["password"]
        }
        response = self.client.post("/api/auth/login", json=login_data)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
        self.assertIn("expires_in", data)

    def test_login_invalid_credentials(self):
        """Test login with invalid credentials."""
        login_data = {
            "username": "nonexistent",
            "password": "wrongpassword"
        }
        response = self.client.post("/api/auth/login", json=login_data)
        self.assertEqual(response.status_code, 401)
        
        data = response.json()
        self.assertIn("Incorrect username or password", data["detail"])

    def test_protected_endpoint_with_valid_token(self):
        """Test protected endpoint with valid JWT token."""
        # Register and login user
        self.client.post("/api/auth/register", json=self.test_user_data)
        
        login_data = {
            "username": self.test_user_data["username"],
            "password": self.test_user_data["password"]
        }
        login_response = self.client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Access protected endpoint
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertEqual(data["username"], self.test_user_data["username"])

    def test_protected_endpoint_with_invalid_token(self):
        """Test protected endpoint with invalid JWT token."""
        headers = {"Authorization": "Bearer invalid_token"}
        response = self.client.get("/api/auth/me", headers=headers)
        self.assertEqual(response.status_code, 401)

    def test_protected_endpoint_without_token(self):
        """Test protected endpoint without JWT token."""
        response = self.client.get("/api/auth/me")
        self.assertEqual(response.status_code, 403)  # FastAPI returns 403 for missing auth

    def test_register_invalid_email(self):
        """Test registration with invalid email format."""
        invalid_data = self.test_user_data.copy()
        invalid_data["email"] = "invalid-email"
        
        response = self.client.post("/api/auth/register", json=invalid_data)
        self.assertEqual(response.status_code, 422)  # Pydantic validation error

    def test_token_refresh(self):
        """Test token refresh endpoint."""
        # Register and login user
        self.client.post("/api/auth/register", json=self.test_user_data)
        
        login_data = {
            "username": self.test_user_data["username"],
            "password": self.test_user_data["password"]
        }
        login_response = self.client.post("/api/auth/login", json=login_data)
        token = login_response.json()["access_token"]
        
        # Refresh token
        headers = {"Authorization": f"Bearer {token}"}
        response = self.client.post("/api/auth/refresh", headers=headers)
        self.assertEqual(response.status_code, 200)
        
        data = response.json()
        self.assertIn("access_token", data)
        self.assertEqual(data["token_type"], "bearer")
