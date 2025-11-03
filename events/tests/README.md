# Events App Tests

This directory contains all tests for the Events application.

## Test Files

- `test_events.py` - Tests for event models, views, and serializers

## Running Tests

```bash
# Run all tests for the events app
python manage.py test events

# Run specific test class
python manage.py test events.tests.test_events.EventModelTest

# Run with verbose output
python manage.py test events --verbosity=2
```

## Test Coverage

The tests cover:
- Model creation and validation
- Serializer functionality
- API endpoint behavior
- Permission checks
- Business logic

