# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for Storage system jobs and management commands
(``coldfront.storage.jobs``, ``storage_sync``, ``storage_usage_sync``).

Organized by test class:

- ``TestSyncJob`` — periodic + on-demand reconciliation jobs
- ``TestUsageJobs`` — periodic + on-demand usage-only jobs
- ``TestSyncCommand`` — ``storage_sync`` management command
- ``TestUsageSyncCommand`` — ``storage_usage_sync`` management command
"""

from unittest import mock

from django.core.management import call_command
from django.test import TestCase

from coldfront.storage.models import StorageCluster
from coldfront.storage.sync import SyncReport


def _ok_report(cluster):
    """Build a synthetic success report for the storage sync drivers."""
    return SyncReport(cluster=cluster, success=True)


class TestSyncJob(TestCase):
    """Periodic + on-demand reconciliation jobs."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = StorageCluster.objects.create(
            name="hpc01",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )

    def test_skips_when_no_cluster_has_backend(self):
        from coldfront.storage.jobs import StorageSyncJob

        job = StorageSyncJob(mock.MagicMock())
        with mock.patch("coldfront.storage.jobs._clusters_with_backend", return_value=[]):
            with mock.patch("coldfront.storage.sync.sync_storage_clusters") as mock_sync:
                result = job.run()
        assert result is None  # prevents rescheduling
        mock_sync.assert_not_called()

    def test_runs_sync_when_clusters_configured(self):
        from coldfront.storage.jobs import StorageSyncJob

        job = StorageSyncJob(mock.MagicMock())
        with mock.patch(
            "coldfront.storage.sync.sync_storage_clusters",
            return_value=[_ok_report("hpc01")],
        ) as mock_sync:
            result = job.run()
        assert result is True
        mock_sync.assert_called_once_with(["hpc01"])

    def test_now_job_runs_for_cluster(self):
        from coldfront.storage.jobs import StorageSyncNowJob

        job = StorageSyncNowJob(mock.MagicMock())
        with mock.patch(
            "coldfront.storage.sync.sync_storage_clusters",
            return_value=[_ok_report("hpc01")],
        ) as mock_sync:
            result = job.run(cluster_id=self.cluster.pk)
        assert result is True
        mock_sync.assert_called_once_with(["hpc01"])

    def test_failure_notifies_admin(self):
        from coldfront.storage.jobs import StorageSyncJob

        job = StorageSyncJob(mock.MagicMock())
        failing = SyncReport(cluster="hpc01", errors=["boom"])
        with mock.patch("coldfront.storage.sync.sync_storage_clusters", return_value=[failing]):
            with mock.patch("coldfront.storage.jobs.send_system_notification") as mock_notify:
                result = job.run()
        assert result is True
        mock_notify.assert_called_once()
        assert mock_notify.call_args.kwargs["subject"] == "Storage quota sync failed: hpc01"


class TestUsageJobs(TestCase):
    """Periodic + on-demand usage-only jobs."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = StorageCluster.objects.create(
            name="hpc01",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )

    def test_skips_when_no_cluster_has_backend(self):
        from coldfront.storage.jobs import StorageUsageSyncJob

        job = StorageUsageSyncJob(mock.MagicMock())
        with mock.patch("coldfront.storage.jobs._clusters_with_backend", return_value=[]):
            with mock.patch("coldfront.storage.sync.sync_storage_usage") as mock_sync:
                result = job.run()
        assert result is None
        mock_sync.assert_not_called()

    def test_runs_usage_sync_when_clusters_configured(self):
        from coldfront.storage.jobs import StorageUsageSyncJob

        job = StorageUsageSyncJob(mock.MagicMock())
        with mock.patch(
            "coldfront.storage.sync.sync_storage_usage",
            return_value=[_ok_report("hpc01")],
        ) as mock_sync:
            result = job.run()
        assert result is True
        mock_sync.assert_called_once_with(["hpc01"])

    def test_now_job_runs_for_cluster(self):
        from coldfront.storage.jobs import StorageUsageSyncNowJob

        job = StorageUsageSyncNowJob(mock.MagicMock())
        with mock.patch(
            "coldfront.storage.sync.sync_storage_usage",
            return_value=[_ok_report("hpc01")],
        ) as mock_sync:
            result = job.run(cluster_id=self.cluster.pk)
        assert result is True
        mock_sync.assert_called_once_with(["hpc01"])


class TestSyncCommand(TestCase):
    """The ``storage_sync`` management command."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = StorageCluster.objects.create(name="hpc01")

    def test_syncs_all_clusters(self):
        with mock.patch(
            "coldfront.storage.sync.sync_storage_clusters",
            return_value=[_ok_report("hpc01")],
        ) as mock_sync:
            call_command("storage_sync", verbosity=0)
        mock_sync.assert_called_once_with(None, dry_run=False)

    def test_syncs_cluster_by_name(self):
        with mock.patch(
            "coldfront.storage.sync.sync_storage_clusters",
            return_value=[_ok_report("hpc01")],
        ) as mock_sync:
            call_command("storage_sync", cluster="hpc01", verbosity=0)
        mock_sync.assert_called_once_with(["hpc01"], dry_run=False)

    def test_dry_run(self):
        with mock.patch(
            "coldfront.storage.sync.sync_storage_clusters",
            return_value=[_ok_report("hpc01")],
        ) as mock_sync:
            call_command("storage_sync", dry_run=True, verbosity=0)
        mock_sync.assert_called_once_with(None, dry_run=True)

    def test_unknown_cluster_errors(self):
        with mock.patch("coldfront.storage.sync.sync_storage_clusters") as mock_sync:
            call_command("storage_sync", cluster="nope", verbosity=0)
        assert not mock_sync.called


class TestUsageSyncCommand(TestCase):
    """The ``storage_usage_sync`` management command."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = StorageCluster.objects.create(name="hpc01")

    def test_syncs_all_clusters(self):
        with mock.patch(
            "coldfront.storage.sync.sync_storage_usage",
            return_value=[_ok_report("hpc01")],
        ) as mock_sync:
            call_command("storage_usage_sync", verbosity=0)
        mock_sync.assert_called_once_with(None)

    def test_syncs_cluster_by_name(self):
        with mock.patch(
            "coldfront.storage.sync.sync_storage_usage",
            return_value=[_ok_report("hpc01")],
        ) as mock_sync:
            call_command("storage_usage_sync", cluster="hpc01", verbosity=0)
        mock_sync.assert_called_once_with(["hpc01"])

    def test_unknown_cluster_errors(self):
        with mock.patch("coldfront.storage.sync.sync_storage_usage") as mock_sync:
            call_command("storage_usage_sync", cluster="nope", verbosity=0)
        assert not mock_sync.called
