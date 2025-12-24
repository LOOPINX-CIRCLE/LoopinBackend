# Combined migration: Fix orphaned records AND change FK in one migration
# This prevents Django from seeing multiple leaf nodes

from django.db import migrations, models, transaction
import django.db.models.deletion


def create_missing_user_profiles(apps, schema_editor):
    """
    Create UserProfile records for any Users that don't have them.
    This ensures all AttendanceRecord.user references will be valid after FK change.
    """
    # Use historical models from apps registry (not actual model classes)
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('users', 'UserProfile')
    AttendanceRecord = apps.get_model('attendances', 'AttendanceRecord')
    
    # Find all Users referenced by AttendanceRecords
    attendance_user_ids = list(
        AttendanceRecord.objects.values_list('user_id', flat=True).distinct()
    )
    
    if not attendance_user_ids:
        print("ℹ️  No AttendanceRecords found, skipping UserProfile creation")
        return
    
    print(f"🔍 Found {len(attendance_user_ids)} unique Users referenced by AttendanceRecords")
    
    # Get all users referenced by AttendanceRecords
    all_users = User.objects.filter(id__in=attendance_user_ids)
    missing_user_ids = []
    
    created_count = 0
    with transaction.atomic():
        for user in all_users:
            # Check if UserProfile exists for this user
            if not UserProfile.objects.filter(user_id=user.id).exists():
                missing_user_ids.append(user.id)
                # Create a minimal UserProfile for this user
                try:
                    # Construct user's name from first_name, last_name, or username
                    # Historical models don't have get_full_name() method
                    if user.first_name or user.last_name:
                        user_name = f"{user.first_name} {user.last_name}".strip()
                    else:
                        user_name = user.username or f'User {user.id}'
                    
                    phone_number = user.username if user.username and user.username.startswith('+') else ''
                    
                    UserProfile.objects.create(
                        user=user,
                        name=user_name,
                        phone_number=phone_number,
                        is_active=user.is_active,
                    )
                    created_count += 1
                except Exception as e:
                    print(f"❌ Failed to create UserProfile for user {user.id}: {e}")
                    raise
    
    if created_count > 0:
        print(f"✅ Created {created_count} UserProfile records for users: {missing_user_ids}")
    else:
        print("✅ All Users referenced by AttendanceRecords already have UserProfiles")
    
    # Verify all users now have profiles
    users_still_missing = []
    for user_id in attendance_user_ids:
        if not UserProfile.objects.filter(user_id=user_id).exists():
            users_still_missing.append(user_id)
    
    if users_still_missing:
        raise ValueError(
            f"❌ Migration failed: Users {users_still_missing} still don't have UserProfiles. "
            f"Cannot proceed with FK change."
        )
    else:
        print("✅ Verification passed: All Users referenced by AttendanceRecords have UserProfiles")


def reverse_create_missing_user_profiles(apps, schema_editor):
    """
    Reverse migration - no action needed as we're not deleting anything
    """
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('attendances', '0001_initial'),
        ('users', '0003_userprofile_waitlist_promote_at_and_more'),
    ]

    operations = [
        # Step 1: Create missing UserProfiles (data migration)
        migrations.RunPython(
            create_missing_user_profiles,
            reverse_create_missing_user_profiles
        ),
        # Step 2: Change FK from User to UserProfile (schema migration)
        migrations.AlterField(
            model_name='attendancerecord',
            name='user',
            field=models.ForeignKey(
                help_text='User profile attending the event',
                on_delete=django.db.models.deletion.CASCADE,
                related_name='attendance_records',
                to='users.userprofile'
            ),
        ),
    ]

