from coldfront.core.project.forms_.renewal_forms.request_forms import ProjectRenewalProjectSelectionForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.utils.tests.test_base import TestBase


class TestProjectRenewalProjectSelectionForm(TestBase):
    """A class for testing ProjectRenewalProjectSelectionForm."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    def test_inactive_projects_included_in_project_field(self):
        """Test that Projects with the 'Inactive' status are included in
        the choices for the 'project' field."""
        active_name = 'fc_active_project'
        active_status = ProjectStatusChoice.objects.get(name='Active')
        active_project = Project.objects.create(
            name=active_name, title=active_name, status=active_status)
        inactive_name = 'fc_inactive_project'
        inactive_status = ProjectStatusChoice.objects.get(name='Inactive')
        inactive_project = Project.objects.create(
            name=inactive_name, title=inactive_name, status=inactive_status)

        # Add the user as a PI on both Projects.
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_status = ProjectUserStatusChoice.objects.get(name='Active')
        kwargs = {
            'role': pi_role,
            'status': active_status,
            'user': self.user,
        }
        for project in (active_project, inactive_project):
            kwargs['project'] = project
            ProjectUser.objects.create(**kwargs)

        kwargs = {
            'pi_pk': self.user.pk,
            'non_owned_projects': False,
            'exclude_project_pk': None,
        }
        form = ProjectRenewalProjectSelectionForm(**kwargs)

        project_field_choices = form.fields['project'].queryset
        self.assertEqual(len(project_field_choices), 2)
        self.assertIn(active_project, project_field_choices)
        self.assertIn(inactive_project, project_field_choices)

    # TODO
