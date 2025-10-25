# Loopin Backend

A modern mobile backend built with Django + FastAPI, featuring phone authentication, PostgreSQL database, and Docker containerization.

## 📋 Table of Contents

### 🏗️ System Architecture
- [Architecture Overview](#-architecture-overview)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Database Schema](#-database-schema)
- [Detailed Architecture](#-detailed-architecture)

### 🐳 Infrastructure & DevOps
- [Docker Configuration](#-docker-configuration)
- [Development Environment](#-development-environment)
- [Production Deployment](#-production-deployment)
- [Monitoring & Logging](#-monitoring--logging)

### 📚 Documentation & APIs
- [Module Documentation](#-module-documentation)
- [API Reference](#-api-reference)
- [Development Guides](#-development-guides)

### 🚀 Getting Started
- [Project Setup Guide](#-project-setup-guide)
- [First Steps](#-first-steps)

### 🎯 Development Workflow
- [Code Organization](#-code-organization)
- [Testing Strategy](#-testing-strategy)
- [Deployment Process](#-deployment-process)
- [Contributing Guidelines](#-contributing-guidelines)

## 🏗️ Architecture Overview

### System Architecture
```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Mobile Apps   │────│   FastAPI API    │────│   Supabase      │
│  (iOS/Android)  │    │   (/api/*)       │    │   PostgreSQL    │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                       ┌──────────────────┐
                       │   Django Admin    │
                       │   (/admin/*)     │
                       └──────────────────┘
                              │
                       ┌──────────────────┐
                       │   Twilio SMS     │
                       │   OTP Service    │
                       └──────────────────┘
```

### Request Flow
1. **Mobile App** → **FastAPI** → **Authentication** → **Business Logic**
2. **Admin Panel** → **Django Admin** → **Database Management**
3. **Background Tasks** → **Celery** → **Redis** → **External Services**

### Data Flow
1. **User Registration** → **Phone OTP** → **Profile Creation** → **Database**
2. **Event Management** → **Payment Processing** → **Attendance Tracking**
3. **Analytics** → **Audit Logging** → **Notifications** → **User Engagement**

## 🔧 Tech Stack

### Core Backend Technologies
| Component | Technology | Purpose | Version |
|-----------|------------|---------|---------|
| **Web Framework** | Django | ORM, migrations, admin interface | 5.2 |
| **API Framework** | FastAPI | High-performance API endpoints | Latest |
| **Database** | PostgreSQL | Primary data storage | 15+ |
| **Cache** | Redis | Session storage, caching | 7+ |
| **Message Broker** | Redis | Celery task queue | 7+ |

### Authentication & Security
| Component | Technology | Purpose | Integration |
|-----------|------------|---------|-------------|
| **Phone Auth** | Twilio SMS | OTP delivery service | REST API |
| **JWT Tokens** | PyJWT | Secure authentication | Custom implementation |
| **CORS** | FastAPI CORS | Cross-origin requests | Middleware |
| **Password Hashing** | Django | Secure password storage | Built-in |

### Infrastructure & DevOps
| Component | Technology | Purpose | Configuration |
|-----------|------------|---------|---------------|
| **Containerization** | Docker | Application packaging | Multi-stage builds |
| **Orchestration** | Docker Compose | Service management | Development/Production |
| **Reverse Proxy** | Nginx | Static files, load balancing | Production only |
| **WSGI Server** | Gunicorn | Production web server | Multi-worker |
| **Task Queue** | Celery | Background processing | Redis broker |
| **Monitoring** | Flower | Celery monitoring | Web interface |

### External Services
| Service | Provider | Purpose | Configuration |
|---------|----------|---------|---------------|
| **Database Hosting** | Supabase | Cloud PostgreSQL | Transaction pooler |
| **SMS Service** | Twilio | OTP delivery | REST API |
| **File Storage** | Local/Cloud | Media files | Configurable |

### Development Tools
| Tool | Purpose | Integration |
|------|--------|-------------|
| **Git** | Version control | GitHub integration |
| **Docker** | Development environment | Local development |
| **Pytest** | Testing framework | Unit & integration tests |
| **Coverage** | Test coverage | Code quality metrics |
| **Swagger UI** | API documentation | Auto-generated |

## 📁 Project Structure

### Directory Organization
```
.
├── api
│   ├── docs
│   │   └── README.md
│   ├── health.py
│   ├── __init__.py
│   ├── main.py
│   ├── __pycache__
│   │   ├── __init__.cpython-313.pyc
│   │   └── main.cpython-313.pyc
│   ├── routers
│   │   ├── auth.py
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── auth.cpython-313.pyc
│   │   │   ├── __init__.cpython-313.pyc
│   │   │   └── users.cpython-313.pyc
│   │   └── users.py
│   ├── schemas
│   │   └── __init__.py
│   └── services
│       └── __init__.py
├── attendances
│   ├── admin.py
│   ├── apps.py
│   ├── docs
│   │   └── README.md
│   ├── __init__.py
│   ├── migrations
│   │   └── __init__.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
├── audit
│   ├── admin.py
│   ├── apps.py
│   ├── docs
│   │   └── README.md
│   ├── __init__.py
│   ├── migrations
│   │   └── __init__.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
├── core
│   ├── base_models.py
│   ├── choices.py
│   ├── db_utils.py
│   ├── exceptions.py
│   ├── __init__.py
│   ├── middleware
│   │   ├── auth_middleware.py
│   │   ├── exception_handler.py
│   │   └── request_logging.py
│   ├── permissions.py
│   ├── __pycache__
│   │   ├── base_models.cpython-313.pyc
│   │   └── __init__.cpython-313.pyc
│   ├── signals
│   │   ├── notification_events.py
│   │   └── user_activity.py
│   └── utils
│       ├── cache.py
│       ├── __init__.py
│       └── logger.py
├── docker-compose.dev.yml
├── docker-compose.yml
├── Dockerfile
├── docs
│   ├── ARCHITECTURE_OVERVIEW.md
│   ├── DOCKER_GUIDE.md
│   ├── erd_doc_fixed.md
│   ├── INSTALLATION.md
│   └── README.md
├── events
│   ├── admin.py
│   ├── apps.py
│   ├── docs
│   │   └── README.md
│   ├── __init__.py
│   ├── migrations
│   │   └── __init__.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
├── loopin_backend
│   ├── asgi.py
│   ├── __init__.py
│   ├── __pycache__
│   │   ├── asgi.cpython-313.pyc
│   │   ├── db_utils.cpython-313.pyc
│   │   ├── __init__.cpython-312.pyc
│   │   ├── __init__.cpython-313.pyc
│   │   ├── settings.cpython-312.pyc
│   │   ├── urls.cpython-313.pyc
│   │   └── wsgi.cpython-313.pyc
│   ├── settings
│   │   ├── base.py
│   │   ├── dev.py
│   │   ├── __init__.py
│   │   ├── prod.py
│   │   └── __pycache__
│   │       ├── base.cpython-313.pyc
│   │       ├── dev.cpython-313.pyc
│   │       ├── __init__.cpython-313.pyc
│   │       └── prod.cpython-313.pyc
│   ├── urls.py
│   └── wsgi.py
├── Makefile
├── manage.py
├── media
├── nginx.conf
├── notifications
│   ├── admin.py
│   ├── apps.py
│   ├── docs
│   │   └── README.md
│   ├── __init__.py
│   ├── migrations
│   │   └── __init__.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
├── payments
│   ├── admin.py
│   ├── apps.py
│   ├── docs
│   │   └── README.md
│   ├── __init__.py
│   ├── migrations
│   │   └── __init__.py
│   ├── models.py
│   ├── tests.py
│   └── views.py
├── __pycache__
│   └── manage.cpython-313.pyc
├── README.md
├── requirements.txt
├── staticfiles
├── tests
│   ├── django
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-313.pyc
│   │   │   └── test_users.cpython-313.pyc
│   │   └── test_users.py
│   ├── fastapi
│   │   ├── __init__.py
│   │   ├── __pycache__
│   │   │   ├── __init__.cpython-313.pyc
│   │   │   ├── test_auth.cpython-313.pyc
│   │   │   └── test_integration.cpython-313.pyc
│   │   ├── test_auth.py
│   │   └── test_integration.py
│   ├── __init__.py
│   └── __pycache__
│       └── __init__.cpython-313.pyc
└── users
    ├── admin.py
    ├── apps.py
    ├── auth_router.py
    ├── docs
    │   ├── PHONE_AUTHENTICATION.md
    │   └── README.md
    ├── __init__.py
    ├── migrations
    │   ├── 0001_initial.py
    │   ├── 0002_alter_userprofile_options_userprofile_email_and_more.py
    │   ├── 0003_phoneotp.py
    │   ├── 0004_auto_20251006_1649.py
    │   ├── 0005_eventinterest_userprofile_gender_and_more.py
    │   ├── 0006_remove_userprofile_avatar_remove_userprofile_email.py
    │   ├── __init__.py
    │   └── __pycache__
    │       ├── 0001_initial.cpython-313.pyc
    │       └── __init__.cpython-313.pyc
    ├── models.py
    ├── __pycache__
    │   ├── admin.cpython-313.pyc
    │   ├── apps.cpython-313.pyc
    │   ├── auth_router.cpython-313.pyc
    │   ├── __init__.cpython-313.pyc
    │   ├── models.cpython-313.pyc
    │   └── services.cpython-313.pyc
    ├── schemas.py
    ├── serializers
    │   ├── __init__.py
    │   ├── __pycache__
    │   │   ├── __init__.cpython-313.pyc
    │   │   └── user_serializers.cpython-313.pyc
    │   └── user_serializers.py
    ├── services.py
    ├── tests
    │   ├── __init__.py
    │   ├── __pycache__
    │   │   ├── __init__.cpython-313.pyc
    │   │   └── test_users.cpython-313.pyc
    │   ├── README.md
    │   ├── test_auth_working.py
    │   ├── test_comprehensive_auth.py
    │   ├── test_schemas.py
    │   ├── test_services.py
    │   └── test_users.py
    └── views
        ├── __init__.py
        ├── __pycache__
        │   ├── __init__.cpython-313.pyc
        │   └── user_views.cpython-313.pyc
        └── user_views.py

53 directories, 156 files
```

### Module Responsibilities
| Module | Purpose | Key Components | Documentation |
|--------|---------|----------------|---------------|
| **users** | Authentication & user management | Phone OTP, profiles, interests | [users/docs/](./users/docs/) |
| **events** | Event creation & management | Venues, requests, invites | [events/docs/](./events/docs/) |
| **attendances** | Check-in/check-out system | Records, OTP validation | [attendances/docs/](./attendances/docs/) |
| **payments** | Payment processing | Orders, transactions, webhooks | [payments/docs/](./payments/docs/) |
| **audit** | System auditing | Logs, compliance tracking | [audit/docs/](./audit/docs/) |
| **notifications** | User communication | Messages, alerts | [notifications/docs/](./notifications/docs/) |
| **api** | FastAPI endpoints | Mobile API, health checks | [api/docs/](./api/docs/) |

### Code Organization Principles
1. **Separation of Concerns**: Each module handles specific business logic
2. **Modular Design**: Independent, reusable components
3. **Clear Interfaces**: Well-defined APIs between modules
4. **Documentation**: Each module maintains its own documentation
5. **Testing**: Comprehensive test coverage per module

## 🗄️ Database Schema

### Database Architecture
The system uses a comprehensive PostgreSQL database schema with proper relationships, constraints, and indexing for optimal performance.

**📋 For complete database documentation and ERD diagrams, see:**
**[🗄️ docs/erd_doc_fixed.md](./docs/erd_doc_fixed.md)**

### Core Entities & Relationships
| Entity | Purpose | Key Relationships |
|--------|---------|-------------------|
| **UserProfile** | User authentication & profiles | One-to-One with User |
| **PhoneOTP** | OTP verification system | One-to-One with User |
| **EventInterest** | Dynamic event categories | Many-to-Many with UserProfile |
| **Event** | Event management | One-to-Many with User (host) |
| **EventRequest** | Event join requests | Many-to-One with Event & User |
| **AttendanceRecord** | Check-in/check-out tracking | Many-to-One with Event & User |
| **PaymentOrder** | Payment processing | Many-to-One with Event & User |
| **AuditLog** | System auditing | Many-to-One with User |
| **Notification** | User communications | Many-to-One with User |

### Database Features
- **ACID Compliance**: Full transaction support
- **Referential Integrity**: Foreign key constraints
- **Indexing Strategy**: Optimized for common queries
- **Data Validation**: Database-level constraints
- **Audit Trail**: Complete change tracking
- **Soft Deletes**: Data preservation with logical deletion

## 🏗️ Detailed Architecture

### Comprehensive Technical Architecture
For detailed technical architecture, component interactions, and architectural decisions:

**📋 Complete architecture documentation:**
**[🏗️ docs/ARCHITECTURE_OVERVIEW.md](./docs/ARCHITECTURE_OVERVIEW.md)**

### Key Architectural Components
- **Core Package**: Shared utilities, base models, and common functionality
- **Modular Django Apps**: Standardized app structure with verbose names
- **Organized API Layer**: Separated authentication and user management routers
- **Service Architecture**: Clear separation of concerns and responsibilities
- **Security Architecture**: Comprehensive authentication and authorization system

## 🐳 Docker Configuration

### Development Environment
| Service | Purpose | Port | Configuration |
|---------|--------|------|--------------|
| **web** | Django + FastAPI app | 8000 | Hot reload, debug mode |
| **postgres** | PostgreSQL database | 5432 | Persistent data |
| **redis** | Cache & message broker | 6379 | Session storage |
| **celery** | Background tasks | - | Async processing |
| **celery-beat** | Scheduled tasks | - | Cron-like scheduling |
| **flower** | Celery monitoring | 5555 | Task monitoring |

### Production Environment
| Component | Technology | Purpose | Configuration |
|-----------|------------|---------|---------------|
| **Reverse Proxy** | Nginx | Static files, load balancing | Production only |
| **WSGI Server** | Gunicorn | Multi-worker web server | Production only |
| **Database** | Supabase | Cloud PostgreSQL | Transaction pooler |
| **Cache** | Redis | Session & cache storage | Persistent |
| **Monitoring** | Flower | Task monitoring | Web interface |

**📋 For complete Docker setup and management, see:**
**[🐳 docs/DOCKER_GUIDE.md](./docs/DOCKER_GUIDE.md)**

## 🚀 API Reference

### API Endpoints Overview
| Endpoint Category | Base URL | Purpose |
|-------------------|----------|---------|
| **Authentication** | `/api/auth/` | Phone OTP, user management |
| **Events** | `/api/events/` | Event CRUD operations |
| **Attendances** | `/api/attendances/` | Check-in/check-out |
| **Payments** | `/api/payments/` | Payment processing |
| **Health** | `/api/health` | System health check |

### Access Points
- **FastAPI Swagger UI**: `http://localhost:8000/api/docs`
- **Django Admin**: `http://localhost:8000/admin/`
- **API Root**: `http://localhost:8000/api/`
- **Flower Monitoring**: `http://localhost:5555`

### Authentication System
**📋 Complete authentication documentation, flowcharts, and API examples:**
**[📱 users/docs/PHONE_AUTHENTICATION.md](./users/docs/PHONE_AUTHENTICATION.md)**

#### Authentication Flow
1. **Phone Registration** → **OTP Verification** → **Profile Completion** → **JWT Token**
2. **Lead Tracking** → **User Conversion** → **Profile Management** → **Event Participation**

## 🚀 Getting Started

### Project Setup Guide
**📋 For step-by-step setup instructions, see:**
**[🚀 docs/INSTALLATION.md](./docs/INSTALLATION.md)**

### First Steps
1. **Environment Setup**: Configure `.env` file with credentials
2. **Docker Setup**: Build and start all services
3. **Database Setup**: Run migrations and create superuser
4. **API Testing**: Test endpoints via Swagger UI
5. **Authentication Flow**: Test phone OTP system

## 🎯 Development Workflow

### Code Organization
| Layer | Technology | Purpose | Location |
|-------|------------|---------|----------|
| **Models** | Django ORM | Database schema | `*/models.py` |
| **Serializers** | DRF | Data validation | `*/serializers/` |
| **Views** | Django Views | Web interface | `*/views/` |
| **API Routes** | FastAPI | Mobile API | `api/routers/` |
| **Tests** | Pytest/Django | Test coverage | `tests/` |
| **Documentation** | Markdown | Module docs | `*/docs/` |

### Testing Strategy
| Test Type | Framework | Coverage | Location |
|-----------|-----------|----------|----------|
| **Unit Tests** | Django TestCase | Models, serializers | `tests/django/` |
| **API Tests** | FastAPI TestClient | Endpoints | `tests/fastapi/` |
| **Integration Tests** | Pytest | Cross-module | `tests/` |
| **Coverage** | Coverage.py | Code metrics | Reports |

### Deployment Process
1. **Development** → **Testing** → **Staging** → **Production**
2. **Docker Build** → **Database Migration** → **Service Deployment** → **Health Check**
3. **Monitoring** → **Logging** → **Performance** → **Maintenance**

### Contributing Guidelines
1. **Branch Strategy**: `feature/` → `staging` → `main`
2. **Code Standards**: PEP 8, type hints, documentation
3. **Testing**: Comprehensive test coverage required
4. **Documentation**: Update relevant documentation
5. **Review Process**: Code review before merge

## 📚 Module Documentation

### Documentation Structure
This project follows a modular documentation structure where each module maintains its own comprehensive documentation:

### 🏗️ Core Infrastructure
- **[docs/README.md](./docs/README.md)** - Global documentation hub
- **[docs/ARCHITECTURE_OVERVIEW.md](./docs/ARCHITECTURE_OVERVIEW.md)** - Comprehensive technical architecture documentation
- **[docs/DOCKER_GUIDE.md](./docs/DOCKER_GUIDE.md)** - Docker setup and development guide
- **[docs/erd_doc_fixed.md](./docs/erd_doc_fixed.md)** - Database schema and ERD diagrams

### 👥 User Management
- **[users/docs/README.md](./users/docs/README.md)** - User module overview and features
- **[users/docs/PHONE_AUTHENTICATION.md](./users/docs/PHONE_AUTHENTICATION.md)** - Complete phone authentication system documentation

### 🎪 Event Management
- **[events/docs/README.md](./events/docs/README.md)** - Event creation, management, and user interactions

### ✅ Attendance Tracking
- **[attendances/docs/README.md](./attendances/docs/README.md)** - Check-in/check-out processes and ticket validation

### 💳 Payment Processing
- **[payments/docs/README.md](./payments/docs/README.md)** - Payment processing, orders, and transaction management

### 🔍 Audit & Compliance
- **[audit/docs/README.md](./audit/docs/README.md)** - System auditing, logging, and compliance tracking

### 📢 Notifications
- **[notifications/docs/README.md](./notifications/docs/README.md)** - User notifications and communication system

### 🚀 API Documentation
- **[api/docs/README.md](./api/docs/README.md)** - FastAPI endpoints and mobile API documentation

## 🔧 Development Guides

### Quick Setup
1. **Clone Repository**: `git clone https://github.com/LOOPINX-CIRCLE/LoopinBackend.git`
2. **Follow Setup Guide**: See [docs/INSTALLATION.md](./docs/INSTALLATION.md) for detailed instructions
3. **Start Development**: Use Docker commands from [docs/DOCKER_GUIDE.md](./docs/DOCKER_GUIDE.md)

---

## 🏆 System Overview

This project structure is designed for **long-term maintainability** and **team collaboration**. By following these conventions consistently, you ensure:

- **Scalability**: Easy to add new features without architectural debt
- **Clarity**: New developers can quickly understand the codebase
- **Maintainability**: Clean separation makes debugging and updates easier
- **Quality**: Structured testing and coding standards prevent technical debt
- **Security**: Phone authentication with proper OTP validation
- **Lead Management**: Comprehensive user tracking and conversion

**Remember**: Consistency is key. Follow this structured approach religiously to maintain a professional, enterprise-grade codebase that scales with your team and requirements.

Happy coding! 🚀
