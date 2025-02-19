from django.test import TestCase, tag
from coldfront.core.test_helpers import utils
from coldfront.core.test_helpers.factories import setup_models
from coldfront.core.allocation.models import AllocationChangeRequest, AllocationChangeStatusChoice

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
