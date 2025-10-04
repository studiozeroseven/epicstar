# GitHub-to-OneDev Sync Service - Development Plan Summary

## Executive Summary

This document provides a high-level overview of the comprehensive development plan for building an automated GitHub-to-OneDev repository synchronization service.

**Project Goal**: Automatically clone starred GitHub repositories to a private OneDev Git instance.

**Estimated Timeline**: 8-12 weeks  
**Current Status**: Planning Complete - Ready for Phase 0 Implementation

---

## Quick Links

- **Full Development Plan**: [docs/project-plan.md](docs/project-plan.md)
- **Architecture Overview**: [docs/architecture/overview.md](docs/architecture/overview.md)
- **Database Schema**: [docs/architecture/database-schema.md](docs/architecture/database-schema.md)
- **Use Case Documentation**: [docs/use-cases/basic-sync.md](docs/use-cases/basic-sync.md)
- **Setup Guides**: [docs/setup/](docs/setup/)

---

## Technology Stack

| Component | Technology | Justification |
|-----------|-----------|---------------|
| **Language** | Python 3.11+ | Rich ecosystem, async support, easy containerization |
| **Web Framework** | FastAPI | Built-in OpenAPI docs, async support, Pydantic validation |
| **Database** | PostgreSQL 15+ | ACID compliance, reliable state management |
| **Containerization** | Podman | Daemonless, rootless, Docker-compatible |
| **GitHub Integration** | PyGithub + Webhooks | Official library, webhook signature verification |
| **OneDev Integration** | Custom REST client (httpx) | Flexible async API integration |
| **Testing** | pytest + pytest-asyncio | Comprehensive testing framework |
| **CI/CD** | GitHub Actions | Native GitHub integration |

---

## Architecture Overview

### High-Level Flow

```
GitHub (Star Event) 
    ↓ Webhook
Middleware Service (FastAPI)
    ↓ Validate & Process
GitHub API (Fetch Metadata)
    ↓
OneDev API (Create Repository)
    ↓
Git Operations (Clone & Push)
    ↓
Database (Update State)
```

### Key Components

1. **Webhook Receiver**: Accepts GitHub webhook events
2. **Signature Validator**: Verifies webhook authenticity (HMAC-SHA256)
3. **GitHub API Client**: Fetches repository metadata
4. **OneDev API Client**: Creates repositories in OneDev
5. **Git Operations Module**: Clones from GitHub, pushes to OneDev
6. **Sync Orchestrator**: Coordinates the entire workflow
7. **Database Layer**: Tracks synchronization state and audit logs

---

## Implementation Phases

