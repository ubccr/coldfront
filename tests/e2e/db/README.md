# ColdFront DB-backend e2e suite

This suite runs the **entire ColdFront unit test suite** against a live
PostgreSQL or MySQL database engines instead of the sqlite default. It spins up
a database container via `testcontainers` and rewrites
`settings.DATABASES["default"]`.

This is **disabled by default** — a plain `pytest` runs against sqlite and
starts no containers. Enable it with the `--db=postgres` or `--db=mysql` CLI
option.

## Requirements

- Docker on the host.
- Backend driver installed:
  - Postgres: `uv sync --extra pg` 
  - MySQL/MariaDB: `uv sync --extra mysql`
- Images are pulled pre-built from Docker Hub; nothing is built locally.

## Running

```bash
# All unit tests against a live PostgreSQL
uv sync --extra pg
COLDFRONT_ENV=.env.testing uv run -m pytest tests/ --db=postgres

# All unit tests against a live MariaDB
uv sync --extra mysql
COLDFRONT_ENV=.env.testing uv run -m pytest tests/ --db=mysql
```

## Backend matrix

| `--db` value | Container | Django engine | Driver | User |
|-------------|-----------|---------------|--------|------|
| `sqlite` (default) | none | sqlite | —      | —    |
| `postgres`    | `postgres:18` | `django.db.backends.postgresql` | psycopg2-binary | `coldfront` (superuser) |
| `mysql`       | `mariadb:12` | `django.db.backends.mysql`      | mysqlclient | `root` |

### MySQL/MariaDB uses root

Django's `setup_databases` creates a separate `test_coldfront` database and
needs global `CREATE DATABASE` privilege. The official MariaDB image's
non-root `MARIADB_USER` is granted only its own database, so the `MySqlStack`
connects as `root` (full privileges). `MySqlContainer(username="root",
password=...)` maps the password to `MYSQL_ROOT_PASSWORD`, which the MariaDB
image honours as a legacy alias for `MARIADB_ROOT_PASSWORD`.

### Test database name

Both backends use `dbname="coldfront"`, so Django's test database is
`test_coldfront` (rather than the default `test_test`).
