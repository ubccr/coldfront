# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Live Slurm sync e2e tests.

Drives the real batch sync engine (``sync_slurm_clusters``) against the live
stack via Django DB seeding (``pytest.mark.django_db``) + ``slurm_settings``.

These lock in the refactored batch-only sync behavior discovered against live:

* ``POST /config`` is upsert-only on the live stack (it does **not** create),
  so creates go through the entity endpoints — accounts + account-level
  parents via ``accounts_association`` add_cond, then user records, then the
  user-level associations — in dependency order.
* The account-level (parent) association is **always** created (it is the
  hierarchy root); GrpTresMins (SU grant) is folded in only when
  ``enforce_su_limits`` is on.
* TRES limits are sent as ``tres_list`` arrays (dict form -> ``9208 Data
  parser expected a list``); verified stored via ``sacctmgr``.
* Re-runs are idempotent: re-creating an account /
  association is silent success and present-counts-as-success.
* Full sync is a superset reconciliation: it creates the desired entities,
  then sweeps orphaned associations/users/accounts/QOS that ColdFront no
  longer expects.
"""

import uuid

import pytest
from django.contrib.auth import get_user_model

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.models import Allocation, Project, ProjectUser
from coldfront.slurm.models import SlurmAccount, SlurmAssociation, SlurmCluster, SlurmQOS
from coldfront.slurm.sync import sync_slurm_clusters

# Cluster name defined in the vendored slurm.conf (ClusterName=linux).
CLUSTER = "linux"

User = get_user_model()


def _uniq(prefix: str) -> str:
    """Unique name for this run, so tests never collide on the shared stack."""
    return f"e2e-{prefix}-{uuid.uuid4().hex[:10]}"


def _seed(slurm_stack, *, enforce_su_limits: bool = False, service_units: int | None = None):
    """Seed the Django models a sync pass operates on.

    Creates a Django User (whose username becomes a real OS account in the
    containers), an active Allocation on the live cluster, its SlurmAccount
    and SlurmAssociation. Returns the objects plus the live entity names.

    The Django rows roll back at test teardown (pytest-django); the live
    Slurm entities are removed by the autouse ``slurm_cleanup``.
    """
    user_name = _uniq("user")
    acct_name = _uniq("acct")

    user = User.objects.create(username=user_name, is_active=True)
    cluster_obj = SlurmCluster.objects.create(
        name=CLUSTER,
        description="e2e sync",
        enforce_su_limits=enforce_su_limits,
    )
    project = Project.objects.create(name=_uniq("proj"), owner=user)
    ProjectUser.objects.create(project=project, user=user)
    allocation = Allocation.objects.create(
        project=project,
        resource_object=cluster_obj,
        owner=user,
        status=AllocationStatusChoices.STATUS_ACTIVE,
        description="e2e sync",
    )
    account = SlurmAccount.objects.create(
        name=acct_name,
        cluster=cluster_obj,
        description="e2e sync",
        service_units=service_units,
    )
    association = SlurmAssociation.objects.create(
        allocation=allocation,
        slurm_account=account,
        fairshare=1,
    )

    # slurmdbd resolves the user's uid against /etc/passwd — create the OS
    # account so user records/assocs actually materialize.
    slurm_stack.ensure_system_user(user_name)

    return cluster_obj, allocation, account, association, user


def _assert_sync_success(report) -> None:
    """A sync report must carry no errors."""
    assert report.errors == [], f"sync errors: {report.errors}"
    assert report.success, f"sync failed: {report.errors}"


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.usefixtures("slurm_settings")
class TestSyncLive:
    """Drive the real batch sync engine against the live stack."""

    def test_full_sync_materializes_hierarchy(self, slurm_stack, slurm_client):
        """sync_slurm_clusters creates account + parent + user + user assoc."""
        cluster_obj, allocation, account, _, user = _seed(slurm_stack)
        acct, uname = account.name, user.username

        report = sync_slurm_clusters([CLUSTER])[0]
        _assert_sync_success(report)
        assert report.accounts_created >= 1

        # account + account-level parent
        assert acct in {a.get("name", "") for a in slurm_client.get_accounts().get("accounts", [])}
        assocs = slurm_client.get_associations(account=acct, cluster=CLUSTER).get("associations", [])
        assert any(a.get("user") == "" for a in assocs), f"missing account-level parent: {assocs}"
        # user record + user-level assoc
        assert uname in {u.get("name", "") for u in slurm_client.get_users().get("users", [])}
        assert any(a.get("account") == acct and a.get("user") == uname for a in assocs), (
            f"missing user-level assoc: {assocs}"
        )

    def test_full_sync_rerun_idempotent(self, slurm_stack, slurm_client):
        """Re-running the full sync is silent-success / present-counts-as-success."""
        cluster_obj, allocation, account, _, user = _seed(slurm_stack)
        acct = account.name

        first = sync_slurm_clusters([CLUSTER])[0]
        _assert_sync_success(first)
        second = sync_slurm_clusters([CLUSTER])[0]
        _assert_sync_success(second)

        assert acct in {a.get("name", "") for a in slurm_client.get_accounts().get("accounts", [])}

    def test_full_sync_creates_hierarchy_and_carries_qos(self, slurm_stack, slurm_client):
        """sync_slurm_clusters creates the hierarchy, upserts QOS defs, and the
        created user assoc carries the linked QOS."""
        cluster_obj, allocation, account, association, user = _seed(slurm_stack)
        acct, uname = account.name, user.username
        qos_name = _uniq("qos")
        unlinked_qos = _uniq("unlinked")

        # Two QOS records: one linked to the association, one unreferenced —
        # the full sync upserts every SlurmQOS definition regardless of use.
        qos_obj = SlurmQOS.objects.create(
            name=qos_name,
            priority=10,
            max_submit_jobs_per_user=5,
            max_jobs_per_user=3,
        )
        SlurmQOS.objects.create(name=unlinked_qos)
        association.qos_add.add(qos_obj)

        report = sync_slurm_clusters([CLUSTER])[0]
        _assert_sync_success(report)
        assert report.accounts_created >= 1
        assert report.associations_created >= 1
        assert report.qos_synced >= 1

        # desired hierarchy materialized (account parent + user assoc)
        assocs = slurm_client.get_associations(cluster=CLUSTER).get("associations", [])
        assert any(a.get("account") == acct and a.get("user") == "" for a in assocs)
        assert any(a.get("account") == acct and a.get("user") == uname for a in assocs)

        # linked QOS definition upserted live, limits included
        got = slurm_client.get_qos(name=qos_name)
        q = next((x for x in got.get("qos", []) if x.get("name") == qos_name), None)
        assert q is not None, f"qos not found: {got}"
        assert q["priority"]["number"] == 10
        assert q["limits"]["max"]["jobs"]["per"]["user"]["number"] == 5
        assert q["limits"]["max"]["jobs"]["active_jobs"]["per"]["user"]["number"] == 3

        # unreferenced QOS definition also upserted live
        got = slurm_client.get_qos(name=unlinked_qos)
        assert any(x.get("name") == unlinked_qos for x in got.get("qos", []))

        # the created user assoc carries the linked QOS under ``qos``
        user_assoc = next((a for a in assocs if a.get("account") == acct and a.get("user") == uname), None)
        assert user_assoc is not None
        assert qos_name in user_assoc.get("qos", []), f"qos not on assoc: {user_assoc}"

    def test_full_sync_deletes_orphans_keeps_parents(self, slurm_stack, slurm_client):
        """sync_slurm_clusters deletes orphaned user assocs but keeps parents."""
        cluster_obj, allocation, account, _, user = _seed(slurm_stack)
        stray_acct = _uniq("stray")

        # Seed a stray live account+parent+user that is NOT in the Django DB.
        slurm_client.create_accounts_with_associations(
            slurm_client.serialize_accounts_add_cond(accounts=[stray_acct], clusters=[CLUSTER])
        )
        slurm_stack.ensure_system_user("cgray")
        slurm_client.create_users([{"name": "cgray", "default": {"account": stray_acct, "wckey": ""}}])
        slurm_client.create_associations([{"account": stray_acct, "user": "cgray", "cluster": CLUSTER}])

        report = sync_slurm_clusters([CLUSTER])[0]
        _assert_sync_success(report)

        assocs = slurm_client.get_associations(cluster=CLUSTER).get("associations", [])
        # the stray user assoc was orphaned -> deleted; its account-level parent kept
        assert not any(a.get("account") == stray_acct and a.get("user") == "cgray" for a in assocs)
        assert any(a.get("account") == stray_acct and a.get("user") == "" for a in assocs)

    def test_deactivate_allocation_removes_assocs(self, slurm_stack, slurm_client):
        """A revoked allocation's assoc is orphaned and removed by the sweep."""
        cluster_obj, allocation, account, _, user = _seed(slurm_stack)
        acct, uname = account.name, user.username

        sync_slurm_clusters([CLUSTER])

        # flip to revoked; the full sync only keeps active allocations' assocs
        allocation.status = AllocationStatusChoices.STATUS_REVOKED
        allocation.save()
        report = sync_slurm_clusters([CLUSTER])[0]
        _assert_sync_success(report)
        assert report.associations_deleted >= 1

        assocs = slurm_client.get_associations(account=acct, cluster=CLUSTER).get("associations", [])
        assert not any(a.get("user") == uname for a in assocs)

    def test_remove_project_user_removes_assoc(self, slurm_stack, slurm_client):
        """Removing a project user orphans their user assoc, swept by full sync."""
        cluster_obj, allocation, account, _, user = _seed(slurm_stack)
        acct, uname = account.name, user.username

        sync_slurm_clusters([CLUSTER])

        # Remove the project user; the DB-only listener drops the SlurmUser
        # record, and the full sync no longer expects their assoc.
        ProjectUser.objects.filter(project=allocation.project, user=user).delete()
        report = sync_slurm_clusters([CLUSTER])[0]
        _assert_sync_success(report)
        assert report.associations_deleted >= 1

        assocs = slurm_client.get_associations(account=acct, cluster=CLUSTER).get("associations", [])
        assert not any(a.get("user") == uname for a in assocs)


