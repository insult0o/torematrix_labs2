# TORE Matrix Labs V3 - Processing Pipeline Docker Image
# Multi-stage build for optimized production image

# Build stage
FROM python:3.11-slim as builder

# Set build arguments
ARG PYTHON_VERSION=3.11
ARG BUILD_DATE
ARG VERSION=3.0.0

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements first for better caching
COPY requirements.txt requirements-dev.txt ./

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt && \
    pip install -r requirements-dev.txt

# Copy source code
COPY src/ /app/src/
COPY tests/ /app/tests/
COPY pyproject.toml setup.py /app/

# Set working directory
WORKDIR /app

# Install the package
RUN pip install -e .

# Production stage
FROM python:3.11-slim as production

# Set labels
LABEL maintainer="TORE Matrix Labs" \
      version="${VERSION}" \
      description="TORE Matrix V3 Document Processing Pipeline" \
      build-date="${BUILD_DATE}"

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    TOREMATRIX_CONFIG_PATH=/app/config \
    TOREMATRIX_DATA_PATH=/app/data \
    TOREMATRIX_LOGS_PATH=/app/logs

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    lsb-release \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r torematrix && \
    useradd -r -g torematrix -d /app -s /bin/bash torematrix

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY --from=builder /app /app

# Create necessary directories
RUN mkdir -p /app/config /app/data /app/logs /app/temp && \
    chown -R torematrix:torematrix /app

# Copy configuration files
COPY deployment/config/ /app/config/
COPY deployment/scripts/ /app/scripts/

# Make scripts executable
RUN chmod +x /app/scripts/*.sh

# Switch to non-root user
USER torematrix

# Set working directory
WORKDIR /app

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose ports
EXPOSE 8000 9090

# Default command
CMD ["/app/scripts/start.sh"]

# Development stage
FROM production as development

# Switch back to root for development tools
USER root

# Install development dependencies
RUN apt-get update && apt-get install -y \
    vim \
    htop \
    strace \
    tcpdump \
    && rm -rf /var/lib/apt/lists/*

# Install additional Python development tools
RUN pip install \
    jupyter \
    ipython \
    black \
    flake8 \
    mypy \
    pytest-cov \
    pytest-xdist

# Switch back to torematrix user
USER torematrix

# Override default command for development
CMD ["/app/scripts/start-dev.sh"]