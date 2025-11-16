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
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

WORKDIR /app

# Copy dependency files and README (needed by pyproject.toml)
COPY pyproject.toml uv.lock README.md ./

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

# Expose port
EXPOSE 8000

# Run with hot reload
CMD ["uv", "run", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# =============================================================================
# Production Stage
# =============================================================================
FROM base AS production

# Copy application code
COPY backend/ /app/backend/
COPY bo1/ /app/bo1/

# Expose port
EXPOSE 8000

# Run without hot reload
CMD ["uv", "run", "uvicorn", "backend.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
