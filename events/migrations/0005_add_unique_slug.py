# Add unique constraint to slug after data is populated
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('events', '0004_populate_uuid_slug'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='slug',
            field=models.SlugField(blank=True, help_text='URL-friendly slug', max_length=200, unique=True),
        ),
    ]
