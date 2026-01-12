"""
Production-Grade ASGI Configuration for Loopin Backend

This module integrates Django and FastAPI into a unified ASGI application
with enterprise-level features including:
- Environment-aware configuration
- Comprehensive error handling
- Structured logging
- Health monitoring
- Static/media file serving
- Graceful degradation
- Security best practices

Architecture:
- FastAPI mounted at /api for API endpoints
- Django mounted at /django for admin interface
- Static files served at /django/static/ and /static/
- Media files served at /django/media/ and /media/

Author: CTO Team
Version: 2.0.0
"""

import os
import sys
import logging
import traceback
from pathlib import Path
from typing import Optional
from contextlib import contextmanager

from django.core.asgi import get_asgi_application
from django.conf import settings
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.wsgi import WSGIMiddleware
from starlette.middleware.gzip import GZipMiddleware

# Configure logging before any imports that might log
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Determine environment
ENVIRONMENT = os.environ.get('ENVIRONMENT', os.environ.get('DJANGO_SETTINGS_MODULE', '').split('.')[-1] if '.' in os.environ.get('DJANGO_SETTINGS_MODULE', '') else 'dev')
IS_PRODUCTION = ENVIRONMENT == 'production'
IS_DEVELOPMENT = not IS_PRODUCTION

# Set Django settings module - prioritize explicit setting, fallback to environment
if 'DJANGO_SETTINGS_MODULE' not in os.environ:
    if IS_PRODUCTION:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loopin_backend.settings.prod')
    else:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loopin_backend.settings.dev')

logger.info(f"🚀 Initializing ASGI application in {ENVIRONMENT} environment")
logger.info(f"   Django settings: {os.environ.get('DJANGO_SETTINGS_MODULE')}")

# Initialize Django ASGI application early
try:
    django_asgi_app = get_asgi_application()
    logger.info("✅ Django ASGI application initialized successfully")
except Exception as e:
    logger.critical(f"❌ Failed to initialize Django ASGI application: {e}", exc_info=True)
    sys.exit(1)

# Import Django settings after initialization
try:
    from django.conf import settings
    logger.info(f"✅ Django settings loaded (DEBUG={settings.DEBUG})")
except Exception as e:
    logger.critical(f"❌ Failed to load Django settings: {e}", exc_info=True)
    sys.exit(1)


@contextmanager
def safe_import(module_name: str, description: str):
    """Context manager for safe module imports with error handling."""
    try:
        module = __import__(module_name, fromlist=[module_name.split('.')[-1]])
        logger.info(f"✅ {description} imported successfully")
        yield module
    except ImportError as e:
        logger.warning(f"⚠️  Could not import {description}: {e}")
        yield None
    except Exception as e:
        logger.error(f"❌ Error importing {description}: {e}", exc_info=True)
        yield None


# Import routers directly to include in main app (instead of mounting)
# This ensures all routes appear in the OpenAPI schema
try:
    from api.routers import hosts, events, events_attendance, payouts, payments, notifications
    logger.info("✅ API routers imported successfully")
except Exception as e:
    logger.critical(f"❌ Failed to import API routers: {e}", exc_info=True)
    sys.exit(1)

# Get Django WSGI application for admin interface
try:
    from django.core.wsgi import get_wsgi_application
    django_wsgi_app = get_wsgi_application()
    logger.info("✅ Django WSGI application initialized successfully")
except Exception as e:
    logger.critical(f"❌ Failed to initialize Django WSGI application: {e}", exc_info=True)
    sys.exit(1)


def configure_static_files(app: FastAPI, static_root: Path, mount_path: str = "/django/static") -> bool:
    """
    Configure static file serving with comprehensive error handling.
    
    Args:
        app: FastAPI application instance
        static_root: Path to static files directory
        mount_path: Path to mount static files at
        
    Returns:
        True if successfully mounted, False otherwise
    """
    try:
        # Ensure directory exists
        static_root = Path(static_root).resolve()
        static_root.mkdir(parents=True, exist_ok=True)
        
        if not static_root.exists():
            logger.warning(f"⚠️  Static files directory does not exist: {static_root}")
            return False
        
        # Check if directory has content (optional check)
        if not any(static_root.iterdir()):
            logger.warning(f"⚠️  Static files directory is empty: {static_root}")
            # Still mount it - files might be added later
        
        # Mount static files
        app.mount(mount_path, StaticFiles(directory=str(static_root)), name=f"static-{mount_path.replace('/', '-')}")
        logger.info(f"✅ Static files mounted at {mount_path} from {static_root}")
        return True
        
    except RuntimeError as e:
        if "already mounted" in str(e).lower():
            logger.warning(f"⚠️  Static files already mounted at {mount_path}: {e}")
        else:
            logger.error(f"❌ Runtime error mounting static files at {mount_path}: {e}")
        return False
    except PermissionError as e:
        logger.error(f"❌ Permission denied accessing static files directory {static_root}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error mounting static files at {mount_path}: {e}", exc_info=True)
        return False


