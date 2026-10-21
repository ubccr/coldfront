# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Top-level pytest configuration for ColdFront.

Hosts the DB-backend fixtures: with ``--db=postgres`` or ``--db=mysql`` spins up
a database container (testcontainers) and merges its connection settings into
``settings.DATABASES["default"]``, so **all** unit tests run against the live
engine instead of sqlite.
"""

import django.conf
import pytest

from tests.e2e.containers import ensure_docker_available
from tests.e2e.db.containers import build_db_stack

DB_BACKENDS = ("sqlite", "postgres", "mysql")


def pytest_addoption(parser) -> None:
    """Add ``--db`` to choose the database backend for the unit suite."""
    parser.addoption(
        "--db",
        choices=DB_BACKENDS,
        default="sqlite",
        help="Database backend for the unit suite: sqlite (default), postgres, mysql.",
    )


@pytest.fixture(scope="session")
def db_container(request) -> dict[str, object]:
    """Start the live DB container and yield its connection settings.

    ``sqlite`` (default) starts nothing and yields ``{}``; ``postgres`` /
    ``mysql`` start the container and yield only the connection fields
    (ENGINE/NAME/USER/PASSWORD/HOST/PORT) derived from the running container,
    so the dynamic host port is captured.
    """
    kind = request.config.getoption("--db")
    if kind == "sqlite":
        yield {}
        return

    try:
        ensure_docker_available()
    except RuntimeError as exc:
        pytest.skip(f"docker unavailable for --db={kind}: {exc}", allow_module_level=True)

    stack = build_db_stack(kind)
    with stack:
        yield stack.django_database_config()


@pytest.fixture(scope="session")
def django_db_modify_db_settings(
    django_db_modify_db_settings_parallel_suffix,
    db_container,
) -> None:
    """Override pytest-django's hook: merge the live DB connection into DATABASES.

    pytest-django's ``django_db_setup`` depends on this fixture by name, so
    defining it here (same name) overrides the plugin's and runs right before
    the test databases are created. ``update`` preserves the existing keys
    (``ATOMIC_REQUESTS``, ``TIME_ZONE``, ``TEST``, ...) and only swaps the
    connection fields. ``django_db_modify_db_settings_parallel_suffix`` keeps
    pytest-django's tox/xdist test-DB suffixing intact.
    """
    settings = django.conf.settings.DATABASES["default"]
    settings.update(db_container)
