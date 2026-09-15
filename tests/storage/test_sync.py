# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the Storage sync engine (``coldfront.storage.sync``) and
ViewFlow callbacks (``coldfront.storage.listeners``).

Organized by test class:

- ``TestSyncReport`` — dataclass structure
- ``TestFullSync`` — ``sync_storage_clusters`` integration
- ``TestOrphanSweep`` — scoped orphan-quota sweep
- ``TestDryRun`` — engine dry-run mode
- ``TestUsageSync`` — ``sync_storage_usage`` (usage-only)
- ``TestSnapshotPolicies`` — snapshot policy reconciliation
- ``TestRecalculateUsedBytes`` — ``_recalculate_used_bytes``
- ``TestCallbacks`` — ViewFlow callbacks (approve, activate, expire, revoke, deny)
- ``TestSignal`` — post_save signal for hard_limit_bytes changes
- ``TestAutoGeneratePath`` — path template resolution
- ``TestManagedPrefixes`` — orphan-sweep scope derivation

Tests drive the real engine against a stateful ``DummyBackend`` seeded via
the ``backends`` test seam — no method-level monkeypatching.
"""

from __future__ import annotations

from django.db.models import F
from django.test import TestCase

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.models import Allocation, Project
from coldfront.storage.backends.dummy import DummyBackend
from coldfront.storage.listeners import (
    on_allocation_activated,
    on_allocation_approved,
    on_allocation_denied,
    on_allocation_expired,
    on_allocation_revoked,
)
from coldfront.storage.models import (
    StorageCluster,
    StorageQuota,
    StorageResource,
    StorageSnapshotPolicy,
)
from coldfront.storage.sync import (
    SyncReport,
    _managed_prefixes,
    _recalculate_used_bytes,
    sync_storage_clusters,
    sync_storage_quota,
    sync_storage_usage,
)
from coldfront.users.models import Group, User

DEFAULT_LIMIT = 1073741824
QUOTA_PATH = "/home/groups/sync-project/1"


def _seed_quota(backend, path, *, hard=DEFAULT_LIMIT, soft=None, files=None, soft_files=None):
    """Create a path + quota on a DummyBackend for ``path``."""
    backend.create_path(path, "sync-owner", "sync-group", 2770)
    backend.create_quota(
        path,
        "posix",
        hard,
        files,
        None,
        soft_limit_bytes=soft,
        soft_limit_files=soft_files,
    )


def _make_active_quota(resource, project, owner, group, *, path=QUOTA_PATH, hard=DEFAULT_LIMIT, soft=None):
    """Create an active StorageQuota row for the shared fixtures."""
    allocation = Allocation.objects.create(
        resource_object=resource,
        project=project,
        owner=owner,
        status=AllocationStatusChoices.STATUS_ACTIVE,
    )
    return StorageQuota.objects.create(
        allocation=allocation,
        storage=resource,
        path=path,
        owning_user=owner,
        owning_group=group,
        hard_limit_bytes=hard,
        soft_limit_bytes=soft,
    )


# ======================================================================
# 1. SyncReport
# ======================================================================


class TestSyncReport(TestCase):
    """Test SyncReport dataclass structure."""

    def test_defaults(self):
        r = SyncReport(cluster="test")
        assert r.cluster == "test"
        assert r.success is False
        assert r.paths_created == 0
        assert r.paths_locked == 0
        assert r.paths_unlocked == 0
        assert r.quotas_created == 0
        assert r.quotas_updated == 0
        assert r.quotas_deleted == 0
        assert r.usage_updated == 0
        assert r.errors == []
        assert r.warnings == []
        assert r.duration_ms == 0

    def test_full_report(self):
        r = SyncReport(
            cluster="hpc01",
            success=True,
            paths_created=2,
            paths_locked=1,
            paths_unlocked=1,
            quotas_created=3,
            quotas_updated=1,
            quotas_deleted=1,
            usage_updated=2,
            errors=["err1"],
            warnings=["warn1"],
            duration_ms=500,
        )
        assert r.cluster == "hpc01"
        assert r.success
        assert r.paths_created == 2
        assert r.paths_locked == 1
        assert r.paths_unlocked == 1
        assert r.quotas_created == 3
        assert r.quotas_updated == 1
        assert r.quotas_deleted == 1
        assert r.usage_updated == 2
        assert r.errors == ["err1"]
        assert r.warnings == ["warn1"]
        assert r.duration_ms == 500


# ======================================================================
# 2. Full sync
# ======================================================================


class TestFullSync(TestCase):
    """Test sync_storage_clusters integration."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="sync-owner")
        cls.group = Group.objects.create(name="sync-group")
        cls.cluster = StorageCluster.objects.create(
            name="sync-cluster",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )
        cls.resource = StorageResource.objects.create(
            name="Sync Resource",
            path_template="/home/groups/{project.slug}/{allocation.id}",
        )
        cls.resource.clusters.add(cls.cluster)
        cls.project = Project.objects.create(name="Sync Project", slug="sync-project", owner=cls.owner)

    def _sync(self, backend=None, dry_run=False):
        kwargs = {}
        if backend is not None:
            kwargs["backends"] = {self.cluster.name: backend}
        return sync_storage_clusters([self.cluster.name], dry_run=dry_run, **kwargs)

    def test_creates_missing_path_and_quota(self):
        _make_active_quota(self.resource, self.project, self.owner, self.group)
        backend = DummyBackend(self.cluster.name)
        reports = self._sync(backend)

        assert len(reports) == 1
        assert reports[0].success
        assert reports[0].paths_created == 1
        assert reports[0].quotas_created == 1

        stat = backend.stat_path(QUOTA_PATH)
        assert stat.owning_user == "sync-owner"
        assert stat.owning_group == "sync-group"
        assert stat.path_mode == 2770

        quota = backend.get_quota(QUOTA_PATH)
        assert quota.name == QUOTA_PATH
        assert quota.state == "OK"
        assert quota.hard_limit_bytes == DEFAULT_LIMIT

    def test_creates_via_registry_backend(self):
        # No injection — the backend resolves through the registry.
        _make_active_quota(self.resource, self.project, self.owner, self.group)
        reports = self._sync()
        assert len(reports) == 1
        assert reports[0].success
        assert reports[0].paths_created == 1
        assert reports[0].quotas_created == 1

    def test_updates_out_of_sync_limits(self):
        quota = _make_active_quota(
            self.resource,
            self.project,
            self.owner,
            self.group,
            soft=536870912,
        )
        backend = DummyBackend(self.cluster.name)
        _seed_quota(backend, QUOTA_PATH, hard=1)  # wrong hard limit, no soft
        reports = self._sync(backend)

        assert reports[0].quotas_updated == 1
        updated = backend.get_quota(QUOTA_PATH)
        assert updated.hard_limit_bytes == quota.hard_limit_bytes
        assert updated.soft_limit_bytes == quota.soft_limit_bytes

    def test_limits_match_skips_update(self):
        _make_active_quota(self.resource, self.project, self.owner, self.group)
        backend = DummyBackend(self.cluster.name)
        _seed_quota(backend, QUOTA_PATH)
        reports = self._sync(backend)
        assert reports[0].quotas_updated == 0

    def test_pulls_usage(self):
        quota = _make_active_quota(self.resource, self.project, self.owner, self.group)
        backend = DummyBackend(self.cluster.name, random_usage=False)
        _seed_quota(backend, QUOTA_PATH)
        backend.get_quota(QUOTA_PATH).used_bytes = 1000
        backend.get_quota(QUOTA_PATH).used_files = 10
        backend.get_quota(QUOTA_PATH).state = "OK"

        reports = self._sync(backend)
        assert reports[0].usage_updated == 1

        quota.refresh_from_db()
        assert quota.used_bytes == 1000
        assert quota.used_files == 10
        assert quota.state == "OK"

    def test_unlocks_reactivated_path(self):
        _make_active_quota(self.resource, self.project, self.owner, self.group)
        backend = DummyBackend(self.cluster.name)
        _seed_quota(backend, QUOTA_PATH)
        backend.lock_path(QUOTA_PATH)

        reports = self._sync(backend)
        assert reports[0].paths_unlocked == 1
        assert backend.stat_path(QUOTA_PATH).locked is False

    def test_no_backend_cluster_skipped(self):
        StorageCluster.objects.create(name="no-backend")  # backend_path None
        reports = sync_storage_clusters(["no-backend"])
        assert len(reports) == 1
        assert reports[0].success
        assert reports[0].paths_created == 0
        assert reports[0].quotas_created == 0

    def test_bad_backend_path_fails_report(self):
        StorageCluster.objects.create(name="bad-cluster", backend_path="coldfront.storage.backends.missing.Backend")
        reports = sync_storage_clusters(["bad-cluster"])
        assert len(reports) == 1
        assert not reports[0].success
        assert "Failed to instantiate backend" in reports[0].errors[0]

    def test_sync_all_clusters_and_filtering(self):
        _make_active_quota(self.resource, self.project, self.owner, self.group)
        other = StorageCluster.objects.create(name="other-cluster")
        self.resource.clusters.add(other)

        # All clusters
        reports = sync_storage_clusters()
        assert len(reports) == 2

        # Filtered by name
        reports = sync_storage_clusters(["other-cluster"])
        assert len(reports) == 1
        assert reports[0].cluster == "other-cluster"


