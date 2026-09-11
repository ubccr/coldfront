# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Live e2e test: the full project -> allocation -> association -> running-job flow.

Exercises every code path that lets an owner go from a project with an
allocation on a Slurm cluster through to an actual running job:

* seed the Django models (owner + members, allocation, account, association),
* ingest the live cluster config from the REST API,
* ``sync_slurm_clusters`` to materialize the live Slurm hierarchy (account +
  account-level parent + user records + user-level associations) and the
  ``SlurmUser`` bookkeeping,
* verify the hierarchy, default accounts, and that a synced member can submit
  and run a real job.

Uses the four system users baked into the ``slurm-docker-cluster`` images
(``cgray sfoster csimmons astewart``); ``cgray`` owns the project, all four
are members. A second test re-runs the sync to lock in idempotency.
"""

import uuid

import pytest
from django.contrib.auth import get_user_model

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.models import Allocation, Project, ProjectUser
from coldfront.slurm.ingest import ingest_cluster_from_api
from coldfront.slurm.models import SlurmAccount, SlurmAssociation, SlurmCluster, SlurmPartition, SlurmUser
from coldfront.slurm.sync import sync_slurm_clusters
from tests.e2e.slurm.conftest import submit_sleep_job, wait_for_job_completion

# Cluster name defined in the slurm.conf (ClusterName=linux).
CLUSTER = "linux"

User = get_user_model()

# The four system users baked into the slurm-docker-cluster images.
SYSTEM_USERS = ["cgray", "sfoster", "csimmons", "astewart"]
OWNER = "cgray"

# The stock partition that the ingested cluster is expected to carry.
STOCK_PARTITION = "cpu"


def _uniq(prefix: str) -> str:
    """Unique name for this run, so tests never collide on the shared stack."""
    return f"e2e-flow-{prefix}-{uuid.uuid4().hex[:10]}"


def _seed_project_with_allocation(slurm_client):
    """Seed the Django models the full project->allocation flow operates on.

    Creates Django User rows for the four baked-in system users, a Project
    owned by ``cgray`` with all four as project members, ingests the live
    cluster from the REST API, then creates an active Allocation on the
    ingested cluster together with its SlurmAccount and SlurmAssociation.

    Returns ``(cluster, account, allocation, association, users)`` so tests can
    tweak the association (fairshare, limits, ...) before activating.

    The Django rows roll back at test teardown (pytest-django); the live Slurm
    entities are removed by the autouse ``slurm_cleanup``.
    """
    users = {name: User.objects.create(username=name, is_active=True) for name in SYSTEM_USERS}
    project = Project.objects.create(name=_uniq("proj"), owner=users[OWNER])
    for name in SYSTEM_USERS:
        ProjectUser.objects.create(project=project, user=users[name])

    # Ingest the stock cluster config from the live API — the cluster,
    # partitions (cpu/gpu), and QOS all land in the Django DB.
    report = ingest_cluster_from_api(CLUSTER, client=slurm_client)
    assert report.errors == [], f"ingest errors: {report.errors}"
    cluster = SlurmCluster.objects.get(name=CLUSTER)

    allocation = Allocation.objects.create(
        project=project,
        resource_object=cluster,
        owner=users[OWNER],
        status=AllocationStatusChoices.STATUS_ACTIVE,
        description="e2e project allocation flow",
    )
    account = SlurmAccount.objects.create(
        name=_uniq("acct"),
        cluster=cluster,
        description="e2e project allocation flow",
    )
    association = SlurmAssociation.objects.create(
        allocation=allocation,
        slurm_account=account,
        fairshare=1,
    )

    return cluster, account, allocation, association, users


def _assert_sync_success(report) -> None:
    """A sync report must carry no errors."""
    assert report.errors == [], f"sync errors: {report.errors}"
    assert report.success, f"sync failed: {report.errors}"


def _live_default_accounts(slurm_stack) -> dict[str, str]:
    """Query slurmdbd for each user's default account (authoritative).

    ``sacctmgr -nP show user format=U,DefaultA`` prints
    ``<user>|<default-account>`` lines; returns a {username: account} map.
    """
    out, _err, rc = slurm_stack.exec(
        "slurmdbd",
        ["bash", "-c", "sacctmgr -nP show user format=U,DefaultA"],
    )
    assert rc == 0, f"sacctmgr show user failed: {_err.strip()}"
    defaults = {}
    for line in out.splitlines():
        fields = line.split("|")
        if len(fields) >= 2 and fields[0].strip():
            defaults[fields[0].strip()] = fields[1].strip()
    return defaults


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.usefixtures("slurm_settings")
class TestProjectAllocationFlow:
    """Full project -> allocation -> association -> running-job flow, live."""

    def test_project_allocation_round_trip(self, slurm_stack, slurm_client):
        """An allocation sync creates the hierarchy, default accounts, and a runnable job."""
        cluster, account, allocation, _, users = _seed_project_with_allocation(slurm_client)
        acct = account.name
        # The ingest must have landed the stock partition the job uses below.
        assert SlurmPartition.objects.get(cluster=cluster, name=STOCK_PARTITION)

        report = sync_slurm_clusters([CLUSTER])[0]
        _assert_sync_success(report)
        assert report.accounts_created >= 1
        assert report.users_created >= len(SYSTEM_USERS)
        assert report.associations_created >= len(SYSTEM_USERS)

        # account + account-level (parent) association
        assert acct in {a.get("name", "") for a in slurm_client.get_accounts().get("accounts", [])}
        assocs = slurm_client.get_associations(account=acct, cluster=CLUSTER).get("associations", [])
        assert any(a.get("user") == "" for a in assocs), f"missing account-level parent: {assocs}"

        # user-level associations for every member
        for name in SYSTEM_USERS:
            assert any(a.get("account") == acct and a.get("user") == name for a in assocs), (
                f"missing user-level assoc for {name}: {assocs}"
            )

        # DB bookkeeping: a SlurmUser row per member with the allocation account as default
        su_rows = {su.user.username: su for su in SlurmUser.objects.filter(cluster=cluster)}
        assert set(su_rows) == set(SYSTEM_USERS), f"missing SlurmUser rows: {set(su_rows) ^ set(SYSTEM_USERS)}"
        for su in su_rows.values():
            assert su.default_account == account, f"{su.user.username} default account wrong"

        # Live default accounts land in slurmdbd
        defaults = _live_default_accounts(slurm_stack)
        for name in SYSTEM_USERS:
            assert defaults.get(name) == acct, f"live default account for {name}: {defaults.get(name)!r}"

        # A synced member can submit and run a real job against the allocation account
        job_id = submit_sleep_job(slurm_stack, acct, username="csimmons")
        wait_for_job_completion(slurm_stack, job_id)

    def test_project_allocation_rerun_idempotent(self, slurm_stack, slurm_client):
        """Re-running activation is silent-success / present-counts-as-success."""
        cluster, account, allocation, _, users = _seed_project_with_allocation(slurm_client)
        acct = account.name
        first = sync_slurm_clusters([CLUSTER])[0]
        _assert_sync_success(first)
        second = sync_slurm_clusters([CLUSTER])[0]
        _assert_sync_success(second)

        assert acct in {a.get("name", "") for a in slurm_client.get_accounts().get("accounts", [])}