### ✅ Phase 0: Project Setup & Documentation (Week 1)
**Status**: Ready to Start  
**Deliverables**:
- Git repository with branching strategy (main, dev, feature/*)
- Project directory structure (app/, docs/, tests/, alembic/)
- Python virtual environment and dependency management
- Code quality tools (black, flake8, mypy, isort)
- Documentation structure
- Pre-commit hooks
- Environment configuration templates

**Tasks**:
- [x] Create comprehensive project plan
- [x] Design architecture diagrams
- [x] Document database schema
- [x] Write use case documentation
- [x] Create setup guides
- [ ] Initialize Git repository
- [ ] Set up project structure
- [ ] Configure development environment

---

### Phase 1: GitHub App Configuration (Week 1-2)
**Deliverables**:
- Configured GitHub App with webhook subscription
- Webhook secret and private key
- Step-by-step setup documentation
- Test webhook delivery mechanism

---

### Phase 2: Middleware Core (Week 2-3)
**Deliverables**:
- FastAPI application with webhook endpoint
- Signature verification implementation
- Payload validation with Pydantic
- Structured logging (JSON format)
- Configuration management
- Health check endpoint
- Unit tests (>80% coverage)

---

### Phase 3: GitHub Integration (Week 3-4)
**Deliverables**:
- GitHub API client wrapper (PyGithub)
- Rate limiting and backoff implementation
- Error handling for API failures
- Mock GitHub API for testing
- Integration tests

---

### Phase 4: OneDev Integration (Week 4-6)
**Deliverables**:
- OneDev API client (httpx-based)
- Repository creation logic
- Naming conflict resolution
- Mock OneDev API for testing
- Integration tests

**⚠️ Note**: May require clarification on OneDev API capabilities

---

### Phase 5: Git Operations Module (Week 6-7)
**Deliverables**:
- Git clone and push functionality
- Authentication handling (SSH/HTTPS)
- Progress tracking for large repositories
- Timeout and retry logic
- Temporary directory cleanup
- Integration tests

---

### Phase 6: State Management & Database (Week 7-8)
**Deliverables**:
- Database schema and SQLAlchemy models
- Alembic migration system
- CRUD operations
- Sync status tracking
- Audit logging
- Database tests

---

### Phase 7: Sync Orchestration (Week 8-9)
**Deliverables**:
- Complete end-to-end workflow
- Idempotency handling
- Comprehensive error handling
- Rollback on failures
- End-to-end tests
- Performance benchmarks

---

### Phase 8: Containerization (Week 9-10)
**Deliverables**:
- Multi-stage Containerfile
- Podman Compose configuration
- Deployment scripts
- Volume mounts for persistence
- Health check configuration
- Security scan results

---

### Phase 9: CI/CD Pipeline (Week 10)
**Deliverables**:
- GitHub Actions workflow
- Automated testing on PR
- Code quality checks
- Security scanning
- Automated container builds
- Release workflow

---

### Phase 10: Monitoring & Observability (Week 11)
**Deliverables**:
- Prometheus metrics endpoint
- Custom metrics (sync success/failure, duration)
- Structured logging with correlation IDs
- Grafana dashboard (optional)
- Error alerting
- Operational runbook

---

### Phase 11: Advanced Features (Week 12+)
**Deliverables**:
- Un-starring support (archive/delete in OneDev)
- Retry mechanism with exponential backoff
- Batch synchronization (sync all starred repos)
- Admin API endpoints
- Webhook replay capability
- Repository update detection

---

## Security Considerations

### Critical Security Measures

1. **Webhook Security**:
   - ✅ HMAC-SHA256 signature verification
   - ✅ Payload validation before processing
   - ✅ Rate limiting (100 requests/minute)
   - ✅ HTTPS only in production

2. **Credential Management**:
   - ✅ Environment variables for secrets
   - ✅ Never commit secrets to Git
   - ✅ Support for external secret managers (Vault, AWS Secrets Manager)
   - ✅ Regular credential rotation

3. **Container Security**:
   - ✅ Run as non-root user
   - ✅ Minimal base image (python:3.11-slim)
   - ✅ Security scanning (Trivy)
   - ✅ Regular dependency updates

4. **Network Security**:
   - ✅ TLS 1.2+ for all external API calls
   - ✅ Reverse proxy for HTTPS termination
   - ✅ Firewall rules for OneDev access

5. **Data Protection**:
   - ✅ Sanitize logs (no secrets)
   - ✅ Encrypted database connections
   - ✅ Audit logging for all operations

---

## Testing Strategy

### Test Pyramid

- **Unit Tests (60%)**: Business logic, utilities, validation
- **Integration Tests (30%)**: GitHub API, OneDev API, database
- **E2E Tests (10%)**: Complete workflow, performance tests

### Coverage Goals

- **Overall**: >80% code coverage
- **Critical paths**: 100% coverage (webhook processing, sync orchestration)
- **All external API interactions**: Integration tests required

### Testing Tools

- pytest (test framework)
- pytest-asyncio (async test support)
- pytest-cov (coverage reporting)
- pytest-mock (mocking)
- httpx-mock (HTTP mocking)
- faker (test data generation)

---

## Deployment Strategy

### Development
- Local development with hot reload
- SQLite database
- ngrok/smee.io for webhook testing

### Staging
- Podman containers
- PostgreSQL database
- Test OneDev instance
- Monitoring enabled

### Production
- Podman containers with Podman Compose
- PostgreSQL with backups
- Reverse proxy (nginx/Traefik) with HTTPS
- Monitoring and alerting
- Automated backups

### Update Procedure
1. Build new container image with version tag
2. Backup database
3. Run database migrations
4. Rolling update with health checks
5. Verify deployment
6. Rollback procedure if needed

---

## Success Metrics

### Performance Targets

- **Webhook Processing**: <500ms (p95)
- **Small Repo Sync (<100MB)**: <2 minutes
- **Medium Repo Sync (100MB-1GB)**: <10 minutes
- **Large Repo Sync (>1GB)**: <30 minutes
- **Success Rate**: >95%
- **Uptime**: >99.9%

### Quality Targets

- **Test Coverage**: >80%
- **Code Quality**: No critical issues
- **Documentation**: 100% of public APIs documented
- **Security**: Zero high/critical vulnerabilities

---

## Risk Assessment

### High-Priority Risks

| Risk | Mitigation |
|------|------------|
| OneDev API changes | Version API calls, monitor releases |
| GitHub rate limiting | Implement caching, respect rate limits |
| Large repository timeout | Timeout handling, async processing |
| Credential exposure | Secret management, audit logging |

### Medium-Priority Risks

| Risk | Mitigation |
|------|------------|
| Webhook delivery failure | Retry mechanism, manual trigger |
| Network connectivity | Retry logic, offline queue |
| Disk space exhaustion | Monitoring, cleanup policies |

---

## Questions Requiring Clarification

Before proceeding with implementation, please provide:

1. **OneDev API Access**: Do you have API documentation for your OneDev instance?
2. **OneDev Version**: What version of OneDev are you running?
3. **Authentication Method**: Does OneDev support API tokens or OAuth?
4. **Repository Permissions**: What permissions are needed to create repositories?
5. **Hosting Environment**: Where will this service be deployed?
6. **Un-starring Behavior**: Should un-starring delete, archive, or ignore repos?
7. **Repository Organization**: How should repos be organized in OneDev?

---

## Next Steps

### Immediate Actions (This Week)

1. **Review this plan** and provide feedback
2. **Answer clarification questions** about OneDev
3. **Set up development environment** (Phase 0)
4. **Create GitHub App** (Phase 1)

### Week 1 Deliverables

- [ ] Git repository initialized with proper structure
- [ ] Development environment configured
- [ ] Documentation structure in place
- [ ] GitHub App created and configured
- [ ] First webhook test successful

### Week 2-3 Deliverables

- [ ] FastAPI application with webhook endpoint
- [ ] Signature verification working
- [ ] Unit tests passing
- [ ] GitHub API integration complete

---

## Development Rules Compliance

This project adheres to strict development rules:

✅ **No Assumptions**: Halt and request clarification when unclear  
✅ **Atomic Commits**: Every change committed with descriptive messages  
✅ **Feature Isolation**: New features in separate branches  
✅ **Modular Design**: All code independently testable  
✅ **Complete Documentation**: Living docs updated with code  
✅ **Git Workflow**: main (deployable), dev (integration), feature/* branches  
✅ **Testing Standards**: Unit tests for every function, all tests pass before phase completion  
✅ **Sequential Execution**: Follow defined task sequence  

---

## Resources

### Documentation
- [Full Project Plan](docs/project-plan.md)
- [Architecture Overview](docs/architecture/overview.md)
- [Database Schema](docs/architecture/database-schema.md)
- [GitHub App Setup](docs/setup/github-app-setup.md)
- [Deployment Guide](docs/setup/deployment.md)
- [Basic Sync Use Case](docs/use-cases/basic-sync.md)

### External References
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [GitHub Webhooks Guide](https://docs.github.com/en/developers/webhooks-and-events/webhooks)
- [OneDev Documentation](https://docs.onedev.io/)
- [Podman Documentation](https://docs.podman.io/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

## Contact & Support

For questions or issues during development:
1. Review the [Troubleshooting Guide](docs/operations/troubleshooting.md) (to be created)
2. Check the [FAQ](docs/FAQ.md) (to be created)
3. Open an issue in the GitHub repository
4. Contact the project maintainer

---

**Document Version**: 1.0  
**Last Updated**: 2025-10-04  
**Status**: Planning Complete - Ready for Implementation  
**Next Phase**: Phase 0 - Project Setup & Documentation

