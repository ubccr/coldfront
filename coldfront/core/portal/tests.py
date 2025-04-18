from django.test import TestCase, tag
from coldfront.core.test_helpers import utils
from coldfront.core.test_helpers.factories import setup_models
from coldfront.core.allocation.models import AllocationChangeRequest, AllocationChangeStatusChoice
from coldfront.core.test_helpers.factories import setup_models, ProjectFactory, ResourceFactory, ResourceAttributeTypeFactory, ResourceAttributeFactory
from coldfront.core.resource.models import AttributeType

UTIL_FIXTURES = ['coldfront/core/test_helpers/test_data/test_fixtures/ifx.json']

class PortalViewTest(TestCase):
    """Base class for portal view tests
    """
    fixtures = UTIL_FIXTURES

    @classmethod
    def setUpTestData(cls):
        """create test data for portal view tests
        """
        setup_models(cls)


class CenterSummaryTest(PortalViewTest):

    @tag('net')
    def test_center_summary(self):
        """check that center summary displays properly with the existing database
        """
        response = self.client.get('/center-summary')
        self.assertEqual(response.status_code, 200)


class HomePageTest(PortalViewTest):

    def test_pi_home_page(self):
        """check that the pi home page displays properly with the existing database
        """
        response = utils.login_and_get_page(self.client, self.pi_user, '')
        self.assertEqual(response.status_code, 200) # page renders
        self.assertContains(response, 'Projects') # page contains the title
        self.assertEqual(response.context['project_list'].count(), 1) # page contains the correct number of Projects
        self.assertEqual(response.context['allocation_list'].count(), 2) # page contains the correct number of Allocations

    def test_home_page_requests_view(self):
        # when PI has no requests, the requests table is not visible
        response = utils.login_and_get_page(self.client, self.pi_user, '')
        self.assertNotContains(response, 'Requests')
        # When PI has requests, the requests table is visible
        AllocationChangeRequest.objects.create(
            allocation=self.storage_allocation,
            status=AllocationChangeStatusChoice.objects.get(name='Pending')
            )
        response = self.client.get('')
        self.assertContains(response, 'Requests')
        # normal user sees no requests even when one exists
        response = utils.login_and_get_page(self.client, self.proj_allocationuser, '')
        self.assertNotContains(response, 'Requests')

    def test_home_page_allocations_display(self):
        """check that project allocations display properly on the home page
        """
        # PI sees allocation
        response = utils.login_and_get_page(self.client, self.pi_user, '')
        self.assertEqual(response.context['allocation_list'].count(), 2)
        # Storage Manager sees allocation
        response = utils.login_and_get_page(self.client, self.proj_datamanager, '')
        self.assertEqual(response.context['allocation_list'].count(), 1)
        # project user not belonging to allocation cannot see allocation
        response = utils.login_and_get_page(self.client, self.proj_nonallocationuser, '')
        self.assertEqual(response.context['allocation_list'].count(), 0)
        # allocation user not belonging to project cannot see storage allocation, can see cluster allocation
        response = utils.login_and_get_page(self.client, self.nonproj_allocationuser, '')
        self.assertEqual(response.context['allocation_list'].count(), 1)

    def test_home_page_projects_display(self):
        """check that projects display properly on the home page
        """
        # PI sees project
        response = utils.login_and_get_page(self.client, self.pi_user, '')
        self.assertEqual(response.context['project_list'].count(), 1)
        # Storage Manager sees project
        response = utils.login_and_get_page(self.client, self.proj_datamanager, '')
        self.assertEqual(response.context['project_list'].count(), 1)
        # project user can see project
        response = utils.login_and_get_page(self.client, self.proj_allocationuser, '')
        self.assertEqual(response.context['project_list'].count(), 1)
        # allocationuser not belonging to project cannot see project
        response = utils.login_and_get_page(self.client, self.nonproj_allocationuser, '')
        self.assertEqual(response.context['project_list'].count(), 0)

    def test_home_page_managed_resources_display(self):
        """check that managed resources display properly on the home page
        """
        ProjectFactory(pi=self.pi_user, title="managed_lab")
        ProjectFactory(pi=self.admin_user, title="admin_lab")
        text_attribute_type = AttributeType.objects.get(name="Text")
        managed_resource = ResourceFactory(name="managed_lab", resource_type__name='Compute Node')
        managed_resource2 = ResourceFactory(name="managed_lab2", resource_type__name='Compute Node')
        admin_resource = ResourceFactory(name="admin_lab", resource_type__name='Compute Node')
        owner_resourcer_attr_type = ResourceAttributeTypeFactory(name="Owner", attribute_type=text_attribute_type)
        ResourceAttributeFactory(resource_attribute_type=owner_resourcer_attr_type, value="managed_lab",
                                 resource=managed_resource)
        ResourceAttributeFactory(resource_attribute_type=owner_resourcer_attr_type, value="managed_lab",
                                 resource=managed_resource2)
        ResourceAttributeFactory(resource_attribute_type=owner_resourcer_attr_type, value="admin_lab",
                                 resource=admin_resource)
        utils.page_contains_for_user(self, self.pi_user, '', 'Managed Resources')
        utils.page_contains_for_user(self, self.admin_user, '', 'Managed Resources')
        utils.page_contains_for_user(self, self.pi_user, '', 'managed_lab')
        utils.page_contains_for_user(self, self.pi_user, '', 'managed_lab2')
        utils.page_does_not_contain_for_user(self, self.pi_user, '', 'admin_lab')
        utils.page_contains_for_user(self, self.admin_user, '', 'admin_lab')
        utils.page_does_not_contain_for_user(self, self.admin_user, '', 'managed_lab')
        utils.page_does_not_contain_for_user(self, self.admin_user, '', 'managed_lab2')

    def test_home_page_archive_resources_dont_show(self):
        ProjectFactory(pi=self.pi_user, title="managed_lab")
        text_attribute_type = AttributeType.objects.get(name="Text")
        owner_resourcer_attr_type = ResourceAttributeTypeFactory(name="Owner", attribute_type=text_attribute_type)
        archived_resource = ResourceFactory(name="archived_resource", resource_type__name='Compute Node', is_available=False)
        archived_resource2 = ResourceFactory(name="archived_resource2", resource_type__name='Compute Node', is_available=False)
        active_resource = ResourceFactory(name="active_resource", resource_type__name='Compute Node')
        ResourceAttributeFactory(resource_attribute_type=owner_resourcer_attr_type, value="managed_lab", resource=archived_resource)
        ResourceAttributeFactory(resource_attribute_type=owner_resourcer_attr_type, value="managed_lab", resource=archived_resource2)
        ResourceAttributeFactory(resource_attribute_type=owner_resourcer_attr_type, value="managed_lab", resource=active_resource)
        utils.page_contains_for_user(self, self.pi_user, '', 'active_resource')
        utils.page_does_not_contain_for_user(self, self.pi_user, '', 'archived_resource')
        utils.page_does_not_contain_for_user(self, self.pi_user, '', 'archived_resource2')
