# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Live partition-config e2e tests.

Probes the partition-config pipeline (``coldfront.slurm.export.config``) against the
live stack:

* ``fetch_partition_config`` reads the running config from
  ``GET /partitions/`` (version-agnostic — both supported versions expose GET).
* ``generate_partition_config`` merges ColdFront DB records over the running
  baseline, so the rendered ``PartitionName`` sections match the vendored
  slurm.conf partition lines, and DB edits show up as a structured diff.

The merge rule is exercised live: ColdFront's ``Nodes=cpu_nodes`` (the
conf-style NodeSet reference) wins over the running API's expanded node list
(``c1``), while ``MaxTime=UNLIMITED``/``State=UP`` flow from running because
they match the DB (DB present but equal -> keep running).
"""

from pathlib import Path

import pytest

from coldfront.slurm.export import generate_partition_config
from coldfront.slurm.ingest import ingest_cluster_from_conf
from coldfront.slurm.models import SlurmCluster, SlurmPartition

CONF_DIR = Path(__file__).resolve().parent / "config"


def _split_line(line: str) -> tuple[str, dict[str, str]]:
    """Split a PartitionName line into (name, {subparam: value})."""
    tokens = line.split()
    name = ""
    params: dict[str, str] = {}
    for token in tokens:
        key, _, value = token.partition("=")
        if key == "PartitionName":
            name = value
        else:
            params[key] = value
    return name, params


@pytest.mark.django_db
@pytest.mark.e2e
def test_partition_config_render_matches_vendored_conf(slurm_stack, slurm_client):
    """Merged render reproduces the vendored conf partition lines."""
    report = ingest_cluster_from_conf(str(CONF_DIR / "slurm.conf"))
    assert report.errors == [], f"import errors: {report.errors}"
    cluster = SlurmCluster.objects.get(name="linux")

    result = generate_partition_config(cluster, slurm_client)
    assert result["source"] == "merged", f"expected merged, got {result['source']}"

    sections = dict(_split_line(line) for line in result["sections"])
    # DB's Nodes (NodeSet reference) wins over running's expanded node list.
    cpu = sections["cpu"]
    assert cpu["Nodes"] == "cpu_nodes"
    assert cpu["Default"] == "YES"
    assert cpu["MaxTime"] == "UNLIMITED"
    assert cpu["State"] == "UP"

    gpu = sections["gpu"]
    assert gpu["Nodes"] == "gpu_nodes"
    assert gpu["Default"] == "NO"
    assert gpu["MaxTime"] == "UNLIMITED"
    assert gpu["State"] == "UP"


@pytest.mark.django_db
@pytest.mark.e2e
def test_partition_config_diff_reports_db_override(slurm_stack, slurm_client):
    """A DB-only field (TRESBillingWeights) appears as a structured diff."""
    cluster = SlurmCluster.objects.create(name="linux")
    SlurmPartition.objects.create(
        cluster=cluster,
        name="cpu",
        tres_billing_weights={"CPU": 2.0, "Node": 3.0},
    )

    result = generate_partition_config(cluster, slurm_client)
    assert result["source"] == "merged", f"expected merged, got {result['source']}"

    assert "cpu" in result["diff"], f"no cpu diff: {result['diff']}"
    running_value, merged_value = result["diff"]["cpu"]["TRESBillingWeights"]
    assert running_value == ""  # stock conf has no billing weights
    assert merged_value == "CPU=2.0,Node=3.0"

    # The merged render carries the DB override.
    sections = dict(_split_line(line) for line in result["sections"])
    assert sections["cpu"]["TRESBillingWeights"] == "CPU=2.0,Node=3.0"
