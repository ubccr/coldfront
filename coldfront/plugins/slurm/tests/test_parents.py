# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from io import StringIO
import sys

from django.core.management import call_command
from django.test import TestCase

from coldfront.core.allocation.models import AllocationAttributeType, Allocation
from coldfront.core.resource.models import Resource, ResourceAttribute, ResourceAttributeType, ResourceType
from coldfront.core.test_helpers.factories import (
    AllocationAttributeFactory,
    AllocationAttributeTypeFactory,
    AllocationFactory,
    AllocationStatusChoiceFactory,
    AllocationUserFactory,
    ProjectFactory,
    ProjectUserFactory,
    ResourceFactory,
    ResourceTypeFactory,
    UserFactory,
)
from coldfront.plugins.slurm.associations import SlurmCluster

# Building this account structure in slurm/coldfront
# 'a' represents an account and 'u' represents a user
#
#      a1            a7
#     /  \          /  \
#   a2    a3       u1  u3
#   /    /  \
# u1   a4    a5
#     /  \   |
#    u1  u2  a6
#            |
#            u3


class AssociationTest(TestCase):
    @classmethod
    def setUpClass(cls):
        # call_command("import_field_of_science_data")
        # call_command("add_default_grant_options")
        call_command("add_default_project_choices")
        call_command("add_allocation_defaults")
        call_command("add_resource_defaults")

        super(AssociationTest, cls).setUpClass()

    @classmethod
    def setUpTestData(cls):
        # create cluster resource
        cls.resource = ResourceFactory(resource_type=ResourceType.objects.get(name="Cluster"))
        ResourceAttribute.objects.create(
            resource=cls.resource,
            resource_attribute_type=ResourceAttributeType.objects.get(name="slurm_cluster"),
            value="test_cluster",
        )
        # create users
        cls.u1 = UserFactory(username="u1")
        cls.u2 = UserFactory(username="u2")
        cls.u3 = UserFactory(username="u3")
        # create project
        cls.project = ProjectFactory(title="test_proj")
        ProjectUserFactory(project=cls.project, user=cls.u1)
        ProjectUserFactory(project=cls.project, user=cls.u2)
        ProjectUserFactory(project=cls.project, user=cls.u3)
        # create allocations
        alloc_kwargs = {"project": cls.project, "status": AllocationStatusChoiceFactory(name="Active")}
        san_aat = AllocationAttributeType.objects.get(name="slurm_account_name")
        sc_aat = AllocationAttributeType.objects.get(name="slurm_children")
        cls.a1 = Allocation.objects.create(**alloc_kwargs)
        cls.a2 = Allocation.objects.create(**alloc_kwargs)
        cls.a3 = Allocation.objects.create(**alloc_kwargs)
        cls.a4 = Allocation.objects.create(**alloc_kwargs)
        cls.a5 = Allocation.objects.create(**alloc_kwargs)
        cls.a6 = Allocation.objects.create(**alloc_kwargs)
        cls.a7 = Allocation.objects.create(**alloc_kwargs)
        cls.a1.resources.add(cls.resource)
        cls.a2.resources.add(cls.resource)
        cls.a3.resources.add(cls.resource)
        cls.a4.resources.add(cls.resource)
        cls.a5.resources.add(cls.resource)
        cls.a6.resources.add(cls.resource)
        cls.a7.resources.add(cls.resource)
        # slurm account names
        aat_kwargs = {"allocation_attribute_type": san_aat}
        AllocationAttributeFactory(allocation=cls.a1, value="a1", **aat_kwargs)
        AllocationAttributeFactory(allocation=cls.a2, value="a2", **aat_kwargs)
        AllocationAttributeFactory(allocation=cls.a3, value="a3", **aat_kwargs)
        AllocationAttributeFactory(allocation=cls.a4, value="a4", **aat_kwargs)
        AllocationAttributeFactory(allocation=cls.a5, value="a5", **aat_kwargs)
        AllocationAttributeFactory(allocation=cls.a6, value="a6", **aat_kwargs)
        AllocationAttributeFactory(allocation=cls.a7, value="a7", **aat_kwargs)
        # slurm children
        aat_kwargs = {"allocation_attribute_type": sc_aat}
        AllocationAttributeFactory(allocation=cls.a1, value="a2", **aat_kwargs)
        AllocationAttributeFactory(allocation=cls.a1, value="a3", **aat_kwargs)
        AllocationAttributeFactory(allocation=cls.a3, value="a4", **aat_kwargs)
        AllocationAttributeFactory(allocation=cls.a3, value="a5", **aat_kwargs)
        AllocationAttributeFactory(allocation=cls.a5, value="a6", **aat_kwargs)
        # add users to allocations
        AllocationUserFactory(allocation=cls.a2, user=cls.u1)
        AllocationUserFactory(allocation=cls.a4, user=cls.u1)
        AllocationUserFactory(allocation=cls.a4, user=cls.u2)
        AllocationUserFactory(allocation=cls.a6, user=cls.u3)
        AllocationUserFactory(allocation=cls.a7, user=cls.u1)
        AllocationUserFactory(allocation=cls.a7, user=cls.u3)

    def test_allocations_to_slurm(self):
        """non-exhaustive, should make better"""
        cluster = SlurmCluster.new_from_resource(self.resource)
        self.assertEqual(cluster.name, "test_cluster")
        self.assertEqual(len(cluster.accounts), 2)
        self.assertIn("a1", cluster.accounts)
        self.assertIn("a7", cluster.accounts)
        self.assertEqual(len(cluster.accounts["a7"].children), 2)

    def test_slurm_dump_roundtrip(self):
        """todo"""
        dump = StringIO("""
# To edit this file start with a cluster line for the new cluster
# Cluster - 'cluster_name':MaxNodesPerJob=50
# Followed by Accounts you want in this fashion (root is created by default)...
# Parent - 'root'
# Account - 'cs':MaxNodesPerJob=5:MaxJobs=4:MaxTRESMins=cpu=20:FairShare=399:MaxWallDuration=40:Description='Computer Science':Organization='LC'
# Any of the options after a ':' can be left out and they can be in any order.
# If you want to add any sub accounts just list the Parent THAT HAS ALREADY 
# BEEN CREATED before the account line in this fashion...
# Parent - 'cs'
# Account - 'test':MaxNodesPerJob=1:MaxJobs=1:MaxTRESMins=cpu=1:FairShare=1:MaxWallDuration=1:Description='Test Account':Organization='Test'
# To add users to a account add a line like this after a Parent - 'line'
# User - 'lipari':MaxNodesPerJob=2:MaxJobs=3:MaxTRESMins=cpu=4:FairShare=1:MaxWallDurationPerJob=1
Cluster - 'test_cluster'
Parent - 'root'
User - 'root':DefaultAccount='root':AdminLevel='Administrator':Fairshare=1
Account - 'a1':Description='a1':Organization='a1'
Account - 'a7':Description='a7':Organization='a7'
Parent - 'a1'
Account - 'a2':Description='a2':Organization='a2'
Account - 'a3':Description='a3':Organization='a3'
Parent - 'a2'
User - 'u1'
Parent - 'a3'
Account - 'a4':Description='a4':Organization='a4'
Account - 'a5':Description='a5':Organization='a5'
Parent - 'a4'
User - 'u1'
User - 'u2'
Parent - 'a5'
Account - 'a6':Description='a6':Organization='a6'
Parent - 'a6'
User - 'u3'
Parent - 'a7'
User - 'u1'
User - 'u3'
        """)

        expected = """Cluster - 'test_cluster':
Parent - 'root'
User - 'root':DefaultAccount='root':AdminLevel='Administrator':Fairshare=1
Account - 'a1':
Account - 'a7':
Parent - 'a1'
Account - 'a3':
Account - 'a2':
Parent - 'a3'
Account - 'a4':
Account - 'a5':
Parent - 'a4'
User - 'u1':
User - 'u2':
Parent - 'a5'
Account - 'a6':
Parent - 'a6'
User - 'u3':
Parent - 'a2'
User - 'u1':
Parent - 'a7'
User - 'u1':
User - 'u3':""".strip()

        cluster = SlurmCluster.new_from_resource(self.resource)
        out = StringIO("")
        cluster.write(out)
        cluster.write(sys.stdout)
        out.seek(0)

        cluster = SlurmCluster.new_from_stream(out)

        self.assertEqual(cluster.name, "test_cluster")
        self.assertEqual(len(cluster.accounts), 3)
        self.assertIn("a1", cluster.accounts)
        self.assertIn("a7", cluster.accounts)
        self.assertEqual(len(cluster.accounts["a7"].children), 2)
