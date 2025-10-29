# Generated migration for changing email to phone_number in HostLead model

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0007_hostlead'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='hostlead',
            name='email',
        ),
        migrations.AddField(
            model_name='hostlead',
            name='phone_number',
            field=models.CharField(help_text='Phone number of the potential host', max_length=20, unique=True),
            preserve_default=False,
        ),
    ]

