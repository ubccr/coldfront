# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Slurm system jobs and management commands
(``coldfront.slurm.jobs``, ``slurm_sync``, ``slurm_usage_sync``).

Organized by test class:

- ``TestUsageJobs`` — periodic + on-demand usage jobs
- ``TestUsageSyncCommand`` — ``slurm_usage_sync`` management command
- ``TestSyncJob`` — periodic batch association sync job
- ``TestSyncNowJob`` — on-demand association sync job
- ``TestSyncCommand`` — ``slurm_sync`` management command
"""

from datetime import date, timedelta
from unittest import mock

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from coldfront.slurm.models import SlurmCluster


class TestUsageJobs(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")

    def test_periodic_job_calls_run_usage_sync(self):
        from coldfront.slurm.jobs import SlurmUsageSyncJob

        job = SlurmUsageSyncJob(mock.MagicMock())
        yesterday = timezone.localdate() - timedelta(days=1)
        with (
            mock.patch("coldfront.slurm.jobs.slurmrestd_configured", return_value=True),
            mock.patch(
                "coldfront.slurm.jobs.resolve_catchup_range",
                return_value=(yesterday - timedelta(days=2), yesterday),
            ) as mock_range,
            mock.patch("coldfront.slurm.jobs.run_usage_sync") as mock_sync,
        ):
            mock_sync.return_value.success = True
            result = job.run()
        assert result is True
        mock_range.assert_called_once()
        mock_sync.assert_called_once()
        # cluster arg is the real cluster instance
        assert mock_sync.call_args[0][0] == self.cluster
        assert mock_sync.call_args[0][1] == yesterday - timedelta(days=2)
        assert mock_sync.call_args[0][2] == yesterday

    def test_periodic_job_no_days_to_sync(self):
        from coldfront.slurm.jobs import SlurmUsageSyncJob

        job = SlurmUsageSyncJob(mock.MagicMock())
        with (
            mock.patch("coldfront.slurm.jobs.slurmrestd_configured", return_value=True),
            mock.patch(
                "coldfront.slurm.jobs.resolve_catchup_range",
                return_value=None,
            ) as mock_range,
            mock.patch(
                "coldfront.slurm.jobs.run_usage_sync",
            ) as mock_sync,
        ):
            result = job.run()
        assert result is True
        mock_range.assert_called_once()
        mock_sync.assert_not_called()

    def test_periodic_job_skips_when_no_cluster_configured(self):
        """No cluster has slurmrestd configured -> return None (no reschedule)."""
        from coldfront.slurm.jobs import SlurmUsageSyncJob

        job = SlurmUsageSyncJob(mock.MagicMock())
        with mock.patch("coldfront.slurm.jobs.slurmrestd_configured", return_value=False):
            result = job.run()
        assert result is None

    def test_on_demand_job_with_explicit_range(self):
        from coldfront.slurm.jobs import SlurmUsageSyncNowJob

        job = SlurmUsageSyncNowJob(mock.MagicMock())
        start = "2024-01-01"
        end = "2024-01-10"
        with mock.patch("coldfront.slurm.jobs.slurmrestd_configured", return_value=True):
            with mock.patch("coldfront.slurm.jobs.run_usage_sync") as mock_sync:
                mock_sync.return_value.success = True
                result = job.run(cluster_id=self.cluster.pk, start=start, end=end)
        assert result is True
        mock_sync.assert_called_once()
        assert mock_sync.call_args[0][0] == self.cluster
        assert mock_sync.call_args[0][1] == date(2024, 1, 1)
        assert mock_sync.call_args[0][2] == date(2024, 1, 10)


class TestUsageSyncCommand(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")

    def test_command_runs_range_sync(self):
        with mock.patch("coldfront.slurm.sync.run_usage_sync") as mock_sync:
            mock_sync.return_value.success = True
            call_command("slurm_usage_sync", cluster="hpc01", verbosity=0)
        assert mock_sync.called
        assert mock_sync.call_args[0][0] == self.cluster

    def test_command_with_explicit_dates(self):
        with mock.patch("coldfront.slurm.sync.run_usage_sync") as mock_sync:
            mock_sync.return_value.success = True
            call_command(
                "slurm_usage_sync",
                cluster="hpc01",
                start="2024-01-01",
                end="2024-01-05",
                verbosity=0,
            )
        assert mock_sync.call_args[0][1] == date(2024, 1, 1)
        assert mock_sync.call_args[0][2] == date(2024, 1, 5)

    def test_command_unknown_cluster_errors(self):
        with mock.patch("coldfront.slurm.sync.run_usage_sync") as mock_sync:
            call_command("slurm_usage_sync", cluster="nope", verbosity=0)
        assert not mock_sync.called


def _ok_report(cluster):
    """Build a synthetic success report for sync_slurm_clusters."""
    return mock.MagicMock(
        success=True,
        cluster=cluster,
        accounts_created=0,
        associations_created=0,
        users_created=0,
        qos_synced=0,
        associations_deleted=0,
        users_deleted=0,
        accounts_deleted=0,
        qos_deleted=0,
        jobs_killed=0,
        duration_ms=0,
        errors=[],
    )


class TestSyncJob(TestCase):
    """Periodic batch association-sync job (SlurmSyncJob)."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")

    def test_skips_when_no_cluster_configured(self):
        """When no cluster has slurmrestd configured, return None (no reschedule)."""
        from coldfront.slurm.jobs import SlurmSyncJob

        job = SlurmSyncJob(mock.MagicMock())
        with mock.patch("coldfront.slurm.jobs.slurmrestd_configured", return_value=False):
            with mock.patch("coldfront.slurm.sync.sync_slurm_clusters") as mock_sync:
                result = job.run()
        assert result is None  # prevents rescheduling
        mock_sync.assert_not_called()

    def test_runs_sync_when_clusters_configured(self):
        """With a cluster configured, sync_slurm_clusters is called with its name."""
        from coldfront.slurm.jobs import SlurmSyncJob

        job = SlurmSyncJob(mock.MagicMock())
        with mock.patch("coldfront.slurm.jobs.slurmrestd_configured", return_value=True):
            with mock.patch(
                "coldfront.slurm.sync.sync_slurm_clusters",
                return_value=[_ok_report("hpc01")],
            ) as mock_sync:
                result = job.run()
        assert result is True
        mock_sync.assert_called_once_with(["hpc01"])


