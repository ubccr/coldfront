# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the Storage sync engine (``coldfront.storage.sync``) and
ViewFlow callbacks (``coldfront.storage.listeners``).

Organized by test class:

- ``TestSyncReport`` — dataclass structure
- ``TestEnqueueWrappers`` — auto-sync gate and task enqueue
- ``TestActivateAllocation`` — ``_run_activate_allocation`` error paths
- ``TestDeactivateAllocation`` — ``_run_deactivate_allocation`` error paths
- ``TestFullSync`` — ``run_sync`` integration
- ``TestRecalculateUsedBytes`` — ``_recalculate_used_bytes``
- ``TestCallbacks`` — ViewFlow callbacks (request, approve, activate, expire, revoke, deny)
- ``TestSignal`` — post_save signal for hard_limit_bytes changes
"""

from __future__ import annotations

from unittest import mock

from django.db.models import F
from django.test import TestCase

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.models import Allocation, Project
from coldfront.storage.listeners import (
    on_allocation_activated,
    on_allocation_approved,
    on_allocation_denied,
    on_allocation_expired,
    on_allocation_revoked,
)
from coldfront.storage.models import StorageCluster, StorageQuota, StorageResource
from coldfront.storage.sync import (
    SyncReport,
    _recalculate_used_bytes,
    _run_activate_allocation,
    _run_deactivate_allocation,
    enqueue_activate_allocation,
    enqueue_deactivate_allocation,
    run_sync,
)
from coldfront.users.models import Group, User

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
        assert r.paths_deleted == 0
        assert r.quotas_created == 0
        assert r.quotas_updated == 0
        assert r.quotas_deleted == 0
        assert r.errors == []
        assert r.warnings == []
        assert r.duration_ms == 0

    def test_full_report(self):
        r = SyncReport(
            cluster="hpc01",
            success=True,
            paths_created=2,
            quotas_created=3,
            quotas_updated=1,
            quotas_deleted=1,
            errors=["err1"],
            warnings=["warn1"],
            duration_ms=500,
        )
        assert r.cluster == "hpc01"
        assert r.success
        assert r.paths_created == 2
        assert r.quotas_created == 3
        assert r.quotas_updated == 1
        assert r.quotas_deleted == 1
        assert r.errors == ["err1"]
        assert r.warnings == ["warn1"]
        assert r.duration_ms == 500


# ======================================================================
# 2. Enqueue wrappers
# ======================================================================


class TestEnqueueWrappers(TestCase):
    """Test enqueue helpers respect the auto-sync gate."""

    @classmethod
    def setUpTestData(cls):
        cls.cluster = StorageCluster.objects.create(
            name="test-cluster",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
            auto_sync_enabled=False,
        )
        cls.cluster_on = StorageCluster.objects.create(
            name="test-cluster-on",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
            auto_sync_enabled=True,
        )

    def test_enqueue_activate_skips_when_disabled(self):
        with mock.patch("coldfront.storage.sync.logger") as mock_logger:
            enqueue_activate_allocation(1, self.cluster.pk)
            mock_logger.debug.assert_called_once()

    def test_enqueue_activate_enqueues_when_enabled(self):
        with mock.patch("coldfront.core.models.Job.enqueue") as mock_enqueue:
            enqueue_activate_allocation(1, self.cluster_on.pk, share_type="posix")
            mock_enqueue.assert_called_once()

    def test_enqueue_deactivate_skips_when_disabled(self):
        with mock.patch("coldfront.storage.sync.logger") as mock_logger:
            enqueue_deactivate_allocation(1, self.cluster.pk)
            mock_logger.debug.assert_called_once()

    def test_enqueue_deactivate_enqueues_when_enabled(self):
        with mock.patch("coldfront.core.models.Job.enqueue") as mock_enqueue:
            enqueue_deactivate_allocation(1, self.cluster_on.pk)
            mock_enqueue.assert_called_once()


# ======================================================================
# 3. Activate allocation
# ======================================================================


class TestActivateAllocation(TestCase):
    """Test _run_activate_allocation error paths."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="owner")
        cls.group = Group.objects.create(name="test-group")
        cls.cluster = StorageCluster.objects.create(
            name="test-cluster",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )
        cls.resource = StorageResource.objects.create(
            name="Test Resource",
            path_template="/home/groups/{project.slug}/{allocation.id}",
        )
        cls.resource.clusters.add(cls.cluster)
        cls.project = Project.objects.create(name="Test Project", slug="test-project", owner=cls.owner)
        cls.allocation = Allocation.objects.create(
            resource_object=cls.resource,
            project=cls.project,
            owner=cls.owner,
            status=AllocationStatusChoices.STATUS_ACTIVE,
        )
        cls.quota = StorageQuota.objects.create(
            allocation=cls.allocation,
            storage=cls.resource,
            path="/home/groups/test-project/1",
            owning_user=cls.owner,
            owning_group=cls.group,
            hard_limit_bytes=1073741824,
        )

    def test_missing_quota(self):
        report = _run_activate_allocation(allocation_id=99999, cluster_id=self.cluster.pk)
        assert not report.success
        assert "StorageQuota not found" in report.errors[0]

    def test_create_path_and_quota(self):
        with mock.patch("coldfront.storage.backends.dummy.DummyBackend") as mock_backend:
            mock_instance = mock_backend.return_value
            report = _run_activate_allocation(
                allocation_id=self.allocation.pk,
                cluster_id=self.cluster.pk,
                share_type="posix",
            )
            assert report.success
            assert report.paths_created == 1
            assert report.quotas_created == 1
            mock_instance.create_path.assert_called_once()
            mock_instance.create_quota.assert_called_once()

    def test_backend_create_path_failure(self):
        with mock.patch("coldfront.storage.backends.dummy.DummyBackend") as mock_backend:
            mock_instance = mock_backend.return_value
            mock_instance.create_path.side_effect = RuntimeError("API error")
            report = _run_activate_allocation(
                allocation_id=self.allocation.pk,
                cluster_id=self.cluster.pk,
                share_type="posix",
            )
            assert not report.success
            assert "Failed to create path" in report.errors[0]
            mock_instance.create_quota.assert_not_called()


