# Deployment Guide

## Overview

This guide covers deploying the epicstar using Podman containers in development, staging, and production environments.

## Prerequisites

- Podman 4.0+ installed
- PostgreSQL 15+ (or use containerized version)
- GitHub App configured (see [github-app-setup.md](github-app-setup.md))
- OneDev instance accessible
- Domain name with SSL certificate (production)

## Quick Start

```bash
# Clone repository
git clone https://github.com/your-username/epicstar.git
cd epicstar

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
nano .env

# Build container
podman build -t epicstar:latest .

# Run with Podman Compose
podman-compose up -d

# Check logs
podman logs -f epicstar

# Verify health
curl http://localhost:8000/health
```

## Environment Setup

### 1. Environment Variables

Create a `.env` file with the following variables:

```bash
# Application
ENVIRONMENT=production  # development, staging, production
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
APP_NAME=epicstar
APP_VERSION=1.0.0

# GitHub App Configuration
GITHUB_APP_ID=123456
GITHUB_WEBHOOK_SECRET=your-webhook-secret-here
GITHUB_PRIVATE_KEY_PATH=/app/secrets/github-app-key.pem
# OR use inline key (base64 encoded)
# GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"

# OneDev Configuration
ONEDEV_API_URL=https://onedev.example.com
ONEDEV_API_TOKEN=your-onedev-api-token
ONEDEV_REPO_PREFIX=github-  # Optional: prefix for created repos
ONEDEV_CONFLICT_STRATEGY=use_existing  # use_existing, append_timestamp, fail

# Database Configuration
DATABASE_URL=postgresql://syncuser:password@db:5432/syncdb
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Git Operations
GIT_CLONE_TIMEOUT=1800  # 30 minutes
GIT_PUSH_TIMEOUT=1800
GIT_TEMP_DIR=/tmp/git-sync
GIT_CLONE_DEPTH=0  # 0 for full clone, >0 for shallow clone

# Security
WEBHOOK_RATE_LIMIT=100  # requests per minute
API_RATE_LIMIT=60  # requests per minute

# Monitoring (Optional)
PROMETHEUS_ENABLED=true
PROMETHEUS_PORT=9090

# Retry Configuration
MAX_RETRIES=3
RETRY_BACKOFF_FACTOR=2  # Exponential backoff multiplier
RETRY_MIN_WAIT=4  # Minimum wait time in seconds
RETRY_MAX_WAIT=60  # Maximum wait time in seconds
```

### 2. Secrets Management

**Option A: Environment Variables** (Simple, for development)
```bash
export GITHUB_WEBHOOK_SECRET="abc123..."
export ONEDEV_API_TOKEN="token123..."
```

**Option B: Docker Secrets** (Recommended for production)
```bash
# Create secrets
echo "your-webhook-secret" | podman secret create github_webhook_secret -
echo "your-onedev-token" | podman secret create onedev_api_token -

# Reference in Podman Compose
# See docker-compose.yml example below
```

**Option C: External Secret Manager** (Enterprise)
- HashiCorp Vault
- AWS Secrets Manager
- Azure Key Vault
- Google Secret Manager

## Container Configuration

### Containerfile

```dockerfile
# Multi-stage build for minimal image size
FROM python:3.11-slim AS builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app/logs /tmp/git-sync && \
    chown -R appuser:appuser /app /tmp/git-sync

# Copy Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Set PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Podman Compose Configuration

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Containerfile
    image: epicstar:${VERSION:-latest}
    container_name: epicstar
    restart: unless-stopped
    ports:
      - "${APP_PORT:-8000}:8000"
    environment:
      - ENVIRONMENT=${ENVIRONMENT:-production}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - GITHUB_APP_ID=${GITHUB_APP_ID}
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
      - ONEDEV_API_URL=${ONEDEV_API_URL}
      - ONEDEV_API_TOKEN=${ONEDEV_API_TOKEN}
      - DATABASE_URL=postgresql://${DB_USER}:${DB_PASSWORD}@db:5432/${DB_NAME}
    volumes:
      - ./logs:/app/logs
      - ./secrets:/app/secrets:ro
      - git-temp:/tmp/git-sync
    depends_on:
      db:
        condition: service_healthy
    networks:
      - sync-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 10s

  db:
    image: postgres:15-alpine
    container_name: epicstar-db
    restart: unless-stopped
    environment:
      - POSTGRES_DB=${DB_NAME:-syncdb}
      - POSTGRES_USER=${DB_USER:-syncuser}
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_INITDB_ARGS=--encoding=UTF-8 --lc-collate=C --lc-ctype=C
    volumes:
      - pgdata:/var/lib/postgresql/data
      - ./init-db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - sync-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${DB_USER:-syncuser}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Optional: Prometheus for monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: epicstar-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    networks:
      - sync-network
    profiles:
      - monitoring

  # Optional: Grafana for dashboards
  grafana:
    image: grafana/grafana:latest
    container_name: epicstar-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD:-admin}
    volumes:
      - grafana-data:/var/lib/grafana
      - ./grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    networks:
      - sync-network
    profiles:
      - monitoring

networks:
  sync-network:
    driver: bridge

volumes:
  pgdata:
  git-temp:
  prometheus-data:
  grafana-data:
```

## Deployment Procedures

### Development Deployment

```bash
# Set environment
export ENVIRONMENT=development

# Use SQLite for development
export DATABASE_URL=sqlite:///./dev.db

# Start only app (no database container)
podman-compose up app

# Or with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Staging Deployment

```bash
# Set environment
export ENVIRONMENT=staging

