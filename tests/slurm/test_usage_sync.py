# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for daily SU usage aggregation and sync.

Organized by test class:

- ``TestSlurmAccountUsageModel`` — model fields + unique constraint
- ``TestGetJobUsage`` — client REST query (params + payload)
- ``TestRollUpJobUsage`` — aggregation (consumed + completed attribution)
- ``TestResolveCatchupRange`` — catch-up range computation + cap
- ``TestRunUsageSync`` — orchestration (upsert, unknown accounts, failures)
- ``TestUsageJobs`` — periodic + on-demand jobs
- ``TestUsageSyncCommand`` — management command
"""

from __future__ import annotations

from datetime import date, timedelta
from unittest import mock

import pytest
import responses
from django.test import TestCase
from django.utils import timezone

from coldfront.slurm.client import SlurmClient
from coldfront.slurm.models import SlurmAccount, SlurmAccountUsage, SlurmCluster
from coldfront.slurm.sync import (
    USAGE_SYNC_MAX_CATCHUP_DAYS,
    _resolve_catchup_range,
    _roll_up_job_usage,
    _run_usage_sync,
    _utc_day_bounds,
)

_DEFAULT_BASE = "http://mock.slurm.test"
_DEFAULT_VER = "v0.0.44"


# ======================================================================
# 1. MODEL
# ======================================================================


class TestSlurmAccountUsageModel(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")
        cls.account = SlurmAccount.objects.create(
            name="acct-a",
            cluster=cls.cluster,
            service_units=10000,
        )

    def test_row_fields(self):
        row = SlurmAccountUsage.objects.create(
            cluster=self.cluster,
            account=self.account,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 1),
            billing_units_consumed=10.5,
            billing_units_completed=12.0,
            walltime_sec_consumed=3600,
            walltime_sec_completed=7200,
            node_hours_consumed=4.0,
            node_hours_by_partition={"gpu": 4.0},
            billing_by_qos={"normal": 10.5},
            job_count_consumed=2,
            job_count_completed=1,
        )
        assert row.billing_units_consumed == 10.5
        assert row.node_hours_by_partition == {"gpu": 4.0}
        assert str(row) == "acct-a @ hpc01 2024-01-01"

    def test_unique_per_account_day(self):
        SlurmAccountUsage.objects.create(
            cluster=self.cluster,
            account=self.account,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 1),
        )
        # Same cluster/account/day must violate the unique constraint
        with pytest.raises(Exception):
            SlurmAccountUsage.objects.create(
                cluster=self.cluster,
                account=self.account,
                period_start=date(2024, 1, 1),
                period_end=date(2024, 1, 1),
            )

    def test_allows_same_account_different_day(self):
        SlurmAccountUsage.objects.create(
            cluster=self.cluster,
            account=self.account,
            period_start=date(2024, 1, 1),
            period_end=date(2024, 1, 1),
        )
        row2 = SlurmAccountUsage.objects.create(
            cluster=self.cluster,
            account=self.account,
            period_start=date(2024, 1, 2),
            period_end=date(2024, 1, 2),
        )
        assert row2.pk is not None


# ======================================================================
# 2. CLIENT — get_job_usage
# ======================================================================


class TestGetJobUsage:
    @responses.activate
    def test_queries_jobs_with_overlap_window(self):
        resp_body = {
            "jobs": [
                {
                    "account": "acct-a",
                    "partition": "gpu",
                    "qos": "normal",
                    "time": {"start": 1000, "end": 5000},
                    "tres": {
                        "allocated": [
                            {"type": "billing", "name": "billing", "id": 5, "count": 2},
                            {"type": "node", "name": "node", "id": 4, "count": 4},
                        ]
                    },
                }
            ],
            "errors": [],
            "warnings": [],
        }
        responses.add(
            responses.GET,
            f"{_DEFAULT_BASE}/slurmdb/{_DEFAULT_VER}/jobs/",
            json=resp_body,
            status=200,
        )
        client = SlurmClient(base_url=_DEFAULT_BASE, jwt_token="t", version=_DEFAULT_VER)
        jobs = client.get_job_usage(86400, 172800, "hpc01")

        req = responses.calls[0].request
        assert req.params["start_time"] == "86400"
        assert req.params["end_time"] == "172800"
        assert req.params["cluster"] == "hpc01"
        assert req.params["disable_truncate_usage_time"] == "true"
        assert jobs[0]["account"] == "acct-a"
        assert jobs[0]["tres"]["allocated"][0]["count"] == 2

    @responses.activate
    def test_returns_empty_when_no_jobs(self):
        responses.add(
            responses.GET,
            f"{_DEFAULT_BASE}/slurmdb/{_DEFAULT_VER}/jobs/",
            json={"jobs": [], "errors": [], "warnings": []},
            status=200,
        )
        client = SlurmClient(base_url=_DEFAULT_BASE, jwt_token="t", version=_DEFAULT_VER)
        assert client.get_job_usage(86400, 172800, "hpc01") == []


# ======================================================================
# 3. AGGREGATION — _roll_up_job_usage
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

    def test_no_last_sync_ingests_capped_window(self):
        start, end = _resolve_catchup_range(self.cluster)
        yesterday = timezone.localdate() - timedelta(days=1)
        assert end == yesterday
        assert start == yesterday - timedelta(days=USAGE_SYNC_MAX_CATCHUP_DAYS - 1)

    def test_resumes_from_last_sync_plus_one(self):
        yesterday = timezone.localdate() - timedelta(days=1)
        self.cluster.last_usage_sync = yesterday - timedelta(days=10)
        self.cluster.save()
        start, end = _resolve_catchup_range(self.cluster)
        assert start == self.cluster.last_usage_sync + timedelta(days=1)
        assert end == yesterday

    def test_none_when_already_caught_up(self):
        self.cluster.last_usage_sync = timezone.localdate() - timedelta(days=1)
        self.cluster.save()
        assert _resolve_catchup_range(self.cluster) is None

    def test_caps_long_gap_to_most_recent_days(self):
        # last_usage_sync far older than the cap -> clamp to most recent CAP days
        self.cluster.last_usage_sync = timezone.localdate() - timedelta(days=500)
        self.cluster.save()
        start, end = _resolve_catchup_range(self.cluster)
        yesterday = timezone.localdate() - timedelta(days=1)
        assert start == yesterday - timedelta(days=USAGE_SYNC_MAX_CATCHUP_DAYS - 1)
        assert end == yesterday


# ======================================================================
# 5. ORCHESTRATION — _run_usage_sync
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

    def test_upserts_rows_and_advances_last_sync(self):
        day = timezone.localdate() - timedelta(days=1)
        day_start, _ = _utc_day_bounds(day)
        # One job overlapping that day (runs in the first hour)
        job = {
            "account": "acct-a",
            "partition": "gpu",
            "qos": "normal",
            "time": {"start": day_start + 3600, "end": day_start + 7200, "elapsed": 3600},
            "tres": {
                "allocated": [
                    {"type": "billing", "name": "billing", "id": 5, "count": 2},
                    {"type": "node", "name": "node", "id": 4, "count": 4},
                ]
            },
        }
        client = self._client({day_start: [job]})
        with mock.patch("coldfront.slurm.sync._build_client", return_value=client):
            report = _run_usage_sync(self.cluster, day, day)

        assert report.success
        assert report.days_synced == 1
        assert report.accounts_updated == 1
        row = SlurmAccountUsage.objects.get(account=self.account, period_start=day)
        assert row.billing_units_consumed == 2.0
        assert row.billing_units_completed == 2.0
        self.cluster.refresh_from_db()
        assert self.cluster.last_usage_sync == day

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
        with mock.patch("coldfront.slurm.sync._build_client", return_value=client):
            report = _run_usage_sync(self.cluster, day, day)
        assert report.success
        assert report.accounts_updated == 0
        assert SlurmAccountUsage.objects.filter(account=self.account).count() == 0
        # last_usage_sync still advances (no errors)
        self.cluster.refresh_from_db()
        assert self.cluster.last_usage_sync == day

    def test_no_client_returns_error(self):
        with mock.patch("coldfront.slurm.sync._build_client", return_value=None):
            report = _run_usage_sync(self.cluster, date(2024, 1, 1), date(2024, 1, 1))
        assert not report.success
        assert "not configured" in report.errors[0]
        self.cluster.refresh_from_db()
        assert self.cluster.last_usage_sync is None

    def test_auth_failure_fails_fast_without_advancing(self):
        client = mock.MagicMock()
        client.get_job_usage.side_effect = Exception("401 unauthorized")
        day = timezone.localdate() - timedelta(days=1)
        with mock.patch("coldfront.slurm.sync._build_client", return_value=client):
            report = _run_usage_sync(self.cluster, day, day)
        assert not report.success
        assert "401 unauthorized" in report.errors[0]
        self.cluster.refresh_from_db()
        assert self.cluster.last_usage_sync is None


# ======================================================================
# 6. JOBS
# ======================================================================


class TestUsageJobs(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")

    def test_periodic_job_calls_run_usage_sync(self):
        from coldfront.slurm.jobs import SlurmUsageSyncJob

        job = SlurmUsageSyncJob(mock.MagicMock())
        yesterday = timezone.localdate() - timedelta(days=1)
        with (
            mock.patch(
                "coldfront.slurm.jobs._resolve_catchup_range",
                return_value=(yesterday - timedelta(days=2), yesterday),
            ) as mock_range,
            mock.patch("coldfront.slurm.jobs._run_usage_sync") as mock_sync,
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
            mock.patch(
                "coldfront.slurm.jobs._resolve_catchup_range",
                return_value=None,
            ) as mock_range,
            mock.patch(
                "coldfront.slurm.jobs._run_usage_sync",
            ) as mock_sync,
        ):
            result = job.run()
        assert result is True
        mock_range.assert_called_once()
        mock_sync.assert_not_called()

    def test_on_demand_job_with_explicit_range(self):
        from coldfront.slurm.jobs import SlurmUsageSyncNowJob

        job = SlurmUsageSyncNowJob(mock.MagicMock())
        start = "2024-01-01"
        end = "2024-01-10"
        with mock.patch("coldfront.slurm.jobs._run_usage_sync") as mock_sync:
            mock_sync.return_value.success = True
            result = job.run(cluster_id=self.cluster.pk, start=start, end=end)
        assert result is True
        mock_sync.assert_called_once()
        assert mock_sync.call_args[0][0] == self.cluster
        assert mock_sync.call_args[0][1] == date(2024, 1, 1)
        assert mock_sync.call_args[0][2] == date(2024, 1, 10)


# ======================================================================
# 7. MANAGEMENT COMMAND
# ======================================================================


class TestUsageSyncCommand(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cluster = SlurmCluster.objects.create(name="hpc01")

    def test_command_runs_range_sync(self):
        from django.core.management import call_command

        with mock.patch("coldfront.slurm.sync._run_usage_sync") as mock_sync:
            mock_sync.return_value.success = True
            call_command("slurm_usage_sync", cluster="hpc01", verbosity=0)
        assert mock_sync.called
        assert mock_sync.call_args[0][0] == self.cluster

    def test_command_with_explicit_dates(self):
        from django.core.management import call_command

        with mock.patch("coldfront.slurm.sync._run_usage_sync") as mock_sync:
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
        from django.core.management import call_command

        with mock.patch("coldfront.slurm.sync._run_usage_sync") as mock_sync:
            call_command("slurm_usage_sync", cluster="nope", verbosity=0)
        assert not mock_sync.called
