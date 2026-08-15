# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.storage.forms import StorageResourceForm
from coldfront.storage.models import (
    StorageCluster,
    StorageQuota,
    StorageResource,
    StorageSnapshotPolicy,
)
from coldfront.utils.testing import ViewTestCases, create_tags

DEFAULT_PATH_TEMPLATE = "/home/groups/{project.slug}/{allocation.id}"


class StorageResourceTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = StorageResource

    @classmethod
    def setUpTestData(cls):

        clusters = (
            StorageCluster(name="Cluster 1"),
            StorageCluster(name="Cluster 2"),
            StorageCluster(name="Cluster 3"),
        )
        for cluster in clusters:
            cluster.save()

        resources = (
            StorageResource(name="Resource 1"),
            StorageResource(name="Resource 2"),
            StorageResource(name="Resource 3"),
        )
        for resource in resources:
            resource.save()
        resources[0].clusters.add(clusters[0])
        resources[1].clusters.add(clusters[0], clusters[1])
        resources[2].clusters.add(clusters[0], clusters[1], clusters[2])

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "name": "Resource X",
            "description": "A new storage resource",
            "locked": False,
            "clusters": [clusters[0].pk, clusters[1].pk],
            "path_template": "/home/groups/{project.slug}/{allocation.id}",
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "name,description,path_template",
            f"Resource 4,Fourth resource,{DEFAULT_PATH_TEMPLATE}",
            f"Resource 5,Fifth resource,{DEFAULT_PATH_TEMPLATE}",
            f"Resource 6,Sixth resource,{DEFAULT_PATH_TEMPLATE}",
        )

        cls.csv_update_data = (
            "id,name,description,path_template",
            f"{resources[0].pk},Resource 7,Seven resource,{DEFAULT_PATH_TEMPLATE}",
            f"{resources[1].pk},Resource 8,Eight resource,{DEFAULT_PATH_TEMPLATE}",
            f"{resources[2].pk},Resource 9,Nine resource,{DEFAULT_PATH_TEMPLATE}",
        )

        cls.bulk_edit_form_data = {
            "description": "Updated resource",
            "locked": True,
        }

    def test_capacity_bytes_accepts_human_readable(self):
        form = StorageResourceForm(
            data={
                "name": "New Storage Resource",
                "clusters": [StorageCluster.objects.first().pk],
                "tenant": None,
                "path_template": "/mnt",
                "capacity_bytes": "10 TB",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_capacity_bytes_accepts_plain_integer_string(self):
        form = StorageResourceForm(
            data={
                "name": "New Storage Resource",
                "clusters": [StorageCluster.objects.first().pk],
                "tenant": None,
                "path_template": "/mnt",
                "capacity_bytes": "100000000000000000",
            }
        )
        self.assertTrue(form.is_valid())
        self.assertTrue(form.save())

    def test_capacity_bytes_invalid(self):
        form = StorageResourceForm(
            data={
                "name": "New Storage Resource",
                "clusters": [StorageCluster.objects.first().pk],
                "tenant": None,
                "path_template": "/mnt",
                "capacity_bytes": "asdfasdfaasdf",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("capacity_bytes", form.errors)


class StorageClusterTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = StorageCluster

    @classmethod
    def setUpTestData(cls):

        clusters = (
            StorageCluster(name="Cluster 1"),
            StorageCluster(name="Cluster 2"),
            StorageCluster(name="Cluster 3"),
        )
        for cluster in clusters:
            cluster.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "name": "Cluster X",
            "description": "A new storage cluster",
            "backend_path": "coldfront.storage.backends.dummy.DummyBackend",
            "auto_sync_enabled": True,
            "sync_interval": 1440,
            "capacity_bytes": None,
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "name,description,backend_path,sync_interval",
            "Cluster 4,Fourth cluster,coldfront.storage.backends.dummy.DummyBackend,1440",
            "Cluster 5,Fifth cluster,coldfront.storage.backends.dummy.DummyBackend,1440",
            "Cluster 6,Sixth cluster,coldfront.storage.backends.dummy.DummyBackend,1440",
        )

        cls.csv_update_data = (
            "id,name,description,backend_path,sync_interval",
            f"{clusters[0].pk},Cluster 7,Seven cluster,coldfront.storage.backends.dummy.DummyBackend,1440",
            f"{clusters[1].pk},Cluster 8,Eight cluster,coldfront.storage.backends.dummy.DummyBackend,1440",
            f"{clusters[2].pk},Cluster 9,Nine cluster,coldfront.storage.backends.dummy.DummyBackend,1440",
        )

        cls.bulk_edit_form_data = {
            "description": "Updated cluster",
            "auto_sync_enabled": True,
        }


class StorageSnapshotPolicyTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = StorageSnapshotPolicy

    @classmethod
    def setUpTestData(cls):

        cluster = StorageCluster.objects.create(name="Test Cluster")

        policies = (
            StorageSnapshotPolicy(name="Policy 1", cluster=cluster, interval="daily", retention_days=7),
            StorageSnapshotPolicy(name="Policy 2", cluster=cluster, interval="weekly", retention_days=14),
            StorageSnapshotPolicy(name="Policy 3", cluster=cluster, interval="monthly", retention_days=30),
        )
        for policy in policies:
            policy.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "cluster": cluster.pk,
            "name": "Policy X",
            "description": "A new snapshot policy",
            "interval": "daily",
            "retention_days": 7,
            "extra_config": "{}",
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "cluster,name,description,interval,retention_days",
            "Test Cluster,Policy 4,Fourth policy,daily,7",
            "Test Cluster,Policy 5,Fifth policy,weekly,14",
            "Test Cluster,Policy 6,Sixth policy,monthly,30",
        )

        cls.csv_update_data = (
            "id,cluster,name,description,interval,retention_days",
            f"{policies[0].pk},Test Cluster,Policy 7,Seven policy,daily,7",
            f"{policies[1].pk},Test Cluster,Policy 8,Eight policy,weekly,14",
            f"{policies[2].pk},Test Cluster,Policy 9,Nine policy,monthly,30",
        )

        cls.bulk_edit_form_data = {
            "description": "Updated policy",
            "retention_days": 90,
        }


class StorageQuotaTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = StorageQuota

    @classmethod
    def setUpTestData(cls):

        cluster = StorageCluster.objects.create(name="Test Cluster")
        resource = StorageResource.objects.create(name="Test Resource")
        resource.clusters.add(cluster)

        from coldfront.ras.models import Allocation, Project
        from coldfront.users.models import Group, User

        owner = User.objects.create(username="storage-owner")
        owning_user = User.objects.create(username="storage-quota-owner")
        owning_group = Group.objects.create(name="testgroup")

        # Create users and groups for CSV import tests
        for suffix in ["4", "5", "6", "7", "8", "9"]:
            User.objects.create(username=f"testuser{suffix}")
            Group.objects.create(name=f"testgroup{suffix}")
        project = Project.objects.create(name="Test Project", slug="test-project", owner=owner)
        allocations = tuple(
            Allocation.objects.create(
                resource_object=resource,
                project=project,
                owner=owner,
            )
            for _ in range(6)
        )

        quotas = (
            StorageQuota(
                allocation=allocations[0],
                storage=resource,
                path="/test/1",
                owning_user=owning_user,
                owning_group=owning_group,
            ),
            StorageQuota(
                allocation=allocations[1],
                storage=resource,
                path="/test/2",
                owning_user=owning_user,
                owning_group=owning_group,
            ),
            StorageQuota(
                allocation=allocations[2],
                storage=resource,
                path="/test/3",
                owning_user=owning_user,
                owning_group=owning_group,
            ),
        )
        for quota in quotas:
            quota.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "allocation": allocations[3].pk,
            "storage": resource.pk,
            "clusters": [cluster.pk],
            "path": "/test/quota-x",
            "owning_user": owning_user.pk,
            "owning_group": owning_group.pk,
            "path_mode": 2770,
            "hard_limit_bytes": 1073741824,  # 1 GB
            "soft_limit_bytes": None,
            "hard_limit_files": None,
            "soft_limit_files": None,
            "grace_period": None,
            "share_type": "posix",
            "snapshot_policy": None,
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "allocation,storage,path,owning_user,owning_group,path_mode,hard_limit_bytes,share_type",
            f"{allocations[3].pk},Test Resource,/test/4,testuser4,testgroup4,2770,1073741824,posix",
            f"{allocations[4].pk},Test Resource,/test/5,testuser5,testgroup5,2770,1073741824,posix",
            f"{allocations[5].pk},Test Resource,/test/6,testuser6,testgroup6,2770,1073741824,posix",
        )

        cls.csv_update_data = (
            "id,allocation,storage,path,owning_user,owning_group,path_mode,hard_limit_bytes,share_type",
            f"{quotas[0].pk},{allocations[0].pk},Test Resource,/test/7,testuser7,testgroup7,2770,1073741824,posix",
            f"{quotas[1].pk},{allocations[1].pk},Test Resource,/test/8,testuser8,testgroup8,2770,1073741824,posix",
            f"{quotas[2].pk},{allocations[2].pk},Test Resource,/test/9,testuser9,testgroup9,2770,1073741824,posix",
        )

        cls.bulk_edit_form_data = {
            "path_mode": 2775,
            "share_type": "nfs",
        }

    def test_bulk_update_objects_with_permission(self):
        # Grant view permissions for User and Group so CSV import can look them up by username
        self.add_permissions("users.view_user", "users.view_group")
        super().test_bulk_update_objects_with_permission()

    validation_excluded_fields = ("clusters",)
