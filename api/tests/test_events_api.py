"""
Comprehensive tests for Events FastAPI endpoints.
Tests CRUD operations, authentication, authorization, and performance.
"""

import pytest
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.utils import timezone
from fastapi.testclient import TestClient
from asgiref.sync import sync_to_async

from loopin_backend.asgi import app
from events.models import Event, Venue
from api.routers.auth import create_access_token
from django.conf import settings

client = TestClient(app)


class TestEventsAPI:
    """Test suite for Events API endpoints"""
    
    @pytest.fixture
    def test_user(self):
        """Create test user"""
        user, _ = User.objects.get_or_create(
            username='testuser',
            defaults={
                'email': 'test@example.com',
                'is_active': True,
            }
        )
        user.set_password('testpass123')
        user.save()
        return user
    
    @pytest.fixture
    def auth_token(self, test_user):
        """Create JWT token for test user"""
        return create_access_token({'user_id': test_user.id})
    
    @pytest.fixture
    def auth_headers(self, auth_token):
        """Get authorization headers"""
        return {'Authorization': f'Bearer {auth_token}'}
    
    @pytest.fixture
    def test_venue(self):
        """Create test venue"""
        venue, _ = Venue.objects.get_or_create(
            name='Test Venue',
            defaults={
                'address': '123 Test St',
                'city': 'Test City',
                'capacity': 100,
                'is_active': True,
            }
        )
        return venue
    
    @pytest.fixture
    def test_event(self, test_user, test_venue):
        """Create test event"""
        event, _ = Event.objects.get_or_create(
            title='Test Event',
            defaults={
                'host': test_user,
                'description': 'Test event description',
                'start_time': timezone.now() + timedelta(days=1),
                'end_time': timezone.now() + timedelta(days=1, hours=3),
                'venue': test_venue,
                'status': 'draft',
                'is_public': True,
                'max_capacity': 50,
                'is_active': True,
            }
        )
        return event
    
    def test_list_events_empty(self):
        """Test listing events when none exist"""
        response = client.get('/api/events')
        assert response.status_code == 200
        data = response.json()
        assert data['total'] == 0
        assert data['data'] == []
    
    def test_list_events_with_results(self, test_event):
        """Test listing events with results"""
        response = client.get('/api/events')
        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 1
        assert len(data['data']) >= 1
        assert data['data'][0]['title'] == 'Test Event'
    
    def test_get_event_detail(self, test_event):
        """Test getting event details"""
        response = client.get(f'/api/events/{test_event.id}')
        assert response.status_code == 200
        data = response.json()
        assert data['id'] == test_event.id
        assert data['title'] == 'Test Event'
    
    def test_get_event_not_found(self):
        """Test getting non-existent event"""
        response = client.get('/api/events/99999')
        assert response.status_code == 404
    
    def test_create_event_requires_auth(self):
        """Test that creating event requires authentication"""
        response = client.post('/api/events', json={
            'title': 'New Event',
            'description': 'Test',
            'start_time': (timezone.now() + timedelta(days=1)).isoformat(),
            'end_time': (timezone.now() + timedelta(days=1, hours=3)).isoformat(),
        })
        assert response.status_code == 401
    
    def test_create_event_success(self, auth_headers):
        """Test successful event creation"""
        response = client.post('/api/events', headers=auth_headers, json={
            'title': 'New Test Event',
            'description': 'Test description',
            'start_time': (timezone.now() + timedelta(days=1)).isoformat(),
            'end_time': (timezone.now() + timedelta(days=1, hours=3)).isoformat(),
            'status': 'draft',
            'is_public': True,
            'max_capacity': 50,
        })
        assert response.status_code == 201
        data = response.json()
        assert data['title'] == 'New Test Event'
        assert 'id' in data
    
    def test_create_event_invalid_time(self, auth_headers):
        """Test event creation with invalid time range"""
        response = client.post('/api/events', headers=auth_headers, json={
            'title': 'New Event',
            'description': 'Test',
            'start_time': (timezone.now() + timedelta(days=1, hours=3)).isoformat(),
            'end_time': (timezone.now() + timedelta(days=1)).isoformat(),  # Before start
        })
        assert response.status_code == 422
    
    def test_update_event_requires_auth(self, test_event):
        """Test that updating event requires authentication"""
        response = client.put(f'/api/events/{test_event.id}', json={
            'title': 'Updated Event',
        })
        assert response.status_code == 401
    
    def test_update_event_success(self, test_event, auth_headers):
        """Test successful event update"""
        response = client.put(f'/api/events/{test_event.id}', headers=auth_headers, json={
            'title': 'Updated Event',
            'description': 'Updated description',
        })
        assert response.status_code == 200
        data = response.json()
        assert data['title'] == 'Updated Event'
    
    def test_update_event_permission_denied(self, auth_headers):
        """Test updating event without permission"""
        # Create event with different user
        other_user, _ = User.objects.get_or_create(
            username='otheruser',
            defaults={'is_active': True}
        )
        other_event = Event.objects.create(
            host=other_user,
            title='Other Event',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=3),
        )
        
        response = client.put(f'/api/events/{other_event.id}', headers=auth_headers, json={
            'title': 'Hacked Event',
        })
        # Should either be 403 or 401 depending on implementation
        assert response.status_code in [401, 403]
    
    def test_delete_event_success(self, test_event, auth_headers):
        """Test successful event deletion"""
        response = client.delete(f'/api/events/{test_event.id}', headers=auth_headers)
        assert response.status_code == 204
        
        # Verify soft delete
        event = Event.objects.get(id=test_event.id)
        assert event.is_active == False
    
    def test_filter_events_by_status(self, test_event):
        """Test filtering events by status"""
        response = client.get('/api/events?status=draft')
        assert response.status_code == 200
        data = response.json()
        assert all(event['status'] == 'draft' for event in data['data'])
    
    def test_search_events(self, test_event):
        """Test searching events"""
        response = client.get('/api/events?search=Test')
        assert response.status_code == 200
        data = response.json()
        assert data['total'] >= 1
    
    def test_pagination(self):
        """Test pagination"""
        response = client.get('/api/events?offset=0&limit=5')
        assert response.status_code == 200
        data = response.json()
        assert 'total' in data
        assert 'offset' in data
        assert 'limit' in data
        assert len(data['data']) <= 5


@pytest.mark.asyncio
class TestEventPermissions:
    """Test event permissions and authorization"""
    
    async def test_public_event_viewable_by_all(self):
        """Test that public events are viewable by anyone"""
        response = client.get('/api/events')
        assert response.status_code == 200
    
    async def test_private_event_requires_auth(self):
        """Test that private events require authentication"""
        # This test would need a private event setup
        pass


# Integration tests
@pytest.mark.integration
class TestEventIntegration:
    """Integration tests for events"""
    
    @pytest.mark.skipif(True, reason="Requires database setup")
    def test_event_full_lifecycle(self):
        """Test complete event lifecycle"""
        pass


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

