# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from coldfront.core.choices import CommentKindChoices
from coldfront.core.models import CommentEntry
from coldfront.ras.choices import AllocationChangeRequestStatusChoices, AllocationStatusChoices, ResourceStatusChoices
from coldfront.ras.models import (
    Allocation,
    Project,
    ProjectUser,
    Resource,
    ResourceType,
)
from coldfront.ras.models.change_requests import (
    AllocationChangeRequest,
)
from coldfront.tenancy.models import Tenant
from coldfront.users.models import User
from coldfront.utils.testing import ViewTestCases, create_tags
from coldfront.utils.testing.utils import disable_warnings
from coldfront.utils.testing.views import ModelViewTestCase


class ProjectTestCase(ViewTestCases.OrganizationalObjectViewTestCase):
    model = Project

    @classmethod
    def setUpTestData(cls):

        users = (
            User(username="User1"),
            User(username="User2"),
            User(username="User3"),
        )
        for user in users:
            user.save()

        projects = (
            Project(name="Project 1", owner=users[0]),
            Project(name="Project 2", owner=users[1]),
            Project(name="Project 3", owner=users[2]),
        )
        for project in projects:
            project.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "name": "Project X",
            "description": "A new project",
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "name,description,owner",
            "Project 4,Fourth project,User1",
            "Project 5,Fifth project,User2",
            "Project 6,Sixth project,User3",
        )

        cls.csv_update_data = (
            "id,name,description",
            f"{projects[0].pk},Project 7,Fourth project7",
            f"{projects[1].pk},Project 8,Fifth project8",
            f"{projects[2].pk},Project 9,Sixth project9",
        )

        cls.bulk_edit_form_data = {
            "description": "Updated project",
        }

    def test_tenant_validation_enforced(self):
        """
        Test that editing a tenant on a project is restricted.
        """
        tenant = Tenant.objects.create(name="Tenant 1")

        self.add_permissions("ras.add_project")
        data = {
            "name": "Project X",
            "description": "A new project",
            "tenant": tenant.pk,
        }

        request = {
            "path": self._get_url("add"),
            "data": data,
        }

        # No perms
        response = self.client.post(**request)
        self.assertHttpStatus(response, 200)

        # With perms
        self.add_permissions("tenancy.view_tenant")
        response = self.client.post(**request)
        self.assertHttpStatus(response, 302)


class ResourceTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Resource

    @classmethod
    def setUpTestData(cls):

        resource_type = ResourceType.objects.create(name="Cluster")

        resources = (
            Resource(name="Resource 1", slug="r-1", resource_type=resource_type),
            Resource(name="Resource 2", slug="r-2", resource_type=resource_type),
            Resource(name="Resource 3", slug="r-3", resource_type=resource_type),
        )
        for resource in resources:
            resource.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "name": "Resource X",
            "slug": "r-x",
            "description": "A new resource",
            "resource_type": resource_type.pk,
            "status": ResourceStatusChoices.STATUS_ACTIVE,
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "name,slug,description,status,resource_type",
            "Resource 4,r-4,Fourth resource,active,Cluster",
            "Resource 5,r-5,Fifth resource,active,Cluster",
            "Resource 6,r-6,Sixth resource,active,Cluster",
        )

        cls.csv_update_data = (
            "id,name,description",
            f"{resources[0].pk},Resource 7,Seven resource7",
            f"{resources[1].pk},Resource 8,Eight resource8",
            f"{resources[2].pk},Resource 9,Nine resource9",
        )

        cls.bulk_edit_form_data = {
            "description": "Updated resource",
            "locked": True,
        }


class AllocationTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = Allocation
    validation_excluded_fields = ("resource_object",)

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="User1")
        project = Project.objects.create(name="Project 1", owner=user)
        resource_type = ResourceType.objects.create(name="Cluster")

        resources = (
            Resource(name="Resource 1", slug="r-1", resource_type=resource_type),
            Resource(name="Resource 2", slug="r-2", resource_type=resource_type),
            Resource(name="Resource 3", slug="r-3", resource_type=resource_type),
        )
        for resource in resources:
            resource.save()

        resource_ct = ContentType.objects.get_for_model(Resource)
        allocations = (
            Allocation(
                justification="Need resources 1",
                project=project,
                owner=user,
                resource_object_type=resource_ct,
                resource_object_id=resources[0].pk,
            ),
            Allocation(
                justification="Need resources 2",
                project=project,
                owner=user,
                resource_object_type=resource_ct,
                resource_object_id=resources[1].pk,
            ),
            Allocation(
                justification="Need resources 3",
                project=project,
                owner=user,
                resource_object_type=resource_ct,
                resource_object_id=resources[2].pk,
            ),
        )
        for allocation in allocations:
            allocation.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        resource_ct = ContentType.objects.get_for_model(Resource)
        cls.form_data = {
            "justification": "Need resources X",
            "description": "A new Allocation",
            "owner": user.pk,
            "project": project.pk,
            "resource_object": f"{resource_ct.pk}:{resources[0].pk}",
            "status": AllocationStatusChoices.STATUS_REQUESTED,
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "justification,description,status,owner,project,resource_object",
            "need resources4,Fourth allocation,active,User1,Project 1,ras.resource:Resource 1",
            "need resources5,Fifth allocation,active,User1,Project 1,ras.resource:Resource 2",
            "need resources6,Sixth allocation,active,User1,Project 1,ras.resource:Resource 3",
        )

        cls.csv_update_data = (
            "id,description",
            f"{allocations[0].pk},Fourth allocation7",
            f"{allocations[1].pk},Fifth allocation8",
            f"{allocations[2].pk},Sixth allocation9",
        )

        cls.bulk_edit_form_data = {
            "description": "Updated allocation",
        }