def configure_media_files(app: FastAPI, media_root: Path, mount_path: str = "/django/media") -> bool:
    """
    Configure media file serving with comprehensive error handling.
    
    Args:
        app: FastAPI application instance
        media_root: Path to media files directory
        mount_path: Path to mount media files at
        
    Returns:
        True if successfully mounted, False otherwise
    """
    try:
        # Ensure directory exists
        media_root = Path(media_root).resolve()
        media_root.mkdir(parents=True, exist_ok=True)
        
        if not media_root.exists():
            logger.warning(f"⚠️  Media files directory does not exist: {media_root}")
            return False
        
        # Mount media files
        app.mount(mount_path, StaticFiles(directory=str(media_root)), name=f"media-{mount_path.replace('/', '-')}")
        logger.info(f"✅ Media files mounted at {mount_path} from {media_root}")
        return True
        
    except RuntimeError as e:
        if "already mounted" in str(e).lower():
            logger.warning(f"⚠️  Media files already mounted at {mount_path}: {e}")
        else:
            logger.error(f"❌ Runtime error mounting media files at {mount_path}: {e}")
        return False
    except PermissionError as e:
        logger.error(f"❌ Permission denied accessing media files directory {media_root}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Unexpected error mounting media files at {mount_path}: {e}", exc_info=True)
        return False


# Create main FastAPI application
app = FastAPI(
    title="Loopin Backend",
    description="Production-grade mobile backend combining Django and FastAPI",
    version="2.0.0",
    docs_url="/api/docs" if IS_DEVELOPMENT else None,  # Disable docs in production
    openapi_url="/api/openapi.json" if IS_DEVELOPMENT else None,  # Disable OpenAPI schema in production
    redoc_url="/api/redoc" if IS_DEVELOPMENT else None,  # Disable ReDoc in production
)

# Add CORS middleware (from fastapi_app)
try:
    from fastapi.middleware.cors import CORSMiddleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("✅ CORS middleware added")
except Exception as e:
    logger.warning(f"⚠️  Failed to add CORS middleware: {e}")

# Add compression middleware for production
if IS_PRODUCTION:
    app.add_middleware(GZipMiddleware, minimum_size=1000)

# Add trusted host middleware in production
if IS_PRODUCTION and hasattr(settings, 'ALLOWED_HOSTS'):
    allowed_hosts = settings.ALLOWED_HOSTS
    if allowed_hosts and '*' not in allowed_hosts:
        app.add_middleware(TrustedHostMiddleware, allowed_hosts=allowed_hosts)
        logger.info(f"✅ TrustedHostMiddleware enabled for hosts: {allowed_hosts}")


