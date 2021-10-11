from coldfront.api.statistics.utils import get_accounting_allocation_objects
from coldfront.api.statistics.utils import set_project_user_allocation_value
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.utils import get_or_create_active_allocation_user
from coldfront.core.allocation.utils import next_allocation_start_datetime
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils import get_project_compute_allocation
from coldfront.core.project.utils import validate_num_service_units
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import utc_now_offset_aware
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
import logging


logger = logging.getLogger(__name__)


def get_current_allocation_period():
    # TODO: Account for other periods.
    return AllocationPeriod.objects.get(name='AY21-22')


def get_pi_current_active_fca_project(pi_user):
    # TODO: This is flawed because PI "A" could be on a Project where a
    # TODO: different PI "B" has renewed, but "A" hasn't. The "Service Units"
    # TODO: would be non-zero.
    # TODO: Use AllocationRenewalRequest objects instead.
    """Given a User object representing a PI, return its current,
    active fc_ Project.

    A Project is considered "active" if it has a non-zero allocation
    of "Service Units". If there are zero or multiple such Projects,
    raise an exception.

    Parameters:
        - pi_user: a User object.

    Returns:
        - A Project object.

    Raises:
        - Project.DoesNotExist, if none are found.
        - Project.MultipleObjectsReturned, if multiple are found.
        - Exception, if any other errors occur.
    """
    role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')
    status = ProjectUserStatusChoice.objects.get(name='Active')
    project_users = ProjectUser.objects.select_related('project').filter(
        project__name__startswith='fc_', role=role, status=status,
        user=pi_user)
    active_fca_projects = []
    for project_user in project_users:
        project = project_user.project
        allocation_objects = get_accounting_allocation_objects(project)
        num_service_units = Decimal(
            allocation_objects.allocation_attribute.value)
        if num_service_units > settings.ALLOCATION_MIN:
            active_fca_projects.append(project)
    n = len(active_fca_projects)
    if n == 0:
        raise Project.DoesNotExist('No active FCA Project found.')
    elif n == 2:
        raise Project.MultipleObjectsReturned(
            'More than one active FCA Project found.')
    return active_fca_projects[0]


def has_non_denied_renewal_request(pi, allocation_period):
    """Return whether or not the given PI User has a non-"Denied"
    AllocationRenewalRequest for the given AllocationPeriod."""
    if not isinstance(pi, User):
        raise TypeError(f'{pi} is not a User object.')
    if not isinstance(allocation_period, AllocationPeriod):
        raise TypeError(
            f'{allocation_period} is not an AllocationPeriod object.')
    return AllocationRenewalRequest.objects.filter(
        pi=pi,
        allocation_period=allocation_period,
        status__name__in=['Under Review', 'Approved', 'Complete']).exists()


def is_pooled(project):
    """Return whether the given Project is a pooled project. In
    particular, a Project is pooled if it has more than one PI."""
    pi_role = ProjectUserRoleChoice.objects.get(
        name='Principal Investigator')
    return project.projectuser_set.filter(role=pi_role).count() > 1


def is_any_project_pi_renewable(project, allocation_period):
    """Return whether the Project has at least one PI who is eligible to
    make an AllocationRenewalRequest during the given
    AllocationPeriod."""
    for pi in project.pis():
        if not has_non_denied_renewal_request(pi, allocation_period):
            return True
    return False


