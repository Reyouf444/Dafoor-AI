# ── Stage 1: Build dependencies ─────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build tools for any compiled packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies into an isolated location
COPY backend/requirements.txt ./requirements.txt
RUN pip install --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Runtime image ───────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /app

# Copy installed packages from builder stage
COPY --from=builder /install /usr/local

# Copy application source
COPY backend/ ./backend/
COPY static/  ./static/

# Create the data directory and set ownership
RUN mkdir -p backend/data/pdfs \
    && chown -R appuser:appuser /app

# Switch to non-root user
USER appuser

# Cloud Run injects PORT env variable (default 8080)
ENV PORT=8080

# Expose the port
EXPOSE 8080

# Health check — Cloud Run uses this
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:${PORT}/health')" || exit 1

# Use exec form to properly handle signals
CMD exec uvicorn backend.main:app \
        --host 0.0.0.0 \
        --port ${PORT} \
        --workers 2 \
        --log-level info
