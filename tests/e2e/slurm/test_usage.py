# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Live Slurm usage/billing e2e tests.

Drives the usage sync engine (``run_usage_sync``) against the live stack via
Django DB seeding (``pytest.mark.django_db``) + ``slurm_settings``, using
**real completed jobs** submitted as the baked-in ``cgray`` user.

These lock in the billing reality probed live:

* ``tres.allocated`` carries a ``billing`` TRES. The base ``slurm.conf`` has no
  ``TRESBillingWeights``, so billing falls back to the default ``CPU=1`` weight
  (``billing`` count ``1`` for a 1-cpu job).
* A test sets ``TRESBillingWeights=CPU=2.0,Node=3.0`` at runtime on the shared
  stack via the REST API (``POST /partitions/`` -> ``tres/billing_weights``),
  so a 1-cpu job bills ``5`` (= 1 x 2.0 + 1 x 3.0). This path is only available
  on versions that expose ``POST /partitions/`` (26.05.x / v0.0.45); the
  billing test skips others. The runtime weights are wiped by the generic
  cleanup's reconfigure, so the default ``CPU=1`` billing of the other tests is
  never affected.
* ``_roll_up_job_usage``'s math (``billing_count x overlap / 3600``) matches
  the live record, so the ``SlurmAccountUsage`` DB row is verified against the
  **computed** value (there is no ``sacct Billing`` column on the live stack).
