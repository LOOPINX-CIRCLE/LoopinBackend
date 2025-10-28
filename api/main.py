"""
FastAPI main application initialization.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from django.conf import settings

from api.routers import auth, users, hosts

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

# Include routers
app.include_router(auth.router, prefix="/auth", tags=["Authentication"])
app.include_router(users.router, prefix="/users", tags=["Users"])
app.include_router(hosts.router, prefix="/hosts", tags=["Host Leads"])

# Phone auth router will be imported in asgi.py after Django is set up

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
