# Health check endpoint for Docker
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.db import connection
from django.core.cache import cache
import redis
import os

@csrf_exempt
@require_http_methods(["GET"])
def health_check(request):
    """
    Health check endpoint for Docker containers
    Returns status of all critical services
    """
    health_status = {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "services": {}
    }
    
    # Check database connection
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        health_status["services"]["database"] = "healthy"
    except Exception as e:
        health_status["services"]["database"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Redis connection
    try:
        cache.set('health_check', 'ok', 10)
        cache.get('health_check')
        health_status["services"]["redis"] = "healthy"
    except Exception as e:
        health_status["services"]["redis"] = f"unhealthy: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Celery (if configured)
    try:
        celery_broker = os.getenv('CELERY_BROKER_URL')
        if celery_broker:
            # Simple Redis check for Celery broker
            redis_client = redis.from_url(celery_broker)
            redis_client.ping()
            health_status["services"]["celery"] = "healthy"
        else:
            health_status["services"]["celery"] = "not_configured"
    except Exception as e:
        health_status["services"]["celery"] = f"unhealthy: {str(e)}"
    
    # Return appropriate HTTP status
    if health_status["status"] == "healthy":
        return JsonResponse(health_status, status=200)
    else:
        return JsonResponse(health_status, status=503)
