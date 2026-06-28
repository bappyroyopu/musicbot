# ================================================================
# Multi-stage Dockerfile for Telegram Voice Chat Music Bot
# ================================================================
# Stage 1: Builder — install Python dependencies
# Stage 2: Runtime — minimal image with FFmpeg and bot code
# ================================================================

# ------- Stage 1: Builder ----------------------------------------
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libffi-dev \
    libssl-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir --prefix=/install -r requirements.txt

# ------- Stage 2: Runtime ----------------------------------------
FROM python:3.11-slim AS runtime

# Labels
LABEL maintainer="your@email.com"
LABEL description="Telegram Voice Chat Music Bot"
LABEL version="1.0.0"

# Install system dependencies:
#   - FFmpeg: audio processing
#   - yt-dlp: YouTube downloads (also installed via pip but system fallback)
#   - curl: health checks
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application code
COPY . .

# Create required directories
RUN mkdir -p storage/temp logs alembic/versions /tmp/music /tmp/music/logs

# Create non-root user for security
RUN useradd -m -u 1000 botuser \
    && chown -R botuser:botuser /app
USER botuser

# Health check — verify the API is responsive
# PORT defaults to 10000 (Render's default for web services)
HEALTHCHECK --interval=30s --timeout=10s --start-period=90s --retries=5 \
    CMD curl -f http://localhost:${PORT:-10000}/health || exit 1

# Expose the health check port (Render injects $PORT at runtime)
EXPOSE 10000

# Default command
CMD ["python", "main.py"]
