# =============================================================================
# Little Research Lab - Production Dockerfile (FastAPI Backend)
# =============================================================================

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_HOME=/app \
    LAB_DATA_DIR=/data

WORKDIR $APP_HOME

# Install system dependencies
# - build-essential: for compiling Python packages
# - libffi-dev, libssl-dev: for cryptography (argon2)
# - fonts-dejavu: for matplotlib chart rendering
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    libssl-dev \
    fonts-dejavu \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency specification first (for Docker layer caching)
COPY pyproject.toml README.md ./

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[dev]" || pip install --no-cache-dir .

# Copy application code
COPY src/ src/
COPY rules.yaml .
COPY seed_db.py .
COPY migrations/ migrations/

# Create data directory (will be overridden by volume mount in production)
RUN mkdir -p /data/filestore /data/backups

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser && \
    chown -R appuser:appuser $APP_HOME /data

USER appuser

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run FastAPI with uvicorn
CMD ["uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
