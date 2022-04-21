from coldfront.api.statistics.utils import create_project_allocation
from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.models import AllocationUser
from coldfront.core.allocation.models import AllocationUserStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils import ProjectClusterAccessRequestRunner
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.resource.models import Resource
from coldfront.core.user.models import UserProfile
from decimal import Decimal
from django.contrib.auth.models import User
from django.core import mail
from django.core.management import call_command
from flags.state import enable_flag
from io import StringIO
import os
import sys


class TestRunnerMixinBase(object):
    """A base mixin for testing runners."""

    def setUp(self):
        """Set up test data."""
        enable_flag('BRC_ONLY', create_boolean_condition=True)

        out, err = StringIO(), StringIO()
        commands = [
            'add_resource_defaults',
            'add_allocation_defaults',
            'add_brc_accounting_defaults',
            'create_allocation_periods',
            # This command calls 'print', whose output must be suppressed.
            'import_field_of_science_data',
            'add_default_project_choices',
            'create_staff_group',
        ]
        sys.stdout = open(os.devnull, 'w')
        for command in commands:
            call_command(command, stdout=out, stderr=err)
        sys.stdout = sys.__stdout__

        self.allocation_period = get_current_allowance_year_period()

        # Create a requester user and multiple PI users.
        self.requester = User.objects.create(
            email='requester@email.com',
            first_name='Requester',
            last_name='User',
            username='requester')
        for i in range(4):
            username = f'pi{i}'
            user = User.objects.create(
                email=f'{username}@email.com',
                first_name=f'PI{i}',
                last_name='User',
                username=username)
            # Set self.pi{i} to the created user.
            setattr(self, username, user)
            # Set each PI's is_pi status.
            user_profile = UserProfile.objects.get(user=user)
            user_profile.is_pi = True
            user_profile.save()

        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        inactive_project_status = ProjectStatusChoice.objects.get(
            name='Inactive')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        manager_project_user_role = ProjectUserRoleChoice.objects.get(
            name='Manager')
        pi_project_user_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')

        # Create Projects.
        self.unpooled_project0 = Project.objects.create(
            name='unpooled_project0', status=active_project_status)
        self.unpooled_project1 = Project.objects.create(
            name='unpooled_project1', status=inactive_project_status)
        self.pooled_project0 = Project.objects.create(
            name='pooled_project0', status=active_project_status)
        self.pooled_project1 = Project.objects.create(
            name='pooled_project1', status=active_project_status)

        # Add the designated PIs to each Project.
        self.projects_and_pis = {
            self.unpooled_project0: [self.pi0],
            self.unpooled_project1: [self.pi1],
            self.pooled_project0: [self.pi0, self.pi1],
            self.pooled_project1: [self.pi2, self.pi3],
        }
        for project, pi_users in self.projects_and_pis.items():
            for pi_user in pi_users:
                ProjectUser.objects.create(
                    project=project,
                    user=pi_user,
                    role=pi_project_user_role,
                    status=active_project_user_status)
            # Add the requester as a manager on each Project.
            ProjectUser.objects.create(
                project=project,
                user=self.requester,
                role=manager_project_user_role,
                status=active_project_user_status)

        # Create a 'CLUSTER_NAME Compute' Allocation for each Project.
        self.project_service_units = {}
        self.projects_and_allocations = {}
        for i, project in enumerate(self.projects_and_pis.keys()):
            value = Decimal(str(i * 1000))
            allocation = create_project_allocation(project, value).allocation
            self.project_service_units[project] = value
            self.projects_and_allocations[project] = allocation

        # Create AllocationUsers on the 'CLUSTER_NAME Compute' Allocation.
        active_allocation_user_status = AllocationUserStatusChoice.objects.get(
            name='Active')
        for project, pi_users in self.projects_and_pis.items():
            allocation = self.projects_and_allocations[project]
            for pi_user in pi_users:
                AllocationUser.objects.create(
                    allocation=allocation,
                    user=pi_user,
                    status=active_allocation_user_status)
            # For the requesters only, also create cluster access requests and
            # approve them.
            project_user_obj = ProjectUser.objects.get(
                project=project, user=self.requester)
            request_runner = ProjectClusterAccessRequestRunner(
                project_user_obj)
            runner_result = request_runner.run()

            self.assertTrue(runner_result.success)
        # Clear the mail outbox.
        mail.outbox = []

        # This should be set by the subclasses.
        self.request_obj = None

    def create_under_review_new_project_request(self):
        """Create a new Project, a corresponding 'CLUSTER_NAME Compute'
        Allocation, and an 'Under Review' new project request for it."""
        # Create a new Project.
        new_project_name = 'unpooled_project2'
        new_project_status = ProjectStatusChoice.objects.get(name='New')
        new_project = Project.objects.create(
            name=new_project_name,
            status=new_project_status,
            title=new_project_name,
            description=f'Description of {new_project_name}.')

        # Create a compute Allocation for the new Project.
        new_allocation_status = AllocationStatusChoice.objects.get(name='New')
        allocation = Allocation.objects.create(
            project=new_project, status=new_allocation_status)
        resource = Resource.objects.get(name='Savio Compute')
        allocation.resources.add(resource)
        allocation.save()

        # Create an 'Under Review' SavioProjectAllocationRequest for the new
        # Project.
        under_review_request_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Under Review')
        new_project_request = SavioProjectAllocationRequest.objects.create(
            requester=self.requester,
            allocation_type=SavioProjectAllocationRequest.FCA,
            pi=self.pi0,
            project=new_project,
            survey_answers={},
            status=under_review_request_status)

        return new_project_request
