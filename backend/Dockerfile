# =============================================================================
# Backend Dockerfile for Board of One FastAPI Service
# =============================================================================

FROM python:3.12-slim AS base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
# curl: required for healthcheck probes
# build-essential/g++: required for native extensions (e.g., phik from ydata-profiling)
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app

# Copy dependency files and README (needed by pyproject.toml)
# Note: Build context is the repo root, so paths are relative to root
COPY pyproject.toml ./
COPY README.md ./
COPY uv.lock ./

# Copy source code (needed for local package build during uv sync)
COPY bo1/ /app/bo1/

# Install Python dependencies (including local bo1 package)
RUN uv sync --frozen

# =============================================================================
# Development Stage
# =============================================================================
FROM base AS development

# Copy application code
COPY backend/ /app/backend/
COPY bo1/ /app/bo1/
COPY scripts/ /app/scripts/

# Copy alembic configuration and migrations
COPY alembic.ini /app/alembic.ini
COPY migrations/ /app/migrations/

# Expose port
EXPOSE 8000

# Run with hot reload
CMD ["uv", "run", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Production Stage
# =============================================================================
FROM base AS production

# Security: Run as non-root user
RUN useradd -m -u 1000 appuser

# Build metadata - set via docker build --build-arg
ARG BUILD_TIMESTAMP=""
ARG GIT_COMMIT=""

# Write build info to file (read by health endpoint)
RUN echo "{\"build_timestamp\": \"${BUILD_TIMESTAMP:-$(date -u +%Y-%m-%dT%H:%M:%SZ)}\", \"git_commit\": \"${GIT_COMMIT:-unknown}\"}" > /app/build_info.json

# Copy application code
COPY backend/ /app/backend/
COPY bo1/ /app/bo1/
COPY scripts/ /app/scripts/

# Copy alembic configuration and migrations
COPY alembic.ini /app/alembic.ini
COPY migrations/ /app/migrations/

# Fix ownership for non-root user
RUN chown -R appuser:appuser /app

# Expose port
EXPOSE 8000

# Switch to non-root user
USER appuser

# Run without hot reload
CMD ["uv", "run", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
