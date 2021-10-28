from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.utils.tests.test_base import TestBase
from django.urls import reverse
from urllib.parse import urlencode


class TestProjectJoinListView(TestBase):
    """A class for testing ProjectJoinListView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    @staticmethod
    def project_join_list_url(**parameters):
        """Return the URL for listing Projects to join, including the
        given URL parameters."""
        return f'{reverse("project-join-list")}?{urlencode(parameters)}'

    def test_inactive_projects_not_included(self):
        """Test that Projects with the 'Inactive' status are not
        included in the list."""
        active_name = 'active_project'
        active_status = ProjectStatusChoice.objects.get(name='Active')
        Project.objects.create(
            name=active_name, title=active_name, status=active_status)
        inactive_name = 'inactive_project'
        inactive_status = ProjectStatusChoice.objects.get(name='Inactive')
        Project.objects.create(
            name=inactive_name, title=inactive_name, status=inactive_status)

        url = self.project_join_list_url()
        response = self.client.get(url)

        self.assertContains(response, active_name)
        self.assertNotContains(response, inactive_name)

    # TODO
