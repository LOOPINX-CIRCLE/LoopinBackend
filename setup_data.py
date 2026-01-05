#!/usr/bin/env python
"""
Setup script for initial data loading
"""
import os
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loopin_backend.settings.dev')
django.setup()

from django.contrib.auth.models import User
from users.models import EventInterest

def create_superuser():
    """Create superuser if it doesn't exist"""
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@loopin.com', 'admin123')
        print("✅ Superuser 'admin' created with password 'admin123'")
    else:
        print("ℹ️  Superuser 'admin' already exists")

def load_event_interests():
    """Load default event interests"""
    interests = [
        "Music",
        "Sports",
        "Food & Drink",
        "Technology",
        "Art & Culture",
        "Travel",
        "Fitness",
        "Business",
        "Education",
        "Entertainment",
        "Gaming",
        "Photography",
        "Dance",
        "Comedy",
        "Fashion",
        "Health & Wellness",
        "Volunteering",
        "Outdoor",
        "Networking",
        "Workshop"
    ]

    created_count = 0
    for interest_name in interests:
        interest, created = EventInterest.objects.get_or_create(
            name=interest_name
        )
        if created:
            created_count += 1

    print(f"✅ Loaded {created_count} new event interests (total: {EventInterest.objects.count()})")

if __name__ == "__main__":
    print("🚀 Starting data setup...")
    create_superuser()
    load_event_interests()
    print("✅ Data setup completed!")