class AllocationRenewalRunnerBase(object):
    """A base class that Runners for handling AllocationRenewalsRequests
    should inherit from."""

    def __init__(self, request_obj, *args, **kwargs):
        self.request_obj = request_obj

    def run(self):
        raise NotImplementedError('This method is not implemented.')

    def assert_request_status(self, expected_status):
        """Raise an assertion error if the request does not have the
        given expected status."""
        if not isinstance(
                expected_status, AllocationRenewalRequestStatusChoice):
            raise TypeError(
                'Status is not an AllocationRenewalRequestStatusChoice.')
        assert self.request_obj.status == expected_status

    def create_allocation_users(self, allocation):
        """Create active AllocationUsers for the requester and/or the
        PI. Return the created objects (requester and then PI)."""
        requester = self.request_obj.requester
        pi = self.request_obj.pi
        requester_allocation_user = None
        if requester.pk != pi.pk:
            requester_allocation_user = get_or_create_active_allocation_user(
                allocation, requester)
        pi_allocation_user = get_or_create_active_allocation_user(
            allocation, pi)
        return requester_allocation_user, pi_allocation_user

    @staticmethod
    def create_cluster_access_request_for_requester(allocation_user):
        """Create a 'Cluster Account Status' for the given
        AllocationUser corresponding to the request's requester."""
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Cluster Account Status')
        pending_add = 'Pending - Add'
        # get_or_create's 'defaults' arguments are only considered if a create
        # is required.
        defaults = {
            'value': pending_add,
        }
        allocation_user_attribute, created = \
            allocation_user.allocationuserattribute_set.get_or_create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation_user.allocation,
                defaults=defaults)
        if not created:
            if allocation_user_attribute.value == 'Active':
                message = (
                    f'AllocationUser {allocation_user.pk} for requester '
                    f'{allocation_user.user.pk} unexpectedly already has '
                    f'active cluster access status.')
                logger.warning(message)
            else:
                allocation_user_attribute.value = pending_add
                allocation_user_attribute.save()

    def create_project_users(self):
        """Create active ProjectUsers with the appropriate roles for the
        requester and/or the PI. If the requester is already has the
        'Principal Investigator' role, do not give it the 'Manager'
        role."""
        project = self.request_obj.project
        requester = self.request_obj.requester
        pi = self.request_obj.pi
        status = ProjectUserStatusChoice.objects.get(name='Active')
        pi_role = ProjectUserRoleChoice.objects.get(
            name='Principal Investigator')

        if requester.pk != pi.pk:
            role = ProjectUserRoleChoice.objects.get(name='Manager')
            if project.projectuser_set.filter(user=requester).exists():
                requester_project_user = project.projectuser_set.get(
                    user=requester)
                if requester_project_user.role != pi_role:
                    requester_project_user.role = role
                requester_project_user.status = status
                requester_project_user.save()
            else:
                ProjectUser.objects.create(
                    project=project, user=requester, role=role, status=status)

        if project.projectuser_set.filter(user=pi).exists():
            pi_project_user = project.projectuser_set.get(user=pi)
            pi_project_user.role = pi_role
            pi_project_user.status = status
            pi_project_user.save()
        else:
            ProjectUser.objects.create(
                project=project, user=pi, role=pi_role, status=status)

    def handle_by_preference(self):
        request = self.request_obj
        pi = request.pi
        pre_project = request.pre_project
        post_project = request.post_project
        is_pooled_pre = is_pooled(pre_project)
        is_pooled_post = is_pooled(post_project)
        if pre_project == post_project:
            if not is_pooled_pre:
                return self.handle_unpooled_to_unpooled()
            else:
                return self.handle_pooled_to_pooled_same()
        else:
            if request.new_project_request:
                return self.handle_pooled_to_unpooled_new()
            else:
                if not is_pooled_pre:
                    if not is_pooled_post:
                        message = (
                            f'Ran into unexpected case: non-pooling in '
                            f'pre-project {pre_project.name} to non-pooling '
                            f'in post-project {post_project.name}.')
                        logger.error(message)
                        raise ValueError('Unexpected case.')
                    else:
                        return self.handle_unpooled_to_pooled()
                else:
                    if pi in post_project.pis():
                        return self.handle_pooled_to_unpooled_old()
                    else:
                        return self.handle_pooled_to_pooled_different()

    def handle_unpooled_to_unpooled(self):
        """Handle the case when the preference is to stay unpooled."""
        raise NotImplementedError('This method is not implemented.')

    def handle_unpooled_to_pooled(self):
        """Handle the case when the preference is to start pooling."""
        raise NotImplementedError('This method is not implemented.')

    def handle_pooled_to_pooled_same(self):
        """Handle the case when the preference is to stay pooled with
        the same project."""
        raise NotImplementedError('This method is not implemented.')

    def handle_pooled_to_pooled_different(self):
        """Handle the case when the preference is to stop pooling with
        the current project and start pooling with a different
        project."""
        raise NotImplementedError('This method is not implemented.')

    def handle_pooled_to_unpooled_old(self):
        """Handle the case when the preference is to stop pooling and
        reuse another existing project owned by the PI."""
        raise NotImplementedError('This method is not implemented.')

    def handle_pooled_to_unpooled_new(self):
        """Handle the case when the preference is to stop pooling and
        create a new project."""
        raise NotImplementedError('This method is not implemented.')


class AllocationRenewalApprovalRunner(AllocationRenewalRunnerBase):
    """An object that performs necessary database changes when an
    AllocationRenewalRequest is approved."""

    def __init__(self, request_obj, num_service_units):
        super().__init__(request_obj)
        expected_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Under Review')
        self.assert_request_status(expected_status)
        validate_num_service_units(num_service_units)


class AllocationRenewalDenialRunner(AllocationRenewalRunnerBase):
    """An object that performs necessary database changes when an
    AllocationRenewalRequest is denied."""

    def __init__(self, request_obj):
        super().__init__(request_obj)
        expected_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Under Review')
        self.assert_request_status(expected_status)

    def run(self):
        # Only update the Project if pooling is not involved.

        self.deny_request()
        self.send_email()

    # def deny_project(self):
    #     """Set the Project's status to 'Denied'."""
    #     project = self.request_obj.post_project
    #     project.status = ProjectStatusChoice.objects.get(name='Denied')
    #     project.save()
    #     return project

    def deny_request(self):
        """Set the status of the request to 'Denied'."""
        self.request_obj.status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Denied')
        self.request_obj.save()

    def send_email(self):
        """Send a notification email to the requester and PI."""
        try:
            # TODO
            pass
        except Exception as e:
            logger.error('Failed to send notification email. Details:')
            logger.exception(e)


