import os
import sys
from decimal import Decimal
from http import HTTPStatus
from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from coldfront.api.statistics.utils import create_project_allocation, \
    create_user_project_allocation
from coldfront.core.project.models import ProjectStatusChoice, \
    ProjectUserStatusChoice, ProjectUserRoleChoice, Project, ProjectUser
from coldfront.core.user.models import EmailAddress, UserProfile
from coldfront.core.user.tests.utils import TestUserBase
from coldfront.core.user.utils import account_activation_url
from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.test import Client
from django.urls import reverse


class TestRequestHubView(TestCase):
    """A class for testing the view for activating a user's account."""

    password = 'test1234'

    def setUp(self):
        """Set up test data."""
        out, err = StringIO(), StringIO()
        commands = [
            'add_resource_defaults',
            'add_allocation_defaults',
            'import_field_of_science_data',
            'add_default_project_choices',
            'create_staff_group',
        ]
        sys.stdout = open(os.devnull, 'w')
        for command in commands:
            call_command(command, stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        self.password = 'password'

        self.pi = User.objects.create(
            username='pi0', email='pi0@nonexistent.com')
        user_profile = UserProfile.objects.get(user=self.pi)
        user_profile.is_pi = True
        user_profile.save()

        self.admin = User.objects.create(
            username='admin', email='admin@nonexistent.com')
        user_profile = UserProfile.objects.get(user=self.admin)
        user_profile.is_superuser = True
        user_profile.save()

        self.staff = User.objects.create(
            username='staff', email='staff@nonexistent.com')
        user_profile = UserProfile.objects.get(user=self.staff)
        user_profile.is_staff = True
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
            ProjectUser.objects.create(
                user=getattr(self, 'user0'), project=project,
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

        for user in User.objects.all():
            user.set_password(self.password)

        self.url = reverse('request-hub')
        self.admin_url = reverse('request-hub-admin')

    def assert_has_access(self, user, url, has_access):
        self.client.login(username=user.username, password=self.password)
        response = self.client.get(url)
        status_code = HTTPStatus.OK if has_access else HTTPStatus.FORBIDDEN
        self.assertEqual(response.status_code, status_code)
        self.client.logout()

    def get_response(self, user, url):
        self.client.login(username=user.username, password=self.password)
        return self.client.get(url)

    def test_access(self):
        """Testing access to RequestHubView"""
