"""
Tests for event models, views, and serializers.
"""

from django.test import TestCase
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta

from events.models import Venue, Event, EventRequest, EventInvite, EventAttendee
from events.serializers.event_serializers import (
    VenueSerializer,
    EventSerializer,
    EventCreateSerializer,
    EventRequestSerializer,
    EventAttendeeSerializer,
)


class VenueModelTest(TestCase):
    """Test cases for Venue model."""

    def setUp(self):
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test Street',
            city='Test City',
            venue_type='indoor',
            capacity=100
        )

    def test_venue_creation(self):
        """Test venue creation."""
        self.assertEqual(self.venue.name, 'Test Venue')
        self.assertEqual(self.venue.city, 'Test City')
        self.assertEqual(self.venue.capacity, 100)
        self.assertTrue(self.venue.is_active)

    def test_venue_string_representation(self):
        """Test Venue string representation."""
        self.assertEqual(str(self.venue), 'Test Venue - Test City')


class EventModelTest(TestCase):
    """Test cases for Event model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test Street',
            city='Test City'
        )
        self.event = Event.objects.create(
            host=self.user,
            title='Test Event',
            description='Test Description',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=3),
            venue=self.venue,
            max_capacity=50
        )

    def test_event_creation(self):
        """Test event creation."""
        self.assertEqual(self.event.title, 'Test Event')
        self.assertEqual(self.event.host, self.user)
        self.assertEqual(self.event.venue, self.venue)
        self.assertEqual(self.event.status, 'draft')
        self.assertEqual(self.event.going_count, 0)

    def test_event_string_representation(self):
        """Test Event string representation."""
        self.assertEqual(str(self.event), 'Test Event')

    def test_is_past_property(self):
        """Test is_past property."""
        # Future event
        self.assertFalse(self.event.is_past)
        
        # Past event
        past_event = Event.objects.create(
            host=self.user,
            title='Past Event',
            description='Past',
            start_time=timezone.now() - timedelta(days=2),
            end_time=timezone.now() - timedelta(days=1)
        )
        self.assertTrue(past_event.is_past)

    def test_is_full_property(self):
        """Test is_full property."""
        # Not full
        self.assertFalse(self.event.is_full)
        
        # Full event
        full_event = Event.objects.create(
            host=self.user,
            title='Full Event',
            description='Full',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=3),
            max_capacity=2,
            going_count=2
        )
        self.assertTrue(full_event.is_full)


class EventRequestModelTest(TestCase):
    """Test cases for EventRequest model."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.event = Event.objects.create(
            host=self.user,
            title='Test Event',
            description='Test',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=3)
        )

    def test_event_request_creation(self):
        """Test event request creation."""
        request = EventRequest.objects.create(
            event=self.event,
            requester=self.user,
            message='Please accept me',
            seats_requested=2
        )
        self.assertEqual(request.event, self.event)
        self.assertEqual(request.requester, self.user)
        self.assertEqual(request.status, 'pending')

    def test_event_request_string_representation(self):
        """Test EventRequest string representation."""
        request = EventRequest.objects.create(
            event=self.event,
            requester=self.user
        )
        expected = f"{self.user} requests to join {self.event.title}"
        self.assertEqual(str(request), expected)


class VenueSerializerTest(TestCase):
    """Test cases for venue serializers."""

    def setUp(self):
        self.venue = Venue.objects.create(
            name='Test Venue',
            address='123 Test Street',
            city='Test City',
            capacity=100
        )

    def test_venue_serializer(self):
        """Test VenueSerializer."""
        serializer = VenueSerializer(self.venue)
        expected_fields = [
            'id', 'name', 'address', 'city', 'venue_type', 
            'capacity', 'latitude', 'longitude', 'is_active',
            'created_at', 'updated_at'
        ]
        self.assertEqual(set(serializer.data.keys()), set(expected_fields))


class EventSerializerTest(TestCase):
    """Test cases for event serializers."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.event = Event.objects.create(
            host=self.user,
            title='Test Event',
            description='Test',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=3)
        )

    def test_event_serializer(self):
        """Test EventSerializer."""
        serializer = EventSerializer(self.event)
        self.assertIn('host', serializer.data)
        self.assertIn('title', serializer.data)
        self.assertEqual(serializer.data['title'], 'Test Event')


class EventAPITest(APITestCase):
    """Test cases for event API endpoints."""

    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)

    def test_create_event(self):
        """Test event creation via API."""
        url = reverse('event-list-create')
        data = {
            'title': 'New Event',
            'description': 'New Event Description',
            'start_time': (timezone.now() + timedelta(days=1)).isoformat(),
            'end_time': (timezone.now() + timedelta(days=1, hours=3)).isoformat(),
            'max_capacity': 50
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(Event.objects.count(), 1)

    def test_list_events(self):
        """Test listing events via API."""
        # Create some events
        Event.objects.create(
            host=self.user,
            title='Event 1',
            start_time=timezone.now() + timedelta(days=1),
            end_time=timezone.now() + timedelta(days=1, hours=3)
        )
        Event.objects.create(
            host=self.user,
            title='Event 2',
            start_time=timezone.now() + timedelta(days=2),
            end_time=timezone.now() + timedelta(days=2, hours=3)
        )
        
        url = reverse('event-list-create')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)