# ======================================================================
# 3. DummyBackend bootstrap (first-use seeding)
# ======================================================================


class TestBootstrap(TestCase):
    """Test lazy first-use seeding of the DummyBackend shared cache."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="bootstrap-owner")
        cls.group = Group.objects.create(name="bootstrap-group")
        cls.cluster = StorageCluster.objects.create(
            name="bootstrap-cluster",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )
        cls.resource = StorageResource.objects.create(
            name="Bootstrap Resource",
            path_template="/home/groups/{project.slug}/{allocation.id}",
        )
        cls.resource.clusters.add(cls.cluster)
        cls.project = Project.objects.create(
            name="Bootstrap Project",
            slug="bootstrap-project",
            owner=cls.owner,
        )

    def test_first_use_seeds_cache(self):
        _make_active_quota(self.resource, self.project, self.owner, self.group)
        with self.settings(STORAGE_DUMMY_AUTO_SEED=True):
            backend = DummyBackend(self.cluster.name)

        quotas = backend.get_all_quotas()
        assert len(quotas) == 1
        assert quotas[0].path == QUOTA_PATH
        assert backend.stat_path(QUOTA_PATH) is not None

    def test_no_seed_when_disabled(self):
        # .env.testing sets STORAGE_DUMMY_AUTO_SEED=False.
        backend = DummyBackend(self.cluster.name)
        assert backend.get_all_quotas() == []

    def test_bootstraps_once_per_cluster(self):
        _make_active_quota(self.resource, self.project, self.owner, self.group)
        with self.settings(STORAGE_DUMMY_AUTO_SEED=True):
            DummyBackend(self.cluster.name)
            DummyBackend(self.cluster.name)
        # A later construction shares the already-seeded cache.
        assert len(DummyBackend(self.cluster.name).get_all_quotas()) == 1


# ======================================================================
# 4. Orphan sweep
# ======================================================================


class TestOrphanSweep(TestCase):
    """Test the scoped orphan-quota sweep."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="sweep-owner")
        cls.group = Group.objects.create(name="sweep-group")
        cls.cluster = StorageCluster.objects.create(
            name="sweep-cluster",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )
        cls.resource = StorageResource.objects.create(
            name="Sweep Resource",
            path_template="/home/groups/{project.slug}/{allocation.id}",
        )
        cls.resource.clusters.add(cls.cluster)
        cls.project = Project.objects.create(name="Sweep Project", slug="sweep-project", owner=cls.owner)

    def _sync(self, backend):
        return sync_storage_clusters([self.cluster.name], backends={self.cluster.name: backend})

    def test_expired_allocation_sweeps_quota_and_locks_path(self):
        quota = _make_active_quota(self.resource, self.project, self.owner, self.group)
        backend = DummyBackend(self.cluster.name)
        _seed_quota(backend, QUOTA_PATH)
        self._sync(backend)  # reconcile as active

        # Expire the allocation — next sync removes the quota and locks the path
        quota.allocation.status = AllocationStatusChoices.STATUS_EXPIRED
        quota.allocation.save()
        reports = self._sync(backend)

        assert reports[0].quotas_deleted == 1
        assert reports[0].paths_locked == 1
        with self.assertRaises(Exception):
            backend.get_quota(QUOTA_PATH)
        assert backend.stat_path(QUOTA_PATH).locked is True

    def test_sweep_spares_foreign_quota(self):
        # A quota outside every managed prefix (e.g. admin-created) is never touched
        _make_active_quota(self.resource, self.project, self.owner, self.group)
        backend = DummyBackend(self.cluster.name)
        _seed_quota(backend, QUOTA_PATH)
        backend.create_quota("/fs1/exists", "posix", 10000000000000, None, None)

        reports = self._sync(backend)
        assert reports[0].success
        assert reports[0].quotas_deleted == 0
        assert "/fs1/exists" in backend._quotas

    def test_sweep_spares_restricted_path(self):
        # A resource whose prefix overlaps a restricted path — quota preserved
        restricted = StorageResource.objects.create(
            name="Restricted Resource",
            path_template="/tmp{project.slug}",
        )
        restricted.clusters.add(self.cluster)

        backend = DummyBackend(self.cluster.name)
        backend.create_quota("/tmp", "posix", 1000, None, None)

        reports = self._sync(backend)
        assert reports[0].quotas_deleted == 0
        assert any("restricted" in w for w in reports[0].warnings)
        assert "/tmp" in backend._quotas

    def test_dynamic_template_out_of_scope(self):
        # A resource with no static prefix contributes nothing to the scope
        dynamic = StorageResource.objects.create(
            name="Dynamic Resource",
            path_template="{{ project.slug }}/{allocation.id}",
        )
        dynamic.clusters.add(self.cluster)

        backend = DummyBackend(self.cluster.name)
        backend.create_quota("/dynamic/1", "posix", 1000, None, None)

        reports = self._sync(backend)
        assert reports[0].quotas_deleted == 0
        assert any("static prefix" in w for w in reports[0].warnings)
        assert "/dynamic/1" in backend._quotas


