# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""Tests for the Slurm cluster-ingest engine (``coldfront.slurm.ingest``).

``ingest_cluster_from_api`` reads the live REST partition_info shape.
"""

from django.test import TestCase

from coldfront.slurm.models import SlurmPartition


class ImportClusterFromApiTestCase(TestCase):
    """ingest_cluster_from_api reads the live REST partition_info shape."""

    def test_captures_max_time_and_default_time_from_nested_shape(self):
        from coldfront.slurm.ingest import ingest_cluster_from_api
        from tests.slurm.test_export_config import _rest_partition

        class _FakeApiClient:
            def __init__(self, part):
                self.part = part

            def get_partitions(self):
                return {"partitions": [self.part]}

            def get_qos(self):
                return {"qos": []}

        # Maximums/time is the live NO_VAL struct; MaxTime=UNLIMITED.
        part = _rest_partition("cpu", nodes="c1", max_time_infinite=True)
        # Defaults/time set -> DefaultTime=00:30:00.
        part["defaults"]["time"] = {"infinite": False, "number": 30, "set": True}
        client = _FakeApiClient(part)

        report = ingest_cluster_from_api("hpc", client=client)
        self.assertTrue(report.success)
        partition = SlurmPartition.objects.get(cluster__name="hpc", name="cpu")
        self.assertTrue(partition.max_time.is_unlimited())
        self.assertEqual(partition.default_time.to_seconds(), 30 * 60)
