# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmQOS,
    SlurmUser,
)
from coldfront.users.models import User
from coldfront.utils.testing import APIViewTestCases, create_tags


class SlurmQOSAPITestCase(APIViewTestCases.APIViewTestCase):
    model = SlurmQOS
    brief_fields = ["description", "display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        qoss = (
            SlurmQOS(name="QOS 1"),
            SlurmQOS(name="QOS 2"),
            SlurmQOS(name="QOS 3"),
        )
        for qos in qoss:
            qos.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.create_data = [
            {
                "name": "QOS X",
                "description": "A new Slurm QOS",
                "tags": [t.pk for t in tags],
            },
        ]

        cls.update_data = {
            "name": "QOS Y",
            "description": "Updated description",
        }


class SlurmClusterAPITestCase(APIViewTestCases.APIViewTestCase):
    model = SlurmCluster
    brief_fields = ["description", "display", "id", "locked", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        clusters = (
            SlurmCluster(name="Cluster 1"),
            SlurmCluster(name="Cluster 2"),
            SlurmCluster(name="Cluster 3"),
        )
        for cluster in clusters:
            cluster.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.create_data = [
            {
                "name": "Cluster X",
                "description": "A new Slurm cluster",
                "locked": True,
                "tags": [t.pk for t in tags],
            },
        ]

        cls.update_data = {
            "name": "Cluster Y",
            "description": "Updated cluster",
            "locked": False,
        }


class SlurmPartitionAPITestCase(APIViewTestCases.APIViewTestCase):
    model = SlurmPartition
    brief_fields = [
        "description",
        "display",
        "id",
        "is_default",
        "locked",
        "name",
        "nodes",
        "priority",
        "slug",
        "state",
        "url",
    ]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        cluster = SlurmCluster.objects.create(name="Test Cluster")

        partitions = (
            SlurmPartition(name="Partition 1", cluster=cluster),
            SlurmPartition(name="Partition 2", cluster=cluster),
            SlurmPartition(name="Partition 3", cluster=cluster),
        )
        for partition in partitions:
            partition.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.create_data = [
            {
                "cluster": cluster.pk,
                "name": "Partition X",
                "description": "A new partition",
                "locked": True,
                "nodes": "node[01-64]",
                "priority": 100,
                "is_default": True,
                "state": "UP",
                "preempt_mode": "OFF",
                "def_mem_per_cpu": 2800,
                "tags": [t.pk for t in tags],
            },
        ]

        cls.update_data = {
            "name": "Partition Y",
            "slug": "test-cluster-partition-y",
            "description": "Updated partition",
            "locked": False,
            "nodes": "node[65-128]",
            "priority": 50,
            "is_default": False,
            "state": "DOWN",
            "preempt_mode": "REQUEUE",
            "def_mem_per_cpu": 4000,
        }


class SlurmAccountAPITestCase(APIViewTestCases.APIViewTestCase):
    model = SlurmAccount
    brief_fields = ["description", "display", "id", "name", "url"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):
        cluster = SlurmCluster.objects.create(name="Test Cluster")

        accounts = (
            SlurmAccount(name="Account 1", cluster=cluster),
            SlurmAccount(name="Account 2", cluster=cluster),
            SlurmAccount(name="Account 3", cluster=cluster),
        )
        for account in accounts:
            account.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.create_data = [
            {
                "cluster": cluster.pk,
                "name": "Account X",
                "description": "A new account",
                "tags": [t.pk for t in tags],
            },
        ]

        cls.update_data = {
            "name": "Account Y",
            "description": "Updated account",
        }


class SlurmAssociationAPITestCase(APIViewTestCases.APIViewTestCase):
    model = SlurmAssociation
    brief_fields = ["display", "fairshare", "id", "slurm_account", "url"]
    bulk_update_data = {
        "fairshare": 200,
    }

    @classmethod
    def setUpTestData(cls):
        cluster = SlurmCluster.objects.create(name="Test Cluster")
        account = SlurmAccount.objects.create(name="Test Account", cluster=cluster)
        qos1 = SlurmQOS.objects.create(name="high")
        qos2 = SlurmQOS.objects.create(name="normal")

        from django.contrib.contenttypes.models import ContentType

        from coldfront.ras.models import Allocation, Project, Resource, ResourceType
        from coldfront.users.models import User

        owner = User.objects.create(username="pi")
        project = Project.objects.create(name="Test Project", owner=owner)
        resource_type = ResourceType.objects.create(name="Cluster", slug="cluster")
        resource = Resource.objects.create(name="Test Resource", slug="test-resource", resource_type=resource_type)
        resource_ct = ContentType.objects.get_for_model(Resource)
        allocation1 = Allocation.objects.create(
            project=project,
            slug="TEST-001",
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
            owner=owner,
        )
        allocation2 = Allocation.objects.create(
            project=project,
            slug="TEST-002",
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
            owner=owner,
        )
        allocation3 = Allocation.objects.create(
            project=project,
            slug="TEST-003",
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
            owner=owner,
        )
        allocation4 = Allocation.objects.create(
            project=project,
            slug="TEST-004",
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
            owner=owner,
        )

        associations = (
            SlurmAssociation(allocation=allocation1, slurm_account=account),
            SlurmAssociation(allocation=allocation2, slurm_account=account),
            SlurmAssociation(allocation=allocation3, slurm_account=account),
        )
        for association in associations:
            association.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.create_data = [
            {
                "allocation": allocation4.pk,
                "slurm_account": account.pk,
                "fairshare": 1,
                "qos_add": [qos1.pk],
                "qos_remove": [qos2.pk],
                "tags": [t.pk for t in tags],
            },
        ]

        cls.update_data = {
            "fairshare": 2,
        }


class SlurmUserAPITestCase(APIViewTestCases.APIViewTestCase):
    model = SlurmUser
    brief_fields = ["admin_level", "cluster", "default_account", "display", "id", "url", "user"]
    bulk_update_data = {
        "admin_level": 1,
    }

    @classmethod
    def setUpTestData(cls):
        cluster = SlurmCluster.objects.create(name="Test Cluster")
        account = SlurmAccount.objects.create(name="Test Account", cluster=cluster)
        user1 = User.objects.create(username="user1")
        user2 = User.objects.create(username="user2")
        user3 = User.objects.create(username="user3")
        user4 = User.objects.create(username="user4")

        users = (
            SlurmUser(user=user1, cluster=cluster, default_account=account),
            SlurmUser(user=user2, cluster=cluster, default_account=account),
            SlurmUser(user=user3, cluster=cluster, default_account=account),
        )
        for user_obj in users:
            user_obj.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.create_data = [
            {
                "user": user4.pk,
                "cluster": cluster.pk,
                "default_account": account.pk,
                "admin_level": 0,
                "tags": [t.pk for t in tags],
            },
        ]

        cls.update_data = {
            "admin_level": 1,
        }
