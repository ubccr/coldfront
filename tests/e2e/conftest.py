# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Shared pytest configuration for ColdFront end-to-end (e2e) tests.

The e2e suite spins up real containers (Slurm, PostgreSQL, MySQL, ...) via
``testcontainers`` and is expensive. It is **disabled by default**:

* ``pyproject.toml`` adds ``-m "not e2e"`` to default ``addopts``, so plain
  ``pytest`` runs never collect the e2e tests.
* Even when run explicitly with ``pytest -m e2e``, every collected e2e test is
  skipped unless the ``COLDFRONT_E2E=1`` environment variable is set.

Generic e2e setup code that can be reused by all e2e test apps (container
wrappers, fixtures) lives here and in ``containers.py``.
"""

from __future__ import annotations

import os

import pytest

from tests.e2e.containers import ensure_docker_available

# Env gate: e2e tests only run when COLDFRONT_E2E=1 is set.
E2E_ENABLED = os.environ.get("COLDFRONT_E2E", "").strip() == "1"


def pytest_configure(config) -> None:
    """Register the ``e2e`` marker (also declared in pyproject.toml)."""
    config.addinivalue_line(
        "markers",
        "e2e: end-to-end test that spins up real containers via testcontainers (requires docker + COLDFRONT_E2E=1)",
    )


def pytest_collection_modifyitems(config, items) -> None:
    """Skip every e2e test unless the e2e suite is explicitly enabled.

    This is a second gate on top of the ``-m "not e2e"`` addopt: it lets
    ``pytest -m e2e`` collect the tests, but skips them unless
    ``COLDFRONT_E2E=1`` is set, so a forgotten env var can't silently launch
    containers.
    """
    if E2E_ENABLED:
        return
    for item in items:
        if _is_e2e_item(item):
            item.add_marker(
                pytest.mark.skip(
                    reason="e2e tests disabled (set COLDFRONT_E2E=1 to enable)",
                )
            )


def _is_e2e_item(item) -> bool:
    """True if the collected test lives under ``tests/e2e/``."""
    nodeid = item.nodeid
    # nodeid is relative to the rootdir, e.g. "tests/e2e/slurm/test_ping.py::..."
    return "/tests/e2e/" in nodeid or nodeid.startswith("tests/e2e/")


@pytest.fixture(scope="session", autouse=True)
def docker_available():
    """Skip every e2e test if the Docker daemon is not reachable.

    Autouse and session-scoped, so ``docker info`` is checked once per session
    and the whole e2e suite is skipped when Docker is unavailable.
    """
    try:
        ensure_docker_available()
    except RuntimeError as exc:
        pytest.skip(f"docker unavailable: {exc}", allow_module_level=True)
