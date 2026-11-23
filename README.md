# epicstar

Automatically sync starred GitHub repositories to your OneDev instance.

A GitHub App webhooks this service every time a repository of interest is
starred; the service verifies the signature, records the event, and clones +
pushes the repository to OneDev as an ongoing mirror.

## How it works

```
GitHub App (watch/star event)
        │  X-Hub-Signature-256 verified
        ▼
FastAPI receiver  ── 202 Accepted ──▶ GitHub
        │  sync queued as a background task
        ▼
1. POST {onedev}/~api/projects        (create project, Basic auth)
2. git clone  --mirror <source>       (subprocess, hard timeout)
3. git push   --mirror <onedev git>   (subprocess, hard timeout)
4. status + sync log persisted to DB  (sqlite / postgres)
```

- Webhook responses are fast (202 + background processing) so GitHub is never
  left waiting while a multi-GB clone runs.
- Every step is retried independently with exponential backoff (`OneDevAPIError`
  / `GitOperationError` only - a transient failure is never mislabeled
  `already_synced`).
- A failed star can simply be re-starred: the existing row is reset and reused.

## OneDev integration facts (probed, not guessed)

- REST base is `<server>/~api` - `/api/projects` returns 404.
- Authentication is HTTP **Basic** with the OneDev username + access token
  (Bearer tokens are rejected with 401).
- `POST /~api/projects` requires `gitPackConfig` and `codeIndexingSetting`
  fields and returns the project **id as plain text**, not JSON.
- Git-over-HTTPS works as `https://<username>:<token>@<server>/<project>.git`;
  the token is percent-encoded before embedding in the URL.

## Quick start

Prerequisites: Python 3.11+, a GitHub App
([docs/setup/github-app-setup.md](docs/setup/github-app-setup.md)), a OneDev
instance, and Git installed locally.

```bash
git clone https://github.com/studiozeroseven/epicstar.git
cd epicstar

python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# edit .env: GITHUB_APP_ID, GITHUB_WEBHOOK_SECRET, GITHUB_PRIVATE_KEY_PATH,
#            ONEDEV_API_URL, ONEDEV_USERNAME, ONEDEV_API_TOKEN

alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Container deployment

```bash
podman-compose up -d
podman-compose logs -f app
curl http://localhost:8000/health
```

The compose stack defaults to `postgresql://syncuser:syncpass@db:5432/syncdb`;
override via `DATABASE_URL` before starting. See
[docs/deployment/podman-deployment.md](docs/deployment/podman-deployment.md).

## Configuration

All settings are read from the environment (or `.env`); see
[.env.example](.env.example) for the full annotated list. Required values:

| Variable | Purpose |
| --- | --- |
| `GITHUB_APP_ID` | numeric id of the GitHub App |
| `GITHUB_WEBHOOK_SECRET` | shared secret used to verify webhook signatures |
| `GITHUB_PRIVATE_KEY_PATH` (or inline `GITHUB_PRIVATE_KEY`) | App private key (.pem) |
| `ONEDEV_API_URL` | OneDev server root URL (no `/api` suffix) |
| `ONEDEV_USERNAME` | OneDev login name (REST + git auth) |
| `ONEDEV_API_TOKEN` | OneDev access token |

Useful optional values: `ONEDEV_REPO_PREFIX` (default `github-`),
`ONEDEV_CONFLICT_STRATEGY` (`use_existing` | `append_timestamp` | `fail`),
`ONEDEV_PROJECT_PARENT_ID` (create repos under a parent project),
`DATABASE_URL` (defaults to `sqlite:///./dev.db`), retry tuning, git timeouts.

## API endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/` | service info |
| GET | `/health` | health check + database status |
| POST | `/webhooks/github` | GitHub webhook receiver (signature verified) |
| GET | `/metrics` | Prometheus metrics |
| GET | `/metrics/summary` | human-readable counters from the DB |
| GET | `/docs` | OpenAPI/Swagger UI |

## Development

```bash
pip install -r requirements-dev.txt

# run the test suite (53 tests, sqlite, no external services)
python -m pytest tests/

# format / lint
black app/ tests/
isort app/ tests/
mypy app/
bandit -c pyproject.toml -r app/
```

Pre-commit hooks are available: `pre-commit install`.

## Documentation

- [GitHub App setup](docs/setup/github-app-setup.md)
- [Deployment](docs/setup/deployment.md) and
  [Podman specifics](docs/deployment/podman-deployment.md)
- [Webhook API reference](docs/api/webhook-api.md)
- [Database schema](docs/architecture/database-schema.md)
- [Test plan](docs/testing/test-plan.md)

## Status

Alpha quality and re-verified in November 2026 against real OneDev
behaviour (API path/auth/response shapes, git URL form, timeouts, retries).
Not yet battle-tested in production; issues and feedback are welcome via
GitHub issues.

## License

MIT - see [LICENSE](LICENSE).
