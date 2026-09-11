# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Tests for the Slurm signal handlers and allocation-flow callbacks
(``coldfront.slurm.listeners``).

Organized by test class:

- ``SlurmAssociationLifecycleTest`` — allocation flow request/activate/expire/revoke/deny callbacks
- ``ProjectUserSignalTest`` — on_project_user_saved / on_project_user_deleted
"""

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from coldfront.ras.choices import AllocationStatusChoices
from coldfront.ras.flows import AllocationStatusFlow
from coldfront.ras.models import Allocation, Project, Resource, ResourceType
from coldfront.ras.models.projects import ProjectUser
from coldfront.slurm.models import (
    SlurmAccount,
    SlurmAssociation,
    SlurmCluster,
    SlurmPartition,
    SlurmUser,
)
from coldfront.users.models import User


class SlurmAssociationLifecycleTest(TestCase):
    """Test the allocation-flow lifecycle callbacks in coldfront.slurm.listeners."""

    @classmethod
    def setUpTestData(cls):
        # Users
        cls.user1 = User.objects.create(username="Alice")
        cls.user2 = User.objects.create(username="Bob")

        # Project with members
        cls.project = Project.objects.create(name="Research Lab", owner=cls.user1)

        ProjectUser.objects.create(project=cls.project, user=cls.user1)
        ProjectUser.objects.create(project=cls.project, user=cls.user2)

        # Slurm cluster and partition
        cls.cluster = SlurmCluster.objects.create(name="hpc01")
        cls.partition = SlurmPartition.objects.create(
            name="gpu",
            cluster=cls.cluster,
        )

        # Slurm account
        cls.slurm_account = SlurmAccount.objects.create(
            name="lab-acct",
            cluster=cls.cluster,
        )

        # Resource type for generic FK (non-slurm)
        cls.resource_type = ResourceType.objects.create(name="Generic Resource")

        # ContentType for slurm cluster
        cls.cluster_ct = ContentType.objects.get_for_model(SlurmCluster)
        cls.partition_ct = ContentType.objects.get_for_model(SlurmPartition)
        cls.resource_ct = ContentType.objects.get_for_model(Resource)

    def setUp(self):
        # Clear any previously registered callbacks before each test
        AllocationStatusFlow._target_callbacks = {}
        AllocationStatusFlow._transition_permission_callbacks = {}

        # Re-register the slurm lifecycle callbacks
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

    def tearDown(self):
        super().tearDown()

    def _create_allocation(self, resource, resource_ct):
        allocation = Allocation.objects.create(
            justification="Need compute resources",
            project=self.project,
            owner=self.user1,
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
        )
        # SlurmAssociation is now created via the allocation form, not automatically.
        # Only create for slurm resources (SlurmCluster / SlurmPartition).
        if isinstance(resource, (SlurmCluster, SlurmPartition)):
            SlurmAssociation.objects.create(allocation=allocation)
        return allocation

    # ---------- Step 1: On allocation requested ----------

    def test_request_creates_slurm_association(self):
        """Requesting an allocation targeting a SlurmCluster or SlurmPartition
        creates a SlurmAssociation."""
        for resource, ct in [
            (self.cluster, self.cluster_ct),
            (self.partition, self.partition_ct),
        ]:
            allocation = self._create_allocation(resource, ct)
            flow = AllocationStatusFlow(allocation)
            flow.request()
            self.assertIsNotNone(SlurmAssociation.objects.filter(allocation=allocation).first())

    def test_request_does_not_create_duplicate_association(self):
        """Requesting twice should not create a second SlurmAssociation."""
        allocation = self._create_allocation(self.cluster, self.cluster_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()
        flow.request()  # second call — self-loop on STATUS_REQUESTED

        associations = SlurmAssociation.objects.filter(allocation=allocation)
        self.assertEqual(associations.count(), 1)

    def test_request_ignores_non_slurm_resource(self):
        """Requesting an allocation targeting a non-slurm resource should not
        create a SlurmAssociation."""
        resource = Resource.objects.create(
            name="Generic Storage",
            slug="s-1",
            resource_type=self.resource_type,
        )
        allocation = self._create_allocation(resource, self.resource_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()

        self.assertFalse(SlurmAssociation.objects.filter(allocation=allocation).exists())

    # ---------- Step 2: On allocation activated ----------

    def test_activate_creates_slurm_user_for_each_project_user(self):
        """Activating an allocation should create a SlurmUser for each ProjectUser
        if one doesn't already exist."""
        allocation = self._create_allocation(self.cluster, self.cluster_ct)

        # Request -> create SlurmAssociation
        flow = AllocationStatusFlow(allocation)
        flow.request()

        # Set the slurm_account on the association (simulates admin action)
        association = SlurmAssociation.objects.get(allocation=allocation)
        association.slurm_account = self.slurm_account
        association.save()

        # Approve -> Activate
        flow.approve()
        flow.activate()

        # SlurmUser records should exist for Alice and Bob
        alice_su = SlurmUser.objects.filter(user=self.user1, cluster=self.cluster).first()
        bob_su = SlurmUser.objects.filter(user=self.user2, cluster=self.cluster).first()
        self.assertIsNotNone(alice_su)
        self.assertIsNotNone(bob_su)
        self.assertEqual(alice_su.default_account, self.slurm_account)
        self.assertEqual(bob_su.default_account, self.slurm_account)

    def test_activate_updates_existing_slurm_user_default(self):
        """Activating should reconcile an existing SlurmUser's default_account
        to the active allocation's account (mirrors _sync_slurm_users_for_user)."""
        # Create a SlurmUser manually with a different default account
        other_account = SlurmAccount.objects.create(
            name="other-acct",
            cluster=self.cluster,
        )
        SlurmUser.objects.create(
            user=self.user1,
            cluster=self.cluster,
            default_account=other_account,
        )

        allocation = self._create_allocation(self.cluster, self.cluster_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()

        association = SlurmAssociation.objects.get(allocation=allocation)
        association.slurm_account = self.slurm_account
        association.save()

        flow.approve()
        flow.activate()

        # Alice's existing SlurmUser is reconciled to the active allocation's account
        alice_su = SlurmUser.objects.get(user=self.user1, cluster=self.cluster)
        self.assertEqual(alice_su.default_account, self.slurm_account)

        # Bob's SlurmUser should be created with slurm_account
        bob_su = SlurmUser.objects.get(user=self.user2, cluster=self.cluster)
        self.assertEqual(bob_su.default_account, self.slurm_account)

    def test_activate_skips_when_no_slurm_account_set(self):
        """Activating should not create SlurmUser records if slurm_account is null.

        Note: bypasses permission callbacks because the condition check would
        otherwise block the activate transition."""
        AllocationStatusFlow._transition_permission_callbacks = {}

        allocation = self._create_allocation(self.cluster, self.cluster_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()
        # Do NOT set slurm_account — leave it null
        flow.approve()
        flow.activate()

        # No SlurmUser records should exist
        self.assertFalse(SlurmUser.objects.filter(cluster=self.cluster).exists())

    def test_activate_skips_when_no_slurm_association(self):
        """Activating should skip if no SlurmAssociation exists for the allocation.

        Note: bypasses permission callbacks because the condition check would
        otherwise block the activate transition."""
        AllocationStatusFlow._transition_permission_callbacks = {}

        allocation = self._create_allocation(self.cluster, self.cluster_ct)

        # Bypass the request callback — go straight to approve/activate
        # (simulates an allocation created without the callback)
        flow = AllocationStatusFlow(allocation)
        # Manually set status to approved so we can activate
        allocation.status = AllocationStatusChoices.STATUS_APPROVED
        allocation.save()

        flow.activate()

        # No SlurmUser records should exist
        self.assertFalse(SlurmUser.objects.filter(cluster=self.cluster).exists())

    def test_activate_ignores_non_slurm_resource(self):
        """Activating a non-slurm allocation should not create SlurmUser records."""
        resource = Resource.objects.create(
            name="Generic Storage",
            slug="s-1",
            resource_type=self.resource_type,
        )
        allocation = self._create_allocation(resource, self.resource_ct)

        flow = AllocationStatusFlow(allocation)
        # Request (no SlurmAssociation created for non-slurm resource)
        flow.request()

        # Manually set to approved so we can activate
        allocation.status = AllocationStatusChoices.STATUS_APPROVED
        allocation.save()

        flow.activate()

        self.assertFalse(SlurmUser.objects.filter(cluster__isnull=False).exists())

    # ---------- Expired / revoked / denied reconcile ----------

    def test_expired_removes_slurm_user_when_no_other_active_access(self):
        """Expiring an allocation removes members' SlurmUser records unless
        they have another active allocation on the cluster."""
        allocation = self._create_allocation(self.cluster, self.cluster_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()

        association = SlurmAssociation.objects.get(allocation=allocation)
        association.slurm_account = self.slurm_account
        association.save()

        flow.approve()
        flow.activate()
        self.assertTrue(SlurmUser.objects.filter(user=self.user1, cluster=self.cluster).exists())

        flow.expire()

        # No other active allocation -> SlurmUser removed
        self.assertFalse(SlurmUser.objects.filter(user=self.user1, cluster=self.cluster).exists())
        self.assertFalse(SlurmUser.objects.filter(user=self.user2, cluster=self.cluster).exists())

    def test_revoked_removes_slurm_user_when_no_other_active_access(self):
        """Revoking an allocation removes members' SlurmUser records unless
        they have another active allocation on the cluster."""
        allocation = self._create_allocation(self.cluster, self.cluster_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()

        association = SlurmAssociation.objects.get(allocation=allocation)
        association.slurm_account = self.slurm_account
        association.save()

        flow.approve()
        flow.activate()
        self.assertTrue(SlurmUser.objects.filter(user=self.user1, cluster=self.cluster).exists())

        flow.revoke()

        self.assertFalse(SlurmUser.objects.filter(user=self.user1, cluster=self.cluster).exists())

    def test_denied_removes_slurm_user_when_no_other_active_access(self):
        """Denying an allocation removes a member's stale SlurmUser record
        when they have no other active allocation on the cluster."""
        SlurmUser.objects.create(
            user=self.user1,
            cluster=self.cluster,
            default_account=self.slurm_account,
        )
        allocation = self._create_allocation(self.cluster, self.cluster_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()
        flow.deny()

        # Denied allocation is not active -> no active access -> SlurmUser removed
        self.assertFalse(SlurmUser.objects.filter(user=self.user1, cluster=self.cluster).exists())

    def test_expired_keeps_slurm_user_when_other_active_access(self):
        """Expiring one allocation keeps a member's SlurmUser when they have
        another active allocation on the same cluster."""
        other = SlurmAccount.objects.create(name="other-acct", cluster=self.cluster)

        # Two active allocations on the same cluster
        alloc1 = self._create_allocation(self.cluster, self.cluster_ct)
        alloc2 = self._create_allocation(self.cluster, self.cluster_ct)

        flow1 = AllocationStatusFlow(alloc1)
        flow1.request()
        a1 = SlurmAssociation.objects.get(allocation=alloc1)
        a1.slurm_account = self.slurm_account
        a1.save()
        flow1.approve()
        flow1.activate()

        flow2 = AllocationStatusFlow(alloc2)
        flow2.request()
        a2 = SlurmAssociation.objects.get(allocation=alloc2)
        a2.slurm_account = other
        a2.save()
        flow2.approve()
        flow2.activate()

        # Expire alloc1 — user1 still has alloc2 active
        flow1.expire()

        su = SlurmUser.objects.get(user=self.user1, cluster=self.cluster)
        self.assertEqual(su.default_account, other)

    # ---------- Permission callback tests ----------

    def test_activate_blocked_when_no_slurm_account(self):
        """
        The permission callback should block activation when the SlurmAssociation
        has no slurm_account set.
        """
        allocation = self._create_allocation(self.cluster, self.cluster_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()  # creates SlurmAssociation without slurm_account
        flow.approve()  # moves to STATUS_APPROVED

        # can_proceed passes (source matches), but has_perm fails (permission
        # callback denies it)
        self.assertTrue(flow.activate.can_proceed())
        self.assertFalse(flow.activate.has_perm(self.user1))

    def test_activate_allowed_when_slurm_account_set(self):
        """
        The permission callback should allow activation when the SlurmAssociation
        has a slurm_account set.
        """
        allocation = self._create_allocation(self.cluster, self.cluster_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()

        # Set the slurm_account on the association
        association = SlurmAssociation.objects.get(allocation=allocation)
        association.slurm_account = self.slurm_account
        association.save()

        flow.approve()

        self.assertTrue(flow.activate.can_proceed())
        self.assertTrue(flow.activate.has_perm(self.user1))

    def test_activate_allowed_for_non_slurm_allocation(self):
        """
        The permission callback should allow activation for non-slurm allocations
        (no SlurmAssociation exists — no restriction).
        """
        resource = Resource.objects.create(
            name="Generic Storage",
            slug="s-1",
            resource_type=self.resource_type,
        )
        allocation = self._create_allocation(resource, self.resource_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()  # no SlurmAssociation created for non-slurm
        flow.approve()

        self.assertTrue(flow.activate.can_proceed())
        self.assertTrue(flow.activate.has_perm(self.user1))


class ProjectUserSignalTest(TestCase):
    """Test the ProjectUser signal handlers in coldfront.slurm.listeners."""

    @classmethod
    def setUpTestData(cls):
        # Users
        cls.user1 = User.objects.create(username="Alice")
        cls.user2 = User.objects.create(username="Bob")
        cls.user3 = User.objects.create(username="Charlie")

        # Projects
        cls.project_a = Project.objects.create(name="Project Alpha", owner=cls.user1)
        cls.project_b = Project.objects.create(name="Project Beta", owner=cls.user2)

        # Slurm clusters and accounts
        cls.cluster1 = SlurmCluster.objects.create(name="hpc01")
        cls.cluster2 = SlurmCluster.objects.create(name="hpc02")
        cls.account_a = SlurmAccount.objects.create(name="alpha-acct", cluster=cls.cluster1)
        cls.account_b = SlurmAccount.objects.create(name="beta-acct", cluster=cls.cluster2)
        cls.account_c = SlurmAccount.objects.create(name="alt-acct", cluster=cls.cluster1)

        # Resource type and content types
        cls.resource_type = ResourceType.objects.create(name="Generic Resource")
        cls.cluster_ct = ContentType.objects.get_for_model(SlurmCluster)
        cls.partition_ct = ContentType.objects.get_for_model(SlurmPartition)
        cls.resource_ct = ContentType.objects.get_for_model(Resource)

    def _create_active_allocation(self, resource, resource_ct, project, account):
        """Create an allocation and move it through the flow to ACTIVE status,
        setting slurm_account on the association before activation."""
        allocation = Allocation.objects.create(
            justification="Need compute resources",
            project=project,
            owner=self.user1,
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
        )
        # SlurmAssociation is now created via the allocation form, not automatically.
        association = SlurmAssociation.objects.create(allocation=allocation)
        association.slurm_account = account
        association.save()
        flow = AllocationStatusFlow(allocation)
        flow.request()
        flow.approve()
        # Bypass permission callbacks for activation
        AllocationStatusFlow._transition_permission_callbacks = {}
        flow.activate()
        return allocation

    def _create_active_partition_allocation(self, partition, project, account):
        """Create an allocation on a SlurmPartition and activate it."""
        return self._create_active_allocation(partition, self.partition_ct, project, account)

    def _create_active_cluster_allocation(self, cluster, project, account):
        """Create an allocation on a SlurmCluster and activate it."""
        return self._create_active_allocation(cluster, self.cluster_ct, project, account)

    # ---------- ProjectUser created ----------

    def test_project_user_created_creates_slurm_user(self):
        """Creating a ProjectUser on a project with an active slurm allocation
        creates a SlurmUser on the cluster (direct or via partition)."""
        # cluster target
        self._create_active_cluster_allocation(self.cluster1, self.project_a, self.account_a)
        ProjectUser.objects.create(project=self.project_a, user=self.user3)
        su = SlurmUser.objects.filter(user=self.user3, cluster=self.cluster1).first()
        self.assertIsNotNone(su)
        self.assertEqual(su.default_account, self.account_a)

        # partition target — use a distinct project/user to avoid unique conflicts
        project_c = Project.objects.create(name="Project Gamma", owner=self.user2)
        user4 = User.objects.create(username="Diana")
        partition = SlurmPartition.objects.create(name="gpu", cluster=self.cluster1)
        self._create_active_partition_allocation(partition, project_c, self.account_a)
        ProjectUser.objects.create(project=project_c, user=user4)
        su = SlurmUser.objects.filter(user=user4, cluster=self.cluster1).first()
        self.assertIsNotNone(su)
        self.assertEqual(su.default_account, self.account_a)

    def test_project_user_created_skips_when_no_active_allocation(self):
        """Creating a ProjectUser on a project with only non-active slurm
        allocations should not create any SlurmUser."""
        allocation = Allocation.objects.create(
            justification="Pending",
            project=self.project_a,
            owner=self.user1,
            resource_object_type=self.cluster_ct,
            resource_object_id=self.cluster1.pk,
            status=AllocationStatusChoices.STATUS_REQUESTED,
        )
        # SlurmAssociation is now created via the allocation form, not automatically.
        assoc = SlurmAssociation.objects.create(allocation=allocation)
        assoc.slurm_account = self.account_a
        assoc.save()

        ProjectUser.objects.create(project=self.project_a, user=self.user3)

        self.assertFalse(SlurmUser.objects.filter(user=self.user3).exists())

    def test_project_user_created_uses_first_account_when_multiple(self):
        """When a project has multiple active allocations on the same cluster
        with different accounts, the first one's account should be used."""
        self._create_active_cluster_allocation(self.cluster1, self.project_a, self.account_a)
        self._create_active_cluster_allocation(self.cluster1, self.project_a, self.account_c)

        ProjectUser.objects.create(project=self.project_a, user=self.user3)

        su = SlurmUser.objects.get(user=self.user3, cluster=self.cluster1)
        self.assertEqual(su.default_account, self.account_a)

    def test_project_user_created_handles_multiple_clusters(self):
        """When a project has active allocations on multiple clusters, a
        SlurmUser should be created for each cluster."""
        self._create_active_cluster_allocation(self.cluster1, self.project_a, self.account_a)
        self._create_active_cluster_allocation(self.cluster2, self.project_a, self.account_b)

        ProjectUser.objects.create(project=self.project_a, user=self.user3)

        su1 = SlurmUser.objects.get(user=self.user3, cluster=self.cluster1)
        su2 = SlurmUser.objects.get(user=self.user3, cluster=self.cluster2)
        self.assertEqual(su1.default_account, self.account_a)
        self.assertEqual(su2.default_account, self.account_b)

    def test_project_user_created_updates_existing_slurm_user(self):
        """If a SlurmUser already exists for the user/cluster but with a
        different account, it should be updated to the project's account."""
        other_account = SlurmAccount.objects.create(name="old-acct", cluster=self.cluster1)
        SlurmUser.objects.create(
            user=self.user3,
            cluster=self.cluster1,
            default_account=other_account,
        )

        self._create_active_cluster_allocation(self.cluster1, self.project_a, self.account_a)

        ProjectUser.objects.create(project=self.project_a, user=self.user3)

        su = SlurmUser.objects.get(user=self.user3, cluster=self.cluster1)
        self.assertEqual(su.default_account, self.account_a)

    # ---------- ProjectUser deleted ----------

    def test_project_user_deleted_removes_slurm_user_when_no_other_access(self):
        """When a ProjectUser is deleted and the user has no other projects
        with access to that cluster, the SlurmUser should be removed."""
        self._create_active_cluster_allocation(self.cluster1, self.project_a, self.account_a)

        pu = ProjectUser.objects.create(project=self.project_a, user=self.user3)
        self.assertTrue(SlurmUser.objects.filter(user=self.user3, cluster=self.cluster1).exists())

        pu.delete()

        self.assertFalse(SlurmUser.objects.filter(user=self.user3, cluster=self.cluster1).exists())

    def test_project_user_deleted_keeps_slurm_user_when_other_project_has_access(self):
        """When a ProjectUser is deleted but the user has another project
        with access to the same cluster, the SlurmUser should remain."""
        self._create_active_cluster_allocation(self.cluster1, self.project_a, self.account_a)
        self._create_active_cluster_allocation(self.cluster1, self.project_b, self.account_c)

        pu_a = ProjectUser.objects.create(project=self.project_a, user=self.user3)
        ProjectUser.objects.create(project=self.project_b, user=self.user3)
        self.assertTrue(SlurmUser.objects.filter(user=self.user3, cluster=self.cluster1).exists())

        pu_a.delete()

        su = SlurmUser.objects.get(user=self.user3, cluster=self.cluster1)
        self.assertEqual(su.default_account, self.account_c)
