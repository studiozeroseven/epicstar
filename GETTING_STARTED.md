# Getting Started with GitHub-to-OneDev Sync Service

## Welcome! 👋

This guide will help you get started with the GitHub-to-OneDev Sync Service development. Follow these steps to set up your development environment and begin contributing.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Python 3.11+** ([Download](https://www.python.org/downloads/))
- **Git** ([Download](https://git-scm.com/downloads))
- **Podman** ([Install Guide](https://podman.io/getting-started/installation))
- **PostgreSQL 15+** (optional for local development)
- **GitHub Account** with admin access to create GitHub Apps
- **OneDev Instance** with API access

## Quick Start (5 Minutes)

### 1. Clone the Repository

```bash
git clone https://github.com/your-username/epicstar.git
cd epicstar
```

### 2. Set Up Python Environment

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

# Upgrade pip
pip install --upgrade pip
```

### 3. Install Dependencies

```bash
# Install development dependencies
pip install -r requirements-dev.txt
```

### 4. Configure Environment

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your credentials
# Use your favorite editor (nano, vim, code, etc.)
nano .env
```

**Minimum required configuration for development**:
```bash
ENVIRONMENT=development
DATABASE_URL=sqlite:///./dev.db
GITHUB_APP_ID=your-app-id
GITHUB_WEBHOOK_SECRET=your-webhook-secret
GITHUB_PRIVATE_KEY_PATH=/path/to/github-app-key.pem
ONEDEV_API_URL=https://your-onedev-instance.com
ONEDEV_API_TOKEN=your-onedev-token
```

### 5. Initialize Database

```bash
# Run database migrations
alembic upgrade head
```

### 6. Start Development Server

```bash
# Start with hot reload
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 7. Verify Installation

Open your browser and navigate to:
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

You should see the interactive API documentation (Swagger UI).

## Development Workflow

### Branch Strategy

We follow a Git Flow branching strategy:

```
main (production-ready code)
  ↓
dev (integration branch)
  ↓
feature/* (feature branches)
```

### Creating a Feature Branch

```bash
# Make sure you're on dev branch
git checkout dev
git pull origin dev

# Create feature branch
git checkout -b feature/your-feature-name

# Make your changes...

# Commit with semantic commit message
git add .
git commit -m "feat(component): add new feature"

# Push to remote
git push origin feature/your-feature-name

# Create Pull Request to dev branch
```

### Commit Message Format

We use semantic commit messages:

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```bash
git commit -m "feat(webhook): add signature verification"
git commit -m "fix(database): resolve connection pool issue"
git commit -m "docs(setup): update GitHub App setup guide"
git commit -m "test(orchestrator): add integration tests"
```

## Running Tests

### Run All Tests

```bash
pytest
```

### Run with Coverage

```bash
pytest --cov=app --cov-report=html
```

View coverage report: `open htmlcov/index.html`

### Run Specific Tests

```bash
# Run tests in a specific file
pytest tests/unit/test_webhook_validation.py

# Run tests matching a pattern
pytest -k "test_signature"

# Run with verbose output
pytest -v
```

### Run Tests in Parallel

```bash
pytest -n auto
```

## Code Quality Checks

### Format Code

```bash
# Format with black
black .

# Sort imports
isort .
```

### Lint Code

```bash
# Run flake8
flake8 app/ tests/

# Run mypy (type checking)
mypy app/

# Run pylint
pylint app/

# Security check with bandit
bandit -r app/
```

### Run All Quality Checks

```bash
# Run pre-commit hooks manually
pre-commit run --all-files
```

## Project Structure

```
epicstar/
├── app/                    # Application code
│   ├── __init__.py
│   ├── main.py            # FastAPI app initialization
│   ├── config.py          # Configuration management
│   ├── api/               # API endpoints
│   ├── core/              # Core functionality
│   ├── db/                # Database models and operations
│   ├── integrations/      # External API clients
│   ├── models/            # Pydantic models
│   ├── services/          # Business logic
│   └── utils/             # Utility functions
├── tests/                 # Test files
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   ├── e2e/               # End-to-end tests
│   └── conftest.py        # Pytest fixtures
├── docs/                  # Documentation
│   ├── architecture/      # Architecture docs
│   ├── setup/             # Setup guides
│   ├── api/               # API documentation
│   ├── operations/        # Operational guides
│   └── development/       # Development guides
├── alembic/               # Database migrations
├── scripts/               # Utility scripts
├── .env.example           # Environment template
├── .gitignore            # Git ignore rules
├── requirements.txt       # Production dependencies
├── requirements-dev.txt   # Development dependencies
├── README.md             # Project overview
└── GETTING_STARTED.md    # This file
```

## Common Tasks

### Create a New Database Migration

```bash
# Auto-generate migration from model changes
alembic revision --autogenerate -m "Add new column"

# Create empty migration
alembic revision -m "Custom migration"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

### Add a New Dependency

```bash
# Add to requirements.txt
echo "new-package==1.0.0" >> requirements.txt

# Install
pip install -r requirements.txt

# For development dependencies
echo "new-dev-package==1.0.0" >> requirements-dev.txt
pip install -r requirements-dev.txt
```

### Run with Docker/Podman

```bash
# Build container
podman build -t github-onedev-sync:dev .

# Run container
podman run -d \
  --name github-onedev-sync \
  -p 8000:8000 \
  --env-file .env \
  github-onedev-sync:dev

# View logs
podman logs -f github-onedev-sync

# Stop container
podman stop github-onedev-sync
podman rm github-onedev-sync
```

## Debugging

### Using IPython

```bash
# Start IPython shell with app context
ipython

# In IPython:
from app.main import app
from app.config import settings
print(settings.dict())
```

### Using Debugger

Add breakpoint in code:
```python
import ipdb; ipdb.set_trace()
```

Or use Python's built-in debugger:
```python
import pdb; pdb.set_trace()
```

### View Logs

```bash
# Application logs
tail -f logs/app.log

# Filter by level
grep ERROR logs/app.log
```

## Testing Webhooks Locally

### Option 1: ngrok

```bash
# Install ngrok
brew install ngrok  # macOS

# Start ngrok tunnel
ngrok http 8000

# Use the HTTPS URL in GitHub App webhook settings
# Example: https://abc123.ngrok.io/webhooks/github
```

### Option 2: smee.io

```bash
# Install smee client
npm install -g smee-client

# Start smee channel
smee --url https://smee.io/abc123 --target http://localhost:8000/webhooks/github

# Use the smee.io URL in GitHub App settings
```

## Documentation

### View Documentation Locally

```bash
# Install mkdocs (included in requirements-dev.txt)
pip install -r requirements-dev.txt

# Serve documentation
mkdocs serve

# Open browser to http://localhost:8001
```

### Build Documentation

```bash
mkdocs build
```

## Getting Help

### Resources

- **Full Development Plan**: [docs/project-plan.md](docs/project-plan.md)
- **Architecture Overview**: [docs/architecture/overview.md](docs/architecture/overview.md)
- **Setup Guides**: [docs/setup/](docs/setup/)
- **API Documentation**: http://localhost:8000/docs (when running)

### Common Issues

**Issue: `ModuleNotFoundError`**
```bash
# Solution: Ensure virtual environment is activated and dependencies installed
source venv/bin/activate
pip install -r requirements-dev.txt
```

**Issue: Database connection error**
```bash
# Solution: Check DATABASE_URL in .env
# For development, use SQLite:
DATABASE_URL=sqlite:///./dev.db
```

**Issue: GitHub webhook not received**
```bash
# Solution: Check ngrok/smee is running and URL is correct in GitHub App settings
ngrok http 8000
# Update webhook URL in GitHub App settings
```

## Next Steps

Now that you have the development environment set up:

1. ✅ Read the [Development Plan](docs/project-plan.md)
2. ✅ Review the [Architecture Overview](docs/architecture/overview.md)
3. ✅ Set up your [GitHub App](docs/setup/github-app-setup.md)
4. ✅ Start with [Phase 0 tasks](docs/project-plan.md#phase-0-project-setup--documentation-week-1)
5. ✅ Join the development workflow!

## Contributing

We follow strict development rules to ensure code quality:

- ✅ Write tests for all new code
- ✅ Follow the coding standards
- ✅ Update documentation
- ✅ Use semantic commit messages
- ✅ Create PRs to `dev` branch
- ✅ Ensure all tests pass before PR

See [docs/development/contributing.md](docs/development/contributing.md) for detailed guidelines.

## Questions?

If you have questions or run into issues:

1. Check the [Troubleshooting Guide](docs/operations/troubleshooting.md)
2. Review existing [GitHub Issues](https://github.com/your-username/epicstar/issues)
3. Create a new issue with detailed information
4. Ask in the project discussions

---

**Happy Coding! 🚀**

Last Updated: 2025-10-04

