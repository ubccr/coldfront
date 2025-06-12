# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

import logging

from django.test import TestCase
from django.urls import reverse

from coldfront.core.allocation.models import (
    AllocationChangeRequest,
    AllocationChangeStatusChoice,
)
from coldfront.core.test_helpers import utils
from coldfront.core.test_helpers.factories import (
    AllocationAttributeFactory,
    AllocationAttributeTypeFactory,
    AllocationChangeRequestFactory,
    AllocationFactory,
    AllocationStatusChoiceFactory,
    AllocationUserFactory,
    ProjectFactory,
    ProjectStatusChoiceFactory,
    ProjectUserFactory,
    ProjectUserRoleChoiceFactory,
    ResourceFactory,
    UserFactory,
)

logging.disable(logging.CRITICAL)

BACKEND = "django.contrib.auth.backends.ModelBackend"


class AllocationViewBaseTest(TestCase):
    """Base class for allocation view tests."""

    @classmethod
    def setUpTestData(cls):
        """Test Data setup for all allocation view tests."""
        AllocationStatusChoiceFactory(name="New")
        cls.project = ProjectFactory(status=ProjectStatusChoiceFactory(name="Active"))
        cls.allocation = AllocationFactory(project=cls.project)
        cls.allocation.resources.add(ResourceFactory(name="holylfs07/tier1"))
        # create allocation user that belongs to project
        allocation_user = AllocationUserFactory(allocation=cls.allocation)
        cls.allocation_user = allocation_user.user
        ProjectUserFactory(project=cls.project, user=allocation_user.user)
        # create project user that isn't an allocationuser
        proj_nonallocation_user = ProjectUserFactory()
        cls.proj_nonallocation_user = proj_nonallocation_user.user
        cls.admin_user = UserFactory(is_staff=True, is_superuser=True)
        manager_role = ProjectUserRoleChoiceFactory(name="Manager")
        pi_user = ProjectUserFactory(user=cls.project.pi, project=cls.project, role=manager_role)
        cls.pi_user = pi_user.user
        # make a quota TB allocation attribute
        AllocationAttributeFactory(
            allocation=cls.allocation,
            value=100,
            allocation_attribute_type=AllocationAttributeTypeFactory(name="Storage Quota (TB)"),
        )

    def allocation_access_tstbase(self, url):
        """Test basic access control for views. For all views:
        - if not logged in, redirect to login page
        - if logged in as admin, can access page
        """
        utils.test_logged_out_redirect_to_login(self, url)
        utils.test_user_can_access(self, self.admin_user, url)  # admin can access


class AllocationListViewTest(AllocationViewBaseTest):
    """Tests for AllocationListView"""

    @classmethod
    def setUpTestData(cls):
        """Set up users and project for testing"""
        super(AllocationListViewTest, cls).setUpTestData()
        cls.additional_allocations = [AllocationFactory() for i in list(range(100))]
        for allocation in cls.additional_allocations:
            allocation.resources.add(ResourceFactory(name="holylfs09/tier1"))
        cls.nonproj_nonallocation_user = UserFactory()

    def test_allocation_list_access_admin(self):
        """Confirm that AllocationList access control works for admin"""
        self.allocation_access_tstbase("/allocation/")
        # confirm that show_all_allocations=on enables admin to view all allocations
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context["allocation_list"]), 25)

    def test_allocation_list_access_pi(self):
        """Confirm that AllocationList access control works for pi
        When show_all_allocations=on, pi still sees only allocations belonging
        to the projects they are pi for.
        """
        # confirm that show_all_allocations=on enables admin to view all allocations
        self.client.force_login(self.pi_user, backend=BACKEND)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context["allocation_list"]), 1)

    def test_allocation_list_access_user(self):
        """Confirm that AllocationList access control works for non-pi users
        When show_all_allocations=on, users see only the allocations they
        are AllocationUsers of.
        """
        # confirm that show_all_allocations=on is accessible to non-admin but
        # contains only the user's allocations
        self.client.force_login(self.allocation_user, backend=BACKEND)
        response = self.client.get("/allocation/")
        self.assertEqual(len(response.context["allocation_list"]), 1)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context["allocation_list"]), 1)
        # nonallocation user belonging to project can't see allocation
        self.client.force_login(self.nonproj_nonallocation_user, backend=BACKEND)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context["allocation_list"]), 0)
        # nonallocation user belonging to project can't see allocation
        self.client.force_login(self.proj_nonallocation_user, backend=BACKEND)
        response = self.client.get("/allocation/?show_all_allocations=on")
        self.assertEqual(len(response.context["allocation_list"]), 0)

    def test_allocation_list_search_admin(self):
        """Confirm that AllocationList search works for admin"""
        self.client.force_login(self.admin_user, backend=BACKEND)
        base_url = "/allocation/?show_all_allocations=on"
        response = self.client.get(base_url + f"&resource_name={self.allocation.resources.first().pk}")
        self.assertEqual(len(response.context["allocation_list"]), 1)


