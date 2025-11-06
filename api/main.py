"""
FastAPI main application initialization.
"""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from django.conf import settings

from api.routers import users, hosts, events
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

# Create FastAPI app
app = FastAPI(
    title="Loopin Backend API",
    description="Mobile backend with Django + FastAPI",
    version="1.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json",
)

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
app.include_router(users.router, prefix="/users", tags=["users"])
app.include_router(hosts.router, prefix="/hosts", tags=["Host Leads"])
app.include_router(events.router)

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint for API."""
    return {
        "message": "Welcome to Loopin Backend API",
        "version": "1.0.0",
        "docs": "/api/docs"
    }

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "loopin-backend",
        "version": "1.0.0"
    }
