# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Database container wrappers for the ColdFront DB-backend e2e suite.

:class:`DbStack` wraps a single testcontainers database container (PostgreSQL
or MySQL) and exposes a uniform :meth:`django_database_config` so the
``tests/conftest.py`` fixture can rewrite ``settings.DATABASES["default"]``
to point at the live container *before* pytest-django creates the test
database.
"""

from typing import Any

from testcontainers.community.mysql import MySqlContainer
from testcontainers.community.postgres import PostgresContainer

# Django engines for each live backend.
DJANGO_ENGINE_POSTGRES = "django.db.backends.postgresql"
DJANGO_ENGINE_MYSQL = "django.db.backends.mysql"

# Connection-mode normalization: testcontainers can return 0.0.0.0/::/localhost
# as the host on Linux; those are not connectable from the host, so fall back
# to loopback (the compose port is published on all interfaces).
_LOOPBACK_HOSTS = ("0.0.0.0", "::", "localhost", "")


def _normalize_host(host: str) -> str:
    return "127.0.0.1" if host in _LOOPBACK_HOSTS else host


class DbStack:
    """Uniform wrapper over a testcontainers database container.

    Subclasses pick the concrete container (``_CONTAINER_CLASS``), the Django
    engine (``_DJANGO_ENGINE``) and the credentials; the base handles
    lifecycle and builds the ``DATABASES["default"]`` dict from the live
    container.
    """

    _CONTAINER_CLASS: type[PostgresContainer | MySqlContainer]
    _DJANGO_ENGINE: str
    _USERNAME: str
    _PASSWORD: str
    _DBNAME: str
    _IMAGE: str

    def __init__(self, image: str | None = None) -> None:
        self._container = self._CONTAINER_CLASS(
            image=image or self._IMAGE,
            username=self._USERNAME,
            password=self._PASSWORD,
            dbname=self._DBNAME,
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Start the container and wait for it to be ready."""
        self._container.start()

    def stop(self) -> None:
        """Tear the container down (removes the container + its volume)."""
        self._container.stop()

    def __enter__(self) -> "DbStack":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.stop()

    # ------------------------------------------------------------------
    # Django configuration
    # ------------------------------------------------------------------

    def django_database_config(self) -> dict[str, Any]:
        """The ``settings.DATABASES["default"]`` dict pointing at the container.

        Built from the running container so the dynamic host port is captured.
        Django's ``setup_databases`` reads this lazily when pytest-django
        creates the ``test_coldfront`` database, so rewriting ``DATABASES`` in
        the session fixture is enough.
        """
        host = _normalize_host(self._container.get_container_host_ip())
        port = self._container.get_exposed_port(self._container.port)
        return {
            "ENGINE": self._DJANGO_ENGINE,
            "NAME": self._DBNAME,
            "USER": self._USERNAME,
            "PASSWORD": self._PASSWORD,
            "HOST": host,
            "PORT": str(port),
        }


class PostgresStack(DbStack):
    """A PostgreSQL server for the unit suite.

    The official image's ``POSTGRES_USER`` is a superuser, so Django's
    ``setup_databases`` can freely create/drop ``test_coldfront``.
    """

    _CONTAINER_CLASS = PostgresContainer
    _DJANGO_ENGINE = DJANGO_ENGINE_POSTGRES
    _USERNAME = "coldfront"
    _PASSWORD = "coldfront"
    _DBNAME = "coldfront"
    _IMAGE = "postgres:18"


class MySqlStack(DbStack):
    """A MariaDB server for the unit suite.

    Uses the **root** user: the official MariaDB image's non-root
    ``MARIADB_USER`` is granted only its own database and lacks the global
    ``CREATE DATABASE`` privilege Django needs to create ``test_coldfront``.
    Root has full privileges. ``MySqlContainer(username="root", password=...)``
    maps the password to ``MYSQL_ROOT_PASSWORD``, which the MariaDB image
    honours as a legacy alias for ``MARIADB_ROOT_PASSWORD``.
    """

    _CONTAINER_CLASS = MySqlContainer
    _DJANGO_ENGINE = DJANGO_ENGINE_MYSQL
    _USERNAME = "root"
    _PASSWORD = "coldfront"
    _DBNAME = "coldfront"
    _IMAGE = "mariadb:12"


def build_db_stack(backend: str) -> DbStack:
    """Build the stack for a ``COLDFRONT_TEST_DB`` backend name."""
    backend = backend.strip().lower()
    if backend == "postgres":
        return PostgresStack()
    if backend == "mysql":
        return MySqlStack()
    raise ValueError(f"unknown COLDFRONT_TEST_DB backend {backend!r}; expected sqlite | postgres | mysql")
