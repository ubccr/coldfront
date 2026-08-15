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
from coldfront.slurm.models import SlurmCluster
from coldfront.slurm.sync import _auto_sync_enabled

__all__ = (
    "SlurmSyncJob",
    "SlurmSyncNowJob",
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


@system_job(interval=0)  # never reschedules — on-demand only
class SlurmSyncNowJob(JobRunner):
    """
    On-demand sync triggered by admin action (CLI ``--now`` or UI button).

    Runs a full reconciliation sync immediately.  Registered with
    interval=0 so it never reschedules — each invocation is a single
    fire-and-forget task.
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
