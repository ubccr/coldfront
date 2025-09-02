# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from coldfront.core.resource.models import Resource
from coldfront.plugins.slurm.associations import SlurmCluster


class AssociationTest(TestCase):
    fixtures = ["test_data.json"]

    @classmethod
    def setUpClass(cls):
        call_command("import_field_of_science_data")
        call_command("add_default_grant_options")
        call_command("add_default_project_choices")
        call_command("add_default_allocation_choices")
        call_command("add_default_publication_sources")
        super(AssociationTest, cls).setUpClass()

    def test_allocations_to_slurm(self):
        resource = Resource.objects.get(name="University HPC")
        cluster = SlurmCluster.new_from_resource(resource)
        self.assertEqual(cluster.name, "university-hpc")
        self.assertEqual(len(cluster.accounts), 1)
        self.assertIn("ccollins", cluster.accounts)
        self.assertEqual(len(cluster.accounts["ccollins"].users), 3)
        for u in ["ccollins", "radams", "mlopez"]:
            self.assertIn(u, cluster.accounts["ccollins"].users)

    def test_parse_sacctmgr_roundtrip(self):
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
Cluster - 'alpha':DefaultQOS='general-compute':Fairshare=1:QOS='normal'
Parent - 'root'
User - 'root':DefaultAccount='root':AdminLevel='Administrator':Fairshare=1
Account - 'physics':Description='physics':Organization='physics':Fairshare=100:QOS='debug,general-compute'
Parent - 'physics'
User - 'jane':DefaultAccount='physics':Fairshare=parent
User - 'john':DefaultAccount='physics':Fairshare=parent
User - 'larry':DefaultAccount='physics':Fairshare=parent
        """)

        # Parse sacctmgr dump format
        cluster = SlurmCluster.new_from_stream(dump)
        self.assertEqual(cluster.name, "alpha")
        self.assertEqual(len(cluster.accounts), 2)
        self.assertIn("physics", cluster.accounts)
        self.assertEqual(len(cluster.accounts["physics"].users), 3)
        for u in ["jane", "john", "larry"]:
            self.assertIn(u, cluster.accounts["physics"].users)

        # Write sacctmgr dump format
        out = StringIO("")
        cluster.write(out)

        # Roundtrip
        cluster2 = SlurmCluster.new_from_stream(StringIO(out.getvalue()))
        self.assertEqual(cluster2.name, "alpha")
        self.assertEqual(len(cluster2.accounts), 2)
        self.assertIn("physics", cluster2.accounts)
        self.assertEqual(len(cluster2.accounts["physics"].users), 3)
        for u in ["jane", "john", "larry"]:
            self.assertIn(u, cluster2.accounts["physics"].users)
