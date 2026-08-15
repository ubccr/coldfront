# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import copy
from datetime import timedelta

from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from django.utils import timezone
from rest_framework import status

from coldfront.core.choices import ObjectChangeActionChoices
from coldfront.core.models import ObjectChange, ObjectType
from coldfront.ras.choices import AllocationStatusChoices, ResourceStatusChoices
from coldfront.ras.models import (
    Allocation,
    AllocationChangeRequest,
    Project,
    ProjectUser,
    Resource,
    ResourceType,
)
from coldfront.users.models import ObjectPermission, User
from coldfront.utils.testing import APITestCase, APIViewTestCases
from coldfront.utils.testing.utils import get_random_string


class AppTest(APITestCase):
    def test_root(self):

        url = reverse("ras-api:api-root")
        response = self.client.get("{}?format=api".format(url), **self.header)

        self.assertEqual(response.status_code, 200)


class ProjectTest(APIViewTestCases.APIViewTestCase):
    model = Project
    brief_fields = ["description", "display", "id", "name", "slug", "url"]
    bulk_update_data = {
        "description": "New description",
    }

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

        cls.create_data = [
            {
                "name": "Project X",
                "description": "A new project",
                "owner": users[0].pk,
            },
            {
                "name": "Project Y",
                "description": "A new project",
                "owner": users[1].pk,
            },
            {
                "name": "Project Z",
                "description": "A new project",
                "owner": users[2].pk,
            },
        ]


class ProjectUserTest(APIViewTestCases.APIViewTestCase):
    model = ProjectUser
    brief_fields = ["display", "id", "project", "url", "user"]

    @classmethod
    def setUpTestData(cls):
        owner = User.objects.create(username="pi")
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

        projects = (
            Project(name="Project 1", owner=owner),
            Project(name="Project 2", owner=owner),
            Project(name="Project 3", owner=owner),
        )
        for project in projects:
            project.save()

        project_users = (
            ProjectUser(user=users[0], project=projects[0]),
            ProjectUser(user=users[1], project=projects[1]),
            ProjectUser(user=users[2], project=projects[0]),
        )
        for pu in project_users:
            pu.save()

        cls.bulk_update_data = {
            "project": projects[2].pk,
        }

        cls.create_data = [
            {
                "user": users[3].pk,
                "project": projects[2].pk,
            },
            {
                "user": users[4].pk,
                "project": projects[1].pk,
            },
            {
                "user": users[5].pk,
                "project": projects[0].pk,
            },
        ]


