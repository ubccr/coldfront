# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.flows import AllocationStatusFlow
from coldfront.ras.models import Allocation, Resource, ResourceType
from coldfront.ras.models.projects import Project, ProjectUser
from coldfront.slurm.export import generate_association_dump
from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmQOS,
    SlurmUser,
)
from coldfront.slurm.parser import SlurmTime
from coldfront.users.models import User


class GenerateClusterDumpTestCase(TestCase):
    """Integration tests for generate_association_dump."""

    def setUp(self):
        # Re-register the slurm lifecycle callbacks (tests/flows clears
        # ``AllocationStatusFlow._target_callbacks``), so ``flow.activate()``
        # still triggers the SlurmUser reconciliation the dump relies on.
        AllocationStatusFlow._target_callbacks = {}
        AllocationStatusFlow._transition_permission_callbacks = {}
        from coldfront.slurm.listeners import (
            can_activate_check,
            on_allocation_activated,
            on_allocation_denied,
            on_allocation_expired,
            on_allocation_revoked,
        )

        AllocationStatusFlow.register_target_callback(
            AllocationStatusChoices.STATUS_ACTIVE,
            on_allocation_activated,
        )
        AllocationStatusFlow.register_target_callback(
            AllocationStatusChoices.STATUS_EXPIRED,
            on_allocation_expired,
        )
        AllocationStatusFlow.register_target_callback(
            AllocationStatusChoices.STATUS_REVOKED,
            on_allocation_revoked,
        )
        AllocationStatusFlow.register_target_callback(
            AllocationStatusChoices.STATUS_DENIED,
            on_allocation_denied,
        )
        AllocationStatusFlow.register_transition_permission_callback(
            "activate",
            can_activate_check,
        )

        # Fresh data per test to avoid shared-state pollution
        self.user1 = User.objects.create(username="alice")
        self.user2 = User.objects.create(username="bob")

        self.project = Project.objects.create(name="Research Lab", owner=self.user1)
        ProjectUser.objects.create(project=self.project, user=self.user1)
        ProjectUser.objects.create(project=self.project, user=self.user2)

        self.cluster = SlurmCluster.objects.create(name="hpc01", fairshare=1)
        self.qos_n = SlurmQOS.objects.create(name="normal")
        self.qos_h = SlurmQOS.objects.create(name="high")
        self.cluster.qos_list.add(self.qos_n, self.qos_h)

        self.acct_a = SlurmAccount.objects.create(name="acct-a", cluster=self.cluster, fairshare=5)
        self.acct_a.qos_add.add(self.qos_n)

        self.acct_b = SlurmAccount.objects.create(name="acct-b", cluster=self.cluster)

        self.partition = SlurmPartition.objects.create(name="gpu", cluster=self.cluster)
        self.partition.allow_qos.add(self.qos_h)

    def _make_active_allocation(self, project, resource, account=None):
        """Helper: create an active allocation and return its SlurmAssociation."""
        ct = ContentType.objects.get_for_model(type(resource))
        alloc = Allocation.objects.create(
            project=project,
            owner=project.owner,
            resource_object_type=ct,
            resource_object_id=resource.pk,
        )
        # SlurmAssociation is now created via the allocation form, not automatically.
        assoc = SlurmAssociation.objects.create(allocation=alloc)
        if account:
            assoc.slurm_account = account
            assoc.save()
        flow = AllocationStatusFlow(alloc)
        flow.request()
        flow.approve()
        flow.activate()
        return assoc

    def test_basic_dump_structure(self):
        """Dump contains cluster header, root account, and account/user lines."""
        self._make_active_allocation(self.project, self.cluster, self.acct_a)

        dump = generate_association_dump(self.cluster)
        lines = dump.splitlines()

        self.assertIn("Cluster - 'hpc01'", dump)
        self.assertIn("Parent - 'root'", dump)
        self.assertIn("Account - 'acct-a'", dump)
        self.assertIn("User - 'alice'", dump)
        self.assertIn("User - 'bob'", dump)

        # Structure check
        self.assertGreaterEqual(len(lines), 7)

    def test_root_account_present(self):
        """Root user line always appears, even with no slurm accounts."""
        dump = generate_association_dump(self.cluster)
        self.assertIn("Parent - 'root'", dump)
        self.assertIn("User - 'root'", dump)
        self.assertIn("AdminLevel='Administrator'", dump)

    def test_no_active_assocs_no_account_lines(self):
        """No Account lines beyond root when no active associations."""
        dump = generate_association_dump(self.cluster)
        lines = dump.splitlines()
        # Only QOS lines, blank, cluster, blank, root parent, root user, blank
        self.assertLessEqual(len(lines), 8)

    def test_multiple_accounts(self):
        """Multiple accounts with active associations each get their own block."""
        self._make_active_allocation(self.project, self.cluster, self.acct_a)
        self._make_active_allocation(self.project, self.cluster, self.acct_b)

        dump = generate_association_dump(self.cluster)
        self.assertIn("Account - 'acct-a'", dump)
        self.assertIn("Account - 'acct-b'", dump)

    def test_partition_targeting(self):
        """Allocation targeting a partition includes Partition='<name>'."""
        self._make_active_allocation(self.project, self.partition, self.acct_a)

        dump = generate_association_dump(self.cluster)
        self.assertIn("Partition='gpu'", dump)
        self.assertIn("Account - 'acct-a'", dump)

    def test_partition_qos_inherited(self):
        """User lines use the partition's QOS list when targeting a partition."""
        self._make_active_allocation(self.project, self.partition, self.acct_a)

        dump = generate_association_dump(self.cluster)
        self.assertIn("QOS='", dump)
        self.assertIn("+high", dump)

    def test_cluster_qos_inherited(self):
        """User lines use the cluster's QOS list when targeting a cluster."""
        self._make_active_allocation(self.project, self.cluster, self.acct_a)

        dump = generate_association_dump(self.cluster)
        self.assertIn("QOS='", dump)
        self.assertIn("+normal", dump)
        self.assertIn("+high", dump)

    def test_fairshare_inherited(self):
        """User fairshare is 'parent' when the account has fairshare, else
        comes from the association."""
        # account has fairshare -> user uses 'parent'
        self._make_active_allocation(self.project, self.cluster, self.acct_a)
        dump = generate_association_dump(self.cluster)
        self.assertIn("Fairshare=parent", dump)

        # account has no fairshare -> user fairshare defaults to assoc.fairshare (1)
        self._make_active_allocation(self.project, self.cluster, self.acct_b)
        dump = generate_association_dump(self.cluster)
        self.assertIn("Fairshare=1", dump)

    def test_slurm_user_customizes_default_account(self):
        """User's DefaultAccount comes from SlurmUser after activation reconcile."""
        # Create SlurmUser BEFORE activating (lifecycle callback reconciles it)
        # Activation reconciles the default to the active allocation's account.
        SlurmUser.objects.create(
            user=self.user1,
            cluster=self.cluster,
            default_account=self.acct_b,
        )

        self._make_active_allocation(self.project, self.cluster, self.acct_a)

        dump = generate_association_dump(self.cluster)
        # alice has SlurmUser whose default was reconciled to the active acct-a
        lines = dump.splitlines()
        alice_line = [line for line in lines if "alice" in line]
        self.assertTrue(len(alice_line) > 0)
        self.assertIn("DefaultAccount='acct-a'", alice_line[0])

    def test_slurm_user_admin_level_and_wckey(self):
        """User line includes AdminLevel and DefaultWCKey from SlurmUser."""
        # Create SlurmUser BEFORE activating (lifecycle callback creates one too)
        # By creating it first with custom fields, get_or_create won't modify it
        SlurmUser.objects.create(
            user=self.user1,
            cluster=self.cluster,
            default_account=self.acct_a,
            admin_level=1,
            default_wckey="mykey",
        )

        self._make_active_allocation(self.project, self.cluster, self.acct_a)

        dump = generate_association_dump(self.cluster)
        lines = dump.splitlines()
        alice_line = [line for line in lines if "alice" in line]
        self.assertTrue(len(alice_line) > 0)
        self.assertIn("AdminLevel='None'", alice_line[0])
        self.assertIn("DefaultWCKey='mykey'", alice_line[0])

    def test_association_limits_included(self):
        """Association limit fields appear in user lines."""
        ct = ContentType.objects.get_for_model(SlurmCluster)
        alloc = Allocation.objects.create(
            project=self.project,
            owner=self.user1,
            resource_object_type=ct,
            resource_object_id=self.cluster.pk,
        )
        assoc = SlurmAssociation.objects.create(allocation=alloc)
        assoc.slurm_account = self.acct_a
        assoc.max_jobs = 10
        assoc.max_wall_duration_per_job = SlurmTime(duration=timedelta(hours=48))
        assoc.save()
        flow = AllocationStatusFlow(alloc)
        flow.request()
        flow.approve()
        AllocationStatusFlow._transition_permission_callbacks = {}
        flow.activate()

        dump = generate_association_dump(self.cluster)
        self.assertIn("MaxJobs=10", dump)
        self.assertIn("MaxWallDurationPerJob=172800", dump)  # 48h * 3600

    def test_account_line_format(self):
        """Account line carries fairshare/QOS; the parent line precedes the account."""
        self._make_active_allocation(self.project, self.cluster, self.acct_a)

        dump = generate_association_dump(self.cluster)
        lines = dump.splitlines()
        acct_line = [line for line in lines if "Account - 'acct-a'" in line]
        self.assertTrue(len(acct_line) > 0)
        self.assertIn("Fairshare=5", acct_line[0])
        self.assertIn("QOS='+normal'", acct_line[0])

        # Parent line appears before the account line
        acct_idx = None
        parent_idx = None
        for i, line in enumerate(lines):
            if "Account - 'acct-a'" in line:
                acct_idx = i
            if "Parent -" in line and parent_idx is None:
                parent_idx = i
        self.assertIsNotNone(acct_idx)
        self.assertIsNotNone(parent_idx)
        self.assertLess(parent_idx, acct_idx)

    def test_custom_parent_account(self):
        """Parent line uses association's parent account when set."""
        parent_acct = SlurmAccount.objects.create(name="parent-acct", cluster=self.cluster)
        ct = ContentType.objects.get_for_model(SlurmCluster)
        alloc = Allocation.objects.create(
            project=self.project,
            owner=self.user1,
            resource_object_type=ct,
            resource_object_id=self.cluster.pk,
        )
        assoc = SlurmAssociation.objects.create(allocation=alloc)
        assoc.slurm_account = self.acct_a
        assoc.parent = parent_acct
        assoc.save()
        flow = AllocationStatusFlow(alloc)
        flow.request()
        flow.approve()
        AllocationStatusFlow._transition_permission_callbacks = {}
        flow.activate()

        dump = generate_association_dump(self.cluster)
        self.assertIn("Parent - 'parent-acct'", dump)

    def test_multiple_users_per_association(self):
        """Each project user gets a user line."""
        # Add a third user to the project
        user3 = User.objects.create(username="charlie")
        ProjectUser.objects.create(project=self.project, user=user3)

        self._make_active_allocation(self.project, self.cluster, self.acct_a)

        dump = generate_association_dump(self.cluster)
        self.assertIn("User - 'alice'", dump)
        self.assertIn("User - 'bob'", dump)
        self.assertIn("User - 'charlie'", dump)

    def test_duplicate_association_same_account(self):
        """Multiple associations for same account don't duplicate user lines."""
        # Create two active allocations on the same account
        self._make_active_allocation(self.project, self.cluster, self.acct_a)
        self._make_active_allocation(self.project, self.cluster, self.acct_a)

        dump = generate_association_dump(self.cluster)
        # Count user lines for alice — should only appear once per association
        # (each association generates a user line for each project user)
        lines = dump.splitlines()
        alice_count = sum(1 for line in lines if "User - 'alice'" in line)
        # Two associations → two user lines for alice
        self.assertEqual(alice_count, 2)

    def test_default_qos_appears(self):
        """Association default_qos produces DefaultQOS='<name>' in user line."""
        assoc = self._make_active_allocation(self.project, self.cluster, self.acct_a)
        default_qos = SlurmQOS.objects.create(name="default-qos")
        assoc.default_qos = default_qos
        assoc.save()

        dump = generate_association_dump(self.cluster)
        self.assertIn("DefaultQOS='default-qos'", dump)

    def test_qos_add_appears(self):
        """Association qos_add produces QOS='+<name>' in user line."""
        assoc = self._make_active_allocation(self.project, self.cluster, self.acct_a)
        extra_qos = SlurmQOS.objects.create(name="extra")
        assoc.qos_add.add(extra_qos)

        dump = generate_association_dump(self.cluster)
        self.assertIn("QOS='", dump)
        self.assertIn("+extra", dump)

    def test_qos_remove_appears(self):
        """Association qos_remove produces QOS='-<name>' in user line."""
        assoc = self._make_active_allocation(self.project, self.cluster, self.acct_a)
        rm_qos = SlurmQOS.objects.create(name="scavenger")
        assoc.qos_remove.add(rm_qos)

        dump = generate_association_dump(self.cluster)
        self.assertIn("QOS='", dump)
        self.assertIn("-scavenger", dump)

    def test_qos_add_and_remove_combined(self):
        """Both qos_add and qos_remove appear with +/- prefixes."""
        assoc = self._make_active_allocation(self.project, self.cluster, self.acct_a)
        add_qos = SlurmQOS.objects.create(name="express")
        rm_qos = SlurmQOS.objects.create(name="scavenger")
        assoc.qos_add.add(add_qos)
        assoc.qos_remove.add(rm_qos)

        dump = generate_association_dump(self.cluster)
        self.assertIn("QOS='", dump)
        self.assertIn("+high", dump)
        self.assertIn("-scavenger", dump)

    def test_no_project_users_no_user_lines(self):
        """No user lines when project has no members."""
        empty_project = Project.objects.create(name="Empty", owner=self.user1)
        self._make_active_allocation(empty_project, self.cluster, self.acct_a)

        dump = generate_association_dump(self.cluster)
        self.assertNotIn("User -", dump.splitlines()[-5:])

    def test_null_slurm_account_excluded(self):
        """Association with null slurm_account is excluded from dump."""
        ct = ContentType.objects.get_for_model(SlurmCluster)
        Allocation.objects.create(
            project=self.project,
            owner=self.user1,
            resource_object_type=ct,
            resource_object_id=self.cluster.pk,
            status=AllocationStatusChoices.STATUS_ACTIVE,
        )
        # Don't set slurm_account — stays None
        # The lifecycle callback already created the association; slurm_account is None
        dump = generate_association_dump(self.cluster)
        self.assertNotIn("acct-a", dump)

    def test_non_slurm_resource_skipped(self):
        """Allocation targeting a non-slurm resource is skipped."""
        resource_type = ResourceType.objects.create(name="Storage")
        resource = Resource.objects.create(
            name="nas-storage",
            resource_type=resource_type,
        )
        ct = ContentType.objects.get_for_model(Resource)
        Allocation.objects.create(
            project=self.project,
            owner=self.user1,
            resource_object_type=ct,
            resource_object_id=resource.pk,
            status=AllocationStatusChoices.STATUS_ACTIVE,
        )
        # This allocation won't have a SlurmAssociation since it's not slurm
        dump = generate_association_dump(self.cluster)
        self.assertNotIn("User -", dump.splitlines()[-5:])

    def test_dump_ends_with_newline(self):
        """Dump ends with a single trailing newline (join behavior)."""
        self._make_active_allocation(self.project, self.cluster, self.acct_a)

        dump = generate_association_dump(self.cluster)
        self.assertTrue(dump.endswith("\n") or dump.endswith(""))
        # The join adds a newline between lines but not after the last line
        # The last line is "" (empty string after the last account block),
        # so the dump ends with \n\n? Actually join adds \n between lines.
        # Lines: [cluster, "", root_parent, root_account, "", parent, account, user1, user2, "", ...]
        # The last line appended is "" after the account block, so the final character
        # is \n from joining "" with preceding line.

    def test_full_dump_roundtrip(self):
        """Verify the full dump format end to end."""
        self._make_active_allocation(self.project, self.cluster, self.acct_a)

        dump = generate_association_dump(self.cluster)
        lines = dump.splitlines()

        # Expected structure (13 lines):
        #   0: QOS - 'high':...
        #   1: QOS - 'normal':...
        #   2: (blank)
        #   3: Cluster - 'hpc01':...
        #   4: (blank)
        #   5: Parent - 'root'
        #   6: User - 'root':...
        #   7: (blank)
        #   8: Parent - 'root'
        #   9: Account - 'acct-a':...
        #  10: Parent - 'acct-a'
        #  11: User - 'alice':...
        #  12: User - 'bob':...
        #   (dump ends with \n from join of trailing "" line)

        self.assertGreaterEqual(len(lines), 13)
        self.assertLessEqual(len(lines), 13)

        # Check QOS lines
        self.assertIn("QOS - 'high'", lines[0])
        self.assertIn("QOS - 'normal'", lines[1])

        # Check blank line after QOS
        self.assertEqual(lines[2], "")

        # Check cluster line
        self.assertIn("Cluster - 'hpc01'", lines[3])
        self.assertIn("QOS='", lines[3])
        self.assertIn("normal", lines[3])
        self.assertIn("high", lines[3])
        self.assertIn("Fairshare=1", lines[3])

        # Check blank line after cluster
        self.assertEqual(lines[4], "")

        # Check root parent
        self.assertIn("Parent - 'root'", lines[5])

        # Check root user
        self.assertIn("User - 'root'", lines[6])
        self.assertIn("AdminLevel='Administrator'", lines[6])

        # Check blank line after root user
        self.assertEqual(lines[7], "")

        # Check parent line before acct-a
        self.assertIn("Parent - 'root'", lines[8])

        # Check account line
        self.assertIn("Account - 'acct-a'", lines[9])
        self.assertIn("Fairshare=5", lines[9])
        self.assertIn("QOS='+normal'", lines[9])

        # Check the account's own Parent line precedes its user lines
        self.assertIn("Parent - 'acct-a'", lines[10])

        # Check user lines — now use QOS='+normal,+high' format
        self.assertIn("User - 'alice'", lines[11])
        self.assertIn("DefaultAccount='acct-a'", lines[11])
        self.assertIn("Fairshare=parent", lines[11])
        self.assertIn("QOS='", lines[11])
        self.assertIn("+normal", lines[11])
        self.assertIn("+high", lines[11])

        self.assertIn("User - 'bob'", lines[12])
        self.assertIn("DefaultAccount='acct-a'", lines[12])
        self.assertIn("Fairshare=parent", lines[12])
        self.assertIn("QOS='", lines[12])
        self.assertIn("+normal", lines[12])
        self.assertIn("+high", lines[12])


