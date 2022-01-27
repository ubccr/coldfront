from bs4 import BeautifulSoup

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.api.statistics.utils import set_project_usage_value
from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.allocation.models import AllocationAdditionRequestStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase

from decimal import Decimal
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.urls import reverse
from http import HTTPStatus


class TestAllocationAdditionRequestLandingView(TestBase):
    """A class for testing AllocationAdditionRequestLandingView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    @staticmethod
    def create_active_project(project_name, pi_user):
        """Create an 'Active' Project with the given name and the given
        user as its PI. Return the Project."""
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        project = Project.objects.create(
            name=project_name,
            title=project_name,
            status=active_project_status)
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        ProjectUser.objects.create(
            project=project,
            role=pi_role,
            status=active_project_user_status,
            user=pi_user)
        return project

    @staticmethod
    def landing_view_url(pk):
        """Return the URL to the request landing view for the Project
        with the given primary key."""
        return reverse('purchase-service-units-landing', kwargs={'pk': pk})

    @staticmethod
    def project_detail_url(pk):
        """Return the URL to the detail view for the Project with the
        given primary key."""
        return reverse('project-detail', kwargs={'pk': pk})

    @staticmethod
    def request_view_url(pk):
        """Return the URL to the request view for the Project with the
        given primary key."""
        return reverse('purchase-service-units', kwargs={'pk': pk})

    def test_allocation_usage_displayed(self):
        """Test that the project's current 'Service Units' usage of its
        total allocation is displayed on a GET request."""
        project = self.create_active_project('ac_project', self.user)

        allocation_value = Decimal('1000.00')
        usage_value = Decimal('500.00')

        create_project_allocation(project, allocation_value)
        set_project_usage_value(project, usage_value)

        url = self.landing_view_url(project.pk)
        response = self.client.get(url)

        self.assertContains(response, allocation_value)
        self.assertContains(response, usage_value)

    def test_continue_button_conditionally_disabled(self):
        """Test that, if the Project already has an 'Under Review'
        request, the button redirecting to the form to request another
        is disabled."""
        project = self.create_active_project('ac_project', self.user)

        allocation_value = Decimal('1000.00')
        usage_value = Decimal('500.00')

        create_project_allocation(project, allocation_value)
        set_project_usage_value(project, usage_value)

        request = AllocationAdditionRequest.objects.create(
            requester=self.user,
            project=project,
            status=AllocationAdditionRequestStatusChoice.objects.get(
                name='Complete'),
            num_service_units=Decimal('1000.00'))

        for status in AllocationAdditionRequestStatusChoice.objects.all():
            request.status = status
            request.save()

            url = self.landing_view_url(project.pk)
            response = self.client.get(url)
            html = response.content.decode('utf-8')
            soup = BeautifulSoup(html, 'html.parser')

            if status.name == 'Under Review':
                button = soup.find(
                    'button', {'id': 'continue-button-disabled'})
                self.assertIsNotNone(button.get('disabled'))
            else:
                a = soup.find('a', {'id': 'continue-button-enabled'})
                self.assertEqual(
                    a.get('href'), self.request_view_url(project.pk))

    def test_ineligible_projects_redirected(self):
        """Test that GET requests for ineligible Projects are redirected
        back to the Project's Detail view."""
        for prefix in ('ac_', 'co_', 'fc_', 'ic_', 'pc_'):
            project = self.create_active_project(
                f'{prefix}project', self.user)
            url = self.landing_view_url(project.pk)
            response = self.client.get(url)
            messages = self.get_message_strings(response)
            if prefix == 'ac_':
                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assertFalse(messages)
            else:
                self.assertRedirects(
                    response, self.project_detail_url(project.pk))
                self.assertEqual(len(messages), 1)
                self.assertIn('ineligible', messages[0])

    def test_permissions_get(self):
        """Test that the correct users have permissions to perform GET
        requests."""
        project = self.create_active_project('ac_project', self.user)
        url = self.landing_view_url(project.pk)

        project_user = ProjectUser.objects.get(project=project, user=self.user)
        project_user.status = ProjectUserStatusChoice.objects.get(
            name='Removed')
        project_user.save()

        # Superusers should have access.
        self.user.is_superuser = True
        self.user.save()
        self.assert_has_access(url, self.user)
        self.user.is_superuser = False
        self.user.save()

        # Active PIs and Managers of the Project who have signed the access
        # agreement should have access.
        for status in ProjectUserStatusChoice.objects.all():
            project_user.status = status
            for role in ProjectUserRoleChoice.objects.all():
                project_user.role = role
                project_user.save()
                for signed_status in (True, False):
                    self.user.userprofile.access_agreement_signed_date = (
                        utc_now_offset_aware() if signed_status else None)
                    self.user.userprofile.save()
                    has_access = (
                        status.name == 'Active' and
                        role.name in ('Principal Investigator', 'Manager') and
                        signed_status)
                    self.assert_has_access(
                        url, self.user, has_access=has_access)

        project_user.delete()

        # Users with the permission to view should have access. (Re-fetch the
        # user to avoid permission caching.)
        permission = Permission.objects.get(
            codename='view_allocationadditionrequest')
        self.user.user_permissions.add(permission)
        self.user = User.objects.get(pk=self.user.pk)
        self.assertTrue(
            self.user.has_perm(f'allocation.{permission.codename}'))
        self.assert_has_access(url, self.user)
