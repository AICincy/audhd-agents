# AuDHD Agents Runtime: Production Container
# Optimized for Cloud Run single-container deployment.
# AUDIT-FIX: P2-5 -- multi-stage build; P3-7 -- pin to patch version

FROM python:3.12.10-slim AS builder

WORKDIR /build

COPY . .
RUN pip install --no-cache-dir --prefix=/install .



FROM python:3.12.10-slim

WORKDIR /app

# System deps (curl for health checks)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
COPY . .

# Non-root user
RUN useradd -r -s /bin/false appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/healthz || exit 1

# Cloud Run uses PORT env var (default 8080)
ENV PORT=8080
EXPOSE ${PORT}

CMD ["uvicorn", "runtime.app:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--log-level", "info"]