class ProjectUserTestCase(ViewTestCases.PrimaryObjectViewTestCase):
    model = ProjectUser

    @classmethod
    def setUpTestData(cls):
        owner = User.objects.create(username="pi")
        users = (
            User(username="User1"),
            User(username="User2"),
            User(username="User3"),
        )
        for user in users:
            user.save()

        projects = (
            Project(name="Project 1", owner=owner),
            Project(name="Project 2", owner=owner),
            Project(name="Project 3", owner=owner),
            Project(name="Project 4", owner=owner),
        )
        for project in projects:
            project.save()

        project_users = (
            ProjectUser(user=users[0], project=projects[0]),
            ProjectUser(user=users[1], project=projects[0]),
            ProjectUser(user=users[2], project=projects[0]),
        )
        for pu in project_users:
            pu.save()

        cls.form_data = {
            "project": projects[1].pk,
            "user": users[0].pk,
        }

        cls.csv_data = (
            "user,project",
            "User1,Project 3",
            "User2,Project 3",
            "User3,Project 3",
        )

        cls.csv_update_data = (
            "id,project",
            f"{project_users[0].pk},Project 4",
            f"{project_users[1].pk},Project 4",
            f"{project_users[2].pk},Project 4",
        )

        cls.bulk_edit_form_data = {
            "project": projects[2].pk,
        }


class AllocationChangeRequestTestCase(
    ViewTestCases.GetObjectViewTestCase,
    ViewTestCases.GetObjectChangelogViewTestCase,
    ViewTestCases.DeleteObjectViewTestCase,
    ViewTestCases.ListObjectsViewTestCase,
):
    # Create/Edit/Bulk operations are not tested via standard patterns because
    # AllocationChangeRequestForm dynamically adds fields based on the allocation.
    model = AllocationChangeRequest
    validation_excluded_fields = ("slug", "status", "requested_by", "reviewer", "tags")

    def setUp(self):
        super().setUp()
        # Need view_allocation to see allocations in the form dropdown
        self.add_permissions("ras.view_allocation")

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="User1")
        project = Project.objects.create(name="Project 1", owner=user)
        resource_type = ResourceType.objects.create(name="Cluster", slug="cluster")

        resources = (
            Resource(name="Resource 1", slug="r-1", resource_type=resource_type),
            Resource(name="Resource 2", slug="r-2", resource_type=resource_type),
            Resource(name="Resource 3", slug="r-3", resource_type=resource_type),
        )
        for resource in resources:
            resource.save()

        resource_ct = ContentType.objects.get_for_model(Resource)
        now = timezone.now()

        allocations = (
            Allocation(
                justification="Need resources 1",
                project=project,
                owner=user,
                resource_object_type=resource_ct,
                resource_object_id=resources[0].pk,
                status=AllocationStatusChoices.STATUS_ACTIVE,
                start_date=now,
                end_date=now + timedelta(days=30),
            ),
            Allocation(
                justification="Need resources 2",
                project=project,
                owner=user,
                resource_object_type=resource_ct,
                resource_object_id=resources[1].pk,
                status=AllocationStatusChoices.STATUS_ACTIVE,
                start_date=now,
                end_date=now + timedelta(days=30),
            ),
            Allocation(
                justification="Need resources 3",
                project=project,
                owner=user,
                resource_object_type=resource_ct,
                resource_object_id=resources[2].pk,
                status=AllocationStatusChoices.STATUS_ACTIVE,
                start_date=now,
                end_date=now + timedelta(days=30),
            ),
        )
        for allocation in allocations:
            allocation.save()

        # Create pre-existing AllocationChangeRequest instances for edit/delete/list tests
        change_requests = (
            AllocationChangeRequest(
                allocation=allocations[0],
                requested_by=user,
                justification="Change 1",
                extension_days=30,
            ),
            AllocationChangeRequest(
                allocation=allocations[1],
                requested_by=user,
                justification="Change 2",
                extension_days=60,
            ),
            AllocationChangeRequest(
                allocation=allocations[2],
                requested_by=user,
                justification="Change 3",
                extension_days=90,
            ),
        )
        for cr in change_requests:
            cr.save()

        tags = create_tags("Alpha", "Bravo", "Charlie")

        cls.form_data = {
            "allocation": allocations[0].pk,
            "justification": "Need more resources",
            "extension_days": 30,
            "tags": [t.pk for t in tags],
        }

        cls.csv_data = (
            "allocation,justification,extension_days",
            f"{allocations[0].slug},Fourth change,30",
            f"{allocations[1].slug},Fifth change,60",
            f"{allocations[2].slug},Sixth change,90",
        )

        cls.csv_update_data = (
            "id,justification",
            f"{change_requests[0].pk},Updated change",
            f"{change_requests[1].pk},Updated change",
            f"{change_requests[2].pk},Updated change",
        )

        cls.bulk_edit_form_data = {
            "justification": "Bulk updated justification",
        }


