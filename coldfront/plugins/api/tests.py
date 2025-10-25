# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import unittest

from rest_framework import status
from rest_framework.test import APITestCase

from coldfront.config.env import ENV
from coldfront.core.allocation.models import Allocation
from coldfront.core.project.models import Project
from coldfront.core.test_helpers.factories import (
    AllocationAttributeFactory,
    AllocationFactory,
    AllocationUserFactory,
    PAttributeTypeFactory,
    ProjectAttributeFactory,
    ProjectAttributeTypeFactory,
    ProjectFactory,
    ProjectStatusChoiceFactory,
    ProjectUserFactory,
    ResourceFactory,
    UserFactory,
)


@unittest.skipUnless(ENV.bool("PLUGIN_API", default=False), "Only run API tests if enabled")
class ColdfrontAPI(APITestCase):
    """Tests for the Coldfront REST API"""

    @classmethod
    def setUpTestData(self):
        """Test Data setup for ColdFront REST API tests."""
        self.admin_user = UserFactory(is_staff=True, is_superuser=True)
        pat = ProjectAttributeTypeFactory(attribute_type=PAttributeTypeFactory(name="Text"))

        for i in range(10):
            project = ProjectFactory(status=ProjectStatusChoiceFactory(name="Active"))
            ProjectUserFactory(project=project, user=self.admin_user)
            ProjectAttributeFactory(project=project, proj_attr_type=pat)

            allocation = AllocationFactory(project=project)
            allocation.resources.add(ResourceFactory(name="test"))
            AllocationUserFactory(allocation=allocation, user=self.admin_user)
            AllocationAttributeFactory(allocation=allocation)
            self.pi_user = project.pi

    def test_requires_login(self):
        """Test that the API requires authentication"""
        response = self.client.get("/api/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_allocation_request_api_permissions(self):
        """Test that accessing the allocation-request API view as an admin returns all
        allocations, and that accessing it as a user is forbidden"""
        # login as admin
        self.client.force_login(self.admin_user)
        response = self.client.get("/api/allocation-requests/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_login(self.pi_user)
        response = self.client.get("/api/allocation-requests/", format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_allocation_api_permissions(self):
        """Test that accessing the allocation API view as an admin returns all
        allocations, and that accessing it as a user returns only the allocations
        for that user"""
        # login as admin
        self.client.force_login(self.admin_user)
        response = self.client.get("/api/allocations/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), Allocation.objects.all().count())

        self.client.force_login(self.pi_user)
        response = self.client.get("/api/allocations/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_allocation_query_params(self):
        """Test that specifying the query parameters returns the related
        information"""
        # login as admin
        self.client.force_login(self.admin_user)
        response = self.client.get("/api/allocations/?allocation_users=true", format="json")
        for alloc in response.json():
            self.assertEqual(len(alloc["allocation_users"]), 1)
            self.assertIsNone(alloc["allocation_attributes"])

        response = self.client.get("/api/allocations/?allocation_attributes=true", format="json")
        for alloc in response.json():
            self.assertIsNone(alloc["allocation_users"])
            self.assertEqual(len(alloc["allocation_attributes"]), 1)

        response = self.client.get("/api/allocations/?allocation_users=true&allocation_attributes=true", format="json")
        for alloc in response.json():
            self.assertEqual(len(alloc["allocation_users"]), 1)
            self.assertEqual(len(alloc["allocation_attributes"]), 1)

    def test_project_api_permissions(self):
        """Confirm permissions for project API:
        admin user should be able to access everything
        Projectusers should be able to access only their projects
        """
        # login as admin
        self.client.force_login(self.admin_user)
        response = self.client.get("/api/projects/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), Project.objects.all().count())

        self.client.force_login(self.pi_user)
        response = self.client.get("/api/projects/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 1)

    def test_project_query_params(self):
        """Test that specifying the query parameters returns the related
        information"""
        # login as admin
        self.client.force_login(self.admin_user)
        response = self.client.get("/api/projects/?project_users=true", format="json")
        for proj in response.json():
            self.assertEqual(len(proj["project_users"]), 1)

        response = self.client.get("/api/projects/?project_attributes=true", format="json")
        for proj in response.json():
            self.assertEqual(len(proj["project_attributes"]), 1)

        response = self.client.get("/api/projects/?allocations=true", format="json")
        for proj in response.json():
            self.assertEqual(len(proj["allocations"]), 1)

    def test_user_api_permissions(self):
        """Test that accessing the user API view as an admin returns all
        allocations, and that accessing it as a user is forbidden"""
        # login as admin
        self.client.force_login(self.admin_user)
        response = self.client.get("/api/users/", format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.force_login(self.pi_user)
        response = self.client.get("/api/users/", format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