# ======================================================================
# 4. Dry run
# ======================================================================


class TestDryRun(TestCase):
    """Test engine dry-run mode: records actions, makes no calls."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="dry-owner")
        cls.group = Group.objects.create(name="dry-group")
        cls.cluster = StorageCluster.objects.create(
            name="dry-cluster",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )
        cls.resource = StorageResource.objects.create(
            name="Dry Resource",
            path_template="/home/groups/{project.slug}/{allocation.id}",
        )
        cls.resource.clusters.add(cls.cluster)
        cls.project = Project.objects.create(name="Dry Project", slug="dry-project", owner=cls.owner)

    def test_dry_run_records_actions_without_mutating(self):
        # Active quota missing on backend
        _make_active_quota(self.resource, self.project, self.owner, self.group)
        # Active quota with differing limits
        other = _make_active_quota(
            self.resource,
            self.project,
            self.owner,
            self.group,
            path="/home/groups/dry-project/2",
        )
        # An orphan under the managed prefix
        orphan_path = "/home/groups/dry-project/3"

        backend = DummyBackend(self.cluster.name)
        _seed_quota(backend, other.path, hard=1)
        _seed_quota(backend, orphan_path)

        reports = sync_storage_clusters([self.cluster.name], dry_run=True, backends={self.cluster.name: backend})

        assert reports[0].success
        assert reports[0].paths_created == 1  # QUOTA_PATH
        assert reports[0].quotas_created == 1  # QUOTA_PATH
        assert reports[0].quotas_updated == 1  # other.path
        assert reports[0].quotas_deleted == 1  # orphan_path
        # No locks counted in dry run
        assert reports[0].paths_locked == 0

        # Backend unchanged
        with self.assertRaises(Exception):
            backend.get_quota(QUOTA_PATH)
        assert backend.get_quota(other.path).hard_limit_bytes == 1
        assert orphan_path in backend._quotas

        # A real run performs the recorded actions
        reports = sync_storage_clusters([self.cluster.name], backends={self.cluster.name: backend})
        assert reports[0].paths_created == 1
        assert reports[0].quotas_created == 1
        assert reports[0].quotas_updated == 1
        assert reports[0].quotas_deleted == 1
        assert reports[0].paths_locked == 1
        assert backend.get_quota(QUOTA_PATH).hard_limit_bytes == DEFAULT_LIMIT
        assert backend.get_quota(other.path).hard_limit_bytes == DEFAULT_LIMIT
        with self.assertRaises(Exception):
            backend.get_quota(orphan_path)


# ======================================================================
# 5. Usage-only sync
# ======================================================================


class TestUsageSync(TestCase):
    """Test sync_storage_usage — usage-only, no backend mutations."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="usage-owner")
        cls.group = Group.objects.create(name="usage-group")
        cls.cluster = StorageCluster.objects.create(
            name="usage-cluster",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )
        cls.resource = StorageResource.objects.create(
            name="Usage Resource",
            path_template="/home/groups/{project.slug}/{allocation.id}",
        )
        cls.resource.clusters.add(cls.cluster)
        cls.project = Project.objects.create(name="Usage Project", slug="usage-project", owner=cls.owner)

    def test_updates_usage_only(self):
        quota = _make_active_quota(self.resource, self.project, self.owner, self.group)
        backend = DummyBackend(self.cluster.name, random_usage=False)
        _seed_quota(backend, QUOTA_PATH, hard=1)  # deliberately out of sync
        backend.get_quota(QUOTA_PATH).used_bytes = 999
        backend.get_quota(QUOTA_PATH).used_files = 42

        reports = sync_storage_usage([self.cluster.name], backends={self.cluster.name: backend})

        assert reports[0].success
        assert reports[0].usage_updated == 1
        # Limits untouched — usage sync never mutates the backend
        assert backend.get_quota(QUOTA_PATH).hard_limit_bytes == 1

        quota.refresh_from_db()
        assert quota.used_bytes == 999
        assert quota.used_files == 42

    def test_ignores_inactive_rows(self):
        _make_active_quota(self.resource, self.project, self.owner, self.group, path="/home/groups/usage-project/1")
        inactive = Allocation.objects.create(
            resource_object=self.resource,
            project=self.project,
            owner=self.owner,
            status=AllocationStatusChoices.STATUS_EXPIRED,
        )
        StorageQuota.objects.create(
            allocation=inactive,
            storage=self.resource,
            path="/home/groups/usage-project/2",
        )

        backend = DummyBackend(self.cluster.name)
        _seed_quota(backend, "/home/groups/usage-project/1")
        _seed_quota(backend, "/home/groups/usage-project/2")

        reports = sync_storage_usage([self.cluster.name], backends={self.cluster.name: backend})
        assert reports[0].usage_updated == 1  # only the active row

    def test_recalculates_used_bytes(self):
        _make_active_quota(self.resource, self.project, self.owner, self.group)
        backend = DummyBackend(self.cluster.name)
        _seed_quota(backend, QUOTA_PATH)
        backend.get_quota(QUOTA_PATH).used_bytes = 500 * 1024 * 1024

        sync_storage_usage([self.cluster.name], backends={self.cluster.name: backend})
        assert StorageCluster.objects.get(pk=self.cluster.pk).used_bytes == 500 * 1024 * 1024
        assert StorageResource.objects.get(pk=self.resource.pk).used_bytes == 500 * 1024 * 1024

    def test_no_backend_cluster_skipped(self):
        StorageCluster.objects.create(name="usage-no-backend")
        reports = sync_storage_usage(["usage-no-backend"])
        assert len(reports) == 1
        assert reports[0].success
        assert reports[0].usage_updated == 0


