# GitHub-to-OneDev Sync Service

An automated service that synchronizes starred GitHub repositories to a private OneDev Git instance.

## Overview

When you star a repository on GitHub, this service automatically:
1. Receives a webhook notification from GitHub
2. Fetches the repository metadata and clone URL
3. Creates a new repository in your OneDev instance
4. Clones the GitHub repository and pushes it to OneDev
5. Tracks synchronization status and handles errors gracefully

## Architecture

```
GitHub (Star Event) → GitHub App Webhook → Middleware Service → OneDev API
                                                ↓
                                          Database (State)
```

### Components

1. **GitHub App**: Subscribes to `watch` events and sends webhooks
2. **Middleware Service**: FastAPI-based service that orchestrates the sync
3. **OneDev Integration**: API client for repository creation and management
4. **State Database**: Tracks synchronized repositories and status

## Technology Stack

- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **Database**: PostgreSQL (production) / SQLite (development)
- **Containerization**: Podman
- **GitHub Integration**: PyGithub + GitHub Webhooks
- **OneDev Integration**: REST API client
- **Testing**: pytest, pytest-asyncio, pytest-cov
- **Monitoring**: Prometheus metrics (optional)

## Quick Start

### Prerequisites

- Python 3.11+
- Podman
- GitHub account with admin access to create GitHub Apps
- OneDev instance with API access

### Local Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd epicstar

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# See docs/setup/configuration.md for details

# Run database migrations
alembic upgrade head

# Start the development server
uvicorn app.main:app --reload
```

### Production Deployment

```bash
# Build the container
podman build -t github-onedev-sync:latest .

# Run with Podman Compose
podman-compose up -d

# Check logs
podman logs -f github-onedev-sync
```

See [docs/setup/deployment.md](docs/setup/deployment.md) for detailed deployment instructions.

## Documentation

- [Architecture Overview](docs/architecture/overview.md)
- [Setup Guide](docs/setup/README.md)
  - [GitHub App Configuration](docs/setup/github-app-setup.md)
  - [OneDev Configuration](docs/setup/onedev-configuration.md)
  - [Deployment Guide](docs/setup/deployment.md)
- [API Documentation](docs/api/README.md)
- [Operations Guide](docs/operations/README.md)
- [Development Guide](docs/development/README.md)

## Project Status

This project follows a phased development approach. See [docs/project-plan.md](docs/project-plan.md) for the complete development roadmap.

Current Phase: **Phase 0 - Project Setup**

## Contributing

See [docs/development/contributing.md](docs/development/contributing.md) for contribution guidelines.

## License

[Specify your license here]

## Support

For issues and questions, please refer to:
- [Troubleshooting Guide](docs/operations/troubleshooting.md)
- [GitHub Issues](../../issues)

