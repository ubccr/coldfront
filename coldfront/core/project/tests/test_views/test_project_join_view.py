from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.utils.tests.test_base import TestBase
from django.urls import reverse


class TestProjectJoinView(TestBase):
    """A class for testing ProjectJoinView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    @staticmethod
    def project_join_url(pk):
        """Return the URL for joining the Project with the given primary
        key."""
        return reverse('project-join', kwargs={'pk': pk})

    def test_inactive_projects_cannot_be_joined(self):
        """Test that Projects with the 'Inactive' status cannot be
        joined."""
        name = 'inactive_project'
        inactive_status = ProjectStatusChoice.objects.get(name='Inactive')
        project = Project.objects.create(
            name=name, title=name, status=inactive_status)

        url = self.project_join_url(project.pk)
        data = {
            'reason': 'This is a test reason for joining the project.',
        }
        response = self.client.post(url, data)

        expected = f'Project {name} is inactive, and may not be joined.'
        messages = list(response.context['messages'])
        self.assertEqual(len(messages), 1)
        actual = messages[0].message
        self.assertEqual(expected, actual)

    # TODO
