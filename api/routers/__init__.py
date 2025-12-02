"""
FastAPI routers package.
"""

from . import auth, users, hosts, events, events_attendance, payouts

__all__ = ['auth', 'users', 'hosts', 'events', 'events_attendance', 'payouts']
