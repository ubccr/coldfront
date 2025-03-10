"""View tests for cluster allocations"""
import logging

import urllib.parse
from django.db.models import Count
from django.test import TestCase
from django.urls import reverse

from coldfront.core.test_helpers import utils
from coldfront.core.allocation.models import (
    Allocation,
    AllocationUserNote,
    AllocationAttribute,
    AllocationAttributeType,
    AllocationStatusChoice,
    AllocationChangeRequest,
)
from coldfront.core.resource.models import Resource
from coldfront.core.test_helpers.factories import (
    setup_models,
    UserFactory,
    ResourceFactory,
    ResourceTypeFactory,
    AllocationFactory,
    AllocationChangeRequestFactory,
)


logging.disable(logging.CRITICAL)

UTIL_FIXTURES = [
    "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]

BACKEND = "django.contrib.auth.backends.ModelBackend"


class ClusterAllocationViewBaseTest(TestCase):
    """Base class for allocation view tests."""

    fixtures = UTIL_FIXTURES

    @classmethod
    def setUpTestData(cls):
        """Test Data setup for all allocation view tests."""
        setup_models(cls)

    def allocation_access_tstbase(self, url):
        """Test basic access control for views. For all views:
        - if not logged in, redirect to login page
        - if logged in as admin, can access page
        """
        utils.test_logged_out_redirect_to_login(self, url)
        utils.test_user_can_access(self, self.admin_user, url)  # admin can access


class ClusterAllocationChangeViewTest(ClusterAllocationViewBaseTest):
    """Tests for AllocationChangeView"""

    def setUp(self):
        self.client.force_login(self.admin_user, backend=BACKEND)
        self.url = f'/allocation/{self.cluster_allocation.pk}/change-request'
        self.post_data = {
            'justification': 'just a test',
            'attributeform-0-new_value': '',
            'attributeform-INITIAL_FORMS': '1',
            'attributeform-MAX_NUM_FORMS': '1',
            'attributeform-MIN_NUM_FORMS': '0',
            'attributeform-TOTAL_FORMS': '1',
            'end_date_extension': 0,
        }
        self.success_msg = "Allocation change request successfully submitted."

    def test_allocationchangeview_access(self):
        """Test get request - can't access for cluster allocations"""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(self.url, follow=True)
        self.assertContains(response, 'You can only request changes for storage allocations.')

    def test_allocationchangeview_post_permissions(self):
        """Test post request"""
        response = self.client.post(self.url, data=self.post_data)
        self.assertEqual(response.status_code, 302)
        response = self.client.post(self.url, data=self.post_data, follow=True)
        self.assertContains(response, 'You can only request changes for storage allocations.')


class ClusterAllocationDetailViewTest(ClusterAllocationViewBaseTest):
    """Tests for AllocationDetailView"""

    def setUp(self):
        self.url = f'/allocation/{self.cluster_allocation.pk}/'

    def test_allocation_detail_access(self):
        self.allocation_access_tstbase(self.url)
        # pi, project nonallocation user, nonproj_allocationuser can access
        utils.test_user_can_access(self, self.pi_user, self.url)
        utils.test_user_can_access(self, self.proj_nonallocationuser, self.url)
        utils.test_user_can_access(self, self.nonproj_allocationuser, self.url)
        # check access for allocation user with "Removed" status

    def test_allocationdetail_requestchange_button(self):
        """'Request Change' button not visible for cluster allocations"""
        search_text = 'Request Change'
        self.client.force_login(self.admin_user, backend=BACKEND)
        response = self.client.get(self.url)
        utils.page_does_not_contain_for_user(self, self.admin_user, self.url, search_text)

    def test_allocationattribute_button_visibility(self):
        """Test visibility of "Add Attribute" button for different user types"""
        # admin
        add_text = 'Add Allocation Attribute'
        delete_text = 'Delete Allocation Attribute'
        utils.page_contains_for_user(self, self.admin_user, self.url, add_text)
        utils.page_contains_for_user(self, self.admin_user, self.url, delete_text)
        # pi
        utils.page_does_not_contain_for_user(self, self.pi_user, self.url, add_text)
        utils.page_does_not_contain_for_user(self, self.pi_user, self.url, delete_text)
        # allocation user
        utils.page_does_not_contain_for_user(
            self, self.proj_allocationuser, self.url, add_text
        )
        utils.page_does_not_contain_for_user(
            self, self.proj_allocationuser, self.url, delete_text
        )

    def test_compute_allocationuser_button_visibility(self):
        """Test visibility of "Add/Remove Users" buttons for different user types"""
        # these buttons will only be available for compute allocations
        # admin can see add/remove users buttons
        utils.page_contains_for_user(
                self, self.admin_user, self.url, 'Add Users')
        utils.page_contains_for_user(
                self, self.admin_user, self.url, 'Remove Users')
        # pi can see add/remove users buttons
        utils.page_contains_for_user(
                self, self.pi_user, self.url, 'Add Users')
        utils.page_contains_for_user(
                self, self.pi_user, self.url, 'Remove Users')
        # allocation user can't see add/remove users buttons
        utils.page_does_not_contain_for_user(
            self, self.proj_allocationuser, self.url, 'Add Users')
        utils.page_does_not_contain_for_user(
            self, self.proj_allocationuser, self.url, 'Remove Users')


class ClusterAllocationAddUsersViewTest(ClusterAllocationViewBaseTest):
    """Tests for the AllocationAddUsersView"""

    def setUp(self):
        self.url = f'/allocation/{self.cluster_allocation.pk}/add-users'

    def test_allocationaddusersview_access(self):
        self.allocation_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)
        utils.test_user_cannot_access(self, self.proj_allocationuser, self.url)

    def test_allocation_non_project_user_space_separated_search(self):
        username_list = ['iberlin', 'gvanrossum']
        space_separated_search = " ".join(username_list)
        self.client.force_login(self.admin_user, backend="django.contrib.auth.backends.ModelBackend")
        url = f'/allocation/{self.cluster_allocation.pk}/add-users?search={space_separated_search}'
        space_separated_search_response = str(self.client.get(url).content)
        self.assertTrue('Found 2 matchs.' in space_separated_search_response)
        self.assertTrue('<td>iberlin</td>' in space_separated_search_response)
        self.assertTrue('<td>gvanrossum</td>' in space_separated_search_response)

    def test_allocation_non_project_user_new_line_separated_search(self):
        username_list = ['iberlin', 'gvanrossum']
        new_line_separated_search = urllib.parse.quote_plus("\n".join(username_list))
        self.client.force_login(self.admin_user, backend="django.contrib.auth.backends.ModelBackend")
        url = f'/allocation/{self.cluster_allocation.pk}/add-users?search={new_line_separated_search}'
        new_line_separated_search_response = str(self.client.get(url).content)
        self.assertTrue('<td>iberlin</td>' in new_line_separated_search_response)
        self.assertTrue('<td>gvanrossum</td>' in new_line_separated_search_response)
        self.assertTrue('Found 2 matchs.' in new_line_separated_search_response)


class ClusterAllocationEditUsersViewTest(ClusterAllocationViewBaseTest):
    """Tests for the AllocationEditUsersView"""

    def setUp(self):
        self.url = f'/allocation/{self.cluster_allocation.pk}/edit-users'

    def test_allocationeditusersview_access(self):
        self.allocation_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)
        utils.test_user_cannot_access(self, self.proj_allocationuser, self.url)


class ClusterAllocationEditUserViewTest(ClusterAllocationViewBaseTest):
    """Tests for the AllocationEditUserView"""

    def setUp(self):
        self.url = f'/allocation/{self.cluster_allocation.pk}/edit-user/{self.proj_allocationuser.pk}'

    def test_allocationedituserview_access(self):
        self.allocation_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)
        utils.test_user_cannot_access(self, self.proj_allocationuser, self.url)


class ClusterAllocationRemoveUsersViewTest(ClusterAllocationViewBaseTest):
    """Tests for the AllocationRemoveUsersView"""

    def setUp(self):
        self.url = f'/allocation/{self.cluster_allocation.pk}/remove-users'

    def test_allocationremoveusersview_access(self):
        """Cluster allocations have this view available"""
        utils.test_user_can_access(self, self.admin_user, self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)