class AllocationChangeRequestFlowViewTestCase(ModelViewTestCase):
    """Test the flow action views (approve, deny, apply) for AllocationChangeRequest."""

    model = AllocationChangeRequest

    @classmethod
    def setUpTestData(cls):
        # Use a different username than "testuser" (created in setUp) to avoid conflicts
        cls.test_user = User.objects.create(username="flow_user")
        cls.reviewer = User.objects.create(username="reviewer")

        resource_type = ResourceType.objects.create(name="Cluster", slug="cluster")
        resource = Resource.objects.create(name="Resource 1", slug="r-1", resource_type=resource_type)
        resource_ct = ContentType.objects.get_for_model(Resource)

        project = Project.objects.create(name="Project 1", owner=cls.test_user)
        now = timezone.now()
        cls.allocation = Allocation.objects.create(
            justification="Need resources",
            project=project,
            owner=cls.test_user,
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
            status=AllocationStatusChoices.STATUS_ACTIVE,
            start_date=now,
            end_date=now + timedelta(days=30),
        )

        cls.change_request = AllocationChangeRequest.objects.create(
            allocation=cls.allocation,
            requested_by=cls.test_user,
            justification="Need more resources",
            extension_days=30,
        )

    def setUp(self):
        super().setUp()
        # Grant view permission so flow views are accessible
        self.add_permissions(
            "ras.view_allocationchangerequest",
            "ras.view_allocation",
        )
        # Compute URLs per-instance (needed because _get_url requires an instance)
        self.approve_url = self._get_url("approve", self.change_request)
        self.deny_url = self._get_url("deny", self.change_request)
        self.apply_url = self._get_url("apply", self.change_request)

    def test_approve_view_get_without_permission(self):
        """GET the approve view without approve permission."""
        with disable_warnings("django.request"):
            self.assertHttpStatus(self.client.get(self.approve_url), 403)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
    def test_approve_view_get_with_permission(self):
        """GET the approve view with permission."""
        self.add_permissions("ras.approve_allocationchangerequest")
        self.assertHttpStatus(self.client.get(self.approve_url), 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
    def test_approve_view_post(self):
        """POST to approve a change request."""
        self.add_permissions("ras.approve_allocationchangerequest")

        data = {"comments": "Approved!"}
        response = self.client.post(self.approve_url, data)
        self.assertHttpStatus(response, 302)

        self.change_request.refresh_from_db()
        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_APPROVED,
        )

        # Verify comment was created
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(self.change_request)
        comments = CommentEntry.objects.filter(
            assigned_object_type=ct,
            assigned_object_id=self.change_request.pk,
            kind=CommentKindChoices.KIND_INFO,
        )
        self.assertEqual(len(comments), 1)
        self.assertIn("Approved!", str(comments[0].comments))

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
    def test_deny_view_get_with_permission(self):
        """GET the deny view with permission."""
        self.add_permissions("ras.deny_allocationchangerequest")
        self.assertHttpStatus(self.client.get(self.deny_url), 200)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
    def test_deny_view_post(self):
        """POST to deny a change request."""
        self.add_permissions("ras.deny_allocationchangerequest")

        data = {"comments": "Denied because..."}
        response = self.client.post(self.deny_url, data)
        self.assertHttpStatus(response, 302)

        self.change_request.refresh_from_db()
        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_DENIED,
        )

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
    def test_apply_view_requires_approved_first(self):
        """Applying from requested state should fail."""
        self.add_permissions("ras.apply_allocationchangerequest")

        data = {"comments": "Applying"}
        response = self.client.post(self.apply_url, data)
        # Should return error because apply is only valid from approved state
        self.assertHttpStatus(response, 403)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
    def test_apply_view_post(self):
        """POST to apply an approved change request."""
        # First approve
        self.add_permissions(
            "ras.approve_allocationchangerequest",
            "ras.apply_allocationchangerequest",
        )
        self.client.post(self.approve_url, {"comments": "Approved"})

        self.change_request.refresh_from_db()
        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_APPROVED,
        )

        # Now apply
        response = self.client.post(self.apply_url, {"comments": "Applied!"})
        self.assertHttpStatus(response, 302)

        self.change_request.refresh_from_db()
        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_APPLIED,
        )

        # Verify comment was created
        from django.contrib.contenttypes.models import ContentType

        ct = ContentType.objects.get_for_model(self.change_request)
        comments = CommentEntry.objects.filter(
            assigned_object_type=ct,
            assigned_object_id=self.change_request.pk,
            kind=CommentKindChoices.KIND_INFO,
        )
        self.assertEqual(len(comments), 2)  # approve comment + apply comment

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
    def test_full_workflow_via_views(self):
        """Test the full approve → apply workflow through the view layer."""
        self.add_permissions(
            "ras.approve_allocationchangerequest",
            "ras.apply_allocationchangerequest",
        )

        # Approve
        self.client.post(self.approve_url, {"comments": "Looks good"})
        self.change_request.refresh_from_db()
        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_APPROVED,
        )

        # Apply
        self.client.post(self.apply_url, {"comments": "Applied changes"})
        self.change_request.refresh_from_db()
        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_APPLIED,
        )

        # Verify allocation was updated (extension of 30 days)
        self.allocation.refresh_from_db()
        expected_end = self.allocation.start_date + timedelta(days=60)
        self.assertEqual(self.allocation.end_date, expected_end)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
    def test_reviewer_set_on_approve(self):
        """Verify reviewer is set to the approving user."""
        self.add_permissions("ras.approve_allocationchangerequest")
        self.client.post(self.approve_url, {"comments": "Approved"})
        self.change_request.refresh_from_db()
        self.assertEqual(self.change_request.reviewer.pk, self.user.pk)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
    def test_reviewer_set_on_deny(self):
        """Verify reviewer is set to the denying user."""
        self.add_permissions("ras.deny_allocationchangerequest")
        self.client.post(self.deny_url, {"comments": "Denied"})
        self.change_request.refresh_from_db()
        self.assertEqual(self.change_request.reviewer.pk, self.user.pk)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
    def test_apply_with_attribute_changes(self):
        """
        Apply a change request with attribute_changes.
        Verify attribute_data is updated and snapshot_attribute_values is captured.
        """
        # Create a change request with attribute_changes
        self.change_request.attribute_changes = {"gpu": "H100", "memory": 8192}
        self.change_request.save()

        # First approve
        self.add_permissions("ras.approve_allocationchangerequest")
        self.client.post(self.approve_url, {"comments": "Approved"})

        # Now apply
        self.add_permissions("ras.apply_allocationchangerequest")
        self.client.post(self.apply_url, {"comments": "Applied"})

        self.change_request.refresh_from_db()
        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_APPLIED,
        )
        # Verify snapshot was captured
        self.assertIsNotNone(self.change_request.snapshot_attribute_values)

    @override_settings(EXEMPT_VIEW_PERMISSIONS=["*"], EXEMPT_EXCLUDE_MODELS=[])
    def test_apply_with_extension_changes(self):
        """
        Apply a change request with extension_changes.
        Verify extension instance is updated and snapshot_extension_values is captured.
        """
        from coldfront.storage.models import StorageQuota, StorageResource
        from coldfront.users.models import Group

        # First create a StorageResource and StorageQuota extension instance
        storage_resource = StorageResource.objects.create(name="Flow-Storage")
        group = Group.objects.create(name="ext-group")
        ext = StorageQuota.objects.create(
            allocation=self.allocation,
            storage=storage_resource,
            path=f"/home/groups/test/{self.allocation.id}",
            owning_user=self.test_user,
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

        # Approve
        self.add_permissions("ras.approve_allocationchangerequest")
        self.client.post(self.approve_url, {"comments": "Approved"})

        # Apply
        self.add_permissions("ras.apply_allocationchangerequest")
        self.client.post(self.apply_url, {"comments": "Applied"})

        self.change_request.refresh_from_db()
        self.assertEqual(
            self.change_request.status,
            AllocationChangeRequestStatusChoices.STATUS_APPLIED,
        )
        # Verify extension instance was updated
        ext.refresh_from_db()
        self.assertEqual(ext.hard_limit_bytes, 200)
        self.assertEqual(ext.soft_limit_bytes, 50)
        # Verify snapshot was captured
        self.assertIsNotNone(self.change_request.snapshot_extension_values)


class AllocationExtensionViewTest(ModelViewTestCase):
    """Test that allocation extensions are created and displayed correctly."""

    model = AllocationChangeRequest

    @classmethod
    def setUpTestData(cls):
        cls.test_user = User.objects.create(username="ext_user")
        from coldfront.storage.models import StorageResource

        cls.storage_resource = StorageResource.objects.create(name="Storage-1")
        storage_ct = ContentType.objects.get_for_model(StorageResource)
        project = Project.objects.create(name="Project Ext", owner=cls.test_user)
        now = timezone.now()
        cls.allocation = Allocation.objects.create(
            justification="Need storage",
            project=project,
            owner=cls.test_user,
            resource_object_type=storage_ct,
            resource_object_id=cls.storage_resource.pk,
            status=AllocationStatusChoices.STATUS_ACTIVE,
            start_date=now,
            end_date=now + timedelta(days=30),
        )

    def setUp(self):
        super().setUp()
        self.add_permissions(
            "ras.view_allocationchangerequest",
            "ras.view_allocation",
            "ras.add_allocationchangerequest",
            "ras.approve_allocationchangerequest",
            "ras.apply_allocationchangerequest",
            "storage.view_storagequota",
            "storage.add_storagequota",
        )

    def test_change_request_with_extension_changes(self):
        """
        Create a change request that includes extension_changes for
        StorageQuota, then apply it.
        """
        from coldfront.storage.models import StorageQuota

        # First create an extension
        from coldfront.users.models import Group

        group = Group.objects.create(name="ext-group")
        StorageQuota.objects.create(
            allocation=self.allocation,
            storage=self.storage_resource,
            path=f"/home/groups/test/{self.allocation.id}",
            owning_user=self.test_user,
            owning_group=group,
            hard_limit_bytes=100,
            soft_limit_bytes=50,
        )

        # Create a change request with extension_changes via the form
        add_url = self._get_url("add")
        response = self.client.post(
            add_url,
            {
                "allocation": self.allocation.pk,
                "justification": "Increase quota",
                "extension_days": 30,
                "ext_storagequota_hard_limit_bytes": 200,
                "ext_storagequota_soft_limit_bytes": 75,
            },
        )
        self.assertHttpStatus(response, 302)
        cr = AllocationChangeRequest.objects.get(
            allocation=self.allocation,
            justification="Increase quota",
        )
        self.assertEqual(cr.extension_days, 30)
        self.assertIn("storage.storagequota", cr.extension_changes)
        self.assertEqual(cr.extension_changes["storage.storagequota"]["hard_limit_bytes"], 200)

        # Approve and apply
        approve_url = self._get_url("approve", cr)
        self.client.post(approve_url, {"comments": "Approved"})
        apply_url = self._get_url("apply", cr)
        self.client.post(apply_url, {"comments": "Applied"})

        # Verify end_date was extended
        self.allocation.refresh_from_db()
        expected_end = self.allocation.start_date + timedelta(days=60)
        self.assertEqual(self.allocation.end_date, expected_end)

        # Verify extension values were applied to the live instance
        ext = StorageQuota.objects.get(allocation=self.allocation)
        self.assertEqual(ext.hard_limit_bytes, 200)
        self.assertEqual(ext.soft_limit_bytes, 50)

        # Verify snapshot was captured at apply time
        cr.refresh_from_db()
        self.assertIn("storage.storagequota", cr.snapshot_extension_values)
        self.assertEqual(cr.snapshot_extension_values["storage.storagequota"]["hard_limit_bytes"], 100)
        self.assertEqual(cr.snapshot_extension_values["storage.storagequota"]["soft_limit_bytes"], 50)

    def test_extension_detail_display(self):
        """
        Verify the change request detail view includes extension_change_sets.
        """
        from coldfront.storage.models import StorageQuota, StorageResource
        from coldfront.users.models import Group

        storage_resource = StorageResource.objects.first()
        if not storage_resource:
            storage_resource = StorageResource.objects.create(name="Storage-Ext3")
        group = Group.objects.create(name="ext-group3")
        StorageQuota.objects.create(
            allocation=self.allocation,
            storage=storage_resource,
            path=f"/home/groups/test/{self.allocation.id}",
            owning_user=self.test_user,
            owning_group=group,
            hard_limit_bytes=100,
            soft_limit_bytes=50,
        )

        cr = AllocationChangeRequest.objects.create(
            allocation=self.allocation,
            requested_by=self.test_user,
            justification="Test extension display",
            extension_days=15,
            extension_changes={
                "storage.StorageQuota": {
                    "hard_limit_bytes": 200,
                    "soft_limit_bytes": 75,
                }
            },
        )

        # Verify extension_changes is stored properly
        cr.refresh_from_db()
        self.assertIn("storage.StorageQuota", cr.extension_changes)
        self.assertEqual(cr.extension_changes["storage.StorageQuota"]["hard_limit_bytes"], 200)

        # Verify extension instance exists
        from coldfront.storage.models import StorageQuota

        ext = StorageQuota.objects.get(allocation=self.allocation)
        self.assertEqual(ext.hard_limit_bytes, 100)

        detail_url = reverse("ras:allocationchangerequest", kwargs={"pk": cr.pk})
        response = self.client.get(detail_url)
        self.assertHttpStatus(response, 200)
        # The template should render without errors
        self.assertContains(response, "Current Values")
        self.assertContains(response, "Requested Changes")
        # Extension values should appear in the diff
        self.assertContains(response, "hard_limit_bytes")


class AllocationWithSchemaAttributesTest(ModelViewTestCase):
    """
    Test that allocations with a resource that has a JSON schema
    properly show attribute fields on the edit form and save attribute_data.
    """

    model = Allocation

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="User1")
        project = Project.objects.create(name="Project 1", owner=user)
        resource_type = ResourceType.objects.create(name="Cluster")
        resource = Resource.objects.create(
            name="Resource with schema",
            slug="r-schema",
            resource_type=resource_type,
            schema={
                "properties": {
                    "gpu": {"title": "GPU", "type": "string"},
                    "memory": {"title": "Memory (MB)", "type": "integer"},
                },
                "required": ["memory"],
            },
        )
        resource_ct = ContentType.objects.get_for_model(Resource)
        cls.allocation = Allocation.objects.create(
            justification="Need resources",
            project=project,
            owner=user,
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
            attribute_data={"gpu": "A100", "memory": 4096},
        )
        cls.resource = resource
        cls.user = user
        cls.project = project

    def setUp(self):
        super().setUp()
        self.add_permissions(
            "ras.view_allocation",
            "ras.add_allocation",
            "ras.change_allocation",
            "ras.view_resource",
            "ras.view_project",
            "users.view_user",
        )

    def test_allocation_edit_form_contains_schema_fields(self):
        """
        Verify the edit form includes fields for schema attributes.
        """
        edit_url = self._get_url("edit", self.allocation)
        response = self.client.get(edit_url)
        self.assertHttpStatus(response, 200)
        self.assertContains(response, "attr_gpu")
        self.assertContains(response, "attr_memory")

    def test_allocation_edit_with_attributes(self):
        """
        Edit an allocation and update its schema attribute values.
        """
        edit_url = self._get_url("edit", self.allocation)
        form_data = {
            "justification": "Updated resources",
            "description": "Updated allocation",
            "owner": self.user.pk,
            "project": self.project.pk,
            "resource_object": f"{ContentType.objects.get_for_model(Resource).pk}:{self.resource.pk}",
            "attr_gpu": "B200",
            "attr_memory": 8192,
            "status": AllocationStatusChoices.STATUS_ACTIVE,
        }
        response = self.client.post(edit_url, form_data)
        self.assertHttpStatus(response, 302)
        self.allocation.refresh_from_db()
        self.assertEqual(self.allocation.attribute_data["gpu"], "B200")
        self.assertEqual(self.allocation.attribute_data["memory"], 8192)

    def test_allocation_create_with_attributes(self):
        """
        Create an allocation with schema attribute values via the form.
        """
        self.add_permissions("ras.add_allocation")
        form_data = {
            "justification": "Need resources X",
            "description": "Test allocation",
            "owner": self.user.pk,
            "project": self.project.pk,
            "resource_object": f"{ContentType.objects.get_for_model(Resource).pk}:{self.resource.pk}",
            "attr_gpu": "A100",
            "attr_memory": 4096,
            "status": AllocationStatusChoices.STATUS_REQUESTED,
        }
        response = self.client.post(self._get_url("add"), form_data)
        self.assertHttpStatus(response, 302)
        allocation = Allocation.objects.order_by("pk").last()
        self.assertEqual(allocation.attribute_data["gpu"], "A100")
        self.assertEqual(allocation.attribute_data["memory"], 4096)


