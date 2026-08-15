# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Storage sync engine.

Provides core synchronization logic between ColdFront's local models and
storage system backends.  Two entry points:

* ``run_sync()`` — full reconciliation sync for one or all clusters.
* ``_recalculate_used_bytes()`` — update resource/cluster used_bytes from
  active quota sums.

* ``enqueue_activate_allocation()`` — targeted handler for allocation
  activation.
* ``enqueue_deactivate_allocation()`` — targeted handler for allocation
  expire / revoke.

The ``enqueue_*()`` wrappers are thin — they check the auto-sync gate and
delegate to the task queue.  The actual backend logic is done by the
``_run_activate_allocation()`` / ``_run_deactivate_allocation()`` functions
so the CLI command can call them directly without going through the queue.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from django.db.models import Q, Sum
from django.utils import timezone

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SyncReport
# ---------------------------------------------------------------------------


@dataclass
class SyncReport:
    """Detailed report returned by sync operations."""

    cluster: str
    success: bool = False
    paths_created: int = 0
    paths_deleted: int = 0
    quotas_created: int = 0
    quotas_updated: int = 0
    quotas_deleted: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# Targeted handler wrappers (enqueue helpers)
# ---------------------------------------------------------------------------


def enqueue_activate_allocation(allocation_id: int, cluster_id: int, share_type: str = "posix") -> None:
    """Enqueue a targeted task to create path + quota on a cluster.

    Called by the ViewFlow callback when an allocation is activated.
    Respects the per-cluster ``auto_sync_enabled`` setting and skips
    clusters with no backend (``backend_path`` is null).
    """
    cluster = StorageCluster.objects.get(pk=cluster_id)
    if cluster.backend_path is None:
        logger.debug(
            "Storage cluster %s has no backend — skipping activate enqueue for allocation %s",
            cluster.name,
            allocation_id,
        )
        return
    if not cluster.auto_sync_enabled:
        logger.debug(
            "Storage auto sync disabled for cluster %s — skipping activate enqueue for allocation %s",
            cluster.name,
            allocation_id,
        )
        return

    logger.info("Enqueuing Storage activate for allocation %s on cluster %s", allocation_id, cluster.name)
    from coldfront.core.models import Job

    Job.enqueue(
        "coldfront.storage.sync._run_activate_allocation",
        name=f"StorageActivate:allocation-{allocation_id}:cluster-{cluster_id}",
        args=(),
        kwargs={
            "allocation_id": allocation_id,
            "cluster_id": cluster_id,
            "share_type": share_type,
        },
        priority=3,
    )


def enqueue_deactivate_allocation(allocation_id: int, cluster_id: int) -> None:
    """Enqueue a targeted task to remove quota on a cluster.

    Called by ViewFlow callbacks when an allocation is expired or revoked.
    Respects the per-cluster ``auto_sync_enabled`` setting and skips
    clusters with no backend (``backend_path`` is null).
    """
    cluster = StorageCluster.objects.get(pk=cluster_id)
    if cluster.backend_path is None:
        logger.debug(
            "Storage cluster %s has no backend — skipping deactivate enqueue for allocation %s",
            cluster.name,
            allocation_id,
        )
        return
    if not cluster.auto_sync_enabled:
        logger.debug(
            "Storage auto sync disabled for cluster %s — skipping deactivate enqueue for allocation %s",
            cluster.name,
            allocation_id,
        )
        return

    logger.info("Enqueuing Storage deactivate for allocation %s on cluster %s", allocation_id, cluster.name)
    from coldfront.core.models import Job

    Job.enqueue(
        "coldfront.storage.sync._run_deactivate_allocation",
        name=f"StorageDeactivate:allocation-{allocation_id}:cluster-{cluster_id}",
        args=(),
        kwargs={
            "allocation_id": allocation_id,
            "cluster_id": cluster_id,
        },
        priority=3,
    )


