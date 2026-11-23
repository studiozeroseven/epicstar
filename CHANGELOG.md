# Changelog

All notable changes to this project are documented in this file.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.2.0] - 2026-11-23

Re-verified every external integration against real OneDev behaviour and
reworked the core so the service actually works; previous claims of
"production-ready" were false.

### Fixed

- **OneDev REST base path**: `/api` never existed (404); client now uses
  `~api` (e.g. `GET {server}/~api/projects`) - verified against a live server.
- **OneDev authentication**: Bearer tokens are rejected (401); REST and git
  calls now use HTTP Basic with `ONEDEV_USERNAME` + `ONEDEV_API_TOKEN`
  (new required setting).
- **Create-project payload**: OneDev rejects projects without
  `gitPackConfig`/`codeIndexingSetting`; payload now includes them and parses
  the plain-text integer id OneDev returns (not JSON).
- **Git URL auth**: token-only / `oauth2:` URL forms fail; the client embeds
  the percent-encoded username + token (`https://user:token@host/project.git`)
  and redacts credentials in every log line.
- **Containerfile/compose port mismatch**: image listened on 5000 while
  compose mapped 8000; both now use 8000 (and `app.port`).
- **`starred_at` crash**: timezone-aware `datetime` values are stored as JSON
  strings via `model_dump(mode="json")` instead of raising `TypeError` on
  every real webhook payload.
- **Whole-flow retry trap**: a failed attempt could later resurface as
  `already_synced`. Retries are now per-step (OneDev API / git) and the repo
  row is reset to `in_progress` on re-star; a failed star is retried on the
  next star event.
- **Duplicate projects**: creation is now preceded by a paginated
  name lookup (`offset`/`count`) so `use_existing` actually adopts the
  existing project.

### Changed

- **Webhook receiver returns `202 Accepted` immediately** and syncs in a
  background task instead of blocking the HTTP response for the entire
  clone+push (GitHub aborts webhooks at ~10s).
- **GitPython removed**: git operations run via the `git` CLI with enforced
  subprocess timeouts (GitPython has no timeout support); large-file CVE
  exposure drops as a side effect.
- **Naive UTC datetimes** at every database boundary (asyncpg rejects tz-aware
  values into naive columns).
- **Dependency floors raised and unused deps removed** (`aiohttp`,
  `python-jose`, `python-dateutil`, `python-multipart`, `psycopg2-binary`,
  `GitPython`, `PyGithub`-only-what's-needed); `aiosqlite` added because the
  documented default `sqlite:///./dev.db` needs it.
- **Metrics are real** (prometheus_client counters/gauges/histograms backed by
  DB state); removed the hardcoded summary values.
- **Config system** moved to pydantic-settings with fail-fast validation for
  missing GitHub App credentials and CORS list parsing.

### Added

- Working async SQLAlchemy 2.0 engine with URL normalization
  (`postgres://`/`postgresql://` -> `postgresql+asyncpg://`,
  sqlite -> `sqlite+aiosqlite://`).
- Retry configuration exposed via settings (`MAX_RETRIES`, `RETRY_*`).
- `/metrics/summary` reads real repository/sync-log state.
- Test suite: 53 tests (unit + integration, async webhook flow with fake
  OneDev/git) - the previous suite could not even collect on a clean checkout.
- `requirements-dev.txt` aligned with the CI toolchain (pytest 8, pytest-asyncio,
  black, isort, mypy, bandit).
- GitHub Actions CI (test matrix, lint).

### Removed

- Root-level AI process files (`BUILD_COMPLETE_SUMMARY.md`,
  `M1_COMPLETION_REPORT.md`, `SETUP_COMPLETE.md`, etc.) that documented
  milestones rather than the product, with false completion claims.
- Stale docs (`docs/project-plan.md`, `docs/use-cases/basic-sync.md`,
  `docs/architecture/overview.md`) describing the pre-fix architecture.

## [0.1.0]

Initial attempt. Looked complete, was not.
