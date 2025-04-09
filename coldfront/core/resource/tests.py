from boto3 import resource
from django.db.models import Q
from django.test import TestCase

from coldfront.core.test_helpers import utils
from coldfront.core.test_helpers.factories import setup_models, AttributeTypeFactory, ProjectFactory, ResourceFactory, ResourceTypeFactory, ResourceAttributeTypeFactory, ResourceAttributeFactory
from coldfront.core.project.models import Project
from coldfront.core.resource.models import AttributeType, ResourceType


UTIL_FIXTURES = [
    "coldfront/core/test_helpers/test_data/test_fixtures/ifx.json",
]
RESOURCE_FIXTURES = [
    "coldfront/core/test_helpers/test_data/test_fixtures/resource.json",
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
    fixtures = RESOURCE_FIXTURES

    def setUp(self):
        self.client.force_login(self.pi_user, backend=BACKEND)
        self.url = f'/resource/'

    def test_only_user_managed_compute_nodes_show(self):
        ProjectFactory(pi=self.pi_user, title="managed_lab")
        ProjectFactory(pi=self.admin_user, title="admin_lab")
        text_attribute_type = AttributeType.objects.get(name="Text")
        managed_resource = ResourceFactory(name="managed_lab", resource_type__name='Compute Node')
        admin_resource = ResourceFactory(name="admin_lab", resource_type__name='Compute Node')
        owner_resourcer_attr_type = ResourceAttributeTypeFactory(name="Owner", attribute_type=text_attribute_type)
        ResourceAttributeFactory(resource_attribute_type=owner_resourcer_attr_type, value="managed_lab", resource=managed_resource)
        ResourceAttributeFactory(resource_attribute_type=owner_resourcer_attr_type, value="admin_lab", resource=admin_resource)
        utils.page_contains_for_user(self, self.pi_user, self.url, 'managed_lab')
        utils.page_does_not_contain_for_user(self, self.pi_user, self.url, 'admin_lab')
        utils.page_contains_for_user(self, self.admin_user, self.url, 'admin_lab')
        utils.page_contains_for_user(self, self.admin_user, self.url, 'managed_lab')

    def test_retired_resources_filter_shows(self):
        utils.page_contains_for_user(self, self.pi_user, self.url, 'View retired resources')
        utils.page_contains_for_user(self, self.admin_user, self.url, 'View retired resources')


class ResourceArchivedListViewTest(ResourceViewBaseTest):
    """Tests for ResourceArchivedListView"""
    fixtures = RESOURCE_FIXTURES

    def setUp(self):
        self.client.force_login(self.pi_user, backend=BACKEND)
        self.url = f'/resource/archived/'

    def test_archive_resources_show(self):
        ResourceFactory(name="archived_resource", resource_type__name='Compute Node', is_available=False)
        ResourceFactory(name="active_resource", resource_type__name='Compute Node')
        utils.page_contains_for_user(self, self.pi_user, self.url, 'archived_resource')
        utils.page_does_not_contain_for_user(self, self.pi_user, self.url, 'active_resource')
        utils.page_contains_for_user(self, self.admin_user, self.url, 'archived_resource')
        utils.page_does_not_contain_for_user(self, self.admin_user, self.url, 'active_resource')

    def test_can_filter_by_name(self):
        AttributeType.objects.get(name="Text")
        ResourceFactory(name="archived_resource", resource_type__name='Compute Node', is_available=False)
        ResourceFactory(name="archived_resource2", resource_type__name='Compute Node', is_available=False)
        ResourceFactory(name="active_resource", resource_type__name='Compute Node')
        search_url = f'{self.url}?resource_name=archived_resource'
        utils.page_contains_for_user(self, self.pi_user, search_url, 'archived_resource')
        utils.page_does_not_contain_for_user(self, self.pi_user, search_url, 'archived_resource2')
        utils.page_does_not_contain_for_user(self, self.pi_user, search_url, 'active_resource')
        search_url = f'{self.url}?resource_name=archived_resource2'
        utils.page_contains_for_user(self, self.pi_user, search_url, 'archived_resource2')
        utils.page_does_not_contain_for_user(self, self.pi_user, search_url, 'archived_resource')
        utils.page_does_not_contain_for_user(self, self.pi_user, search_url, 'active_resource')


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