class TestSyncNowJob(TestCase):
    """On-demand association-sync job (SlurmSyncNowJob)."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")

    def test_runs_sync_for_cluster(self):
        from coldfront.slurm.jobs import SlurmSyncNowJob

        job = SlurmSyncNowJob(mock.MagicMock())
        with mock.patch(
            "coldfront.slurm.sync.sync_slurm_clusters",
            return_value=[_ok_report("hpc01")],
        ) as mock_sync:
            result = job.run(cluster_id=self.cluster.pk)
        assert result is True
        mock_sync.assert_called_once_with(["hpc01"])


class TestSyncCommand(TestCase):
    """The ``slurm_sync`` management command."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")

    def test_syncs_all_clusters(self):
        with mock.patch(
            "coldfront.slurm.sync.sync_slurm_clusters",
            return_value=[_ok_report("hpc01")],
        ) as mock_sync:
            call_command("slurm_sync", verbosity=0)
        mock_sync.assert_called_once_with(None)

    def test_syncs_cluster_by_name(self):
        with mock.patch(
            "coldfront.slurm.sync.sync_slurm_clusters",
            return_value=[_ok_report("hpc01")],
        ) as mock_sync:
            call_command("slurm_sync", cluster="hpc01", verbosity=0)
        mock_sync.assert_called_once_with(["hpc01"])

    def test_syncs_cluster_by_pk(self):
        with mock.patch(
            "coldfront.slurm.sync.sync_slurm_clusters",
            return_value=[_ok_report("hpc01")],
        ) as mock_sync:
            call_command("slurm_sync", cluster=str(self.cluster.pk), verbosity=0)
        mock_sync.assert_called_once_with(["hpc01"])

    def test_unknown_cluster_errors(self):
        with mock.patch("coldfront.slurm.sync.sync_slurm_clusters") as mock_sync:
            call_command("slurm_sync", cluster="nope", verbosity=0)
        assert not mock_sync.called
