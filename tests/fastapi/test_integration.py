#!/usr/bin/env python3
"""
API Test Script for Loopin Backend
Demonstrates the complete authentication flow and API usage
"""

import requests
import json
import sys

BASE_URL = "http://localhost:8000/api"

def test_health():
    """Test API health endpoint"""
    print("🔍 Testing API health...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        print("✅ API is healthy:", response.json())
        return True
    else:
        print("❌ API health check failed:", response.status_code)
        return False

def test_register():
    """Test user registration"""
    print("\n👤 Testing user registration...")
    user_data = {
        "username": "apitest",
        "email": "apitest@example.com",
        "password": "testpassword123",
        "first_name": "API",
        "last_name": "Test"
    }
    
    response = requests.post(f"{BASE_URL}/auth/register", json=user_data)
    if response.status_code == 200:
        user = response.json()
        print("✅ User registered successfully:")
        print(f"   ID: {user['id']}")
        print(f"   Username: {user['username']}")
        print(f"   Email: {user['email']}")
        return True
    elif response.status_code == 400 and "already registered" in response.json().get("detail", ""):
        print("ℹ️  User already exists, continuing...")
        return True
    else:
        print("❌ Registration failed:", response.status_code, response.text)
        return False

def test_login():
    """Test user login and return JWT token"""
    print("\n🔐 Testing user login...")
    login_data = {
        "username": "apitest",
        "password": "testpassword123"
    }
    
    response = requests.post(f"{BASE_URL}/auth/login", json=login_data)
    if response.status_code == 200:
        token_data = response.json()
        print("✅ Login successful:")
        print(f"   Token type: {token_data['token_type']}")
        print(f"   Expires in: {token_data['expires_in']} seconds")
        print(f"   Token: {token_data['access_token'][:50]}...")
        return token_data['access_token']
    else:
        print("❌ Login failed:", response.status_code, response.text)
        return None

def test_protected_endpoint(token):
    """Test protected endpoint with JWT token"""
    print("\n🛡️  Testing protected endpoint...")
    headers = {"Authorization": f"Bearer {token}"}
    
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    if response.status_code == 200:
        user = response.json()
        print("✅ Protected endpoint access successful:")
        print(f"   User: {user['username']} ({user['first_name']} {user['last_name']})")
        print(f"   Email: {user['email']}")
        print(f"   Active: {user['is_active']}")
        return True
    else:
        print("❌ Protected endpoint failed:", response.status_code, response.text)
        return False

def test_invalid_token():
    """Test endpoint with invalid token"""
    print("\n🚫 Testing invalid token...")
    headers = {"Authorization": "Bearer invalid_token_here"}
    
    response = requests.get(f"{BASE_URL}/auth/me", headers=headers)
    if response.status_code == 401:
        print("✅ Invalid token correctly rejected")
        return True
    else:
        print("❌ Invalid token should have been rejected:", response.status_code)
        return False

def main():
    """Run all API tests"""
    print("🚀 Starting Loopin Backend API Tests")
    print("=" * 50)
    
    tests = [
        test_health,
        test_register,
        test_login,
    ]
    
    # Run basic tests
    for test in tests:
        if not test():
            print("\n❌ Test suite failed!")
            sys.exit(1)
    
    # Get token for protected tests
    token = test_login()
    if not token:
        print("\n❌ Could not get authentication token!")
        sys.exit(1)
    
    # Run protected endpoint tests
    protected_tests = [
        lambda: test_protected_endpoint(token),
        test_invalid_token,
    ]
    
    for test in protected_tests:
        if not test():
            print("\n❌ Test suite failed!")
            sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎉 All tests passed successfully!")
    print("\n📚 API Documentation: http://localhost:8000/api/docs")
    print("🔧 Django Admin: http://localhost:8000/django/admin/")
    print("   Username: admin")
    print("   Password: admin123")

if __name__ == "__main__":
    try:
        main()
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to API. Make sure the server is running:")
        print("   docker-compose up -d")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n\n👋 Test interrupted by user")
        sys.exit(0)