class AllocationChangeDetailViewTest(AllocationViewBaseTest):
    """Tests for AllocationChangeDetailView"""

    def setUp(self):
        """create an AllocationChangeRequest to test"""
        self.client.force_login(self.admin_user, backend=BACKEND)
        AllocationChangeRequestFactory(id=2, allocation=self.allocation)

    def test_allocationchangedetailview_access(self):
        response = self.client.get(reverse("allocation-change-detail", kwargs={"pk": 2}))
        self.assertEqual(response.status_code, 200)

    def test_allocationchangedetailview_post_deny(self):
        """Test that posting to AllocationChangeDetailView with action=deny
        changes the status of the AllocationChangeRequest to denied."""
        param = {"action": "deny"}
        response = self.client.post(reverse("allocation-change-detail", kwargs={"pk": 2}), param, follow=True)
        self.assertEqual(response.status_code, 200)
        alloc_change_req = AllocationChangeRequest.objects.get(pk=2)
        denied_status_id = AllocationChangeStatusChoice.objects.get(name="Denied").pk
        self.assertEqual(alloc_change_req.status_id, denied_status_id)


class AllocationChangeViewTest(AllocationViewBaseTest):
    """Tests for AllocationChangeView"""

    def setUp(self):
        self.client.force_login(self.admin_user, backend=BACKEND)
        self.post_data = {
            "justification": "just a test",
            "attributeform-0-new_value": "",
            "attributeform-INITIAL_FORMS": "1",
            "attributeform-MAX_NUM_FORMS": "1",
            "attributeform-MIN_NUM_FORMS": "0",
            "attributeform-TOTAL_FORMS": "1",
            "end_date_extension": 0,
        }
        self.url = "/allocation/1/change-request"

    def test_allocationchangeview_access(self):
        """Test get request"""
        self.allocation_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)  # Manager can access
        utils.test_user_cannot_access(self, self.allocation_user, self.url)  # user can't access

    def test_allocationchangeview_post_extension(self):
        """Test post request to extend end date"""

        self.post_data["end_date_extension"] = 90
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 0)
        response = self.client.post("/allocation/1/change-request", data=self.post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Allocation change request successfully submitted.")
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 1)

    def test_allocationchangeview_post_no_change(self):
        """Post request with no change should not go through"""

        self.assertEqual(len(AllocationChangeRequest.objects.all()), 0)

        response = self.client.post("/allocation/1/change-request", data=self.post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "You must request a change")
        self.assertEqual(len(AllocationChangeRequest.objects.all()), 0)


