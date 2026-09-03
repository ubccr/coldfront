# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Slurm sync engine.

Provides the core synchronization logic between ColdFront's local models
and the Slurm REST API (``slurmrestd``).  Three entry points:

* ``run_sync()`` — full reconciliation sync for one or all clusters.
* ``enqueue_activate_allocation()`` — targeted handler for allocation
  activation.
* ``enqueue_deactivate_allocation()`` — targeted handler for allocation
  expire / revoke.
* ``enqueue_remove_project_user()`` — targeted handler for ProjectUser
  deletion.

The ``enqueue_*()`` wrappers are thin — they check the auto-sync gate and
delegate to the task queue.  The actual REST API logic lives in the
corresponding ``_run_*()`` functions so that the CLI command can call them
directly without going through the queue.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone

from coldfront.core.models import Job
from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.models import Allocation, ProjectUser
from coldfront.slurm.choices import (
    SlurmPartitionStateChoices,
    SlurmPreemptModeChoices,
    SlurmPriorityFlagsChoices,
    SlurmPriorityTypeChoices,
    SlurmPriorityUsageResetPeriodChoices,
)
from coldfront.slurm.client import SlurmClient
from coldfront.slurm.client.exceptions import (
    SlurmAlreadyExistsException,
)
from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAccountUsage,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmQOS,
    SlurmUser,
)
from coldfront.slurm.parser import ParsedSlurmConfig, parse_slurm_conf, parse_tres_weights

