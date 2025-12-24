# Data migration to create default platform fee configuration

from django.db import migrations
from decimal import Decimal


def create_default_platform_fee_config(apps, schema_editor):
    """Create default platform fee configuration with 10% fee"""
    PlatformFeeConfig = apps.get_model('core', 'PlatformFeeConfig')
    
    # Only create if it doesn't exist
    if not PlatformFeeConfig.objects.filter(id=1).exists():
        PlatformFeeConfig.objects.create(
            id=1,
            fee_percentage=Decimal('10.00'),
            is_active=True,
            description="Default platform fee configuration (10%)"
        )
        print("✅ Created default PlatformFeeConfig with 10% fee")
    else:
        print("ℹ️  PlatformFeeConfig already exists, skipping creation")


def reverse_create_default_platform_fee_config(apps, schema_editor):
    """Remove default platform fee configuration"""
    PlatformFeeConfig = apps.get_model('core', 'PlatformFeeConfig')
    PlatformFeeConfig.objects.filter(id=1).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(
            create_default_platform_fee_config,
            reverse_create_default_platform_fee_config
        ),
    ]