class AllocationDetailViewTest(AllocationViewBaseTest):
    """Tests for AllocationDetailView"""

    def setUp(self):
        self.url = f"/allocation/{self.allocation.pk}/"

    def test_allocation_detail_access(self):
        self.allocation_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)  # PI can access
        utils.test_user_cannot_access(self, self.proj_nonallocation_user, self.url)
        # check access for allocation user with "Removed" status

    def test_allocationdetail_requestchange_button(self):
        """Test visibility of "Request Change" button for different user types"""
        utils.page_contains_for_user(self, self.admin_user, self.url, "Request Change")
        utils.page_contains_for_user(self, self.pi_user, self.url, "Request Change")
        utils.page_does_not_contain_for_user(self, self.allocation_user, self.url, "Request Change")

    def test_allocationattribute_button_visibility(self):
        """Test visibility of "Add Attribute" button for different user types"""
        # admin
        utils.page_contains_for_user(self, self.admin_user, self.url, "Add Allocation Attribute")
        utils.page_contains_for_user(self, self.admin_user, self.url, "Delete Allocation Attribute")
        # pi
        utils.page_does_not_contain_for_user(self, self.pi_user, self.url, "Add Allocation Attribute")
        utils.page_does_not_contain_for_user(self, self.pi_user, self.url, "Delete Allocation Attribute")
        # allocation user
        utils.page_does_not_contain_for_user(self, self.allocation_user, self.url, "Add Allocation Attribute")
        utils.page_does_not_contain_for_user(self, self.allocation_user, self.url, "Delete Allocation Attribute")

    def test_allocationuser_button_visibility(self):
        """Test visibility of "Add/Remove Users" buttons for different user types"""
        # admin
        utils.page_contains_for_user(self, self.admin_user, self.url, "Add Users")
        utils.page_contains_for_user(self, self.admin_user, self.url, "Remove Users")
        # pi
        utils.page_contains_for_user(self, self.pi_user, self.url, "Add Users")
        utils.page_contains_for_user(self, self.pi_user, self.url, "Remove Users")
        # allocation user
        utils.page_does_not_contain_for_user(self, self.allocation_user, self.url, "Add Users")
        utils.page_does_not_contain_for_user(self, self.allocation_user, self.url, "Remove Users")


class AllocationCreateViewTest(AllocationViewBaseTest):
    """Tests for the AllocationCreateView"""

    def setUp(self):
        self.url = f"/allocation/project/{self.project.pk}/create"  # url for AllocationCreateView
        self.client.force_login(self.pi_user)
        self.post_data = {
            "justification": "test justification",
            "quantity": "1",
            "resource": f"{self.allocation.resources.first().pk}",
        }

    def test_allocationcreateview_access(self):
        """Test access to the AllocationCreateView"""
        self.allocation_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)
        utils.test_user_cannot_access(self, self.proj_nonallocation_user, self.url)

    def test_allocationcreateview_post(self):
        """Test POST to the AllocationCreateView"""
        self.assertEqual(len(self.project.allocation_set.all()), 1)
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Allocation requested.")
        self.assertEqual(len(self.project.allocation_set.all()), 2)

    def test_allocationcreateview_post_zeroquantity(self):
        """Test POST to the AllocationCreateView"""
        self.post_data["quantity"] = "0"
        self.assertEqual(len(self.project.allocation_set.all()), 1)
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Allocation requested.")
        self.assertEqual(len(self.project.allocation_set.all()), 2)


class AllocationAddUsersViewTest(AllocationViewBaseTest):
    """Tests for the AllocationAddUsersView"""

    def setUp(self):
        self.url = f"/allocation/{self.allocation.pk}/add-users"

    def test_allocationaddusersview_access(self):
        """Test access to AllocationAddUsersView"""
        self.allocation_access_tstbase(self.url)
        no_permission = "You do not have permission to add users to the allocation."

        self.client.force_login(self.admin_user, backend=BACKEND)
        admin_response = self.client.get(self.url)
        self.assertTrue(no_permission not in str(admin_response.content))

        self.client.force_login(self.pi_user, backend=BACKEND)
        pi_response = self.client.get(self.url)
        self.assertTrue(no_permission not in str(pi_response.content))

        self.client.force_login(self.allocation_user, backend=BACKEND)
        user_response = self.client.get(self.url)
        self.assertTrue(no_permission in str(user_response.content))


class AllocationRemoveUsersViewTest(AllocationViewBaseTest):
    """Tests for the AllocationRemoveUsersView"""

    def setUp(self):
        self.url = f"/allocation/{self.allocation.pk}/remove-users"

    def test_allocationremoveusersview_access(self):
        self.allocation_access_tstbase(self.url)


class AllocationChangeListViewTest(AllocationViewBaseTest):
    """Tests for the AllocationChangeListView"""

    def setUp(self):
        self.url = "/allocation/change-list"

    def test_allocationchangelistview_access(self):
        self.allocation_access_tstbase(self.url)


class AllocationNoteCreateViewTest(AllocationViewBaseTest):
    """Tests for the AllocationNoteCreateView"""

    def setUp(self):
        self.url = f"/allocation/{self.allocation.pk}/allocationnote/add"

    def test_allocationnotecreateview_access(self):
        self.allocation_access_tstbase(self.url)
