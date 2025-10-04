# Podman Deployment Guide

## Prerequisites

- Podman installed
- Podman Compose installed
- GitHub App created and configured
- OneDev instance accessible

## Quick Start

### 1. Prepare Secrets

Create a `secrets` directory and add your GitHub App private key:

```bash
mkdir -p secrets
cp /path/to/your/github-app-key.pem secrets/
chmod 600 secrets/github-app-key.pem
```

### 2. Configure Environment

Copy the example environment file and configure it:

```bash
cp .env.example .env.production
```

Edit `.env.production` with your actual values:

```env
ENVIRONMENT=production
LOG_LEVEL=INFO

# GitHub App
GITHUB_APP_ID=your_app_id
GITHUB_WEBHOOK_SECRET=your_webhook_secret

# OneDev
ONEDEV_API_URL=https://your-onedev-instance.com
ONEDEV_API_TOKEN=your_onedev_token

# Database
DB_USER=syncuser
DB_PASSWORD=your_secure_password
DB_NAME=syncdb
```

### 3. Build and Run

```bash
# Build the container
podman-compose build

# Start services
podman-compose up -d

# Check logs
podman-compose logs -f app

# Check status
podman-compose ps
```

### 4. Run Database Migrations

```bash
podman-compose exec app alembic upgrade head
```

### 5. Verify Deployment

```bash
# Health check
curl http://localhost:8000/health

# Check API docs
open http://localhost:8000/docs
```

## Production Deployment

### Using Systemd

Create a systemd service file `/etc/systemd/system/github-onedev-sync.service`:

```ini
[Unit]
Description=GitHub-to-OneDev Sync Service
After=network.target

[Service]
Type=forking
User=your-user
WorkingDirectory=/path/to/epicstar
ExecStart=/usr/bin/podman-compose up -d
ExecStop=/usr/bin/podman-compose down
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable github-onedev-sync
sudo systemctl start github-onedev-sync
```

### Reverse Proxy (Nginx)

```nginx
server {
    listen 80;
    server_name sync.yourdomain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### SSL/TLS with Let's Encrypt

```bash
sudo certbot --nginx -d sync.yourdomain.com
```

## Maintenance

### View Logs

```bash
# All logs
podman-compose logs

# App logs only
podman-compose logs app

# Follow logs
podman-compose logs -f app
```

### Restart Services

```bash
podman-compose restart app
```

### Update Application

```bash
# Pull latest code
git pull origin main

# Rebuild and restart
podman-compose down
podman-compose build
podman-compose up -d

# Run migrations
podman-compose exec app alembic upgrade head
```

### Backup Database

```bash
podman-compose exec db pg_dump -U syncuser syncdb > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
podman-compose exec -T db psql -U syncuser syncdb < backup_20231004.sql
```

## Troubleshooting

### Container Won't Start

```bash
# Check logs
podman-compose logs app

# Check container status
podman ps -a

# Inspect container
podman inspect github-onedev-sync
```

### Database Connection Issues

```bash
# Check database is running
podman-compose ps db

# Test database connection
podman-compose exec db psql -U syncuser -d syncdb -c "SELECT 1"
```

### Permission Issues

```bash
# Fix ownership
sudo chown -R 1000:1000 secrets/
sudo chmod 600 secrets/github-app-key.pem
```

## Monitoring

### Health Checks

The container includes a built-in health check that runs every 30 seconds:

```bash
podman inspect github-onedev-sync | grep -A 10 Health
```

### Resource Usage

```bash
podman stats github-onedev-sync
```

## Security Best Practices

1. **Never commit secrets** - Use environment variables and secret files
2. **Use strong passwords** - Generate secure database passwords
3. **Limit network exposure** - Use reverse proxy with SSL/TLS
4. **Regular updates** - Keep containers and dependencies updated
5. **Monitor logs** - Set up log aggregation and monitoring
6. **Backup regularly** - Automate database backups

## Scaling

For high-volume deployments:

1. **Increase workers** - Set `WORKERS=4` in environment
2. **Use PostgreSQL connection pooling** - Configure `DATABASE_POOL_SIZE`
3. **Add load balancer** - Distribute traffic across multiple instances
4. **Monitor performance** - Use Prometheus metrics endpoint

