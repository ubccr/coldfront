# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from coldfront.core.jobs.registry import system_jobs


@pytest.fixture(autouse=True)
def system_jobs_isolated():
    """
    Snapshot and restore the shared ``system_jobs`` registry around every test
    in ``tests/jobs`` so runner classes registered by test-local decorators
    cannot leak into other tests.

    The registry is a module-global dict shared by reference across several
    modules (``registry.py``, ``jobs/__init__.py``, ``runner.py``,
    ``taskworker.py``), so it must be mutated in place (clear + update) rather
    than rebound.
    """
    original = dict(system_jobs)
    yield
    system_jobs.clear()
    system_jobs.update(original)
