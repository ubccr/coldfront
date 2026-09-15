# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Storage system jobs.

Periodic and on-demand jobs that drive the storage quota sync:

* ``StorageSyncJob`` — periodic full reconciliation sync.
* ``StorageSyncNowJob`` — on-demand full reconciliation sync
  (admin-triggered).
* ``StorageUsageSyncJob`` — periodic usage-only sync.
* ``StorageUsageSyncNowJob`` — on-demand usage-only sync
  (admin-triggered).

Both sync paths are batch-only: they call the single reconciliation code
path (``sync_storage_clusters`` / ``sync_storage_usage``) and skip
clusters that have no backend configured.
"""

import logging

from django.conf import settings

from coldfront.core.jobs.registry import system_job
from coldfront.core.jobs.runner import JobRunner
from coldfront.core.notifications import send_system_notification
from coldfront.storage.models import StorageCluster

__all__ = (
    "StorageSyncJob",
    "StorageSyncNowJob",
    "StorageUsageSyncJob",
    "StorageUsageSyncNowJob",
)

logger = logging.getLogger(__name__)


def _clusters_with_backend(cluster_names=None):
    """Return clusters that have a backend configured.

    Args:
        cluster_names: Optional list of cluster names to restrict to.

    Returns:
        List of ``StorageCluster`` with ``backend_path`` set.
    """
    clusters = StorageCluster.objects.all()
    if cluster_names is not None:
        clusters = clusters.filter(name__in=cluster_names)
    return [c for c in clusters if c.backend_path is not None]


def _log_reports(reports, verb):
    """Log a list of ``SyncReport`` objects; notify admins on failures."""
    failing_clusters = []
    for report in reports:
        if report.success:
            logger.info(
                "Cluster '%s' synced: %d paths created, %d quotas created, %d quotas updated; "
                "%d paths locked, %d paths unlocked, %d quotas deleted; %d usage rows updated (%d ms)",
                report.cluster,
                report.paths_created,
                report.quotas_created,
                report.quotas_updated,
                report.paths_locked,
                report.paths_unlocked,
                report.quotas_deleted,
                report.usage_updated,
                report.duration_ms,
            )
        else:
            logger.warning("Cluster '%s' sync failed: %s", report.cluster, "; ".join(report.errors))
            failing_clusters.append(report.cluster)

    ok = sum(1 for r in reports if r.success)
    logger.info("Storage %s finished: %d/%d clusters OK", verb, ok, len(reports))

    # Notify admins so failed scheduled syncs are surfaced promptly.
    for name in failing_clusters:
        try:
            cluster = StorageCluster.objects.get(name=name)
        except StorageCluster.DoesNotExist:
            continue
        failure = next((r for r in reports if r.cluster == name and not r.success), None)
        send_system_notification(
            target=cluster,
            subject=f"Storage quota sync failed: {cluster.name}",
            text=(
                f"The storage quota sync for cluster '{cluster.name}' failed.\n"
                f"Errors:\n" + "\n".join(f"- {e}" for e in failure.errors)
            ),
        )


@system_job(cron_schedule=settings.STORAGE_SYNC_CRON)
class StorageSyncJob(JobRunner):
    """
    Periodic full reconciliation sync of storage quotas.

    Runs a full reconciliation sync via :func:`sync_storage_clusters` for
    all clusters that have a backend configured. Clusters without a
    backend are skipped; when none are configured the job logs a message
    and returns without rescheduling.
    """

    class Meta:
        name = "coldfront.storage.jobs.StorageSyncJob"

    def run(self, *_args, **_kwargs):
        from coldfront.storage.sync import sync_storage_clusters

        clusters = _clusters_with_backend()
        if not clusters:
            self.logger.info("No storage clusters have a backend configured — skipping scheduled sync")
            return None  # prevents rescheduling

        self.logger.info("Starting storage quota sync for %d cluster(s)", len(clusters))
        reports = sync_storage_clusters([c.name for c in clusters])
        _log_reports(reports, "sync")
        return True


class StorageSyncNowJob(JobRunner):
    """
    On-demand full reconciliation sync triggered by admin action.

    Runs a full reconciliation sync immediately.  Not registered as a
    periodic system job — it is enqueued as a single fire-and-forget task
    and never reschedules.
    """

    class Meta:
        name = "coldfront.storage.jobs.StorageSyncNowJob"

    def run(self, *_args, cluster_id=None, **_kwargs):
        from coldfront.storage.sync import sync_storage_clusters

        names = None
        if cluster_id is not None:
            cluster = StorageCluster.objects.get(pk=cluster_id)
            names = [cluster.name]

        self.logger.info("Starting on-demand storage quota sync (cluster_id=%s)", cluster_id)
        reports = sync_storage_clusters(names)
        _log_reports(reports, "on-demand sync")
        return True


@system_job(cron_schedule=settings.STORAGE_USAGE_SYNC_CRON)
class StorageUsageSyncJob(JobRunner):
    """
    Periodic usage-only sync for all configured clusters.

    Fetches all quotas once per cluster and pulls usage into the active
    quota rows via :func:`sync_storage_usage`.  Never mutates the
    backend.
    """

    class Meta:
        name = "coldfront.storage.jobs.StorageUsageSyncJob"

    def run(self, *_args, **_kwargs):
        from coldfront.storage.sync import sync_storage_usage

        clusters = _clusters_with_backend()
        if not clusters:
            self.logger.info("No storage clusters have a backend configured — skipping usage sync")
            return None  # prevents rescheduling

        self.logger.info("Starting storage usage sync for %d cluster(s)", len(clusters))
        reports = sync_storage_usage([c.name for c in clusters])
        _log_reports(reports, "usage sync")
        return True


class StorageUsageSyncNowJob(JobRunner):
    """
    On-demand usage-only sync (admin-triggered).

    Not registered as a periodic system job — enqueued as a single
    fire-and-forget task.
    """

    class Meta:
        name = "coldfront.storage.jobs.StorageUsageSyncNowJob"

    def run(self, *_args, cluster_id=None, **_kwargs):
        from coldfront.storage.sync import sync_storage_usage

        names = None
        if cluster_id is not None:
            cluster = StorageCluster.objects.get(pk=cluster_id)
            names = [cluster.name]

        self.logger.info("Starting on-demand storage usage sync (cluster_id=%s)", cluster_id)
        reports = sync_storage_usage(names)
        _log_reports(reports, "on-demand usage sync")
        return True
