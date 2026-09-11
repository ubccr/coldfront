# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""SU usage rollup: ingest per-day job usage from the Slurm REST API.

Pulls job accounting from slurmrestd, aggregates it into per-account daily
usage, and writes :class:`SlurmAccountUsage` records. Entry points:

* ``run_usage_sync()`` — ingest a day range for a cluster.
* ``resolve_catchup_range()`` — the (start, end) day range to ingest.
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from datetime import timezone as dt_timezone
from typing import Any

from django.core.exceptions import ImproperlyConfigured
from django.utils import timezone

from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAccountUsage,
    SlurmCluster,
)
from coldfront.slurm.utils import build_client

logger = logging.getLogger(__name__)


@dataclass
class UsageSyncReport:
    """Detailed report returned by :func:`run_usage_sync`."""

    cluster: str
    success: bool = False
    days_synced: int = 0
    accounts_updated: int = 0
    jobs_ingested: int = 0
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    duration_ms: int = 0


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
    """Return (start, end) UNIX timestamps for the UTC midnight window of a day.

    The window is anchored at true UTC midnight regardless of Django's
    ``TIME_ZONE`` — Slurm accounts usage on UTC calendar days, so the day
    label fed in here must line up with the UTC day a job's ``time.start`` /
    ``time.end`` (UNIX seconds) fall into. (``timezone.make_aware`` would
    interpret the naive date in the configured local zone and drift the
    window by the UTC offset.)
    """
    start = datetime.combine(day, time.min, tzinfo=dt_timezone.utc).timestamp()
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


def resolve_catchup_range(cluster: SlurmCluster) -> tuple[datetime.date, datetime.date] | None:
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


def run_usage_sync(
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
    try:
        client = build_client(cluster.name)
    except ImproperlyConfigured as exc:
        report.errors.append(f"slurmrestd not configured: {exc}")
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