# Build with staging tag
podman build -t epicstar:staging .

# Start all services
podman-compose -f docker-compose.staging.yml up -d

# Run database migrations
podman exec epicstar alembic upgrade head

# Verify
curl https://staging.example.com/health
```

### Production Deployment

```bash
# Set environment
export ENVIRONMENT=production

# Build with version tag
export VERSION=1.0.0
podman build -t epicstar:${VERSION} .
podman tag epicstar:${VERSION} epicstar:latest

# Start all services
podman-compose up -d

# Run database migrations
podman exec epicstar alembic upgrade head

# Verify health
curl https://sync.example.com/health

# Check logs
podman logs -f epicstar

# Monitor metrics
curl https://sync.example.com/metrics
```

## Reverse Proxy Configuration

### Nginx

```nginx
# /etc/nginx/sites-available/epicstar
upstream sync_backend {
    server localhost:8000;
}

server {
    listen 80;
    server_name sync.example.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name sync.example.com;

    ssl_certificate /etc/letsencrypt/live/sync.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/sync.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-Frame-Options "DENY" always;

    # Webhook endpoint
    location /webhooks/github {
        proxy_pass http://sync_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeout for long-running syncs
        proxy_read_timeout 300s;
        proxy_connect_timeout 75s;
    }

    # Health check
    location /health {
        proxy_pass http://sync_backend;
        access_log off;
    }

    # Metrics (restrict access)
    location /metrics {
        proxy_pass http://sync_backend;
        allow 10.0.0.0/8;  # Internal network only
        deny all;
    }
}
```

### Traefik

```yaml
# docker-compose.yml with Traefik
services:
  app:
    # ... existing config ...
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.sync.rule=Host(`sync.example.com`)"
      - "traefik.http.routers.sync.entrypoints=websecure"
      - "traefik.http.routers.sync.tls.certresolver=letsencrypt"
      - "traefik.http.services.sync.loadbalancer.server.port=8000"
      
  traefik:
    image: traefik:v2.10
    command:
      - "--api.insecure=true"
      - "--providers.docker=true"
      - "--entrypoints.web.address=:80"
      - "--entrypoints.websecure.address=:443"
      - "--certificatesresolvers.letsencrypt.acme.email=admin@example.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.httpchallenge.entrypoint=web"
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - letsencrypt:/letsencrypt
```

## Update Procedures

### Rolling Update

```bash
# 1. Pull latest code
git pull origin main

# 2. Build new image with version tag
export NEW_VERSION=1.1.0
podman build -t epicstar:${NEW_VERSION} .

# 3. Backup database
podman exec epicstar-db pg_dump -U syncuser syncdb > backup_$(date +%Y%m%d).sql

# 4. Run database migrations (if any)
podman run --rm \
  --network sync-network \
  -e DATABASE_URL=postgresql://syncuser:password@db:5432/syncdb \
  epicstar:${NEW_VERSION} \
  alembic upgrade head

# 5. Update docker-compose.yml with new version
sed -i "s/VERSION=.*/VERSION=${NEW_VERSION}/" .env

# 6. Recreate containers
podman-compose up -d --force-recreate app

# 7. Verify health
curl https://sync.example.com/health

# 8. Monitor logs for errors
podman logs -f epicstar --since 5m

# 9. If successful, tag as latest
podman tag epicstar:${NEW_VERSION} epicstar:latest
```

### Rollback Procedure

```bash
# 1. Identify previous version
export PREVIOUS_VERSION=1.0.0

# 2. Update .env
sed -i "s/VERSION=.*/VERSION=${PREVIOUS_VERSION}/" .env

# 3. Rollback database (if needed)
podman exec -i epicstar-db psql -U syncuser syncdb < backup_20251004.sql

# 4. Recreate containers with previous version
podman-compose up -d --force-recreate app

# 5. Verify
curl https://sync.example.com/health
```

## Monitoring and Maintenance

### Health Checks

```bash
# Application health
curl https://sync.example.com/health

# Expected response:
# {"status": "healthy", "database": "connected", "version": "1.0.0"}

# Database health
podman exec epicstar-db pg_isready -U syncuser

# Container status
podman ps
podman stats epicstar
```

### Log Management

```bash
# View logs
podman logs epicstar
podman logs epicstar-db

# Follow logs
podman logs -f epicstar

# Filter logs by level
podman logs epicstar 2>&1 | grep ERROR

# Export logs
podman logs epicstar > app.log 2>&1
```

### Database Backup

```bash
# Manual backup
podman exec epicstar-db pg_dump -U syncuser syncdb > backup.sql

# Automated daily backup (cron)
0 2 * * * podman exec epicstar-db pg_dump -U syncuser syncdb > /backups/syncdb_$(date +\%Y\%m\%d).sql

# Restore from backup
podman exec -i epicstar-db psql -U syncuser syncdb < backup.sql
```

## Troubleshooting

### Container won't start

```bash
# Check logs
podman logs epicstar

# Check environment variables
podman exec epicstar env

# Verify configuration
podman exec epicstar python -c "from app.config import settings; print(settings)"
```

### Database connection issues

```bash
# Test database connection
podman exec epicstar-db psql -U syncuser -d syncdb -c "SELECT 1;"

# Check network
podman network inspect sync-network

# Verify DATABASE_URL
echo $DATABASE_URL
```

### Webhook not received

```bash
# Check if port is exposed
podman port epicstar

# Test webhook endpoint
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'

# Check nginx/reverse proxy logs
tail -f /var/log/nginx/access.log
```

---

**Last Updated**: 2025-10-04  
**Version**: 1.0

