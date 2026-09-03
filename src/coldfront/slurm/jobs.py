# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Slurm system jobs.

Periodic and on-demand jobs that drive the Slurm accounting sync:

* ``SlurmSyncJob`` — periodic batch sync (default daily).
* ``SlurmSyncNowJob`` — on-demand sync (triggered by admin via UI or CLI).
"""

from __future__ import annotations

import logging

from coldfront.core.jobs.registry import system_job
from coldfront.core.jobs.runner import JobRunner
from coldfront.core.notifications import send_system_notification
from coldfront.slurm.models import SlurmCluster
from coldfront.slurm.sync import _auto_sync_enabled, _resolve_catchup_range, _run_usage_sync

__all__ = (
    "SlurmSyncJob",
    "SlurmSyncNowJob",
    "SlurmUsageSyncJob",
    "SlurmUsageSyncNowJob",
)

logger = logging.getLogger(__name__)


@system_job(interval=1440)  # daily by default
class SlurmSyncJob(JobRunner):
    """
    Periodic batch sync of Slurm accounting.

    Runs a full reconciliation sync via :func:`run_sync` for all clusters.
    Respects the per-cluster ``auto_sync_enabled`` setting — when disabled
    for all clusters the job logs a message and returns without rescheduling.
    """

    class Meta:
        name = "coldfront.slurm.jobs.SlurmSyncJob"

    def run(self, *_args, **_kwargs):
        from coldfront.slurm.sync import run_sync

        # Check if any cluster has auto_sync enabled
        clusters = SlurmCluster.objects.all()
        enabled_clusters = [c for c in clusters if _auto_sync_enabled(c)]
        if not enabled_clusters:
            self.logger.info("Slurm auto sync disabled for all clusters — skipping scheduled batch")
            return None  # prevents rescheduling

        self.logger.info(
            "Starting Slurm batch sync for %d cluster(s)",
            len(enabled_clusters),
        )
        reports = run_sync()
        for r in reports:
            if r.success:
                self.logger.info(
                    "Cluster '%s' synced: %d accounts, %d associations, %d users created; %d associations deleted",
                    r.cluster,
                    r.accounts_created,
                    r.associations_created,
                    r.users_created,
                    r.associations_deleted,
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
        from coldfront.slurm.sync import run_sync

        self.logger.info("Starting on-demand Slurm sync (cluster_id=%s)", cluster_id)
        reports = run_sync(cluster_id=cluster_id)
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


@system_job(interval=1440)  # daily by default
class SlurmUsageSyncJob(JobRunner):
    """
    Periodic daily SU usage ingest for all clusters.

    Computes a capped catch-up range from ``SlurmCluster.last_usage_sync``
    and ingests per-account daily usage via :func:`_run_usage_sync`.
    """

    class Meta:
        name = "coldfront.slurm.jobs.SlurmUsageSyncJob"

    def run(self, *_args, **_kwargs):
        clusters = SlurmCluster.objects.all()
        if not clusters:
            self.logger.info("No Slurm clusters configured — skipping usage sync")
            return None  # prevents rescheduling

        ok = 0
        for cluster in clusters:
            rng = _resolve_catchup_range(cluster)
            if rng is None:
                self.logger.info(
                    "Cluster '%s': no days to sync (last=%s)",
                    cluster.name,
                    cluster.last_usage_sync,
                )
                continue
            start_day, end_day = rng
            report = _run_usage_sync(cluster, start_day, end_day)
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
    :func:`_resolve_catchup_range`.  Not registered as a periodic system
    job — enqueued as a single fire-and-forget task.
    """

    class Meta:
        name = "coldfront.slurm.jobs.SlurmUsageSyncNowJob"

    def run(self, *_args, cluster_id=None, start=None, end=None, **_kwargs):
        from datetime import date

        clusters = SlurmCluster.objects.all()
        if cluster_id is not None:
            clusters = clusters.filter(pk=cluster_id)
        if not clusters:
            self.logger.info("No Slurm clusters configured — skipping usage sync")
            return None

        for cluster in clusters:
            if start and end:
                start_day = date.fromisoformat(start)
                end_day = date.fromisoformat(end)
            else:
                rng = _resolve_catchup_range(cluster)
                if rng is None:
                    self.logger.info(
                        "Cluster '%s': no days to sync (last=%s)",
                        cluster.name,
                        cluster.last_usage_sync,
                    )
                    continue
                start_day, end_day = rng
            report = _run_usage_sync(cluster, start_day, end_day)
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
