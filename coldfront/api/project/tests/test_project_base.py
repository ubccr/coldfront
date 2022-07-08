from decimal import Decimal

from coldfront.api.statistics.utils import create_project_allocation, \
    create_user_project_allocation
from coldfront.api.utils.tests.test_api_base import TestAPIBase
from coldfront.core.project.models import ProjectStatusChoice, \
    ProjectUserStatusChoice, ProjectUserRoleChoice, Project, ProjectUser
from coldfront.core.user.models import UserProfile, ExpiringToken
from django.contrib.auth.models import User
from django.core.management import call_command


class TestProjectBase(TestAPIBase):
    """A base class for testing Project-related functionality."""

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create default choices.
        call_command('add_default_user_choices')

        # Create a superuser.
        self.superuser = User.objects.create_superuser(
            email='superuser@nonexistent.com',
            username='superuser',
            password=self.password)

        # Fetch the staff user.
        self.staff_user = User.objects.get(username='staff')

        # Create a PI.
        self.pi = User.objects.create(
            username=f'pi', email=f'pi@nonexistent.com')
        user_profile = UserProfile.objects.get(user=self.pi)
        user_profile.is_pi = True
        user_profile.save()

        # Create three Users.
        for i in range(3):
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
            for j in range(3):
                ProjectUser.objects.create(
                    user=getattr(self, f'user{j}'), project=project,
                    role=user_role, status=project_user_status)
            ProjectUser.objects.create(
                user=self.pi, project=project, role=pi_role,
                status=project_user_status)

            # Create a compute allocation for the Project.
            allocation = Decimal(f'{i + 1}000.00')
            create_project_allocation(project, allocation)

            # Create a compute allocation for each User on the Project.
            for j in range(3):
                create_user_project_allocation(
                    getattr(self, f'user{j}'), project, allocation / 2)

        # Create an ExpiringToken for each User.
        for user in User.objects.all():
            token, _ = ExpiringToken.objects.get_or_create(user=user)
            setattr(self, f'{user.username}_token', token)
