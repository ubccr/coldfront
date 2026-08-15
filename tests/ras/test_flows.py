# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase
from django.utils import timezone

from coldfront.ras.choices import AllocationChangeRequestStatusChoices, AllocationStatusChoices
from coldfront.ras.flows import AllocationStatusFlow
from coldfront.ras.flows.change_requests import AllocationChangeRequestFlow
from coldfront.ras.models import (
    Allocation,
    AllocationChangeRequest,
    Project,
    Resource,
    ResourceType,
)
from coldfront.users.models import User


class AllocationStatusFlowTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="User1")
        project = Project.objects.create(name="Project 1", owner=user)
        resource_type = ResourceType.objects.create(name="Cluster")
        resource = Resource.objects.create(name="Resource 1", slug="r-1", resource_type=resource_type)
        resource_ct = ContentType.objects.get_for_model(Resource)
        Allocation.objects.create(
            justification="Need resources 1",
            project=project,
            owner=user,
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
        )

    def test_allocation_status_flow(self):
        allocation = Allocation.objects.first()
        flow = AllocationStatusFlow(allocation)

        flow.request()
        self.assertEqual(allocation.status, AllocationStatusChoices.STATUS_REQUESTED)

        flow.approve()
        self.assertEqual(allocation.status, AllocationStatusChoices.STATUS_APPROVED)

        self.assertEqual(
            [
                (transition.target, transition.slug)
                for transition in AllocationStatusFlow.status.get_outgoing_transitions(allocation.status)
            ],
            [(AllocationStatusChoices.STATUS_ACTIVE, "activate")],
        )

        flow.activate()
        self.assertEqual(allocation.status, AllocationStatusChoices.STATUS_ACTIVE)

        self.assertEqual(
            [
                (transition.target, transition.slug)
                for transition in AllocationStatusFlow.status.get_outgoing_transitions(allocation.status)
            ],
            [
                (AllocationStatusChoices.STATUS_EXPIRED, "expire"),
                (AllocationStatusChoices.STATUS_RENEW, "renew"),
                (AllocationStatusChoices.STATUS_REVOKED, "revoke"),
            ],
        )

        flow.expire()
        self.assertEqual(allocation.status, AllocationStatusChoices.STATUS_EXPIRED)

        self.assertEqual(
            [
                (transition.target, transition.slug)
                for transition in AllocationStatusFlow.status.get_outgoing_transitions(allocation.status)
            ],
            [(AllocationStatusChoices.STATUS_RENEW, "renew")],
        )


class AllocationChangeRequestFlowTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="test_user")
        resource_type = ResourceType.objects.create(name="Cluster", slug="cluster")
        resource = Resource.objects.create(name="Resource 1", slug="r-1", resource_type=resource_type)
        resource_ct = ContentType.objects.get_for_model(Resource)
        project = Project.objects.create(name="Project 1", owner=user)
        now = timezone.now()
        cls.allocation = Allocation.objects.create(
            justification="Need resources",
            project=project,
            owner=user,
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
            status=AllocationStatusChoices.STATUS_ACTIVE,
            start_date=now,
            end_date=now + timedelta(days=30),
        )
        cls.change_request = AllocationChangeRequest.objects.create(
            allocation=cls.allocation,
            requested_by=user,
            justification="Need more resources",
            extension_days=30,
        )
        cls.flow = AllocationChangeRequestFlow(cls.change_request)

    def test_initial_state(self):
        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_REQUESTED,
        )

    def test_approve_transition(self):
        self.flow.approve()
        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_APPROVED,
        )

    def test_deny_transition(self):
        self.flow.deny()
        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_DENIED,
        )

    def test_apply_requires_approved_first(self):
        # Trying to apply from requested state should fail
        with self.assertRaises(Exception):
            self.flow.apply()

    def test_apply_transition(self):
        # First approve
        self.flow.approve()
        # Then apply
        self.flow.apply()
        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_APPLIED,
        )
        # Verify extension_days was applied
        self.allocation.refresh_from_db()
        expected_end = self.allocation.start_date + timedelta(days=60)
        self.assertEqual(self.allocation.end_date, expected_end)

    def test_apply_with_attribute_changes(self):
        """
        Apply a change request with attribute_changes.
        Verify attribute_data is updated and snapshot_attribute_values is captured.
        """
        # Set attribute changes on the change request
        self.change_request.attribute_changes = {"gpu": "H100", "memory": 8192}
        self.change_request.save()

        # First approve
        self.flow.approve()

        # Set allocation attribute_data (simulating current values)
        self.allocation.attribute_data = {"gpu": "A100", "memory": 4096}
        self.allocation.save()

        # Then apply
        self.flow.apply()

        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_APPLIED,
        )
        # Verify snapshot was captured
        self.assertIsNotNone(self.change_request.snapshot_attribute_values)
        self.assertEqual(self.change_request.snapshot_attribute_values["gpu"], "A100")
        self.assertEqual(self.change_request.snapshot_attribute_values["memory"], 4096)

    def test_apply_with_extension_changes(self):
        """
        Apply a change request with extension_changes.
        Verify extension instance is updated and snapshot_extension_values is captured.
        """
        from coldfront.storage.models import StorageQuota, StorageResource
        from coldfront.users.models import Group

        # Create a storage resource and extension for the allocation
        storage_resource = StorageResource.objects.create(name="Flow-Storage")
        group = Group.objects.create(name="flow-group")
        StorageQuota.objects.create(
            allocation=self.allocation,
            storage=storage_resource,
            path=f"/home/groups/flow/{self.allocation.id}",
            owning_user=self.allocation.owner,
            owning_group=group,
            hard_limit_bytes=100,
            soft_limit_bytes=50,
        )

        # Set extension_changes on the change request
        self.change_request.extension_changes = {
            "storage.StorageQuota": {
                "hard_limit_bytes": 200,
            }
        }
        self.change_request.save()

        # Approve then apply
        self.flow.approve()
        self.flow.apply()

        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_APPLIED,
        )
        # Verify extension instance was updated
        ext = StorageQuota.objects.get(allocation=self.allocation)
        self.assertEqual(ext.hard_limit_bytes, 200)
        self.assertEqual(ext.soft_limit_bytes, 50)
        # Verify snapshot was captured
        self.assertIsNotNone(self.change_request.snapshot_extension_values)
        self.assertIn("storage.StorageQuota", self.change_request.snapshot_extension_values)
        self.assertEqual(
            self.change_request.snapshot_extension_values["storage.StorageQuota"]["hard_limit_bytes"],
            100,
        )

    def test_apply_with_invalid_attribute_changes(self):
        """
        Apply a change request with attribute_changes that don't match the
        resource schema — verify a ValidationError is raised and the flow
        is aborted.
        """
        # Create a new allocation whose resource has a JSON schema
        user = User.objects.create(username="schema_user")
        resource_type = ResourceType.objects.create(name="Schema Type", slug="schema-type")
        resource = Resource.objects.create(
            name="Schema Resource",
            slug="schema-resource",
            resource_type=resource_type,
            schema={
                "properties": {
                    "memory": {"title": "Memory (MB)", "type": "integer"},
                },
                "required": ["memory"],
                "additionalProperties": False,
            },
        )
        resource_ct = ContentType.objects.get_for_model(Resource)
        project = Project.objects.create(name="Schema Project", owner=user)
        now = timezone.now()
        allocation = Allocation.objects.create(
            justification="Schema test",
            project=project,
            owner=user,
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
            status=AllocationStatusChoices.STATUS_ACTIVE,
            start_date=now,
            end_date=now + timedelta(days=30),
            attribute_data={"memory": 2048},
        )
        change_request = AllocationChangeRequest.objects.create(
            allocation=allocation,
            requested_by=user,
            justification="Invalid attribute test",
            attribute_changes={"nonexistent_field": "value"},
        )
        flow = AllocationChangeRequestFlow(change_request)

        # Approve first
        flow.approve()

        # Applying should raise an error due to schema validation
        with self.assertRaises(Exception):
            flow.apply()
