# Loopin Backend Setup Guide

This guide provides step-by-step instructions for setting up the Loopin Backend development environment.

## 📋 Table of Contents

### 🚀 Prerequisites
- [System Requirements](#-system-requirements)
- [Account Setup](#-account-setup)

### 🛠️ Development Setup
- [Environment Configuration](#-environment-configuration)
- [Docker Setup](#-docker-setup)
- [Database Setup](#-database-setup)
- [Verification](#-verification)

### 🧪 Testing & Validation
- [Running Tests](#-running-tests)
- [API Testing](#-api-testing)
- [Troubleshooting](#-troubleshooting)

## 🚀 Prerequisites

### System Requirements
- **Docker** and **Docker Compose** installed
- **Git** for version control
- **Text Editor** (VS Code, Vim, Nano, etc.)
- **Terminal/Command Line** access
- **Internet Connection** for downloading dependencies

### Account Setup

#### 1. Twilio Account (Required for SMS OTP)
1. **Sign up** at [Twilio Console](https://console.twilio.com/)
2. **Get Account SID** and **Auth Token** from dashboard
3. **Purchase a phone number** or use trial number
4. **Note**: Trial accounts can only send to verified numbers

#### 2. Supabase Account (Required for Database)
1. **Sign up** at [Supabase](https://supabase.com/)
2. **Create a new project**
3. **Get database connection string** from Settings > Database
4. **Note**: Use Transaction pooler URL for better performance

## 🛠️ Development Setup

### 1. Clone Repository
```bash
git clone https://github.com/LOOPINX-CIRCLE/LoopinBackend.git
cd LoopinBackend
```

### 2. Environment Configuration

#### Create Environment File
```bash
# Copy the example file
cp .env.example .env

# Edit with your actual credentials
nano .env
```

#### Required Environment Variables
```bash
# Django Settings
SECRET_KEY=your-very-long-and-secure-secret-key-here
DEBUG=True
DJANGO_SETTINGS_MODULE=loopin_backend.settings.dev

# Database Configuration (Supabase)
DATABASE_URL=postgresql://username:password@host:port/database

# JWT Settings
JWT_SECRET_KEY=your-jwt-secret-key-here
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# Twilio Configuration (Get from Twilio Console)
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_PHONE_NUMBER=+15005550006
TWILIO_TEST_MODE=true  # Set to false for production

# CORS Settings
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://127.0.0.1:3000
```

### 3. Docker Setup

**📋 For detailed Docker commands and management, see:**
**[🐳 DOCKER_README.md](./DOCKER_README.md)**

#### Build and Start Containers
```bash
# Build and start all services in the background
docker-compose up -d --build

# Check that services are running
docker-compose ps
```

#### Expected Services
- **web**: Django + FastAPI application (port 8000)
- **postgres**: PostgreSQL database (port 5432)
- **redis**: Redis cache (port 6379)
- **celery**: Background task worker
- **celery-beat**: Scheduled task scheduler
- **flower**: Celery monitoring (port 5555)

### 4. Database Setup

#### Run Migrations
```bash
# Run migrations inside the web container
docker-compose exec web python manage.py migrate

# This creates all necessary database tables:
# - User authentication tables
# - UserProfile, PhoneOTP, EventInterest
# - Events, Attendances, Payments, Audit, Notifications
```

#### Create Superuser
```bash
# Create an admin user for Django admin interface
docker-compose exec web python manage.py createsuperuser

# Follow the prompts:
# Username: admin
# Email: admin@example.com
# Password: [choose a secure password]
```

#### Load Initial Data
```bash
# Load default event interests
docker-compose exec web python manage.py shell -c "
from users.models import EventInterest
interests = [
    'Music & Concerts', 'Sports & Fitness', 'Food & Dining',
    'Art & Culture', 'Technology', 'Travel & Adventure',
    'Business & Networking', 'Health & Wellness',
    'Education & Learning', 'Entertainment'
]
for interest in interests:
    EventInterest.objects.get_or_create(name=interest)
print('Event interests loaded successfully')
"
```

#### Collect Static Files
```bash
# Collect all static files for production serving
docker-compose exec web python manage.py collectstatic --noinput
```

## 🧪 Testing & Validation

### Verification

#### 1. Test API Health
```bash
# Test API health endpoint
curl http://localhost:8000/api/health

# Expected response:
# {"status": "healthy", "service": "loopin-backend", "version": "1.0.0"}
```

#### 2. Access Services
- **FastAPI Swagger UI**: http://localhost:8000/api/docs
- **Django Admin**: http://localhost:8000/admin/
- **API Root**: http://localhost:8000/api/
- **Flower (Celery)**: http://localhost:5555

#### 3. Test Phone Authentication
```bash
# Test signup endpoint
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890"}'

# Expected response:
# {"message": "OTP sent successfully", "phone_number": "+1234567890"}
```

### Running Tests

#### Django Tests
```bash
# Run Django model and view tests
docker-compose exec web python manage.py test

# Run specific app tests
docker-compose exec web python manage.py test users
docker-compose exec web python manage.py test events
```

#### FastAPI Tests
```bash
# Run FastAPI endpoint tests
docker-compose exec web python -m pytest tests/fastapi/

# Run all tests
docker-compose exec web python -m pytest
```

#### Test Coverage
```bash
# Install coverage (if not already installed)
docker-compose exec web pip install coverage

# Run with coverage
docker-compose exec web coverage run --source='.' manage.py test
docker-compose exec web coverage report
docker-compose exec web coverage html  # Generates HTML report
```

### API Testing

#### Test Phone Authentication Flow
```bash
# 1. Send OTP
curl -X POST http://localhost:8000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890"}'

# 2. Verify OTP (use the OTP received via SMS)
curl -X POST http://localhost:8000/api/auth/verify-otp \
  -H "Content-Type: application/json" \
  -d '{"phone_number": "+1234567890", "otp": "1234"}'

# 3. Complete Profile
curl -X POST http://localhost:8000/api/auth/complete-profile \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \
  -d '{
    "name": "John Doe",
    "birth_date": "1990-01-01",
    "gender": "male",
    "location": "New York",
    "bio": "Hello world!"
  }'
```

## 🔧 Development Commands

**📋 For comprehensive Docker commands and management, see:**
**[🐳 DOCKER_README.md](./DOCKER_README.md)**

### Django Management
```bash
# Django shell
docker-compose exec web python manage.py shell

# Create migrations
docker-compose exec web python manage.py makemigrations

# Run migrations
docker-compose exec web python manage.py migrate

# Create superuser
docker-compose exec web python manage.py createsuperuser

# Collect static files
docker-compose exec web python manage.py collectstatic --noinput
```

### Database Management
```bash
# Access database shell
docker-compose exec postgres psql -U postgres -d loopin

# Backup database
docker-compose exec postgres pg_dump -U postgres loopin > backup.sql

# Restore database
docker-compose exec -T postgres psql -U postgres loopin < backup.sql
```

## 🐛 Troubleshooting

**📋 For Docker-specific troubleshooting, see:**
**[🐳 DOCKER_README.md](./DOCKER_README.md)**

### Common Issues

#### 1. Twilio SMS Issues
- **Trial Account**: Can only send to verified numbers
- **Invalid Number**: Check phone number format (+1234567890)
- **Auth Token**: Verify TWILIO_AUTH_TOKEN is correct
- **Account SID**: Verify TWILIO_ACCOUNT_SID is correct

#### 2. Environment Configuration Issues
- **Missing Variables**: Ensure all required environment variables are set
- **Invalid Format**: Check phone number format and database URL format
- **File Permissions**: Ensure `.env` file is readable by Docker

#### 3. Database Connection Issues
- **Connection String**: Verify DATABASE_URL format in `.env` file
- **Supabase Settings**: Check Supabase project settings and connection details
- **Network Issues**: Ensure internet connection for Supabase access

### Debug Mode

#### Enable Debug Logging
```bash
# Add to .env file
DEBUG=True
LOG_LEVEL=DEBUG

# Restart services
docker-compose restart web
```

#### View Detailed Logs
```bash
# Follow logs in real-time
docker-compose logs -f web

# View specific service logs
docker-compose logs postgres
docker-compose logs redis
```

## 🚀 Next Steps

### Development Workflow
1. **Make Changes**: Edit code in your preferred editor
2. **Test Changes**: Run tests to ensure everything works
3. **Commit Changes**: Use proper git workflow
4. **Deploy**: Follow deployment procedures

### Documentation Resources
- **System Overview**: [README.md](./README.md) - Complete system architecture and overview
- **Docker Management**: [DOCKER_README.md](./DOCKER_README.md) - Docker commands and troubleshooting
- **Module Documentation**: Each module has its own `docs/` directory
- **API Documentation**: Visit http://localhost:8000/api/docs

### Learning Resources
- **Django Documentation**: https://docs.djangoproject.com/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **Docker Documentation**: https://docs.docker.com/
- **Twilio Documentation**: https://www.twilio.com/docs

### Getting Help
- **Check Logs**: Always check Docker logs first
- **Review Documentation**: See module-specific docs
- **Test Endpoints**: Use API testing tools
- **Community**: Django and FastAPI communities

---

## ✅ Setup Complete!

Your Loopin Backend development environment is now ready! 

**Next Steps:**
1. **Explore the API**: Visit http://localhost:8000/api/docs
2. **Check Admin**: Visit http://localhost:8000/admin/
3. **Read Documentation**: Review module-specific docs
4. **Start Coding**: Begin your development journey!

**Happy coding! 🚀**
