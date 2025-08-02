# Multi-stage Dockerfile for Social Media Reports System
# QA-Engineer Implementation - Production-ready containerization

# Stage 1: Frontend Build
FROM node:20-alpine AS frontend-builder

WORKDIR /app/frontend

# Copy frontend package files
COPY social-media-dashboard/package*.json ./

# Install frontend dependencies
RUN npm ci --only=production

# Copy frontend source code
COPY social-media-dashboard/ ./

# Build frontend for production
RUN npm run build

# Stage 2: Python Dependencies
FROM python:3.11-slim AS python-deps

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    libffi-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Stage 3: Production Image
FROM python:3.11-slim AS production

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    FLASK_ENV=production \
    FLASK_APP=main.py

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r appuser \
    && useradd -r -g appuser appuser

# Copy virtual environment from python-deps stage
COPY --from=python-deps /opt/venv /opt/venv

# Create application directory
WORKDIR /app

# Copy backend source code
COPY src/ ./src/
COPY *.py ./
COPY *.md ./
COPY *.txt ./

# Copy frontend build from frontend-builder stage
COPY --from=frontend-builder /app/frontend/dist ./src/static/

# Create necessary directories
RUN mkdir -p /app/reports /app/logs /app/uploads && \
    chown -R appuser:appuser /app

# Copy configuration files
COPY docker/entrypoint.sh /entrypoint.sh
COPY docker/healthcheck.py /healthcheck.py

# Make scripts executable
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER appuser

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python /healthcheck.py

# Set entrypoint
ENTRYPOINT ["/entrypoint.sh"]

# Default command
CMD ["python", "src/main.py"]