class AllocationRenewalProcessingRunner(AllocationRenewalRunnerBase):
    """An object that performs necessary database changes when an
    AllocationRenewalRequest is processed."""

    def __init__(self, request_obj, num_service_units):
        super().__init__(request_obj)
        expected_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Approved')
        self.assert_request_status(expected_status)
        validate_num_service_units(num_service_units)

    def run(self):
        request = self.request_obj
        post_project = request.post_project

        self.upgrade_pi_user()
        post_project = self.activate_project(post_project)

        # TODO
        pool = False
        allocation, new_value = self.update_allocation(pool)
        # In the pooling case, set the Service Units of the existing users to
        # the updated value.
        if pool:
            self.update_existing_user_allocations(new_value)

        self.create_project_users()
        requester_allocation_user, pi_allocation_user = \
            self.create_allocation_users(allocation)

        # If the AllocationUser for the requester was not created, then the PI
        # was the requester.
        if requester_allocation_user is None:
            self.create_cluster_access_request_for_requester(
                pi_allocation_user)
        else:
            self.create_cluster_access_request_for_requester(
                requester_allocation_user)

        self.complete_request()
        # self.send_email

        return post_project, allocation

    @staticmethod
    def activate_project(project):
        """Set the given Project's status to 'Active'."""
        status = ProjectStatusChoice.objects.get(name='Active')
        project.status = status
        project.save()
        return project

    def add_service_units_to_allocation(self):
        pass

    def add_service_units_to_allocation_users(self):
        post_project = self.request_obj.post_project
        date_time = utc_now_offset_aware()
        for project_user in post_project.projectuser_set.all():
            user = project_user.user
        # TODO

    def complete_request(self):
        """Set the status of the request to 'Complete'."""
        self.request_obj.status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Complete')
        self.request_obj.save()

    def handle_unpooled_to_unpooled(self):
        """
        TODO
        """
        post_project = self.request_obj.post_project
        self.activate_project(post_project)
        # Set SUs

    def handle_unpooled_to_pooled(self):
        """Handle the case when the preference is to start pooling."""
        # Add the requester as a Manager and PI as a Principal Investigator.
        project = self.request_obj.post_project

    def handle_pooled_to_pooled_same(self):
        """Handle the case when the preference is to stay pooled with
        the same project."""
        raise NotImplementedError('This method is not implemented.')

    def handle_pooled_to_pooled_different(self):
        """Handle the case when the preference is to stop pooling with
        the current project and start pooling with a different
        project."""
        raise NotImplementedError('This method is not implemented.')

    def handle_pooled_to_unpooled_old(self):
        """Handle the case when the preference is to stop pooling and
        reuse another existing project owned by the PI."""
        raise NotImplementedError('This method is not implemented.')

    def handle_pooled_to_unpooled_new(self):
        """Handle the case when the preference is to stop pooling and
        create a new project."""
        raise NotImplementedError('This method is not implemented.')

    def update_allocation(self, pool):
        """Perform allocation-related handling, differing based on
        whether pooling is involved."""
        project = self.request_obj.post_project
        # TODO: Support other types.
        allocation_type = SavioProjectAllocationRequest.FCA

        allocation = get_project_compute_allocation(project)
        allocation.status = AllocationStatusChoice.objects.get(name='Active')
        # If this is a new Project, set its Allocation's start and end dates.
        if not pool:
            allocation.start_date = utc_now_offset_aware()
            allocation.end_date = \
                next_allocation_start_datetime() - timedelta(seconds=1)
        allocation.save()

        # Set the allocation's allocation type.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Savio Allocation Type')
        allocation_attribute, _ = \
            AllocationAttribute.objects.get_or_create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation, defaults={'value': allocation_type})

        # Set or increase the allocation's service units.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        allocation_attribute, _ = \
            AllocationAttribute.objects.get_or_create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation)
        if pool:
            existing_value = Decimal(allocation_attribute.value)
            new_value = existing_value + self.num_service_units
            validate_num_service_units(new_value)
        else:
            new_value = self.num_service_units
        allocation_attribute.value = str(new_value)
        allocation_attribute.save()

        # Create a ProjectTransaction to store the change in service units.
        ProjectTransaction.objects.create(
            project=project,
            date_time=utc_now_offset_aware(),
            allocation=Decimal(new_value))

        return allocation, new_value

    def update_existing_user_allocations(self, value):
        """Perform user-allocation-related handling.

        In particular, update the Service Units for existing Users to
        the given value. The requester and/or PI will have their values
        set once their cluster account requests are approved."""
        project = self.request_obj.project
        date_time = utc_now_offset_aware()
        for project_user in project.projectuser_set.all():
            user = project_user.user
            set_project_user_allocation_value(user, project, value)
            ProjectUserTransaction.objects.create(
                project_user=project_user,
                date_time=date_time,
                allocation=Decimal(value))

    def upgrade_pi_user(self):
        """Set the is_pi field of the request's PI UserProfile to
        True."""
        pi = self.request_obj.pi
        pi.userprofile.is_pi = True
        pi.userprofile.save()
