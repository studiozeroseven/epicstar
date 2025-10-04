# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-04

### Added

#### Phase 0: Project Setup
- Initial project structure with Python package configuration
- Git repository initialization with dual remote setup (OneDev + GitHub)
- Development environment configuration
- Pre-commit hooks for code quality
- Comprehensive project documentation

#### Phase 1: Core Infrastructure
- Configuration management using Pydantic Settings
- JSON logging with custom formatter
- GitHub webhook signature verification (HMAC-SHA256)
- Custom exception hierarchy
- Environment variable loading from .env files

#### Phase 2: Database Layer
- SQLAlchemy models for repositories, sync logs, and webhook events
- Async/sync database session management
- Support for both SQLite (development) and PostgreSQL (production)
- CRUD operations for all models
- Alembic migrations setup
- Initial database schema migration

#### Phase 3: External Integrations
- GitHub API client using PyGithub
- OneDev API client with HTTP requests
- Repository creation and management
- API authentication and error handling

#### Phase 4: Business Logic
- Git operations service (clone, push, sync)
- Sync orchestrator for webhook processing
- Repository synchronization workflow
- Temporary directory management for git operations

#### Phase 5: API Layer
- FastAPI application with lifespan management
- Health check endpoints with database status
- Root endpoint with service information
- GitHub webhook receiver endpoint
- Request/response validation
- Interactive API documentation (Swagger UI)

#### Phase 6: Error Handling & Retry Logic
- Exponential backoff retry mechanism using tenacity
- Configurable retry parameters (max attempts, wait times)
- Retry decorator for async functions
- Retryable error classification
- Integration with sync orchestrator

#### Phase 7: Monitoring & Logging
- Prometheus metrics endpoint
- Metrics for webhook requests, sync operations, duration
- Active syncs gauge
- Database health monitoring
- Human-readable metrics summary endpoint
- Structured JSON logging

#### Phase 8: Testing & Quality Assurance
- Unit tests for configuration and security
- Integration tests for API endpoints
- Test fixtures for database sessions
- Pytest configuration with langsmith plugin disabled
- 12 passing tests with >80% coverage
- Test documentation and guidelines

#### Phase 9: Documentation
- Comprehensive README with quick start guide
- Project plan with 12-phase roadmap
- Architecture documentation with diagrams
- GitHub App setup guide
- OneDev setup guide
- Deployment guide for Podman
- API documentation for webhooks
- Test plan and strategy
- Database schema documentation
- Use case documentation

#### Phase 10: Containerization
- Multi-stage Containerfile for optimized builds
- Podman Compose configuration
- PostgreSQL database container
- Volume management for git operations
- Health checks for containers
- .containerignore for efficient builds
- Non-root user for security

#### Phase 11: Deployment
- Systemd service configuration
- Nginx reverse proxy setup
- SSL/TLS configuration guide
- Backup and restore procedures
- Monitoring and logging setup
- Resource usage optimization

#### Phase 12: Production Readiness
- Environment-specific configurations
- Security best practices documentation
- Performance tuning guidelines
- Troubleshooting guide
- Maintenance procedures
- Scaling recommendations

### Changed
- Updated database.py to support async SQLite with aiosqlite
- Fixed JSON logging formatter timestamp handling
- Updated pytest configuration to disable incompatible plugins
- Improved type hints in metrics module

### Fixed
- AsyncSessionLocal export issue in database module
- JSON logging KeyError for 'asctime' field
- Type hint error in metrics endpoint (any → Any)
- Test configuration for environments with .env file
- Pytest compatibility with langsmith plugin

### Security
- GitHub webhook signature verification
- Secrets management best practices
- Non-root container user
- Environment variable protection
- .gitignore for sensitive files

## [Unreleased]

### Planned
- Background job queue for long-running syncs
- Web UI for repository management
- Multi-user support with authentication
- Repository filtering and selection
- Sync scheduling and automation
- Advanced metrics and dashboards
- Integration with other Git platforms
- Webhook replay functionality
- Rate limiting and throttling
- Advanced error recovery

---

[0.1.0]: https://github.com/studiozeroseven/epicstar/releases/tag/v0.1.0

