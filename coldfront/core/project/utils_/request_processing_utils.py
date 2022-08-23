import logging

from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserRunnerFactory
from coldfront.core.project.utils_.new_project_user_utils import NewProjectUserSource
from coldfront.core.utils.email.email_strategy import validate_email_strategy_or_get_default


logger = logging.getLogger(__name__)


def create_project_users(project, requester, pi, request_class,
                         email_strategy=None):
    """Create active ProjectUsers on the given Project with the
    appropriate roles for the requester and/or the PI of the request
    of the given class. If the requester is already has the 'Principal
    Investigator' role, do not give it the 'Manager' role."""
    email_strategy = validate_email_strategy_or_get_default(
        email_strategy=email_strategy)

    active_status = ProjectUserStatusChoice.objects.get(name='Active')
    manager_role = ProjectUserRoleChoice.objects.get(name='Manager')
    pi_role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')

    is_requester_pi = requester.pk == pi.pk
    runners_to_run = []

    if not is_requester_pi:
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
            new_project_user_runner = runner_factory.get_runner(
                requester_project_user, source, email_strategy=email_strategy)
            runners_to_run.append(new_project_user_runner)

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
            if is_requester_pi:
                source = NewProjectUserSource.ALLOCATION_RENEWAL_REQUESTER
            else:
                source = \
                    NewProjectUserSource.ALLOCATION_RENEWAL_NON_REQUESTER_PI
        else:
            if is_requester_pi:
                source = NewProjectUserSource.NEW_PROJECT_REQUESTER
            else:
                source = NewProjectUserSource.NEW_PROJECT_NON_REQUESTER_PI
        new_project_user_runner = runner_factory.get_runner(
            pi_project_user, source, email_strategy=email_strategy)
        runners_to_run.append(new_project_user_runner)

    for runner in runners_to_run:
        runner.run()
