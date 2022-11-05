from coldfront.core.project.models import Project
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.models import Resource
from coldfront.core.resource.utils_.allowance_utils.constants import BRCAllowances
from coldfront.core.resource.utils_.allowance_utils.interface import ComputingAllowanceInterface
from coldfront.core.utils.tests.test_base import TestBase
from django.urls import reverse
from http import HTTPStatus


class TestSavioProjectRequestWizard(TestBase):
    """A class for testing SavioProjectRequestWizard."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

        self.interface = ComputingAllowanceInterface()

    @staticmethod
    def request_url():
        """Return the URL for requesting to create a new Savio
        project."""
        return reverse('new-project-request')

    def test_post_creates_request(self):
        """Test that a POST request creates a
        SavioProjectAllocationRequest."""
        self.assertEqual(SavioProjectAllocationRequest.objects.count(), 0)
        self.assertEqual(Project.objects.count(), 0)

        computing_allowance = Resource.objects.get(name=BRCAllowances.FCA)
        allocation_period = get_current_allowance_year_period()

        view_name = 'savio_project_request_wizard'
        current_step_key = f'{view_name}-current_step'
        computing_allowance_form_data = {
            '0-computing_allowance': computing_allowance.pk,
            current_step_key: '0',
        }
        allocation_period_form_data = {
            '1-allocation_period': allocation_period.pk,
            current_step_key: '1',
        }
        existing_pi_form_data = {
            '2-PI': self.user.pk,
            current_step_key: '2',
        }
        pool_allocations_data = {
            '6-pool': False,
            current_step_key: '6',
        }
        details_data = {
            '8-name': 'name',
            '8-title': 'title',
            '8-description': 'a' * 20,
            current_step_key: '8',
        }
        survey_data = {
            '10-scope_and_intent': 'b' * 20,
            '10-computational_aspects': 'c' * 20,
            current_step_key: '10',
        }
        form_data = [
            computing_allowance_form_data,
            allocation_period_form_data,
            existing_pi_form_data,
            pool_allocations_data,
            details_data,
            survey_data,
        ]

        url = self.request_url()
        for i, data in enumerate(form_data):
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(response, reverse('home'))
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)

        requests = SavioProjectAllocationRequest.objects.all()
        self.assertEqual(requests.count(), 1)
        projects = Project.objects.all()
        self.assertEqual(projects.count(), 1)

        request = requests.first()
        project = projects.first()
        self.assertEqual(request.requester, self.user)
        self.assertEqual(
            request.allocation_type,
            self.interface.name_short_from_name(computing_allowance.name))
        self.assertEqual(request.computing_allowance, computing_allowance)
        self.assertEqual(request.allocation_period, allocation_period)
        self.assertEqual(request.pi, self.user)
        self.assertEqual(request.project, project)
        self.assertEqual(project.name, f'fc_{details_data["8-name"]}')
        self.assertEqual(project.title, details_data['8-title'])
        self.assertEqual(project.description, details_data['8-description'])
        self.assertFalse(request.pool)
        self.assertEqual(
            request.survey_answers['scope_and_intent'],
            survey_data['10-scope_and_intent'])
        self.assertEqual(
            request.survey_answers['computational_aspects'],
            survey_data['10-computational_aspects'])
        self.assertEqual(request.status.name, 'Under Review')

    # TODO
