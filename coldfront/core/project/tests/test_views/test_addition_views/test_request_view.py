from coldfront.core.allocation.models import AllocationAdditionRequest
from coldfront.core.allocation.models import AllocationAdditionRequestStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase

from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import Permission
from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse

from http import HTTPStatus


class TestAllocationAdditionRequestView(TestBase):
    """A class for testing AllocationAdditionRequestView."""

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

    @staticmethod
    def request_view_url(pk):
        """Return the URL to the request view for the Project with the
        given primary key."""
        return reverse('purchase-service-units', kwargs={'pk': pk})

    def test_ineligible_projects_redirected(self):
        """Test that requests for ineligible Projects are redirected
        back to the Project's Detail view."""
        for prefix in ('ac_', 'co_', 'fc_', 'ic_', 'pc_'):
            project = self.create_active_project_with_pi(
                f'{prefix}project', self.user)
            url = self.request_view_url(project.pk)
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
        project = self.create_active_project_with_pi('ac_project', self.user)
        url = self.request_view_url(project.pk)

        project_user = ProjectUser.objects.get(project=project, user=self.user)
        project_user.status = ProjectUserStatusChoice.objects.get(
            name='Removed')
        project_user.save()

        # Superusers should not have access.
        self.user.is_superuser = True
        self.user.save()
        self.assert_has_access(url, self.user, has_access=False)
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

        # Users with the permission to view AllocationAdditionRequests should
        # not have access. (Re-fetch the user to avoid permission caching.)
        permission = Permission.objects.get(
            codename='view_allocationadditionrequest')
        self.user.user_permissions.add(permission)
        self.user = User.objects.get(pk=self.user.pk)
        self.assertTrue(
            self.user.has_perm(f'allocation.{permission.codename}'))
        self.assert_has_access(url, self.user, has_access=False)

    def test_project_with_under_review_request_redirected(self):
        """Test that, if the Project already has an 'Under Review'
        request, the request is redirected."""
        project = self.create_active_project_with_pi('ac_project', self.user)

        request = AllocationAdditionRequest.objects.create(
            requester=self.user,
            project=project,
            status=AllocationAdditionRequestStatusChoice.objects.get(
                name='Complete'),
            num_service_units=Decimal('1000.00'))

        url = self.request_view_url(project.pk)

        for status in AllocationAdditionRequestStatusChoice.objects.all():
            request.status = status
            request.save()

            response = self.client.get(url)

            if status.name == 'Under Review':
                self.assertRedirects(
                    response, self.project_detail_url(project.pk))
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assertContains(response, 'Submit')

    def test_valid_post(self):
        """Test that a valid POST request creates an
        AllocationAdditionRequest and sends a notification email."""
        project = self.create_active_project_with_pi('ac_project', self.user)
        url = self.request_view_url(project.pk)

        self.assertEqual(AllocationAdditionRequest.objects.count(), 0)

        pre_time = utc_now_offset_aware()

        data = {
            'num_service_units': '100',
            'campus_chartstring': 'Campus Chartstring',
            'chartstring_account_type': 'Chartstring Account Type',
            'chartstring_contact_name': 'Chartstring Account Name',
            'chartstring_contact_email': 'charstring_contact@email.com',
        }
        response = self.client.post(url, data)

        post_time = utc_now_offset_aware()

        self.assertRedirects(response, self.project_detail_url(project.pk))
        messages = self.get_message_strings(response)
        self.assertEqual(len(messages), 1)
        self.assertIn('Thank you', messages[0])

        # A request should have been created.
        self.assertEqual(AllocationAdditionRequest.objects.count(), 1)
        request = AllocationAdditionRequest.objects.first()
        self.assertEqual(request.requester, self.user)
        self.assertEqual(request.project, project)
        self.assertEqual(request.status.name, 'Under Review')
        self.assertEqual(
            request.num_service_units, Decimal(data['num_service_units']))
        self.assertTrue(pre_time <= request.request_time <= post_time)
        extra_fields = request.extra_fields
        self.assertEqual(len(extra_fields) + 1, len(data))
        for field in data:
            if field == 'num_service_units':
                self.assertNotIn(field, extra_fields)
            else:
                self.assertEqual(data[field], extra_fields[field])

        # A notification email should have been sent to admins.
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]

        self.assertIn('New Service Units Purchase Request', email.subject)

        expected_body_snippets = [
            'There is a new request to purchase',
            project.name,
            self.user.first_name,
            self.user.last_name,
            reverse(
                'service-units-purchase-request-detail',
                kwargs={'pk': request.pk}),
        ]
        for expected_body_snippet in expected_body_snippets:
            self.assertIn(expected_body_snippet, email.body)

        expected_from_email = settings.EMAIL_SENDER
        self.assertEqual(expected_from_email, email.from_email)

        expected_to = sorted(settings.EMAIL_ADMIN_LIST)
        self.assertEqual(expected_to, sorted(email.to))