# ======================================================================
# 6. Snapshot policies
# ======================================================================


class NoSnapshotBackend(DummyBackend):
    """A backend that does not support snapshot policies."""

    supports_snapshot_policies = False


class TestSnapshotPolicies(TestCase):
    """Test snapshot policy reconciliation in the full sync."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="snap-owner")
        cls.group = Group.objects.create(name="snap-group")
        cls.cluster = StorageCluster.objects.create(
            name="snap-cluster",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )
        cls.resource = StorageResource.objects.create(
            name="Snap Resource",
            path_template="/home/groups/{project.slug}/{allocation.id}",
        )
        cls.resource.clusters.add(cls.cluster)
        cls.project = Project.objects.create(name="Snap Project", slug="snap-project", owner=cls.owner)
        cls.policy = StorageSnapshotPolicy.objects.create(
            cluster=cls.cluster,
            name="daily-7d",
            interval="daily",
            retention_days=7,
        )

    def test_applied_on_create(self):
        quota = _make_active_quota(self.resource, self.project, self.owner, self.group)
        quota.snapshot_policy = self.policy
        quota.save()

        backend = DummyBackend(self.cluster.name)
        reports = sync_storage_clusters([self.cluster.name], backends={self.cluster.name: backend})

        assert reports[0].success
        assert reports[0].quotas_created == 1
        assert backend._snapshot_policies[QUOTA_PATH] == {
            "interval": "daily",
            "retention_days": 7,
            "extra_config": {},
        }

    def test_unsupported_backend_warns(self):
        quota = _make_active_quota(self.resource, self.project, self.owner, self.group)
        quota.snapshot_policy = self.policy
        quota.save()

        backend = NoSnapshotBackend(self.cluster.name)
        reports = sync_storage_clusters([self.cluster.name], backends={self.cluster.name: backend})

        assert reports[0].success
        assert reports[0].quotas_created == 1
        assert any("does not support snapshot policies" in w for w in reports[0].warnings)


# ======================================================================
# 7. Recalculate used bytes
# ======================================================================


class TestRecalculateUsedBytes(TestCase):
    """Test _recalculate_used_bytes updates resource/cluster sums."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="used-owner")
        cls.group = Group.objects.create(name="used-group")
        cls.cluster = StorageCluster.objects.create(
            name="used-cluster",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )
        cls.resource = StorageResource.objects.create(
            name="Used Resource",
            path_template="/home/groups/{project.slug}/{allocation.id}",
        )
        cls.resource.clusters.add(cls.cluster)
        cls.project = Project.objects.create(name="Used Project", slug="used-project", owner=cls.owner)
        cls.allocation = Allocation.objects.create(
            resource_object=cls.resource,
            project=cls.project,
            owner=cls.owner,
            status=AllocationStatusChoices.STATUS_ACTIVE,
        )
        cls.quota = StorageQuota.objects.create(
            allocation=cls.allocation,
            storage=cls.resource,
            path="/home/groups/used-project/1",
            owning_user=cls.owner,
            owning_group=cls.group,
            hard_limit_bytes=DEFAULT_LIMIT,
            used_bytes=500 * 1024 * 1024,  # 500 MB
        )

    def test_recalculate_resource(self):
        _recalculate_used_bytes()
        resource = StorageResource.objects.get(pk=self.resource.pk)
        assert resource.used_bytes == 500 * 1024 * 1024

    def test_recalculate_cluster(self):
        _recalculate_used_bytes()
        cluster = StorageCluster.objects.get(pk=self.cluster.pk)
        assert cluster.used_bytes == 500 * 1024 * 1024

    def test_recalculate_no_active_quotas(self):
        self.quota.allocation.status = AllocationStatusChoices.STATUS_EXPIRED
        self.quota.allocation.save()
        _recalculate_used_bytes()
        resource = StorageResource.objects.get(pk=self.resource.pk)
        cluster = StorageCluster.objects.get(pk=self.cluster.pk)
        assert resource.used_bytes == 0
        assert cluster.used_bytes == 0