class AllocationWithExtensionTest(ModelViewTestCase):
    """
    Test that allocations with an allocation extension properly show
    extension fields on the edit form and create extension instances.
    """

    model = Allocation

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="User1")
        project = Project.objects.create(name="Project Ext", owner=user)
        from coldfront.storage.models import StorageResource

        cls.storage_resource = StorageResource.objects.create(name="Storage-1")
        storage_ct = ContentType.objects.get_for_model(StorageResource)
        now = timezone.now()
        cls.allocation = Allocation.objects.create(
            justification="Need storage",
            project=project,
            owner=user,
            resource_object_type=storage_ct,
            resource_object_id=cls.storage_resource.pk,
            status=AllocationStatusChoices.STATUS_ACTIVE,
            start_date=now,
            end_date=now + timedelta(days=30),
        )
        cls.user = user
        cls.project = project

    def setUp(self):
        super().setUp()
        self.add_permissions(
            "ras.view_allocation",
            "ras.add_allocation",
            "ras.change_allocation",
            "storage.view_storagequota",
            "storage.add_storagequota",
            "storage.view_storageresource",
            "ras.view_project",
            "users.view_user",
        )

    def test_allocation_edit_form_contains_extension_fields(self):
        """
        Verify the edit form includes fields for the extension's requestable fields.
        """
        edit_url = self._get_url("edit", self.allocation)
        response = self.client.get(edit_url)
        self.assertHttpStatus(response, 200)
        self.assertContains(response, "ext_storagequota_hard_limit_bytes")

    def test_allocation_create_with_extension(self):
        """
        Create an allocation with extension values, verify extension instance is created.
        """
        from coldfront.storage.models import StorageQuota, StorageResource

        self.add_permissions("ras.add_allocation")
        form_data = {
            "justification": "Need storage",
            "description": "Test extension",
            "owner": self.user.pk,
            "project": self.project.pk,
            "resource_object": f"{ContentType.objects.get_for_model(StorageResource).pk}:{self.storage_resource.pk}",
            "ext_storagequota_hard_limit_bytes": 500,
            "status": AllocationStatusChoices.STATUS_REQUESTED,
        }
        response = self.client.post(self._get_url("add"), form_data)
        self.assertHttpStatus(response, 302)
        # Verify the extension instance was created
        new_id = response.url.rstrip("/").split("/")[-1]
        ext = StorageQuota.objects.filter(allocation_id=new_id).first()
        self.assertIsNotNone(ext)
        self.assertEqual(ext.hard_limit_bytes, 500)

    def test_allocation_detail_shows_extension_tab(self):
        """
        Verify the allocation detail page shows a tab for the extension.
        """
        from coldfront.storage.models import StorageQuota
        from coldfront.users.models import Group

        group = Group.objects.create(name="ext-group")
        StorageQuota.objects.create(
            allocation=self.allocation,
            storage=self.storage_resource,
            path=f"/home/groups/test/{self.allocation.id}",
            owning_user=self.user,
            owning_group=group,
            hard_limit_bytes=100,
            soft_limit_bytes=50,
        )
        detail_url = self.allocation.get_absolute_url()
        response = self.client.get(detail_url)
        self.assertHttpStatus(response, 200)
        self.assertContains(response, "Storage Quota")


