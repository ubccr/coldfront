# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import pytest

from coldfront.storage.backends.dummy import DummyBackend


@pytest.fixture(autouse=True)
def _reset_dummy_backend():
    """Isolate the DummyBackend shared per-cluster caches between tests."""
    DummyBackend.reset()
    yield
    DummyBackend.reset()
