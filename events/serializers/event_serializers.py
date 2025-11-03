"""
Event-related serializers for Django REST Framework.
"""

from rest_framework import serializers
from django.contrib.auth.models import User
from events.models import Venue, Event, EventRequest, EventInvite, EventAttendee


class VenueSerializer(serializers.ModelSerializer):
    """Serializer for Venue model."""
    
    class Meta:
        model = Venue
        fields = [
            'id', 'name', 'address', 'city', 'venue_type', 
            'capacity', 'latitude', 'longitude', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class VenueListSerializer(serializers.ModelSerializer):
    """Simplified serializer for venue lists."""
    
    class Meta:
        model = Venue
        fields = ['id', 'name', 'city', 'venue_type', 'capacity']
        read_only_fields = ['id']


class EventSerializer(serializers.ModelSerializer):
    """Serializer for Event model."""
    
    host = serializers.StringRelatedField(read_only=True)
    venue = VenueListSerializer(read_only=True)
    venue_id = serializers.PrimaryKeyRelatedField(
        queryset=Venue.objects.filter(is_active=True),
        write_only=True,
        required=False,
        allow_null=True
    )
    
    class Meta:
        model = Event
        fields = [
            'id', 'host', 'title', 'description', 'start_time', 'end_time',
            'venue', 'venue_id', 'status', 'is_public', 'max_capacity',
            'going_count', 'cover_images', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'host', 'going_count', 'created_at', 'updated_at']


class EventListSerializer(serializers.ModelSerializer):
    """Simplified serializer for event lists."""
    
    host = serializers.StringRelatedField()
    venue = serializers.StringRelatedField()
    status = serializers.CharField(source='get_status_display')
    
    class Meta:
        model = Event
        fields = [
            'id', 'title', 'host', 'venue', 'start_time', 'end_time',
            'status', 'going_count', 'max_capacity', 'cover_images'
        ]


class EventCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new events."""
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'start_time', 'end_time',
            'venue', 'status', 'is_public', 'max_capacity', 'cover_images'
        ]
        read_only_fields = ['status']
    
    def validate(self, attrs):
        """Validate event data."""
        # Check that end_time is after start_time
        if attrs.get('end_time') and attrs.get('start_time'):
            if attrs['end_time'] <= attrs['start_time']:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time.'
                })
        return attrs
    
    def create(self, validated_data):
        """Create event with host set to current user."""
        validated_data['host'] = self.context['request'].user
        return super().create(validated_data)


class EventUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating events."""
    
    class Meta:
        model = Event
        fields = [
            'title', 'description', 'start_time', 'end_time',
            'venue', 'status', 'is_public', 'max_capacity', 'cover_images', 'is_active'
        ]
    
    def validate(self, attrs):
        """Validate event data."""
        # Check that end_time is after start_time
        if 'end_time' in attrs and 'start_time' in attrs:
            if attrs['end_time'] <= attrs['start_time']:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time.'
                })
        elif 'end_time' in attrs:
            start_time = self.instance.start_time if self.instance else None
            if start_time and attrs['end_time'] <= start_time:
                raise serializers.ValidationError({
                    'end_time': 'End time must be after start time.'
                })
        elif 'start_time' in attrs:
            end_time = self.instance.end_time if self.instance else None
            if end_time and attrs['start_time'] >= end_time:
                raise serializers.ValidationError({
                    'start_time': 'Start time must be before end time.'
                })
        return attrs


class EventRequestSerializer(serializers.ModelSerializer):
    """Serializer for EventRequest model."""
    
    requester = serializers.StringRelatedField(read_only=True)
    event = EventListSerializer(read_only=True)
    
    class Meta:
        model = EventRequest
        fields = [
            'id', 'requester', 'event', 'status', 'message', 
            'seats_requested', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'requester', 'created_at', 'updated_at']


class EventRequestCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating event requests."""
    
    class Meta:
        model = EventRequest
        fields = ['event', 'message', 'seats_requested']
    
    def create(self, validated_data):
        """Create request with requester set to current user."""
        validated_data['requester'] = self.context['request'].user
        return super().create(validated_data)


class EventInviteSerializer(serializers.ModelSerializer):
    """Serializer for EventInvite model."""
    
    invited_user = serializers.StringRelatedField(read_only=True)
    event = EventListSerializer(read_only=True)
    
    class Meta:
        model = EventInvite
        fields = [
            'id', 'invited_user', 'event', 'status', 'message', 
            'expires_at', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class EventInviteCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating event invites."""
    
    class Meta:
        model = EventInvite
        fields = ['invited_user', 'event', 'message', 'expires_at']
    
    def validate_invited_user(self, value):
        """Validate that invited user is not the event host."""
        event = self.initial_data.get('event')
        if event and hasattr(event, 'host'):
            if value == event.host:
                raise serializers.ValidationError(
                    "Cannot invite the event host."
                )
        return value


class EventAttendeeSerializer(serializers.ModelSerializer):
    """Serializer for EventAttendee model."""
    
    user = serializers.StringRelatedField(read_only=True)
    event = serializers.StringRelatedField(read_only=True)
    
    class Meta:
        model = EventAttendee
        fields = [
            'id', 'user', 'event', 'status', 'checked_in_at', 
            'seats', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'user', 'checked_in_at', 'created_at', 'updated_at']

