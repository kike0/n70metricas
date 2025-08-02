#!/bin/bash
# Docker Entrypoint Script for Social Media Reports System
# QA-Engineer Implementation - Production-ready container startup

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to wait for database
wait_for_db() {
    if [ -n "$DATABASE_URL" ]; then
        log "Waiting for database to be ready..."
        
        # Extract database connection details from DATABASE_URL
        # Format: postgresql://user:password@host:port/database
        if [[ $DATABASE_URL =~ postgresql://([^:]+):([^@]+)@([^:]+):([^/]+)/(.+) ]]; then
            DB_USER="${BASH_REMATCH[1]}"
            DB_PASS="${BASH_REMATCH[2]}"
            DB_HOST="${BASH_REMATCH[3]}"
            DB_PORT="${BASH_REMATCH[4]}"
            DB_NAME="${BASH_REMATCH[5]}"
            
            # Wait for PostgreSQL to be ready
            until PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -c '\q' 2>/dev/null; do
                log "Database is unavailable - sleeping"
                sleep 2
            done
            
            success "Database is ready!"
        else
            warn "Could not parse DATABASE_URL, skipping database wait"
        fi
    else
        warn "DATABASE_URL not set, skipping database wait"
    fi
}

# Function to wait for Redis
wait_for_redis() {
    if [ -n "$REDIS_URL" ]; then
        log "Waiting for Redis to be ready..."
        
        # Extract Redis connection details
        if [[ $REDIS_URL =~ redis://([^:]+):([^/]+)/(.+) ]]; then
            REDIS_HOST="${BASH_REMATCH[1]}"
            REDIS_PORT="${BASH_REMATCH[2]}"
            
            until redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping 2>/dev/null | grep -q PONG; do
                log "Redis is unavailable - sleeping"
                sleep 2
            done
            
            success "Redis is ready!"
        else
            warn "Could not parse REDIS_URL, skipping Redis wait"
        fi
    else
        warn "REDIS_URL not set, skipping Redis wait"
    fi
}

# Function to run database migrations
run_migrations() {
    log "Running database migrations..."
    
    if [ -f "src/database/migrate.py" ]; then
        python src/database/migrate.py
        success "Database migrations completed"
    else
        warn "Migration script not found, skipping migrations"
    fi
}

# Function to validate environment
validate_environment() {
    log "Validating environment configuration..."
    
    # Required environment variables
    REQUIRED_VARS=(
        "FLASK_ENV"
        "APIFY_API_TOKEN"
    )
    
    # Optional but recommended variables
    OPTIONAL_VARS=(
        "DATABASE_URL"
        "REDIS_URL"
        "SECRET_KEY"
        "JWT_SECRET_KEY"
    )
    
    # Check required variables
    for var in "${REQUIRED_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    # Check optional variables
    for var in "${OPTIONAL_VARS[@]}"; do
        if [ -z "${!var}" ]; then
            warn "Optional environment variable $var is not set"
        fi
    done
    
    success "Environment validation completed"
}

# Function to setup logging
setup_logging() {
    log "Setting up logging..."
    
    # Create logs directory if it doesn't exist
    mkdir -p /app/logs
    
    # Set log level based on environment
    if [ "$FLASK_ENV" = "production" ]; then
        export LOG_LEVEL="INFO"
    else
        export LOG_LEVEL="DEBUG"
    fi
    
    success "Logging configured (Level: $LOG_LEVEL)"
}

# Function to setup file permissions
setup_permissions() {
    log "Setting up file permissions..."
    
    # Ensure application user owns necessary directories
    chown -R appuser:appuser /app/reports /app/logs /app/uploads 2>/dev/null || true
    
    # Set proper permissions
    chmod 755 /app/reports /app/logs /app/uploads 2>/dev/null || true
    
    success "File permissions configured"
}

# Function to perform health check
health_check() {
    log "Performing initial health check..."
    
    # Check if the application can start
    python -c "
import sys
sys.path.insert(0, '/app/src')
try:
    from main import app
    print('✓ Application imports successfully')
except Exception as e:
    print(f'✗ Application import failed: {e}')
    sys.exit(1)
"
    
    if [ $? -eq 0 ]; then
        success "Health check passed"
    else
        error "Health check failed"
        exit 1
    fi
}

# Function to start application
start_application() {
    log "Starting Social Media Reports System..."
    
    # Change to application directory
    cd /app
    
    # Start the application based on environment
    if [ "$FLASK_ENV" = "production" ]; then
        log "Starting in production mode with Gunicorn..."
        exec gunicorn \
            --bind 0.0.0.0:5000 \
            --workers 4 \
            --worker-class gevent \
            --worker-connections 1000 \
            --max-requests 1000 \
            --max-requests-jitter 100 \
            --timeout 30 \
            --keep-alive 2 \
            --log-level info \
            --access-logfile /app/logs/access.log \
            --error-logfile /app/logs/error.log \
            --capture-output \
            --enable-stdio-inheritance \
            src.main:app
    else
        log "Starting in development mode..."
        exec python src/main.py
    fi
}

# Main execution
main() {
    log "Starting Social Media Reports System container..."
    
    # Validate environment
    validate_environment
    
    # Setup logging
    setup_logging
    
    # Setup file permissions
    setup_permissions
    
    # Wait for dependencies
    wait_for_db
    wait_for_redis
    
    # Run migrations
    run_migrations
    
    # Perform health check
    health_check
    
    # Start application
    start_application
}

# Handle signals for graceful shutdown
trap 'log "Received SIGTERM, shutting down gracefully..."; exit 0' TERM
trap 'log "Received SIGINT, shutting down gracefully..."; exit 0' INT

# Execute main function with all arguments
main "$@"

