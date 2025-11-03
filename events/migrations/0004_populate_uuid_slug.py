# Generated migration to populate UUID and slug fields
import uuid
from django.db import migrations
from django.utils.text import slugify


def populate_event_uuids_and_slugs(apps, schema_editor):
    """Populate UUID and slug fields for existing Event records"""
    Event = apps.get_model('events', 'Event')
    
    for event in Event.objects.all():
        # Generate UUID if not exists
        if not event.uuid:
            event.uuid = uuid.uuid4()
        
        # Generate slug if not exists
        if not event.slug:
            from django.utils.text import slugify
            base_slug = slugify(event.title)
            slug = base_slug
            count = 1
            # Ensure unique slug
            while Event.objects.filter(slug=slug).exclude(pk=event.pk).exists():
                slug = f"{base_slug}-{count}"
                count += 1
            event.slug = slug
        
        # Only update if changes were made
        if event.uuid or event.slug:
            # Save with update_fields to avoid triggering other signals
            Event.objects.filter(pk=event.pk).update(
                uuid=event.uuid,
                slug=event.slug
            )


def reverse_populate_uuid_slug(apps, schema_editor):
    """Reverse operation - no need to do anything"""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0003_event_metadata_event_slug_event_uuid'),
    ]

    operations = [
        migrations.RunPython(
            populate_event_uuids_and_slugs,
            reverse_populate_uuid_slug
        ),
    ]