# ---------------------------------------------------------------------------
# Full reconciliation sync
# ---------------------------------------------------------------------------


def run_sync(cluster_id: int | None = None) -> list[SyncReport]:
    """Perform a full reconciliation sync for one or all storage clusters.

    For each cluster, queries active ``StorageQuota`` records, compares
    against the backend's current state, and creates/updates/deletes paths
    and quotas as needed.

    Args:
        cluster_id: Optional cluster PK.  If ``None``, syncs all clusters.

    Returns:
        List of ``SyncReport`` — one per cluster processed.
    """
    reports: list[SyncReport] = []

    clusters = StorageCluster.objects.all()
    if cluster_id is not None:
        clusters = clusters.filter(pk=cluster_id)

    for cluster in clusters:
        report = _sync_cluster(cluster)
        reports.append(report)

    # Recalculate used_bytes after all clusters are synced
    _recalculate_used_bytes()

    return reports


def _sync_cluster(cluster: StorageCluster) -> SyncReport:
    """Reconcile a single storage cluster with its backend."""
    from coldfront.storage.backends.registry import get_backend

    start = timezone.now()
    report = SyncReport(cluster=cluster.name, success=False)

    # ---- Step 0: Skip clusters with no backend ----
    if cluster.backend_path is None:
        logger.debug(
            "Storage cluster %s has no backend — skipping sync",
            cluster.name,
        )
        report.success = True
        report.duration_ms = int((timezone.now() - start).total_seconds() * 1000)
        return report

    # ---- Step 1: Instantiate the backend ----
    try:
        backend = get_backend(cluster.backend_path, cluster_name=cluster.name)
    except Exception as exc:
        report.errors.append(f"Failed to instantiate backend: {exc}")
        report.duration_ms = int((timezone.now() - start).total_seconds() * 1000)
        return report

    # ---- Step 2: Fetch current backend state ----
    try:
        backend_quotas = backend.get_all_quotas()
    except Exception as exc:
        report.errors.append(f"Failed to fetch backend quotas: {exc}")
        report.duration_ms = int((timezone.now() - start).total_seconds() * 1000)
        return report

    # Build a lookup of backend quotas by path
    backend_by_path: dict[str, object] = {}
    for q in backend_quotas:
        backend_by_path[q.path] = q

    # ---- Step 3: Get active ColdFront quotas that apply to this cluster ----
    active_quotas = StorageQuota.objects.filter(
        allocation__status=AllocationStatusChoices.STATUS_ACTIVE,
    ).select_related("storage", "allocation", "snapshot_policy")

    # Build lookup of quotas that should exist on this cluster
    expected_quotas: list[StorageQuota] = []
    for quota in active_quotas:
        if quota.clusters.exists():
            if quota.clusters.filter(pk=cluster.pk).exists():
                expected_quotas.append(quota)
        else:
            # Empty M2M means apply to ALL clusters backing the resource
            if quota.storage.clusters.filter(pk=cluster.pk).exists():
                expected_quotas.append(quota)

    # ---- Step 4: Reconcile — for each expected quota, ensure it exists on backend ----
    for quota in expected_quotas:
        path = quota.path
        backend_q = backend_by_path.get(path)

        if backend_q is None:
            # Quota doesn't exist on backend — create path + quota
            try:
                backend.create_path(
                    path=path,
                    user=quota.owning_user.username if quota.owning_user else "",
                    group=quota.owning_group.name if quota.owning_group else "",
                    mode=quota.path_mode,
                )
                report.paths_created += 1
            except Exception as exc:
                report.errors.append(f"Failed to create path {path}: {exc}")
                continue

            try:
                backend.create_quota(
                    path=path,
                    share_type=quota.share_type,
                    hard_limit_bytes=quota.hard_limit_bytes,
                    files_limit=quota.hard_limit_files,
                    grace=str(quota.grace_period) if quota.grace_period else None,
                )
                report.quotas_created += 1
            except Exception as exc:
                report.errors.append(f"Failed to create quota for {path}: {exc}")
                continue

            # Apply snapshot policy if set
            if quota.snapshot_policy_id and hasattr(backend, "apply_snapshot_policy"):
                try:
                    backend.apply_snapshot_policy(
                        path=path,
                        policy={
                            "interval": quota.snapshot_policy.interval,
                            "retention_days": quota.snapshot_policy.retention_days,
                            "extra_config": quota.snapshot_policy.extra_config,
                        },
                    )
                except Exception as exc:
                    report.warnings.append(f"Failed to apply snapshot policy for {path}: {exc}")

        else:
            # Quota exists on backend — check if limits need updating
            new_hard = quota.hard_limit_bytes
            new_files = quota.hard_limit_files
            current_hard = backend_q.hard_limit_bytes
            current_files = backend_q.hard_limit_files

            if new_hard != current_hard or new_files != current_files:
                try:
                    backend.update_quota(
                        quota_id=backend_q.id,
                        hard_limit_bytes=new_hard,
                        files_limit=new_files,
                    )
                    report.quotas_updated += 1
                except Exception as exc:
                    report.errors.append(f"Failed to update quota for {path}: {exc}")

            # Update usage tracking from backend
            if backend_q.used is not None:
                StorageQuota.objects.filter(pk=quota.pk).update(
                    used=backend_q.used,
                    used_files=backend_q.used_files,
                    state=backend_q.state or "",
                )

    # ---- Step 5: Remove orphaned quotas on backend ----
    expected_paths = {q.path for q in expected_quotas}
    for backend_q in backend_quotas:
        if backend_q.path not in expected_paths:
            try:
                backend.delete_quota(path=backend_q.path)
                report.quotas_deleted += 1
            except Exception as exc:
                report.errors.append(f"Failed to delete orphaned quota {backend_q.path}: {exc}")

    report.duration_ms = int((timezone.now() - start).total_seconds() * 1000)
    report.success = len(report.errors) == 0
    return report


