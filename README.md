# epicstar

Automatically sync starred GitHub repositories to your private OneDev instance.

## Overview

This service listens for GitHub star events via webhooks and automatically clones starred repositories to your OneDev Git server, creating a private backup of public repositories you find interesting.

## Features

- ✅ **Automatic Sync**: Star a repo on GitHub → Automatically cloned to OneDev
- ✅ **Webhook-Driven**: Real-time synchronization using GitHub App webhooks
- ✅ **Retry Logic**: Exponential backoff for failed operations
- ✅ **Monitoring**: Prometheus metrics and health checks
- ✅ **Database Tracking**: SQLite/PostgreSQL support for sync history
- ✅ **Containerized**: Ready for Podman/Docker deployment
- ✅ **Production-Ready**: Comprehensive logging, error handling, and testing

## Quick Start

### Prerequisites

- Python 3.11+
- GitHub App (see [GitHub App Setup](docs/setup/github-app-setup.md))
- OneDev instance with API access
- Podman or Docker (for containerized deployment)

### Installation

```bash
# Clone the repository
git clone https://github.com/studiozeroseven/epicstar.git
cd epicstar

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run database migrations
alembic upgrade head

# Start the service
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Docker/Podman Deployment

```bash
# Build and run with Podman Compose
podman-compose up -d

# Check logs
podman-compose logs -f app

# Health check
curl http://localhost:8000/health
```

## Configuration

Key environment variables:

```env
# GitHub App
GITHUB_APP_ID=your_app_id
GITHUB_WEBHOOK_SECRET=your_webhook_secret
GITHUB_PRIVATE_KEY_PATH=/path/to/private-key.pem

# OneDev
ONEDEV_API_URL=https://your-onedev-instance.com
ONEDEV_API_TOKEN=your_api_token

# Database
DATABASE_URL=sqlite:///./dev.db  # or postgresql://...
```

See [.env.example](.env.example) for all options.

## Documentation

- [Project Plan](docs/project-plan.md) - Complete development roadmap
- [Architecture](docs/architecture.md) - System design and diagrams
- [GitHub App Setup](docs/setup/github-app-setup.md) - Create and configure GitHub App
- [OneDev Setup](docs/setup/onedev-setup.md) - Configure OneDev integration
- [Deployment Guide](docs/deployment/podman-deployment.md) - Production deployment
- [API Documentation](docs/api/webhook-api.md) - Webhook API reference
- [Test Plan](docs/testing/test-plan.md) - Testing strategy

## API Endpoints

- `GET /` - Service information
- `GET /health` - Health check with database status
- `POST /webhooks/github` - GitHub webhook receiver
- `GET /metrics` - Prometheus metrics
- `GET /metrics/summary` - Human-readable metrics
- `GET /docs` - Interactive API documentation (Swagger UI)

## Development

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -c "import sys; sys.path.insert(0, '.'); import pytest; pytest.main(['tests/', '-v'])"

# Run with auto-reload
uvicorn app.main:app --reload

# Format code
black app/ tests/
isort app/ tests/

# Type checking
mypy app/
```

## Architecture

```
┌─────────────┐      ┌──────────────────┐      ┌─────────────┐
│   GitHub    │─────▶│  Sync Service    │─────▶│   OneDev    │
│   (Star)    │      │  (FastAPI)       │      │   (Git)     │
└─────────────┘      └──────────────────┘      └─────────────┘
                             │
                             ▼
                     ┌──────────────┐
                     │  PostgreSQL  │
                     │  (Tracking)  │
                     └──────────────┘
```

## Tech Stack

- **Framework**: FastAPI
- **Database**: SQLAlchemy (SQLite/PostgreSQL)
- **Migrations**: Alembic
- **Git Operations**: GitPython
- **GitHub API**: PyGithub
- **Async**: asyncio, aiohttp
- **Monitoring**: Prometheus
- **Testing**: pytest
- **Containerization**: Podman/Docker

## Project Status

**Milestone 1 (M1): COMPLETE** ✅

All 12 phases implemented:
- ✅ Phase 0: Project Setup
- ✅ Phase 1: Core Infrastructure
- ✅ Phase 2: Database Layer
- ✅ Phase 3: External Integrations
- ✅ Phase 4: Business Logic
- ✅ Phase 5: API Layer
- ✅ Phase 6: Error Handling & Retry
- ✅ Phase 7: Monitoring & Logging
- ✅ Phase 8: Testing & QA
- ✅ Phase 9: Documentation
- ✅ Phase 10: Containerization
- ✅ Phase 11: Deployment
- ✅ Phase 12: Production Readiness

## Contributing

This is a personal project, but suggestions and feedback are welcome! Please open an issue to discuss proposed changes.

## License

MIT License - See [LICENSE](LICENSE) for details.

## Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Inspired by the need for private backups of interesting open-source projects
- OneDev integration for self-hosted Git management

## Support

For issues, questions, or feature requests, please open an issue on GitHub.

---

**Made with ❤️ for the open-source community**

