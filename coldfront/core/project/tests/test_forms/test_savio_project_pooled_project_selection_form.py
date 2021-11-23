from coldfront.core.project.forms import SavioProjectPooledProjectSelectionForm
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.utils.tests.test_base import TestBase


class TestSavioProjectPooledProjectSelectionForm(TestBase):
    """A class for testing SavioProjectPooledProjectSelectionForm."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

    def test_inactive_projects_not_included_in_project_field(self):
        """Test that Projects with the 'Inactive' status are not
        included in the choices for the 'project' field."""
        active_name = 'fc_active_project'
        active_status = ProjectStatusChoice.objects.get(name='Active')
        active_project = Project.objects.create(
            name=active_name, title=active_name, status=active_status)
        inactive_name = 'fc_inactive_project'
        inactive_status = ProjectStatusChoice.objects.get(name='Inactive')
        Project.objects.create(
            name=inactive_name, title=inactive_name, status=inactive_status)

        form = SavioProjectPooledProjectSelectionForm(allocation_type='FCA')
        project_field_choices = form.fields['project'].queryset
        self.assertEqual(len(project_field_choices), 1)
        self.assertEqual(project_field_choices[0], active_project)

    # TODO
