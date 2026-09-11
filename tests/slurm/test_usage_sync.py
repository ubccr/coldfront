# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for daily SU usage aggregation and sync.

Organized by test class:

- ``TestRollUpJobUsage`` — aggregation (consumed + completed attribution)
- ``TestResolveCatchupRange`` — catch-up range computation + cap
- ``TestRunUsageSync`` — orchestration (upsert, unknown accounts, failures)
"""

from datetime import date, timedelta
from unittest import mock

from django.core.exceptions import ImproperlyConfigured
from django.test import TestCase
from django.utils import timezone

from coldfront.slurm.models import SlurmAccount, SlurmAccountUsage, SlurmCluster
from coldfront.slurm.sync.usage import (
    USAGE_SYNC_MAX_CATCHUP_DAYS,
    _roll_up_job_usage,
    _utc_day_bounds,
    resolve_catchup_range,
    run_usage_sync,
)

# ======================================================================
# 1. MODEL
# ======================================================================


def _job(
    account="acct-a",
    partition="gpu",
    qos="normal",
    start=3600,
    end=7200,
    elapsed=3600,
    billing_count=2,
    node_count=4,
) -> dict:
    """Build a synthetic slurmdbd job record for _roll_up_job_usage tests."""
    return {
        "account": account,
        "partition": partition,
        "qos": qos,
        "time": {"start": start, "end": end, "elapsed": elapsed},
        "tres": {
            "allocated": [
                {"type": "billing", "name": "billing", "id": 5, "count": billing_count},
                {"type": "node", "name": "node", "id": 4, "count": node_count},
            ]
        },
    }


class TestRollUpJobUsage:
    DAY_START = 0
    DAY_END = 86400

    def test_consumed_attribution(self):
        agg = _roll_up_job_usage([_job()], self.DAY_START, self.DAY_END)
        a = agg["acct-a"]
        # billing_count(2) x overlap(3600s) / 3600 = 2.0
        assert a.billing_units_consumed == 2.0
        assert a.walltime_sec_consumed == 3600
        # node_count(4) x overlap-hours(1) = 4.0
        assert a.node_hours_consumed == 4.0
        assert a.job_count_consumed == 1
        # completed: job finished (end=7200) inside window -> full elapsed
        assert a.billing_units_completed == 2.0
        assert a.walltime_sec_completed == 3600
        assert a.job_count_completed == 1
        assert a.node_hours_by_partition == {"gpu": 4.0}
        assert a.billing_by_qos == {"normal": 2.0}

    def test_still_running_job_clipped_at_day_end(self):
        # end=0 means still running -> clipped to day_end
        agg = _roll_up_job_usage([_job(start=1000, end=0)], self.DAY_START, self.DAY_END)
        a = agg["acct-a"]
        overlap = 86400 - 1000  # 85400
        assert a.billing_units_consumed == 2 * overlap / 3600.0
        assert a.walltime_sec_consumed == overlap
        # No completed attribution for a running job
        assert a.billing_units_completed == 0.0
        assert a.job_count_completed == 0

    def test_skips_pending_and_zero_overlap_jobs(self):
        pending = _job(start=0, end=0)
        # job starting after day_end -> zero overlap in window
        future = _job(start=self.DAY_END + 3600, end=self.DAY_END + 7200)
        agg = _roll_up_job_usage([pending, future], self.DAY_START, self.DAY_END)
        assert agg == {}

    def test_missing_billing_tres_counts_as_zero(self):
        job = _job()
        job["tres"]["allocated"] = [{"type": "node", "name": "node", "id": 4, "count": 4}]
        agg = _roll_up_job_usage([job], self.DAY_START, self.DAY_END)
        a = agg["acct-a"]
        assert a.billing_units_consumed == 0.0
        assert a.node_hours_consumed == 4.0

    def test_groups_by_account(self):
        jobs = [_job(account="acct-a"), _job(account="acct-b")]
        agg = _roll_up_job_usage(jobs, self.DAY_START, self.DAY_END)
        assert set(agg.keys()) == {"acct-a", "acct-b"}

    def test_job_spanning_two_days_pro_rates(self):
        # A job spanning midnight: 1 hour before, 1 hour after.
        # Day1 window [0, 86400): overlap = 86400 - 82800 = 3600
        # Day2 window [86400, 172800): overlap = 90000 - 86400 = 3600
        job = _job(start=82800, end=90000, elapsed=7200, billing_count=2)
        day1 = _roll_up_job_usage([job], 0, 86400)["acct-a"]
        day2 = _roll_up_job_usage([job], 86400, 172800)["acct-a"]
        assert day1.billing_units_consumed == 2 * 3600 / 3600.0  # 2.0
        assert day2.billing_units_consumed == 2 * 3600 / 3600.0  # 2.0
        # Completed attribution only on the day the job finished (day2)
        assert day1.billing_units_completed == 0.0
        assert day2.billing_units_completed == 2 * 7200 / 3600.0  # 4.0


# ======================================================================
# 4. CATCH-UP RANGE
# ======================================================================


class TestResolveCatchupRange(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")

    def test_caps_window_to_most_recent_days(self):
        """No last sync (or one far older than the cap) -> ingest the most
        recent CAP days ending yesterday."""
        yesterday = timezone.localdate() - timedelta(days=1)
        expected_start = yesterday - timedelta(days=USAGE_SYNC_MAX_CATCHUP_DAYS - 1)

        # no last sync
        start, end = resolve_catchup_range(self.cluster)
        assert end == yesterday
        assert start == expected_start

        # last sync far older than the cap -> clamp to most recent CAP days
        self.cluster.last_usage_sync = timezone.localdate() - timedelta(days=500)
        self.cluster.save()
        start, end = resolve_catchup_range(self.cluster)
        assert start == expected_start
        assert end == yesterday

    def test_resumes_from_last_sync_plus_one(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        self.cluster.last_usage_sync = yesterday - timedelta(days=10)
        self.cluster.save()
        start, end = resolve_catchup_range(self.cluster)
        assert start == self.cluster.last_usage_sync + timedelta(days=1)
        assert end == yesterday

    def test_none_when_already_caught_up(self):
        self.cluster.last_usage_sync = timezone.localdate() - timedelta(days=1)
        self.cluster.save()
        assert resolve_catchup_range(self.cluster) is None

    def test_caps_long_gap_to_most_recent_days(self):
        # last_usage_sync far older than the cap -> clamp to most recent CAP days
        self.cluster.last_usage_sync = timezone.localdate() - timedelta(days=500)
        self.cluster.save()
        start, end = resolve_catchup_range(self.cluster)
        yesterday = timezone.localdate() - timedelta(days=1)
        assert start == yesterday - timedelta(days=USAGE_SYNC_MAX_CATCHUP_DAYS - 1)
        assert end == yesterday


# ======================================================================
# 5. ORCHESTRATION — run_usage_sync
# ======================================================================


class TestRunUsageSync(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")
        cls.account = SlurmAccount.objects.create(
            name="acct-a",
            cluster=cls.cluster,
            service_units=10000,
        )
        cls.other = SlurmAccount.objects.create(
            name="acct-b",
            cluster=cls.cluster,
            service_units=5000,
        )

    def _client(self, jobs_by_day):
        client = mock.MagicMock()
        client.get_job_usage.side_effect = lambda s, e, c: jobs_by_day.get(s, [])
        return client

    def test_skips_unknown_accounts(self):
        day = timezone.localdate() - timedelta(days=1)
        day_start, _ = _utc_day_bounds(day)
        job = {
            "account": "root",  # not managed by ColdFront
            "partition": "gpu",
            "qos": "normal",
            "time": {"start": day_start + 3600, "end": day_start + 7200, "elapsed": 3600},
            "tres": {
                "allocated": [
                    {"type": "billing", "name": "billing", "id": 5, "count": 1},
                ]
            },
        }
        client = self._client({day_start: [job]})
        with mock.patch("coldfront.slurm.sync.usage.build_client", return_value=client):
            report = run_usage_sync(self.cluster, day, day)
        assert report.success
        assert report.accounts_updated == 0
        assert SlurmAccountUsage.objects.filter(account=self.account).count() == 0
        # last_usage_sync still advances (no errors)
        self.cluster.refresh_from_db()
        assert self.cluster.last_usage_sync == day

    def test_unconfigured_cluster_returns_error_report(self):
        """No slurmrestd config -> error report (no REST call), last_sync unadvanced."""
        with mock.patch(
            "coldfront.slurm.sync.usage.build_client",
            side_effect=ImproperlyConfigured("no url"),
        ):
            report = run_usage_sync(self.cluster, date(2024, 1, 1), date(2024, 1, 1))
        assert not report.success
        assert "not configured" in report.errors[0]
        self.cluster.refresh_from_db()
        assert self.cluster.last_usage_sync is None

    def test_auth_failure_fails_fast_without_advancing(self):
        client = mock.MagicMock()
        client.get_job_usage.side_effect = Exception("401 unauthorized")
        day = timezone.localdate() - timedelta(days=1)
        with mock.patch("coldfront.slurm.sync.usage.build_client", return_value=client):
            report = run_usage_sync(self.cluster, day, day)
        assert not report.success
        assert "401 unauthorized" in report.errors[0]
        self.cluster.refresh_from_db()
        assert self.cluster.last_usage_sync is None


# ======================================================================
# 6. JOBS
# ======================================================================
