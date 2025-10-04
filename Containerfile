# Multi-stage Containerfile for epicstar

# Stage 1: Builder
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 syncuser && \
    mkdir -p /tmp/git-sync && \
    chown -R syncuser:syncuser /app /tmp/git-sync

# Copy Python dependencies from builder
COPY --from=builder /root/.local /home/syncuser/.local

# Copy application code
COPY --chown=syncuser:syncuser app/ /app/app/
COPY --chown=syncuser:syncuser alembic/ /app/alembic/
COPY --chown=syncuser:syncuser alembic.ini /app/

# Set environment variables
ENV PATH=/home/syncuser/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER syncuser

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Run application
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

