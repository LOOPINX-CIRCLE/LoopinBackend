# 🐳 Docker Development Setup

This document explains how to use Docker for development with the Loopin Backend.

**📋 For complete setup instructions, see:**
**[🚀 INSTALLATION.md](./INSTALLATION.md)**

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose installed
- Git (for cloning the repository)
- **Complete setup**: Follow [SETUP_GUIDE.md](./SETUP_GUIDE.md) for full environment setup

### 1. Start Development Environment
```bash
# Using Makefile (recommended) - Uses Django runserver
make setup

# Or manually - Development mode
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# For production-like testing - Uses Nginx + Gunicorn
make prod
```

### 2. Access Services
- **Web Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs
- **Django Admin**: http://localhost:8000/admin/ (Database Management)
- **Flower (Celery Monitor)**: http://localhost:5555

## 📋 Available Commands

### Using Makefile (Recommended)
```bash
make help              # Show all available commands
make build             # Build Docker images
make dev               # Start development environment
make up                # Start production-like environment
make down              # Stop all services
make logs              # Show logs for all services
make shell             # Open shell in web container
make migrate           # Run Django migrations
make test              # Run Django tests
make clean             # Clean up containers and volumes
```

### Using Docker Compose Directly
```bash
# Development environment
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Production-like environment
docker-compose up -d

# View logs
docker-compose logs -f web
docker-compose logs -f celery

# Run commands in containers
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py shell
```

## 🗄️ Database Management with Django Admin

### **Why Django Admin is Perfect for Development**

Django Admin provides everything you need for database management during development:

#### **✅ Features:**
- **User-friendly Interface**: Easy to navigate and use
- **Model Management**: View, create, edit, delete records
- **User Management**: Create superusers, manage permissions
- **Data Visualization**: See all your Django models and data
- **Search & Filter**: Find records quickly
- **Bulk Actions**: Perform actions on multiple records
- **No External Tools**: Everything built into Django

#### **🚀 Quick Access:**
```bash
# 1. Start development environment
make dev

# 2. Create superuser (if not already done)
make createsuperuser

# 3. Access Django Admin
# Visit: http://localhost:8000/admin/
```

#### **📊 What You Can Manage:**
- **Users**: User profiles, authentication, permissions
- **Events**: Event creation, management, requests
- **Attendances**: Check-in/check-out records
- **Payments**: Payment orders and transactions
- **Audit Logs**: System activity tracking
- **Notifications**: User notifications

**📋 For detailed database setup and management, see:**
**[🚀 SETUP_GUIDE.md](./SETUP_GUIDE.md)**

## 🚀 Server Choice: Django vs Nginx

### **Development Mode (Recommended)**
- **Server**: Django's built-in runserver
- **Command**: `python manage.py runserver 0.0.0.0:8000`
- **Benefits**: 
  - ✅ Hot reload (code changes auto-refresh)
  - ✅ Debug mode with detailed error messages
  - ✅ Easy debugging and development
  - ✅ Direct access to Django features
- **Access**: http://localhost:8000

### **Production Mode (Future)**
- **Server**: Nginx + Gunicorn/Uvicorn
- **Command**: `gunicorn loopin_backend.asgi:application -w 4 -k uvicorn.workers.UvicornWorker`
- **Benefits**:
  - ✅ Better performance and scalability
  - ✅ Static file serving optimization
  - ✅ Security headers and rate limiting
  - ✅ SSL/TLS termination
- **Access**: http://localhost:80 (Nginx) → http://localhost:8000 (Django)

### **When to Use Which?**

| Mode | Command | Use Case | Server |
|------|---------|----------|--------|
| **Development** | `make dev` | Daily coding, debugging | Django runserver |
| **Testing** | `make prod` | Production testing | Nginx + Gunicorn |
| **Production** | `make prod` | Live deployment | Nginx + Gunicorn |

## 🏗️ Architecture

### Services Overview

| Service | Port | Purpose | Development Features |
|---------|------|---------|---------------------|
| **web** | 8000 | Django + FastAPI application | Hot reload, debug mode |
| **postgres** | 5432 | PostgreSQL database | Exposed port, persistent data |
| **redis** | 6379 | Redis cache & Celery broker | Exposed port, persistent data |
| **celery** | - | Background task worker | Debug logging, single concurrency |
| **celery-beat** | - | Scheduled task scheduler | Debug logging |
| **flower** | 5555 | Celery monitoring | Basic auth (admin/admin) |
| **nginx** | 80 | Reverse proxy & static files | Rate limiting, gzip compression |

### Development vs Production

#### Development Mode (`docker-compose.dev.yml`)
- **Hot Reload**: Code changes automatically reload
- **Debug Mode**: Detailed error messages and logging
- **Exposed Ports**: Direct access to services
- **Single Concurrency**: Easier debugging