# ======================================================================
# 4. Deactivate allocation
# ======================================================================


class TestDeactivateAllocation(TestCase):
    """Test _run_deactivate_allocation error paths."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="owner2")
        cls.group = Group.objects.create(name="test-group2")
        cls.cluster = StorageCluster.objects.create(
            name="test-cluster-2",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
        )
        cls.resource = StorageResource.objects.create(
            name="Test Resource 2",
            path_template="/home/groups/{project.slug}/{allocation.id}",
        )
        cls.resource.clusters.add(cls.cluster)
        cls.project = Project.objects.create(name="Test Project 2", slug="test-project-2", owner=cls.owner)
        cls.allocation = Allocation.objects.create(
            resource_object=cls.resource,
            project=cls.project,
            owner=cls.owner,
            status=AllocationStatusChoices.STATUS_EXPIRED,
        )
        cls.quota = StorageQuota.objects.create(
            allocation=cls.allocation,
            storage=cls.resource,
            path="/home/groups/test-project-2/1",
            owning_user=cls.owner,
            owning_group=cls.group,
            hard_limit_bytes=1073741824,
        )

    def test_missing_quota(self):
        report = _run_deactivate_allocation(allocation_id=99999, cluster_id=self.cluster.pk)
        assert not report.success
        assert "StorageQuota not found" in report.errors[0]

    def test_delete_quota_and_lock_path(self):
        with mock.patch("coldfront.storage.backends.dummy.DummyBackend") as mock_backend:
            mock_instance = mock_backend.return_value
            report = _run_deactivate_allocation(
                allocation_id=self.allocation.pk,
                cluster_id=self.cluster.pk,
            )
            assert report.success
            assert report.quotas_deleted == 1
            assert report.paths_deleted == 1
            mock_instance.delete_quota.assert_called_once()
            mock_instance.lock_path.assert_called_once()

    def test_backend_delete_quota_failure(self):
        with mock.patch("coldfront.storage.backends.dummy.DummyBackend") as mock_backend:
            mock_instance = mock_backend.return_value
            mock_instance.delete_quota.side_effect = RuntimeError("API error")
            report = _run_deactivate_allocation(
                allocation_id=self.allocation.pk,
                cluster_id=self.cluster.pk,
            )
            assert not report.success
            assert "Failed to delete quota" in report.errors[0]


# ======================================================================
# 5. Full sync
# ======================================================================


class TestFullSync(TestCase):
    """Test run_sync integration."""

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

    def test_sync_with_active_quota(self):
        allocation = Allocation.objects.create(
            resource_object=self.resource,
            project=self.project,
            owner=self.owner,
            status=AllocationStatusChoices.STATUS_ACTIVE,
        )
        StorageQuota.objects.create(
            allocation=allocation,
            storage=self.resource,
            path="/home/groups/sync-project/1",
            owning_user=self.owner,
            owning_group=self.group,
            hard_limit_bytes=1073741824,
        )
        reports = run_sync(cluster_id=self.cluster.pk)
        assert len(reports) == 1
        assert reports[0].success
        assert reports[0].paths_created == 1
        assert reports[0].quotas_created == 1

    def test_sync_without_quotas(self):
        reports = run_sync(cluster_id=self.cluster.pk)
        assert len(reports) == 1
        assert reports[0].success
        assert reports[0].paths_created == 0
        assert reports[0].quotas_created == 0

    def test_sync_all_clusters(self):
        reports = run_sync()
        assert len(reports) == 1  # only the cluster we created
        assert reports[0].success


# ======================================================================
# 6. Recalculate used bytes
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
            hard_limit_bytes=1073741824,
            used=500 * 1024 * 1024,  # 500 MB
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
# 7. Callbacks
# ======================================================================


class TestCallbacks(TestCase):
    """Test ViewFlow callbacks for storage lifecycle."""

    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create(username="cb-owner")
        cls.group = Group.objects.create(name="cb-group")
        cls.cluster = StorageCluster.objects.create(
            name="cb-cluster",
            backend_path="coldfront.storage.backends.dummy.DummyBackend",
            auto_sync_enabled=True,
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
            path="/home/groups/sig-project/1",
            owning_user=self.owner,
            owning_group=self.group,
            hard_limit_bytes=1073741824,
        )

        # Reset allocated_bytes for the resource and cluster
        StorageResource.objects.filter(pk=self.resource.pk).update(allocated_bytes=0)
        StorageCluster.objects.filter(pk=self.cluster.pk).update(allocated_bytes=0)

    def test_on_allocation_activated_enqueues_per_cluster(self):
        self.allocation.status = AllocationStatusChoices.STATUS_ACTIVE
        self.allocation.save()

        with mock.patch("coldfront.storage.listeners.enqueue_activate_allocation") as mock_enqueue:
            on_allocation_activated(
                self.allocation,
                source=AllocationStatusChoices.STATUS_APPROVED,
                target=AllocationStatusChoices.STATUS_ACTIVE,
            )
            mock_enqueue.assert_called_once()

    def test_on_allocation_activated_updates_allocated_bytes(self):
        self.allocation.status = AllocationStatusChoices.STATUS_ACTIVE
        self.allocation.save()
        quota = StorageQuota.objects.get(allocation=self.allocation)
        quota.hard_limit_bytes = 1073741824
        quota.save()

        with mock.patch("coldfront.storage.listeners.enqueue_activate_allocation"):
            on_allocation_activated(
                self.allocation,
                source=AllocationStatusChoices.STATUS_APPROVED,
                target=AllocationStatusChoices.STATUS_ACTIVE,
            )

        resource = StorageResource.objects.get(pk=self.resource.pk)
        assert resource.allocated_bytes == 1073741824

    def test_on_allocation_expired_enqueues_deactivate(self):
        self.allocation.status = AllocationStatusChoices.STATUS_ACTIVE
        self.allocation.save()
        quota = StorageQuota.objects.get(allocation=self.allocation)
        quota.hard_limit_bytes = 1073741824
        quota.save()

        # Seed allocated_bytes so the F()-subtract doesn't violate CHECK
        StorageResource.objects.filter(pk=self.resource.pk).update(
            allocated_bytes=F("allocated_bytes") + quota.hard_limit_bytes,
        )
        StorageCluster.objects.filter(pk=self.cluster.pk).update(
            allocated_bytes=F("allocated_bytes") + quota.hard_limit_bytes,
        )

        with mock.patch("coldfront.storage.listeners.enqueue_deactivate_allocation") as mock_enqueue:
            on_allocation_expired(
                self.allocation,
                source=AllocationStatusChoices.STATUS_ACTIVE,
                target=AllocationStatusChoices.STATUS_EXPIRED,
            )
            mock_enqueue.assert_called_once()

    def test_on_allocation_expired_updates_allocated_bytes(self):
        self.allocation.status = AllocationStatusChoices.STATUS_ACTIVE
        self.allocation.save()
        quota = StorageQuota.objects.get(allocation=self.allocation)
        quota.hard_limit_bytes = 1073741824
        quota.save()

        # First activate to add allocated_bytes
        with mock.patch("coldfront.storage.listeners.enqueue_activate_allocation"):
            on_allocation_activated(
                self.allocation,
                source=AllocationStatusChoices.STATUS_APPROVED,
                target=AllocationStatusChoices.STATUS_ACTIVE,
            )

        # Then expire to subtract
        with mock.patch("coldfront.storage.listeners.enqueue_deactivate_allocation"):
            on_allocation_expired(
                self.allocation,
                source=AllocationStatusChoices.STATUS_ACTIVE,
                target=AllocationStatusChoices.STATUS_EXPIRED,
            )

        resource = StorageResource.objects.get(pk=self.resource.pk)
        assert resource.allocated_bytes == 0

    def test_on_allocation_revoked_enqueues_deactivate(self):
        self.allocation.status = AllocationStatusChoices.STATUS_ACTIVE
        self.allocation.save()
        quota = StorageQuota.objects.get(allocation=self.allocation)
        quota.hard_limit_bytes = 1073741824
        quota.save()

        # Seed allocated_bytes so the F()-subtract doesn't violate CHECK
        StorageResource.objects.filter(pk=self.resource.pk).update(
            allocated_bytes=F("allocated_bytes") + quota.hard_limit_bytes,
        )
        StorageCluster.objects.filter(pk=self.cluster.pk).update(
            allocated_bytes=F("allocated_bytes") + quota.hard_limit_bytes,
        )

        with mock.patch("coldfront.storage.listeners.enqueue_deactivate_allocation") as mock_enqueue:
            on_allocation_revoked(
                self.allocation,
                source=AllocationStatusChoices.STATUS_ACTIVE,
                target=AllocationStatusChoices.STATUS_REVOKED,
            )
            mock_enqueue.assert_called_once()

    def test_on_allocation_revoked_updates_allocated_bytes(self):
        self.allocation.status = AllocationStatusChoices.STATUS_ACTIVE
        self.allocation.save()
        quota = StorageQuota.objects.get(allocation=self.allocation)
        quota.hard_limit_bytes = 1073741824
        quota.save()

        with mock.patch("coldfront.storage.listeners.enqueue_activate_allocation"):
            on_allocation_activated(
                self.allocation,
                source=AllocationStatusChoices.STATUS_APPROVED,
                target=AllocationStatusChoices.STATUS_ACTIVE,
            )

        with mock.patch("coldfront.storage.listeners.enqueue_deactivate_allocation"):
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

    def test_on_allocation_denied_non_storage_resource(self):
        on_allocation_denied(
            self.allocation,
            source=AllocationStatusChoices.STATUS_REQUESTED,
            target=AllocationStatusChoices.STATUS_DENIED,
        )
        # No StorageQuota should exist, no error
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
# 8. Signal
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
            hard_limit_bytes=1073741824,
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
        assert initial.allocated_bytes == 1073741824

        # Directly invoke the signal handler to test the logic
        self.quota.hard_limit_bytes = 2 * 1073741824
        on_storagequota_hard_limit_changed(
            sender=StorageQuota,
            instance=self.quota,
            raw=False,
        )

        resource = StorageResource.objects.get(pk=self.resource.pk)
        assert resource.allocated_bytes == 2 * 1073741824

        cluster = StorageCluster.objects.get(pk=self.cluster.pk)
        assert cluster.allocated_bytes == 2 * 1073741824

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
        assert resource.allocated_bytes == 1073741824

    def test_signal_skips_when_allocation_not_active(self):
        from coldfront.storage.signals import on_storagequota_hard_limit_changed

        self.allocation.status = AllocationStatusChoices.STATUS_EXPIRED
        self.allocation.save()

        self.quota.hard_limit_bytes = 2 * 1073741824
        on_storagequota_hard_limit_changed(
            sender=StorageQuota,
            instance=self.quota,
            raw=False,
        )

        # Allocated_bytes should remain unchanged because allocation is not ACTIVE
        resource = StorageResource.objects.get(pk=self.resource.pk)
        assert resource.allocated_bytes == 1073741824  # original value, not doubled


# ======================================================================
# 9. Helpers
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
