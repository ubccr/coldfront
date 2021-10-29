from coldfront.core.project.forms import SavioProjectExistingPIForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.utils.tests.test_base import TestBase


class TestSavioProjectExistingPIForm(TestBase):
    """A class for testing SavioProjectExistingPIForm."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    def test_pis_with_inactive_fc_projects_disabled(self):
        """Test that PIs of Projects with the 'Inactive' status are
        disabled in the 'PI' field."""
        inactive_name = 'fc_inactive_project'
        inactive_status = ProjectStatusChoice.objects.get(name='Inactive')
        inactive_project = Project.objects.create(
            name=inactive_name, title=inactive_name, status=inactive_status)

        # Add the user as a PI on both Projects.
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_status = ProjectUserStatusChoice.objects.get(name='Active')
        kwargs = {
            'project': inactive_project,
            'role': pi_role,
            'status': active_status,
            'user': self.user,
        }
        ProjectUser.objects.create(**kwargs)

        form = SavioProjectExistingPIForm(allocation_type='FCA')
        pi_field_disabled_choices = form.fields['PI'].widget.disabled_choices
        self.assertIn(self.user.pk, pi_field_disabled_choices)

    # TODO
