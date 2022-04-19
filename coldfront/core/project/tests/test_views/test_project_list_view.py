from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
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

    def test_renew_pi_allowance_button_conditionally_enabled(self):
        """Test that the button for renewing a PI's allowance is only
        enabled for Users who are """

    # TODO