# ---------------------------------------------------------------------------
# Used bytes recalculation
# ---------------------------------------------------------------------------


def _recalculate_used_bytes() -> None:
    """Update resource and cluster ``used_bytes`` from active quota sums.

    Called at the end of ``run_sync()`` and after each targeted handler
    completes.
    """
    STATUS_ACTIVE = AllocationStatusChoices.STATUS_ACTIVE

    # Per resource: sum of all active quotas on that resource
    for resource in StorageResource.objects.iterator():
        total = (
            StorageQuota.objects.filter(
                storage=resource,
                allocation__status=STATUS_ACTIVE,
            ).aggregate(total=Sum("used"))["total"]
            or 0
        )
        StorageResource.objects.filter(pk=resource.pk).update(used_bytes=total)

    # Per cluster: sum of all active quotas on that cluster.
    # Quotas with empty clusters M2M apply to ALL clusters backing
    # their resource, so they must be included too.
    for cluster in StorageCluster.objects.iterator():
        total = (
            StorageQuota.objects.filter(
                allocation__status=STATUS_ACTIVE,
            )
            .filter(
                # Quota explicitly has this cluster in its M2M
                Q(clusters=cluster)
                # OR quota has empty M2M but its resource uses this cluster
                | Q(
                    clusters__isnull=True,
                    storage__clusters=cluster,
                )
            )
            .aggregate(total=Sum("used"))["total"]
            or 0
        )
        StorageCluster.objects.filter(pk=cluster.pk).update(used_bytes=total)


# ---------------------------------------------------------------------------
# Targeted handler implementations (called by worker or CLI)
# ---------------------------------------------------------------------------


