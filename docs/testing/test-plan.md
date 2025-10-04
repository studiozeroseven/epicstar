# Test Plan

## Overview

Comprehensive testing strategy for the GitHub-to-OneDev Sync Service covering unit, integration, and end-to-end tests.

## Test Levels

### 1. Unit Tests

Test individual components in isolation.

**Coverage Target**: >80%

**Components**:
- Configuration management
- Security/signature verification
- Database CRUD operations
- API clients (GitHub, OneDev)
- Git operations
- Sync orchestrator logic

**Location**: `tests/unit/`

**Run**: `pytest tests/unit/ -v`

### 2. Integration Tests

Test interactions between components.

**Components**:
- API endpoints with database
- Webhook processing flow
- Database migrations
- Error handling and retry logic

**Location**: `tests/integration/`

**Run**: `pytest tests/integration/ -v`

### 3. End-to-End Tests

Test complete workflows from webhook to OneDev.

**Scenarios**:
- Star repository → Clone → Push to OneDev
- Handle duplicate stars
- Handle errors gracefully
- Retry failed syncs

**Location**: `tests/e2e/`

**Run**: `pytest tests/e2e/ -v`

## Test Execution

### Local Development

```bash
# All tests
pytest

# With coverage
pytest --cov=app --cov-report=html

# Specific test file
pytest tests/unit/test_security.py -v

# Specific test
pytest tests/unit/test_security.py::TestGitHubSignatureVerification::test_valid_signature -v
```

### CI/CD Pipeline

Tests run automatically on:
- Pull requests
- Commits to dev branch
- Before deployment

## Test Data

### Fixtures

Located in `tests/conftest.py`:
- `test_settings`: Test configuration
- `async_db_session`: Async database session
- `sync_db_session`: Sync database session
- `client`: FastAPI test client

### Mock Data

- GitHub webhook payloads
- OneDev API responses
- Git repository data

## Manual Testing

### 1. Health Check

```bash
curl http://localhost:8000/health
```

Expected:
```json
{
  "status": "healthy",
  "version": "0.1.0",
  "environment": "development",
  "database": "connected"
}
```

### 2. Webhook Endpoint

```bash
# Valid signature
curl -X POST http://localhost:8000/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: watch" \
  -H "X-GitHub-Delivery: test-123" \
  -H "X-Hub-Signature-256: sha256=..." \
  -d '{"action":"started","repository":{"name":"test"}}'
```

### 3. Database

```bash
# Check tables
sqlite3 dev.db ".tables"

# Check repositories
sqlite3 dev.db "SELECT * FROM repositories;"
```

## Performance Testing

### Load Testing

Use `locust` or `k6` for load testing:

```python
# locustfile.py
from locust import HttpUser, task

class WebhookUser(HttpUser):
    @task
    def post_webhook(self):
        self.client.post("/webhooks/github", json={...})
```

Run:
```bash
locust -f locustfile.py --host=http://localhost:8000
```

### Benchmarks

- Webhook processing: <500ms
- Git clone (small repo): <30s
- Git clone (large repo): <5min
- Database query: <100ms

## Security Testing

### 1. Signature Verification

Test invalid signatures are rejected:
```bash
curl -X POST http://localhost:8000/webhooks/github \
  -H "X-Hub-Signature-256: sha256=invalid" \
  -d '{}'
```

Expected: 401 Unauthorized

### 2. SQL Injection

Test database queries are parameterized and safe.

### 3. Secrets Management

Verify secrets are not logged or exposed in responses.

## Regression Testing

After each change:
1. Run full test suite
2. Verify existing functionality still works
3. Check no performance degradation

## Test Reporting

### Coverage Report

```bash
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### Test Results

- Console output for quick feedback
- HTML report for detailed analysis
- CI/CD integration for automated checks

## Continuous Improvement

- Add tests for every bug fix
- Increase coverage over time
- Review and update test plan quarterly
- Monitor test execution time

