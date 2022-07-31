from decimal import Decimal
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth.models import User
from django.core import mail
from django.urls import reverse
from flags.state import enable_flag
from iso8601 import iso8601

from coldfront.api.statistics.utils import create_project_allocation, \
    create_user_project_allocation
from coldfront.core.allocation.models import (Allocation,
                                              SecureDirRequest,
                                              SecureDirRequestStatusChoice,
                                              AllocationAttribute,
                                              AllocationAttributeType)
from coldfront.core.project.models import (ProjectUser,
                                           ProjectUserStatusChoice,
                                           ProjectUserRoleChoice, Project,
                                           ProjectStatusChoice)
from coldfront.core.resource.models import Resource
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase


class TestSecureDirRequestBase(TestBase):
    """A base testing class for secure directory manage user requests."""

    def setUp(self):
        """Set up test data."""
        enable_flag('SECURE_DIRS_REQUESTABLE')
        super().setUp()

        # Create two PIs.
        for i in range(2):
            pi = User.objects.create(
                username=f'pi{i}', email=f'pi{i}@nonexistent.com')
            user_profile = UserProfile.objects.get(user=pi)
            user_profile.is_pi = True
            user_profile.save()
            setattr(self, f'pi{i}', pi)

        # Create two Users.
        for i in range(2):
            user = User.objects.create(
                username=f'user{i}', email=f'user{i}@nonexistent.com')
            user_profile = UserProfile.objects.get(user=user)
            user_profile.cluster_uid = f'{i}'
            user_profile.save()
            setattr(self, f'user{i}', user)
            setattr(self, f'user_profile{i}', user_profile)

        # Create Projects and associate Users with them.
        project_status = ProjectStatusChoice.objects.get(name='Active')
        project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        user_role = ProjectUserRoleChoice.objects.get(name='User')
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        for i in range(2):
            # Create a Project and ProjectUsers.
            project = Project.objects.create(
                name=f'fc_project{i}', status=project_status)
            setattr(self, f'project{i}', project)
            for j in range(2):
                ProjectUser.objects.create(
                    user=getattr(self, f'user{j}'), project=project,
                    role=user_role, status=project_user_status)
                ProjectUser.objects.create(
                    user=getattr(self, f'pi{j}'), project=project, role=pi_role,
                    status=project_user_status)

            # Create a compute allocation for the Project.
            allocation = Decimal(f'{i + 1}000.00')
            create_project_allocation(project, allocation)

            # Create a compute allocation for each User on the Project.
            for j in range(2):
                create_user_project_allocation(
                    getattr(self, f'user{j}'), project, allocation / 2)

        # Create superuser
        self.admin = User.objects.create(username='admin')
        self.admin.is_superuser = True
        self.admin.save()

        # Create staff user
        self.staff = User.objects.create(
            username='staff', email='staff@nonexistent.com', is_staff=True)

        self.password = 'password'
        for user in User.objects.all():
            self.sign_user_access_agreement(user)
            user.set_password(self.password)
            user.save()


