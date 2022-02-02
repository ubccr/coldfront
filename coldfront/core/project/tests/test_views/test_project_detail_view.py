from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.utils.tests.test_base import TestBase

from decimal import Decimal
from django.urls import reverse


class TestProjectDetailView(TestBase):
    """A class for testing ProjectDetailView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    @staticmethod
    def project_detail_url(pk):
        """Return the URL to the detail view for the Project with the
        given primary key."""
        return reverse('project-detail', kwargs={'pk': pk})

    def test_purchase_sus_button_invisible_for_ineligible_projects(self):
        """Test that the 'Purchase Service Units' button only appears
        for Projects that are eligible to do so."""
        for prefix in ('ac_', 'co_', 'fc_', 'ic_', 'pc_'):
            project = self.create_active_project_with_pi(
                f'{prefix}project', self.user)
            url = self.project_detail_url(project.pk)
            response = self.client.get(url)
            button_text = 'Purchase Service Units'
            if prefix == 'ac_':
                self.assertContains(response, button_text)
            else:
                self.assertNotContains(response, button_text)

    def test_purchase_sus_button_invisible_for_user_roles(self):
        """Test that the 'Purchase Service Units' button only appears
        for superusers, PIs, and Managers."""
        project = self.create_active_project_with_pi('ac_project', self.user)
        create_project_allocation(project, Decimal('0.00'))

        url = self.project_detail_url(project.pk)
        button_text = 'Purchase Service Units'

        project_user = ProjectUser.objects.get(project=project, user=self.user)
        self.assertEqual(project_user.role.name, 'Principal Investigator')
        response = self.client.get(url)
        self.assertContains(response, button_text)

        project_user.role = ProjectUserRoleChoice.objects.get(name='Manager')
        project_user.save()
        response = self.client.get(url)
        self.assertContains(response, button_text)

        project_user.role = ProjectUserRoleChoice.objects.get(name='User')
        project_user.save()
        response = self.client.get(url)
        self.assertNotContains(response, button_text)

        self.user.is_superuser = True
        self.user.save()
        response = self.client.get(url)
        self.assertContains(response, button_text)

    # TODO
