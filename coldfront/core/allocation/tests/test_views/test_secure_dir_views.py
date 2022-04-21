from http import HTTPStatus

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.management import call_command
from django.test.utils import override_settings
from django.urls import reverse

from coldfront.api.allocation.tests.test_allocation_base import \
    TestAllocationBase
from coldfront.core.allocation.models import Allocation, AllocationStatusChoice, \
    SecureDirAddUserRequest, SecureDirAddUserRequestStatusChoice, \
    SecureDirRemoveUserRequest, SecureDirRemoveUserRequestStatusChoice, \
    AllocationUser, AllocationUserStatusChoice
from coldfront.core.allocation.utils import create_secure_dir
from coldfront.core.project.models import ProjectUser, ProjectUserStatusChoice, \
    ProjectUserRoleChoice, Project, ProjectStatusChoice
from coldfront.core.utils.common import utc_now_offset_aware


class TestSecureDirManageUsersView(TestAllocationBase):
    """A class for testing SecureDirManageUsersView."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

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
        self.staff = User.objects.get(username='staff')

        self.subdirectory_name = 'test_dir'
        call_command('create_directory_defaults')
        create_secure_dir(self.project1, self.subdirectory_name)

        self.password = 'password'
        for user in User.objects.all():
            user.set_password(self.password)
            user.save()

        self.groups_allocation = Allocation.objects.get(
            project=self.project1,
            status=AllocationStatusChoice.objects.get(name='Active'),
            resources__name='Groups PL1 Directory')

        self.scratch2_allocation = Allocation.objects.get(
            project=self.project1,
            status=AllocationStatusChoice.objects.get(name='Active'),
            resources__name='Scratch2 PL1 Directory')

    def get_response(self, user, url, kwargs=None):
        self.client.login(username=user.username, password=self.password)
        url = reverse(url, kwargs=kwargs)
        response = self.client.get(url)
        self.client.logout()
        return response

    def post_response(self, user, url, kwargs=None, data=None):
        self.client.login(username=user.username, password=self.password)
        url = reverse(url, kwargs=kwargs)
        response = self.client.post(url, data, follow=True)
        self.client.logout()
        return response

    def assert_has_access(self, user, url, has_access, kwargs=None):
        self.client.login(username=user.username, password=self.password)
        url = reverse(url, kwargs=kwargs)
        status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
        response = self.client.get(url)
        self.assertEqual(response.status_code, status_code)
        self.client.logout()

    def test_access(self):
        """Test that the correct users have access to """
        url = 'secure-dir-manage-users'
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
            temp_user = User.objects.create(username=f'user{i}')
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
                name='Pending - Add'))

        # Users with a pending SecureDirRemoveUserRequest should not be shown
        SecureDirRemoveUserRequest.objects.create(
            user=self.user2,
            allocation=self.groups_allocation,
            status=SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Pending - Remove'))

        # Users with a completed SecureDirRemoveUserRequest should be shown
        SecureDirRemoveUserRequest.objects.create(
            user=self.user3,
            allocation=self.groups_allocation,
            status=SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Completed'))

        # Users that are already part of the allocation should not be shown.
        AllocationUser.objects.create(
            allocation=self.groups_allocation,
            user=self.user3,
            status=AllocationUserStatusChoice.objects.get(name='Active'))

        # Testing users shown on groups_allocation add users page
        kwargs = {'pk': self.groups_allocation.pk, 'action': 'add'}
        response = self.get_response(self.pi,
                                     'secure-dir-manage-users',
                                     kwargs=kwargs)
        html = response.content.decode('utf-8')
        self.assertIn(self.user0.username, html)
        self.assertIn(self.user4.username, html)

        self.assertNotIn(self.user1.username, html)
        self.assertNotIn(self.user2.username, html)
        self.assertNotIn(self.user3.username, html)
        self.assertNotIn(self.admin.username, html)
        self.assertNotIn(self.pi.email, html)

        # Testing users shown on scratch2_allocation add users page
        kwargs = {'pk': self.scratch2_allocation.pk, 'action': 'add'}
        response = self.get_response(self.pi,
                                     'secure-dir-manage-users',
                                     kwargs=kwargs)
        html = response.content.decode('utf-8')
        self.assertIn(self.user0.username, html)
        self.assertIn(self.user1.username, html)
        self.assertIn(self.user2.username, html)
        self.assertIn(self.user3.username, html)
        self.assertIn(self.user4.username, html)

        self.assertNotIn(self.admin.username, html)
        self.assertNotIn(self.pi.email, html)

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
                name='Pending - Remove'))

        # Testing users shown on groups_allocation remove users page
        kwargs = {'pk': self.groups_allocation.pk, 'action': 'remove'}
        response = self.get_response(self.pi,
                                     'secure-dir-manage-users',
                                     kwargs=kwargs)
        html = response.content.decode('utf-8')
        self.assertIn(self.user3.username, html)
        self.assertIn(self.user4.username, html)

        self.assertNotIn(self.user0.username, html)
        self.assertNotIn(self.user1.username, html)
        self.assertNotIn(self.user2.username, html)
        self.assertNotIn(self.admin.username, html)
        self.assertNotIn(self.pi.email, html)

        # Testing users shown on scratch2_allocation remove users page
        kwargs = {'pk': self.scratch2_allocation.pk, 'action': 'remove'}
        response = self.get_response(self.pi,
                                     'secure-dir-manage-users',
                                     kwargs=kwargs)
        html = response.content.decode('utf-8')

        self.assertNotIn(self.user0.username, html)
        self.assertNotIn(self.user1.username, html)
        self.assertNotIn(self.user2.username, html)
        self.assertNotIn(self.user3.username, html)
        self.assertNotIn(self.user4.username, html)
        self.assertNotIn(self.admin.username, html)
        self.assertNotIn(self.pi.email, html)

    def test_add_users(self):
        """Test that the correct SecureDirAddUserRequest is created"""

        form_data = {'userform-TOTAL_FORMS': ['1'],
                     'userform-INITIAL_FORMS': ['1'],
                     'userform-MIN_NUM_FORMS': ['0'],
                     'userform-MAX_NUM_FORMS': ['2'],
                     'userform-0-selected': ['on']}

        pre_time = utc_now_offset_aware()

        kwargs = {'pk': self.groups_allocation.pk, 'action': 'add'}
        response = self.post_response(self.pi,
                                      'secure-dir-manage-users',
                                      kwargs=kwargs,
                                      data=form_data)

        request = SecureDirAddUserRequest.objects.filter(
            user=self.user0,
            allocation=self.groups_allocation,
            status=SecureDirAddUserRequestStatusChoice.objects.get(
                name='Pending - Add'))
        self.assertTrue(request.exists())

        request = request.first()
        self.assertTrue(request.completion_time is None)
        self.assertTrue(pre_time <=
                        request.request_time <=
                        utc_now_offset_aware())

        self.assertRedirects(response,
                             reverse('allocation-detail',
                                     kwargs={'pk': self.groups_allocation.pk}))

    def test_remove_users(self):
        """Test that the correct SecureDirRemoveUserRequest is created"""
        # Add users to allocation.
        for i in range(2):
            AllocationUser.objects.create(
                allocation=self.groups_allocation,
                user=getattr(self, f'user{i}'),
                status=AllocationUserStatusChoice.objects.get(name='Active'))

        form_data = {'userform-TOTAL_FORMS': ['1'],
                     'userform-INITIAL_FORMS': ['1'],
                     'userform-MIN_NUM_FORMS': ['0'],
                     'userform-MAX_NUM_FORMS': ['2'],
                     'userform-0-selected': ['on']}

        pre_time = utc_now_offset_aware()

        kwargs = {'pk': self.groups_allocation.pk, 'action': 'remove'}
        response = self.post_response(self.pi,
                                      'secure-dir-manage-users',
                                      kwargs=kwargs,
                                      data=form_data)

        request = SecureDirRemoveUserRequest.objects.filter(
            user=self.user0,
            allocation=self.groups_allocation,
            status=SecureDirRemoveUserRequestStatusChoice.objects.get(
                name='Pending - Remove'))
        self.assertTrue(request.exists())

        request = request.first()
        self.assertTrue(request.completion_time is None)
        self.assertTrue(pre_time <=
                        request.request_time <=
                        utc_now_offset_aware())

        self.assertRedirects(response,
                             reverse('allocation-detail',
                                     kwargs={'pk': self.groups_allocation.pk}))