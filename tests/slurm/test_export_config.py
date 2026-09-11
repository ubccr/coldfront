# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for partition-config generation (``coldfront.slurm.export.config``).

Covers:
- fetch_partition_config: REST partition_info -> canonical section dicts.
- merge_partition_config: "DB present AND != running" wins + changed; else
  keep running.
- diff_partition_config: structured per-partition, per-field changes.
- render_partition_section: canonical PartitionName line format.
- generate_partition_config: merged vs DB-only fallback.

The REST payloads mirror the live ``GET /partitions/`` shape probed against
Slurm 26.05.x (v0.0.45).
"""

from typing import Any

from django.test import TestCase

from coldfront.slurm.export import (
    db_partition_config,
    diff_partition_config,
    fetch_partition_config,
    generate_partition_config,
    merge_partition_config,
    render_partition_section,
)
from coldfront.slurm.models import SlurmCluster, SlurmPartition, SlurmQOS
from coldfront.slurm.parser import parse_slurm_time


def _no_val(infinite: bool = False, number: int = 0, set: bool = False) -> dict[str, Any]:
    return {"infinite": infinite, "number": number, "set": set}


def _rest_partition(
    name: str,
    nodes: str = "",
    default: bool = False,
    max_time_infinite: bool = False,
    billing: str = "",
) -> dict[str, Any]:
    """Build a live-shaped partition_info dict for ``GET /partitions/``."""
    return {
        "name": name,
        "nodes": {"allowed_allocation": "", "configured": nodes, "total": 1 if nodes else 0},
        "accounts": {"allowed": "", "deny": ""},
        "groups": {"allowed": ""},
        "qos": {"allowed": "", "assigned": "", "deny": ""},
        "alternate": "",
        "tres": {"billing_weights": billing, "configured": ""},
        "cluster": "",
        "select_type": ["NONE"],
        "cpus": {"task_binding": [], "total": 6},
        "defaults": {
            "job": "",
            "memory_per_cpu": 0,
            "partition_memory_per_cpu": _no_val(),
            "partition_memory_per_node": _no_val(),
            "time": _no_val(),
        },
        "flags": ["DEFAULT"] if default else [],
        "partition": {"exclusive": "NO", "oversubscribe": "NO", "state": ["UP"]},
        "grace_time": 0,
        "maximums": {
            "cpus_per_node": _no_val(infinite=True),
            "cpus_per_socket": _no_val(infinite=True),
            "memory_per_cpu": 0,
            "nodes": _no_val(infinite=True),
            "over_time_limit": _no_val(),
            "oversubscribe": {"flags": [], "jobs": 0},
            "partition_memory_per_cpu": _no_val(),
            "partition_memory_per_node": _no_val(set=True),
            "shares": 0,
            "time": _no_val(infinite=max_time_infinite),
        },
        "minimums": {"nodes": 0},
        "node_sets": nodes,
        "preempt_mode": ["CLUSTER_GLOBAL"],
        "priority": {"job_factor": 1, "tier": 1},
        "timeouts": {"resume": _no_val(), "suspend": _no_val()},
        "topology": "",
        "suspend_time": _no_val(),
    }


class _FakeClient:
    """Minimal SlurmClient stub returning a canned GET /partitions/ body."""

    def __init__(self, parts: list[dict[str, Any]]):
        self._parts = parts

    def get_partitions(self, *args, **kwargs):  # noqa: ARG002
        return {"partitions": self._parts}


class FetchPartitionConfigTestCase(TestCase):
    """fetch_partition_config maps REST partition_info to canonical subparams."""

    def test_maps_live_shape(self):
        client = _FakeClient([_rest_partition("cpu", nodes="c1", default=True, max_time_infinite=True)])
        sections = fetch_partition_config(client)
        self.assertEqual(len(sections), 1)
        section = sections[0]
        self.assertEqual(section["PartitionName"], "cpu")
        self.assertEqual(section["Nodes"], "c1")
        self.assertEqual(section["Default"], "YES")
        self.assertEqual(section["MaxTime"], "UNLIMITED")
        self.assertEqual(section["State"], "UP")
        self.assertEqual(section["NodeSets"], "c1")
        # Effective running defaults carried (UNLIMITED for unset limits).
        self.assertEqual(section["MaxNodes"], "UNLIMITED")
        self.assertEqual(section["MaxCPUsPerNode"], "UNLIMITED")

    def test_non_default_no_max_time(self):
        client = _FakeClient([_rest_partition("gpu", nodes="g1")])
        section = fetch_partition_config(client)[0]
        self.assertEqual(section["Default"], "NO")
        self.assertNotIn("MaxTime", section)
        self.assertEqual(section["State"], "UP")

    def test_billing_captured(self):
        client = _FakeClient([_rest_partition("cpu", nodes="c1", billing="CPU=2.0,Node=3.0")])
        section = fetch_partition_config(client)[0]
        self.assertEqual(section["TRESBillingWeights"], "CPU=2.0,Node=3.0")

    def test_deny_qos_captured(self):
        part = _rest_partition("cpu", nodes="c1")
        part["qos"] = {"allowed": "", "assigned": "", "deny": "gpu"}
        sections = fetch_partition_config(_FakeClient([part]))
        self.assertEqual(sections[0]["DenyQOS"], "gpu")


class MergePartitionConfigTestCase(TestCase):
    """merge_partition_config: DB wins only when present AND different."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc")
        cls.part = SlurmPartition.objects.create(cluster=cls.cluster, name="cpu")
        cls.qos = SlurmQOS.objects.create(name="gpu")

    def test_db_overrides_running_when_different(self):
        self.part.max_nodes = 8
        self.part.save()
        db = db_partition_config(self.cluster)
        running = [{"PartitionName": "cpu", "Nodes": "c1", "MaxNodes": "UNLIMITED", "Default": "YES"}]
        merged, changed = merge_partition_config(db, running)
        self.assertEqual(merged[0]["MaxNodes"], "8")
        self.assertIn("MaxNodes", changed["cpu"])

    def test_running_kept_when_db_absent(self):
        db = db_partition_config(self.cluster)  # no max_nodes set
        running = [{"PartitionName": "cpu", "Nodes": "c1", "MaxNodes": "UNLIMITED"}]
        merged, changed = merge_partition_config(db, running)
        self.assertEqual(merged[0]["MaxNodes"], "UNLIMITED")
        self.assertEqual(changed, {})

    def test_running_kept_when_db_equal(self):
        self.part.max_nodes = 4
        self.part.save()
        db = db_partition_config(self.cluster)
        running = [{"PartitionName": "cpu", "Nodes": "c1", "MaxNodes": "4"}]
        merged, changed = merge_partition_config(db, running)
        self.assertEqual(merged[0]["MaxNodes"], "4")
        self.assertEqual(changed, {})

    def test_db_only_partition_added(self):
        self.part.max_nodes = 8
        self.part.save()
        db = db_partition_config(self.cluster)
        running = []
        merged, changed = merge_partition_config(db, running)
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["PartitionName"], "cpu")
        self.assertIn("MaxNodes", changed["cpu"])

    def test_db_renders_max_time_and_default_time_canonical(self):
        # UNLIMITED renders as MaxTime=UNLIMITED; finite as HH:MM:SS.
        self.part.max_time = parse_slurm_time("UNLIMITED")
        self.part.default_time = parse_slurm_time("00:30:00")
        self.part.save()
        db = db_partition_config(self.cluster)
        self.assertEqual(db[0]["MaxTime"], "UNLIMITED")
        self.assertEqual(db[0]["DefaultTime"], "00:30:00")


