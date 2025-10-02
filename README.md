# Loopin Backend

A comprehensive mobile backend built with Django + FastAPI, featuring JWT authentication, PostgreSQL database, and Docker containerization. This project combines the power of Django's ORM and admin interface with FastAPI's high-performance API endpoints in a clean, modular architecture.

## 🚀 Features

- **Django 5.2** for ORM, migrations, and admin interface
- **FastAPI** for high-performance API endpoints
- **JWT Authentication** with secure token-based auth
- **PostgreSQL** database with persistent storage
- **Docker & Docker Compose** for containerization
- **Swagger UI** for API documentation
- **CORS** support for mobile clients
- **Async/Await** support with proper Django ORM integration
- **Modular Architecture** with clean separation of concerns

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Mobile Apps   │────│   FastAPI API    │────│   PostgreSQL   │
│  (iOS/Android)  │    │   (/api/*)       │    │   Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                       ┌──────────────────┐
                       │   Django Admin   │
                       │   (/django/*)    │
                       └──────────────────┘
```

## 🛠️ Development Setup

### Prerequisites

- **Docker** and **Docker Compose** installed
- **Git** for version control
- Basic understanding of Django and FastAPI

### Step-by-Step Setup for New Developers

#### 1. Clone and Navigate to Project

```bash
git clone https://github.com/LOOPINX-CIRCLE/LoopinBackend.git
cd LoopinBackend
```

#### 2. Environment Configuration

The project includes a pre-configured `.env` file for development. For production, create your own:

```bash
# Development (default .env works out of the box)
cat .env

# For production, update these critical variables:
SECRET_KEY=your-very-long-and-secure-secret-key
JWT_SECRET_KEY=your-jwt-secret-key
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
DB_PASSWORD=your-secure-database-password
```

#### 3. Build and Start Docker Containers

```bash
# Build and start all services in the background
docker-compose up -d --build

# Check that services are running
docker-compose ps
```

This command will:
- Build the Python/Django/FastAPI application container
- Start PostgreSQL database container
- Set up networking between containers
- Mount volumes for persistent data

**Note**: The database will be ready when the health check passes, then you can run setup commands.

#### 4. Run Database Migrations

```bash
# Run migrations inside the web container
docker-compose exec web python manage.py migrate

# Create database tables for all apps
# This sets up User tables, UserProfile, and other models
```

#### 5. Create Django Superuser

```bash
# Create an admin user for Django admin interface
docker-compose exec web python manage.py createsuperuser

# Follow the prompts to set username, email, and password
# Example: admin / admin@example.com / securepassword123

# Alternative: Create superuser programmatically
docker-compose exec web python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"
```

#### 6. Collect Static Files

```bash
# Collect all static files for production serving
docker-compose exec web python manage.py collectstatic --noinput
```

#### 7. Verify Installation

```bash
# Test API health endpoint
curl http://localhost:8000/api/health

# Access services:
# - FastAPI Swagger UI: http://localhost:8000/api/docs
# - Django Admin: http://localhost:8000/django/admin/
# - API Root: http://localhost:8000/api/
```

#### 8. Run Tests

```bash
# Run Django tests
docker-compose exec web python manage.py test

# Run FastAPI tests
docker-compose exec web python -m pytest tests/fastapi/

# Run all tests
docker-compose exec web python -m pytest
```

## 📁 Project Structure

This project follows a clean, standards-based structure that separates concerns and maintains scalability:

```
loopin_backend/
├── 🐳 Docker Configuration
│   ├── docker-compose.yml       # Multi-container orchestration
│   └── Dockerfile              # Python application container
│
├── 🔧 Django Project (loopin_backend/)
│   ├── asgi.py                 # ASGI application (combines Django + FastAPI)
│   ├── wsgi.py                 # WSGI application (Django only)
│   ├── urls.py                 # Root URL configuration
│   └── settings/               # Environment-specific settings
│       ├── __init__.py         # Settings module initialization
│       ├── base.py             # Common settings for all environments
│       ├── dev.py              # Development-specific settings
│       └── prod.py             # Production-specific settings
│
├── 👥 Django App (users/)
│   ├── models.py               # User and UserProfile models
│   ├── admin.py                # Django admin configuration
│   ├── apps.py                 # App configuration
│   ├── migrations/             # Database schema migrations
│   │   ├── __init__.py
│   │   └── 0001_initial.py
│   ├── serializers/            # 📦 Modular DRF serializers
│   │   ├── __init__.py         # Clean imports from serializers
│   │   └── user_serializers.py # User-related serializers
│   ├── views/                  # 📦 Modular Django views
│   │   ├── __init__.py         # Clean imports from views
│   │   └── user_views.py       # User-related DRF views
│   └── tests/                  # 🧪 App-specific tests
│       ├── __init__.py
│       └── test_users.py       # Django model/serializer tests
│
├── 🚀 FastAPI Application (api/)
│   ├── main.py                 # FastAPI app initialization and configuration
│   └── routers/                # 📡 Feature-based API routes
│       ├── __init__.py         # Router module initialization
│       ├── auth.py             # 🔐 Authentication endpoints (JWT)
│       └── users.py            # 👥 User management endpoints
│
├── 🧪 Unified Testing (tests/)
│   ├── __init__.py             # Test module initialization
│   ├── django/                 # 🏗️ Django-specific tests
│   │   ├── __init__.py
│   │   └── test_users.py       # Django integration tests
│   └── fastapi/                # ⚡ FastAPI-specific tests
│       ├── __init__.py
│       ├── test_auth.py        # Authentication endpoint tests
│       └── test_integration.py # Cross-endpoint integration tests
│
├── 📂 Static & Media Files
│   ├── staticfiles/            # 🔄 Collected static files (CSS, JS, images)
│   └── media/                  # 🔄 User-uploaded files (avatars, documents)
│
└── 📋 Configuration Files
    ├── manage.py               # Django management commands
    ├── requirements.txt        # Python dependencies
    └── README.md              # This comprehensive guide
```

### Detailed Folder Explanations

#### `loopin_backend/` - Django Project Core
- **Purpose**: Contains Django project configuration and ASGI/WSGI applications
- **Key Files**:
  - `asgi.py`: Combines Django + FastAPI into single ASGI application
  - `settings/`: Environment-specific configurations (dev/prod separation)
  - `urls.py`: Root URL routing (only Django admin, FastAPI handles `/api/*`)

#### `users/` - Django App for User Management
- **Purpose**: Django app handling user models, admin interface, and DRF endpoints
- **Modular Structure**:
  - `serializers/`: One file per feature (e.g., `user_serializers.py`)
  - `views/`: One file per feature (e.g., `user_views.py`)
  - `tests/`: App-specific unit tests
- **Benefits**: Clean imports, easy to scale, maintainable

#### `api/` - FastAPI Application
- **Purpose**: High-performance API endpoints for mobile clients
- **Structure**:
  - `main.py`: FastAPI app initialization, middleware, CORS
  - `routers/`: Feature-based routing (auth, users, etc.)
- **Separation**: Completely independent from Django views

#### `tests/` - Framework-Specific Testing
- **Purpose**: Organized testing by framework type
- **Structure**:
  - `django/`: Django model, serializer, and integration tests
  - `fastapi/`: FastAPI endpoint and integration tests
- **Benefits**: Clear test organization, framework-specific test utilities

## 🎯 Development Strategy & Best Practices

### Coding Standards

#### 1. **Naming Conventions** (PEP 8 Compliant)
```python
# Files & Modules: snake_case
user_views.py, test_auth.py, user_serializers.py

# Classes: PascalCase
class UserProfile(models.Model):
class UserSerializer(serializers.ModelSerializer):
class UserListCreateView(generics.ListCreateAPIView):

# Functions & Variables: snake_case
def get_current_user():
def create_access_token():
user_data = request.json
access_token = "..."

# Constants: UPPER_SNAKE_CASE
SECRET_KEY = "..."
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30
```

#### 2. **Modular Organization**

**For Django Apps**:
```python
# users/serializers/__init__.py
from .user_serializers import *

# users/views/__init__.py  
from .user_views import *

# Clean imports in other files
from users.serializers import UserSerializer
from users.views import UserListCreateView
```

**For FastAPI Routers**:
```python
# api/main.py
from api.routers import auth, users

app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
```

#### 3. **Separation of Concerns**

| Component | Responsibility | Location |
|-----------|---------------|----------|
| **Django Models** | Database schema, ORM | `users/models.py` |
| **Django Admin** | Admin interface | `users/admin.py` |
| **DRF Serializers** | Data validation/serialization | `users/serializers/` |
| **DRF Views** | Web API endpoints | `users/views/` |
| **FastAPI Routers** | Mobile API endpoints | `api/routers/` |
| **Tests** | Framework-specific testing | `tests/django/`, `tests/fastapi/` |

### Adding New Features

#### Adding a New Django App
```bash
# 1. Create the app
docker-compose exec web python manage.py startapp new_app

# 2. Create modular structure
mkdir new_app/serializers new_app/views new_app/tests
touch new_app/serializers/__init__.py
touch new_app/views/__init__.py  
touch new_app/tests/__init__.py

# 3. Add to INSTALLED_APPS in settings/base.py
LOCAL_APPS = [
    'users',
    'new_app',  # Add here
]
```

#### Adding a New FastAPI Router
```python
# 1. Create new router file: api/routers/new_feature.py
from fastapi import APIRouter
router = APIRouter()

@router.get("/")
async def list_items():
    return {"items": []}

# 2. Import and include in api/main.py
from api.routers import auth, users, new_feature

app.include_router(new_feature.router, prefix="/new-feature", tags=["New Feature"])
```

#### Adding Tests
```python
# Django tests: tests/django/test_new_feature.py
from django.test import TestCase

class NewFeatureTest(TestCase):
    def test_something(self):
        pass

# FastAPI tests: tests/fastapi/test_new_feature.py  
from fastapi.testclient import TestClient

def test_new_endpoint():
    # Test FastAPI endpoints
    pass
```

## 🐳 Dockerized Development Best Practices

### Working with Containers

```bash
# Always run commands inside containers for consistency
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py shell
docker-compose exec web python manage.py test

# View logs
docker-compose logs web
docker-compose logs db

# Restart services
docker-compose restart web
docker-compose restart db
```

### Environment Management

```bash
# Development
export ENVIRONMENT=dev  # Uses settings/dev.py

# Production  
export ENVIRONMENT=prod  # Uses settings/prod.py

# Override individual settings
export DEBUG=False
export SECRET_KEY=production-secret-key
```

### Volume Management

```yaml
# docker-compose.yml volumes ensure data persistence
volumes:
  - static_volume:/app/staticfiles  # Static files persist
  - media_volume:/app/media        # User uploads persist
  - postgres_data:/var/lib/postgresql/data/  # Database persists
```

### Database Operations

```bash
# Backup database
docker-compose exec db pg_dump -U postgres loopin_db > backup.sql

# Restore database
docker-compose exec -T db psql -U postgres loopin_db < backup.sql

# Access database directly
docker-compose exec db psql -U postgres loopin_db
```

## 📚 API Documentation

### Access Points
- **FastAPI Swagger UI**: `http://localhost:8000/api/docs`
- **Django Admin**: `http://localhost:8000/django/admin/`
- **API Root**: `http://localhost:8000/api/`

### Example API Usage

#### Authentication Flow
```bash
# 1. Register user
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "email": "user@example.com", 
    "password": "securepassword123",
    "first_name": "John",
    "last_name": "Doe"
  }'

# 2. Login and get JWT token
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "newuser",
    "password": "securepassword123"
  }'

# 3. Use token for authenticated requests
curl -X GET http://localhost:8000/api/auth/me \
  -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

## 🧪 Testing Strategy

### Test Organization
```bash
# Run specific test types
python manage.py test users.tests         # Django app tests
python -m pytest tests/django/           # Django integration tests  
python -m pytest tests/fastapi/          # FastAPI endpoint tests
python -m pytest                         # All tests
```

### Test Coverage
```bash
# Install coverage
pip install coverage

# Run with coverage
coverage run --source='.' manage.py test
coverage run -m pytest
coverage report
coverage html  # Generates HTML report
```

## 🚀 Deployment

### Production Checklist
- [ ] Update `SECRET_KEY` and `JWT_SECRET_KEY`
- [ ] Set `DEBUG=False`
- [ ] Configure `ALLOWED_HOSTS`
- [ ] Set strong `DB_PASSWORD`
- [ ] Configure SSL certificates
- [ ] Set up proper CORS origins
- [ ] Configure email backend
- [ ] Set up monitoring and logging

### Environment Variables for Production
```bash
SECRET_KEY=your-production-secret-key
JWT_SECRET_KEY=your-production-jwt-key
DEBUG=False
ENVIRONMENT=prod
ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
DB_NAME=loopin_prod
DB_USER=loopin_user
DB_PASSWORD=secure-database-password
DB_HOST=your-db-host
DB_PORT=5432
```

## 🎯 Maintaining Code Quality

### Pre-commit Checklist
- [ ] All tests pass: `python -m pytest`
- [ ] Code follows naming conventions
- [ ] New features include tests
- [ ] Documentation updated
- [ ] No linting errors
- [ ] Migrations created if needed

### Code Review Guidelines
- [ ] Proper separation between Django and FastAPI code
- [ ] Consistent naming conventions followed
- [ ] Modular organization maintained
- [ ] Tests cover new functionality
- [ ] Security considerations addressed

## 📝 Contributing Guidelines

When contributing to this project, please:

1. **Follow the established structure**: Place code in appropriate folders (`serializers/`, `views/`, `routers/`)
2. **Maintain naming conventions**: Use snake_case for files/functions, PascalCase for classes
3. **Write tests**: Add tests in the correct framework folder (`tests/django/` or `tests/fastapi/`)
4. **Update documentation**: Keep README and docstrings current
5. **Use Docker**: Run all commands within containers for consistency

### Example Contribution Workflow
```bash
# 1. Create feature branch
git checkout -b feature/new-api-endpoint

# 2. Make changes following project structure
# Add router: api/routers/new_feature.py
# Add tests: tests/fastapi/test_new_feature.py

# 3. Test your changes
docker-compose exec web python -m pytest tests/fastapi/test_new_feature.py

# 4. Commit and push
git add .
git commit -m "Add new API endpoint for feature X"
git push origin feature/new-api-endpoint

# 5. Create pull request
```

---

## 🏆 Final Notes

This project structure is designed for **long-term maintainability** and **team collaboration**. By following these conventions consistently, you ensure:

- **Scalability**: Easy to add new features without architectural debt
- **Clarity**: New developers can quickly understand the codebase
- **Maintainability**: Clean separation makes debugging and updates easier
- **Quality**: Structured testing and coding standards prevent technical debt

**Remember**: Consistency is key. Follow this structured approach religiously to maintain a professional, enterprise-grade codebase that scales with your team and requirements.

Happy coding! 🚀