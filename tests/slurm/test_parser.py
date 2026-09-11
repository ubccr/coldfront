# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for SU billing TRES configuration.

Covers:
- parse_slurm_conf: DEFAULT TRESBillingWeights, per-partition override, and
  the global PriorityFlags/PriorityType/PriorityDecayHalfLife/
  PriorityUsageResetPeriod captures (end-to-end from a sample slurm.conf).
- parse_tres_weights: raw string -> dict (empty -> {}).
- ingest_cluster_from_conf: writes only present keys, never sets
  enforce_su_limits.
"""

from pathlib import Path

from django.test import TestCase

from coldfront.slurm.ingest import ingest_cluster_from_conf
from coldfront.slurm.models import SlurmCluster, SlurmPartition
from coldfront.slurm.parser import parse_slurm_conf, parse_tres_weights

_CONF_DIR = Path(__file__).parent / "conf"
_CONF = str(_CONF_DIR / "slurm.conf")
_MINIMAL = str(_CONF_DIR / "minimal.conf")


class ParseSlurmConfTestCase(TestCase):
    """parse_slurm_conf captures the SU billing TRES configuration."""

    def test_global_priority_settings_captured(self):
        parsed = parse_slurm_conf(_CONF)
        self.assertEqual(parsed.priority_flags, "NO_NORMAL_TRES")
        self.assertEqual(parsed.priority_type, "priority/multifactor")
        self.assertEqual(parsed.priority_decay_half_life, "30-0")
        self.assertEqual(parsed.priority_usage_reset_period, "MONTHLY")

    def test_default_tres_billing_weights_absorbed_into_partitions(self):
        # DEFAULT's TRESBillingWeights flows into every partition unless
        # overridden (matching Slurm's _flush_partition_buffer and the REST
        # /partitions effective config). It is NOT captured cluster-wide.
        parsed = parse_slurm_conf(_CONF)
        normal = next(p for p in parsed.partitions if p.name == "normal")
        self.assertEqual(normal.tres_billing_weights, "CPU=1.0,Mem=0.25G,gres/gpu=2.0")
        gpu = next(p for p in parsed.partitions if p.name == "gpu")
        self.assertEqual(gpu.tres_billing_weights, "CPU=1.0,gres/gpu=2.5")

    def test_partition_override_captured(self):
        parsed = parse_slurm_conf(_CONF)
        gpu = next(p for p in parsed.partitions if p.name == "gpu")
        self.assertEqual(gpu.tres_billing_weights, "CPU=1.0,gres/gpu=2.5")
        # The DEFAULT template record is still present; import skips it.
        default = next(p for p in parsed.partitions if p.name.upper() == "DEFAULT")
        self.assertEqual(default.tres_billing_weights, "CPU=1.0,Mem=0.25G,gres/gpu=2.0")

    def test_no_billing_config_defaults_to_empty(self):
        parsed = parse_slurm_conf(_MINIMAL)
        normal = next(p for p in parsed.partitions if p.name == "normal")
        self.assertEqual(normal.tres_billing_weights, "")
        self.assertEqual(parsed.priority_flags, "")
        self.assertEqual(parsed.priority_type, "")


class ParseTresWeightsTestCase(TestCase):
    """parse_tres_weights raw string -> dict."""

    def test_empty_returns_empty_dict(self):
        self.assertEqual(parse_tres_weights(""), {})

    def test_parses_weights(self):
        self.assertEqual(
            parse_tres_weights("CPU=1.0,Mem=0.25G,gres/gpu=2.0"),
            {"CPU": 1.0, "Mem": 0.25, "gres/gpu": 2.0},
        )

    def test_ignores_malformed_tokens(self):
        self.assertEqual(parse_tres_weights("CPU=1.0,bogus,gres/gpu=abc"), {"CPU": 1.0})


class ImportClusterFromConfTestCase(TestCase):
    """ingest_cluster_from_conf writes present billing keys, never enforce_su_limits."""

    def test_creates_cluster_with_billing_config(self):
        report = ingest_cluster_from_conf(_CONF)
        self.assertTrue(report.success)
        cluster = SlurmCluster.objects.get(name="snowflake")
        self.assertEqual(cluster.priority_flags, ["NO_NORMAL_TRES"])
        self.assertEqual(cluster.priority_type, "priority/multifactor")
        self.assertEqual(cluster.priority_decay_half_life, "30-0")
        self.assertEqual(cluster.priority_usage_reset_period, "MONTHLY")
        # ColdFront-only toggle is never set by import
        self.assertFalse(cluster.enforce_su_limits)

    def test_partition_billing_weights_imported(self):
        ingest_cluster_from_conf(_CONF)
        partition = SlurmPartition.objects.get(cluster__name="snowflake", name="gpu")
        self.assertEqual(partition.tres_billing_weights, {"CPU": 1.0, "gres/gpu": 2.5})
        # normal inherits the DEFAULT template's billing
        normal = SlurmPartition.objects.get(cluster__name="snowflake", name="normal")
        self.assertEqual(normal.tres_billing_weights, {"CPU": 1.0, "Mem": 0.25, "gres/gpu": 2.0})

    def test_partition_max_time_and_default_time_imported(self):
        # MaxTime/DefaultTime were previously parsed but never written to the
        # DB (only default_time was); both are now captured as SlurmTime.
        ingest_cluster_from_conf(_CONF)
        normal = SlurmPartition.objects.get(cluster__name="snowflake", name="normal")
        self.assertEqual(normal.max_time.to_seconds(), 72 * 3600)  # MaxTime=72:00:00
        self.assertEqual(normal.default_time.to_seconds(), 30 * 60)  # DefaultTime=00:30:00
        # MaxTime=UNLIMITED maps to the UNLIMITED state, not a finite duration
        gpu = SlurmPartition.objects.get(cluster__name="snowflake", name="gpu")
        self.assertTrue(gpu.max_time.is_unlimited())
        self.assertIsNone(gpu.default_time)

    def test_update_writes_billing_keys_present(self):
        cluster = SlurmCluster.objects.create(name="snowflake", enforce_su_limits=True)
        report = ingest_cluster_from_conf(_CONF, update=True)
        self.assertTrue(report.success)
        cluster.refresh_from_db()
        self.assertEqual(cluster.priority_type, "priority/multifactor")
        # Hand-set ColdFront-only value is preserved on update
        self.assertTrue(cluster.enforce_su_limits)

    def test_missing_keys_left_default(self):
        ingest_cluster_from_conf(_MINIMAL)
        cluster = SlurmCluster.objects.get(name="bare")
        self.assertEqual(cluster.priority_flags, [])
        self.assertEqual(cluster.priority_type, "priority/multifactor")
        self.assertEqual(cluster.priority_decay_half_life, "7-0")
        self.assertEqual(cluster.priority_usage_reset_period, "NONE")
        self.assertFalse(cluster.enforce_su_limits)
