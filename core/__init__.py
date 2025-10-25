# Core Package

This package contains shared utilities, base models, and common functionality used across the Loopin Backend application.

## 📁 Package Structure

```
core/
├── __init__.py              # Package initialization
├── base_models.py           # Abstract base models
├── choices.py              # Application constants and choices
├── db_utils.py             # Database utilities
├── exceptions.py            # Custom exceptions
├── permissions.py           # Permission utilities
├── utils/                   # Utility modules
│   ├── __init__.py
│   ├── logger.py           # Logging utilities
│   ├── cache.py            # Caching utilities
│   ├── validators.py        # Data validators
│   ├── decorators.py        # Custom decorators
│   └── helpers.py           # Helper functions
├── middleware/              # Custom middleware
│   ├── __init__.py
│   ├── analytics.py        # Analytics middleware
│   └── security.py         # Security middleware
└── signals/                 # Django signals
    ├── __init__.py
    ├── user_signals.py     # User-related signals
    └── audit_signals.py    # Audit-related signals
```

## 🔧 Core Components

### Base Models (`base_models.py`)
- **TimeStampedModel**: Abstract model with created_at and updated_at
- **SoftDeleteModel**: Abstract model with soft delete functionality
- **UUIDModel**: Abstract model with UUID primary key

### Choices (`choices.py`)
- **Gender Choices**: User gender options
- **Event Status Choices**: Event status options
- **Payment Status Choices**: Payment status options
- **Attendance Status Choices**: Attendance status options
- **Notification Types**: Notification type options

### Database Utils (`db_utils.py`)
- **Connection Management**: Database connection utilities
- **Query Optimization**: Database query helpers
- **Migration Utilities**: Database migration helpers

### Utilities (`utils/`)
- **Logger**: Structured logging utilities
- **Cache**: Redis caching utilities
- **Validators**: Data validation helpers
- **Decorators**: Custom decorators for common patterns
- **Helpers**: General-purpose helper functions

### Middleware (`middleware/`)
- **Analytics**: PostHog analytics middleware
- **Security**: Security headers and validation middleware

### Signals (`signals/`)
- **User Signals**: User-related Django signals
- **Audit Signals**: Audit logging signals

## 📚 Usage

### Importing Core Components

```python
# Base models
from core.base_models import TimeStampedModel, SoftDeleteModel

# Choices
from core.choices import GENDER_CHOICES, EVENT_STATUS_CHOICES

# Database utilities
from core.db_utils import get_db_connection

# Utilities
from core.utils.logger import get_logger
from core.utils.cache import cache_result
from core.utils.validators import validate_phone_number

# Middleware
from core.middleware.analytics import AnalyticsMiddleware

# Signals
from core.signals.user_signals import user_created_signal
```

### Using Base Models

```python
from django.db import models
from core.base_models import TimeStampedModel

class MyModel(TimeStampedModel):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name = "My Model"
        verbose_name_plural = "My Models"
```

### Using Choices

```python
from django.db import models
from core.choices import GENDER_CHOICES

class UserProfile(models.Model):
    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
```

## 🔧 Configuration

### Settings Integration

```python
# settings/base.py
INSTALLED_APPS = [
    'core',  # Add core package
    # ... other apps
]

MIDDLEWARE = [
    'core.middleware.analytics.AnalyticsMiddleware',
    'core.middleware.security.SecurityMiddleware',
    # ... other middleware
]```

### Logging Configuration

```python
# settings/base.py
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': 'logs/django.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'core': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 🧪 Testing

### Testing Core Components

```python
# tests/test_core.py
from django.test import TestCase
from core.base_models import TimeStampedModel
from core.utils.validators import validate_phone_number

class CoreTestCase(TestCase):
    def test_phone_validation(self):
        self.assertTrue(validate_phone_number("+1234567890"))
        self.assertFalse(validate_phone_number("invalid"))
```

## 📈 Performance Considerations

### Caching Strategy
- **Model Caching**: Cache frequently accessed models
- **Query Caching**: Cache expensive database queries
- **Session Caching**: Cache user session data

### Database Optimization
- **Connection Pooling**: Efficient database connections
- **Query Optimization**: Optimized database queries
- **Indexing**: Proper database indexing

## 🔒 Security Considerations

### Data Protection
- **Input Validation**: Validate all input data
- **SQL Injection**: Use Django ORM properly
- **XSS Protection**: Sanitize user input

### Access Control
- **Permission System**: Use Django permissions
- **Authentication**: Secure authentication flow
- **Authorization**: Proper access control

---

**The core package provides the foundation for consistent, maintainable, and scalable Django applications.** 🏗️

