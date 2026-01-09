"""
FastAPI main application initialization.
"""

import logging
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from django.conf import settings

from api.routers import users, hosts, events, events_attendance, payouts, payments, notifications
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

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Loopin Backend API",
    description="Mobile backend with Django + FastAPI",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

# Startup event to log loaded routers
@app.on_event("startup")
async def startup_event():
    """Log all loaded routers on application startup"""
    logger.info("=" * 60)
    logger.info("🚀 Loopin Backend API Starting Up")
    logger.info("=" * 60)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception Handlers
@app.exception_handler(LoopinBaseException)
async def loopin_exception_handler(request: Request, exc: LoopinBaseException):
    """Handle custom Loopin exceptions and convert to HTTP responses"""
    # Map exception types to HTTP status codes
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


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    import logging
    logger = logging.getLogger(__name__)
    logger.error(f"Unhandled exception: {type(exc).__name__}: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": "An unexpected error occurred. Please try again later.",
            "error_code": "INTERNAL_SERVER_ERROR",
            "details": {},
        }
    )

# Include routers
# Note: Legacy auth router (api/routers/auth.py) is deprecated in favor of phone authentication
# Phone auth router is registered in asgi.py after Django is set up
try:
    app.include_router(users.router, prefix="/users", tags=["users"])
    print("✅ Users router loaded successfully (prefix: /users)")
except Exception as e:
    print(f"❌ Failed to load users router: {e}")

try:
    app.include_router(hosts.router, prefix="/hosts", tags=["Host Leads"])
    print("✅ Host Leads router loaded successfully (prefix: /hosts)")
except Exception as e:
    print(f"❌ Failed to load host leads router: {e}")

try:
    app.include_router(events.router)
    print("✅ Events router loaded successfully (prefix: /events)")
except Exception as e:
    print(f"❌ Failed to load events router: {e}")

try:
    app.include_router(events_attendance.router)
    print("✅ Events Attendance router loaded successfully (prefix: /events)")
except Exception as e:
    print(f"❌ Failed to load events attendance router: {e}")

try:
    app.include_router(payouts.router)
    print("✅ Payouts router loaded successfully (prefix: /payouts)")
except Exception as e:
    print(f"❌ Failed to load payouts router: {e}")

try:
    app.include_router(payments.router)
    print("✅ Payments router loaded successfully (prefix: /payments)")
except Exception as e:
    print(f"❌ Failed to load payments router: {e}")

try:
    app.include_router(notifications.router)
    print("✅ Notifications router loaded successfully (prefix: /notifications)")
except Exception as e:
    print(f"❌ Failed to load notifications router: {e}")

# Log router summary after all routers are loaded
print("=" * 60)
print("📋 All routers loaded successfully!")
print("=" * 60)

# Root endpoint
@app.get("/", operation_id="root_api")
async def root():
    """Root endpoint for API."""
    return {
        "message": "Welcome to Loopin Backend API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }

# Health check endpoint
@app.get("/health", operation_id="health_check_api")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "loopin-backend",
        "version": "1.0.0"
    }