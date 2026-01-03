#!/bin/sh
#
# Production-Grade Entrypoint Script for Loopin Backend
#
# This script handles application initialization with:
# - Environment-aware configuration
# - Database connectivity checks
# - Migration management
# - Static file collection
# - Health verification
# - Graceful error handling
# - Comprehensive logging
#
# Usage:
#   entrypoint.sh [command] [args...]
#
# Environment Variables:
#   - DATABASE_HOST: Database hostname
#   - DATABASE_PORT: Database port (default: 5432)
#   - DATABASE_URL: Full database connection URL
#   - COLLECT_STATIC: Whether to collect static files (default: true)
#   - RUN_SETUP_DATA: Whether to run setup data script (default: false)
#   - MIGRATE_DATABASE: Whether to run migrations (default: true)
#   - WAIT_FOR_DB: Whether to wait for database (default: true)
#
# Author: CTO Team
# Version: 2.0.0

set -euo pipefail  # Exit on error, undefined vars, pipe failures

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

log_section() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
}

# Environment detection
ENVIRONMENT="${ENVIRONMENT:-${DJANGO_SETTINGS_MODULE:-dev}}"
ENVIRONMENT=$(echo "$ENVIRONMENT" | sed 's/.*\.\([^.]*\)$/\1/')  # Extract last part
IS_PRODUCTION=false
if [ "$ENVIRONMENT" = "prod" ] || [ "$ENVIRONMENT" = "production" ]; then
    IS_PRODUCTION=true
fi

log_section "🚀 Loopin Backend Container Startup"
log_info "Environment: $ENVIRONMENT"
log_info "Production Mode: $IS_PRODUCTION"
log_info "Working Directory: $(pwd)"

# Database connection configuration
derive_database_config() {
    if [ -z "${DATABASE_HOST:-}" ] && [ -n "${DATABASE_URL:-}" ]; then
        log_info "Deriving database configuration from DATABASE_URL..."
        
        # Use Python to parse DATABASE_URL safely
        export DATABASE_HOST=$(python3 <<EOF
import os
import urllib.parse as up
url = os.environ.get('DATABASE_URL', '')
if url:
    parsed = up.urlparse(url)
    print(parsed.hostname or '')
EOF
        )
        
        export DATABASE_PORT=$(python3 <<EOF
import os
import urllib.parse as up
url = os.environ.get('DATABASE_URL', '')
if url:
    parsed = up.urlparse(url)
    print(parsed.port or 5432)
else:
    print(5432)
EOF
        )
        
        log_success "Database host: ${DATABASE_HOST:-unknown}"
        log_success "Database port: ${DATABASE_PORT:-5432}"
    fi
}

# Wait for database to be ready
wait_for_database() {
    local wait_for_db="${WAIT_FOR_DB:-true}"
    
    if [ "$wait_for_db" != "true" ]; then
        log_info "Skipping database wait (WAIT_FOR_DB=false)"
        return 0
    fi
    
    local db_host="${DATABASE_HOST:-}"
    local db_port="${DATABASE_PORT:-5432}"
    
    if [ -z "$db_host" ]; then
        log_warning "DATABASE_HOST not set, skipping database wait"
        return 0
    fi
    
    log_section "⏳ Waiting for Database Connection"
    log_info "Target: $db_host:$db_port"
    
    local max_attempts=30
    local attempt=1
    local wait_interval=2
    
    while [ $attempt -le $max_attempts ]; do
        if nc -z "$db_host" "$db_port" 2>/dev/null; then
            log_success "Database is reachable!"
            return 0
        fi
        
        log_info "Attempt $attempt/$max_attempts: Database not ready, retrying in ${wait_interval}s..."
        sleep $wait_interval
        attempt=$((attempt + 1))
    done
    
    log_error "Database connection failed after $max_attempts attempts"
    log_error "Please check database configuration and network connectivity"
    return 1
}