# ======================================================================
# 8. Callbacks
# ======================================================================


class TestCallbacks(TestCase):
    """Test DB-only ViewFlow callbacks for storage lifecycle."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="cb-owner")
        cls.group = Group.objects.create(name="cb-group")
        cls.cluster = StorageCluster.objects.create(
            name="cb-cluster",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )
        cls.resource = StorageResource.objects.create(
            name="CB Resource",
            path_template="/home/groups/{project.slug}/{allocation.id}",
        )
        cls.resource.clusters.add(cls.cluster)

    def setUp(self):
        self.project = Project.objects.create(
            name="CB Project",
            slug="cb-project",
            owner=self.owner,
        )
        self.allocation = Allocation.objects.create(
            resource_object=self.resource,
            project=self.project,
            owner=self.owner,
            status=AllocationStatusChoices.STATUS_REQUESTED,
        )
        self.quota = StorageQuota.objects.create(
            allocation=self.allocation,
            storage=self.resource,
            path="/home/groups/cb-project/1",
            owning_user=self.owner,
            owning_group=self.group,
            hard_limit_bytes=DEFAULT_LIMIT,
        )

        # Reset allocated_bytes for the resource and cluster
        StorageResource.objects.filter(pk=self.resource.pk).update(allocated_bytes=0)
        StorageCluster.objects.filter(pk=self.cluster.pk).update(allocated_bytes=0)

    def test_on_allocation_activated_updates_allocated_bytes(self):
        self.allocation.status = AllocationStatusChoices.STATUS_ACTIVE
        self.allocation.save()

        on_allocation_activated(
            self.allocation,
            source=AllocationStatusChoices.STATUS_APPROVED,
            target=AllocationStatusChoices.STATUS_ACTIVE,
        )

        resource = StorageResource.objects.get(pk=self.resource.pk)
        assert resource.allocated_bytes == DEFAULT_LIMIT

    def test_on_allocation_expired_updates_allocated_bytes(self):
        self.allocation.status = AllocationStatusChoices.STATUS_ACTIVE
        self.allocation.save()

        on_allocation_activated(
            self.allocation,
            source=AllocationStatusChoices.STATUS_APPROVED,
            target=AllocationStatusChoices.STATUS_ACTIVE,
        )
        # Seed allocated_bytes so the F()-subtract doesn't violate CHECK
        StorageResource.objects.filter(pk=self.resource.pk).update(allocated_bytes=DEFAULT_LIMIT)
        StorageCluster.objects.filter(pk=self.cluster.pk).update(allocated_bytes=DEFAULT_LIMIT)

        on_allocation_expired(
            self.allocation,
            source=AllocationStatusChoices.STATUS_ACTIVE,
            target=AllocationStatusChoices.STATUS_EXPIRED,
        )

        resource = StorageResource.objects.get(pk=self.resource.pk)
        assert resource.allocated_bytes == 0

    def test_on_allocation_revoked_updates_allocated_bytes(self):
        self.allocation.status = AllocationStatusChoices.STATUS_ACTIVE
        self.allocation.save()

        on_allocation_activated(
            self.allocation,
            source=AllocationStatusChoices.STATUS_APPROVED,
            target=AllocationStatusChoices.STATUS_ACTIVE,
        )
        StorageResource.objects.filter(pk=self.resource.pk).update(allocated_bytes=DEFAULT_LIMIT)
        StorageCluster.objects.filter(pk=self.cluster.pk).update(allocated_bytes=DEFAULT_LIMIT)

        on_allocation_revoked(
            self.allocation,
            source=AllocationStatusChoices.STATUS_ACTIVE,
            target=AllocationStatusChoices.STATUS_REVOKED,
        )

        resource = StorageResource.objects.get(pk=self.resource.pk)
        assert resource.allocated_bytes == 0

    def test_on_allocation_denied_deletes_quota(self):
        assert StorageQuota.objects.filter(allocation=self.allocation).count() == 1

        on_allocation_denied(
            self.allocation,
            source=AllocationStatusChoices.STATUS_REQUESTED,
            target=AllocationStatusChoices.STATUS_DENIED,
        )
        assert StorageQuota.objects.filter(allocation=self.allocation).count() == 0

    def test_all_callbacks_skip_non_storage_resource(self):
        self.allocation.resource_object = self.cluster  # Not a StorageResource
        self.allocation.save()

        # None of these should raise or create objects
        on_allocation_approved(
            self.allocation,
            source=AllocationStatusChoices.STATUS_REQUESTED,
            target=AllocationStatusChoices.STATUS_APPROVED,
        )
        on_allocation_activated(
            self.allocation,
            source=AllocationStatusChoices.STATUS_APPROVED,
            target=AllocationStatusChoices.STATUS_ACTIVE,
        )
        on_allocation_expired(
            self.allocation, source=AllocationStatusChoices.STATUS_ACTIVE, target=AllocationStatusChoices.STATUS_EXPIRED
        )
        on_allocation_revoked(
            self.allocation, source=AllocationStatusChoices.STATUS_ACTIVE, target=AllocationStatusChoices.STATUS_REVOKED
        )
        on_allocation_denied(
            self.allocation,
            source=AllocationStatusChoices.STATUS_REQUESTED,
            target=AllocationStatusChoices.STATUS_DENIED,
        )


# ======================================================================
# 9. Signal
# ======================================================================


class TestSignal(TestCase):
    """Test post_save signal for hard_limit_bytes changes."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="sig-owner")
        cls.group = Group.objects.create(name="sig-group")
        cls.cluster = StorageCluster.objects.create(
            name="sig-cluster",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )
        cls.resource = StorageResource.objects.create(
            name="Sig Resource",
            path_template="/home/groups/{project.slug}/{allocation.id}",
        )
        cls.resource.clusters.add(cls.cluster)
        cls.project = Project.objects.create(name="Sig Project", slug="sig-project", owner=cls.owner)

    def setUp(self):
        self.allocation = Allocation.objects.create(
            resource_object=self.resource,
            project=self.project,
            owner=self.owner,
            status=AllocationStatusChoices.STATUS_ACTIVE,
        )
        self.quota = StorageQuota.objects.create(
            allocation=self.allocation,
            storage=self.resource,
            path="/home/groups/sig-project/1",
            owning_user=self.owner,
            owning_group=self.group,
            hard_limit_bytes=DEFAULT_LIMIT,
        )
        # Simulate what on_allocation_activated does: add hard_limit_bytes to allocated_bytes
        StorageResource.objects.filter(pk=self.resource.pk).update(
            allocated_bytes=F("allocated_bytes") + self.quota.hard_limit_bytes
        )
        StorageCluster.objects.filter(pk=self.cluster.pk).update(
            allocated_bytes=F("allocated_bytes") + self.quota.hard_limit_bytes
        )
        # Refresh instances
        self.resource.refresh_from_db()
        self.cluster.refresh_from_db()

    def test_hard_limit_increase_adjusts_allocated_bytes(self):
        from coldfront.storage.signals import on_storagequota_hard_limit_changed

        # Verify initial state
        initial = StorageResource.objects.get(pk=self.resource.pk)
        assert initial.allocated_bytes == DEFAULT_LIMIT

        # Directly invoke the signal handler to test the logic
        self.quota.hard_limit_bytes = 2 * DEFAULT_LIMIT
        on_storagequota_hard_limit_changed(
            sender=StorageQuota,
            instance=self.quota,
            raw=False,
        )

        resource = StorageResource.objects.get(pk=self.resource.pk)
        assert resource.allocated_bytes == 2 * DEFAULT_LIMIT

        cluster = StorageCluster.objects.get(pk=self.cluster.pk)
        assert cluster.allocated_bytes == 2 * DEFAULT_LIMIT

    def test_hard_limit_decrease_adjusts_allocated_bytes(self):
        from coldfront.storage.signals import on_storagequota_hard_limit_changed

        self.quota.hard_limit_bytes = 500 * 1024 * 1024  # 500 MB
        on_storagequota_hard_limit_changed(
            sender=StorageQuota,
            instance=self.quota,
            raw=False,
        )

        resource = StorageResource.objects.get(pk=self.resource.pk)
        assert resource.allocated_bytes == 500 * 1024 * 1024

    def test_hard_limit_no_change_skips_update(self):
        from coldfront.storage.signals import on_storagequota_hard_limit_changed

        # Re-save with same value — no delta
        self.quota.save(update_fields=["hard_limit_bytes"])  # noqa: B033
        on_storagequota_hard_limit_changed(
            sender=StorageQuota,
            instance=self.quota,
            raw=False,
        )
        # Re-fetch to avoid cached values
        resource = StorageResource.objects.get(pk=self.resource.pk)
        assert resource.allocated_bytes == DEFAULT_LIMIT

    def test_signal_skips_when_allocation_not_active(self):
        from coldfront.storage.signals import on_storagequota_hard_limit_changed

        self.allocation.status = AllocationStatusChoices.STATUS_EXPIRED
        self.allocation.save()

        self.quota.hard_limit_bytes = 2 * DEFAULT_LIMIT
        on_storagequota_hard_limit_changed(
            sender=StorageQuota,
            instance=self.quota,
            raw=False,
        )

        # Allocated_bytes should remain unchanged because allocation is not ACTIVE
        resource = StorageResource.objects.get(pk=self.resource.pk)
        assert resource.allocated_bytes == DEFAULT_LIMIT  # original value, not doubled