@pytest.mark.django_db
@pytest.mark.e2e
@pytest.mark.usefixtures("slurm_settings")
class TestQosSyncLive:
    """Drive the orphan-QOS sweep of the full sync against the live stack.

    QOS-definition upsert is exercised by the general full-sync tests
    (:class:`TestSyncLive`); this class covers the deletion path.
    """

    def test_orphan_qos_removed_by_full_sync(self, slurm_stack, slurm_client):
        """A QOS present live but not in ColdFront is deleted by the sweep."""
        cluster_obj, allocation, account, _, user = _seed(slurm_stack)
        orphan_qos = _uniq("orphan")

        # Create a live QOS that ColdFront does not track.
        slurm_client.upsert_qos([{"name": orphan_qos}])
        assert any(x.get("name") == orphan_qos for x in slurm_client.get_qos().get("qos", []))

        report = sync_slurm_clusters([CLUSTER])[0]
        _assert_sync_success(report)
        assert report.qos_deleted >= 1

        # Fresh QOS records are hard-deleted: hidden even with with_deleted.
        got = slurm_client.get_qos(name=orphan_qos)
        assert not any(x.get("name") == orphan_qos for x in got.get("qos", []))
        got = slurm_client.get_qos(name=orphan_qos, with_deleted=True)
        assert not any(x.get("name") == orphan_qos for x in got.get("qos", []))
