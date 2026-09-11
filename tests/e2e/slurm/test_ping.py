# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Smoke test: ColdFront's Slurm REST client against a live slurmrestd.

This is the first e2e test — it proves the whole chain works end to end:

1. the docker compose stack brings up a real slurmdbd/slurmctld/slurmrestd,
2. ``scontrol token`` yields an admin JWT,
3. :meth:`SlurmClient.discover_version` negotiates the correct API version
   against the live ``/slurmdb/{version}/ping/`` endpoints,
4. authenticated reads (partitions/config) succeed via JWT.

Run with::

    COLDFRONT_E2E=1 COLDFRONT_ENV=.env.testing uv run -m pytest tests/e2e/slurm/
"""

import pytest


@pytest.mark.e2e
class TestPing:
    def test_discover_version_against_live_restd(self, slurm_stack, slurm_client):
        """The client should negotiate the API version the live stack actually ships."""
        version = slurm_client.discover_version()
        assert version == slurm_stack.api_version

    def test_authenticated_config_read(self, slurm_stack, slurm_client):
        """JWT auth works: an authenticated GET returns the cluster config."""
        if slurm_client.version is None:
            slurm_client.discover_version()
        config = slurm_client.get_config()
        # slurmrestd returns a config record for the cluster.
        assert "meta" in config
        assert config.get("errors", []) == []

    def test_partitions_list(self, slurm_stack, slurm_client):
        """The live cluster exposes the cpu partition defined in slurm.conf."""
        if slurm_client.version is None:
            slurm_client.discover_version()
        partitions = slurm_client.get_partitions()
        # The partition name is the ``name`` field; ``partition`` is an object.
        names = {p.get("name", "") for p in partitions.get("partitions", [])}
        assert "cpu" in names