# Global exception handler for unhandled errors
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled errors."""
    error_id = os.urandom(8).hex()
    logger.error(
        f"Unhandled exception [{error_id}]: {type(exc).__name__}: {str(exc)}",
        exc_info=True,
        extra={
            'error_id': error_id,
            'path': request.url.path,
            'method': request.method,
        }
    )
    
    # Don't expose internal errors in production
    if IS_PRODUCTION:
        error_message = "An internal server error occurred. Please contact support."
        error_details = {"error_id": error_id}
    else:
        error_message = f"Unhandled exception: {type(exc).__name__}: {str(exc)}"
        error_details = {
            "error_id": error_id,
            "type": type(exc).__name__,
            "message": str(exc),
            "traceback": traceback.format_exc().split('\n') if settings.DEBUG else None,
        }
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": error_message,
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": error_details,
        }
    )


# Add exception handlers from fastapi_app
try:
    from core.exceptions import (
        LoopinBaseException,
        ValidationError,
        AuthenticationError,
        AuthorizationError,
        NotFoundError,
        ConflictError,
        RateLimitError,
        ExternalServiceError,
        DatabaseError,
        BusinessLogicError,
    )
    
    @app.exception_handler(LoopinBaseException)
    async def loopin_exception_handler(request: Request, exc: LoopinBaseException):
        """Handle custom Loopin exceptions and convert to HTTP responses"""
        status_mapping = {
            ValidationError: status.HTTP_400_BAD_REQUEST,
            AuthenticationError: status.HTTP_401_UNAUTHORIZED,
            AuthorizationError: status.HTTP_403_FORBIDDEN,
            NotFoundError: status.HTTP_404_NOT_FOUND,
            ConflictError: status.HTTP_409_CONFLICT,
            RateLimitError: status.HTTP_429_TOO_MANY_REQUESTS,
            ExternalServiceError: status.HTTP_502_BAD_GATEWAY,
            DatabaseError: status.HTTP_503_SERVICE_UNAVAILABLE,
            BusinessLogicError: status.HTTP_400_BAD_REQUEST,
        }
        status_code = status_mapping.get(type(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)
        return JSONResponse(
            status_code=status_code,
            content={
                "success": False,
                "error": exc.message,
                "error_code": exc.code or type(exc).__name__,
                "details": exc.details,
            }
        )
    logger.info("✅ Loopin exception handlers added")
except Exception as e:
    logger.warning(f"⚠️  Failed to add Loopin exception handlers: {e}")


# Include all API routers with /api prefix
# This ensures all routes appear in the OpenAPI schema
# Note: Routers that already have prefixes (like /events, /payouts) will be 
# concatenated with /api, so /events becomes /api/events
# Users router removed - redundant/incomplete endpoints
# Use /api/auth/profile (GET/PUT) instead for user profile management
# try:
#     app.include_router(users.router, prefix="/api/users", tags=["users"])
#     logger.info("✅ Users router included")
# except Exception as e:
#     logger.error(f"❌ Failed to include users router: {e}")

try:
    app.include_router(hosts.router, prefix="/api/hosts", tags=["Host Leads"])
    logger.info("✅ Host Leads router included")
except Exception as e:
    logger.error(f"❌ Failed to include hosts router: {e}")

try:
    app.include_router(events.router, prefix="/api", tags=["events"])
    logger.info("✅ Events router included")
except Exception as e:
    logger.error(f"❌ Failed to include events router: {e}")

try:
    app.include_router(events_attendance.router, prefix="/api", tags=["events"])
    logger.info("✅ Events Attendance router included")
except Exception as e:
    logger.error(f"❌ Failed to include events attendance router: {e}")

try:
    app.include_router(payouts.router, prefix="/api", tags=["payouts"])
    logger.info("✅ Payouts router included")
except Exception as e:
    logger.error(f"❌ Failed to include payouts router: {e}")

try:
    app.include_router(payments.router, prefix="/api", tags=["payments"])
    logger.info("✅ Payments router included")
except Exception as e:
    logger.error(f"❌ Failed to include payments router: {e}")

try:
    app.include_router(notifications.router, prefix="/api", tags=["notifications"])
    logger.info("✅ Notifications router included")
except Exception as e:
    logger.error(f"❌ Failed to include notifications router: {e}")

# Import phone auth router after Django is set up
with safe_import('users.auth_router', 'Phone Authentication router') as auth_router_module:
    if auth_router_module:
        try:
            router = getattr(auth_router_module, 'router', None)
            if router:
                app.include_router(router, prefix="/api", tags=["Phone Authentication"])
                logger.info("✅ Phone Authentication router registered successfully")
            else:
                logger.warning("⚠️  Phone Authentication router module found but 'router' attribute missing")
        except Exception as e:
            logger.error(f"❌ Failed to register Phone Authentication router: {e}", exc_info=True)

# Mount Django WSGI app at /django for admin interface
app.mount("/django", WSGIMiddleware(django_wsgi_app))
logger.info("✅ Django WSGI application mounted at /django")

# Configure static files
if hasattr(settings, 'STATIC_ROOT'):
    static_root = settings.STATIC_ROOT
    # Mount at both paths for compatibility
    configure_static_files(app, static_root, "/django/static")
    if IS_DEVELOPMENT:
        configure_static_files(app, static_root, "/static")
else:
    logger.warning("⚠️  STATIC_ROOT not configured in Django settings")

# Configure media files
if hasattr(settings, 'MEDIA_ROOT'):
    media_root = settings.MEDIA_ROOT
    # Mount at both paths for compatibility
    configure_media_files(app, media_root, "/django/media")
    if IS_DEVELOPMENT:
        configure_media_files(app, media_root, "/media")
else:
    logger.warning("⚠️  MEDIA_ROOT not configured in Django settings")


# API root endpoint
@app.get("/api", operation_id="api_root")
@app.get("/api/", operation_id="api_root_slash")
async def api_root():
    """API root endpoint."""
    return {
        "message": "Welcome to Loopin Backend API",
        "version": "2.0.0",
        "docs": "/api/docs" if IS_DEVELOPMENT else None,
    }

# API health check endpoint (for Docker health checks and monitoring)
@app.get("/api/health", operation_id="api_health_check")
@app.get("/api/health/", operation_id="api_health_check_slash")
async def api_health_check():
    """API health check endpoint for Docker and monitoring."""
    return {
        "status": "healthy",
        "service": "loopin-backend",
        "version": "2.0.0"
    }

# Root endpoint with comprehensive information
@app.get("/", operation_id="root_asgi")
async def root(request: Request):
    """
    Root endpoint providing information about available services.
    Includes environment-aware information.
    """
    response_data = {
        "message": "Welcome to Loopin Backend",
        "version": "2.0.0",
        "environment": ENVIRONMENT,
        "services": {
            "api": "/api/",
            "admin": "/django/admin/",
        },
    }
    
    # Add docs endpoint only in development
    if IS_DEVELOPMENT:
        response_data["services"]["docs"] = "/api/docs"
        response_data["debug"] = True
    
    return response_data


# Health check endpoint
@app.get("/health", operation_id="health_check_asgi")
@app.get("/health/")
async def health_check():
    """
    Comprehensive health check endpoint for monitoring and load balancers.
    Returns detailed status of all critical services.
    """
    health_status = {
        "status": "healthy",
        "service": "loopin-backend",
        "version": "2.0.0",
        "environment": ENVIRONMENT,
        "services": {},
        "checks": {}
    }
    
    overall_status = "healthy"
    
    # Check Django
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status["services"]["django"] = "healthy"
        health_status["checks"]["database"] = "connected"
    except Exception as e:
        health_status["services"]["django"] = "unhealthy"
        health_status["checks"]["database"] = f"error: {str(e)}"
        overall_status = "unhealthy"
    
    # Check cache/Redis (if configured)
    try:
        from django.core.cache import cache
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
        health_status["checks"]["cache"] = "connected"
    except Exception as e:
        health_status["checks"]["cache"] = f"error: {str(e)}"
        if IS_PRODUCTION:
            overall_status = "degraded"
    
    # Check static files
    if hasattr(settings, 'STATIC_ROOT'):
        static_root = Path(settings.STATIC_ROOT)
        health_status["checks"]["static_files"] = "accessible" if static_root.exists() else "missing"
    else:
        health_status["checks"]["static_files"] = "not_configured"
    
    health_status["status"] = overall_status
    
    # Return appropriate HTTP status
    if overall_status == "healthy":
        status_code = status.HTTP_200_OK
    elif overall_status == "degraded":
        status_code = status.HTTP_200_OK  # Still operational
    else:
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return JSONResponse(content=health_status, status_code=status_code)


# Startup event
@app.on_event("startup")
async def startup_event():
    """Application startup event with comprehensive logging."""
    logger.info("=" * 80)
    logger.info(f"🚀 Loopin Backend ASGI Application Starting Up")
    logger.info(f"   Environment: {ENVIRONMENT}")
    logger.info(f"   Django DEBUG: {settings.DEBUG}")
    logger.info(f"   Production Mode: {IS_PRODUCTION}")
    logger.info("=" * 80)


# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event with cleanup logging."""
    logger.info("=" * 80)
    logger.info("🛑 Loopin Backend ASGI Application Shutting Down")
    logger.info("=" * 80)


# Set the application for ASGI server
application = app

logger.info("✅ ASGI application configuration completed successfully")