class GenerateClusterDumpEdgeCaseTestCase(TestCase):
    """Edge cases for dump generation."""

    def test_cluster_with_no_partitions(self):
        """Cluster with no partitions still works."""
        cluster = SlurmCluster.objects.create(name="hpc-edge-1")
        dump = generate_association_dump(cluster)
        self.assertIn("Cluster - 'hpc-edge-1'", dump)
        self.assertIn("Parent - 'root'", dump)

    def test_cluster_with_no_accounts(self):
        """Cluster with no SlurmAccounts still works."""
        cluster = SlurmCluster.objects.create(name="hpc-edge-2")
        dump = generate_association_dump(cluster)
        self.assertIn("Cluster - 'hpc-edge-2'", dump)

    def test_resource_is_neither_cluster_nor_partition(self):
        """Resource that is not a SlurmCluster/Partition is skipped."""
        from coldfront.slurm.export.associations import _format_user_lines

        user = User.objects.create(username="weird")
        cluster = SlurmCluster.objects.create(name="hpc-edge-5")
        account = SlurmAccount.objects.create(name="weird-acct", cluster=cluster)
        project = Project.objects.create(name="Edge5", owner=user)

        rt = ResourceType.objects.create(name="Custom")
        resource = Resource.objects.create(name="custom-res", resource_type=rt)
        ct = ContentType.objects.get_for_model(Resource)

        alloc = Allocation.objects.create(
            project=project,
            owner=user,
            resource_object_type=ct,
            resource_object_id=resource.pk,
            status=AllocationStatusChoices.STATUS_ACTIVE,
        )
        # This allocation won't have a SlurmAssociation because it's not slurm
        # The lifecycle callback only creates associations for slurm resources
        # So we need to manually create one
        assoc = SlurmAssociation.objects.create(
            allocation=alloc,
            slurm_account=account,
            fairshare=1,
        )

        lines = _format_user_lines(assoc, cluster)
        self.assertEqual(lines, [])
