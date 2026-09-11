# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Slurm system jobs.

Periodic and on-demand jobs that drive the Slurm accounting sync:

* ``SlurmSyncJob`` — periodic batch access-control sync.
* ``SlurmSyncNowJob`` — on-demand access-control sync (admin-triggered).
* ``SlurmUsageSyncJob`` — periodic SU usage ingest.
* ``SlurmUsageSyncNowJob`` — on-demand SU usage ingest.

Both sync paths are batch-only: they call the single reconciliation code path
(``sync_slurm_clusters`` for access-control, ``run_usage_sync`` for usage) and
skip clusters that have no slurmrestd configured.
"""

import logging

from django.conf import settings

from coldfront.core.jobs.registry import system_job
from coldfront.core.jobs.runner import JobRunner
from coldfront.core.notifications import send_system_notification
from coldfront.slurm.models import SlurmCluster
from coldfront.slurm.sync import resolve_catchup_range, run_usage_sync
from coldfront.slurm.utils import slurmrestd_configured

__all__ = (
    "SlurmSyncJob",
    "SlurmSyncNowJob",
    "SlurmUsageSyncJob",
    "SlurmUsageSyncNowJob",
)

logger = logging.getLogger(__name__)


@system_job(interval=settings.SLURM_SYNC_INTERVAL)
class SlurmSyncJob(JobRunner):
    """
    Periodic batch sync of Slurm accounting.

    Runs a full reconciliation sync via :func:`sync_slurm_clusters` for all
    clusters that have slurmrestd configured. Clusters without slurmrestd are
    skipped; when none are configured the job logs a message and returns
    without rescheduling.
    """

    class Meta:
        name = "coldfront.slurm.jobs.SlurmSyncJob"

    def run(self, *_args, **_kwargs):
        from coldfront.slurm.sync import sync_slurm_clusters

        clusters = SlurmCluster.objects.all()
        configured = [c for c in clusters if slurmrestd_configured(c)]
        if not configured:
            self.logger.info("No Slurm clusters have slurmrestd configured — skipping scheduled batch")
            return None  # prevents rescheduling

        self.logger.info(
            "Starting Slurm batch sync for %d cluster(s)",
            len(configured),
        )
        reports = sync_slurm_clusters([c.name for c in configured])
        for r in reports:
            if r.success:
                self.logger.info(
                    "Cluster '%s' synced: %d accounts, %d associations, %d users created, %d QOS synced; "
                    "%d assocs / %d users / %d accounts / %d QOS deleted, %d jobs killed",
                    r.cluster,
                    r.accounts_created,
                    r.associations_created,
                    r.users_created,
                    r.qos_synced,
                    r.associations_deleted,
                    r.users_deleted,
                    r.accounts_deleted,
                    r.qos_deleted,
                    r.jobs_killed,
                )
            else:
                self.logger.warning(
                    "Cluster '%s' sync failed: %s",
                    r.cluster,
                    "; ".join(r.errors),
                )
        self.logger.info(
            "Slurm batch sync finished: %d/%d clusters OK",
            sum(1 for r in reports if r.success),
            len(reports),
        )
        return True


class SlurmSyncNowJob(JobRunner):
    """
    On-demand sync triggered by admin action (CLI ``--now`` or UI button).

    Runs a full reconciliation sync immediately.  Not registered as a
    periodic system job — it is enqueued as a single fire-and-forget task
    and never reschedules.
    """

    class Meta:
        name = "coldfront.slurm.jobs.SlurmSyncNowJob"

    def run(self, *_args, cluster_id=None, **_kwargs):
        from coldfront.slurm.sync import sync_slurm_clusters

        names = None
        if cluster_id is not None:
            cluster = SlurmCluster.objects.get(pk=cluster_id)
            names = [cluster.name]

        self.logger.info("Starting on-demand Slurm sync (cluster_id=%s)", cluster_id)
        reports = sync_slurm_clusters(names)
        for r in reports:
            if r.success:
                self.logger.info(
                    "Cluster '%s' synced OK (%d ms)",
                    r.cluster,
                    r.duration_ms,
                )
            else:
                self.logger.warning(
                    "Cluster '%s' sync failed: %s",
                    r.cluster,
                    "; ".join(r.errors),
                )
        self.logger.info(
            "On-demand sync finished: %d/%d clusters OK",
            sum(1 for r in reports if r.success),
            len(reports),
        )
        return True


@system_job(interval=settings.SLURM_USAGE_SYNC_INTERVAL)
class SlurmUsageSyncJob(JobRunner):
    """
    Periodic daily SU usage ingest for all configured clusters.

    Computes a capped catch-up range from ``SlurmCluster.last_usage_sync``
    and ingests per-account daily usage via :func:`run_usage_sync`.
    """

    class Meta:
        name = "coldfront.slurm.jobs.SlurmUsageSyncJob"

    def run(self, *_args, **_kwargs):
        clusters = [c for c in SlurmCluster.objects.all() if slurmrestd_configured(c)]
        if not clusters:
            self.logger.info("No Slurm clusters have slurmrestd configured — skipping usage sync")
            return None  # prevents rescheduling

        ok = 0
        for cluster in clusters:
            rng = resolve_catchup_range(cluster)
            if rng is None:
                self.logger.info(
                    "Cluster '%s': no days to sync (last=%s)",
                    cluster.name,
                    cluster.last_usage_sync,
                )
                continue
            start_day, end_day = rng
            report = run_usage_sync(cluster, start_day, end_day)
            if report.success:
                ok += 1
                self.logger.info(
                    "Cluster '%s' usage synced: %d days, %d accounts, %d jobs",
                    report.cluster,
                    report.days_synced,
                    report.accounts_updated,
                    report.jobs_ingested,
                )
            else:
                self.logger.warning(
                    "Cluster '%s' usage sync failed: %s",
                    report.cluster,
                    "; ".join(report.errors),
                )
                # Notify admins so stale SU usage is surfaced promptly.
                send_system_notification(
                    target=cluster,
                    subject=f"SU usage sync failed: {cluster.name}",
                    text=(
                        f"The daily SU usage sync for cluster '{cluster.name}' failed.\n"
                        f"Errors:\n" + "\n".join(f"- {e}" for e in report.errors)
                    ),
                )
        self.logger.info(
            "Slurm usage sync finished: %d/%d clusters OK",
            ok,
            len(clusters),
        )
        return True


class SlurmUsageSyncNowJob(JobRunner):
    """
    On-demand SU usage ingest (admin-triggered).

    If ``start``/``end`` (YYYY-MM-DD) are given, ingests exactly that range.
    Otherwise runs the normal capped catch-up range via
    :func:`resolve_catchup_range`.  Not registered as a periodic system
    job — enqueued as a single fire-and-forget task.
    """

    class Meta:
        name = "coldfront.slurm.jobs.SlurmUsageSyncNowJob"

    def run(self, *_args, cluster_id=None, start=None, end=None, **_kwargs):
        from datetime import date

        clusters = [c for c in SlurmCluster.objects.all() if slurmrestd_configured(c)]
        if cluster_id is not None:
            clusters = [c for c in clusters if c.pk == cluster_id]
        if not clusters:
            self.logger.info("No Slurm clusters have slurmrestd configured — skipping usage sync")
            return None

        for cluster in clusters:
            if start and end:
                start_day = date.fromisoformat(start)
                end_day = date.fromisoformat(end)
            else:
                rng = resolve_catchup_range(cluster)
                if rng is None:
                    self.logger.info(
                        "Cluster '%s': no days to sync (last=%s)",
                        cluster.name,
                        cluster.last_usage_sync,
                    )
                    continue
                start_day, end_day = rng
            report = run_usage_sync(cluster, start_day, end_day)
            if report.success:
                self.logger.info(
                    "Cluster '%s' usage synced: %d days, %d accounts, %d jobs",
                    report.cluster,
                    report.days_synced,
                    report.accounts_updated,
                    report.jobs_ingested,
                )
            else:
                self.logger.warning(
                    "Cluster '%s' usage sync failed: %s",
                    report.cluster,
                    "; ".join(report.errors),
                )
        return True