* Re-running the sync is idempotent (``update_or_create`` per account/day).
"""

import uuid
from datetime import datetime
from datetime import time as _t
from datetime import timezone as _tz

import pytest
from django.utils import timezone

from coldfront.slurm.models import SlurmAccount, SlurmAccountUsage, SlurmCluster
from coldfront.slurm.sync.usage import run_usage_sync
from tests.e2e.slurm.conftest import (
    create_live_account_for_job,
    require_version,
    submit_sleep_job,
    wait_for_job_completion,
)

# Cluster name defined in the vendored slurm.conf (ClusterName=linux).
CLUSTER = "linux"

# TRES ids in tres.allocated (Slurm internal TRES_ARRAY indices) — verified
# live on both supported versions: cpu=1, mem=2, energy=3, node=4, billing=5.
_TRES_NODE = 4
_TRES_BILLING = 5

# Billing weights baked into each stack variant.
BILLING_COUNT_STOCK = 1  # default CPU=1 weight, 1-cpu job
BILLING_COUNT_WEIGHTED = 5  # CPU=2.0 + Node=3.0, 1-cpu job


def _uniq(prefix: str) -> str:
    """Unique name for this run, so tests never collide on the shared stack."""
    return f"e2e-{prefix}-{uuid.uuid4().hex[:10]}"


def _seed_usage(slurm_stack, slurm_client, slurm_jwt):
    """Seed a Django SlurmCluster + SlurmAccount and the live account.

    Returns (cluster_obj, account, acct_name). The live account + parent +
    cgray assoc are created so a job can be submitted. The Django rows roll
    back at teardown (pytest-django); the live entities are removed by the
    autouse ``slurm_cleanup``.
    """
    acct_name = _uniq("acct")
    cluster_obj = SlurmCluster.objects.create(name=CLUSTER, description="e2e usage")
    account = SlurmAccount.objects.create(name=acct_name, cluster=cluster_obj, description="e2e usage")

    create_live_account_for_job(slurm_stack, slurm_client, slurm_jwt, acct_name)

    return cluster_obj, account, acct_name


def _tres_count(tres_allocated, tres_id: int) -> int:
    """Read a TRES count from a live ``tres.allocated`` list."""
    for entry in tres_allocated or []:
        if entry.get("id") == tres_id:
            return int(entry.get("count", 0))
    return 0


def _find_job(slurm_client, acct_name, job_id):
    """Query a wide usage window and return the live job record for ``job_id``."""
    now = int(timezone.now().timestamp())
    jobs = slurm_client.get_job_usage(now - 7200, now + 7200, CLUSTER)
    for job in jobs:
        if str(job.get("job_id", "")) == str(job_id) and job.get("account", "") == acct_name:
            return job
    raise AssertionError(f"job {job_id} not found in get_job_usage (account={acct_name})")


def _sync_and_verify(cluster_obj, account, acct_name, job, expected_billing_count):
    """Run run_usage_sync for the job's completion day and verify the DB row.

    The expected values are computed **independently** from the live record
    plus the day window (not from ``_roll_up_job_usage`` itself), so the DB
    row proves the ingestion math against the real job accounting.
    """
    start_ts = int(job["time"]["start"])
    end_ts = int(job["time"]["end"])
    elapsed = int(job["time"]["elapsed"])
    assert end_ts != 0 and start_ts != 0

    billing_count = _tres_count(job.get("tres", {}).get("allocated"), _TRES_BILLING)
    node_count = _tres_count(job.get("tres", {}).get("allocated"), _TRES_NODE)
    assert billing_count == expected_billing_count, (
        f"billing count {billing_count} != expected {expected_billing_count} (TRESBillingWeights not honored?): {job}"
    )

    # The job's completion day (UTC) — sync that day. Compute the UTC
    # midnight window independently (not via ``_utc_day_bounds`` itself).
    end_day = datetime.fromtimestamp(end_ts, tz=_tz.utc).date()
    day_start = datetime.combine(end_day, _t.min, tzinfo=_tz.utc).timestamp()
    day_end = day_start + 86400
    overlap = max(0, min(end_ts, day_end) - max(start_ts, day_start))

    report = run_usage_sync(cluster_obj, end_day, end_day)
    assert report.errors == [], f"usage sync errors: {report.errors}"
    assert report.success
    assert report.days_synced == 1
    assert report.jobs_ingested >= 1
    assert report.accounts_updated >= 1

    row = SlurmAccountUsage.objects.get(
        cluster=cluster_obj,
        account=account,
        period_start=end_day,
    )
    assert row.billing_units_consumed == pytest.approx(billing_count * overlap / 3600.0, rel=1e-6)
    assert row.walltime_sec_consumed == overlap
    assert row.node_hours_consumed == pytest.approx(node_count * overlap / 3600.0, rel=1e-6)
    assert row.job_count_consumed == 1
    # informational completion attribution (job finished inside this window)
    assert row.billing_units_completed == pytest.approx(billing_count * elapsed / 3600.0, rel=1e-6)
    assert row.walltime_sec_completed == elapsed
    assert row.job_count_completed == 1
    # per-partition / per-QOS breakdowns
    assert row.node_hours_by_partition == {"cpu": pytest.approx(node_count * overlap / 3600.0, rel=1e-6)}
    assert row.billing_by_qos == {"normal": pytest.approx(billing_count * overlap / 3600.0, rel=1e-6)}

    # last_usage_sync advanced to the ingested day
    cluster_obj.refresh_from_db()
    assert cluster_obj.last_usage_sync == end_day

    return report, end_day


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.usefixtures("slurm_settings")
class TestUsageLive:
    """Usage sync against the stock stack (default CPU=1 billing weight)."""

    def test_usage_sync_ingests_real_job_and_is_idempotent(self, slurm_stack, slurm_client, slurm_jwt):
        """A real completed job is ingested; re-run does not double-count."""
        cluster_obj, account, acct_name = _seed_usage(slurm_stack, slurm_client, slurm_jwt)

        job_id = submit_sleep_job(slurm_stack, acct_name, seconds=30)
        wait_for_job_completion(slurm_stack, job_id)
        job = _find_job(slurm_client, acct_name, job_id)

        report, end_day = _sync_and_verify(cluster_obj, account, acct_name, job, BILLING_COUNT_STOCK)

        # Idempotent re-run: update_or_create keeps the same values, no
        # double-count, and last_usage_sync stays at end_day.
        row_before = SlurmAccountUsage.objects.get(cluster=cluster_obj, account=account, period_start=end_day)
        rerun = run_usage_sync(cluster_obj, end_day, end_day)
        assert rerun.errors == [] and rerun.success
        row_after = SlurmAccountUsage.objects.get(cluster=cluster_obj, account=account, period_start=end_day)
        assert row_after.billing_units_consumed == row_before.billing_units_consumed
        assert row_after.job_count_consumed == row_before.job_count_consumed
        assert SlurmAccountUsage.objects.filter(cluster=cluster_obj, account=account).count() == 1


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.usefixtures("slurm_settings")
class TestUsageBillingVariant:
    """Usage sync against runtime TRESBillingWeights (set via the REST API).

    The shared stack runs on the base slurm.conf (no baked-in
    TRESBillingWeights), so the test sets ``TRESBillingWeights=CPU=2.0,Node=3.0``
    at runtime on the cpu partition via ``POST /partitions/`` and verifies the
    billing TRES honors the weights end-to-end. The autouse cleanup's
    reconfigure wipes the runtime weights after the test, so the default
    ``CPU=1`` billing of the other tests is never affected.
    """

    def test_billing_weights_honored_end_to_end(self, slurm_stack, slurm_client, slurm_jwt):
        """billing count reflects CPU=2.0,Node=3.0 and units follow it."""
        # Runtime TRESBillingWeights pushes need POST /partitions/ (v0.0.45 only).
        require_version(slurm_stack, ">=26.05.4")
        cluster_obj, account, acct_name = _seed_usage(slurm_stack, slurm_client, slurm_jwt)

        # Set explicit billing weights at runtime on the shared stack's cpu
        # partition (the base slurm.conf has none, so default is CPU=1.0).
        body = slurm_client.update_partitions(
            [slurm_client.serialize_partition("cpu", tres_billing_weights="CPU=2.0,Node=3.0")]
        )
        assert not body.get("errors"), f"update_partitions errors: {body.get('errors')}"

        job_id = submit_sleep_job(slurm_stack, acct_name, seconds=30)
        wait_for_job_completion(slurm_stack, job_id)
        job = _find_job(slurm_client, acct_name, job_id)

        _sync_and_verify(cluster_obj, account, acct_name, job, BILLING_COUNT_WEIGHTED)
