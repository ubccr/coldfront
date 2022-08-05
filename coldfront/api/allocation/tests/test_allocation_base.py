from django.core.management import call_command

from coldfront.api.statistics.utils import create_project_allocation
from coldfront.api.statistics.utils import create_user_project_allocation
from coldfront.api.utils.tests.test_api_base import TestAPIBase
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.user.models import UserProfile, ExpiringToken
from decimal import Decimal
from django.contrib.auth.models import User


class TestAllocationBase(TestAPIBase):
    """A base class for testing Allocation-related functionality."""

    allocations_base_url = '/api/allocations/'
    allocation_users_base_url = '/api/allocation_users/'

    def setUp(self):
        """Set up test data."""
        super().setUp()

        # Create a superuser.
        self.superuser = User.objects.create_superuser(
            email='superuser@nonexistent.com',
            username='superuser',
            password=self.password)

        # Fetch the staff user.
        self.staff_user = User.objects.get(username='staff')

        # Create a PI.
        self.pi = User.objects.create(
            username='pi0', email='pi0@nonexistent.com')
        user_profile = UserProfile.objects.get(user=self.pi)
        user_profile.is_pi = True
        user_profile.save()

        # Create two Users.
        for i in range(4):
            user = User.objects.create(
                username=f'user{i}', email=f'user{i}@nonexistent.com')
            user_profile = UserProfile.objects.get(user=user)
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
            for j in range(4):
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
            for j in range(4):
                create_user_project_allocation(
                    getattr(self, f'user{j}'), project, allocation / 2)

        # Create an ExpiringToken for each User.
        for user in User.objects.all():
            token, _ = ExpiringToken.objects.get_or_create(user=user)
            setattr(self, f'{user.username}_token', token)