class ResourceTypeTest(APIViewTestCases.APIViewTestCase):
    model = ResourceType
    brief_fields = ["description", "display", "id", "name", "slug", "url"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        resource_types = (
            ResourceType(name="Resource Type 1", slug="type-1"),
            ResourceType(name="Resource Type 2", slug="type-2"),
            ResourceType(name="Resource Type 3", slug="type-3"),
        )
        for rt in resource_types:
            rt.save()

        cls.create_data = [
            {
                "name": "Resource Type X",
                "description": "A new type",
                "slug": "type-x",
            },
            {
                "name": "Resource Type Y",
                "description": "A new type",
                "slug": "type-y",
            },
            {
                "name": "Resource Type Z",
                "description": "A new type",
                "slug": "type-z",
            },
        ]


class ResourceTest(APIViewTestCases.APIViewTestCase):
    model = Resource
    brief_fields = ["_depth", "description", "display", "id", "name", "slug", "status", "url"]
    bulk_update_data = {
        "description": "New description",
    }

    @classmethod
    def setUpTestData(cls):

        resource_type = ResourceType.objects.create(name="Cluster", slug="cluster")

        resources = (
            Resource(name="Resource 1", slug="r-1", resource_type=resource_type),
            Resource(name="Resource 2", slug="r-2", resource_type=resource_type),
            Resource(name="Resource 3", slug="r-3", resource_type=resource_type),
        )
        for resource in resources:
            resource.save()

        cls.create_data = [
            {
                "name": "Resource X",
                "slug": "r-x",
                "description": "A new resource",
                "resource_type": resource_type.pk,
                "status": ResourceStatusChoices.STATUS_ACTIVE,
            },
            {
                "name": "Resource Y",
                "slug": "r-y",
                "description": "A new resource",
                "resource_type": resource_type.pk,
                "status": ResourceStatusChoices.STATUS_ACTIVE,
            },
            {
                "name": "Resource Z",
                "slug": "r-z",
                "description": "A new resource",
                "resource_type": resource_type.pk,
                "status": ResourceStatusChoices.STATUS_ACTIVE,
            },
        ]


class AllocationTest(APIViewTestCases.APIViewTestCase):
    model = Allocation
    brief_fields = ["description", "display", "id", "slug", "status", "url"]
    bulk_update_data = {
        "description": "New description",
    }

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

        # Create a resource with a schema for attribute testing
        cls.create_data = [
            {
                "justification": "Need resources X",
                "description": "A new Allocation",
                "owner": user.pk,
                "project": project.pk,
                "resource_object_type": "ras.resource",
                "resource_object_id": resources[0].pk,
                "status": AllocationStatusChoices.STATUS_ACTIVE,
            },
            {
                "justification": "Need resources Y",
                "description": "A new Allocation",
                "owner": user.pk,
                "project": project.pk,
                "resource_object_type": "ras.resource",
                "resource_object_id": resources[1].pk,
                "status": AllocationStatusChoices.STATUS_ACTIVE,
            },
            {
                "justification": "Need resources Z",
                "description": "A new Allocation",
                "owner": user.pk,
                "project": project.pk,
                "resource_object_type": "ras.resource",
                "resource_object_id": resources[2].pk,
                "status": AllocationStatusChoices.STATUS_ACTIVE,
            },
        ]


class AllocationChangeRequestTest(APIViewTestCases.APIViewTestCase):
    model = AllocationChangeRequest
    brief_fields = ["allocation", "display", "id", "slug", "status", "url"]
    bulk_update_data = None
    validation_excluded_fields = ["slug", "status", "requested_by", "reviewer"]

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

        # Create pre-existing change requests for list/detail/delete tests
        change_requests = (
            AllocationChangeRequest(
                allocation=allocations[0],
                requested_by=user,
                justification="Test CR 1",
                extension_days=30,
            ),
            AllocationChangeRequest(
                allocation=allocations[1],
                requested_by=user,
                justification="Test CR 2",
                extension_days=60,
            ),
            AllocationChangeRequest(
                allocation=allocations[2],
                requested_by=user,
                justification="Test CR 3",
                extension_days=90,
            ),
        )
        for cr in change_requests:
            cr.save()

        cls.create_data = [
            {
                "allocation": allocations[0].pk,
                "justification": "Need more resources",
                "requested_by": user.pk,
                "extension_days": 30,
            },
            {
                "allocation": allocations[1].pk,
                "justification": "Increase quota",
                "requested_by": user.pk,
                "extension_days": 60,
            },
            {
                "allocation": allocations[2].pk,
                "justification": "Extend access",
                "requested_by": user.pk,
                "extension_days": 90,
            },
        ]

    def test_create_object(self):
        """
        POST a single AllocationChangeRequest with field_changes.
        """
        # Add object-level permission
        obj_perm = ObjectPermission(name="Test permission", actions=["add"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        data = copy.deepcopy(self.create_data[0])
        data["changelog_message"] = get_random_string(10)

        initial_count = self._get_queryset().count()
        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(self._get_queryset().count(), initial_count + 1)
        instance = self._get_queryset().get(pk=response.data["id"])
        self.assertEqual(instance.justification, "Need more resources")

        # Verify ObjectChange creation
        objectchange = ObjectChange.objects.get(
            changed_object_type=ContentType.objects.get_for_model(instance),
            changed_object_id=instance.pk,
            action=ObjectChangeActionChoices.ACTION_CREATE,
        )
        self.assertEqual(objectchange.message, data["changelog_message"])

    def test_bulk_create_objects(self):
        """
        POST a set of AllocationChangeRequests in a single request.
        """
        # Add object-level permission
        obj_perm = ObjectPermission(name="Test permission", actions=["add"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        changelog_message = get_random_string(10)
        data = copy.deepcopy(self.create_data)
        for obj_data in data:
            obj_data["changelog_message"] = changelog_message

        initial_count = self._get_queryset().count()
        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        self.assertEqual(len(response.data), len(data))
        self.assertEqual(self._get_queryset().count(), initial_count + len(data))

    def test_update_object(self):
        """
        PATCH a single AllocationChangeRequest — only simple fields.
        """
        instance = self._get_queryset().first()
        url = self._get_detail_url(instance)

        # Add object-level permission
        obj_perm = ObjectPermission(name="Test permission", actions=["change"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        data = {"justification": "Updated justification"}
        data["changelog_message"] = get_random_string(10)

        response = self.client.patch(url, data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        instance.refresh_from_db()
        self.assertEqual(instance.justification, "Updated justification")

    def test_bulk_update_objects(self):
        """
        PATCH a set of AllocationChangeRequests — skip because nested fields
        are not supported for bulk update.
        """
        pass

    # --- Extension API tests ---

    def test_create_with_extension_changes(self):
        """
        POST a change request with extension_changes for StorageQuota.
        """
        from coldfront.storage.models import StorageQuota, StorageResource

        user = User.objects.get(username="User1")
        project = Project.objects.get(name="Project 1")
        storage_resource = StorageResource.objects.create(
            name="Storage-API",
        )
        storage_ct = ContentType.objects.get_for_model(StorageResource)
        allocation = Allocation.objects.create(
            justification="Need storage",
            project=project,
            owner=user,
            resource_object_type=storage_ct,
            resource_object_id=storage_resource.pk,
        )

        # Create the extension first (simulates allocation-time creation)
        from coldfront.users.models import Group

        group = Group.objects.create(name="api-ext-group")
        StorageQuota.objects.create(
            allocation=allocation,
            storage=storage_resource,
            path=f"/home/groups/Project 1/{allocation.id}",
            owning_user=user,
            owning_group=group,
            hard_limit_bytes=100,
            soft_limit_bytes=50,
        )

        obj_perm = ObjectPermission(name="Test permission", actions=["add"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        data = {
            "allocation": allocation.pk,
            "justification": "Increase storage quota",
            "requested_by": self.user.pk,
            "extension_days": 30,
            "extension_changes": {
                "storage.StorageQuota": {
                    "hard_limit_bytes": 200,
                }
            },
        }
        data["changelog_message"] = get_random_string(10)

        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        instance = self._get_queryset().get(pk=response.data["id"])
        self.assertEqual(instance.justification, "Increase storage quota")
        self.assertEqual(instance.extension_days, 30)
        self.assertIn("storage.StorageQuota", instance.extension_changes)
        self.assertEqual(
            instance.extension_changes["storage.StorageQuota"]["hard_limit_bytes"],
            200,
        )

    def test_create_with_invalid_extension_path(self):
        """
        POST a change request with an extension_changes key that doesn't
        match any registered extension for the resource type.
        """
        allocation = Allocation.objects.first()

        obj_perm = ObjectPermission(name="Test permission", actions=["add"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        data = {
            "allocation": allocation.pk,
            "justification": "Should fail",
            "requested_by": self.user.pk,
            "extension_changes": {
                "nonexistent.FooExtension": {
                    "some_field": 42,
                }
            },
        }

        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_400_BAD_REQUEST)
        self.assertIn("extension_changes", response.data)

    def test_detail_view_includes_extension_changes(self):
        """
        GET a change request that has extension_changes — verify they are
        included in the response with proposed/current values.
        """
        from coldfront.storage.models import StorageQuota, StorageResource

        user = User.objects.get(username="User1")
        project = Project.objects.get(name="Project 1")
        storage_resource = StorageResource.objects.create(
            name="Storage-Detail-API",
        )
        storage_ct = ContentType.objects.get_for_model(StorageResource)
        allocation = Allocation.objects.create(
            justification="Detail test",
            project=project,
            owner=user,
            resource_object_type=storage_ct,
            resource_object_id=storage_resource.pk,
        )

        # Create extension with current values
        from coldfront.users.models import Group

        group = Group.objects.create(name="api-ext-group2")
        StorageQuota.objects.create(
            allocation=allocation,
            storage=storage_resource,
            path=f"/home/groups/Project 1/{allocation.id}",
            owning_user=user,
            owning_group=group,
            hard_limit_bytes=500,
            soft_limit_bytes=250,
        )

        # Create a change request with proposed extension changes
        cr = AllocationChangeRequest.objects.create(
            allocation=allocation,
            requested_by=user,
            justification="Detail view test",
            extension_days=30,
            extension_changes={
                "storage.storagequota": {
                    "hard_limit_bytes": 1000,
                }
            },
        )

        obj_perm = ObjectPermission(name="Test permission", constraints={"pk": cr.pk}, actions=["view"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        response = self.client.get(self._get_detail_url(cr), **self.header)
        self.assertHttpStatus(response, status.HTTP_200_OK)
        self.assertIn("extension_changes", response.data)
        self.assertIn("storage.storagequota", response.data["extension_changes"])
        ext_data = response.data["extension_changes"]["storage.storagequota"]
        self.assertIn("proposed", ext_data)
        self.assertIn("current", ext_data)
        self.assertEqual(ext_data["proposed"]["hard_limit_bytes"], 1000)
        self.assertEqual(ext_data["current"]["hard_limit_bytes"], 500)

    # --- Schema attribute API tests ---

    def test_create_with_attribute_changes(self):
        """
        POST a change request with attribute_changes matching the resource schema.
        """
        resource_type = ResourceType.objects.create(name="API Schema Type", slug="api-schema-type")
        resource = Resource.objects.create(
            name="API Schema Resource",
            slug="api-schema",
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
        user = User.objects.get(username="User1")
        project = Project.objects.get(name="Project 1")
        now = timezone.now()
        allocation = Allocation.objects.create(
            justification="API attribute test",
            project=project,
            owner=user,
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
            status=AllocationStatusChoices.STATUS_ACTIVE,
            start_date=now,
            end_date=now + timedelta(days=30),
            attribute_data={"gpu": "A100", "memory": 4096},
        )

        obj_perm = ObjectPermission(name="Test permission", actions=["add"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        data = {
            "allocation": allocation.pk,
            "justification": "Upgrade GPU",
            "requested_by": self.user.pk,
            "attribute_changes": {
                "gpu": "H100",
                "memory": 8192,
            },
        }
        data["changelog_message"] = get_random_string(10)

        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        instance = self._get_queryset().get(pk=response.data["id"])
        self.assertEqual(instance.justification, "Upgrade GPU")
        self.assertIn("gpu", instance.attribute_changes)
        self.assertIn("memory", instance.attribute_changes)
        self.assertEqual(instance.attribute_changes["gpu"], "H100")
        self.assertEqual(instance.attribute_changes["memory"], 8192)

    def test_create_with_attribute_changes_accepted(self):
        """
        POST a change request with attribute_changes — even fields not in the
        schema are accepted at create time. Validation occurs at apply time.
        """
        resource_type = ResourceType.objects.create(name="API Schema Type 2", slug="api-schema-type-2")
        resource = Resource.objects.create(
            name="API Schema Resource 2",
            slug="api-schema-2",
            resource_type=resource_type,
            schema={
                "properties": {
                    "memory": {"title": "Memory (MB)", "type": "integer"},
                },
                "required": ["memory"],
            },
        )
        resource_ct = ContentType.objects.get_for_model(Resource)
        user = User.objects.get(username="User1")
        project = Project.objects.get(name="Project 1")
        allocation = Allocation.objects.create(
            justification="Accept attribute test",
            project=project,
            owner=user,
            resource_object_type=resource_ct,
            resource_object_id=resource.pk,
            attribute_data={"memory": 2048},
        )

        obj_perm = ObjectPermission(name="Test permission", actions=["add"])
        obj_perm.save()
        obj_perm.users.add(self.user)
        obj_perm.object_types.add(ObjectType.objects.get_for_model(self.model))

        data = {
            "allocation": allocation.pk,
            "justification": "Accepted",
            "requested_by": self.user.pk,
            "attribute_changes": {
                "nonexistent_field": "value",
            },
        }
        data["changelog_message"] = get_random_string(10)

        response = self.client.post(self._get_list_url(), data, format="json", **self.header)
        self.assertHttpStatus(response, status.HTTP_201_CREATED)
        instance = self._get_queryset().get(pk=response.data["id"])
        self.assertIn("nonexistent_field", instance.attribute_changes)
