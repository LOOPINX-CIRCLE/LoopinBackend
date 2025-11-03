# Generated migration to populate UUID and slug fields
import uuid
from django.db import migrations
from django.utils.text import slugify


def populate_userprofile_uuids(apps, schema_editor):
    """Populate UUID field for existing UserProfile records"""
    UserProfile = apps.get_model('users', 'UserProfile')
    
    for profile in UserProfile.objects.all():
        if not profile.uuid:
            profile.uuid = uuid.uuid4()
            # Save with update_fields to avoid triggering other signals
            UserProfile.objects.filter(pk=profile.pk).update(uuid=profile.uuid)


def populate_eventinterest_slugs(apps, schema_editor):
    """Populate slug field for existing EventInterest records"""
    EventInterest = apps.get_model('users', 'EventInterest')
    
    for interest in EventInterest.objects.all():
        if not interest.slug:
            from django.utils.text import slugify
            base_slug = slugify(interest.name)
            slug = base_slug
            count = 1
            # Ensure unique slug
            while EventInterest.objects.filter(slug=slug).exclude(pk=interest.pk).exists():
                slug = f"{base_slug}-{count}"
                count += 1
            interest.slug = slug
            # Save with update_fields to avoid triggering other signals
            EventInterest.objects.filter(pk=interest.pk).update(slug=interest.slug)


def reverse_populate_uuid_slug(apps, schema_editor):
    """Reverse operation - no need to do anything"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0009_eventinterest_slug_userprofile_metadata_and_more'),
    ]

    operations = [
        migrations.RunPython(
            populate_userprofile_uuids,
            reverse_populate_uuid_slug
        ),
        migrations.RunPython(
            populate_eventinterest_slugs,
            reverse_populate_uuid_slug
        ),
    ]