class DiffPartitionConfigTestCase(TestCase):
    """diff_partition_config reports running -> merged per field."""

    def test_changes_only(self):
        running = [{"PartitionName": "cpu", "Nodes": "c1", "MaxTime": "UNLIMITED", "State": "UP"}]
        merged = [{"PartitionName": "cpu", "Nodes": "c1", "MaxTime": "UNLIMITED", "MaxNodes": "8"}]
        diffs = diff_partition_config(merged, running)
        self.assertIn("cpu", diffs)
        self.assertEqual(diffs["cpu"]["MaxNodes"], ("", "8"))
        self.assertNotIn("MaxTime", diffs["cpu"])


class RenderPartitionSectionTestCase(TestCase):
    """render_partition_section emits canonical key=value lines."""

    def test_renders_non_empty_in_order(self):
        section = {
            "PartitionName": "cpu",
            "Nodes": "c1",
            "Default": "YES",
            "MaxTime": "UNLIMITED",
            "State": "UP",
            "MaxNodes": "8",
        }
        rendered = render_partition_section(section)
        self.assertEqual(
            rendered,
            "PartitionName=cpu Nodes=c1 Default=YES MaxTime=UNLIMITED MaxNodes=8 State=UP",
        )

    def test_omits_empty_values(self):
        section = {"PartitionName": "cpu", "Nodes": "c1", "MaxTime": "", "State": ""}
        self.assertEqual(render_partition_section(section), "PartitionName=cpu Nodes=c1")


class GeneratePartitionConfigTestCase(TestCase):
    """generate_partition_config: merged with client, DB-only fallback."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc")
        SlurmPartition.objects.create(cluster=cls.cluster, name="cpu")

    def test_db_only_without_client(self):
        result = generate_partition_config(self.cluster)
        self.assertEqual(result["source"], "db")
        self.assertEqual(len(result["sections"]), 1)
        self.assertTrue(result["sections"][0].startswith("PartitionName=cpu"))

    def test_db_only_on_fetch_error(self):
        class _BoomClient:
            def get_partitions(self):
                raise RuntimeError("boom")

        result = generate_partition_config(self.cluster, _BoomClient())
        self.assertEqual(result["source"], "db")
        self.assertIn("boom", result["error"])
