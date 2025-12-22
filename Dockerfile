# =============================================================================
# Multi-stage Dockerfile for Board of One (bo1)
# Optimized for both development and production deployments
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base image with uv installed
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    mv /root/.local/bin/uv /usr/local/bin/ && \
    mv /root/.local/bin/uvx /usr/local/bin/

# Set Python to unbuffered mode for better logging in containers
ENV PYTHONUNBUFFERED=1

# -----------------------------------------------------------------------------
# Stage 2: Dependencies (cached layer)
# -----------------------------------------------------------------------------
FROM base AS dependencies

WORKDIR /app

# Copy only dependency files (for layer caching)
COPY pyproject.toml .
COPY uv.lock .
COPY README.md .

# Copy source code (needed for editable install)
COPY bo1/ ./bo1/

# Copy alembic configuration and migrations
COPY alembic.ini ./
COPY migrations/ ./migrations/

# Copy scripts (for seed_personas.py)
COPY scripts/ ./scripts/

# Create virtual environment and install dependencies using lock file
RUN uv venv && \
    uv sync --frozen

# Activate virtual environment for subsequent stages
ENV PATH="/app/.venv/bin:$PATH"

# -----------------------------------------------------------------------------
# Stage 3: Development image (with dev dependencies)
# -----------------------------------------------------------------------------
FROM dependencies AS development

WORKDIR /app

# Install dev dependencies using lock file
RUN uv sync --frozen --extra dev

# Copy source code (will be overridden by volume mount in docker-compose)
COPY bo1/ ./bo1/
COPY backend/ ./backend/
COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/

# Create exports directory
RUN mkdir -p /app/exports

# Expose port for future web interface (v2)
EXPOSE 8000

# Default command: interactive shell for development
CMD ["/bin/bash"]

# -----------------------------------------------------------------------------
# Stage 4: Production image (minimal, no dev dependencies)
# -----------------------------------------------------------------------------
FROM dependencies AS production

WORKDIR /app

# Copy only application code (not dev files)
COPY bo1/ ./bo1/
COPY backend/ ./backend/
COPY alembic.ini ./
COPY migrations/ ./migrations/
COPY scripts/ ./scripts/

# Create exports directory
RUN mkdir -p /app/exports

# Run as non-root user for security
RUN useradd -m -u 1000 bo1user && \
    chown -R bo1user:bo1user /app
USER bo1user

# Health check (will be more sophisticated in v2 with web API)
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.exit(0)"

# Default command: run the application
CMD ["python", "-m", "bo1.main"]

# -----------------------------------------------------------------------------
# Stage 5: Testing image (for CI/CD)
# -----------------------------------------------------------------------------
FROM development AS testing

WORKDIR /app

# Copy test files
COPY tests/ ./tests/
COPY backend/ ./backend/

# Run tests
CMD ["pytest", "-v", "--tb=short"]
