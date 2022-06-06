from decimal import Decimal
from http import HTTPStatus

from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core import mail
from django.core.management import call_command
from django.urls import reverse

from coldfront.api.statistics.utils import create_project_allocation, \
    create_user_project_allocation
from coldfront.core.allocation.models import (Allocation,
                                              AllocationStatusChoice,
                                              SecureDirAddUserRequest,
                                              SecureDirAddUserRequestStatusChoice,
                                              SecureDirRemoveUserRequest,
                                              SecureDirRemoveUserRequestStatusChoice,
                                              AllocationUser,
                                              AllocationUserStatusChoice)
from coldfront.core.allocation.utils import create_secure_dirs
from coldfront.core.project.models import (ProjectUser,
                                           ProjectUserStatusChoice,
                                           ProjectUserRoleChoice, Project,
                                           ProjectStatusChoice)
from coldfront.core.user.models import UserProfile
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase


class TestSecureDirBase(TestBase):
    """A base testing class for secure directory manage user requests."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        self.pi = User.objects.create(
            username='pi0', email='pi0@nonexistent.com')
        user_profile = UserProfile.objects.get(user=self.pi)
        user_profile.is_pi = True
        user_profile.save()

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
        manager_role = ProjectUserRoleChoice.objects.get(name='Manager')
        for i in range(2):
            # Create a Project and ProjectUsers.
            project = Project.objects.create(
                name=f'project{i}', status=project_status)
            setattr(self, f'project{i}', project)
            for j in range(2):
                ProjectUser.objects.create(
                    user=getattr(self, f'user{j}'), project=project,
                    role=user_role, status=project_user_status)
            ProjectUser.objects.create(
                user=self.pi, project=project, role=manager_role,
                status=project_user_status)

            # Create a compute allocation for the Project.
            allocation = Decimal(f'{i + 1}000.00')
            create_project_allocation(project, allocation)

            # Create a compute allocation for each User on the Project.
            for j in range(2):
                create_user_project_allocation(
                    getattr(self, f'user{j}'), project, allocation / 2)

        # Make PI for project1
        pi = ProjectUser.objects.get(project=self.project1,
                                     user=self.pi,
                                     status=ProjectUserStatusChoice.objects.get(
                                         name='Active'))
        pi.role = ProjectUserRoleChoice.objects.get(name='Principal '
                                                         'Investigator')
        pi.save()

        # Create superuser
        self.admin = User.objects.create(username='admin')
        self.admin.is_superuser = True
        self.admin.save()

        # Create staff user
        self.staff = User.objects.create(
            username='staff', email='staff@nonexistent.com', is_staff=True)

        self.groups_subdirectory_name = 'project1/test_groups'
        self.scratch_subdirectory_name = 'test_scratch'
        call_command('add_directory_defaults')
        self.groups_allocation, self.scratch2_allocation = \
            create_secure_dirs(self.project1,
                               self.groups_subdirectory_name,
                               self.scratch_subdirectory_name)

        for alloc in [self.groups_allocation, self.scratch2_allocation]:
            AllocationUser.objects.create(
                allocation=alloc,
                user=self.pi,
                status=AllocationUserStatusChoice.objects.get(name='Active')
            )

        self.groups_path = self.groups_allocation.allocationattribute_set.get(
            allocation_attribute_type__name__icontains='Directory').value

        self.scratch2_path = \
            self.scratch2_allocation.allocationattribute_set.get(
                allocation_attribute_type__name__icontains='Directory').value

        self.password = 'password'
        for user in User.objects.all():
            user.set_password(self.password)
            user.save()


    def get_response(self, user, url, kwargs=None):
        """Returns the response to a GET request."""
        self.client.login(username=user.username, password=self.password)
        url = reverse(url, kwargs=kwargs)
        response = self.client.get(url)
        self.client.logout()
        return response

    def post_response(self, user, url, kwargs=None, data=None):
        """Returns the response to a POST request."""
        self.client.login(username=user.username, password=self.password)
        url = reverse(url, kwargs=kwargs)
        response = self.client.post(url, data, follow=True)
        self.client.logout()
        return response

    def assert_has_access(self, user, url, has_access, kwargs=None):
        """Assert that a user has or does not have access to a url."""
        self.client.login(username=user.username, password=self.password)
        url = reverse(url, kwargs=kwargs)
        status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
        response = self.client.get(url)
        self.assertEqual(response.status_code, status_code)
        self.client.logout()

    def get_message_strings(self, response):
        """Return messages included in the given response as a list of
        strings."""
        return [str(m) for m in get_messages(response.wsgi_request)]


class TestSecureDirManageUsersView(TestSecureDirBase):
    """A class for testing SecureDirManageUsersView."""

    def setUp(self):
        super().setUp()
        self.url = 'secure-dir-manage-users'

    def test_access(self):
        """Test that the correct users have access to
        SecureDirManageUsersView"""
        url = self.url
        for allocation in [self.groups_allocation, self.scratch2_allocation]:
            for action in ['add', 'remove']:
                kwargs = {'pk': allocation.pk, 'action': action}

                # Admin and PIs have access
                self.assert_has_access(self.admin, url, True, kwargs)
                self.assert_has_access(self.pi, url, True, kwargs)

                # Staff and normal users do not have access
                self.assert_has_access(self.staff, url, False, kwargs)
                self.assert_has_access(self.user1, url, False, kwargs)

    def test_correct_users_to_add(self):
        """Test that the correct users to be added are displayed by
        SecureDirManageUsersView."""
        # Create another project with the same PI and new users
        temp_project = Project.objects.create(name='temp_project',
                                              status=ProjectStatusChoice.objects.get(
                                                  name='Active'))
        ProjectUser.objects.create(
            project=temp_project,
            user=self.pi,
            status=ProjectUserStatusChoice.objects.get(name='Active'),
            role=ProjectUserRoleChoice.objects.get(
                name='Principal Investigator'))

        for i in range(2, 5):
            temp_user = User.objects.create(username=f'user{i}',
                                            email=f'email{i}@email.com')
            ProjectUser.objects.create(
                project=temp_project,
                user=temp_user,
                status=ProjectUserStatusChoice.objects.get(name='Active'),
                role=ProjectUserRoleChoice.objects.get(name='User'))
            setattr(self, f'user{i}', temp_user)

        # Users with a pending SecureDirAddUserRequest should not be shown
        SecureDirAddUserRequest.objects.create(
            user=self.user1,
            allocation=self.groups_allocation,
            status=SecureDirAddUserRequestStatusChoice.objects.get(
                name='Pending'))

        # Users with a pending SecureDirRemoveUserRequest should not be shown
        SecureDirRemoveUserRequest.objects.create(
            user=self.user2,
            allocation=self.groups_allocation,
            status=SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Pending'))

        # Users with a completed SecureDirRemoveUserRequest should be shown
        SecureDirRemoveUserRequest.objects.create(
            user=self.user3,
            allocation=self.groups_allocation,
            status=SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Complete'))

        # Users that are already part of the allocation should not be shown.
        AllocationUser.objects.create(
            allocation=self.groups_allocation,
            user=self.user3,
            status=AllocationUserStatusChoice.objects.get(name='Active'))

        # Testing users shown on groups_allocation add users page
        kwargs = {'pk': self.groups_allocation.pk, 'action': 'add'}
        response = self.get_response(self.pi,
                                     self.url,
                                     kwargs=kwargs)
        html = response.content.decode('utf-8')
        self.assertIn(self.user0.username, html)
        self.assertIn(self.user4.username, html)

        self.assertNotIn(self.user1.username, html)
        self.assertNotIn(self.user2.username, html)
        self.assertNotIn(self.user3.username, html)
        self.assertNotIn(self.admin.username, html)

        # Testing users shown on scratch2_allocation add users page
        kwargs = {'pk': self.scratch2_allocation.pk, 'action': 'add'}
        response = self.get_response(self.pi,
                                     self.url,
                                     kwargs=kwargs)
        html = response.content.decode('utf-8')
        self.assertIn(self.user0.username, html)
        self.assertIn(self.user1.username, html)
        self.assertIn(self.user2.username, html)
        self.assertIn(self.user3.username, html)
        self.assertIn(self.user4.username, html)

        self.assertNotIn(self.admin.username, html)

    def test_correct_users_to_remove(self):
        """Test that the correct users to be removed are displayed by
        SecureDirManageUsersView."""

        # Adding users to allocation
        for i in range(2, 5):
            temp_user = User.objects.create(username=f'user{i}')
            AllocationUser.objects.create(
                allocation=self.groups_allocation,
                user=temp_user,
                status=AllocationUserStatusChoice.objects.get(name='Active'))
            setattr(self, f'user{i}', temp_user)

        # Users with a pending SecureDirRemoveUserRequest should not be shown
        SecureDirRemoveUserRequest.objects.create(
            user=self.user2,
            allocation=self.groups_allocation,
            status=SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Pending'))

        # Testing users shown on groups_allocation remove users page
        kwargs = {'pk': self.groups_allocation.pk, 'action': 'remove'}
        response = self.get_response(self.pi,
                                     self.url,
                                     kwargs=kwargs)
        html = response.content.decode('utf-8')
        self.assertIn(self.user3.username, html)
        self.assertIn(self.user4.username, html)

        self.assertNotIn(self.user0.username, html)
        self.assertNotIn(self.user1.username, html)
        self.assertNotIn(self.user2.username, html)
        self.assertNotIn(self.admin.username, html)

        # Testing users shown on scratch2_allocation remove users page
        kwargs = {'pk': self.scratch2_allocation.pk, 'action': 'remove'}
        response = self.get_response(self.pi,
                                     self.url,
                                     kwargs=kwargs)
        html = response.content.decode('utf-8')

        self.assertNotIn(self.user0.username, html)
        self.assertNotIn(self.user1.username, html)
        self.assertNotIn(self.user2.username, html)
        self.assertNotIn(self.user3.username, html)
        self.assertNotIn(self.user4.username, html)
        self.assertNotIn(self.admin.username, html)

    def test_add_users(self):
        """Test that the correct SecureDirAddUserRequest is created"""

        # Sending a request to add user0
        form_data = {'userform-TOTAL_FORMS': ['1'],
                     'userform-INITIAL_FORMS': ['1'],
                     'userform-MIN_NUM_FORMS': ['0'],
                     'userform-MAX_NUM_FORMS': ['2'],
                     'userform-0-selected': ['on']}

        pre_time = utc_now_offset_aware()

        kwargs = {'pk': self.scratch2_allocation.pk, 'action': 'add'}
        response = self.post_response(self.pi,
                                      self.url,
                                      kwargs=kwargs,
                                      data=form_data)

        request = SecureDirAddUserRequest.objects.filter(
            allocation=self.scratch2_allocation,
            status=SecureDirAddUserRequestStatusChoice.objects.get(
                name='Pending'),
            directory=self.scratch2_path)
        self.assertTrue(request.exists())

        request = request.first()
        self.assertTrue(request.completion_time is None)
        self.assertTrue(pre_time <=
                        request.request_time <=
                        utc_now_offset_aware())

        # Test that the user is redirected.
        self.assertRedirects(response,
                             reverse('allocation-detail',
                                     kwargs={
                                         'pk': self.scratch2_allocation.pk}))

        # Test that the correct email is sent.
        recipients = settings.EMAIL_ADMIN_LIST
        email_body = [f'There is 1 new secure '
                      f'directory user addition request for '
                      f'{self.scratch2_path}.',
                      'Please process this request here.']

        self.assertEqual(len(recipients), len(mail.outbox))
        for email in mail.outbox:
            for section in email_body:
                self.assertIn(section, email.body)
            self.assertIn(email.to[0], recipients)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def test_remove_users(self):
        """Test that the correct SecureDirRemoveUserRequest is created"""
        # Add users to allocation.
        for i in range(2):
            AllocationUser.objects.create(
                allocation=self.groups_allocation,
                user=getattr(self, f'user{i}'),
                status=AllocationUserStatusChoice.objects.get(name='Active'))

        # Sending a request to remove user0 and user1
        form_data = {'userform-TOTAL_FORMS': ['2'],
                     'userform-INITIAL_FORMS': ['2'],
                     'userform-MIN_NUM_FORMS': ['0'],
                     'userform-MAX_NUM_FORMS': ['2'],
                     'userform-0-selected': ['on'],
                     'userform-1-selected': ['on']}

        pre_time = utc_now_offset_aware()

        kwargs = {'pk': self.groups_allocation.pk, 'action': 'remove'}
        response = self.post_response(self.pi,
                                      self.url,
                                      kwargs=kwargs,
                                      data=form_data)

        for user in [self.user0, self.user1]:
            request = SecureDirRemoveUserRequest.objects.filter(
                user=user,
                allocation=self.groups_allocation,
                status=SecureDirRemoveUserRequestStatusChoice.objects.get(
                    name='Pending'))
            self.assertTrue(request.exists())

            request = request.first()
            self.assertTrue(request.completion_time is None)
            self.assertTrue(pre_time <=
                            request.request_time <=
                            utc_now_offset_aware())

        # Test that the user is redirected.
        self.assertRedirects(response,
                             reverse('allocation-detail',
                                     kwargs={'pk': self.groups_allocation.pk}))

        # Test that the correct email is sent.
        recipients = settings.EMAIL_ADMIN_LIST
        email_body = [f'There are 2 new secure '
                      f'directory user removal requests for '
                      f'{self.groups_path}.',
                      'Please process these requests here.']

        self.assertEqual(len(recipients), len(mail.outbox))
        for email in mail.outbox:
            for section in email_body:
                self.assertIn(section, email.body)
            self.assertIn(email.to[0], recipients)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def test_content(self):
        """Test that the correct variables are displayed."""

        # Groups alllocation with no users to remove
        kwargs = {'pk': self.groups_allocation.pk, 'action': 'add'}
        response = self.get_response(self.pi,
                                     self.url,
                                     kwargs=kwargs)
        html = response.content.decode('utf-8')
        self.assertIn(
            f'Add users to: {self.groups_path}',
            html)

        # Scratch2 allocation with no users to remove
        kwargs = {'pk': self.scratch2_allocation.pk, 'action': 'remove'}
        response = self.get_response(self.pi,
                                     self.url,
                                     kwargs=kwargs)
        html = response.content.decode('utf-8')

        self.assertIn(
            f'Remove users from: {self.scratch2_path}',
            html)


class TestSecureDirManageUsersRequestListView(TestSecureDirBase):
    """Testing class for SecureDirManageUsersRequestListView"""

    def setUp(self):
        super().setUp()
        self.url = 'secure-dir-manage-users-request-list'

    def test_access(self):
        """Testing access to SecureDirManageUsersRequestListView"""
        # Only superusers have access

        for status in ['pending', 'complete']:
            for action in ['add', 'remove']:
                kwargs = {'status': status, 'action': action}

                # Admins and staff have access.
                self.assert_has_access(self.admin, self.url, True, kwargs)
                self.assert_has_access(self.staff, self.url, True, kwargs)

                # Normal users do not have access.
                self.assert_has_access(self.user0, self.url, False, kwargs)
                self.assert_has_access(self.user1, self.url, False, kwargs)
                self.assert_has_access(self.pi, self.url, False, kwargs)

    def test_no_requests(self):
        """Testing messages in SecureDirManageUsersRequestListView when
        there are no requests."""
        for status in ['pending', 'completed']:
            for action in ['add', 'remove']:
                kwargs = {'status': status, 'action': action}

                response = self.get_response(self.admin, self.url,
                                             kwargs=kwargs)
                html = response.content.decode('utf-8')

                if status == 'completed':
                    message = f'No completed secure directory {action}' \
                              f' user requests!'
                else:
                    message = f'No new or pending secure directory {action}' \
                              f' user requests!'

                self.assertIn(message, html)

    def test_correct_add_user_requests_shown(self):
        """Testing that the correct add user requests are shown."""

        for i in range(2, 5):
            temp_user = User.objects.create(username=f'user{i}',
                                            email=f'email{i}@email.com')
            setattr(self, f'user{i}', temp_user)

        SecureDirAddUserRequest.objects.create(
            user=self.user0,
            allocation=self.groups_allocation,
            status=SecureDirAddUserRequestStatusChoice.objects.get(
                name='Pending'),
            directory=self.groups_path)

        SecureDirAddUserRequest.objects.create(
            user=self.user1,
            allocation=self.groups_allocation,
            status=SecureDirAddUserRequestStatusChoice.objects.get(
                name='Complete'),
            directory=self.groups_path)

        SecureDirAddUserRequest.objects.create(
            user=self.user2,
            allocation=self.scratch2_allocation,
            status=SecureDirAddUserRequestStatusChoice.objects.get(
                name='Denied'),
            directory=self.scratch2_allocation)

        # Testing pending requests
        kwargs = {'status': 'pending', 'action': 'add'}
        response = self.get_response(self.admin, self.url, kwargs=kwargs)
        html = response.content.decode('utf-8')

        self.assertIn(self.user0.username, html)
        self.assertIn(self.groups_path, html)
        self.assertIn('Pending', html)

        # Testing completed requests
        kwargs = {'status': 'completed', 'action': 'add'}
        response = self.get_response(self.admin, self.url, kwargs=kwargs)
        html = response.content.decode('utf-8')

        self.assertIn(self.user1.username, html)
        self.assertIn(self.user2.username, html)
        self.assertIn(self.groups_path, html)
        self.assertIn('Complete', html)
        self.assertIn('Denied', html)

    def test_correct_remove_user_requests_shown(self):
        """Testing that the correct remove user requests are shown."""

        for i in range(2, 5):
            temp_user = User.objects.create(username=f'user{i}',
                                            email=f'email{i}@email.com')
            setattr(self, f'user{i}', temp_user)

        SecureDirRemoveUserRequest.objects.create(
            user=self.user0,
            allocation=self.groups_allocation,
            status=SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Pending'),
            directory=self.groups_path)

        SecureDirRemoveUserRequest.objects.create(
            user=self.user1,
            allocation=self.groups_allocation,
            status=SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Complete'),
            directory=self.groups_path)

        SecureDirRemoveUserRequest.objects.create(
            user=self.user2,
            allocation=self.scratch2_allocation,
            status=SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Denied'),
            directory=self.scratch2_path)

        # Testing pending requests
        kwargs = {'status': 'pending', 'action': 'remove'}
        response = self.get_response(self.admin, self.url, kwargs=kwargs)
        html = response.content.decode('utf-8')

        self.assertIn(self.user0.username, html)
        self.assertIn(self.groups_path, html)
        self.assertIn('Pending', html)

        # Testing completed requests
        kwargs = {'status': 'completed', 'action': 'remove'}
        response = self.get_response(self.admin, self.url, kwargs=kwargs)
        html = response.content.decode('utf-8')

        self.assertIn(self.user1.username, html)
        self.assertIn(self.user2.username, html)
        self.assertIn(self.groups_path, html)
        self.assertIn('Complete', html)
        self.assertIn('Denied', html)


class TestSecureDirManageUsersDenyRequestView(TestSecureDirBase):
    """Testing class for SecureDirManageUsersDenyRequestView"""

    def setUp(self):
        super().setUp()

        self.add_request = SecureDirAddUserRequest.objects.create(
            user=self.user0,
            allocation=self.groups_allocation,
            status=SecureDirAddUserRequestStatusChoice.objects.get(
                name='Pending'),
            directory=self.groups_path)

        self.remove_request = SecureDirRemoveUserRequest.objects.create(
            user=self.user1,
            allocation=self.scratch2_allocation,
            status=SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Pending'),
            directory=self.scratch2_path)

        for i, user in enumerate([self.user0, self.user1]):
            user.first_name = f'first{i}'
            user.last_name = f'last{i}'
            user.set_password(self.password)
            user.save()

        self.url = 'secure-dir-manage-user-deny-request'

    def test_access(self):
        """Testing access to SecureDirManageUsersDenyRequestView"""

        # Only superusers can access SecureDirManageUsersDenyRequestView

        def status_code_test(response, has_access):
            status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
            self.assertEqual(response.status_code, status_code)

        def reset_status(request):
            if isinstance(request, SecureDirAddUserRequest):
                status_obj = SecureDirAddUserRequestStatusChoice
            elif isinstance(request, SecureDirRemoveUserRequest):
                status_obj = SecureDirRemoveUserRequestStatusChoice
            else:
                raise ValueError('reset_status: illegal request type.')

            request.status = status_obj.objects.get(name__icontains='Pending')
            request.save()
            request.refresh_from_db()

        for action, request in [('add', self.add_request),
                                ('remove', self.remove_request)]:
            kwargs = {'pk': request.pk, 'action': action}
            data = {'reason': ''}

            # Admin have access
            status_code_test(
                self.post_response(self.admin, self.url, kwargs, data), True)
            reset_status(request)

            # Staff and normal users do not have access
            status_code_test(
                self.post_response(self.staff, self.url, kwargs, data), False)

            status_code_test(
                self.post_response(self.user0, self.url, kwargs, data), False)

            status_code_test(
                self.post_response(self.user1, self.url, kwargs, data), False)

            status_code_test(
                self.post_response(self.pi, self.url, kwargs, data), False)

    def test_deny_add_request(self):
        """Testing that the correct status is set and emails are sent
        when denying a SecureDirAddUserRequest"""

        kwargs = {'pk': self.add_request.pk, 'action': 'add'}
        data = {'reason': 'This is a test for denying SecureDirAddUserRequest.'}
        pre_time = utc_now_offset_aware()

        response = self.post_response(self.admin, self.url, kwargs, data)

        # Test that the correct status and completion time are set
        self.add_request.refresh_from_db()
        self.assertEqual(self.add_request.status.name, 'Denied')
        self.assertTrue(pre_time <=
                        self.add_request.completion_time <=
                        utc_now_offset_aware())

        # Test that the correct emails are sent
        recipients = [self.pi.email, self.user0.email]
        email_body = [f'The request to add first0 last0 (user0) to '
                      f'the secure directory {self.groups_path} '
                      f'has been denied for the following reason:',
                      f'"{data["reason"]}"',
                      'If you have any questions, please contact us at']
        email_subject = 'Secure Directory Addition Request Denied'

        self.assertEqual(len(recipients), len(mail.outbox))
        for email in mail.outbox:
            for section in email_body:
                self.assertIn(section, email.body)
            self.assertIn(email_subject, email.subject)
            self.assertIn(email.to[0], recipients)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)

        # Test that the correct message is displayed.
        expected_message = \
            f'Secure directory addition request for user '\
            f'{self.add_request.user.username} for the secure directory '\
            f'{self.add_request.directory} has been denied.'
        messages = self.get_message_strings(response)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], expected_message)

        # Test that the user is redirected.
        self.assertRedirects(response,
                             reverse(f'secure-dir-manage-users-request-list',
                                     kwargs={'action': 'add',
                                             'status': 'pending'}))

    def test_deny_removal_request(self):
        """Testing that the correct status is set and emails are sent
        when denying a SecureDirRemoveUserRequest"""

        kwargs = {'pk': self.remove_request.pk, 'action': 'remove'}
        data = {
            'reason': 'This is a test for denying SecureDirRemoveUserRequest.'}
        pre_time = utc_now_offset_aware()

        response = self.post_response(self.admin, self.url, kwargs, data)

        # Test that the correct status and completion time are set
        self.remove_request.refresh_from_db()
        self.assertEqual(self.remove_request.status.name, 'Denied')
        self.assertTrue(pre_time <=
                        self.remove_request.completion_time <=
                        utc_now_offset_aware())

        # Test that the correct emails are sent
        recipients = [self.pi.email, self.user1.email]
        email_body = [f'The request to remove first1 last1 (user1) from '
                      f'the secure directory {self.scratch2_path} has '
                      f'been denied for the following reason:',
                      f'"{data["reason"]}"',
                      'If you have any questions, please contact us at']
        email_subject = 'Secure Directory Removal Request Denied'

        self.assertEqual(len(recipients), len(mail.outbox))
        for email in mail.outbox:
            for section in email_body:
                self.assertIn(section, email.body)
            self.assertIn(email_subject, email.subject)
            self.assertIn(email.to[0], recipients)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)

        # Test that the correct message is displayed.
        expected_message = \
            f'Secure directory removal request for user ' \
            f'{self.remove_request.user.username} for the secure directory ' \
            f'{self.remove_request.directory} has been denied.'
        messages = self.get_message_strings(response)
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], expected_message)

        # Test that the user is redirected.
        self.assertRedirects(response,
                             reverse(f'secure-dir-manage-users-request-list',
                                     kwargs={'action': 'remove',
                                             'status': 'pending'}))

    def test_deny_removal_request_bad_status(self):
        """Testing that the user is redirected and no updates are
        made to the request if the status is not pending or processing"""

        self.remove_request.status = \
            SecureDirRemoveUserRequestStatusChoice.objects.get(name='Complete')
        self.remove_request.save()

        kwargs = {'pk': self.remove_request.pk, 'action': 'remove'}
        data = {
            'reason': 'This is a test for denying SecureDirRemoveUserRequest.'}

        response = self.post_response(self.admin, self.url, kwargs, data)

        messages = self.get_message_strings(response)
        expected_message = f'Secure directory user removal request ' \
                           f'has unexpected status "Complete."'
        self.assertEqual(len(messages), 1)
        self.assertEqual(messages[0], expected_message)

        # Test that the user is redirected.
        self.assertRedirects(response,
                             reverse(f'secure-dir-manage-users-request-list',
                                     kwargs={'action': 'remove',
                                             'status': 'pending'}))

        # Test that the status and completion time are not changed
        self.remove_request.refresh_from_db()
        self.assertEqual(self.remove_request.status.name, 'Complete')
        self.assertTrue(self.remove_request.completion_time is None)


class TestSecureDirManageUsersUpdateStatusView(TestSecureDirBase):
    """Testing class for SecureDirManageUsersUpdateStatusView"""

    def setUp(self):
        super().setUp()

        self.add_request = SecureDirAddUserRequest.objects.create(
            user=self.user0,
            allocation=self.groups_allocation,
            status=SecureDirAddUserRequestStatusChoice.objects.get(
                name='Pending'),
            directory=self.groups_path)

        self.remove_request = SecureDirRemoveUserRequest.objects.create(
            user=self.user1,
            allocation=self.scratch2_allocation,
            status=SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Pending'),
            directory=self.scratch2_path)

        self.url = 'secure-dir-manage-user-update-status'

    def test_access(self):
        """Testing access to SecureDirManageUsersUpdateStatusView"""

        for request, action in [(self.add_request, 'add'),
                                (self.remove_request, 'remove')]:
            kwargs = {'pk': request.pk, 'action': action}

            # Only admins should have access
            self.assert_has_access(self.admin, self.url, True, kwargs)

            self.assert_has_access(self.staff, self.url, False, kwargs)
            self.assert_has_access(self.pi, self.url, False, kwargs)
            self.assert_has_access(self.user0, self.url, False, kwargs)
            self.assert_has_access(self.user1, self.url, False, kwargs)

    def test_status_updated(self):
        """Testing that the request status is updated"""

        for request, action in [(self.add_request, 'add'),
                                (self.remove_request, 'remove')]:
            kwargs = {'pk': request.pk, 'action': action}
            data = {'status': 'Processing'}

            response = self.post_response(self.admin, self.url, kwargs=kwargs,
                                          data=data)

            request.refresh_from_db()
            self.assertEqual(request.status.name,
                             f'Processing')

            # Test that the correct message is shown
            expected_message = (
                f'Secure directory '
                f'{"addition" if action == "add" else "removal"} request '
                f'for user {request.user.username} for '
                f'{request.directory} has been marked as "Processing".')
            messages = self.get_message_strings(response)
            self.assertEqual(len(messages), 1)
            self.assertEqual(expected_message, messages[0])

            # Test that the user is redirected.
            self.assertRedirects(response,
                                 reverse('secure-dir-manage-users-request-list',
                                         kwargs={'action': action,
                                                 'status': 'pending'}))

    def test_status_not_updated(self):
        """Testing that the request status is not updated if the same
        status is passed"""

        for request, action in [(self.add_request, 'add'),
                                (self.remove_request, 'remove')]:
            kwargs = {'pk': request.pk, 'action': action}
            data = {'status': 'Pending'}

            response = self.post_response(self.admin, self.url, kwargs=kwargs,
                                          data=data)

            request.refresh_from_db()
            self.assertEqual(request.status.name, 'Pending')

            # Test that the correct message is shown
            expected_message = (
                f'Secure directory '
                f'{"addition" if action == "add" else "removal"} request '
                f'for user {request.user.username} for '
                f'{request.directory} has been marked as "Pending".')
            messages = self.get_message_strings(response)
            self.assertEqual(len(messages), 1)
            self.assertEqual(expected_message, messages[0])

            # Test that the user is redirected.
            self.assertRedirects(response,
                                 reverse('secure-dir-manage-users-request-list',
                                         kwargs={'action': action,
                                                 'status': 'pending'}))

    def test_bad_request_status(self):
        """Testing that the correct message is shown for a bad
        request status."""

        self.add_request.status = \
            SecureDirAddUserRequestStatusChoice.objects.get(
                name='Denied')
        self.add_request.save()
        self.remove_request.status = \
            SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Processing')
        self.remove_request.save()

        for request, action in [(self.add_request, 'add'),
                                (self.remove_request, 'remove')]:
            kwargs = {'pk': request.pk, 'action': action}
            data = {'status': 'Processing'}

            response = self.post_response(self.admin, self.url, kwargs=kwargs,
                                          data=data)
            messages = self.get_message_strings(response)

            expected_message = (
                f'Secure directory user '
                f'{"addition" if action == "add" else "removal"}'
                f' request has unexpected status '
                f'"{request.status.name}."')

            self.assertEqual(len(messages), 1)
            self.assertEqual(expected_message, messages[0])


class TestSecureDirManageUsersCompleteStatusView(TestSecureDirBase):
    """Testing class for SecureDirManageUsersCompleteStatusView"""

    def setUp(self):
        super().setUp()

        self.add_request = SecureDirAddUserRequest.objects.create(
            user=self.user0,
            allocation=self.groups_allocation,
            status=SecureDirAddUserRequestStatusChoice.objects.get(
                name='Processing'),
            directory=self.groups_path)

        self.remove_request = SecureDirRemoveUserRequest.objects.create(
            user=self.user1,
            allocation=self.scratch2_allocation,
            status=SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Processing'),
            directory=self.scratch2_path)

        for i, user in enumerate([self.user0, self.user1]):
            user.first_name = f'first{i}'
            user.last_name = f'last{i}'
            user.set_password(self.password)
            user.save()

        self.url = 'secure-dir-manage-user-complete-status'

    def test_access(self):
        """Testing access to SecureDirManageUsersCompleteStatusView"""

        for request, action in [(self.add_request, 'add'),
                                (self.remove_request, 'remove')]:
            kwargs = {'pk': request.pk, 'action': action}

            # Only admins should have access
            self.assert_has_access(self.admin, self.url, True, kwargs)

            self.assert_has_access(self.staff, self.url, False, kwargs)
            self.assert_has_access(self.pi, self.url, False, kwargs)
            self.assert_has_access(self.user0, self.url, False, kwargs)
            self.assert_has_access(self.user1, self.url, False, kwargs)

    def test_status_not_updated(self):
        """Testing that the request status is not updated if the same
        status is passed"""
        for request, action in [(self.add_request, 'add'),
                                (self.remove_request, 'remove')]:
            kwargs = {'pk': request.pk, 'action': action}
            data = {'status': 'Processing'}

            response = self.post_response(self.admin, self.url, kwargs=kwargs,
                                          data=data)

            request.refresh_from_db()
            self.assertEqual(request.status.name,
                             f'Processing')

            # Test that the correct message is shown
            expected_message = (
                f'Secure directory '
                f'{"addition" if action == "add" else "removal"} request '
                f'for user {request.user.username} for '
                f'{request.directory} has been marked as "Processing".')
            messages = self.get_message_strings(response)
            self.assertEqual(len(messages), 1)
            self.assertEqual(expected_message, messages[0])

            # Test that the user is redirected.
            self.assertRedirects(response,
                                 reverse('secure-dir-manage-users-request-list',
                                         kwargs={'action': action,
                                                 'status': 'pending'}))

    def test_bad_request_status(self):
        """Testing that the correct message is shown for a
        bad request status."""
        self.add_request.status = \
            SecureDirAddUserRequestStatusChoice.objects.get(
                name='Denied')
        self.add_request.save()
        self.remove_request.status = \
            SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Pending')
        self.remove_request.save()

        for request, action in [(self.add_request, 'add'),
                                (self.remove_request, 'remove')]:
            kwargs = {'pk': request.pk, 'action': action}
            data = {'status': 'Processing'}

            response = self.post_response(self.admin, self.url, kwargs=kwargs,
                                          data=data)
            messages = self.get_message_strings(response)

            expected_message = (
                f'Secure directory user '
                f'{"addition" if action == "add" else "removal"}' 
                f' request has unexpected status ' 
                f'"{request.status.name}."')

            self.assertEqual(len(messages), 1)
            self.assertEqual(expected_message, messages[0])

            # Test that the user is redirected.
            self.assertRedirects(response,
                                 reverse('secure-dir-manage-users-request-list',
                                         kwargs={'action': action,
                                                 'status': 'pending'}))

    def test_add_request_status_updated(self):
        """Testing that the request status is updated, corret emails are sent,
        and correct messages are shown."""
        kwargs = {'pk': self.add_request.pk, 'action': 'add'}
        data = {'status': 'Complete'}

        response = self.post_response(self.admin, self.url, kwargs=kwargs,
                                      data=data)

        # Test that the status is updated.
        self.add_request.refresh_from_db()
        self.assertEqual(self.add_request.status.name, 'Complete')

        # Test that the user is redirected.
        self.assertRedirects(response,
                             reverse(f'secure-dir-manage-users-request-list',
                                     kwargs={'action': 'add',
                                             'status': 'pending'}))

        # Test that the allocation user is created and has its status updated
        alloc_user = AllocationUser.objects.filter(
            allocation=self.add_request.allocation,
            user=self.add_request.user,
            status=AllocationUserStatusChoice.objects.get(name='Active'))
        self.assertTrue(alloc_user.exists())

        # Test that the correct message is shown.
        messages = self.get_message_strings(response)

        expected_message = f'Secure directory addition request for user ' \
                           f'user0 for {self.groups_path} has been ' \
                           f'marked as "Complete".'

        self.assertEqual(len(messages), 1)
        self.assertEqual(expected_message, messages[0])

        # Test that the correct emails are sent.
        recipients = [self.pi.email, self.user0.email]
        email_body = [f'The request to add first0 last0 (user0) to the secure '
                      f'directory {self.groups_path} has been '
                      f'completed. first0 last0 now has access to '
                      f'{self.groups_path} on the cluster.',
                      'If you have any questions, please contact us at']
        email_subject = 'Secure Directory Addition Request Complete'

        self.assertEqual(len(recipients), len(mail.outbox))
        for email in mail.outbox:
            for section in email_body:
                self.assertIn(section, email.body)
            self.assertIn(email_subject, email.subject)
            self.assertIn(email.to[0], recipients)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)

    def test_remove_request_status_updated(self):
        """Testing that the request status is updated, corret emails are sent,
        and correct messages are shown."""

        kwargs = {'pk': self.remove_request.pk, 'action': 'remove'}
        data = {'status': 'Complete'}

        response = self.post_response(self.admin, self.url, kwargs=kwargs,
                                      data=data)

        # Test that the status is updated.
        self.remove_request.refresh_from_db()
        self.assertEqual(self.remove_request.status.name, 'Complete')

        # Test that the user is redirected.
        self.assertRedirects(response,
                             reverse(f'secure-dir-manage-users-request-list',
                                     kwargs={'action': 'remove',
                                             'status': 'pending'}))

        # Test that the allocation user is created and has its status updated
        alloc_user = AllocationUser.objects.filter(
            allocation=self.remove_request.allocation,
            user=self.remove_request.user,
            status=AllocationUserStatusChoice.objects.get(name='Removed'))
        self.assertTrue(alloc_user.exists())

        # Test that the correct message is shown.
        messages = self.get_message_strings(response)

        expected_message = f'Secure directory removal request for user ' \
                           f'user1 for {self.scratch2_path} has been ' \
                           f'marked as "Complete".'

        self.assertEqual(len(messages), 1)
        self.assertEqual(expected_message, messages[0])

        # Test that the correct emails are sent.
        recipients = [self.pi.email, self.user1.email]
        email_body = [f'The request to remove first1 last1 (user1) from the '
                      f'secure directory {self.scratch2_path} has been '
                      f'completed. first1 last1 no longer has access to '
                      f'{self.scratch2_path} on the cluster.',
                      'If you have any questions, please contact us at']
        email_subject = 'Secure Directory Removal Request Complete'

        self.assertEqual(len(recipients), len(mail.outbox))
        for email in mail.outbox:
            for section in email_body:
                self.assertIn(section, email.body)
            self.assertIn(email_subject, email.subject)
            self.assertIn(email.to[0], recipients)
            self.assertEqual(settings.EMAIL_SENDER, email.from_email)
