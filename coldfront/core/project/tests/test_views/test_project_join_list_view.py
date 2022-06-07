from copy import deepcopy
from urllib.parse import urlencode

from coldfront.core.project.models import Project, ProjectUser, \
    ProjectUserStatusChoice, ProjectUserRoleChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.tests.test_base import TestBase

from django.contrib.auth.models import User
from django.conf import settings
from django.test import override_settings
from django.urls import reverse

from flags.state import disable_flag
from flags.state import enable_flag


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

    def test_host_user_selectable(self):
        """Testing that the option to select a host user and the help text
        about selecting a host user are correctly displayed"""

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

        url = self.project_join_list_url()

        # Setting LRC_ONLY to True and BRC_ONLY to False
        flags_copy = deepcopy(settings.FLAGS)
        flags_copy['LRC_ONLY'] = [{'condition': 'boolean', 'value': True}]
        flags_copy['BRC_ONLY'] = [{'condition': 'boolean', 'value': False}]
        with override_settings(FLAGS=flags_copy):
            # Help text and form should be available to non-LBL employees
            # with no host.
            response = self.client.get(url)
            html = response.content.decode('utf-8')

            help_message = 'not an LBL employee with an LBL email (@lbl.gov),'
            host_user_form = '<div id="div_id_host_user" class="form-group"> ' \
                             '<label for="id_host_user" class=" requiredField">'
            self.assertIn(help_message, html)
            self.assertIn(host_user_form, html)

            # Help text and form are not available to LBL employees.
            self.user.email = 'user@lbl.gov'
            self.user.save()
            response = self.client.get(url)
            html = response.content.decode('utf-8')

            help_message = 'not an LBL employee with an LBL email (@lbl.gov),'
            host_user_form = '<div id="div_id_host_user" class="form-group"> ' \
                             '<label for="id_host_user" class=" requiredField">'
            self.assertNotIn(help_message, html)
            self.assertNotIn(host_user_form, html)
            self.user.email = 'user@email.com'
            self.user.save()

            # Help text and form not available if user already has host user.
            user_profile = UserProfile.objects.get(user=self.user)
            user_profile.host_user = pi
            user_profile.save()

            response = self.client.get(url)
            html = response.content.decode('utf-8')

            help_message = 'not an LBL employee with an LBL email (@lbl.gov),'
            host_user_form = '<div id="div_id_host_user" class="form-group"> ' \
                             '<label for="id_host_user" class=" requiredField">'
            self.assertNotIn(help_message, html)
            self.assertNotIn(host_user_form, html)
            user_profile.host_user = None
            user_profile.save()

        # Setting LRC_ONLY to False and BRC_ONLY to True
        flags_copy['BRC_ONLY'] = [{'condition': 'boolean', 'value': True}]
        flags_copy['LRC_ONLY'] = [{'condition': 'boolean', 'value': False}]
        with override_settings(FLAGS=flags_copy):
            # Help text and form not available if LRC_ONLY flag set to false.
            response = self.client.get(url)
            html = response.content.decode('utf-8')

            help_message = 'not an LBL employee with an LBL email (@lbl.gov),'
            host_user_form = '<div id="div_id_host_user" class="form-group"> ' \
                             '<label for="id_host_user" class=" requiredField">'
            self.assertNotIn(help_message, html)
            self.assertNotIn(host_user_form, html)

    # TODO
