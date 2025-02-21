from django.test import TestCase

from coldfront.core.test_helpers import utils
from coldfront.core.test_helpers.factories import setup_models


UTIL_FIXTURES = [
    "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]

BACKEND = "django.contrib.auth.backends.ModelBackend"

class ResourceViewBaseTest(TestCase):
    """Base test for resource view tests"""
    fixtures = UTIL_FIXTURES

    @classmethod
    def setUpTestData(cls):
        """Test Data setup for all allocation view tests."""
        setup_models(cls)

    def resource_access_tstbase(self, url):
        """Test basic access control for views. For all views:
        - if not logged in, redirect to login page
        - if logged in as admin, can access page
        """
        utils.test_logged_out_redirect_to_login(self, url)
        utils.test_user_can_access(self, self.admin_user, url)  # admin can access

class ResourceListViewTest(ResourceViewBaseTest):
    """Tests for ResourceListView"""

    def setUp(self):
        self.client.force_login(self.admin_user, backend=BACKEND)


class ClusterResourceDetailViewTest(ResourceViewBaseTest):
    """Tests for ResourceDetailView"""
    def setUp(self):
        self.url = f'/resource/{self.cluster_resource.pk}/'

    def test_resource_detail_access(self):
        self.resource_access_tstbase(self.url)
        # pi, project nonallocation user, nonproj_allocationuser can access
        utils.test_user_can_access(self, self.pi_user, self.url)
        utils.test_user_can_access(self, self.proj_nonallocationuser, self.url)
        utils.test_user_can_access(self, self.nonproj_allocationuser, self.url)
        # check access for allocation user with "Removed" status

    def test_resourceattribute_button_visibility(self):
        """Test visibility of "Add Attribute" button for different user types"""
        # admin
        add_text = 'Add Resource Attribute'
        delete_text = 'Delete Resource Attributes'
        utils.page_contains_for_user(self, self.admin_user, self.url, add_text)
        utils.page_contains_for_user(self, self.admin_user, self.url, delete_text)
        # resource admin
        utils.page_does_not_contain_for_user(self, self.resource_allowed_user, self.url, add_text)
        utils.page_does_not_contain_for_user(self, self.resource_allowed_user, self.url, delete_text)
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
        """Test visibility of "Edit Resource Allocations" buttons for different user types"""
        utils.page_contains_for_user(
                self, self.admin_user, self.url, 'Edit Resource Allocations')
        utils.page_contains_for_user(
                self, self.resource_allowed_user, self.url, 'Edit Resource Allocations')
        utils.page_does_not_contain_for_user(
                self, self.pi_user, self.url, 'Edit Resource Allocations')
        utils.page_does_not_contain_for_user(
            self, self.proj_allocationuser, self.url, 'Edit Resource Allocations')


class StorageResourceDetailViewTest(ResourceViewBaseTest):

    def setUp(self):
        self.url = f'/resource/{self.storage_resource.pk}/'

    def test_resource_detail_access(self):
        self.resource_access_tstbase(self.url)
        utils.test_user_can_access(self, self.pi_user, self.url)
        utils.test_user_can_access(self, self.proj_nonallocationuser, self.url)
        utils.test_user_can_access(self, self.nonproj_allocationuser, self.url)

    def test_resourceattribute_button_visibility(self):
        """Test visibility of "Add Attribute" button for different user types"""
        add_text = 'Add Resource Attribute'
        delete_text = 'Delete Resource Attributes'
        # admin
        utils.page_contains_for_user(self, self.admin_user, self.url, add_text)
        utils.page_contains_for_user(self, self.admin_user, self.url, delete_text)
        # resource admin
        utils.page_does_not_contain_for_user(self, self.resource_allowed_user, self.url, add_text)
        utils.page_does_not_contain_for_user(self, self.resource_allowed_user, self.url, delete_text)
        # pi
        utils.page_does_not_contain_for_user(self, self.pi_user, self.url, add_text)
        utils.page_does_not_contain_for_user(self, self.pi_user, self.url, delete_text)

    def test_storage_allocationuser_button_visibility(self):
        """Test visibility of "Edit Resource Allocations" buttons for different user types"""
        utils.page_does_not_contain_for_user(
                self, self.admin_user, self.url, 'Edit Resource Allocations')


class StorageResourceAttributeCreateViewTest(ResourceViewBaseTest):
    """Tests for ResourceAttributeCreateView"""

    def setUp(self):
        self.url = f'/resource/{self.storage_resource.pk}/resourceattribute/add'

    def test_resource_attribute_create_access(self):
        self.resource_access_tstbase(self.url)
        utils.test_user_cannot_access(self, self.resource_allowed_user, self.url)
        utils.test_user_cannot_access(self, self.pi_user, self.url)


class ClusterResourceAttributeCreateViewTest(ResourceViewBaseTest):
    """Tests for ResourceAttributeCreateView"""

    def setUp(self):
        self.url = f'/resource/{self.cluster_resource.pk}/resourceattribute/add'

    def test_resource_attribute_create_access(self):
        self.resource_access_tstbase(self.url)
        utils.test_user_cannot_access(self, self.resource_allowed_user, self.url)
        utils.test_user_cannot_access(self, self.pi_user, self.url)


class StorageResourceAttributeDeleteViewTest(ResourceViewBaseTest):
    """Tests for ResourceAttributeDeleteView"""

    def setUp(self):
        self.url = f'/resource/{self.storage_resource.pk}/resourceattribute/delete'

    def test_resource_attribute_create_access(self):
        self.resource_access_tstbase(self.url)
        utils.test_user_cannot_access(self, self.resource_allowed_user, self.url)
        utils.test_user_cannot_access(self, self.pi_user, self.url)

class ClusterResourceAttributeDeleteViewTest(ResourceViewBaseTest):
    """Tests for ResourceAttributeDeleteView"""

    def setUp(self):
        self.url = f'/resource/{self.cluster_resource.pk}/resourceattribute/delete'

    def test_resource_attribute_create_access(self):
        self.resource_access_tstbase(self.url)
        utils.test_user_cannot_access(self, self.resource_allowed_user, self.url)
        utils.test_user_cannot_access(self, self.pi_user, self.url)


class StorageResourceAllocationsEditViewTest(ResourceViewBaseTest):
    """Tests for ResourceAllocationsEditView"""

    def setUp(self):
        self.url = f'/resource/{self.storage_resource.pk}/resourceallocations/edit'

    def test_resource_allocation_edit_access(self):
        self.client.force_login(self.admin_user, backend=BACKEND)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 302)


class ClusterResourceAllocationsEditViewTest(ResourceViewBaseTest):
    """Tests for ResourceAllocationsEditView"""

    def setUp(self):
        self.url = f'/resource/{self.cluster_resource.pk}/resourceallocations/edit'

    def test_resource_allocation_edit_access(self):
        self.resource_access_tstbase(self.url)
        utils.test_user_can_access(self, self.resource_allowed_user, self.url)
        utils.test_user_cannot_access(self, self.pi_user, self.url)