class AllocationChangeRequestWithSchemaAttributesTest(ModelViewTestCase):
    """
    Test creating and applying an allocation change request with resource schema attributes.
    """

    model = AllocationChangeRequest

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="User1")
        project = Project.objects.create(name="Project 1", owner=user)
        resource_type = ResourceType.objects.create(name="Cluster")
        cls.resource = Resource.objects.create(
            name="Resource with schema",
            slug="r-schema",
            resource_type=resource_type,
            schema={
                "properties": {
                    "gpu": {"title": "GPU", "type": "string"},
                    "memory": {"title": "Memory (MB)", "type": "integer"},
                },
                "required": ["memory"],
            },
        )
        resource_ct = ContentType.objects.get_for_model(Resource)
        now = timezone.now()
        cls.allocation = Allocation.objects.create(
            justification="Need resources",
            project=project,
            owner=user,
            resource_object_type=resource_ct,
            resource_object_id=cls.resource.pk,
            status=AllocationStatusChoices.STATUS_ACTIVE,
            start_date=now,
            end_date=now + timedelta(days=30),
            attribute_data={"gpu": "A100", "memory": 4096},
        )
        cls.user = user
        cls.project = project

    def setUp(self):
        super().setUp()
        self.add_permissions(
            "ras.view_allocationchangerequest",
            "ras.add_allocationchangerequest",
            "ras.change_allocationchangerequest",
            "ras.approve_allocationchangerequest",
            "ras.apply_allocationchangerequest",
            "ras.view_allocation",
            "ras.view_resource",
        )

    def test_change_request_form_contains_schema_fields(self):
        """
        Verify the edit form includes attribute fields from the resource schema.
        """
        self.add_permissions("ras.add_allocationchangerequest")
        # Create a change request first, then test the edit form
        cr = AllocationChangeRequest.objects.create(
            allocation=self.allocation,
            requested_by=self.user,
            justification="Test edit form",
        )
        edit_url = self._get_url("edit", cr)
        response = self.client.get(edit_url)
        self.assertHttpStatus(response, 200)
        self.assertContains(response, "attr_gpu")
        self.assertContains(response, "attr_memory")

    def test_create_change_request_with_attribute_changes(self):
        """
        Create a change request with proposed attribute changes.
        """
        add_url = self._get_url("add")
        response = self.client.post(
            add_url,
            {
                "allocation": self.allocation.pk,
                "justification": "Increase memory",
                "attr_gpu": "B200",
                "attr_memory": 8192,
            },
        )
        self.assertHttpStatus(response, 302)
        cr = AllocationChangeRequest.objects.get(
            allocation=self.allocation,
            justification="Increase memory",
        )
        self.assertIn("gpu", cr.attribute_changes)
        self.assertIn("memory", cr.attribute_changes)
        self.assertEqual(cr.attribute_changes["gpu"], "B200")
        self.assertEqual(cr.attribute_changes["memory"], 8192)

    def test_apply_change_request_with_attribute_changes(self):
        """
        Create, approve, and apply a change request with attribute changes.
        Verify the allocation's attribute_data is updated and snapshot is captured.
        """
        add_url = self._get_url("add")
        response = self.client.post(
            add_url,
            {
                "allocation": self.allocation.pk,
                "justification": "Upgrade GPU",
                "attr_gpu": "H100",
                "attr_memory": 4096,
            },
        )
        self.assertHttpStatus(response, 302)
        cr = AllocationChangeRequest.objects.get(
            allocation=self.allocation,
            justification="Upgrade GPU",
        )

        # Approve
        approve_url = self._get_url("approve", cr)
        self.client.post(approve_url, {"comments": "Approved"})

        # Apply
        apply_url = self._get_url("apply", cr)
        self.client.post(apply_url, {"comments": "Applied"})

        # Verify allocation was updated
        self.allocation.refresh_from_db()
        self.assertEqual(self.allocation.attribute_data["gpu"], "H100")
        self.assertEqual(self.allocation.attribute_data["memory"], 4096)

        # Verify snapshot was captured
        cr.refresh_from_db()
        self.assertIsNotNone(cr.snapshot_attribute_values)
        self.assertEqual(cr.snapshot_attribute_values["gpu"], "A100")
        self.assertEqual(cr.snapshot_attribute_values["memory"], 4096)

    def test_detail_view_shows_attribute_diff(self):
        """
        Verify the change request detail page shows pre/post values for attributes.
        """
        cr = AllocationChangeRequest.objects.create(
            allocation=self.allocation,
            requested_by=self.user,
            justification="Test attribute display",
            attribute_changes={"gpu": "H100"},
        )
        detail_url = reverse("ras:allocationchangerequest", kwargs={"pk": cr.pk})
        response = self.client.get(detail_url)
        self.assertHttpStatus(response, 200)
        self.assertContains(response, "Current Values")
        self.assertContains(response, "Requested Changes")


