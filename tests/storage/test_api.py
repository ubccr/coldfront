# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.storage.models import (
    StorageCluster,
    StorageQuota,
    StorageResource,
    StorageSnapshotPolicy,
)
from coldfront.utils.testing import APIViewTestCases, create_tags


class StorageSnapshotPolicyAPITestCase(APIViewTestCases.APIViewTestCase):
    model = StorageSnapshotPolicy
    brief_fields = ["description", "display", "id", "interval", "name", "retention_days", "url"]
    bulk_update_data = {
        "retention_days": 45,
    }

    @classmethod
    def setUpTestData(cls):
        cluster = StorageCluster.objects.create(name="Test Cluster")

        policies = (
            StorageSnapshotPolicy(cluster=cluster, name="Policy 1", interval="daily", retention_days=7),
            StorageSnapshotPolicy(cluster=cluster, name="Policy 2", interval="weekly", retention_days=14),
            StorageSnapshotPolicy(cluster=cluster, name="Policy 3", interval="monthly", retention_days=30),
        )
        for policy in policies:
            policy.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.create_data = [
            {
                "cluster": cluster.pk,
                "name": "Policy X",
                "description": "A new snapshot policy",
                "interval": "daily",
                "retention_days": 7,
                "extra_config": {},
                "tags": [t.pk for t in tags],
            },
        ]

        cls.update_data = {
            "name": "Policy Y",
            "description": "Updated policy",
            "retention_days": 30,
        }


class StorageClusterAPITestCase(APIViewTestCases.APIViewTestCase):
    model = StorageCluster
    brief_fields = ["backend_path", "capacity_bytes", "description", "display", "id", "name", "url"]
    bulk_update_data = {
        "backend_path": "coldfront.storage.backends.dummy.DummyBackend",
        "description": "New description",
    }

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

        cls.create_data = [
            {
                "name": "Cluster X",
                "description": "A new storage cluster",
                "backend_path": "coldfront.storage.backends.dummy.DummyBackend",
                "auto_sync_enabled": False,
                "sync_interval": 1440,
                "capacity_bytes": None,
                "tags": [t.pk for t in tags],
            },
        ]

        cls.update_data = {
            "name": "Cluster Y",
            "description": "Updated cluster",
            "backend_path": "coldfront.storage.backends.dummy.DummyBackend",
        }


class StorageResourceAPITestCase(APIViewTestCases.APIViewTestCase):
    model = StorageResource
    brief_fields = ["capacity_bytes", "description", "display", "id", "locked", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }

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

        cls.create_data = [
            {
                "name": "Resource X",
                "description": "A new storage resource",
                "locked": False,
                "clusters": [clusters[0].pk, clusters[1].pk],
                "path_template": "/home/groups/{project.slug}/{allocation.id}",
                "capacity_bytes": None,
                "tags": [t.pk for t in tags],
            },
        ]

        cls.update_data = {
            "name": "Resource Y",
            "description": "Updated resource",
            "locked": True,
        }


class StorageQuotaAPITestCase(APIViewTestCases.APIViewTestCase):
    model = StorageQuota
    brief_fields = ["allocation", "display", "hard_limit_bytes", "id", "path", "share_type", "storage", "url"]
    bulk_update_data = None  # Set in setUpTestData

    @classmethod
    def setUpTestData(cls):
        cluster = StorageCluster.objects.create(name="Test Cluster")
        resource = StorageResource.objects.create(name="Test Resource")
        resource.clusters.add(cluster)

        from coldfront.ras.models import Allocation, Project
        from coldfront.users.models import Group, User

        owner = User.objects.create(username="storage-api-owner")
        api_user = User.objects.create(username="apiuser")
        api_group = Group.objects.create(name="apigroup")
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
                owning_user=api_user,
                owning_group=api_group,
            ),
            StorageQuota(
                allocation=allocations[1],
                storage=resource,
                path="/test/2",
                owning_user=api_user,
                owning_group=api_group,
            ),
            StorageQuota(
                allocation=allocations[2],
                storage=resource,
                path="/test/3",
                owning_user=api_user,
                owning_group=api_group,
            ),
        )
        for quota in quotas:
            quota.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.create_data = [
            {
                "allocation": allocations[3].pk,
                "storage": resource.pk,
                "path": "/api/test/4",
                "owning_user": api_user.pk,
                "owning_group": api_group.pk,
                "path_mode": 2770,
                "hard_limit_bytes": 1073741824,
                "share_type": "posix",
                "tags": [t.pk for t in tags],
            },
        ]

        cls.update_data = {
            "hard_limit_bytes": 2147483648,
            "path": "/api/test/5",
            "owning_user": api_user.pk,
            "owning_group": api_group.pk,
        }

        cls.bulk_update_data = {
            "hard_limit_bytes": 2147483648,  # 2 GB
            "owning_user": api_user.pk,
            "owning_group": api_group.pk,
        }
