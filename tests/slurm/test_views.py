# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import timedelta

from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmQOS,
    SlurmUser,
)
from coldfront.users.models import User
from coldfront.utils.testing import ViewTestCases, create_tags


class SlurmQOSTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = SlurmQOS

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

        cls.form_data = {
            "name": "QOS X",
            "description": "A new Slurm QOS",
            "tags": [t.pk for t in tags],
        }

        cls.bulk_edit_form_data = {
            "description": "Updated QOS",
        }

        cls.csv_data = (
            "name,description",
            "QOS 4,Fourth QOS",
            "QOS 5,Fifth QOS",
            "QOS 6,Sixth QOS",
        )

        cls.csv_update_data = (
            "id,name,description",
            f"{qoss[0].pk},QOS 7,Seven QOS",
            f"{qoss[1].pk},QOS 8,Eight QOS",
            f"{qoss[2].pk},QOS 9,Nine QOS",
        )


class SlurmClusterTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = SlurmCluster

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

        cls.form_data = {
            "name": "Cluster X",
            "tenant_group": None,
            "tenant": None,
            "description": "A new Slurm cluster",
            "locked": True,
            "tags": [t.pk for t in tags],
        }

        cls.bulk_edit_form_data = {
            "description": "Updated cluster",
            "locked": True,
            "fairshare": 5,
        }

        cls.csv_data = (
            "name,description",
            "Cluster 4,Fourth cluster",
            "Cluster 5,Fifth cluster",
            "Cluster 6,Sixth cluster",
        )

        cls.csv_update_data = (
            "id,name,description",
            f"{clusters[0].pk},Cluster 7,Seven cluster",
            f"{clusters[1].pk},Cluster 8,Eight cluster",
            f"{clusters[2].pk},Cluster 9,Nine cluster",
        )


class SlurmPartitionTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = SlurmPartition

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

        cls.form_data = {
            "cluster": cluster.pk,
            "name": "Partition X",
            "description": "A new Slurm partition",
            "locked": True,
            "nodes": "node[01-64]",
            "priority": 100,
            "is_default": True,
            "default_time": timedelta(hours=1),
            "state": "UP",
            "preempt_mode": "OFF",
            "def_mem_per_cpu": 2800,
            "tags": [t.pk for t in tags],
        }

        cls.bulk_edit_form_data = {
            "description": "Updated partition",
            "locked": True,
            "priority": 200,
        }

        cls.csv_data = (
            "cluster,name,slug,description,nodes,priority,is_default,state",
            "Test Cluster,Partition 4,test-cluster-partition-4,Fourth partition,node[01-16],100,TRUE,UP",
            "Test Cluster,Partition 5,test-cluster-partition-5,Fifth partition,node[17-32],50,FALSE,UP",
            "Test Cluster,Partition 6,test-cluster-partition-6,Sixth partition,node[33-48],10,FALSE,DOWN",
        )

        cls.csv_update_data = (
            "id,cluster,name,slug,description,nodes,priority,is_default,state",
            f"{partitions[0].pk},Test Cluster,Partition 7,test-cluster-partition-7,Seven partition,node[49-64],100,TRUE,UP",
            f"{partitions[1].pk},Test Cluster,Partition 8,test-cluster-partition-8,Eight partition,node[65-80],50,FALSE,UP",
            f"{partitions[2].pk},Test Cluster,Partition 9,test-cluster-partition-9,Nine partition,node[81-96],10,FALSE,DOWN",
        )


class SlurmAccountTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = SlurmAccount

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

        cls.form_data = {
            "cluster": cluster.pk,
            "name": "Account X",
            "description": "A new Slurm account",
            "tags": [t.pk for t in tags],
        }

        cls.bulk_edit_form_data = {
            "description": "Updated account",
            "fairshare": 10,
        }

        cls.csv_data = (
            "cluster,name,description",
            "Test Cluster,Account 4,Fourth account",
            "Test Cluster,Account 5,Fifth account",
            "Test Cluster,Account 6,Sixth account",
        )

        cls.csv_update_data = (
            "id,cluster,name,description",
            f"{accounts[0].pk},Test Cluster,Account 7,Seven account",
            f"{accounts[1].pk},Test Cluster,Account 8,Eight account",
            f"{accounts[2].pk},Test Cluster,Account 9,Nine account",
        )


class SlurmAssociationTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = SlurmAssociation

    @classmethod
    def setUpTestData(cls):
        cluster = SlurmCluster.objects.create(name="Test Cluster")
        account = SlurmAccount.objects.create(name="Test Account", cluster=cluster)
        cls.qos1 = SlurmQOS.objects.create(name="high")
        cls.qos2 = SlurmQOS.objects.create(name="normal")

        cls.bulk_edit_form_data = {
            "fairshare": 10,
            "max_jobs": 50,
        }
        # qos_add/qos_remove are optional M2M fields — not set in bulk edit
        cls.bulk_edit_form_data.setdefault("qos_add", [])
        cls.bulk_edit_form_data.setdefault("qos_remove", [])

        from django.contrib.contenttypes.models import ContentType

        from coldfront.ras.models import Allocation, Project, Resource, ResourceType
        from coldfront.users.models import User

        owner = User.objects.create(username="pi")
        resource_type = ResourceType.objects.create(name="Cluster", slug="cluster")
        resource = Resource.objects.create(name="Test Resource", slug="test-resource", resource_type=resource_type)
        resource_ct = ContentType.objects.get_for_model(Resource)

        project = Project.objects.create(name="Test Project", owner=owner)
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
        allocation5 = Allocation.objects.create(
            project=project,
            slug="TEST-005",
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
            owner=owner,
        )
        allocation6 = Allocation.objects.create(
            project=project,
            slug="TEST-006",
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

        cls.form_data = {
            "allocation": allocation4.pk,
            "slurm_account": account.pk,
            "fairshare": 1,
            "qos_add": [cls.qos1.pk],
            "qos_remove": [cls.qos2.pk],
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "allocation,slurm_account,fairshare",
            f"{allocation4.slug},{account.name},1",
            f"{allocation5.slug},{account.name},1",
            f"{allocation6.slug},{account.name},1",
        )

        cls.csv_update_data = (
            "id,allocation,slurm_account,fairshare",
            f"{associations[0].pk},{allocation1.slug},{account.name},2",
            f"{associations[1].pk},{allocation2.slug},{account.name},1",
            f"{associations[2].pk},{allocation3.slug},{account.name},1",
        )


class SlurmUserTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = SlurmUser

    def setUp(self):
        super().setUp()
        self.add_permissions("users.view_user")

    @classmethod
    def setUpTestData(cls):
        cluster = SlurmCluster.objects.create(name="Test Cluster")
        account = SlurmAccount.objects.create(name="Test Account", cluster=cluster)
        users = (
            User(username="User1"),
            User(username="User2"),
            User(username="User3"),
            User(username="User4"),
            User(username="User5"),
            User(username="User6"),
        )
        for user in users:
            user.save()

        slurm_users = (
            SlurmUser(user=users[0], cluster=cluster, default_account=account),
            SlurmUser(user=users[1], cluster=cluster, default_account=account),
            SlurmUser(user=users[2], cluster=cluster, default_account=account),
        )
        for user_obj in slurm_users:
            user_obj.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "user": users[3].pk,  # User4 — no existing SlurmUser record
            "cluster": cluster.pk,
            "default_account": account.pk,
            "admin_level": 0,
            "tags": [t.pk for t in tags],
        }

        cls.bulk_edit_form_data = {
            "default_wckey": "new_wckey",
            "admin_level": 1,
        }

        cls.csv_data = (
            "user,cluster,default_account,admin_level",
            "User4,Test Cluster,Test Account,0",
            "User5,Test Cluster,Test Account,0",
            "User6,Test Cluster,Test Account,0",
        )

        cls.csv_update_data = (
            "id,user,cluster,admin_level",
            f"{slurm_users[0].pk},User4,Test Cluster,0",
            f"{slurm_users[1].pk},User5,Test Cluster,0",
            f"{slurm_users[2].pk},User6,Test Cluster,0",
        )