def _run_activate_allocation(
    *,
    allocation_id: int,
    cluster_id: int,
    share_type: str = "posix",
) -> SyncReport:
    """Create path + quota on a cluster for a newly activated allocation.

    Called by the worker process (or directly by CLI).  Delegates to
    ``_sync_cluster()`` which handles the full reconciliation for the
    cluster, but this function only activates a single allocation.
    """
    cluster = StorageCluster.objects.get(pk=cluster_id)
    report = SyncReport(cluster=cluster.name, success=False)

    from coldfront.storage.backends.registry import get_backend

    backend = get_backend(cluster.backend_path, cluster_name=cluster.name)
    if backend is None:
        report.errors.append(f"Cluster {cluster.name} has no backend — cannot activate allocation {allocation_id}")
        return report

    try:
        quota = StorageQuota.objects.get(allocation_id=allocation_id)
    except StorageQuota.DoesNotExist:
        report.errors.append(f"StorageQuota not found for allocation {allocation_id}")
        return report

    path = quota.path

    # Create path
    try:
        backend.create_path(
            path=path,
            user=quota.owning_user.username if quota.owning_user else "",
            group=quota.owning_group.name if quota.owning_group else "",
            mode=quota.path_mode,
        )
        report.paths_created += 1
    except Exception as exc:
        report.errors.append(f"Failed to create path {path}: {exc}")
        return report

    # Create quota
    try:
        backend.create_quota(
            path=path,
            share_type=share_type,
            hard_limit_bytes=quota.hard_limit_bytes,
            files_limit=quota.hard_limit_files,
            grace=str(quota.grace_period) if quota.grace_period else None,
        )
        report.quotas_created += 1
    except Exception as exc:
        report.errors.append(f"Failed to create quota for {path}: {exc}")
        return report

    # Apply snapshot policy if set
    if quota.snapshot_policy_id and hasattr(backend, "apply_snapshot_policy"):
        try:
            backend.apply_snapshot_policy(
                path=path,
                policy={
                    "interval": quota.snapshot_policy.interval,
                    "retention_days": quota.snapshot_policy.retention_days,
                    "extra_config": quota.snapshot_policy.extra_config,
                },
            )
        except Exception as exc:
            report.warnings.append(f"Failed to apply snapshot policy for {path}: {exc}")

    report.success = len(report.errors) == 0
    _recalculate_used_bytes()
    return report


def _run_deactivate_allocation(*, allocation_id: int, cluster_id: int) -> SyncReport:
    """Remove quota on a cluster for an expired/revoked allocation.

    Called by the worker process (or directly by CLI).
    """
    cluster = StorageCluster.objects.get(pk=cluster_id)
    report = SyncReport(cluster=cluster.name, success=False)

    from coldfront.storage.backends.registry import get_backend

    backend = get_backend(cluster.backend_path, cluster_name=cluster.name)
    if backend is None:
        report.errors.append(f"Cluster {cluster.name} has no backend — cannot deactivate allocation {allocation_id}")
        return report

    try:
        quota = StorageQuota.objects.get(allocation_id=allocation_id)
    except StorageQuota.DoesNotExist:
        report.errors.append(f"StorageQuota not found for allocation {allocation_id}")
        return report

    path = quota.path

    # Remove snapshot policy if set
    if quota.snapshot_policy_id and hasattr(backend, "remove_snapshot_policy"):
        try:
            backend.remove_snapshot_policy(path=path)
        except Exception as exc:
            report.warnings.append(f"Failed to remove snapshot policy for {path}: {exc}")

    # Remove quota
    try:
        backend.delete_quota(path=path)
        report.quotas_deleted += 1
    except Exception as exc:
        report.errors.append(f"Failed to delete quota for {path}: {exc}")
        return report

    # Lock path (optional)
    try:
        backend.lock_path(path=path)
        report.paths_deleted += 1
    except Exception as exc:
        report.warnings.append(f"Failed to lock path {path}: {exc}")

    report.success = len(report.errors) == 0
    _recalculate_used_bytes()
    return report
