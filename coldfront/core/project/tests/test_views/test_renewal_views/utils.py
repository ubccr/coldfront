from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.renewal_utils import get_current_allowance_year_period
from coldfront.core.utils.common import utc_now_offset_aware


class TestRenewalViewsMixin(object):
    """A mixin for testing renewal views."""

    @staticmethod
    def create_project_and_request(project_name, computing_allowance,
                                   requester_and_pi):
        """Create an active Project with the given name and computing
        allowance, add the given user to it, and create an
        AllocationRenewalRequest with 'Under Review' status. Return both."""
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
            user=requester_and_pi)
        allocation_period = get_current_allowance_year_period()
        under_review_request_status = \
            AllocationRenewalRequestStatusChoice.objects.get(
                name='Under Review')
        allocation_renewal_request = AllocationRenewalRequest.objects.create(
            requester=requester_and_pi,
            pi=requester_and_pi,
            computing_allowance=computing_allowance,
            allocation_period=allocation_period,
            status=under_review_request_status,
            pre_project=project,
            post_project=project,
            request_time=utc_now_offset_aware())
        return project, allocation_renewal_request
