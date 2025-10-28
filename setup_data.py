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
        {"name": "Music", "description": "Concerts, festivals, and musical events"},
        {"name": "Sports", "description": "Sports events, tournaments, and competitions"},
        {"name": "Food & Drink", "description": "Food festivals, wine tastings, and culinary events"},
        {"name": "Technology", "description": "Tech meetups, conferences, and workshops"},
        {"name": "Art & Culture", "description": "Art exhibitions, cultural events, and performances"},
        {"name": "Travel", "description": "Travel meetups, adventure trips, and exploration events"},
        {"name": "Fitness", "description": "Fitness classes, marathons, and wellness events"},
        {"name": "Business", "description": "Networking events, business conferences, and seminars"},
        {"name": "Education", "description": "Educational workshops, courses, and learning events"},
        {"name": "Entertainment", "description": "Movies, shows, and entertainment events"},
        {"name": "Gaming", "description": "Gaming tournaments, LAN parties, and gaming events"},
        {"name": "Photography", "description": "Photography workshops, photo walks, and exhibitions"},
        {"name": "Dance", "description": "Dance classes, performances, and dance events"},
        {"name": "Comedy", "description": "Comedy shows, stand-up performances, and humor events"},
        {"name": "Fashion", "description": "Fashion shows, styling events, and fashion meetups"},
        {"name": "Health & Wellness", "description": "Wellness retreats, meditation, and health events"},
        {"name": "Volunteering", "description": "Community service, charity events, and volunteer work"},
        {"name": "Outdoor", "description": "Hiking, camping, and outdoor adventure events"},
        {"name": "Networking", "description": "Professional networking and social meetups"},
        {"name": "Workshop", "description": "Hands-on workshops and skill-building events"}
    ]

    created_count = 0
    for interest_data in interests:
        interest, created = EventInterest.objects.get_or_create(
            name=interest_data["name"],
            defaults={"description": interest_data["description"]}
        )
        if created:
            created_count += 1

    print(f"✅ Loaded {created_count} new event interests (total: {EventInterest.objects.count()})")

if __name__ == "__main__":
    print("🚀 Starting data setup...")
    create_superuser()
    load_event_interests()
    print("✅ Data setup completed!")
