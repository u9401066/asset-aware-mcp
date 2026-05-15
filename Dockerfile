# syntax=docker/dockerfile:1.7
# ============================================================================
# Asset-Aware MCP ??Production Dockerfile (multi-stage)
# ============================================================================
# Usage:
#   docker build -t asset-aware-mcp .
#   docker run -i --rm \
#     -v ./data:/app/data \
#     -e ENABLE_LIGHTRAG=false \
#     asset-aware-mcp
# ============================================================================

# Stage 1: Builder ??install dependencies
FROM python:3.12-slim-bookworm AS builder

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv

WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src/ ./src/

# Install locked runtime deps first, then the local project without re-resolving.
# Keep this step compatible with Docker legacy builder hosts used in release smoke.
RUN uv export --frozen --no-dev --no-emit-project --format requirements-txt -o requirements.txt \
    && uv pip install --system -r requirements.txt \
    && uv pip install --system --no-deps "."

# Stage 2: Runtime
FROM python:3.12-slim-bookworm AS runtime

# Security: non-root user
RUN groupadd -r mcp && useradd -r -g mcp -d /app -s /sbin/nologin mcp

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create data directory owned by mcp user
RUN mkdir -p /app/data && chown -R mcp:mcp /app

# Environment defaults
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DATA_DIR=/app/data \
    ENABLE_LIGHTRAG=false \
    LOG_LEVEL=INFO

USER mcp

# Health metadata
LABEL maintainer="u9401066@gap.kmu.edu.tw" \
      version="0.6.34" \
      description="Asset-Aware Medical RAG MCP Server"

ENTRYPOINT ["asset-aware-mcp"]