# ======================================================================
# 10. Helpers
# ======================================================================


class TestAutoGeneratePath(TestCase):
    """Test auto_generate_path template resolution."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="path-owner")
        cls.project = Project.objects.create(name="Path Project", slug="path-project", owner=cls.owner)
        cls.resource = StorageResource.objects.create(
            name="Path Resource",
            path_template="/home/groups/{{ allocation.project.slug }}/{{ allocation.id }}",
        )

    def setUp(self):
        self.allocation = Allocation.objects.create(
            resource_object=self.resource,
            project=self.project,
            owner=self.owner,
        )

    def test_default_template(self):
        path = self.resource.auto_generate_path(self.allocation)
        assert path == f"/home/groups/path-project/{self.allocation.pk}"

    def test_custom_template_with_resource_attr(self):
        self.resource.path_template = "{{ resource.name }}/{{ allocation.project.slug }}"
        self.resource.save()
        path = self.resource.auto_generate_path(self.allocation)
        assert path == "Path Resource/path-project"


class TestManagedPrefixes(TestCase):
    """Test _managed_prefixes scope derivation."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = StorageCluster.objects.create(name="prefix-cluster")
        cls.owner = User.objects.create(username="prefix-owner")

    def _prefixes(self):
        report = SyncReport(cluster=self.cluster.name)
        return _managed_prefixes(self.cluster, report), report.warnings

    def test_derives_static_prefixes(self):
        r1 = StorageResource.objects.create(
            name="R1",
            path_template="/home/groups/{project.slug}/{allocation.id}",
        )
        r1.clusters.add(self.cluster)
        r2 = StorageResource.objects.create(
            name="R2",
            path_template="/fs1/scratch/{{ allocation.project.slug }}",
        )
        r2.clusters.add(self.cluster)

        prefixes, _ = self._prefixes()
        assert "/home/groups/" in prefixes
        assert "/fs1/scratch/" in prefixes

    def test_skips_dynamic_templates(self):
        dynamic = StorageResource.objects.create(
            name="Dynamic",
            path_template="{{ project.slug }}/{allocation.id}",
        )
        dynamic.clusters.add(self.cluster)

        prefixes, warnings = self._prefixes()
        assert prefixes == []
        assert any("static prefix" in w for w in warnings)

    def test_unattached_resource_not_included(self):
        StorageResource.objects.create(
            name="Elsewhere",
            path_template="/fs2/data/{project.slug}",
        )  # no cluster link
        prefixes, _ = self._prefixes()
        assert prefixes == []


class TestSingleQuotaSync(TestCase):
    """Test the focused ``sync_storage_quota`` driver."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="single-owner")
        cls.group = Group.objects.create(name="single-group")
        cls.cluster = StorageCluster.objects.create(
            name="single-cluster",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )
        cls.resource = StorageResource.objects.create(
            name="Single Resource",
            path_template="/home/groups/{project.slug}/{allocation.id}",
        )
        cls.resource.clusters.add(cls.cluster)
        cls.project = Project.objects.create(name="Single Project", slug="single-project", owner=cls.owner)

    def test_sync_storage_quota_creates_on_backend(self):
        quota = _make_active_quota(self.resource, self.project, self.owner, self.group)
        backend = DummyBackend(self.cluster.name)
        reports = sync_storage_quota(quota, backends={self.cluster.name: backend})

        assert len(reports) == 1
        assert reports[0].cluster == self.cluster.name
        assert reports[0].paths_created == 1
        assert reports[0].quotas_created == 1
        assert backend.get_quota(QUOTA_PATH) is not None