class TestSecureDirRequestWizard(TestSecureDirRequestBase):
    """A class for testing SecureDirRequestWizard."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.url = 'secure-dir-request'

    def get_form_data(self):
        """Generates valid form data for SecureDirRequestWizard."""
        view_name = 'secure_dir_request_wizard'
        current_step_key = f'{view_name}-current_step'
        data_description_form_data = {
            '0-data_description': 'a' * 20,
            '0-rdm_consultation': True,
            current_step_key: '0',
        }
        rdm_consultation_form_data = {
            '1-rdm_consultants': 'Tom and Jerry',
            current_step_key: '1',
        }
        directory_name_data = {
            '2-directory_name': 'test_dir',
            current_step_key: '2',
        }
        form_data = [
            data_description_form_data,
            rdm_consultation_form_data,
            directory_name_data
        ]

        return form_data

    def test_access(self):
        url = reverse(self.url, kwargs={'pk': self.project1.pk})
        self.assert_has_access(url, self.admin, True)
        self.assert_has_access(url, self.pi0, True)
        self.assert_has_access(url, self.pi1, True)
        self.assert_has_access(url, self.user0, False)

    def test_post_creates_request(self):
        """Test that a POST request creates a SecureDirRequest."""
        self.assertEqual(SecureDirRequest.objects.count(), 0)

        pre_time = utc_now_offset_aware()
        form_data = self.get_form_data()

        self.client.login(username=self.pi0.username, password=self.password)
        url = reverse(self.url, kwargs={'pk': self.project1.pk})

        for i, data in enumerate(form_data):
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(response, reverse('home'))

            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)

        requests = SecureDirRequest.objects.all()
        self.assertEqual(requests.count(), 1)

        request = requests.first()
        self.assertEqual(request.requester, self.pi0)
        self.assertEqual(
            request.data_description,
            form_data[0]['0-data_description'])
        self.assertEqual(
            request.rdm_consultation,
            form_data[1]['1-rdm_consultants'])
        self.assertEqual(
            request.directory_name,
            form_data[2]['2-directory_name'])
        self.assertEqual(request.project, self.project1)
        self.assertTrue(
            pre_time < request.request_time < utc_now_offset_aware())
        self.assertTrue(request.completion_time is None)
        self.assertEqual(request.status.name, 'Under Review')

    def test_emails_sent(self):
        """Test that a POST request sends the correct emails."""

        form_data = self.get_form_data()

        self.client.login(username=self.pi1.username, password=self.password)
        url = reverse(self.url, kwargs={'pk': self.project1.pk})
        for i, data in enumerate(form_data):
            response = self.client.post(url, data)
            if i == len(form_data) - 1:
                self.assertRedirects(response, reverse('home'))
            else:
                self.assertEqual(response.status_code, HTTPStatus.OK)

        # Test that the correct emails are sent.
        admin_email = settings.EMAIL_ADMIN_LIST
        pi0_email = self.pi0.email
        pi_email_body = [f'There is a new secure directory request for '
                         f'project {self.project1.name} requested by '
                         f'{self.pi1.first_name} {self.pi1.last_name}'
                         f' ({self.pi1.email})',
                         f'You may view the details of the request here:']
        admin_email_body = [f'There is a new secure directory request for '
                            f'project {self.project1.name} requested by '
                            f'{self.pi1.first_name} {self.pi1.last_name}'
                            f' ({self.pi1.email}).',
                            'Please review the request here:']

        self.assertEqual(2, len(mail.outbox))
        for email in mail.outbox:
            if email.to[0] in admin_email:
                for section in admin_email_body:
                    self.assertIn(section, email.body)
            elif email.to[0] == pi0_email:
                for section in pi_email_body:
                    self.assertIn(section, email.body)
            else:
                self.fail(f'Emails should only be sent to PI0 and admins.')
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)


class TestSecureDirRequestListView(TestSecureDirRequestBase):
    """A class for testing SecureDirRequestListView"""

    def setUp(self):
        super().setUp()

        self.completed_url = reverse('secure-dir-completed-request-list')
        self.pending_url = reverse('secure-dir-pending-request-list')

        # Create 2 SecureDirRequests
        self.request0 = SecureDirRequest.objects.create(
            directory_name='test_dir0',
            requester=self.pi0,
            data_description='a'*20,
            project=self.project0,
            status=SecureDirRequestStatusChoice.objects.get(name='Under Review'),
            request_time=utc_now_offset_aware()
        )

        self.request1 = SecureDirRequest.objects.create(
            directory_name='test_dir1',
            requester=self.pi1,
            data_description='a'*20,
            project=self.project1,
            status=SecureDirRequestStatusChoice.objects.get(name='Under Review'),
            request_time=utc_now_offset_aware()
        )

    def test_access(self):
        for url in [self.completed_url, self.pending_url]:
            self.assert_has_access(url, self.admin, True)
            self.assert_has_access(url, self.staff, True)
            self.assert_has_access(url, self.user0, False)
            self.assert_has_access(url, self.pi0, False)

    def test_pending_requests(self):
        """Test that pending requests are visible."""
        self.request1.status = \
            SecureDirRequestStatusChoice.objects.get(name='Approved - Processing')
        self.request1.save()
        self.request1.refresh_from_db()

        self.client.login(username=self.admin.username, password=self.password)
        response = self.client.get(self.pending_url)

        format_badge = '<span class="badge badge-warning">{}</span>'
        self.assertContains(response, self.project0.name)
        self.assertContains(response,
                            format_badge.format(self.request0.status.name))
        self.assertContains(response, self.project1.name)
        self.assertContains(response,
                            format_badge.format(self.request1.status.name))

        # Testing that the correct title is displayed.
        self.assertContains(response, 'Pending Secure Directory Requests')

    def test_no_pending_requests(self):
        """Test that the correct content is displayed when there are no
        pending requests."""
        for request in SecureDirRequest.objects.all():
            request.status = \
                SecureDirRequestStatusChoice.objects.get(name='Denied')
            request.save()

        self.client.login(username=self.admin.username, password=self.password)
        response = self.client.get(self.pending_url)

        self.assertNotContains(response, self.project0.name)
        self.assertNotContains(response, self.request0.status.name)
        self.assertNotContains(response, self.project1.name)
        self.assertNotContains(response, self.request1.status.name)

        self.assertContains(response, 'No pending secure directory requests!')

        # Testing that the correct title is displayed.
        self.assertContains(response, 'Pending Secure Directory Requests')

    def test_completed_requests(self):
        """Test that completed requests are visible."""
        self.request0.status = \
            SecureDirRequestStatusChoice.objects.get(name='Approved - Complete')
        self.request0.save()
        self.request1.status = \
            SecureDirRequestStatusChoice.objects.get(name='Denied')
        self.request1.save()

        self.client.login(username=self.admin.username, password=self.password)
        response = self.client.get(self.completed_url)

        self.assertContains(response, self.project0.name)
        self.assertContains(response,
                            '<span class="badge badge-success">Approved - Complete</span>')
        self.assertContains(response, self.project1.name)
        self.assertContains(response,
                            '<span class="badge badge-danger">Denied</span>')

        # Testing that the correct title is displayed.
        self.assertContains(response, 'Completed Secure Directory Requests')

    def test_no_completed_requests(self):
        """Test that the correct content is displayed when there are no
        completed requests."""
        for request in SecureDirRequest.objects.all():
            request.status = \
                SecureDirRequestStatusChoice.objects.get(name='Under Review')
            request.save()

        self.client.login(username=self.admin.username, password=self.password)
        response = self.client.get(self.completed_url)

        self.assertNotContains(response, self.project0.name)
        self.assertNotContains(response, self.request0.status.name)
        self.assertNotContains(response, self.project1.name)
        self.assertNotContains(response, self.request1.status.name)

        self.assertContains(response, 'No completed secure directory requests!')

        # Testing that the correct title is displayed.
        self.assertContains(response, 'Completed Secure Directory Requests')


class TestSecureDirRequestDetailView(TestSecureDirRequestBase):
    """Testing class for SecureDirRequestDetailView"""

    def setUp(self):
        super().setUp()

        # Create SecureDirRequest
        self.request0 = SecureDirRequest.objects.create(
            directory_name='test_dir',
            requester=self.pi0,
            data_description='a'*20,
            project=self.project0,
            status=SecureDirRequestStatusChoice.objects.get(name='Approved - Processing'),
            request_time=utc_now_offset_aware()
        )

        self.request0.state['rdm_consultation']['status'] = 'Approved'
        self.request0.state['mou']['status'] = 'Approved'
        self.request0.state['setup']['status'] = 'Completed'
        self.request0.save()

        self.url0 = reverse('secure-dir-request-detail',
                            kwargs={'pk': self.request0.pk})

    def test_access(self):
        self.assert_has_access(self.url0, self.admin, True)
        self.assert_has_access(self.url0, self.staff, True)
        self.assert_has_access(self.url0, self.user0, False)
        self.assert_has_access(self.url0, self.pi0, True)

    def test_content(self):
        """Test that the administrator checklist is only visible to admins."""
        self.client.login(username=self.admin.username, password=self.password)
        response = self.client.get(self.url0)
        html = response.content.decode('utf-8')
        self.assertIn('Administrator Checklist', html)
        self.client.logout()

        for user in [self.staff, self.pi0]:
            self.client.login(username=user.username, password=self.password)
            response = self.client.get(self.url0)
            html = response.content.decode('utf-8')
            self.assertNotIn('Administrator Checklist', html)
            self.client.logout()

    def test_post_request_approves_request(self):
        """Test that a POST request approves the SecureDirRequest."""
        pre_time = utc_now_offset_aware()
        self.client.login(username=self.admin.username, password=self.password)
        response = self.client.post(self.url0, {})

        self.request0.refresh_from_db()
        self.assertRedirects(response, reverse('secure-dir-pending-request-list'))
        self.assertEqual(self.request0.status.name, 'Approved - Complete')
        self.assertTrue(pre_time < self.request0.completion_time < utc_now_offset_aware())

    def test_post_request_creates_allocations(self):
        """Test that a POST request creates the correct allocations."""
        self.client.login(username=self.admin.username, password=self.password)
        response = self.client.post(self.url0, {})

        # Test that the groups directory is created correctly.
        groups_p2p3_directory = Resource.objects.get(name='Groups P2/P3 Directory')
        groups_alloc = Allocation.objects.filter(
            project=self.project0,
            resources__in=[groups_p2p3_directory])
        self.assertTrue(groups_alloc.exists())

        alloc_attr = AllocationAttribute.objects.filter(
            allocation=groups_alloc.first(),
            allocation_attribute_type=AllocationAttributeType.objects.get(
                name='Cluster Directory Access')
        )
        self.assertTrue(alloc_attr.exists())
        alloc_attr = alloc_attr.first()
        self.assertTrue(alloc_attr.value.endswith(self.request0.directory_name))

        # Test that the scratch directory is created correctly.
        scratch_p2p3_directory = Resource.objects.get(name='Scratch P2/P3 Directory')
        scratch_alloc = Allocation.objects.filter(
            project=self.project0,
            resources__in=[scratch_p2p3_directory])
        self.assertTrue(scratch_alloc.exists())

        alloc_attr = AllocationAttribute.objects.filter(
            allocation=scratch_alloc.first(),
            allocation_attribute_type=AllocationAttributeType.objects.get(
                name='Cluster Directory Access')
        )
        self.assertTrue(alloc_attr.exists())
        alloc_attr = alloc_attr.first()
        self.assertTrue(alloc_attr.value.endswith(self.request0.directory_name))

    def test_post_request_emails_sent(self):
        """Test that a POST request sends the correct emails."""
        self.client.login(username=self.admin.username, password=self.password)
        response = self.client.post(self.url0, {})

        # Test that the correct emails are sent.
        pi_emails = self.project0.projectuser_set.filter(
            role__name='Principal Investigator'
        ).values_list('user__email', flat=True)
        email_body = [f'Your request for a secure directory for project '
                      f'\'{self.project0.name}\' was approved. Setup '
                      f'on the cluster is complete.',
                      f'The paths to your secure group and scratch directories '
                      f'are \'/global/home/groups/pl1data/'
                      f'pl1_{self.request0.directory_name}\' and '
                      f'\'/global/scratch/p2p3/'
                      f'pl1_{self.request0.directory_name}\', '
                      f'respectively.']

        self.assertEqual(len(pi_emails), len(mail.outbox))
        for email in mail.outbox:
            self.assertIn(email.to[0], pi_emails)
            for section in email_body:
                self.assertIn(section, email.body)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)


class TestSecureDirRequestUndenyRequestView(TestSecureDirRequestBase):
    """Testing class for SecureDirRequestUndenyRequestView"""

    def setUp(self):
        super().setUp()

        # Create SecureDirRequest
        self.request0 = SecureDirRequest.objects.create(
            directory_name='test_dir',
            requester=self.pi0,
            data_description='a'*20,
            project=self.project0,
            status=SecureDirRequestStatusChoice.objects.get(name='Denied'),
            request_time=utc_now_offset_aware()
        )

        self.request0.state['rdm_consultation']['status'] = 'Denied'
        self.request0.state['rdm_consultation']['timestamp'] = '1234'
        self.request0.state['rdm_consultation']['justification'] = 'test reason'
        self.request0.state['mou']['status'] = 'Denied'
        self.request0.state['mou']['timestamp'] = '1234'
        self.request0.state['mou']['justification'] = 'test reason'
        self.request0.state['setup']['status'] = 'Completed'
        self.request0.state['setup']['timestamp'] = '1234'
        self.request0.state['setup']['justification'] = 'test reason'
        self.request0.state['other']['timestamp'] = '1234'
        self.request0.state['other']['justification'] = 'test reason'
        self.request0.save()

        self.url = reverse('secure-dir-request-undeny',
                           kwargs={'pk': self.request0.pk})
        self.success_url = reverse('secure-dir-request-detail',
                                   kwargs={'pk': self.request0.pk})

    def assert_has_access(self, url, user, has_access):
        """Assert that a user has or does not have access to a url."""
        self.client.login(username=user.username, password=self.password)
        status_code = HTTPStatus.FOUND if has_access else HTTPStatus.FORBIDDEN
        response = self.client.get(url)
        self.assertEqual(response.status_code, status_code)
        self.client.logout()

    def test_access(self):
        self.assert_has_access(self.url, self.staff, False)
        self.assert_has_access(self.url, self.user0, False)
        self.assert_has_access(self.url, self.pi0, False)
        self.assert_has_access(self.url, self.admin, True)

    def test_get_request_denies_request(self):
        """Test that a GET request undenies the SecureDirRequest."""
        self.client.login(username=self.admin.username, password=self.password)
        response = self.client.get(self.url)

        self.request0.refresh_from_db()
        self.assertRedirects(response, self.success_url)
        self.assertEqual(self.request0.status.name, 'Under Review')

        rdm_consultation = self.request0.state['rdm_consultation']
        self.assertEqual(rdm_consultation['status'], 'Pending')
        self.assertEqual(rdm_consultation['timestamp'], '')
        self.assertEqual(rdm_consultation['justification'], '')

        mou = self.request0.state['mou']
        self.assertEqual(mou['status'], 'Pending')
        self.assertEqual(mou['timestamp'], '')
        self.assertEqual(mou['justification'], '')

        setup = self.request0.state['setup']
        self.assertEqual(setup['status'], 'Pending')
        self.assertEqual(setup['timestamp'], '')
        self.assertEqual(setup['justification'], '')

        other = self.request0.state['other']
        self.assertEqual(other['timestamp'], '')
        self.assertEqual(other['justification'], '')


class TestSecureDirRequestReviewDenyView(TestSecureDirRequestBase):
    """Testing class for SecureDirRequestReviewDenyView"""

    def setUp(self):
        super().setUp()

        # Create SecureDirRequest
        self.request0 = SecureDirRequest.objects.create(
            directory_name='test_dir',
            requester=self.pi0,
            data_description='a'*20,
            project=self.project0,
            status=SecureDirRequestStatusChoice.objects.get(name='Approved - Processing'),
            request_time=utc_now_offset_aware()
        )

        self.request0.state['rdm_consultation']['status'] = 'Approved'
        self.request0.state['mou']['status'] = 'Approved'
        self.request0.state['other']['justification'] = \
            'This is a test justification.'
        self.request0.state['other']['timestamp'] = \
            utc_now_offset_aware().isoformat()
        self.request0.save()

        self.url = reverse('secure-dir-request-review-deny',
                           kwargs={'pk': self.request0.pk})
        self.success_url = reverse('secure-dir-request-detail',
                                   kwargs={'pk': self.request0.pk})

    def test_access(self):
        self.assert_has_access(self.url, self.admin, True)
        self.assert_has_access(self.url, self.staff, False)
        self.assert_has_access(self.url, self.user0, False)
        self.assert_has_access(self.url, self.pi0, False)

    def test_post_request_denies_request(self):
        """Test that a POST request denies the SecureDirRequest."""
        pre_time = utc_now_offset_aware()
        self.client.login(username=self.admin.username, password=self.password)
        data = {'justification': 'This is a test denial justification.'}
        response = self.client.post(self.url, data)

        self.request0.refresh_from_db()
        self.assertRedirects(response, self.success_url)
        self.assertEqual(self.request0.status.name, 'Denied')

        timestamp = iso8601.parse_date(self.request0.state['other']['timestamp'])
        self.assertTrue(pre_time < timestamp < utc_now_offset_aware())
        self.assertEqual(self.request0.state['other']['justification'], data['justification'])

    def test_post_request_sends_emails(self):
        """Test that a POST request sends the correct emails."""
        self.client.login(username=self.admin.username, password=self.password)
        data = {'justification': 'This is a test denial justification.'}
        response = self.client.post(self.url, data)

        # Test that the correct emails are sent.
        pi_emails = self.project0.projectuser_set.filter(
            role__name='Principal Investigator'
        ).values_list('user__email', flat=True)
        email_body = [f'Your request for a secure directory for project '
                      f'\'{self.project0.name}\' was denied for the '
                      f'following reason:',
                      data['justification'],
                      'If you have any questions, please contact us at']

        self.assertEqual(len(pi_emails), len(mail.outbox))
        for email in mail.outbox:
            self.assertIn(email.to[0], pi_emails)
            for section in email_body:
                self.assertIn(section, email.body)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)


class TestSecureDirRequestReviewRDMConsultView(TestSecureDirRequestBase):
    """Testing class for SecureDirRequestReviewRDMConsultView."""

    def setUp(self):
        super().setUp()

        # Create SecureDirRequest
        self.request0 = SecureDirRequest.objects.create(
            directory_name='test_dir',
            requester=self.pi0,
            data_description='a'*20,
            project=self.project0,
            status=SecureDirRequestStatusChoice.objects.get(name='Under Review'),
            request_time=utc_now_offset_aware()
        )

        self.url = reverse('secure-dir-request-review-rdm-consultation',
                           kwargs={'pk': self.request0.pk})
        self.success_url = reverse('secure-dir-request-detail',
                                   kwargs={'pk': self.request0.pk})

    def test_access(self):
        self.assert_has_access(self.url, self.admin, True)
        self.assert_has_access(self.url, self.staff, False)
        self.assert_has_access(self.url, self.user0, False)
        self.assert_has_access(self.url, self.pi0, False)

    def test_post_updates_request(self):
        """Test that a post request updates the request."""
        pre_time = utc_now_offset_aware()
        self.client.login(username=self.admin.username, password=self.password)
        data = {'status': 'Approved',
                'justification': 'This is a test rdm justification.'}
        response = self.client.post(self.url, data)

        self.request0.refresh_from_db()
        self.assertRedirects(response, self.success_url)
        self.assertEqual(self.request0.status.name, 'Under Review')
        self.assertEqual(self.request0.state['rdm_consultation']['status'], 'Approved')

        timestamp = iso8601.parse_date(self.request0.state['rdm_consultation']['timestamp'])
        self.assertTrue(pre_time < timestamp < utc_now_offset_aware())
        self.assertEqual(self.request0.state['rdm_consultation']['justification'],
                         data['justification'])

    def test_denied_status_denies_request(self):
        """Tests that a Denied status denies the request."""
        self.client.login(username=self.admin.username, password=self.password)
        data = {'status': 'Denied',
                'justification': 'This is a test denial justification.'}
        response = self.client.post(self.url, data)

        self.request0.refresh_from_db()
        self.assertRedirects(response, self.success_url)
        self.assertEqual(self.request0.status.name, 'Denied')

        # Test that the correct justification is sent in the email to PIs.
        for email in mail.outbox:
            self.assertIn(data['justification'], email.body)


class TestSecureDirRequestReviewMOUView(TestSecureDirRequestBase):
    """Testing class for SecureDirRequestReviewMOUView."""

    def setUp(self):
        super().setUp()

        # Create SecureDirRequest
        self.request0 = SecureDirRequest.objects.create(
            directory_name='test_dir',
            requester=self.pi0,
            data_description='a'*20,
            project=self.project0,
            status=SecureDirRequestStatusChoice.objects.get(name='Under Review'),
            request_time=utc_now_offset_aware()
        )

        self.request0.state['rdm_consultation']['status'] = 'Approved'
        self.request0.state['rdm_consultation']['timestamp'] = \
            utc_now_offset_aware().isoformat()
        self.request0.save()

        self.url = reverse('secure-dir-request-review-mou',
                           kwargs={'pk': self.request0.pk})
        self.success_url = reverse('secure-dir-request-detail',
                                   kwargs={'pk': self.request0.pk})

    def test_access(self):
        self.assert_has_access(self.url, self.admin, True)
        self.assert_has_access(self.url, self.staff, False)
        self.assert_has_access(self.url, self.user0, False)
        self.assert_has_access(self.url, self.pi0, False)

    def test_post_updates_request(self):
        """Test that a post request updates the request."""
        pre_time = utc_now_offset_aware()
        self.client.login(username=self.admin.username, password=self.password)
        data = {'status': 'Approved',
                'justification': 'This is a test mou justification.'}
        response = self.client.post(self.url, data)

        self.request0.refresh_from_db()
        self.assertRedirects(response, self.success_url)
        self.assertEqual(self.request0.status.name, 'Approved - Processing')
        self.assertEqual(self.request0.state['mou']['status'], 'Approved')

        timestamp = iso8601.parse_date(self.request0.state['mou']['timestamp'])
        self.assertTrue(pre_time < timestamp < utc_now_offset_aware())
        self.assertEqual(self.request0.state['mou']['justification'], data['justification'])

    def test_denied_status_denies_request(self):
        """Tests that a Denied status denies the request."""
        self.client.login(username=self.admin.username, password=self.password)
        data = {'status': 'Denied',
                'justification': 'This is a test denial justification.'}
        response = self.client.post(self.url, data)

        self.request0.refresh_from_db()
        self.assertRedirects(response, self.success_url)
        self.assertEqual(self.request0.status.name, 'Denied')

        # Test that the correct justification is sent in the email to PIs.
        for email in mail.outbox:
            self.assertIn(data['justification'], email.body)


class TestSecureDirRequestReviewSetupView(TestSecureDirRequestBase):
    """Testing class for SecureDirRequestReviewSetupView."""

    def setUp(self):
        super().setUp()

        # Create SecureDirRequest
        self.request0 = SecureDirRequest.objects.create(
            directory_name='test_dir',
            requester=self.pi0,
            data_description='a'*20,
            project=self.project0,
            status=SecureDirRequestStatusChoice.objects.get(name='Approved - Processing'),
            request_time=utc_now_offset_aware()
        )

        self.request0.state['rdm_consultation']['status'] = 'Approved'
        self.request0.state['rdm_consultation']['timestamp'] = \
            utc_now_offset_aware().isoformat()
        self.request0.state['mou']['status'] = 'Approved'
        self.request0.state['mou']['timestamp'] = \
            utc_now_offset_aware().isoformat()
        self.request0.save()

        self.url = reverse('secure-dir-request-review-setup',
                           kwargs={'pk': self.request0.pk})
        self.success_url = reverse('secure-dir-request-detail',
                                   kwargs={'pk': self.request0.pk})

    def test_access(self):
        self.assert_has_access(self.url, self.admin, True)
        self.assert_has_access(self.url, self.staff, False)
        self.assert_has_access(self.url, self.user0, False)
        self.assert_has_access(self.url, self.pi0, False)

    def test_post_updates_request(self):
        """Test that a post request updates the request."""
        pre_time = utc_now_offset_aware()
        self.client.login(username=self.admin.username, password=self.password)
        data = {'status': 'Completed',
                'directory_name': 'changed_dir',
                'justification': 'This is a test setup justification.'}
        response = self.client.post(self.url, data)

        self.request0.refresh_from_db()
        self.assertRedirects(response, self.success_url)
        self.assertEqual(self.request0.directory_name, data['directory_name'])
        self.assertEqual(self.request0.status.name, 'Approved - Processing')
        self.assertEqual(self.request0.state['setup']['status'], 'Completed')

        timestamp = iso8601.parse_date(self.request0.state['setup']['timestamp'])
        self.assertTrue(pre_time < timestamp < utc_now_offset_aware())
        self.assertEqual(self.request0.state['setup']['justification'], data['justification'])

    def test_denied_status_denies_request(self):
        """Tests that a Denied status denies the request."""
        self.client.login(username=self.admin.username, password=self.password)
        data = {'status': 'Denied',
                'justification': 'This is a test denial justification.'}
        response = self.client.post(self.url, data)

        self.request0.refresh_from_db()
        self.assertRedirects(response, self.success_url)
        self.assertEqual(self.request0.status.name, 'Denied')

        # Test that the correct justification is sent in the email to PIs.
        for email in mail.outbox:
            self.assertIn(data['justification'], email.body)