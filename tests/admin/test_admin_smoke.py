"""
CTO-Level Admin Smoke Tests

This test suite ensures all admin pages load without errors.
This catches systemic issues early, before they reach production.

Rules enforced:
1. All admin pages must load (status 200)
2. Add pages must not crash on empty object
3. No FieldErrors from missing readonly_fields
4. No TypeError from NULL-unsafe properties
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.apps import apps
from django.contrib import admin

User = get_user_model()


class AdminSmokeTests(TestCase):
    """Smoke tests for all admin interfaces"""
    
    def setUp(self):
        """Create admin user and client"""
        self.user = User.objects.create_user(
            username='admin',
            email='admin@test.com',
            password='testpass123',
            is_staff=True,
            is_superuser=True
        )
        self.client = Client()
        self.client.force_login(self.user)
    
    def test_admin_index_loads(self):
        """Test that admin index page loads"""
        url = reverse('admin:index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200, f"Admin index failed: {response.status_code}")
    
    def test_all_admin_changelist_pages_load(self):
        """Test all changelist (list) pages load without errors"""
        admin_models = [
            # Users
            ('users', 'userprofile'),
            ('users', 'eventinterest'),
            ('users', 'phoneotp'),
            ('users', 'hostlead'),
            # Events
            ('events', 'venue'),
            ('events', 'event'),
            ('events', 'eventrequest'),
            # Payments
            ('payments', 'paymentorder'),
            # Notifications
            ('notifications', 'notification'),
            ('notifications', 'campaign'),
            # Core
            ('core', 'platformfeeconfig'),
        ]
        
        failed = []
        for app_label, model_name in admin_models:
            try:
                url = reverse(f'admin:{app_label}_{model_name}_changelist')
                response = self.client.get(url)
                if response.status_code != 200:
                    failed.append(f"{app_label}.{model_name}: {response.status_code}")
            except Exception as e:
                failed.append(f"{app_label}.{model_name}: {str(e)}")
        
        self.assertEqual(len(failed), 0, f"Failed changelist pages:\n" + "\n".join(failed))
    
    def test_all_admin_add_pages_load(self):
        """Test all add pages load without errors (NULL-safe check)"""
        admin_models = [
            # Users
            ('users', 'eventinterest'),
            # Events
            ('events', 'venue'),
            ('events', 'event'),
            # Payments
            ('payments', 'paymentorder'),
            # Notifications
            ('notifications', 'campaign'),
        ]
        
        failed = []
        for app_label, model_name in admin_models:
            try:
                url = reverse(f'admin:{app_label}_{model_name}_add')
                response = self.client.get(url)
                if response.status_code != 200:
                    failed.append(f"{app_label}.{model_name}: {response.status_code}")
            except Exception as e:
                failed.append(f"{app_label}.{model_name}: {str(e)}")
        
        self.assertEqual(len(failed), 0, f"Failed add pages:\n" + "\n".join(failed))
    
    def test_admin_readonly_fields_exist(self):
        """Test that all readonly_fields methods exist and are callable"""
        errors = []
        for model in apps.get_models():
            if model in admin.site._registry:
                model_admin = admin.site._registry[model]
                readonly_fields = getattr(model_admin, 'readonly_fields', ())
                
                for field_name in readonly_fields:
                    # Skip DB fields
                    try:
                        model._meta.get_field(field_name)
                        continue  # It's a DB field, skip
                    except:
                        pass  # Not a DB field, check if it's a method or property
                    
                    # Check if it's an admin method
                    if hasattr(model_admin, field_name):
                        if callable(getattr(model_admin, field_name, None)):
                            continue  # Valid admin method
                    
                    # Check if it's a model property (descriptor)
                    if hasattr(model, field_name):
                        attr = getattr(model, field_name, None)
                        if hasattr(attr, '__get__'):  # It's a descriptor (property)
                            continue  # Valid model property
                    
                    errors.append(f"{model._meta.label}.{field_name}: not a DB field, admin method, or model property")
        
        self.assertEqual(len(errors), 0, f"Readonly field errors:\n" + "\n".join(errors))
    
    def test_admin_fieldsets_only_use_valid_fields(self):
        """Test that all fieldsets only reference valid fields"""
        errors = []
        for model in apps.get_models():
            if model in admin.site._registry:
                model_admin = admin.site._registry[model]
                fieldsets = getattr(model_admin, 'fieldsets', None)
                readonly_fields = set(getattr(model_admin, 'readonly_fields', ()))
                
                if not fieldsets:
                    continue
                
                for fieldset_name, fieldset_options in fieldsets:
                    fields = fieldset_options.get('fields', ())
                    for field_tuple in fields:
                        if isinstance(field_tuple, str):
                            field_names = [field_tuple]
                        else:
                            field_names = list(field_tuple)
                        
                        for field_name in field_names:
                            # Check if it's a DB field
                            try:
                                model._meta.get_field(field_name)
                                continue  # Valid DB field
                            except:
                                pass
                            
                            # Check if it's a readonly method or property
                            if field_name in readonly_fields:
                                # Check if it's an admin method
                                if hasattr(model_admin, field_name):
                                    if callable(getattr(model_admin, field_name, None)):
                                        continue  # Valid admin method
                                # Check if it's a model property
                                if hasattr(model, field_name):
                                    attr = getattr(model, field_name, None)
                                    if hasattr(attr, '__get__'):  # It's a descriptor (property)
                                        continue  # Valid model property
                                # Check if it's a form field (for custom forms)
                                if hasattr(model_admin, 'form') and hasattr(model_admin.form, 'base_fields'):
                                    if field_name in model_admin.form.base_fields:
                                        continue  # Valid form field
                                
                                errors.append(f"{model._meta.label}.{field_name}: in readonly_fields but not found as method, property, or form field")
                            else:
                                # Check if it's a form field (for custom forms)
                                if hasattr(model_admin, 'form') and hasattr(model_admin.form, 'base_fields'):
                                    if field_name in model_admin.form.base_fields:
                                        continue  # Valid form field
                                
                                errors.append(f"{model._meta.label}.{field_name}: not a DB field, readonly method, property, or form field")
        
        self.assertEqual(len(errors), 0, f"Fieldset field errors:\n" + "\n".join(errors))
