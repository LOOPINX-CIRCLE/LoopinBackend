"""
Views for the Events app.
"""

from .event_views import (
    VenueListCreateView,
    VenueRetrieveUpdateDestroyView,
    EventListCreateView,
    EventRetrieveUpdateDestroyView,
    EventRequestListCreateView,
    EventRequestRetrieveUpdateDestroyView,
    EventInviteListCreateView,
    EventInviteRetrieveUpdateDestroyView,
    EventAttendeeListCreateView,
    EventAttendeeRetrieveUpdateDestroyView,
)

__all__ = [
    'VenueListCreateView',
    'VenueRetrieveUpdateDestroyView',
    'EventListCreateView',
    'EventRetrieveUpdateDestroyView',
    'EventRequestListCreateView',
    'EventRequestRetrieveUpdateDestroyView',
    'EventInviteListCreateView',
    'EventInviteRetrieveUpdateDestroyView',
    'EventAttendeeListCreateView',
    'EventAttendeeRetrieveUpdateDestroyView',
]

