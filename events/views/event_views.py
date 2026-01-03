"""
Event-related views for Django REST Framework.
"""

from rest_framework import generics, permissions, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q

from events.models import Venue, Event, EventRequest, EventInvite, EventAttendee
from events.serializers.event_serializers import (
    VenueSerializer,
    VenueListSerializer,
    EventSerializer,
    EventListSerializer,
    EventCreateSerializer,
    EventUpdateSerializer,
    EventRequestSerializer,
    EventRequestCreateSerializer,
    EventInviteSerializer,
    EventInviteCreateSerializer,
    EventAttendeeSerializer,
)


class VenueListCreateView(generics.ListCreateAPIView):
    """List all venues or create a new venue."""
    
    queryset = Venue.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return VenueListSerializer
        return VenueSerializer


class VenueRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a venue."""
    
    queryset = Venue.objects.all()
    serializer_class = VenueSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def perform_destroy(self, instance):
        """Soft delete by deactivating venue."""
        instance.is_active = False
        instance.save()


class EventListCreateView(generics.ListCreateAPIView):
    """List all events or create a new event."""
    
    queryset = Event.objects.filter(is_active=True)
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return EventListSerializer
        return EventCreateSerializer
    
    def get_queryset(self):
        """Filter events based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by host
        host_id = self.request.query_params.get('host')
        if host_id:
            queryset = queryset.filter(host_id=host_id)
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        # Filter by upcoming/past
        show_past = self.request.query_params.get('show_past', 'false').lower() == 'true'
        if not show_past:
            queryset = queryset.filter(end_time__gte=timezone.now())
        
        # Filter by public/private
        is_public = self.request.query_params.get('is_public')
        if is_public is not None:
            queryset = queryset.filter(is_public=is_public.lower() == 'true')
        
        # Search by title
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(title__icontains=search)
        
        return queryset.order_by('-start_time')


class EventRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete an event."""
    
    queryset = Event.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return EventSerializer
        elif self.request.method in ['PUT', 'PATCH']:
            return EventUpdateSerializer
        return EventSerializer
    
    def get_permissions(self):
        """Only event host can update/delete."""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def perform_destroy(self, instance):
        """Soft delete by deactivating event."""
        instance.is_active = False
        instance.save()
    
    def get_object(self):
        """Ensure users can only update their own events."""
        obj = super().get_object()
        user = self.request.user
        
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            if not user.is_staff and obj.host != user:
                self.permission_denied(
                    self.request, 
                    message="You can only modify your own events."
                )
        
        return obj


class EventRequestListCreateView(generics.ListCreateAPIView):
    """List all event requests or create a new request."""
    
    queryset = EventRequest.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return EventRequestSerializer
        return EventRequestCreateSerializer
    
    def get_queryset(self):
        """Filter requests based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by requester
        requester_id = self.request.query_params.get('requester')
        if requester_id:
            queryset = queryset.filter(requester_id=requester_id)
        
        # Filter by event
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')


class EventRequestRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete an event request."""
    
    queryset = EventRequest.objects.all()
    serializer_class = EventRequestSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Only requester or event host can modify."""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def get_object(self):
        """Ensure proper permissions."""
        obj = super().get_object()
        user = self.request.user
        
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            if not user.is_staff and obj.requester != user and obj.event.host != user:
                self.permission_denied(
                    self.request, 
                    message="You can only modify your own requests or manage requests for your events."
                )
        
        return obj


class EventInviteListCreateView(generics.ListCreateAPIView):
    """List all event invites or create a new invite."""
    
    queryset = EventInvite.objects.all()
    permission_classes = [permissions.IsAuthenticated]
    
    def get_serializer_class(self):
        if self.request.method == 'GET':
            return EventInviteSerializer
        return EventInviteCreateSerializer
    
    def get_queryset(self):
        """Filter invites based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by invited user
        invited_user_id = self.request.query_params.get('invited_user')
        if invited_user_id:
            queryset = queryset.filter(invited_user_id=invited_user_id)
        
        # Filter by event
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')


class EventInviteRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete an event invite."""
    
    queryset = EventInvite.objects.all()
    serializer_class = EventInviteSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Only invited user or event host can modify."""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def get_object(self):
        """Ensure proper permissions."""
        obj = super().get_object()
        user = self.request.user
        
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            if not user.is_staff and obj.invited_user != user and obj.event.host != user:
                self.permission_denied(
                    self.request, 
                    message="You can only modify your own invites or manage invites for your events."
                )
        
        return obj


class EventAttendeeListCreateView(generics.ListCreateAPIView):
    """List all event attendees or create a new attendance record."""
    
    queryset = EventAttendee.objects.all()
    serializer_class = EventAttendeeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Filter attendees based on query parameters."""
        queryset = super().get_queryset()
        
        # Filter by user
        user_id = self.request.query_params.get('user')
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        
        # Filter by event
        event_id = self.request.query_params.get('event')
        if event_id:
            queryset = queryset.filter(event_id=event_id)
        
        # Filter by status
        status = self.request.query_params.get('status')
        if status:
            queryset = queryset.filter(status=status)
        
        return queryset.order_by('-created_at')


class EventAttendeeRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete an attendance record."""
    
    queryset = EventAttendee.objects.all()
    serializer_class = EventAttendeeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        """Only user or event host can modify."""
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def get_object(self):
        """Ensure proper permissions."""
        obj = super().get_object()
        user = self.request.user
        
        if self.request.method in ['PUT', 'PATCH', 'DELETE']:
            if not user.is_staff and obj.user != user and obj.event.host != user:
                self.permission_denied(
                    self.request, 
                    message="You can only modify your own attendance or manage attendance for your events."
                )
        
        return obj


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
def check_in_attendee_view(request, event_id):
    """Check in an attendee for an event."""
    event = get_object_or_404(Event, id=event_id, is_active=True)
    user = request.user
    
    # Verify user has permission to check in
    if not request.user.is_staff and event.host != request.user:
        return Response(
            {'error': 'You can only check in attendees for your own events.'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    attendee_id = request.data.get('attendee_id')
    if not attendee_id:
        return Response(
            {'error': 'attendee_id is required.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    attendee = get_object_or_404(EventAttendee, id=attendee_id, event=event)
    
    if attendee.status != 'going':
        return Response(
            {'error': 'Attendee must have status "going" to check in.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    attendee.status = 'checked_in'
    attendee.checked_in_at = timezone.now()
    attendee.save()
    
    return Response({
        'message': 'Attendee checked in successfully.',
        'data': EventAttendeeSerializer(attendee).data
    })


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def my_events_view(request):
    """Get all events for the current user (hosted, attending, invited)."""
    user = request.user
    
    hosted_events = Event.objects.filter(host=user, is_active=True)
    attending_events = Event.objects.filter(
        attendees__user=user,
        is_active=True
    ).distinct()
    invited_events = Event.objects.filter(
        invites__invited_user=user,
        invites__status='pending',
        is_active=True
    ).distinct()
    
    hosted_serializer = EventListSerializer(hosted_events, many=True)
    attending_serializer = EventListSerializer(attending_events, many=True)
    invited_serializer = EventListSerializer(invited_events, many=True)
    
    return Response({
        'hosted': hosted_serializer.data,
        'attending': attending_serializer.data,
        'invited': invited_serializer.data,
    })

