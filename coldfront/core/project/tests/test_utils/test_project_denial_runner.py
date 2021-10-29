from coldfront.core.allocation.models import Allocation
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils import ProjectDenialRunner
from coldfront.core.project.utils_.renewal_utils import get_current_allocation_period
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.tests.test_base import TestBase


class TestProjectDenialRunner(TestBase):
    """A class for testing ProjectDenialRunner."""

    def setUp(self):
        """Set up test data."""
        super().setUp()
        self.create_test_user()
        self.sign_user_access_agreement(self.user)
        self.client.login(username=self.user.username, password=self.password)

    def test_denies_associated_allocation_renewal_request(self):
        """Test that when a SavioProjectAllocationRequest that is
        referenced by an AllocationRenewalRequest is denied, the latter
        is also denied."""
        # Create a Project for the user to currently be on.
        old_project_name = 'old_project'
        active_project_status = ProjectStatusChoice.objects.get(name='Active')
        old_project = Project.objects.create(
            name=old_project_name,
            title=old_project_name,
            status=active_project_status)
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')
        active_project_user_status = ProjectUserStatusChoice.objects.get(
            name='Active')
        ProjectUser.objects.create(
            project=old_project,
            role=pi_role,
            status=active_project_user_status,
            user=self.user)

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
            requester=self.user,
            allocation_type=SavioProjectAllocationRequest.FCA,
            pi=self.user,
            project=new_project,
            survey_answers={},
            status=under_review_request_status)

        # Create an AllocationRenewalRequest referencing it.
        under_review_request_status = \
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review')
        allocation_renewal_request = AllocationRenewalRequest.objects.create(
            requester=self.user,
            pi=self.user,
            allocation_period=get_current_allocation_period(),
            status=under_review_request_status,
            pre_project=old_project,
            post_project=new_project,
            request_time=utc_now_offset_aware(),
            new_project_request=new_project_request)

        # Deny the SavioProjectAllocationRequest.
        new_project_request.state['other'] = {
            'justification': 'This is a test of the denial signal.',
            'timestamp': utc_now_offset_aware().isoformat(),
        }
        new_project_request.save()
        runner = ProjectDenialRunner(new_project_request)
        runner.run()

        # The AllocationRenewalRequest should be denied.
        allocation_renewal_request.refresh_from_db()
        self.assertEqual(allocation_renewal_request.status.name, 'Denied')

    # TODO
