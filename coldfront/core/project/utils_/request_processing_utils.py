import logging

from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserRunnerFactory
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserSource


logger = logging.getLogger(__name__)


def create_project_users(project, requester, pi, request_class):
    """Create active ProjectUsers on the given Project with the
    appropriate roles for the requester and/or the PI of the request
    of the given class. If the requester is already has the 'Principal
    Investigator' role, do not give it the 'Manager' role."""
    active_status = ProjectUserStatusChoice.objects.get(name='Active')
    manager_role = ProjectUserRoleChoice.objects.get(name='Manager')
    pi_role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')

    if requester.pk != pi.pk:
        run_runner = False
        if project.projectuser_set.filter(user=requester).exists():
            requester_project_user = project.projectuser_set.get(
                user=requester)
            if requester_project_user.role != pi_role:
                requester_project_user.role = manager_role
            if requester_project_user.status != active_status:
                requester_project_user.status = active_status
                run_runner = True
            requester_project_user.save()
        else:
            requester_project_user = ProjectUser.objects.create(
                project=project, user=requester, role=manager_role,
                status=active_status)
            run_runner = True
        if run_runner:
            runner_factory = NewProjectUserRunnerFactory()
            if request_class == AllocationRenewalRequest:
                source = NewProjectUserSource.ALLOCATION_RENEWAL_REQUESTER
            else:
                source = NewProjectUserSource.NEW_PROJECT_REQUESTER
            # TODO: Include an EmailStrategy from above.
            new_project_user_runner = runner_factory.get_runner(
                requester_project_user, source)
            new_project_user_runner.run()

    run_runner = False
    if project.projectuser_set.filter(user=pi).exists():
        pi_project_user = project.projectuser_set.get(user=pi)
        pi_project_user.role = pi_role
        if pi_project_user.status != active_status:
            pi_project_user.status = active_status
            run_runner = True
        pi_project_user.save()
    else:
        pi_project_user = ProjectUser.objects.create(
            project=project, user=pi, role=pi_role, status=active_status)
        run_runner = True
    if run_runner:
        runner_factory = NewProjectUserRunnerFactory()
        if request_class == AllocationRenewalRequest:
            source = NewProjectUserSource.ALLOCATION_RENEWAL_NON_REQUESTER_PI
        else:
            source = NewProjectUserSource.NEW_PROJECT_NON_REQUESTER_PI
        # TODO: Include an EmailStrategy from above.
        new_project_user_runner = runner_factory.get_runner(
            pi_project_user, source)
        new_project_user_runner.run()
