"""
ASGI config for loopin_backend project.

It exposes the ASGI callable as a module-level variable named ``application``.
This configuration integrates Django and FastAPI in a clean, modular way.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os
from django.core.asgi import get_asgi_application
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.wsgi import WSGIMiddleware

# Set Django settings module - use dev by default
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'loopin_backend.settings')

# Initialize Django ASGI application early to ensure Django is set up
django_asgi_app = get_asgi_application()

# Import Django settings and FastAPI app after Django is set up
from django.conf import settings
from api.main import app as fastapi_app

# Import phone auth router after Django is set up
try:
    from users.auth_router import router as auth_router
    fastapi_app.include_router(auth_router, tags=["Phone Authentication"])
    print("Phone authentication router loaded successfully")
except ImportError as e:
    print(f"Warning: Could not import phone auth router: {e}")

# Get Django WSGI application for admin interface
from django.core.wsgi import get_wsgi_application
django_wsgi_app = get_wsgi_application()

# Create the main application that combines both Django and FastAPI
app = FastAPI(
    title="Loopin Backend",
    description="Mobile backend combining Django and FastAPI",
    version="1.0.0",
    docs_url=None,
    openapi_url=None,
)

# Mount FastAPI app at /api
app.mount("/api", fastapi_app)

# Mount Django WSGI app at /django for admin interface
app.mount("/django", WSGIMiddleware(django_wsgi_app))

# Mount static files in development
if settings.DEBUG and hasattr(settings, 'STATIC_ROOT'):
    try:
        app.mount("/static", StaticFiles(directory=settings.STATIC_ROOT), name="static")
    except RuntimeError:
        # Static files directory doesn't exist yet
        pass

# Mount media files in development
if settings.DEBUG and hasattr(settings, 'MEDIA_ROOT'):
    try:
        app.mount("/media", StaticFiles(directory=settings.MEDIA_ROOT), name="media")
    except RuntimeError:
        # Media files directory doesn't exist yet
        pass

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint providing information about available services."""
    return {
        "message": "Welcome to Loopin Backend",
        "services": {
            "api": "/api/",
            "admin": "/django/admin/",
            "docs": "/api/docs"
        },
        "version": "1.0.0"
    }

# Set the application for ASGI server
application = app