#### Production Mode (`docker-compose.yml`)
- **Optimized**: Gunicorn with multiple workers
- **Security**: Rate limiting, security headers
- **Performance**: Nginx reverse proxy, gzip compression
- **Monitoring**: Health checks, restart policies
- **Scalability**: Multiple Celery workers

## 🔧 Configuration

### Environment Variables

Create a `.env` file with the following variables:

```env
# Database
DATABASE_URL=postgresql://postgres:password@postgres:5432/loopin
POSTGRES_DB=loopin
POSTGRES_USER=postgres
POSTGRES_PASSWORD=password

# Redis
REDIS_URL=redis://redis:6379/0

# Celery
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# Django
DEBUG=True
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# External Services
TWILIO_ACCOUNT_SID=your-twilio-sid
TWILIO_AUTH_TOKEN=your-twilio-token
TWILIO_PHONE_NUMBER=your-twilio-number
```

### Volume Mounts

- **Code**: `.:/app` - Live code editing
- **Static Files**: `static_volume:/app/staticfiles` - Persistent static files
- **Media Files**: `media_volume:/app/media` - Persistent media files
- **Logs**: `logs_volume:/app/logs` - Persistent log files
- **Database**: `postgres_data:/var/lib/postgresql/data` - Persistent database
- **Redis**: `redis_data:/data` - Persistent Redis data

## 🛠️ Development Workflow

### Daily Development Commands
```bash
# Start development environment
make dev

# Check service health
make health

# View logs
make logs-web
```

### Code Changes
- Edit code in your local editor
- Changes are automatically reflected in the container
- Restart services if needed: `make restart`

### Background Tasks
```bash
# Monitor Celery tasks
make flower

# Access Celery shell
make celery-shell

# Purge all tasks
make celery-purge
```

**📋 For complete development workflow, database operations, and testing, see:**
**[🚀 SETUP_GUIDE.md](./SETUP_GUIDE.md)**

## 🐛 Troubleshooting

### Common Issues

#### 1. Port Already in Use
```bash
# Check what's using the port
lsof -i :8000

# Kill the process or change port in docker-compose.yml
```

#### 2. Database Connection Issues
```bash
# Check PostgreSQL logs
make logs-postgres

# Restart database
docker-compose restart postgres

# Access Django Admin to verify database
# Visit: http://localhost:8000/admin/
```

#### 3. Redis Connection Issues
```bash
# Check Redis logs
make logs-redis

# Test Redis connection
docker-compose exec redis redis-cli ping
```

#### 4. Celery Not Working
```bash
# Check Celery logs
make logs-celery

# Restart Celery
docker-compose restart celery celery-beat
```

#### 5. Static Files Not Loading
```bash
# Collect static files
make collectstatic

# Check Nginx logs
docker-compose logs nginx
```

### Debugging Commands

```bash
# Check all service status
docker-compose ps

# Check resource usage
docker stats

# Access container shell
make shell

# View detailed logs
docker-compose logs --tail=100 web
```

### Cleanup Commands

```bash
# Clean up containers and volumes
make clean

# Clean up everything including images
make clean-all

# Remove specific service
docker-compose rm -f web
```

## 📊 Monitoring

### Health Checks
- **Web Service**: http://localhost:8000/api/health/
- **Database**: Automatic health checks in Docker
- **Redis**: Automatic health checks in Docker

### Monitoring Tools
- **Flower**: http://localhost:5555 - Celery task monitoring
- **Docker Stats**: `docker stats` - Resource usage

### Logs
- **Application Logs**: `make logs-web`
- **Database Logs**: `make logs-postgres`
- **Redis Logs**: `make logs-redis`
- **Celery Logs**: `make logs-celery`

## 🔒 Security Notes

### Development
- Debug mode enabled
- Exposed ports for easy access
- Basic authentication for Flower monitoring

### Production (Future)
- Debug mode disabled
- Rate limiting enabled
- Security headers configured
- SSL/TLS termination
- Secret management

## 📈 Performance Optimization

### Development
- Single Celery worker for easier debugging
- Debug logging enabled
- Hot reload for faster development

### Production (Future)
- Multiple Gunicorn workers
- Multiple Celery workers
- Redis clustering
- Database connection pooling
- CDN for static files

## 🚀 Deployment Notes

This Docker setup is optimized for **development only**. For production deployment:

1. **Security**: Disable debug mode, use secrets management
2. **Performance**: Use production-grade WSGI server (Gunicorn)
3. **Scalability**: Implement horizontal scaling
4. **Monitoring**: Add comprehensive monitoring and alerting
5. **Backup**: Implement database and file backups
6. **SSL**: Configure SSL/TLS termination

---

## 📞 Support

For issues with Docker setup:
1. Check the troubleshooting section above
2. Review Docker logs: `make logs`
3. Check service health: `make health`
4. Contact the development team

**Happy coding! 🎉**
