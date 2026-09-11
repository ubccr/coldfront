# ColdFront End-to-End (e2e) Tests

This directory contains end-to-end tests that spin up **real containers** via
[`testcontainers`](https://github.com/testcontainers/testcontainers-python) so
ColdFront's code can be exercised against live services (Slurm REST API,
PostgreSQL/MySQL, ...) instead of mocked responses.

## Gating — these do NOT run by default

e2e tests are excluded from normal runs two ways:

1. `pyproject.toml` adds `-m "not e2e"` to default pytest `addopts`, so plain
   `pytest` never collects them.
2. Even when run explicitly with `pytest -m e2e`, every test is skipped unless
   `COLDFRONT_E2E=1` is set.

## Requirements

- Docker + Docker Compose v2 on the host.
- Service images are pulled pre-built from Docker Hub; nothing is built locally.

## Running

```bash
COLDFRONT_E2E=1 COLDFRONT_ENV=.env.testing uv run -m pytest tests/e2e/<app>/ -m e2e
```

Each `<app>/` suite brings up the real service stack it targets, runs
ColdFront's code against it, and tears the stack down (`down --volumes`) at
session end.

## Layout

- `conftest.py` — the e2e gate (env var + collection skip) and shared fixtures.
- `containers.py` — reusable container wrappers (the stack base), shared across
  future service suites.
- `<app>/` — one directory per live service; each holds its own fixtures,
  compose file, config, and tests.

## Unit test vs e2e test coverage split

- **e2e is the integration truth** — real wire-format parsing, live CRUD
  round-trips to APIs
- **Unit tests mirror live responses.** These tests should replay the same
  response shapes as the live e2e tests so pure logic (serializer/spec
  conformance against any vendored OpenAPI specs, retry/transient logic, parser
  edge cases like empty/non-JSON bodies) can run fast without a container.

## Per-service suites

- `tests/e2e/slurm/README.md` — the Slurm e2e suite
