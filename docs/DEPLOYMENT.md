# Deployment Guide

## Quick Start

### Prerequisites
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+
- Python 3.11+

### Local Development

```bash
# Clone repository
git clone <repository-url>
cd LoopinBackend

# Copy environment file
cp .env.example .env

# Update environment variables in .env
nano .env

# Start services
docker-compose up -d

# Run migrations
docker-compose exec web python3 manage.py migrate

# Create superuser
docker-compose exec web python3 setup_data.py

# Access services
# - API: http://localhost:8000/api/
# - Admin: http://localhost:8000/django/admin/
# - Docs: http://localhost:8000/api/docs
```

### Production Deployment

#### Environment Variables
```bash
# Django
SECRET_KEY=<generate-secure-key>
DEBUG=False
ALLOWED_HOSTS=your-domain.com,*.your-domain.com

# Database (Supabase)
DATABASE_URL=postgresql://user:password@host:5432/dbname

# JWT
JWT_SECRET_KEY=<generate-secure-key>
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=30

# CORS
CORS_ALLOWED_ORIGINS=https://your-domain.com,https://app.your-domain.com

# Twilio (for SMS)
TWILIO_ACCOUNT_SID=<your-sid>
TWILIO_AUTH_TOKEN=<your-token>
TWILIO_PHONE_NUMBER=<your-number>
TWILIO_TEST_MODE=false
```

#### Docker Deployment

```bash
# Build image
docker-compose -f docker-compose.yml build

# Start services
docker-compose -f docker-compose.yml up -d

# Run migrations
docker-compose exec web python3 manage.py migrate

# Collect static files
docker-compose exec web python3 manage.py collectstatic --noinput

# Create superuser
docker-compose exec web python3 setup_data.py
```

#### Render Deployment

1. Connect GitHub repository
2. Set environment variables
3. Use build command: `pip install -r requirements.txt`
4. Use start command: `gunicorn loopin_backend.asgi:application -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT`

---

## Database Migrations

```bash
# Create migrations
docker-compose exec web python3 manage.py makemigrations

# Apply migrations
docker-compose exec web python3 manage.py migrate

# Rollback migration
docker-compose exec web python3 manage.py migrate events 0001
```

---

## Health Checks

```bash
# Check API health
curl http://localhost:8000/api/health

# Check database connection
docker-compose exec web python3 manage.py dbshell

# Check Redis connection
docker-compose exec redis redis-cli ping
```

---

## Monitoring

### Logs
```bash
# View logs
docker-compose logs web -f

# View error logs only
docker-compose logs web | grep ERROR
```

### Metrics
- Request rate monitoring
- Response time tracking
- Database query performance
- Error rate alerts

---

## Security Checklist

- [x] JWT authentication
- [x] SQL injection protection (Django ORM)
- [x] XSS protection
- [x] CSRF protection
- [x] Secure headers
- [x] Rate limiting
- [x] Input validation
- [x] Secrets management
- [x] HTTPS enforcement
- [x] Security headers

---

## Performance Optimization

### Database
- Connection pooling enabled
- Query optimization with select_related/prefetch_related
- Database indexes on key fields
- Query caching

### Caching
- Redis for session storage
- Query result caching
- HTTP response caching

### Code
- Async operations where applicable
- Lazy loading of relationships
- Pagination for list endpoints
- Streaming for large responses

---

## Backup & Recovery

### Database Backup
```bash
docker-compose exec postgres pg_dump -U postgres loopin > backup.sql
```

### Database Restore
```bash
docker-compose exec -T postgres psql -U postgres loopin < backup.sql
```

---

## Scaling

### Horizontal Scaling
- Multiple worker processes (Gunicorn)
- Load balancer configuration
- Database read replicas

### Vertical Scaling
- Increase worker processes
- Increase memory allocation
- Database connection pooling

---

## Troubleshooting

### Common Issues

**Database connection errors**:
```bash
# Check database is running
docker-compose ps postgres

# Check connection string
docker-compose exec web python3 manage.py dbshell
```

**Import errors**:
```bash
# Clear Python cache
find . -type d -name __pycache__ -exec rm -r {} +

# Rebuild container
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

**Port conflicts**:
```bash
# Check what's using the port
sudo lsof -i :8000

# Kill process or change port in docker-compose.yml
```

---

## Support

For issues or questions:
- GitHub Issues: https://github.com/LOOPINX-CIRCLE/LoopinBackend/issues
- Documentation: https://docs.loopinx.com
- Email: support@loopinx.com

