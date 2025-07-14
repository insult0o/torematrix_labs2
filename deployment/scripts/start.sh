#!/bin/bash
# TORE Matrix Labs V3 - Production Startup Script

set -euo pipefail

# Configuration
export TOREMATRIX_ENV="${TOREMATRIX_ENV:-production}"
export TOREMATRIX_LOG_LEVEL="${TOREMATRIX_LOG_LEVEL:-INFO}"
export TOREMATRIX_CONFIG_PATH="${TOREMATRIX_CONFIG_PATH:-/app/config}"
export TOREMATRIX_DATA_PATH="${TOREMATRIX_DATA_PATH:-/app/data}"
export TOREMATRIX_LOGS_PATH="${TOREMATRIX_LOGS_PATH:-/app/logs}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING: $1${NC}"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR: $1${NC}"
}

# Trap function for graceful shutdown
cleanup() {
    log "Received shutdown signal, cleaning up..."
    
    # Kill background processes
    if [[ -n "${METRICS_PID:-}" ]]; then
        kill $METRICS_PID 2>/dev/null || true
    fi
    
    if [[ -n "${MAIN_PID:-}" ]]; then
        kill $MAIN_PID 2>/dev/null || true
        wait $MAIN_PID 2>/dev/null || true
    fi
    
    log "Cleanup completed"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Pre-flight checks
log "Starting TORE Matrix Labs V3 Pipeline..."
log "Environment: $TOREMATRIX_ENV"
log "Log Level: $TOREMATRIX_LOG_LEVEL"

# Check required directories
for dir in "$TOREMATRIX_CONFIG_PATH" "$TOREMATRIX_DATA_PATH" "$TOREMATRIX_LOGS_PATH"; do
    if [[ ! -d "$dir" ]]; then
        log "Creating directory: $dir"
        mkdir -p "$dir"
    fi
done

# Check Python environment
if ! python --version &>/dev/null; then
    error "Python not found!"
    exit 1
fi

log "Python version: $(python --version)"

# Check required environment variables
required_vars=("POSTGRES_HOST" "POSTGRES_DB" "POSTGRES_USER" "POSTGRES_PASSWORD")
for var in "${required_vars[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        error "Required environment variable $var is not set"
        exit 1
    fi
done

# Wait for dependencies
log "Waiting for dependencies..."

# Wait for PostgreSQL
log "Waiting for PostgreSQL..."
timeout=60
count=0
while ! pg_isready -h "$POSTGRES_HOST" -p "${POSTGRES_PORT:-5432}" -U "$POSTGRES_USER" -d "$POSTGRES_DB" &>/dev/null; do
    if [[ $count -ge $timeout ]]; then
        error "PostgreSQL is not available after $timeout seconds"
        exit 1
    fi
    sleep 1
    ((count++))
done
log "PostgreSQL is ready"

# Wait for Redis (if configured)
if [[ -n "${REDIS_HOST:-}" ]]; then
    log "Waiting for Redis..."
    count=0
    while ! redis-cli -h "$REDIS_HOST" -p "${REDIS_PORT:-6379}" ping &>/dev/null; do
        if [[ $count -ge $timeout ]]; then
            error "Redis is not available after $timeout seconds"
            exit 1
        fi
        sleep 1
        ((count++))
    done
    log "Redis is ready"
fi

# Database migrations (if needed)
log "Running database migrations..."
if python -c "from torematrix.core.database import run_migrations; run_migrations()" 2>/dev/null; then
    log "Database migrations completed"
else
    warn "Database migrations failed or not available"
fi

# Start metrics server in background (if Prometheus enabled)
if [[ "${PROMETHEUS_ENABLED:-false}" == "true" ]]; then
    log "Starting Prometheus metrics server on port ${PROMETHEUS_PORT:-9090}..."
    python -m torematrix.monitoring.metrics_server \
        --port "${PROMETHEUS_PORT:-9090}" \
        --host "0.0.0.0" &
    METRICS_PID=$!
    log "Metrics server started with PID $METRICS_PID"
fi

# Create configuration file if it doesn't exist
config_file="$TOREMATRIX_CONFIG_PATH/pipeline.yml"
if [[ ! -f "$config_file" ]]; then
    log "Creating default configuration file: $config_file"
    cat > "$config_file" << EOF
pipeline:
  name: "production_pipeline"
  stages:
    - name: "validation"
      type: "validator"
      processor: "validation_processor"
      dependencies: []
    - name: "extraction"
      type: "processor" 
      processor: "unstructured_processor"
      dependencies: ["validation"]
    - name: "metadata"
      type: "processor"
      processor: "metadata_extractor"
      dependencies: ["extraction"]

workers:
  async_workers: ${ASYNC_WORKERS:-4}
  thread_workers: ${THREAD_WORKERS:-2}
  max_queue_size: 1000
  default_timeout: 300.0

resources:
  max_cpu_percent: ${MAX_CPU_PERCENT:-80}
  max_memory_percent: ${MAX_MEMORY_PERCENT:-75}

monitoring:
  enabled: true
  metrics_interval: 60.0

unstructured:
  api_url: "${UNSTRUCTURED_API_URL:-}"
  api_key: "${UNSTRUCTURED_API_KEY:-}"
EOF
fi

# Health check function
health_check() {
    local max_attempts=30
    local attempt=1
    
    log "Performing health checks..."
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -sf "http://localhost:8000/health" &>/dev/null; then
            log "Health check passed"
            return 0
        fi
        
        log "Health check attempt $attempt/$max_attempts failed, retrying..."
        sleep 2
        ((attempt++))
    done
    
    error "Health checks failed after $max_attempts attempts"
    return 1
}

# Start main application
log "Starting main application..."
python -m torematrix.main \
    --config "$config_file" \
    --host "0.0.0.0" \
    --port 8000 \
    --log-level "$TOREMATRIX_LOG_LEVEL" \
    --data-path "$TOREMATRIX_DATA_PATH" \
    --logs-path "$TOREMATRIX_LOGS_PATH" &

MAIN_PID=$!
log "Main application started with PID $MAIN_PID"

# Wait a moment for startup
sleep 5

# Perform health checks
if ! health_check; then
    error "Application failed health checks"
    cleanup
    exit 1
fi

log "TORE Matrix Labs V3 Pipeline is ready!"
log "API available at: http://localhost:8000"
if [[ "${PROMETHEUS_ENABLED:-false}" == "true" ]]; then
    log "Metrics available at: http://localhost:${PROMETHEUS_PORT:-9090}/metrics"
fi

# Keep the script running and monitor the main process
while kill -0 $MAIN_PID 2>/dev/null; do
    sleep 10
    
    # Optional: Perform periodic health checks
    if [[ $((SECONDS % 300)) -eq 0 ]]; then  # Every 5 minutes
        if ! curl -sf "http://localhost:8000/health" &>/dev/null; then
            warn "Periodic health check failed"
        fi
    fi
done

# If we get here, the main process has exited
error "Main application process has exited unexpectedly"
cleanup
exit 1