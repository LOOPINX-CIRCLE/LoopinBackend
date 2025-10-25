# API Module Documentation

## Overview
The API module provides FastAPI-based endpoints for mobile applications, offering high-performance API access to all platform features.

## Architecture
- **FastAPI Framework**: High-performance async API framework
- **Django Integration**: Seamless integration with Django ORM and models
- **JWT Authentication**: Secure token-based authentication
- **CORS Support**: Cross-origin resource sharing for mobile clients

## Router Structure

### Authentication Router (`api/routers/auth.py`)
- **Purpose**: Legacy authentication endpoints
- **Status**: Deprecated in favor of phone authentication
- **Endpoints**: Basic auth, token management

### Users Router (`api/routers/users.py`)
- **Purpose**: User management endpoints
- **Endpoints**: User profiles, preferences, management

### Health Check (`api/health.py`)
- **Purpose**: System health monitoring
- **Endpoints**: Service status, database connectivity, Redis status

## API Features
- **Async Support**: Full async/await support for high performance
- **Automatic Documentation**: Swagger UI at `/api/docs`
- **Request Validation**: Pydantic-based request/response validation
- **Error Handling**: Comprehensive error handling and responses
- **Rate Limiting**: Built-in rate limiting for API protection

## Authentication Flow
1. **Phone Authentication**: Primary authentication via phone + OTP
2. **JWT Tokens**: Secure token-based session management
3. **Token Refresh**: Automatic token refresh mechanisms
4. **Logout**: Secure token invalidation

## Integration Points
- **Django Models**: Direct integration with Django ORM
- **Users Module**: Phone authentication and user management
- **All Modules**: API access to all platform features
- **Audit Module**: API request/response logging
