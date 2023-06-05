from django.test import TestCase, tag
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
        self.client.force_login(self.pi_user)
        response = self.client.get('')
        self.assertEqual(response.status_code, 200) # page renders
        self.assertContains(response, 'Projects') # page contains the title
        self.assertEqual(response.context['project_list'].count(), 1) # page contains the correct number of Projects
        self.assertEqual(response.context['allocation_list'].count(), 1) # page contains the correct number of Allocations

    def test_home_page_requests_view(self):
        # when PI has no requests, the requests table is not visible
        self.client.force_login(self.pi_user)
        response = self.client.get('')
        self.assertNotContains(response, 'Requests')
        # When PI has requests, the requests table is visible
        AllocationChangeRequest.objects.create(
            allocation=self.proj_allocation,
            status=AllocationChangeStatusChoice.objects.get(name='Pending')
            )
        response = self.client.get('')
        self.assertContains(response, 'Requests')
        # normal user sees no requests even when one exists

    def home_create_project_button_visible(self):
        """check that the create project button is visible on the home page
        """