__all__ = (
    "SyncReport",
    "UsageSyncReport",
    "run_sync",
    "_run_usage_sync",
    "enqueue_activate_allocation",
    "enqueue_deactivate_allocation",
    "enqueue_remove_project_user",
    "import_cluster_from_conf",
    "import_cluster_from_api",
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SyncReport
# ---------------------------------------------------------------------------


@dataclass
class SyncReport:
    """Detailed report returned by sync operations."""

    cluster: str
    success: bool = False
    accounts_created: int = 0
    accounts_deleted: int = 0
    associations_created: int = 0
    associations_updated: int = 0
    associations_deleted: int = 0
    users_created: int = 0
    users_updated: int = 0
    users_deleted: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_ms: int = 0


@dataclass
class UsageSyncReport:
    """Detailed report returned by :func:`_run_usage_sync`."""

    cluster: str
    success: bool = False
    days_synced: int = 0
    accounts_updated: int = 0
    jobs_ingested: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_ms: int = 0


# ---------------------------------------------------------------------------
# SlurmClient factory
# ---------------------------------------------------------------------------


def _build_client(cluster: SlurmCluster | None = None) -> SlurmClient | None:
    """Build a :class:`SlurmClient` from Django settings.

    Looks up the cluster's name in ``settings.SLURMRESTD_CLUSTERS``.
    Falls back to the ``"default"`` entry when the cluster is not listed
    or when ``cluster`` is ``None``.

    Returns ``None`` if slurmrestd is not configured (empty URL).
    """
    clusters_config = getattr(settings, "SLURMRESTD_CLUSTERS", {})

    # Resolve config dict for this cluster (or "default")
    key = cluster.name if cluster is not None else "default"
    config = clusters_config.get(key) or clusters_config.get("default", {})

    url = config.get("url", "")
    if not url:
        return None

    jwt = config.get("jwt_token", "")
    version = config.get("api_version", "") or None
    timeout = config.get("timeout", 30)
    retries = config.get("retries", 3)
    backoff = config.get("retry_backoff", 1.5)

    client = SlurmClient(
        base_url=url,
        jwt_token=jwt,
        version=version,
        timeout=timeout,
        retries=retries,
        retry_backoff=backoff,
    )

    if version is None:
        try:
            client.discover_version()
        except RuntimeError:
            logger.warning("Slurm API version discovery failed — client will not be usable")
            return None

    return client


# ---------------------------------------------------------------------------
# Auto-sync gate
# ---------------------------------------------------------------------------


def _auto_sync_enabled(cluster: SlurmCluster | None = None) -> bool:
    """Return ``True`` if automated Slurm sync is enabled.

    Checks the cluster's config in ``settings.SLURMRESTD_CLUSTERS`` first;
    falls back to the ``"default"`` entry when the cluster is not listed
    or when ``cluster`` is ``None``.
    """
    clusters_config = getattr(settings, "SLURMRESTD_CLUSTERS", {})
    key = cluster.name if cluster is not None else "default"
    config = clusters_config.get(key) or clusters_config.get("default", {})
    return config.get("auto_sync_enabled", False)


# ---------------------------------------------------------------------------
# Targeted handler wrappers (enqueue helpers)
# ---------------------------------------------------------------------------


def enqueue_activate_allocation(allocation_id: int, cluster_id: int | None = None) -> None:
    """Enqueue a targeted task to create associations for an allocation.

    Called by the ViewFlow callback when an allocation is activated.
    Respects the per-cluster ``auto_sync_enabled`` gate — if ``cluster_id``
    is provided, checks that cluster's setting; otherwise checks the
    ``"default"`` cluster config.

    The actual work is done by :func:`_run_activate_allocation` in the
    worker process.
    """
    cluster = SlurmCluster.objects.get(pk=cluster_id) if cluster_id is not None else None
    if not _auto_sync_enabled(cluster):
        logger.debug(
            "Slurm auto sync disabled — skipping activate enqueue for allocation %s",
            allocation_id,
        )
        return

    logger.info("Enqueuing Slurm activate for allocation %s", allocation_id)
    Job.enqueue(
        "coldfront.slurm.sync._run_activate_allocation",
        args=(),
        kwargs={"allocation_id": allocation_id},
        priority=3,
    )


def enqueue_deactivate_allocation(allocation_id: int, cluster_id: int | None = None) -> None:
    """Enqueue a targeted task to remove associations for an allocation.

    Called by ViewFlow callbacks when an allocation is expired or revoked.
    Respects the per-cluster ``auto_sync_enabled`` gate — if ``cluster_id``
    is provided, checks that cluster's setting; otherwise checks the
    ``"default"`` cluster config.
    """
    cluster = SlurmCluster.objects.get(pk=cluster_id) if cluster_id is not None else None
    if not _auto_sync_enabled(cluster):
        logger.debug(
            "Slurm auto sync disabled — skipping deactivate enqueue for allocation %s",
            allocation_id,
        )
        return

    logger.info("Enqueuing Slurm deactivate for allocation %s", allocation_id)
    Job.enqueue(
        "coldfront.slurm.sync._run_deactivate_allocation",
        args=(),
        kwargs={"allocation_id": allocation_id},
        priority=3,
    )


def enqueue_remove_project_user(project_id: int, user_id: int, cluster_ids: list[int] | None = None) -> None:
    """Enqueue a targeted task to remove a user from all allocations.

    Called by the ``post_delete`` signal handler when a ProjectUser is
    deleted.  Respects the per-cluster ``auto_sync_enabled`` gate — if
    ``cluster_ids`` is provided, checks each cluster's setting;
    otherwise checks the ``"default"`` cluster config.
    """
    if cluster_ids:
        for cid in cluster_ids:
            try:
                cluster = SlurmCluster.objects.get(pk=cid)
                if _auto_sync_enabled(cluster):
                    break  # at least one cluster has sync enabled
            except SlurmCluster.DoesNotExist:
                continue
        else:
            # no cluster has sync enabled
            logger.debug(
                "Slurm auto sync disabled — skipping remove-project-user enqueue for project %s user %s",
                project_id,
                user_id,
            )
            return
    elif not _auto_sync_enabled():
        logger.debug(
            "Slurm auto sync disabled — skipping remove-project-user enqueue for project %s user %s",
            project_id,
            user_id,
        )
        return

    logger.info(
        "Enqueuing Slurm remove-project-user for project %s user %s",
        project_id,
        user_id,
    )
    Job.enqueue(
        "coldfront.slurm.sync._run_remove_project_user",
        args=(),
        kwargs={
            "project_id": project_id,
            "user_id": user_id,
        },
        priority=3,
    )


# ---------------------------------------------------------------------------
# Targeted handler implementations (called by worker or CLI)
# ---------------------------------------------------------------------------


def _run_activate_allocation(*, allocation_id: int) -> SyncReport:
    """Create Slurm associations for a newly activated allocation.

    Called by the worker process (or directly by CLI).  Builds a minimal
    config payload containing only the entities needed for this allocation
    and sends it via ``POST /config``.
    """
    report = SyncReport(cluster="", success=False)

    try:
        allocation = Allocation.objects.get(pk=allocation_id)
    except Allocation.DoesNotExist:
        report.errors.append(f"Allocation {allocation_id} not found")
        return report

    resource = allocation.resource_object
    if resource is None:
        report.errors.append(f"Allocation {allocation_id} has no resource")
        return report

    # Determine cluster
    if isinstance(resource, SlurmCluster):
        cluster = resource
    elif isinstance(resource, SlurmPartition):
        cluster = resource.cluster
    else:
        report.errors.append(f"Allocation {allocation_id} targets non-slurm resource")
        return report

    report.cluster = cluster.name

    client = _build_client(cluster)
    if client is None:
        report.errors.append("slurmrestd not configured (SLURMRESTD_URL is empty)")
        return report

    # Load SlurmAssociation
    try:
        association = SlurmAssociation.objects.get(allocation=allocation)
    except SlurmAssociation.DoesNotExist:
        report.errors.append(f"No SlurmAssociation for allocation {allocation_id}")
        return report

    slurm_account = association.slurm_account
    if slurm_account is None:
        report.errors.append(f"SlurmAssociation for allocation {allocation_id} has no slurm_account set")
        return report

    # Ensure the account exists in Slurm
    try:
        client.create_accounts(
            [
                {
                    "name": slurm_account.name,
                    "description": slurm_account.description or "",
                }
            ]
        )
        report.accounts_created += 1
    except SlurmAlreadyExistsException:
        report.warnings.append(f"Account '{slurm_account.name}' already exists")
        report.accounts_created += 1  # idempotent — desired state achieved
    except Exception as exc:
        report.errors.append(f"Failed to create account '{slurm_account.name}': {exc}")

    # SU enforcement — push GrpTresMins on the account-level association
    account_assoc_payload = _build_account_assoc_payload(slurm_account, cluster)
    if account_assoc_payload:
        try:
            client.create_associations([account_assoc_payload])
        except SlurmAlreadyExistsException:
            pass  # idempotent upsert — desired state achieved
        except Exception as exc:
            report.errors.append(f"Failed to set GrpTresMins for account '{slurm_account.name}': {exc}")

    # Create associations and users for each ProjectUser
    project = allocation.project
    for pu in ProjectUser.objects.filter(project=project).select_related("user"):
        user = pu.user
        if user is None:
            continue

        # Ensure SlurmUser exists
        slurm_user = _ensure_slurm_user(user, cluster, slurm_account, association)

        # Build assoc_rec_set entry
        assoc_payload = _build_assoc_payload(association, user, cluster, resource)
        try:
            client.create_associations([assoc_payload])
            report.associations_created += 1
        except SlurmAlreadyExistsException:
            report.associations_updated += 1
        except Exception as exc:
            report.errors.append(f"Failed to create association for {user.username}: {exc}")

        # Ensure user exists in Slurm
        try:
            client.create_users(
                [
                    {
                        "name": user.username,
                        "default": {
                            "account": slurm_user.default_account.name,
                            "wckey": slurm_user.default_wckey or "",
                        },
                    }
                ]
            )
            report.users_created += 1
        except SlurmAlreadyExistsException:
            report.users_updated += 1
        except Exception as exc:
            report.errors.append(f"Failed to create user '{user.username}': {exc}")

    # Trigger slurmctld cache refresh
    _reconfigure(client)

    report.success = len(report.errors) == 0
    return report


def _run_deactivate_allocation(*, allocation_id: int) -> SyncReport:
    """Remove associations and kill jobs for a deactivated allocation.

    Called when an allocation is expired or revoked.
    """
    report = SyncReport(cluster="", success=False)

    try:
        allocation = Allocation.objects.get(pk=allocation_id)
    except Allocation.DoesNotExist:
        report.errors.append(f"Allocation {allocation_id} not found")
        return report

    resource = allocation.resource_object
    if resource is None:
        report.errors.append(f"Allocation {allocation_id} has no resource")
        return report

    if isinstance(resource, SlurmCluster):
        cluster = resource
    elif isinstance(resource, SlurmPartition):
        cluster = resource.cluster
    else:
        report.errors.append(f"Allocation {allocation_id} targets non-slurm resource")
        return report

    report.cluster = cluster.name

    client = _build_client(cluster)
    if client is None:
        report.errors.append("slurmrestd not configured (SLURMRESTD_URL is empty)")
        return report

    try:
        association = SlurmAssociation.objects.get(allocation=allocation)
    except SlurmAssociation.DoesNotExist:
        report.success = True
        return report

    slurm_account = association.slurm_account
    if slurm_account is None:
        report.success = True
        return report

    partition_name = resource.name if isinstance(resource, SlurmPartition) else ""

    # Kill running jobs for each ProjectUser
    project = allocation.project
    for pu in ProjectUser.objects.filter(project=project).select_related("user"):
        user = pu.user
        if user is None:
            continue
        _kill_user_jobs(client, user, slurm_account, partition_name)

        # Delete the association
        delete_params: dict[str, Any] = {
            "account": slurm_account.name,
            "user": user.username,
            "cluster": cluster.name,
        }
        if partition_name:
            delete_params["partition"] = partition_name
        try:
            client.delete_associations(delete_params)
            report.associations_deleted += 1
        except Exception as exc:
            report.errors.append(f"Failed to delete association for {user.username}: {exc}")

        # Reconcile SlurmUser
        _reconcile_slurm_user(user, cluster, slurm_account)

    # Trigger slurmctld cache refresh
    _reconfigure(client)

    report.success = len(report.errors) == 0
    return report


def _run_remove_project_user(*, project_id: int, user_id: int) -> SyncReport:
    """Remove a user from all allocations on a project.

    Called when a ProjectUser record is deleted.
    """
    report = SyncReport(cluster="", success=False)

    try:
        user_model = settings.AUTH_USER_MODEL
        from django.apps import apps

        User = apps.get_model(user_model)
        user = User.objects.get(pk=user_id)
    except Exception as exc:
        report.errors.append(f"User {user_id} not found: {exc}")
        return report

    # Find all active allocations for this project
    project_allocations = Allocation.objects.filter(
        project_id=project_id,
        status=AllocationStatusChoices.STATUS_ACTIVE,
    )

    # Collect unique clusters involved
    clusters_seen: set[int] = set()
    for allocation in project_allocations:
        resource = allocation.resource_object
        if resource is None:
            continue
        if isinstance(resource, SlurmCluster):
            clusters_seen.add(resource.pk)
        elif isinstance(resource, SlurmPartition):
            clusters_seen.add(resource.cluster_id)

    # Use the first cluster for client building (all clusters on a project
    # should share the same slurmrestd, but if they don't, the client will
    # be built from the first cluster's config)
    first_cluster = SlurmCluster.objects.filter(pk__in=clusters_seen).first() if clusters_seen else None
    client = _build_client(first_cluster)
    if client is None:
        report.errors.append("slurmrestd not configured (SLURMRESTD_URL is empty)")
        return report

    # Reload the query (we consumed it above)
    project_allocations = Allocation.objects.filter(
        project_id=project_id,
        status=AllocationStatusChoices.STATUS_ACTIVE,
    )

    for allocation in project_allocations:
        resource = allocation.resource_object
        if resource is None:
            continue

        if isinstance(resource, SlurmCluster):
            cluster = resource
        elif isinstance(resource, SlurmPartition):
            cluster = resource.cluster
        else:
            continue

        if report.cluster == "":
            report.cluster = cluster.name

        try:
            association = SlurmAssociation.objects.get(allocation=allocation)
        except SlurmAssociation.DoesNotExist:
            continue

        slurm_account = association.slurm_account
        if slurm_account is None:
            continue

        partition_name = resource.name if isinstance(resource, SlurmPartition) else ""

        # Kill jobs
        _kill_user_jobs(client, user, slurm_account, partition_name)

        # Delete association
        delete_params: dict[str, Any] = {
            "account": slurm_account.name,
            "user": user.username,
            "cluster": cluster.name,
        }
        if partition_name:
            delete_params["partition"] = partition_name
        try:
            client.delete_associations(delete_params)
            report.associations_deleted += 1
        except Exception as exc:
            report.errors.append(f"Failed to delete association for {user.username}: {exc}")

        # Reconcile SlurmUser
        _reconcile_slurm_user(user, cluster, slurm_account)

    # Trigger slurmctld cache refresh
    _reconfigure(client)

    report.success = len(report.errors) == 0
    return report


# ---------------------------------------------------------------------------
# Full reconciliation sync
# ---------------------------------------------------------------------------


def run_sync(cluster_id: int | None = None) -> list[SyncReport]:
    """Perform a full reconciliation sync for one or all clusters.

    Uses ``POST /slurmdb/{version}/config`` to upsert the full desired
    accounting state for each cluster, then queries Slurm for orphaned
    associations and deletes them.

    Args:
        cluster_id: Optional cluster PK.  If ``None``, syncs all clusters.

    Returns:
        List of ``SyncReport`` — one per cluster processed.
    """
    reports: list[SyncReport] = []

    clusters = SlurmCluster.objects.all()
    if cluster_id is not None:
        clusters = clusters.filter(pk=cluster_id)

    for cluster in clusters:
        client = _build_client(cluster)
        if client is None:
            report = SyncReport(cluster=cluster.name, success=False)
            report.errors.append("slurmrestd not configured (SLURMRESTD_URL is empty)")
            reports.append(report)
            continue
        report = _sync_cluster(client, cluster)
        reports.append(report)

    return reports


def _sync_cluster(client: SlurmClient, cluster: SlurmCluster) -> SyncReport:
    """Sync a single cluster with slurmrestd."""
    start = timezone.now()
    report = SyncReport(cluster=cluster.name, success=False)

    # ---- Step 1: Build the full config payload ----
    config = _build_config_payload(cluster)
    if config is None:
        report.warnings.append(f"Cluster '{cluster.name}' has no active associations — nothing to upsert")
        report.success = True
        report.duration_ms = 0
        return report

    # ---- Step 2: Upsert via POST /config ----
    try:
        resp = client.upsert_config(config)
        report.accounts_created = len(config.get("accounts", []))
        report.associations_created = len(config.get("associations", []))
        report.users_created = len(config.get("users", []))
        report.warnings.extend(resp.get("warnings", []))
    except Exception as exc:
        report.errors.append(f"Config upsert failed: {exc}")
        report.duration_ms = int((timezone.now() - start).total_seconds() * 1000)
        return report

    # ---- Step 3: Find and delete orphaned associations ----
    try:
        existing = client.get_associations(params={"cluster": cluster.name, "with_deleted": "false"})
    except Exception as exc:
        report.errors.append(f"Failed to query existing associations: {exc}")
        report.duration_ms = int((timezone.now() - start).total_seconds() * 1000)
        return report

    # Build set of expected (account, user, partition) tuples from active
    # associations in ColdFront
    expected = _build_expected_tuples(cluster)

    # Delete orphaned associations
    for assoc in existing.get("associations", []):
        acct = assoc.get("account", "")
        user = assoc.get("user", "")
        partition = assoc.get("partition", "")
        key = (acct, user, partition)
        if key in expected:
            continue

        # This association exists in Slurm but has no matching active
        # allocation in ColdFront — delete it
        try:
            delete_params: dict[str, Any] = {
                "account": acct,
                "user": user,
                "cluster": cluster.name,
            }
            if partition:
                delete_params["partition"] = partition
            client.delete_associations(delete_params)
            report.associations_deleted += 1
        except Exception as exc:
            report.errors.append(
                f"Failed to delete orphaned association (account={acct}, user={user}, partition={partition}): {exc}"
            )

    # ---- Step 4: Trigger slurmctld cache refresh ----
    _reconfigure(client)

    report.duration_ms = int((timezone.now() - start).total_seconds() * 1000)
    report.success = len(report.errors) == 0
    return report


# ---------------------------------------------------------------------------
# SU usage sync
# ---------------------------------------------------------------------------

# Hard cap on how many past days a single usage sync pass may catch up.
# Bounded by slurmdbd live-DB retention (Purge/Archive); a large catch-up
# costs up to one REST query per day per cluster.
USAGE_SYNC_MAX_CATCHUP_DAYS = 60


# TRES ids used in ``tres.allocated`` (Slurm internal TRES_ARRAY indices).
_TRES_NODE = 4
_TRES_BILLING = 5


def _utc_day_bounds(day: datetime.date) -> tuple[int, int]:
    """Return (start, end) UNIX timestamps for the UTC midnight window of a day."""
    start = timezone.make_aware(datetime.combine(day, time.min)).timestamp()
    end = start + 86400
    return int(start), int(end)


def _tres_count(tres_allocated: list[dict[str, Any]] | None, tres_id: int) -> int:
    """Return the integer count for a TRES entry in ``tres.allocated``."""
    if not tres_allocated:
        return 0
    for entry in tres_allocated:
        if entry.get("id") == tres_id:
            try:
                return int(float(entry.get("count", 0)))
            except (TypeError, ValueError):
                return 0
    return 0


@dataclass
class _DayAggregates:
    """Accumulated per-account aggregates for one day."""

    billing_units_consumed: float = 0.0
    walltime_sec_consumed: int = 0
    node_hours_consumed: float = 0.0
    job_count_consumed: int = 0
    billing_units_completed: float = 0.0
    walltime_sec_completed: int = 0
    job_count_completed: int = 0
    node_hours_by_partition: dict[str, float] = field(default_factory=dict)
    billing_by_qos: dict[str, float] = field(default_factory=dict)


def _roll_up_job_usage(
    jobs: list[dict[str, Any]],
    day_start: int,
    day_end: int,
) -> dict[str, _DayAggregates]:
    """Aggregate job records into per-account daily usage.

    Uses a single overlap query result for both attribution models:

    * ``*_consumed`` — ``billing_count x overlap_sec / 3600`` per day
      (pro-rated; matches sreport's accounting report).
    * ``*_completed`` — ``billing_count x full_elapsed / 3600`` charged on
      the day the job completed (matches sreport's job report; informational).

    Jobs with no start time (pending) and zero-overlap jobs are skipped.

    Args:
        jobs: Job dicts from :meth:`SlurmClient.get_job_usage`.
        day_start: UNIX start of the day window (inclusive).
        day_end: UNIX end of the day window (exclusive).

    Returns:
        Dict mapping account name to :class:`_DayAggregates`.
    """
    agg: dict[str, _DayAggregates] = {}

    for job in jobs:
        start_ts = int(job.get("time", {}).get("start", 0) or 0)
        end_ts = int(job.get("time", {}).get("end", 0) or 0)
        elapsed = int(job.get("time", {}).get("elapsed", 0) or 0)
        if start_ts == 0:
            # Pending / never-started — no usage to attribute.
            continue

        # Still-running jobs are clipped at the window end.
        effective_end = end_ts if end_ts != 0 else day_end
        overlap = max(0, min(effective_end, day_end) - max(start_ts, day_start))
        if overlap <= 0:
            continue

        account = job.get("account", "")
        partition = job.get("partition", "") or ""
        qos = job.get("qos", "") or ""

        billing_count = _tres_count(job.get("tres", {}).get("allocated"), _TRES_BILLING)
        node_count = _tres_count(job.get("tres", {}).get("allocated"), _TRES_NODE)

        a = agg.setdefault(account, _DayAggregates())

        # Consumed (pro-rated) attribution
        a.billing_units_consumed += billing_count * overlap / 3600.0
        a.walltime_sec_consumed += overlap
        a.node_hours_consumed += node_count * overlap / 3600.0
        a.job_count_consumed += 1
        if partition:
            a.node_hours_by_partition[partition] = (
                a.node_hours_by_partition.get(partition, 0.0) + node_count * overlap / 3600.0
            )
        if qos:
            a.billing_by_qos[qos] = a.billing_by_qos.get(qos, 0.0) + billing_count * overlap / 3600.0

        # Completed (completion-day) attribution — only when the job
        # finished inside this window.
        if end_ts != 0 and day_start <= end_ts < day_end:
            a.billing_units_completed += billing_count * elapsed / 3600.0
            a.walltime_sec_completed += elapsed
            a.job_count_completed += 1

    return agg


def _resolve_catchup_range(cluster: SlurmCluster) -> tuple[datetime.date, datetime.date] | None:
    """Return the (start, end) day range the daily sync should ingest.

    Resumes from ``cluster.last_usage_sync + 1`` up to yesterday, capped at
    ``USAGE_SYNC_MAX_CATCHUP_DAYS`` days (most recent days win). Returns
    ``None`` when there are no days to sync.
    """
    today = timezone.localdate()
    yesterday = today - timedelta(days=1)

    if cluster.last_usage_sync is None:
        start = yesterday - timedelta(days=USAGE_SYNC_MAX_CATCHUP_DAYS - 1)
    else:
        start = cluster.last_usage_sync + timedelta(days=1)
        floor = yesterday - timedelta(days=USAGE_SYNC_MAX_CATCHUP_DAYS - 1)
        if start < floor:
            start = floor

    if start > yesterday:
        return None
    return start, yesterday


def _run_usage_sync(
    cluster: SlurmCluster,
    start_day: datetime.date,
    end_day: datetime.date,
) -> UsageSyncReport:
    """Ingest per-day job usage for a cluster into :class:`SlurmAccountUsage`.

    Range-based and idempotent (``update_or_create`` per account/day); the
    caller decides the day range. On success, advances
    ``cluster.last_usage_sync`` to ``end_day``.

    Args:
        cluster: Cluster to sync.
        start_day: First day to ingest (inclusive).
        end_day: Last day to ingest (inclusive).

    Returns:
        :class:`UsageSyncReport`.
    """
    start = timezone.now()
    report = UsageSyncReport(cluster=cluster.name, success=False)
    client = _build_client(cluster)
    if client is None:
        report.errors.append("slurmrestd not configured (SLURMRESTD_URL is empty)")
        return report

    # Cache known accounts for name -> PK lookups.
    accounts = {}
    for acct in SlurmAccount.objects.filter(cluster=cluster).select_related("cluster"):
        accounts.setdefault(acct.name, acct)

    day = start_day
    while day <= end_day:
        day_start, day_end = _utc_day_bounds(day)
        try:
            jobs = client.get_job_usage(day_start, day_end, cluster.name)
        except Exception as exc:
            report.errors.append(f"Failed to query jobs for {day}: {exc}")
            report.duration_ms = int((timezone.now() - start).total_seconds() * 1000)
            return report
        report.jobs_ingested += len(jobs)
        report.days_synced += 1

        for account_name, a in _roll_up_job_usage(jobs, day_start, day_end).items():
            acct = accounts.get(account_name)
            if acct is None:
                # Account not managed by ColdFront (e.g. root) — skip.
                continue
            SlurmAccountUsage.objects.update_or_create(
                cluster=cluster,
                account=acct,
                period_start=day,
                defaults={
                    "period_end": day,
                    "billing_units_consumed": a.billing_units_consumed,
                    "walltime_sec_consumed": a.walltime_sec_consumed,
                    "node_hours_consumed": a.node_hours_consumed,
                    "job_count_consumed": a.job_count_consumed,
                    "billing_units_completed": a.billing_units_completed,
                    "walltime_sec_completed": a.walltime_sec_completed,
                    "job_count_completed": a.job_count_completed,
                    "node_hours_by_partition": a.node_hours_by_partition,
                    "billing_by_qos": a.billing_by_qos,
                },
            )
            report.accounts_updated += 1

        day += timedelta(days=1)

    cluster.last_usage_sync = end_day
    cluster.save(update_fields=["last_usage_sync"])

    report.duration_ms = int((timezone.now() - start).total_seconds() * 1000)
    report.success = True
    return report


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_config_payload(cluster: SlurmCluster) -> dict[str, Any] | None:
    """Build the full ``openapi_slurmdbd_config_resp`` payload for a cluster.

    Returns ``None`` if the cluster has no active associations.
    """
    from coldfront.slurm.dump import _get_active_associations

    active = _get_active_associations(cluster)
    if not active:
        return None

    # Collect unique accounts
    account_ids = set()
    for a in active:
        if a.slurm_account_id:
            account_ids.add(a.slurm_account_id)

    accounts = SlurmAccount.objects.filter(pk__in=account_ids)

    # Collect unique users across all project members
    user_set: set[int] = set()
    for a in active:
        allocation = a.allocation
        if allocation and allocation.project:
            for pu in allocation.project.users.all():
                if pu.user:
                    user_set.add(pu.user.pk)

    users = SlurmUser.objects.filter(
        cluster=cluster,
        user_id__in=user_set,
    ).select_related("user", "default_account")

    # Build association payloads
    assoc_payloads = []
    for a in active:
        allocation = a.allocation
        if not allocation:
            continue
        resource = allocation.resource_object
        if resource is None:
            continue

        for pu in allocation.project.users.all():
            if not pu.user:
                continue
            assoc_payloads.append(_build_assoc_payload(a, pu.user, cluster, resource))

    # Build account payloads
    account_payloads = [
        {
            "name": acct.name,
            "description": acct.description or "",
        }
        for acct in accounts
    ]

    # SU enforcement — account-level associations carrying GrpTresMins
    for acct in accounts:
        account_assoc_payload = _build_account_assoc_payload(acct, cluster)
        if account_assoc_payload:
            assoc_payloads.append(account_assoc_payload)

    # Build user payloads
    user_payloads = []
    for su in users:
        user_payloads.append(
            {
                "name": su.user.username,
                "default": {
                    "account": su.default_account.name,
                    "wckey": su.default_wckey or "",
                },
            }
        )

    # Build cluster payload
    cluster_payload = {
        "name": cluster.name,
    }
    if cluster.default_qos:
        cluster_payload["defaultqos"] = cluster.default_qos.name

    return {
        "clusters": [cluster_payload],
        "accounts": account_payloads,
        "users": user_payloads,
        "associations": assoc_payloads,
    }


def _build_effective_qos(
    account: SlurmAccount | None,
    association: SlurmAssociation,
) -> list[str] | None:
    """
    Compute the effective QOS list for an association by merging
    account-level and association-level qos_add/qos_remove.

    The effective list is:
        (account_qos_add ∪ assoc_qos_add) ∖ (account_qos_remove ∪ assoc_qos_remove)

    Returns ``None`` if both sources have no QOS add/remove entries.
    """
    qos_add_names: set[str] = set()
    qos_remove_names: set[str] = set()

    # Account-level QOS
    if account:
        qos_add_names.update(q.name for q in account.qos_add.all())
        qos_remove_names.update(q.name for q in account.qos_remove.all())

    # Association-level QOS
    qos_add_names.update(q.name for q in association.qos_add.all())
    qos_remove_names.update(q.name for q in association.qos_remove.all())

    # Compute effective list
    effective = list(qos_add_names - qos_remove_names)
    return effective if effective else None


def _build_assoc_payload(
    association: SlurmAssociation,
    user: Any,
    cluster: SlurmCluster,
    resource: SlurmCluster | SlurmPartition,
) -> dict[str, Any]:
    """Build an ``assoc_rec_set`` payload entry from ColdFront models."""
    slurm_account = association.slurm_account
    partition_name = resource.name if isinstance(resource, SlurmPartition) else ""

    payload: dict[str, Any] = {
        "account": slurm_account.name if slurm_account else "",
        "user": user.username,
        "cluster": cluster.name,
        "partition": partition_name,
        "fairshare": association.fairshare,
    }

    if association.default_qos:
        payload["defaultqos"] = association.default_qos.name
    if association.parent:
        payload["parent"] = association.parent.name
    if association.max_jobs is not None:
        payload["maxjobs"] = association.max_jobs
    if association.max_submit_jobs is not None:
        payload["maxsubmitjobs"] = association.max_submit_jobs
    if association.max_tres_per_job is not None:
        payload["maxtresperjob"] = association.max_tres_per_job
    if association.max_tres_mins_per_job is not None:
        payload["maxtresminsperjob"] = association.max_tres_mins_per_job
    if association.max_wall_duration_per_job is not None:
        payload["maxwalldurationperjob"] = int(association.max_wall_duration_per_job.total_seconds())

    # QOS add/remove — merge account-level and association-level
    qoslevel = _build_effective_qos(slurm_account, association)
    if qoslevel:
        payload["qoslevel"] = qoslevel

    return payload


def _build_account_assoc_payload(
    account: SlurmAccount,
    cluster: SlurmCluster,
) -> dict[str, Any] | None:
    """Build the account-level association payload carrying GrpTresMins.

    GrpTresMins is an association-level field; an account's grant is stored
    on the account-level association (``user=""``). Only emitted when the
    cluster enforces SU limits and the account has a service_units grant.

    Returns None when enforcement is off or the grant is unset.
    """
    if not cluster.enforce_su_limits or not account.service_units:
        return None
    return {
        "account": account.name,
        "user": "",
        "cluster": cluster.name,
        "partition": "",
        "grptresmins": {"billing": account.service_units * 60},
    }


def _sync_association_qos(
    association: SlurmAssociation,
    cluster: SlurmCluster,
) -> None:
    """
    Targeted sync of QOS changes for a single association.

    Called when ``qos_add`` or ``qos_remove`` changes on either the
    association itself or its parent ``SlurmAccount``.  Builds an
    association payload with the merged effective QOS list and sends
    it via ``POST /associations/`` (upsert).

    Only syncs if the association has an active allocation and a
    ``slurm_account`` set.
    """
    allocation = association.allocation
    if not allocation:
        return
    if allocation.status != AllocationStatusChoices.STATUS_ACTIVE:
        return
    if not association.slurm_account:
        return

    resource = allocation.resource_object
    if resource is None:
        return
    if not isinstance(resource, (SlurmCluster, SlurmPartition)):
        return

    client = _build_client(cluster)
    if client is None:
        logger.warning(
            "slurmrestd not configured — cannot sync QOS for association %s",
            association.pk,
        )
        return

    # Build and send association payload for each project user
    project = allocation.project
    for pu in ProjectUser.objects.filter(project=project).select_related("user"):
        user = pu.user
        if user is None:
            continue

        assoc_payload = _build_assoc_payload(association, user, cluster, resource)
        try:
            client.create_associations([assoc_payload])
        except SlurmAlreadyExistsException:
            pass  # idempotent — desired state achieved
        except Exception as exc:
            logger.warning(
                "Failed to sync QOS for association %s (user=%s): %s",
                association.pk,
                user.username,
                exc,
            )


def _build_expected_tuples(cluster: SlurmCluster) -> set[tuple[str, str, str]]:
    """Build set of ``(account, user, partition)`` tuples expected in Slurm.

    Only includes active allocations with a non-null slurm_account.
    """
    from coldfront.slurm.dump import _get_active_associations

    expected: set[tuple[str, str, str]] = set()
    for a in _get_active_associations(cluster):
        acct = a.slurm_account
        if acct is None:
            continue
        allocation = a.allocation
        if not allocation:
            continue
        resource = allocation.resource_object
        if resource is None:
            continue
        partition = resource.name if isinstance(resource, SlurmPartition) else ""
        for pu in allocation.project.users.all():
            if pu.user:
                expected.add((acct.name, pu.user.username, partition))
    return expected


def _ensure_slurm_user(
    user: Any,
    cluster: SlurmCluster,
    slurm_account: SlurmAccount,
    association: SlurmAssociation,
) -> SlurmUser:
    """Get or create a SlurmUser record for a user+cluster.

    Uses ``get_or_create`` — existing records are never modified.
    """
    su, _created = SlurmUser.objects.get_or_create(
        user=user,
        cluster=cluster,
        defaults={"default_account": slurm_account},
    )
    return su


def _reconcile_slurm_user(
    user: Any,
    cluster: SlurmCluster,
    removed_account: SlurmAccount,
) -> None:
    """Reconcile a SlurmUser after an association deletion.

    If the removed account was the user's default, find another active
    allocation on this cluster and update the default.  If no active
    allocations remain, delete the SlurmUser entirely.
    """
    try:
        su = SlurmUser.objects.get(user=user, cluster=cluster)
    except SlurmUser.DoesNotExist:
        return

    if su.default_account != removed_account:
        return  # not affected

    # Find another active allocation on this cluster
    from coldfront.slurm.dump import _get_active_associations

    active = _get_active_associations(cluster)
    for a in active:
        allocation = a.allocation
        if not allocation:
            continue
        if allocation.project and allocation.project.users.filter(user=user).exists():
            if a.slurm_account and a.slurm_account != removed_account:
                su.default_account = a.slurm_account
                su.save()
                return

    # No other active allocation found — delete the SlurmUser
    su.delete()


def _kill_user_jobs(
    client: SlurmClient,
    user: Any,
    account: SlurmAccount,
    partition_name: str,
) -> None:
    """Kill all running jobs for a user on a given account+partition."""
    kill_msg: dict[str, Any] = {
        "user_name": user.username,
        "account": account.name,
        "signal": "SIGTERM",
    }
    if partition_name:
        kill_msg["partition"] = partition_name
    try:
        client.kill_jobs(kill_msg)
    except Exception as exc:
        logger.warning(
            "Failed to kill jobs for user %s account %s partition '%s': %s",
            user.username,
            account.name,
            partition_name,
            exc,
        )


def _reconfigure(client: SlurmClient) -> None:
    """Trigger slurmctld to reload its cached association data."""
    try:
        client._request("GET", client._slurm_path("reconfigure/"))
    except Exception as exc:
        logger.warning("Slurmctld reconfigure failed: %s", exc)


# ---------------------------------------------------------------------------
# Cluster import (slurm.conf / REST API)
# ---------------------------------------------------------------------------


@dataclass
class ImportReport:
    """Report from a cluster import operation."""

    cluster: str
    success: bool = False
    cluster_created: bool = False
    cluster_updated: bool = False
    cluster_found: bool = False
    partitions_created: int = 0
    partitions_updated: int = 0
    partitions_found: int = 0
    qos_created: int = 0
    qos_found: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _cluster_billing_kwargs(parsed: ParsedSlurmConfig) -> dict[str, Any]:
    """Build SlurmCluster kwargs for the SU billing TRES config.

    Only includes keys present in the parsed slurm.conf. Never sets
    enforce_su_limits (a ColdFront-only decision, not in slurm.conf).
    """
    kwargs: dict[str, Any] = {}
    if parsed.default_tres_billing_weights:
        kwargs["default_tres_billing_weights"] = parse_tres_weights(parsed.default_tres_billing_weights)
    if parsed.priority_flags:
        flags = [f.strip() for f in parsed.priority_flags.split(",") if f.strip()]
        kwargs["priority_flags"] = [f for f in flags if f in SlurmPriorityFlagsChoices.values()]
    if parsed.priority_type:
        if parsed.priority_type in SlurmPriorityTypeChoices.values():
            kwargs["priority_type"] = parsed.priority_type
    if parsed.priority_decay_half_life:
        kwargs["priority_decay_half_life"] = parsed.priority_decay_half_life
    if parsed.priority_usage_reset_period:
        if parsed.priority_usage_reset_period in SlurmPriorityUsageResetPeriodChoices.values():
            kwargs["priority_usage_reset_period"] = parsed.priority_usage_reset_period
    return kwargs


def import_cluster_from_conf(
    conf_path: str,
    noop: bool = False,
    update: bool = False,
) -> ImportReport:
    """Import a cluster from a slurm.conf file.

    Parses the config file, then creates or updates SlurmCluster,
    SlurmPartition, and SlurmQOS records in ColdFront.

    Args:
        conf_path: Path to the slurm.conf file.
        noop: If True, print what would happen without writing to DB.
        update: If True, update existing records; otherwise skip.

    Returns:
        An ImportReport with counts and errors.
    """
    report = ImportReport(cluster="", success=False)

    parsed = parse_slurm_conf(conf_path)
    if not parsed.cluster_name:
        report.errors.append("No ClusterName found in slurm.conf")
        return report

    report.cluster = parsed.cluster_name

    # --- QOS ---
    for qos_name in sorted(parsed.qos_names):
        if noop:
            report.qos_found += 1
            continue
        try:
            SlurmQOS.objects.get(name=qos_name)
            report.qos_found += 1
        except SlurmQOS.DoesNotExist:
            SlurmQOS.objects.create(name=qos_name)
            report.qos_created += 1

    # --- Cluster ---
    cluster_billing = _cluster_billing_kwargs(parsed)
    if noop:
        report.cluster_created = True  # Would create
    else:
        try:
            cluster = SlurmCluster.objects.get(name=parsed.cluster_name)
            if update:
                for k, v in cluster_billing.items():
                    setattr(cluster, k, v)
                cluster.save()
                report.cluster_updated = True
            else:
                report.cluster_found = True
        except SlurmCluster.DoesNotExist:
            cluster = SlurmCluster.objects.create(
                name=parsed.cluster_name,
                **cluster_billing,
            )
            report.cluster_created = True

    # --- Partitions ---
    if not noop and not parsed.partitions:
        report.warnings.append("No partitions found in slurm.conf")
        report.success = True
        return report

    for pp in parsed.partitions:
        # Skip DEFAULT template partition (it's not a real partition)
        if pp.name.upper() == "DEFAULT":
            continue

        if noop:
            report.partitions_created += 1
            continue

        # Build partition kwargs
        kwargs: dict[str, Any] = {
            "cluster": cluster,
            "name": pp.name,
        }
        if pp.nodes:
            kwargs["nodes"] = pp.nodes
        if pp.priority is not None:
            kwargs["priority"] = pp.priority
        kwargs["is_default"] = pp.is_default
        if pp.default_time:
            kwargs["default_time"] = _parse_duration(pp.default_time)
        if pp.state:
            # Validate state against SlurmPartitionStateChoices
            state_upper = pp.state.upper()
            if state_upper in SlurmPartitionStateChoices.values():
                kwargs["state"] = state_upper
            else:
                kwargs["state"] = pp.state
        if pp.preempt_mode:
            # Validate preempt_mode against SlurmPreemptModeChoices
            preempt_upper = pp.preempt_mode.upper()
            if preempt_upper in SlurmPreemptModeChoices.values():
                kwargs["preempt_mode"] = preempt_upper
            else:
                kwargs["preempt_mode"] = pp.preempt_mode
        if pp.def_mem_per_cpu is not None:
            kwargs["def_mem_per_cpu"] = pp.def_mem_per_cpu
        if pp.tres_billing_weights:
            kwargs["tres_billing_weights"] = parse_tres_weights(pp.tres_billing_weights)

        try:
            partition = SlurmPartition.objects.get(cluster=cluster, name=pp.name)
            if update:
                for k, v in kwargs.items():
                    setattr(partition, k, v)
                partition.save()
                report.partitions_updated += 1
            else:
                report.partitions_found += 1
        except SlurmPartition.DoesNotExist:
            partition = SlurmPartition(**kwargs)
            partition.save()
            report.partitions_created += 1

        # Link QOS references
        if not noop:
            # AllowQOS (whitelist) -> partition.allow_qos M2M
            if pp.allow_qos and pp.allow_qos.upper() != "ALL":
                allow_qos_names = [n.strip() for n in pp.allow_qos.split(",") if n.strip()]
                allow_qos_objs = SlurmQOS.objects.filter(name__in=allow_qos_names)
                partition.allow_qos.set(allow_qos_objs)

            # QOS (assigned partition QOS) -> partition.qos FK
            if pp.qos and pp.qos.upper() != "ALL":
                try:
                    partition.qos = SlurmQOS.objects.get(name=pp.qos.strip())
                    partition.save()
                except SlurmQOS.DoesNotExist:
                    pass

    report.success = len(report.errors) == 0
    return report


def import_cluster_from_api(
    cluster_name: str,
    client: SlurmClient | None = None,
    noop: bool = False,
    update: bool = False,
) -> ImportReport:
    """Import a cluster from the Slurm REST API.

    Fetches partition info from slurmctld and QOS info from slurmdbd,
    then creates or updates models in ColdFront.

    Args:
        cluster_name: Name of the cluster to import.
        client: A SlurmClient instance. If None, builds one from settings.
        noop: If True, print what would happen without writing to DB.
        update: If True, update existing records; otherwise skip.

    Returns:
        An ImportReport with counts and errors.
    """
    report = ImportReport(cluster=cluster_name, success=False)

    # Build client if needed
    if client is None:
        client = _build_client(None)
        if client is None:
            report.errors.append("slurmrestd not configured")
            return report

    # Fetch partitions from slurmctld
    try:
        part_data = client.get_partitions()
    except Exception as exc:
        report.errors.append(f"Failed to fetch partitions: {exc}")
        return report

    partitions = part_data.get("partitions", [])
    if not partitions:
        report.warnings.append("No partitions returned by slurmctld")
        report.success = True
        return report

    # Fetch QOS from slurmdbd
    try:
        qos_data = client.get_qos()
    except Exception as exc:
        report.warnings.append(f"Failed to fetch QOS (non-fatal): {exc}")
        qos_data = {}

    api_qos_list = qos_data.get("qos", [])
    api_qos_names: set[str] = set()
    for q in api_qos_list:
        if isinstance(q, dict):
            qname = q.get("name", "")
            if qname:
                api_qos_names.add(qname)

    # --- QOS ---
    if noop:
        report.qos_found = len(api_qos_names)
    else:
        for qos_name in sorted(api_qos_names):
            try:
                SlurmQOS.objects.get(name=qos_name)
                report.qos_found += 1
            except SlurmQOS.DoesNotExist:
                SlurmQOS.objects.create(
                    name=qos_name,
                )
                report.qos_created += 1

    # --- Cluster ---
    if noop:
        report.cluster_created = True
    else:
        try:
            cluster = SlurmCluster.objects.get(name=cluster_name)
            if update:
                cluster.save()
                report.cluster_updated = True
            else:
                report.cluster_found = True
        except SlurmCluster.DoesNotExist:
            cluster = SlurmCluster.objects.create(
                name=cluster_name,
            )
            report.cluster_created = True

    # --- Partitions ---
    for part in partitions:
        if not isinstance(part, dict):
            continue
        part_name = part.get("name", "")
        if not part_name:
            continue

        if noop:
            report.partitions_created += 1
            continue

        # Build kwargs from API response fields
        kwargs: dict[str, Any] = {
            "cluster": cluster,
            "name": part_name,
        }

        nodes_str = part.get("nodes", "")
        if isinstance(nodes_str, dict):
            # nodes may be a dict with 'nodes' key containing the list
            nodes_list = nodes_str.get("nodes", nodes_str.get("name", ""))
            if isinstance(nodes_list, list):
                kwargs["nodes"] = ",".join(nodes_list)
            else:
                kwargs["nodes"] = str(nodes_list)
        elif nodes_str:
            kwargs["nodes"] = nodes_str

        priority = part.get("priority")
        if priority is not None:
            try:
                kwargs["priority"] = int(priority)
            except (ValueError, TypeError):
                pass

        # State
        state = part.get("state", "")
        if isinstance(state, dict):
            state = state.get("state", "UP")
        state_upper = state.upper() if state else "UP"
        # Validate against SlurmPartitionStateChoices
        if state_upper in SlurmPartitionStateChoices.values():
            kwargs["state"] = state_upper
        else:
            kwargs["state"] = state_upper  # still accept it but warn

        # Default flag
        kwargs["is_default"] = part.get("default", "NO") == "YES"

        # Preempt mode
        preempt = part.get("preempt_mode", "")
        if isinstance(preempt, dict):
            preempt = preempt.get("preempt_mode", "")
        preempt_upper = preempt.upper()
        # Validate against SlurmPreemptModeChoices
        if preempt_upper and preempt_upper in SlurmPreemptModeChoices.values():
            kwargs["preempt_mode"] = preempt_upper
        elif preempt:
            kwargs["preempt_mode"] = preempt
        else:
            kwargs["preempt_mode"] = ""

        # Max time -> max_wall_duration_per_job
        max_time = part.get("max_time", "")
        if isinstance(max_time, dict):
            max_time = max_time.get("number", 0)
        if isinstance(max_time, (int, float)) and max_time > 0:
            kwargs["max_wall_duration_per_job"] = timedelta(minutes=int(max_time))

        # Default time
        default_time = part.get("default_time", "")
        if isinstance(default_time, dict):
            default_time = default_time.get("number", 0)
        if isinstance(default_time, (int, float)) and default_time > 0:
            kwargs["default_time"] = timedelta(minutes=int(default_time))

        # DefMemPerCPU
        def_mem = part.get("def_mem_per_cpu")
        if def_mem is not None:
            try:
                kwargs["def_mem_per_cpu"] = int(def_mem)
            except (ValueError, TypeError):
                pass

        # QOS references
        allow_qos_names: set[str] = set()
        allow_qos = part.get("allow_qos", "")
        if isinstance(allow_qos, str) and allow_qos and allow_qos.upper() != "ALL":
            allow_qos_names.update(n.strip() for n in allow_qos.split(","))
        qos_assigned = part.get("qos", "")

        try:
            partition = SlurmPartition.objects.get(cluster=cluster, name=part_name)
            if update:
                for k, v in kwargs.items():
                    if k != "cluster":
                        setattr(partition, k, v)
                partition.save()
                report.partitions_updated += 1
            else:
                report.partitions_found += 1
        except SlurmPartition.DoesNotExist:
            partition = SlurmPartition(**kwargs)
            partition.save()
            report.partitions_created += 1

        # Link QOS references
        # AllowQOS (whitelist) -> partition.allow_qos M2M
        if allow_qos_names:
            allow_qos_objs = SlurmQOS.objects.filter(name__in=list(allow_qos_names))
            partition.allow_qos.set(allow_qos_objs)

        # QOS (assigned partition QOS) -> partition.qos FK
        if isinstance(qos_assigned, str) and qos_assigned and qos_assigned.upper() != "ALL":
            try:
                partition.qos = SlurmQOS.objects.get(name=qos_assigned.strip())
                partition.save()
            except SlurmQOS.DoesNotExist:
                pass

    report.success = len(report.errors) == 0
    return report


def _parse_duration(duration_str: str) -> timedelta | None:
    """Parse a Slurm duration string into a timedelta.

    Supports formats:
        ``24:00:00`` (HH:MM:SS)
        ``01:00:00`` (HH:MM:SS)
        ``72:00:00`` (HH:MM:SS)
        ``30-0`` (days-hours)
        ``00:30:00`` (HH:MM:SS)
    """
    if not duration_str:
        return None

    duration_str = duration_str.strip()

    # Try HH:MM:SS format
    if ":" in duration_str:
        parts = duration_str.split(":")
        if len(parts) == 3:
            try:
                h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                return timedelta(hours=h, minutes=m, seconds=s)
            except ValueError:
                pass

    # Try days-hours format (e.g., "30-0")
    if "-" in duration_str:
        parts = duration_str.split("-", 1)
        try:
            days = int(parts[0])
            hours = int(parts[1]) if len(parts) > 1 else 0
            return timedelta(days=days, hours=hours)
        except ValueError:
            pass

    # Try plain minutes
    try:
        return timedelta(minutes=int(duration_str))
    except ValueError:
        return None
