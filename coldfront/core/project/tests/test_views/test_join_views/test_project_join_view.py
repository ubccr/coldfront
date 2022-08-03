from django.contrib.auth.models import User

from coldfront.core.project.models import Project, ProjectUser, \
    ProjectUserRoleChoice, ProjectUserStatusChoice, ProjectUserJoinRequest
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

    def test_host_user(self):
        """Test that ProjectJoinView sets the host user in
        ProjectUserJoinRequest if a host user is passed."""
        # Create PI to set as host user.
        pi = User.objects.create(
            email='pi@@lbl.gov',
            first_name='PI',
            last_name='User',
            username='pi')
        pi.set_password(self.password)
        pi.save()

        # Create test project.
        active_status = ProjectStatusChoice.objects.get(name='Active')
        project0 = Project.objects.create(
            name='project0', title='project0', status=active_status)
        ProjectUser.objects.create(
            project=project0,
            user=pi,
            status=ProjectUserStatusChoice.objects.get(name='Active'),
            role=ProjectUserRoleChoice.objects.get(name='Principal Investigator')
        )

        url = self.project_join_url(project0.pk)
        data = {
            'reason': 'This is a test reason for joining the project '
                      'with a host.',
            'host_user': 'pi'
        }
        response = self.client.post(url, data)

        join_request = ProjectUserJoinRequest.objects.filter(project_user__user=self.user,
                                                             project_user__project=project0)
        self.assertTrue(join_request.exists())
        self.assertEqual(join_request.first().host_user, pi)
        self.assertEqual(join_request.first().reason, data['reason'])

    def test_no_host_user(self):
        """Test that ProjectJoinView does not set the host user in
        ProjectUserJoinRequest if a host user is not passed."""
        # Create PI to set as host user.
        pi = User.objects.create(
            email='pi@@lbl.gov',
            first_name='PI',
            last_name='User',
            username='pi')
        pi.set_password(self.password)
        pi.save()

        # Create test project.
        project0 = self.create_active_project_with_pi('project0', pi)

        url = self.project_join_url(project0.pk)
        data = {
            'reason': 'This is a test reason for joining the project '
                      'with a host.'
        }
        response = self.client.post(url, data)

        join_request = ProjectUserJoinRequest.objects.filter(project_user__user=self.user,
                                                             project_user__project=project0)
        self.assertTrue(join_request.exists())
        self.assertIsNone(join_request.first().host_user)
        self.assertEqual(join_request.first().reason, data['reason'])

    # TODO