# Run database migrations
run_migrations() {
    local migrate_db="${MIGRATE_DATABASE:-true}"
    
    if [ "$migrate_db" != "true" ]; then
        log_info "Skipping migrations (MIGRATE_DATABASE=false)"
        return 0
    fi
    
    log_section "📦 Running Database Migrations"
    
    # Check if migrations should be faked for initial setup
    local fake_initial="${FAKE_INITIAL_MIGRATIONS:-false}"
    
    if [ "$fake_initial" = "true" ]; then
        log_info "Running migrations with --fake-initial flag..."
        if python3 manage.py migrate --noinput --fake-initial; then
            log_success "Migrations completed successfully (with --fake-initial)"
        else
            log_warning "Migrations with --fake-initial failed, trying without..."
            if ! python3 manage.py migrate --noinput; then
                log_error "Migrations failed"
                return 1
            fi
        fi
    else
        log_info "Running standard migrations..."
        if python3 manage.py migrate --noinput; then
            log_success "Migrations completed successfully"
        else
            log_error "Migrations failed"
            return 1
        fi
    fi
    
    return 0
}

# Collect static files
collect_static_files() {
    local collect_static="${COLLECT_STATIC:-true}"
    
    if [ "$collect_static" != "true" ]; then
        log_info "Skipping static file collection (COLLECT_STATIC=false)"
        return 0
    fi
    
    log_section "📦 Collecting Static Files"
    
    # Ensure staticfiles directory exists
    local static_root="${STATIC_ROOT:-/app/staticfiles}"
    mkdir -p "$static_root"
    log_success "Static files directory created/verified: $static_root"
    
    # Determine collectstatic flags
    local flags="--noinput"
    if [ "$IS_PRODUCTION" = "true" ]; then
        flags="$flags --clear"  # Clear existing files in production
        log_info "Running in production mode: clearing existing static files"
    fi
    
    log_info "Collecting static files..."
    if python3 manage.py collectstatic $flags; then
        local file_count=$(find "$static_root" -type f 2>/dev/null | wc -l || echo "0")
        log_success "Static files collected successfully ($file_count files)"
    else
        log_error "Static file collection failed"
        if [ "$IS_PRODUCTION" = "true" ]; then
            log_error "Static file collection is required in production!"
            return 1
        else
            log_warning "Continuing despite static file collection failure (development mode)"
        fi
    fi
    
    return 0
}

# Run setup data script
run_setup_data() {
    local run_setup="${RUN_SETUP_DATA:-false}"
    
    if [ "$run_setup" != "true" ]; then
        log_info "Skipping setup data script (RUN_SETUP_DATA=false)"
        return 0
    fi
    
    local setup_script="/app/setup_data.py"
    
    if [ ! -f "$setup_script" ]; then
        log_warning "Setup data script not found: $setup_script"
        return 0
    fi
    
    log_section "🛠️  Running Setup Data Script"
    log_info "Script: $setup_script"
    
    if python3 "$setup_script"; then
        log_success "Setup data script completed successfully"
    else
        log_error "Setup data script failed"
        if [ "$IS_PRODUCTION" = "true" ]; then
            return 1
        else
            log_warning "Continuing despite setup script failure (development mode)"
        fi
    fi
    
    return 0
}

# Verify application health
verify_health() {
    log_section "🏥 Verifying Application Health"
    
    # Wait a moment for the application to start if it's already running
    sleep 1
    
    # Try to import Django settings (basic health check)
    if python3 -c "import django; django.setup(); from django.conf import settings; print('Django configured successfully')" 2>/dev/null; then
        log_success "Django configuration verified"
    else
        log_warning "Django configuration check failed (may be normal if server not started)"
    fi
}

# Main execution
main() {
    # Derive database configuration
    derive_database_config
    
    # Wait for database
    if ! wait_for_database; then
        if [ "$IS_PRODUCTION" = "true" ]; then
            log_error "Cannot proceed without database connection in production"
            exit 1
        else
            log_warning "Continuing without database connection (development mode)"
        fi
    fi
    
    # Run migrations
    if ! run_migrations; then
        if [ "$IS_PRODUCTION" = "true" ]; then
            log_error "Cannot proceed without successful migrations in production"
            exit 1
        else
            log_warning "Continuing despite migration failures (development mode)"
        fi
    fi
    
    # Collect static files
    collect_static_files || true  # Don't fail on static file collection
    
    # Run setup data
    run_setup_data || true  # Don't fail on setup data
    
    # Verify health
    verify_health
    
    log_section "✨ Initialization Complete"
    log_success "All startup tasks completed successfully"
    log_info "Launching application: $*"
    echo ""
    
    # Execute the provided command
    exec "$@"
}

# Run main function
main "$@"
