# Use Python 3.12 as base image (better compatibility)
FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=loopin_backend.settings.dev
ENV PYTHONPATH=/app

# Set work directory
WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        postgresql-client \
        build-essential \
        libpq-dev \
        netcat-traditional \
        curl \
        git \
        vim \
        htop \
    && rm -rf /var/lib/apt/lists/*

# Upgrade pip to latest version
RUN pip install --upgrade pip

# Install Python dependencies
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . /app/

# Create necessary directories
RUN mkdir -p /app/staticfiles /app/media /app/logs

# Set proper permissions
RUN chmod -R 755 /app

# Run database migrations and setup
RUN python3 manage.py migrate
RUN python3 manage.py collectstatic --noinput

# Copy and run setup script
COPY setup_data.py /app/setup_data.py
RUN python3 setup_data.py

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Development startup script - Use ASGI server for FastAPI integration
CMD ["python3", "-m", "uvicorn", "loopin_backend.asgi:application", "--host", "0.0.0.0", "--port", "8000", "--reload"]
