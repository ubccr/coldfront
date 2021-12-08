from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.utils.tests.test_base import TestBase
from django.urls import reverse


class TestUserProjectsManagersView(TestBase):
    """A class for testing UserProjectsManagersView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    @staticmethod
    def user_projects_managers_url(username=None):
        """Return the URL for viewing the Projects and managers of the
        User with the given username."""
        kwargs = {'viewed_username': username} if username else {}
        return reverse('user-projects-managers', kwargs=kwargs)

    def test_inactive_projects_included(self):
        """Test that Projects with the 'Inactive' status are included in
        the view."""
        active_name = 'active_project'
        active_status = ProjectStatusChoice.objects.get(name='Active')
        active_project = Project.objects.create(
            name=active_name, title=active_name, status=active_status)
        inactive_name = 'inactive_project'
        inactive_status = ProjectStatusChoice.objects.get(name='Inactive')
        inactive_project = Project.objects.create(
            name=inactive_name, title=inactive_name, status=inactive_status)

        # Add the user to both Projects.
        user_role = ProjectUserRoleChoice.objects.get(name='User')
        active_status = ProjectUserStatusChoice.objects.get(name='Active')
        kwargs = {
            'role': user_role,
            'status': active_status,
            'user': self.user,
        }
        for project in (active_project, inactive_project):
            kwargs['project'] = project
            ProjectUser.objects.create(**kwargs)

        url = self.user_projects_managers_url()
        response = self.client.get(url)

        self.assertContains(response, active_name)
        self.assertContains(response, inactive_name)

    # TODO
