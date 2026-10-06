# ============================================================================
# AgroSense Café — FastAPI Application Dockerfile
# File: /docker/fastapi/Dockerfile
# ============================================================================

FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies and uv for fast, reliable package management
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_SYSTEM_PYTHON=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv binary directly from official image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy project workspace definitions and lockfile
COPY pyproject.toml uv.lock* ./
COPY apps/api/pyproject.toml ./apps/api/

# Install dependencies into system python
RUN uv pip install --system -r apps/api/pyproject.toml || \
    uv pip install --system fastapi uvicorn[standard] pydantic-settings alembic psycopg2-binary

# Final runtime image
FROM python:3.11-slim AS runner

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Install runtime dependencies (e.g. netcat/curl for health checks, libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    netcat-openbsd \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copy installed packages from builder stage
COPY --from=builder /usr/local /usr/local

# Copy application source code
COPY apps/api ./apps/api
COPY . .

# Copy entrypoint script and ensure executable permissions
COPY docker/fastapi/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Security: run as non-root user
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/entrypoint.sh"]
