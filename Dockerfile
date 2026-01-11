# =============================================================================
# Little Research Lab - Production Dockerfile
# =============================================================================

FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    APP_HOME=/app \
    LRL_DATA_DIR=/data \
    LRL_DB_PATH=/data/lrl.db \
    LRL_FS_PATH=/data/filestore \
    FLET_SERVER_PORT=8080

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
# All versions are pinned in pyproject.toml to ensure compatibility
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[dev]" || pip install --no-cache-dir .

# Copy application code
COPY src/ src/
COPY rules.yaml .
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
    CMD curl -f http://localhost:8080/ || exit 1

# Run the Flet app in web server mode
# host=0.0.0.0 required for container networking
CMD ["python", "-c", "import flet as ft; from src.ui.main import main; ft.app(target=main, port=8080, host='0.0.0.0')"]
