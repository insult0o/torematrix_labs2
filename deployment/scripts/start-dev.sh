#!/bin/bash
# TORE Matrix Labs V3 - Development Startup Script

set -euo pipefail

# Development configuration
export TOREMATRIX_ENV="development"
export TOREMATRIX_LOG_LEVEL="DEBUG"
export TOREMATRIX_CONFIG_PATH="${TOREMATRIX_CONFIG_PATH:-/app/config}"
export TOREMATRIX_DATA_PATH="${TOREMATRIX_DATA_PATH:-/app/data}"
export TOREMATRIX_LOGS_PATH="${TOREMATRIX_LOGS_PATH:-/app/logs}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

info() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')] INFO: $1${NC}"
}

# Trap function for graceful shutdown
cleanup() {
    log "Received shutdown signal, cleaning up development environment..."
    
    # Kill background processes
    jobs -p | xargs -r kill 2>/dev/null || true
    
    log "Development environment cleanup completed"
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Development startup
log "Starting TORE Matrix Labs V3 Development Environment..."
log "Environment: $TOREMATRIX_ENV"
log "Log Level: $TOREMATRIX_LOG_LEVEL"

# Check required directories
for dir in "$TOREMATRIX_CONFIG_PATH" "$TOREMATRIX_DATA_PATH" "$TOREMATRIX_LOGS_PATH"; do
    if [[ ! -d "$dir" ]]; then
        log "Creating directory: $dir"
        mkdir -p "$dir"
    fi
done

# Development-specific setup
log "Setting up development environment..."

# Install development dependencies if not already installed
if ! python -c "import pytest" &>/dev/null; then
    log "Installing development dependencies..."
    pip install -e ".[dev]"
fi

# Set up git hooks (if in a git repository)
if [[ -d ".git" ]]; then
    log "Setting up git hooks..."
    if [[ ! -f ".git/hooks/pre-commit" ]]; then
        cat > .git/hooks/pre-commit << 'EOF'
#!/bin/bash
# Run tests and linting before commit
python -m pytest tests/ --maxfail=1 -q
python -m black --check src/
python -m flake8 src/
EOF
        chmod +x .git/hooks/pre-commit
        log "Pre-commit hook installed"
    fi
fi

# Create development configuration
config_file="$TOREMATRIX_CONFIG_PATH/pipeline-dev.yml"
if [[ ! -f "$config_file" ]]; then
    log "Creating development configuration file: $config_file"
    cat > "$config_file" << EOF
pipeline:
  name: "development_pipeline"
  stages:
    - name: "validation"
      type: "validator"
      processor: "validation_processor"
      dependencies: []
      timeout: 30
    - name: "extraction"
      type: "processor"
      processor: "unstructured_processor"
      dependencies: ["validation"]
      timeout: 60
    - name: "metadata"
      type: "processor"
      processor: "metadata_extractor"
      dependencies: ["extraction"]
      timeout: 30

workers:
  async_workers: 2
  thread_workers: 1
  max_queue_size: 100
  default_timeout: 30.0

resources:
  max_cpu_percent: 70
  max_memory_percent: 60

monitoring:
  enabled: true
  metrics_interval: 30.0

unstructured:
  api_url: "${UNSTRUCTURED_API_URL:-}"
  api_key: "${UNSTRUCTURED_API_KEY:-}"

development:
  hot_reload: true
  debug_mode: true
  test_data_path: "/app/sample-documents"
  enable_profiling: true
EOF
fi

# Create sample test documents if they don't exist
sample_dir="/app/sample-documents"
if [[ ! -d "$sample_dir" ]]; then
    log "Creating sample documents directory..."
    mkdir -p "$sample_dir"
    
    # Create sample files
    cat > "$sample_dir/sample.txt" << EOF
This is a sample text document for testing the TORE Matrix processing pipeline.

It contains multiple paragraphs and different types of content to test various processing capabilities.

Features to test:
- Text extraction
- Metadata extraction
- Validation
- Quality assessment

This document should be processed successfully by the development environment.
EOF

    cat > "$sample_dir/README.md" << EOF
# Sample Documents

This directory contains sample documents for testing the TORE Matrix processing pipeline in development mode.

## Files

- \`sample.txt\` - Basic text document
- \`sample.pdf\` - PDF document (create manually)
- \`sample.docx\` - Word document (create manually)

## Usage

Use these documents to test the processing pipeline:

\`\`\`bash
curl -X POST http://localhost:8000/process \\
     -F "file=@sample.txt" \\
     -F "pipeline=development_pipeline"
\`\`\`
EOF
    
    log "Sample documents created in $sample_dir"
fi

# Start Jupyter notebook server in background
if command -v jupyter &>/dev/null; then
    log "Starting Jupyter notebook server on port 8888..."
    jupyter lab \
        --ip=0.0.0.0 \
        --port=8888 \
        --no-browser \
        --allow-root \
        --notebook-dir=/app \
        --NotebookApp.token='' \
        --NotebookApp.password='' &
    
    info "Jupyter Lab available at: http://localhost:8888"
fi

# Run initial tests
log "Running initial test suite..."
if python -m pytest tests/ -v --tb=short; then
    log "Initial tests passed"
else
    warn "Some initial tests failed - check output above"
fi

# Start file watcher for hot reload (if available)
if command -v watchdog &>/dev/null; then
    log "Starting file watcher for hot reload..."
    watchdog-reload \
        --patterns="*.py" \
        --ignore-patterns="*__pycache__*;*.pyc" \
        --recursive \
        --directory=/app/src \
        -- python -m torematrix.main \
            --config "$config_file" \
            --host "0.0.0.0" \
            --port 8000 \
            --log-level "$TOREMATRIX_LOG_LEVEL" \
            --data-path "$TOREMATRIX_DATA_PATH" \
            --logs-path "$TOREMATRIX_LOGS_PATH" \
            --dev-mode &
else
    # Start main application without hot reload
    log "Starting main application in development mode..."
    python -m torematrix.main \
        --config "$config_file" \
        --host "0.0.0.0" \
        --port 8000 \
        --log-level "$TOREMATRIX_LOG_LEVEL" \
        --data-path "$TOREMATRIX_DATA_PATH" \
        --logs-path "$TOREMATRIX_LOGS_PATH" \
        --dev-mode &
fi

MAIN_PID=$!
log "Main application started with PID $MAIN_PID"

# Wait for application to start
sleep 3

# Development health check
info "Performing development health checks..."
max_attempts=10
attempt=1

while [[ $attempt -le $max_attempts ]]; do
    if curl -sf "http://localhost:8000/health" &>/dev/null; then
        log "Development health check passed"
        break
    fi
    
    if [[ $attempt -eq $max_attempts ]]; then
        warn "Health checks failed - application may still be starting"
        break
    fi
    
    sleep 2
    ((attempt++))
done

# Development environment ready
log "🚀 TORE Matrix Labs V3 Development Environment Ready!"
echo ""
info "📋 Development Services:"
info "   API Server:     http://localhost:8000"
info "   Health Check:   http://localhost:8000/health"
info "   API Docs:       http://localhost:8000/docs"
info "   Metrics:        http://localhost:9090/metrics"
if command -v jupyter &>/dev/null; then
    info "   Jupyter Lab:    http://localhost:8888"
fi
echo ""
info "📁 Development Paths:"
info "   Config:         $TOREMATRIX_CONFIG_PATH"
info "   Data:           $TOREMATRIX_DATA_PATH"
info "   Logs:           $TOREMATRIX_LOGS_PATH"
info "   Sample Docs:    $sample_dir"
echo ""
info "🛠️  Development Commands:"
info "   Run Tests:      python -m pytest tests/"
info "   Lint Code:      python -m black src/ && python -m flake8 src/"
info "   Type Check:     python -m mypy src/"
info "   Shell Access:   docker exec -it torematrix-dev bash"
echo ""
info "📊 Sample API Call:"
info "   curl -X POST http://localhost:8000/process \\"
info "        -F \"file=@$sample_dir/sample.txt\" \\"
info "        -F \"pipeline=development_pipeline\""
echo ""

# Monitor and keep running
log "Monitoring development environment... (Ctrl+C to stop)"

# Keep the script running and monitor the main process
while kill -0 $MAIN_PID 2>/dev/null; do
    sleep 10
done

# If we get here, the main process has exited
warn "Main application process has exited"
cleanup
exit 0