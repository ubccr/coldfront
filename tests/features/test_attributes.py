# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from django.contrib.contenttypes.models import ContentType
from django.test import TestCase

from coldfront.ras.filtersets import AllocationFilterSet
from coldfront.ras.models import (
    Allocation,
    Project,
    Resource,
)
from coldfront.users.models import User


class ResourceTypeTestCase(TestCase):
    queryset = Allocation.objects.all()
    filterset = AllocationFilterSet

    ALLOCATION_ATTRIBUTE_SCHEMA = {
        "properties": {
            "string": {"type": "string"},
            "integer": {"type": "integer"},
            "number": {"type": "number"},
            "boolean": {"type": "boolean"},
        }
    }

    @classmethod
    def setUpTestData(cls):
        user = User.objects.create(username="User1")
        project = Project.objects.create(name="Project 1", owner=user)
        resource_ct = ContentType.objects.get_for_model(Resource)

        resources = (
            Resource(name="Resource 1", slug="r-1", schema=cls.ALLOCATION_ATTRIBUTE_SCHEMA),
            Resource(name="Resource 2", slug="r-2", schema=cls.ALLOCATION_ATTRIBUTE_SCHEMA),
            Resource(name="Resource 3", slug="r-3", schema=cls.ALLOCATION_ATTRIBUTE_SCHEMA),
        )
        for resource in resources:
            resource.save()

        allocations = (
            Allocation(
                justification="Need resources 1",
                project=project,
                owner=user,
                resource_object_type=resource_ct,
                resource_object_id=resources[0].pk,
                attribute_data={
                    "string": "string1",
                    "integer": 1,
                    "number": 1.0,
                    "boolean": True,
                },
            ),
            Allocation(
                justification="Need resources 2",
                project=project,
                owner=user,
                resource_object_type=resource_ct,
                resource_object_id=resources[1].pk,
                attribute_data={
                    "string": "string2",
                    "integer": 2,
                    "number": 2.0,
                    "boolean": False,
                },
            ),
            Allocation(
                justification="Need resources 3",
                project=project,
                owner=user,
                resource_object_type=resource_ct,
                resource_object_id=resources[2].pk,
                attribute_data={
                    "string": "string3",
                    "integer": 3,
                    "number": 3.0,
                    "boolean": None,
                },
            ),
        )

        for a in allocations:
            a.save()

    def test_allocation_attributes(self):
        params = {"attr_string": "string1"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"attr_integer": "1"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"attr_number": "1.0"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"attr_boolean": "true"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 1)
        params = {"attr_number": "10.0"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 0)
        params = {"attr_string": "does not exist"}
        self.assertEqual(self.filterset(params, self.queryset).qs.count(), 0)
