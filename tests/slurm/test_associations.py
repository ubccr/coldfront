# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from unittest import mock

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
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
    """Test the lifecycle callbacks in coldfront.slurm.listeners."""

    @classmethod
    def setUpTestData(cls):
        # Users
        cls.user1 = User.objects.create(username="Alice")
        cls.user2 = User.objects.create(username="Bob")
        cls.user3 = User.objects.create(username="Charlie")

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

        AllocationStatusFlow.register_transition_permission_callback(
            "activate",
            can_activate_check,
        )

        # Patch enqueue wrappers so existing listener tests don't trigger
        # REST API task enqueues (those are tested separately in test_sync.py)
        patcher = mock.patch.multiple(
            "coldfront.slurm.listeners",
            enqueue_activate_allocation=mock.DEFAULT,
            enqueue_deactivate_allocation=mock.DEFAULT,
            enqueue_remove_project_user=mock.DEFAULT,
        )
        self._enqueue_patcher = patcher
        patcher.start()

    def tearDown(self):
        self._enqueue_patcher.stop()
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

    def test_request_creates_slurm_association_for_cluster(self):
        """Requesting an allocation targeting a SlurmCluster should create a SlurmAssociation."""
        allocation = self._create_allocation(self.cluster, self.cluster_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()

        # A SlurmAssociation should exist for this allocation
        association = SlurmAssociation.objects.filter(allocation=allocation).first()
        self.assertIsNotNone(association)

    def test_request_creates_slurm_association_for_partition(self):
        """Requesting an allocation targeting a SlurmPartition should create a SlurmAssociation."""
        allocation = self._create_allocation(self.partition, self.partition_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()

        association = SlurmAssociation.objects.filter(allocation=allocation).first()
        self.assertIsNotNone(association)

    def test_request_does_not_create_duplicate_association(self):
        """Requesting twice should not create a second SlurmAssociation."""
        allocation = self._create_allocation(self.cluster, self.cluster_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()
        flow.request()  # second call — self-loop on STATUS_REQUESTED

        associations = SlurmAssociation.objects.filter(allocation=allocation)
        self.assertEqual(associations.count(), 1)

    def test_request_ignores_non_slurm_resource(self):
        """Requesting an allocation targeting a non-slurm resource should not create a SlurmAssociation."""
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

    def test_activate_does_not_modify_existing_slurm_user(self):
        """Activating should not modify an existing SlurmUser record."""
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

        # Alice's existing SlurmUser should still point to other_account
        alice_su = SlurmUser.objects.get(user=self.user1, cluster=self.cluster)
        self.assertEqual(alice_su.default_account, other_account)

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

    def test_activate_blocked_when_no_registered_permission_callback(self):
        """
        If no permission callback is registered, can_activate should return True
        and the transition should be allowed.
        """
        # Clear permission callbacks for this test
        AllocationStatusFlow._transition_permission_callbacks = {}

        allocation = self._create_allocation(self.cluster, self.cluster_ct)

        flow = AllocationStatusFlow(allocation)
        flow.request()  # creates SlurmAssociation without slurm_account
        flow.approve()

        # With no permission callbacks registered, has_perm should pass
        # (can_activate returns True since _check_permission_callbacks finds nothing)
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
        cls.user4 = User.objects.create(username="Diana")

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

    def test_project_user_created_creates_slurm_user_for_cluster(self):
        """Creating a ProjectUser on a project with an active slurm allocation
        should create a SlurmUser for that user on the cluster."""
        self._create_active_cluster_allocation(self.cluster1, self.project_a, self.account_a)

        ProjectUser.objects.create(project=self.project_a, user=self.user3)

        su = SlurmUser.objects.filter(user=self.user3, cluster=self.cluster1).first()
        self.assertIsNotNone(su)
        self.assertEqual(su.default_account, self.account_a)

    def test_project_user_created_creates_slurm_user_for_partition(self):
        """Creating a ProjectUser on a project with an active partition allocation
        should create a SlurmUser on the partition's cluster."""
        partition = SlurmPartition.objects.create(name="gpu", cluster=self.cluster1)
        self._create_active_partition_allocation(partition, self.project_a, self.account_a)

        ProjectUser.objects.create(project=self.project_a, user=self.user3)

        su = SlurmUser.objects.filter(user=self.user3, cluster=self.cluster1).first()
        self.assertIsNotNone(su)
        self.assertEqual(su.default_account, self.account_a)

    def test_project_user_created_ignores_non_slurm_allocation(self):
        """Creating a ProjectUser on a project with only non-slurm allocations
        should not create any SlurmUser."""
        resource = Resource.objects.create(
            name="Generic Storage",
            slug="s-1",
            resource_type=self.resource_type,
        )
        Allocation.objects.create(
            justification="Need storage",
            project=self.project_a,
            owner=self.user1,
            resource_object_type=self.resource_ct,
            resource_object_id=resource.pk,
            status=AllocationStatusChoices.STATUS_ACTIVE,
        )

        ProjectUser.objects.create(project=self.project_a, user=self.user3)

        self.assertFalse(SlurmUser.objects.filter(user=self.user3).exists())

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

    def test_project_user_deleted_removes_only_affected_users_slurm_user(self):
        """When a ProjectUser is deleted, other users' SlurmUser records
        should remain untouched."""
        # Add user1 as a member of project_a
        ProjectUser.objects.create(project=self.project_a, user=self.user1)
        self._create_active_cluster_allocation(self.cluster1, self.project_a, self.account_a)

        ProjectUser.objects.create(project=self.project_a, user=self.user3)
        self.assertTrue(SlurmUser.objects.filter(user=self.user3, cluster=self.cluster1).exists())
        self.assertTrue(SlurmUser.objects.filter(user=self.user1, cluster=self.cluster1).exists())

        pu = ProjectUser.objects.get(project=self.project_a, user=self.user3)
        pu.delete()

        self.assertFalse(SlurmUser.objects.filter(user=self.user3, cluster=self.cluster1).exists())
        self.assertTrue(SlurmUser.objects.filter(user=self.user1, cluster=self.cluster1).exists())

    def test_project_user_deleted_removes_all_slurm_users_when_no_projects(self):
        """When a user's last ProjectUser is deleted (they have no other
        projects), all their SlurmUser records should be removed."""
        self._create_active_cluster_allocation(self.cluster1, self.project_a, self.account_a)
        self._create_active_cluster_allocation(self.cluster2, self.project_a, self.account_b)

        ProjectUser.objects.create(project=self.project_a, user=self.user3)
        self.assertEqual(SlurmUser.objects.filter(user=self.user3).count(), 2)

        pu = ProjectUser.objects.get(project=self.project_a, user=self.user3)
        pu.delete()

        self.assertFalse(SlurmUser.objects.filter(user=self.user3).exists())


class SlurmAssociationSignalTest(TestCase):
    """Test the SlurmAssociation post_save signal handler."""

    @classmethod
    def setUpTestData(cls):
        # Users
        cls.user1 = User.objects.create(username="Alice")
        cls.user2 = User.objects.create(username="Bob")
        cls.user3 = User.objects.create(username="Charlie")

        # Project with members
        cls.project = Project.objects.create(name="Research Lab", owner=cls.user1)
        ProjectUser.objects.create(project=cls.project, user=cls.user1)
        ProjectUser.objects.create(project=cls.project, user=cls.user2)
        ProjectUser.objects.create(project=cls.project, user=cls.user3)

        # Slurm cluster and account
        cls.cluster = SlurmCluster.objects.create(name="hpc01")
        cls.account_a = SlurmAccount.objects.create(name="acct-a", cluster=cls.cluster)
        cls.account_b = SlurmAccount.objects.create(name="acct-b", cluster=cls.cluster)
        cls.account_c = SlurmAccount.objects.create(name="acct-c", cluster=cls.cluster)

        # Content types
        cls.cluster_ct = ContentType.objects.get_for_model(SlurmCluster)
        cls.resource_type = ResourceType.objects.create(name="Generic Resource")

    def _create_active_allocation(self):
        """Create an active allocation on the cluster with account_a."""
        allocation = Allocation.objects.create(
            justification="Need compute",
            project=self.project,
            owner=self.user1,
            resource_object_type=self.cluster_ct,
            resource_object_id=self.cluster.pk,
        )
        # SlurmAssociation is now created via the allocation form, not automatically.
        assoc = SlurmAssociation.objects.create(allocation=allocation)
        assoc.slurm_account = self.account_a
        assoc.save()
        flow = AllocationStatusFlow(allocation)
        flow.request()
        flow.approve()
        AllocationStatusFlow._transition_permission_callbacks = {}
        flow.activate()
        return allocation

    # ---------- SlurmAssociation account change on active allocation ----------

    def test_slurm_association_account_change_updates_slurm_users(self):
        """Changing slurm_account on an association for an active allocation
        should update the default_account on existing SlurmUser records."""
        allocation = self._create_active_allocation()

        # After activation, SlurmUser records exist with account_a
        su1 = SlurmUser.objects.get(user=self.user1, cluster=self.cluster)
        self.assertEqual(su1.default_account, self.account_a)

        # Admin changes the slurm_account on the association
        assoc = SlurmAssociation.objects.get(allocation=allocation)
        assoc.slurm_account = self.account_b
        assoc.save()

        # SlurmUser records should now have account_b
        su1 = SlurmUser.objects.get(user=self.user1, cluster=self.cluster)
        self.assertEqual(su1.default_account, self.account_b)

        su2 = SlurmUser.objects.get(user=self.user2, cluster=self.cluster)
        self.assertEqual(su2.default_account, self.account_b)

        su3 = SlurmUser.objects.get(user=self.user3, cluster=self.cluster)
        self.assertEqual(su3.default_account, self.account_b)

    def test_slurm_association_account_change_ignores_non_active_allocation(self):
        """Changing slurm_account on an association for a non-active allocation
        should not update SlurmUser records."""
        # Create a non-active allocation (STATUS_REQUESTED)
        allocation = Allocation.objects.create(
            justification="Pending",
            project=self.project,
            owner=self.user1,
            resource_object_type=self.cluster_ct,
            resource_object_id=self.cluster.pk,
            status=AllocationStatusChoices.STATUS_REQUESTED,
        )
        # SlurmAssociation is now created via the allocation form, not automatically.
        assoc = SlurmAssociation.objects.create(allocation=allocation)
        assoc.slurm_account = self.account_a
        assoc.save()

        # No SlurmUser records should exist yet (allocation is not active)
        self.assertFalse(SlurmUser.objects.filter(cluster=self.cluster).exists())

        # Now change the account — still no SlurmUser records
        assoc.slurm_account = self.account_b
        assoc.save()

        self.assertFalse(SlurmUser.objects.filter(cluster=self.cluster).exists())

    def test_slurm_association_account_change_noop_when_same_account(self):
        """Saving a SlurmAssociation with the same slurm_account should not
        trigger any updates."""
        allocation = self._create_active_allocation()

        su1 = SlurmUser.objects.get(user=self.user1, cluster=self.cluster)
        self.assertEqual(su1.default_account, self.account_a)

        # Save the association with the same account — no change
        assoc = SlurmAssociation.objects.get(allocation=allocation)
        assoc.save()  # no account change, just save

        # SlurmUser should still have account_a
        su1 = SlurmUser.objects.get(user=self.user1, cluster=self.cluster)
        self.assertEqual(su1.default_account, self.account_a)

    def test_slurm_association_account_change_ignores_non_slurm_resource(self):
        """Changing slurm_account on an association linked to a non-slurm
        allocation should be ignored (no SlurmUser records to update)."""
        resource = Resource.objects.create(
            name="Generic Storage",
            slug="s-1",
            resource_type=self.resource_type,
        )
        resource_ct = ContentType.objects.get_for_model(Resource)
        allocation = Allocation.objects.create(
            justification="Storage",
            project=self.project,
            owner=self.user1,
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
            status=AllocationStatusChoices.STATUS_ACTIVE,
        )
        # The on_allocation_created signal creates a SlurmAssociation even for
        # non-slurm resources? No — it checks isinstance(resource, (SlurmCluster, SlurmPartition))
        # So no association is created automatically. Create one manually.
        assoc = SlurmAssociation.objects.create(allocation=allocation, slurm_account=self.account_a)

        # Change the account
        assoc.slurm_account = self.account_b
        assoc.save()

        # No SlurmUser records should exist for this cluster
        self.assertFalse(SlurmUser.objects.filter(cluster=self.cluster).exists())

    def test_slurm_association_account_change_creates_missing_slurm_users(self):
        """If SlurmUser records don't exist yet (e.g., member added after
        activation but before account was set), changing the account should
        create them."""
        # Create active allocation but with no slurm_account set
        allocation = Allocation.objects.create(
            justification="Need compute",
            project=self.project,
            owner=self.user1,
            resource_object_type=self.cluster_ct,
            resource_object_id=self.cluster.pk,
        )
        # SlurmAssociation is now created via the allocation form, not automatically.
        assoc = SlurmAssociation.objects.create(allocation=allocation)
        flow = AllocationStatusFlow(allocation)
        flow.request()
        # Don't set slurm_account yet
        flow.approve()
        AllocationStatusFlow._transition_permission_callbacks = {}
        flow.activate()

        # No SlurmUser records because account is None
        self.assertFalse(SlurmUser.objects.filter(cluster=self.cluster).exists())

        # Admin sets the slurm_account
        assoc.slurm_account = self.account_a
        assoc.save()

        # SlurmUser records should now exist for all project members
        su1 = SlurmUser.objects.get(user=self.user1, cluster=self.cluster)
        self.assertEqual(su1.default_account, self.account_a)

        su2 = SlurmUser.objects.get(user=self.user2, cluster=self.cluster)
        self.assertEqual(su2.default_account, self.account_a)

        su3 = SlurmUser.objects.get(user=self.user3, cluster=self.cluster)
        self.assertEqual(su3.default_account, self.account_a)


class SlurmAccountValidationTest(TestCase):
    """Test SlurmAssociation.clean() account conflict validation."""

    @classmethod
    def setUpTestData(cls):
        cls.user1 = User.objects.create(username="Alice")
        cls.project = Project.objects.create(name="Research Lab", owner=cls.user1)

        cls.cluster_a = SlurmCluster.objects.create(name="hpc01")
        cls.cluster_b = SlurmCluster.objects.create(name="hpc02")
        cls.partition_gpu = SlurmPartition.objects.create(name="gpu", cluster=cls.cluster_a)
        cls.partition_cpu = SlurmPartition.objects.create(name="cpu", cluster=cls.cluster_a)
        cls.partition_gpu_b = SlurmPartition.objects.create(name="gpu", cluster=cls.cluster_b)

        cls.account_x = SlurmAccount.objects.create(name="acct-x", cluster=cls.cluster_a)
        cls.account_y = SlurmAccount.objects.create(name="acct-y", cluster=cls.cluster_a)

        cls.cluster_ct = ContentType.objects.get_for_model(SlurmCluster)
        cls.partition_ct = ContentType.objects.get_for_model(SlurmPartition)

    def _make_association(self, resource, resource_ct, account=None):
        """Create an allocation and its SlurmAssociation for a given resource.

        If account is provided, sets it on the association and saves.
        Otherwise the association is saved with slurm_account=None (default).
        """
        allocation = Allocation.objects.create(
            justification="test",
            project=self.project,
            owner=self.user1,
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
        )
        assoc = SlurmAssociation.objects.create(allocation=allocation)
        if account is not None:
            assoc.slurm_account = account
            assoc.save()
        return assoc

    # ---------- Same cluster, direct target ----------

    def test_same_cluster_same_account_direct_raises(self):
        """Two direct-to-cluster allocations on the same cluster with the
        same account should raise ValidationError."""
        self._make_association(self.cluster_a, self.cluster_ct, self.account_x)
        # assoc1 is saved — now try creating a second one
        assoc2 = self._make_association(self.cluster_a, self.cluster_ct)
        assoc2.slurm_account = self.account_x
        with self.assertRaises(ValidationError):
            assoc2.full_clean()

    def test_same_cluster_different_accounts_direct_ok(self):
        """Two direct-to-cluster allocations on the same cluster with
        different accounts should be allowed."""
        self._make_association(self.cluster_a, self.cluster_ct, self.account_x)
        assoc2 = self._make_association(self.cluster_a, self.cluster_ct)
        assoc2.slurm_account = self.account_y
        # Should not raise
        assoc2.full_clean()

    def test_different_clusters_same_account_direct_ok(self):
        """Two direct-to-cluster allocations on different clusters with the
        same account should be allowed."""
        self._make_association(self.cluster_a, self.cluster_ct, self.account_x)
        assoc2 = self._make_association(self.cluster_b, self.cluster_ct)
        assoc2.slurm_account = self.account_x
        # Should not raise (different clusters)
        assoc2.full_clean()

    # ---------- Same partition ----------

    def test_same_partition_same_account_raises(self):
        """Two allocations targeting the same partition with the same
        account should raise ValidationError."""
        self._make_association(self.partition_gpu, self.partition_ct, self.account_x)
        assoc2 = self._make_association(self.partition_gpu, self.partition_ct)
        assoc2.slurm_account = self.account_x
        with self.assertRaises(ValidationError):
            assoc2.full_clean()

    def test_same_partition_different_accounts_ok(self):
        """Two allocations targeting the same partition with different
        accounts should be allowed."""
        self._make_association(self.partition_gpu, self.partition_ct, self.account_x)
        assoc2 = self._make_association(self.partition_gpu, self.partition_ct)
        assoc2.slurm_account = self.account_y
        assoc2.full_clean()

    def test_different_partitions_same_account_ok(self):
        """Two allocations on different partitions with the same account
        should be allowed (different partition values)."""
        self._make_association(self.partition_gpu, self.partition_ct, self.account_x)
        assoc2 = self._make_association(self.partition_cpu, self.partition_ct)
        assoc2.slurm_account = self.account_x
        assoc2.full_clean()

    def test_same_partition_different_clusters_same_account_ok(self):
        """Two allocations targeting 'gpu' on different clusters with the
        same account should be allowed."""
        self._make_association(self.partition_gpu, self.partition_ct, self.account_x)
        # partition_gpu_b is 'gpu' on cluster_b
        assoc2 = self._make_association(self.partition_gpu_b, self.partition_ct)
        assoc2.slurm_account = self.account_x
        assoc2.full_clean()

    # ---------- Mixed: direct vs partition ----------

    def test_one_direct_one_partition_same_account_ok(self):
        """One direct-to-cluster and one partition-specific allocation with
        the same account should be allowed (partition='' vs partition='<name>')."""
        self._make_association(self.cluster_a, self.cluster_ct, self.account_x)
        assoc2 = self._make_association(self.partition_gpu, self.partition_ct)
        assoc2.slurm_account = self.account_x
        assoc2.full_clean()

    # ---------- Edge cases ----------

    def test_null_account_skips_validation(self):
        """Setting slurm_account to None should skip validation."""
        self._make_association(self.cluster_a, self.cluster_ct, self.account_x)
        assoc2 = self._make_association(self.cluster_a, self.cluster_ct)
        # Leave slurm_account as None
        assoc2.full_clean()  # should not raise

    def test_update_self_no_conflict(self):
        """Updating an association should not flag itself as a conflict."""
        assoc = self._make_association(self.cluster_a, self.cluster_ct, self.account_x)
        # Re-save with the same account — should not raise
        assoc.full_clean()
        # Change to a different account — should not raise
        assoc.slurm_account = self.account_y
        assoc.full_clean()
