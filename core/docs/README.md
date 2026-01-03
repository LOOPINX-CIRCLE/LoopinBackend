# Core Package - Technical Documentation

## Executive Summary

The `core` package serves as the foundational infrastructure layer for the Loopin Backend system. It provides shared abstractions, cross-cutting concerns, and system-wide configuration that enable consistency, maintainability, and operational excellence across all domain applications.

**Architectural Role**: Foundation layer providing horizontal capabilities to vertical domain apps.

---

## Package Architecture

### Design Philosophy

The core package implements several architectural patterns:

1. **DRY (Don't Repeat Yourself)**: Centralizes common functionality to eliminate duplication
2. **Separation of Concerns**: Isolates infrastructure concerns from business logic
3. **Singleton Pattern**: System-wide configuration (PlatformFeeConfig) uses singleton enforcement
4. **Abstract Base Classes**: Provides reusable model foundations (TimeStampedModel, SoftDeleteModel)
5. **Dependency Inversion**: Domain apps depend on core abstractions, not implementations

### Package Structure

```
core/
├── models.py              # System-wide models (PlatformFeeConfig)
├── base_models.py         # Abstract base model classes
├── admin.py               # Django admin configurations
├── exceptions.py          # Custom exception hierarchy
├── permissions.py         # Authorization and permission utilities
├── choices.py             # Application-wide constants and enums
├── db_utils.py            # Database connection utilities
├── middleware/            # Request/response middleware
│   ├── auth_middleware.py
│   ├── exception_handler.py
│   └── request_logging.py
├── utils/                 # Utility functions
│   ├── cache.py
│   └── logger.py
└── signals/               # Django signals
    ├── notification_events.py
    └── user_activity.py
```

---

## Core Components

### 1. Base Models (`base_models.py`)

**Purpose**: Abstract base classes that provide common model functionality.

#### `TimeStampedModel`
- **Functionality**: Automatic `created_at` and `updated_at` timestamp fields
- **Performance**: Both fields indexed for query optimization
- **Usage**: Inherited by all domain models requiring audit trails
- **Implementation**: Uses Django's `auto_now_add` and `auto_now` with `db_index=True`

#### `SoftDeleteModel`
- **Functionality**: Non-destructive deletion via `is_deleted` flag
- **Rationale**: Preserves data integrity, enables recovery, supports compliance
- **Usage**: Models requiring soft delete capability
- **Implementation**: Overrides `delete()` method to set flag instead of hard deletion

#### `BaseModel`
- **Functionality**: Combines `TimeStampedModel` and `SoftDeleteModel`
- **Usage**: Default base class for most domain models
- **Benefits**: Single inheritance point for common functionality

**Design Decision**: Abstract base classes prevent code duplication and ensure consistent behavior across 15+ domain models.

---

### 2. Platform Fee Configuration (`models.py`)

**Purpose**: Dynamic, admin-configurable platform fee system replacing hardcoded 10% fee.

#### Architecture

**Singleton Pattern Implementation**:
- Single instance enforced via `id=1` primary key
- Admin interface prevents multiple configurations
- Database-level constraint ensures uniqueness

**Caching Strategy**:
- Three-tier cache: `platform_fee_config`, `platform_fee_percentage`, `platform_fee_decimal`
- 1-hour TTL (3600 seconds) for performance
- Automatic cache invalidation on configuration updates
- Cache-aside pattern with fallback to database

**Business Logic**:
```python
# Fee calculation flow:
base_fare = Decimal('100.00')
fee_percentage = PlatformFeeConfig.get_fee_percentage()  # 10.00
fee_decimal = PlatformFeeConfig.get_fee_decimal()        # 0.10

platform_fee = base_fare * fee_decimal * quantity        # ₹10.00 × 5 = ₹50.00
final_price = base_fare * (1 + fee_decimal)              # ₹110.00
host_earnings = base_fare * quantity                     # ₹500.00 (no deduction)
```

**Validation**:
- Range validation: 0.00% to 100.00%
- Decimal precision: 2 decimal places (0.01% granularity)
- Django model validation via `clean()` method

**API Design**:
- Class methods for stateless access: `get_fee_percentage()`, `get_fee_decimal()`
- Calculation methods: `calculate_platform_fee()`, `calculate_final_price()`
- Automatic rounding: `ROUND_HALF_UP` for financial accuracy

**Performance Considerations**:
- Database query: 1 per hour (cached)
- Cache hit rate: ~99.9% for high-traffic scenarios
- Zero database queries for fee calculations after cache warm-up

---

### 3. Exception Hierarchy (`exceptions.py`)

**Purpose**: Structured exception system with HTTP status code mapping.

#### Exception Types

| Exception | HTTP Status | Use Case |
|-----------|-------------|----------|
| `ValidationError` | 400 | Input validation failures |
| `AuthenticationError` | 401 | Authentication failures |
| `AuthorizationError` | 403 | Permission denied |
| `NotFoundError` | 404 | Resource not found |
| `ConflictError` | 409 | Resource conflicts (duplicates) |
| `RateLimitError` | 429 | Rate limiting violations |
| `ExternalServiceError` | 502 | Third-party service failures |
| `DatabaseError` | 503 | Database connectivity issues |
| `BusinessLogicError` | 400 | Domain rule violations |

**Design Benefits**:
- Consistent error responses across FastAPI and Django
- Automatic HTTP status mapping in middleware
- Structured error details for client debugging
- Error correlation via `code` field

**Usage Pattern**:
```python
from core.exceptions import NotFoundError, AuthorizationError

if not event:
    raise NotFoundError("Event not found", code="EVENT_NOT_FOUND")
    
if not user.is_staff and event.host != user.profile:
    raise AuthorizationError("Not authorized to modify event", code="NOT_EVENT_HOST")
```

---

### 4. Permission System (`permissions.py`)

**Purpose**: Centralized authorization logic with role-based and object-level permissions.

#### Components

**`PermissionChecker`**:
- Static utility methods for permission checks
- Object-level ownership validation
- Raises `AuthorizationError` on denial

**`RoleBasedPermission`**:
- Predefined role hierarchy: admin, moderator, user, guest
- Permission inheritance model
- Extensible role definitions

**Usage Patterns**:
```python
# Check permission
if PermissionChecker.check_user_permission(user, 'events.change_event', event):
    # Allow modification

# Require permission (raises on failure)
PermissionChecker.require_permission(user, 'events.delete_event', event)

# Check ownership
if PermissionChecker.check_ownership(user, event, owner_field='host'):
    # User owns the event
```

**Performance**: Permission checks use Django's built-in permission system with database-level caching.

---

### 5. Database Utilities (`db_utils.py`)

**Purpose**: Handle cloud deployment database connection issues, specifically IPv4/IPv6 resolution.

#### Problem Statement

Cloud platforms (Render, Heroku) may have IPv6 outbound restrictions that prevent connections to services like Supabase when DNS resolution returns IPv6 addresses.

#### Solution

**`force_ipv4_database_url()`**:
- Resolves hostnames to IPv4 addresses explicitly
- **Critical Exception**: Supabase pooler URLs are NOT resolved (preserves SSL/TLS verification)
- Graceful fallback to original URL on resolution failure
- Comprehensive logging for debugging

**`get_database_config()`**:
- Environment-aware configuration
- Automatic IPv4 enforcement on Render platform
- Manual override via `FORCE_IPV4_DB` environment variable
- Returns Django-compatible database configuration dict

**Design Decision**: Platform detection and conditional IPv4 enforcement prevents connection failures while maintaining compatibility with pooler services.

---

### 6. Constants and Choices (`choices.py`)

**Purpose**: Centralized application constants and choice field definitions.

#### Organization

- **User Choices**: Gender, status, verification states
- **Event Choices**: Status, ticket types, invite types, gender restrictions
- **Payment Choices**: Status, providers, currencies
- **OTP Configuration**: Validity, attempts, length
- **Validation Constants**: Min/max lengths, file size limits, allowed formats

**Benefits**:
- Single source of truth for constants
- Type safety via constants (prevents magic numbers/strings)
- Easy refactoring (change once, applies everywhere)
- Documentation via constant names

**Usage**:
```python
from core.choices import OTP_LENGTH, MAX_PROFILE_PICTURES, EVENT_STATUS_CHOICES

otp = generate_otp(length=OTP_LENGTH)  # Uses 4
if len(pictures) > MAX_PROFILE_PICTURES:  # Uses 6
    raise ValidationError(...)
```

---

### 7. Logging Infrastructure (`utils/logger.py`)

**Purpose**: Structured logging with consistent formatting and context.

#### Components

**`get_logger()`**:
- Standardized logger creation
- Environment-aware log levels
- Module-specific loggers for filtering

**`StructuredLogger`**:
- Context-aware logging with extra fields
- Consistent log format across application
- Support for correlation IDs and request tracking

**Specialized Loggers**:
- `log_api_request()`: API endpoint logging with user context
- `log_database_query()`: Query performance tracking
- `log_external_service_call()`: Third-party service monitoring

**Log Levels**:
- DEBUG: Development diagnostics
- INFO: Normal operations, request tracking
- WARNING: Recoverable issues
- ERROR: Failures requiring attention
- CRITICAL: System-level failures

---

### 8. Caching Utilities (`utils/cache.py`)

**Purpose**: Abstraction layer for Django cache framework with organized cache key management.

#### Features

- **Cache Key Generation**: MD5-based key hashing for consistent keys
- **Model Instance Caching**: Automatic caching of Django model instances
- **QuerySet Caching**: Cache entire queryset results
- **Session Caching**: User session data caching
- **API Response Caching**: Endpoint-level response caching
- **Cache Manager**: Object-oriented cache operations with prefix support

**Usage Pattern**:
```python
from core.utils.cache import CacheManager

cache = CacheManager(prefix='platform_fee')
fee = cache.get_or_set('percentage', default=10.0, timeout=3600)
```

---

### 9. Middleware (`middleware/`)

**Purpose**: Request/response processing pipeline components.

#### `ExceptionHandlerMiddleware`
- **Functionality**: Centralized exception handling
- **Mapping**: Custom exceptions → HTTP status codes
- **Logging**: Structured error logging with request context
- **Response Format**: Consistent JSON error responses

#### `AuthMiddleware`
- **Functionality**: Authentication and authorization checks
- **Integration**: Works with JWT tokens and Django sessions
- **Performance**: Early return on authentication failures

#### `RequestLoggingMiddleware`
- **Functionality**: Request/response logging
- **Context**: Correlation IDs, user IDs, request metadata
- **Performance**: Async logging to prevent request blocking

---

### 10. Signals (`signals/`)

**Purpose**: Cross-app event communication via Django signals.

#### Signal Types

- **User Activity Signals**: Track user actions for analytics
- **Notification Events**: Trigger notifications on business events

**Design Pattern**: Signals enable loose coupling between apps while maintaining event-driven architecture.

---

## Technical Implementation Details

### Singleton Pattern: PlatformFeeConfig

**Enforcement Mechanisms**:
1. **Primary Key Constraint**: `id=1` enforced at model level
2. **Admin Interface**: `has_add_permission()` prevents multiple instances
3. **Save Override**: `save()` method always sets `id=1`
4. **Delete Protection**: `has_delete_permission()` returns False

**Cache Invalidation Strategy**:
```python
def save(self, *args, **kwargs):
    # Clear all related cache keys
    cache.delete('platform_fee_percentage')
    cache.delete('platform_fee_decimal')
    cache.delete('platform_fee_config')
    super().save(*args, **kwargs)
```

**Default Creation**:
- `get_current_config()` creates default 10% configuration if missing
- Prevents runtime errors from missing configuration
- Migration ensures default exists in production

---

### Database Connection Management

**IPv4 Resolution Logic**:
```python
# Supabase pooler detection
if 'pooler.supabase.com' in hostname:
    return original_url  # Don't resolve - breaks SSL/TLS

# IPv4 resolution for direct connections
ipv4_address = socket.getaddrinfo(hostname, None, socket.AF_INET, socket.SOCK_STREAM)[0][4][0]
```

**Rationale**: Supabase connection poolers require original hostname for certificate validation. Direct database connections benefit from IPv4 resolution on platforms with IPv6 restrictions.

---

### Exception Handling Flow

```
Request → Middleware → View/Endpoint
                          ↓
                    Business Logic
                          ↓
                    Exception Raised
                          ↓
                    ExceptionHandlerMiddleware
                          ↓
                    HTTP Status Mapping
                          ↓
                    Structured JSON Response
```

**Error Response Format**:
```json
{
    "success": false,
    "error": "Human-readable error message",
    "error_code": "MACHINE_READABLE_CODE",
    "details": {
        "field": "additional context"
    }
}
```

---

## Performance Optimizations

### Caching Strategy

1. **Platform Fee Config**: 1-hour cache (99.9% hit rate expected)
2. **Model Instances**: 5-minute default TTL
3. **QuerySets**: 5-minute default TTL
4. **API Responses**: Endpoint-specific TTLs

### Database Query Optimization

- **Indexes**: All timestamp fields indexed (`created_at`, `updated_at`)
- **Soft Delete Index**: `is_deleted` field indexed for efficient filtering
- **Select Related**: Admin querysets use `select_related()` for FK optimization

### Memory Management

- **Cache TTL**: Prevents unbounded cache growth
- **Cache Key Hashing**: Reduces memory footprint
- **Lazy Loading**: Constants loaded on demand

---

## Security Considerations

### Input Validation

- **Platform Fee**: Range validation (0-100%) prevents invalid configurations
- **Model Validation**: Django's `full_clean()` called on save
- **Type Safety**: Decimal fields prevent floating-point precision issues

### Authorization

- **Permission Checks**: Centralized in `PermissionChecker`
- **Object-Level Security**: Ownership validation before operations
- **Role-Based Access**: Hierarchical permission model

### Data Protection

- **Soft Deletes**: Prevents accidental data loss
- **Audit Trail**: Timestamps on all models via `TimeStampedModel`
- **Configuration Tracking**: `updated_by` field tracks who changed platform fee

---

## Usage Guidelines

### When to Use Core Components

**Use `TimeStampedModel`**:
- All domain models requiring audit trails
- Models needing `created_at`/`updated_at` for analytics

**Use `SoftDeleteModel`**:
- Models requiring data retention (compliance)
- Models with recovery requirements
- Models with referential integrity concerns

**Use `PlatformFeeConfig`**:
- All financial calculations (payouts, analytics)
- Never hardcode fee percentages
- Always use class methods, never direct model access

**Use Custom Exceptions**:
- All API endpoints (FastAPI)
- Business logic validation
- External service integration errors

**Use Permission Utilities**:
- All protected endpoints
- Object-level authorization checks
- Role-based access control

---

## Testing Strategy

### Unit Tests

- **Base Models**: Verify timestamp and soft delete behavior
- **PlatformFeeConfig**: Test singleton enforcement, caching, calculations
- **Exceptions**: Verify HTTP status code mapping
- **Permissions**: Test role-based and object-level checks

### Integration Tests

- **Cache Invalidation**: Verify cache clears on config updates
- **Database Utils**: Test IPv4 resolution logic
- **Middleware**: Verify exception handling flow

---

## Operational Concerns

### Monitoring

- **Platform Fee Changes**: Log all configuration updates with `updated_by`
- **Cache Performance**: Monitor cache hit rates
- **Exception Rates**: Track exception types and frequencies
- **Database Connections**: Monitor IPv4 resolution success rates

### Deployment

- **Migrations**: Core migrations must run before domain app migrations
- **Default Configuration**: Ensure `PlatformFeeConfig` default created on deployment
- **Cache Warm-up**: Consider pre-warming platform fee cache on startup

### Troubleshooting

**Platform Fee Not Updating**:
1. Check cache TTL (1 hour default)
2. Verify admin save cleared cache keys
3. Check database for actual configuration value

**Database Connection Issues**:
1. Verify `FORCE_IPV4_DB` environment variable
2. Check Supabase pooler URL format
3. Review connection logs for IPv4 resolution

**Permission Denied Errors**:
1. Verify user roles in database
2. Check `PermissionChecker` logic
3. Review object ownership relationships

---

## Future Considerations

### Scalability

- **Cache Clustering**: Redis cluster for multi-instance deployments
- **Configuration Versioning**: Track platform fee change history
- **A/B Testing**: Support multiple fee configurations for experimentation

### Extensibility

- **Plugin Architecture**: Allow domain apps to extend base models
- **Custom Middleware**: Framework for app-specific middleware
- **Signal Registry**: Centralized signal management

---

## API Reference

### PlatformFeeConfig

```python
# Get current configuration
config = PlatformFeeConfig.get_current_config()

# Get fee percentage (0-100)
percentage = PlatformFeeConfig.get_fee_percentage()  # Decimal('10.00')

# Get fee decimal (0.00-1.00)
decimal = PlatformFeeConfig.get_fee_decimal()  # Decimal('0.10')

# Calculate platform fee
fee = PlatformFeeConfig.calculate_platform_fee(
    base_fare=Decimal('100.00'),
    quantity=5
)  # Decimal('50.00')

# Calculate final price
price = PlatformFeeConfig.calculate_final_price(
    base_fare=Decimal('100.00')
)  # Decimal('110.00')
```

### Exception Usage

```python
from core.exceptions import NotFoundError, AuthorizationError

# Raise with context
raise NotFoundError(
    "Event not found",
    code="EVENT_NOT_FOUND",
    details={"event_id": 123}
)
```

### Permission Checks

```python
from core.permissions import PermissionChecker

# Check permission
if PermissionChecker.check_user_permission(user, 'events.change_event'):
    # Proceed

# Require permission (raises on failure)
PermissionChecker.require_permission(user, 'events.delete_event', event)

# Check ownership
PermissionChecker.require_ownership(user, event, owner_field='host')
```

---

## Maintenance Notes

### Code Ownership

- **Core Package**: Maintained by platform/infrastructure team
- **Breaking Changes**: Require coordination with all domain apps
- **Deprecation Policy**: 2-version deprecation cycle for API changes

### Version Compatibility

- **Django**: 5.2.1+
- **Python**: 3.11+
- **Database**: PostgreSQL 15+ (Supabase)

---

**Last Updated**: 2025-12-22  
**Maintainer**: Platform Engineering Team  
**Status**: Production Ready

