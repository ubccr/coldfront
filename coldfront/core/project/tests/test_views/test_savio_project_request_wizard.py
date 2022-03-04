from coldfront.core.project.models import Project
from coldfront.core.project.models import SavioProjectAllocationRequest
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

    @staticmethod
    def request_url():
        """Return the URL for requesting to create a new Savio
        project."""
        return reverse('savio-project-request')

    def test_post_creates_request(self):
        """Test that a POST request creates a
        SavioProjectAllocationRequest."""
        self.assertEqual(SavioProjectAllocationRequest.objects.count(), 0)
        self.assertEqual(Project.objects.count(), 0)

        view_name = 'savio_project_request_wizard'
        current_step_key = f'{view_name}-current_step'
        allocation_type_form_data = {
            '0-allocation_type': 'FCA',
            current_step_key: '0',
        }
        existing_pi_form_data = {
            '1-PI': self.user.pk,
            current_step_key: '1',
        }
        pool_allocations_data = {
            '5-pool': False,
            current_step_key: '5',
        }
        details_data = {
            '7-name': 'name',
            '7-title': 'title',
            '7-description': 'a' * 20,
            current_step_key: '7',
        }
        survey_data = {
            '8-scope_and_intent': 'b' * 20,
            '8-computational_aspects': 'c' * 20,
            current_step_key: '8',
        }
        form_data = [
            allocation_type_form_data,
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
            allocation_type_form_data['0-allocation_type'])
        self.assertEqual(request.pi, self.user)
        self.assertEqual(request.project, project)
        self.assertEqual(project.name, f'fc_{details_data["7-name"]}')
        self.assertEqual(project.title, details_data['7-title'])
        self.assertEqual(project.description, details_data['7-description'])
        self.assertFalse(request.pool)
        self.assertEqual(
            request.survey_answers['scope_and_intent'],
            survey_data['8-scope_and_intent'])
        self.assertEqual(
            request.survey_answers['computational_aspects'],
            survey_data['8-computational_aspects'])
        self.assertEqual(request.status.name, 'Under Review')

    # TODO