class AllocationExtensionRequestableFieldsTest(TestCase):
    """
    Test that ``ALLOCATION_EXTENSION_REQUESTABLE_FIELDS`` setting overrides
    ``_requestable_fields`` on extension models, and validates field names.
    """

    def test_setting_overrides_requestable_fields(self):
        """
        Setting ``ALLOCATION_EXTENSION_REQUESTABLE_FIELDS`` for a model
        should override its ``_requestable_fields``.
        """
        from coldfront.storage.models import StorageQuota

        key = f"{StorageQuota.__module__}.{StorageQuota.__qualname__}"
        with override_settings(ALLOCATION_EXTENSION_REQUESTABLE_FIELDS={key: ("hard_limit_bytes",)}):
            fields = StorageQuota.requestable_fields()
            self.assertEqual(fields, ["hard_limit_bytes"])

    def test_setting_overrides_multiple_fields(self):
        """
        Setting multiple fields should return the full list.
        """
        from coldfront.storage.models import StorageQuota

        key = f"{StorageQuota.__module__}.{StorageQuota.__qualname__}"
        with override_settings(ALLOCATION_EXTENSION_REQUESTABLE_FIELDS={key: ("hard_limit_bytes", "soft_limit_bytes")}):
            fields = StorageQuota.requestable_fields()
            self.assertEqual(fields, ["hard_limit_bytes", "soft_limit_bytes"])

    def test_setting_with_empty_list_returns_no_fields(self):
        """
        Setting the value to an empty tuple/list should return an empty list,
        effectively hiding all fields for that model.
        """
        from coldfront.storage.models import StorageQuota

        key = f"{StorageQuota.__module__}.{StorageQuota.__qualname__}"
        with override_settings(ALLOCATION_EXTENSION_REQUESTABLE_FIELDS={key: ()}):
            fields = StorageQuota.requestable_fields()
            self.assertEqual(fields, [])

    def test_setting_with_invalid_field_raises_improperly_configured(self):
        """
        If the setting references a field that doesn't exist on the model,
        ``ImproperlyConfigured`` should be raised.
        """
        from django.core.exceptions import ImproperlyConfigured

        from coldfront.storage.models import StorageQuota

        key = f"{StorageQuota.__module__}.{StorageQuota.__qualname__}"
        with override_settings(ALLOCATION_EXTENSION_REQUESTABLE_FIELDS={key: ("nonexistent_field",)}):
            with self.assertRaises(ImproperlyConfigured):
                StorageQuota.requestable_fields()
