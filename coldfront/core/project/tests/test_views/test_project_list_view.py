from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.utils.tests.test_base import TestBase
from django.urls import reverse
from urllib.parse import urlencode


class TestProjectListView(TestBase):
    """A class for testing ProjectListView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    @staticmethod
    def project_list_url(**parameters):
        """Return the URL for listing Projects, including the given URL
        parameters."""
        return f'{reverse("project-list")}?{urlencode(parameters)}'

    def test_inactive_projects_included(self):
        """Test that Projects with the 'Inactive' status are included in
        the list."""
        active_name = 'active_project'
        active_status = ProjectStatusChoice.objects.get(name='Active')
        Project.objects.create(
            name=active_name, title=active_name, status=active_status)
        inactive_name = 'inactive_project'
        inactive_status = ProjectStatusChoice.objects.get(name='Inactive')
        Project.objects.create(
            name=inactive_name, title=inactive_name, status=inactive_status)

        # Grant the user superuser access to view all projects.
        self.user.is_superuser = True
        self.user.save()

        parameters = {
            'show_all_projects': 'on',
        }
        url = self.project_list_url(**parameters)
        response = self.client.get(url)

        self.assertContains(response, active_name)
        self.assertContains(response, inactive_name)

    def test_renew_pi_allowance_button_conditionally_visible(self):
        """Test that the button for renewing a PI's allowance is only
        visible for Users who are Active Managers or PIs of Projects."""
        url = self.project_list_url()
        button_text = 'Renew a PI\'s Allowance'

        project = Project.objects.create(
            name='fc_project',
            status=ProjectStatusChoice.objects.get(name='Active'))

        all_roles = ProjectUserRoleChoice.objects.distinct()
        all_statuses = ProjectUserStatusChoice.objects.distinct()

        successful_pairs = {
            ('Active', 'Manager'),
            ('Active', 'Principal Investigator'),
        }
        expected_num_successes = len(successful_pairs)
        actual_num_successes = 0
        expected_num_failures = (all_roles.count() * all_statuses.count() -
                                 expected_num_successes)
        actual_num_failures = 0

        for role in all_roles:
            for status in all_statuses:
                defaults = {
                    'role': role,
                    'status': status,
                }
                ProjectUser.objects.update_or_create(
                    project=project, user=self.user, defaults=defaults)
                response = self.client.get(url)

                if (status.name, role.name) in successful_pairs:
                    self.assertContains(response, button_text)
                    actual_num_successes = actual_num_successes + 1
                else:
                    self.assertNotContains(response, button_text)
                    actual_num_failures = actual_num_failures + 1

        self.assertEqual(expected_num_successes, actual_num_successes)
        self.assertEqual(expected_num_failures, actual_num_failures)

    # TODO
