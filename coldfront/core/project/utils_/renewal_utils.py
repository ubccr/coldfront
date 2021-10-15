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
from coldfront.core.project.utils import savio_request_denial_reason
from coldfront.core.project.utils import validate_num_service_units
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.mail import send_email_template
from collections import namedtuple
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
import logging


logger = logging.getLogger(__name__)


def get_current_allocation_period():
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


def send_allocation_renewal_request_denial_email(request):
    """Send a notification email to the requester and PI associated with
    the given AllocationRenewalRequest stating that the request has been
    denied."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = f'{str(request)} Denied'
    template_name = 'email/project_renewal/project_renewal_request_denied.txt'
    reason = allocation_renewal_request_denial_reason(request)

    context = {
        'center_name': settings.CENTER_NAME,
        'current_project_name': (
            request.pre_project.name if request.pre_project else 'N/A'),
        'pi_name': f'{request.pi.first_name} {request.pi.last_name}',
        'reason_category': reason.category,
        'reason_justification': reason.justification,
        'requested_project_name': request.post_project.name,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [request.requester.email, request.pi.email]
    cc = settings.REQUEST_APPROVAL_CC_LIST

    send_email_template(
        subject, template_name, context, sender, receiver_list, cc=cc)


def send_allocation_renewal_request_processing_email(request):
    """Send a notification email to the requester and PI associated with
    the given AllocationRenewalRequest stating that the request has been
    processed."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    # TODO
    subject = f'{str(request)} Processed'
    template_name = ''

    context = {

    }

    sender = settings.EMAIL_SENDER
    receiver_list = [request.requester.email, request.pi.email]
    cc = settings.REQUEST_APPROVAL_CC_LIST

    send_email_template(
        subject, template_name, context, sender, receiver_list, cc=cc)


def allocation_renewal_request_denial_reason(request):
    """Return the reason why the given AllocationRenewalRequest was
    denied, based on its 'state' field and/or an associated
    SavioProjectAllocationRequest."""
    if not isinstance(request, AllocationRenewalRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(request)}.')

    state = request.state
    eligibility = state['eligibility']
    other = state['other']

    DenialReason = namedtuple(
        'DenialReason' 'category justification timestamp')

    new_project_request = request.new_project_request

    if other['timestamp'] == 'Other':
        category = 'Other'
        justification = other['justification']
        timestamp = other['timestamp']
    elif eligibility['status'] == 'Denied':
        category = 'PI Ineligible'
        justification = eligibility['justification']
        timestamp = eligibility['timestamp']
    elif new_project_request and new_project_request.status.name == 'Denied':
        reason = savio_request_denial_reason(new_project_request)
        category = reason.category
        justification = reason.justification
        timestamp = reason.timestamp
    else:
        raise ValueError('Provided request has an unexpected state.')

    return DenialReason(
        category=category, justification=justification, timestamp=timestamp)


def allocation_renewal_request_latest_update_timestamp(request):
    """Return the latest timestamp stored in the given
    AllocationRenewalRequest's 'state' field, or the empty string.

    The expected values are ISO 8601 strings, or the empty string, so
    taking the maximum should provide the correct output."""
    if not isinstance(request, AllocationRenewalRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(request)}.')

    state = request.state
    max_timestamp = ''
    for field in state:
        max_timestamp = max(max_timestamp, state[field].get('timestamp', ''))

    new_project_request = request.new_project_request
    if new_project_request:
        request_updated = new_project_request.updated.isoformat()
        max_timestamp = max(max_timestamp, request_updated)

    return max_timestamp


def allocation_renewal_request_state_status(request):
    """Return an AllocationRenewalRequestStatusChoice, based on the
    'state' field of the given AllocationRenewalRequest, and/or an
    associated SavioProjectAllocationRequest."""
    if not isinstance(request, AllocationRenewalRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(request)}.')

    state = request.state
    eligibility = state['eligibility']
    other = state['other']

    under_review_status = AllocationRenewalRequestStatusChoice.objects.get(
        name='Under Review')
    denied_status = AllocationRenewalRequestStatusChoice.objects.get(
        name='Denied')
    approved_status = AllocationRenewalRequestStatusChoice.objects.get(
        name='Approved')

    # The request was denied for some other non-listed reason.
    if other['timestamp']:
        return denied_status

    new_project_request = request.new_project_request
    if new_project_request:
        status_name = new_project_request.status.name
        if status_name == 'Under Review':
            return under_review_status
        elif status_name in ('Approved - Processing', 'Approved - Complete'):
            return approved_status
        else:
            return denied_status
    else:
        if eligibility['status'] == 'Pending':
            return under_review_status
        elif eligibility['status'] == 'Approved':
            return approved_status
        else:
            return denied_status


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

        def log_message():
            pre_str = 'non-pooling' if not is_pooled_pre else 'pooling'
            post_str = 'non-pooling' if not is_pooled_post else 'pooling'
            return (
                f'AllocationRenewalRequest {request.pk}: {pre_str} in '
                f'pre-project {pre_project.name} to {post_str} in '
                f'post-project {post_project.name}.')

        if pre_project == post_project:
            if not is_pooled_pre:
                logger.info(log_message())
                return self.handle_unpooled_to_unpooled()
            else:
                logger.info(log_message())
                return self.handle_pooled_to_pooled_same()
        else:
            if request.new_project_request:
                logger.info(log_message())
                return self.handle_pooled_to_unpooled_new()
            else:
                if not is_pooled_pre:
                    if not is_pooled_post:
                        logger.error(log_message())
                        raise ValueError('Unexpected case.')
                    else:
                        logger.info(log_message())
                        return self.handle_unpooled_to_pooled()
                else:
                    if pi in post_project.pis():
                        logger.info(log_message())
                        return self.handle_pooled_to_unpooled_old()
                    else:
                        logger.info(log_message())
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

    # TODO: This class will become relevant when there is a need to approve,
    # TODO: but not yet process, a request. Namely, when support for requesting
    # TODO: renewal for the next allocation period is added, requests may be
    # TODO: approved days or weeks before the request is actually processed.

    def __init__(self, request_obj, num_service_units):
        super().__init__(request_obj)
        expected_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Under Review')
        self.assert_request_status(expected_status)
        validate_num_service_units(num_service_units)

    def run(self):
        pass

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


class AllocationRenewalDenialRunner(AllocationRenewalRunnerBase):
    """An object that performs necessary database changes when an
    AllocationRenewalRequest is denied."""

    def __init__(self, request_obj):
        super().__init__(request_obj)
        expected_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Under Review')
        self.assert_request_status(expected_status)

    def run(self):
        self.handle_by_preference()
        self.deny_request()
        self.send_email()

    def deny_post_project(self):
        """Set the post_project's status to 'Denied'."""
        project = self.request_obj.post_project
        project.status = ProjectStatusChoice.objects.get(name='Denied')
        project.save()
        return project

    def deny_request(self):
        """Set the status of the request to 'Denied'."""
        self.request_obj.status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Denied')
        self.request_obj.save()

    def handle_unpooled_to_unpooled(self):
        """Handle the case when the preference is to stay unpooled."""
        pass

    def handle_unpooled_to_pooled(self):
        """Handle the case when the preference is to start pooling."""
        pass

    def handle_pooled_to_pooled_same(self):
        """Handle the case when the preference is to stay pooled with
        the same project."""
        pass

    def handle_pooled_to_pooled_different(self):
        """Handle the case when the preference is to stop pooling with
        the current project and start pooling with a different
        project."""
        pass

    def handle_pooled_to_unpooled_old(self):
        """Handle the case when the preference is to stop pooling and
        reuse another existing project owned by the PI."""
        pass

    def handle_pooled_to_unpooled_new(self):
        """Handle the case when the preference is to stop pooling and
        create a new project."""
        self.deny_post_project()

    def send_email(self):
        """Send a notification email to the requester and PI."""
        request = self.request_obj
        try:
            send_allocation_renewal_request_denial_email(request)
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

        # The post_project is pooled if it has a PI other than the current one.
        role = ProjectUserRoleChoice.objects.get(name='Principal Investigator')
        pool = post_project.projectuser_set.filter(
            Q(role=role) & ~Q(user=self.request_obj.pi)).exists()
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

        self.handle_by_preference()
        self.complete_request()
        self.send_email()

        return post_project, allocation

    @staticmethod
    def activate_project(project):
        """Set the given Project's status to 'Active'."""
        status = ProjectStatusChoice.objects.get(name='Active')
        project.status = status
        project.save()
        return project

    def complete_request(self):
        """Set the status of the request to 'Complete'."""
        self.request_obj.status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Complete')
        self.request_obj.save()

    def demote_pi_to_user_on_pre_project(self):
        """If the pre_project is pooled (i.e., it has more than one PI),
        demote the PI from 'Principal Investigator' to 'User'."""
        request = self.request_obj
        pi = request.pi
        pre_project = request.pre_project
        if pre_project.pis().count() > 1:
            try:
                pi_project_user = pre_project.projectuser_set.get(user=pi)
            except ProjectUser.DoesNotExist:
                message = (
                    f'No ProjectUser exists for PI {pi.username} of Project '
                    f'{pre_project.name}, for which the PI has '
                    f'AllocationRenewalRequest {request.pk} to stop pooling '
                    f'under it.')
                logger.error(message)
            else:
                pi_project_user.role = ProjectUserRoleChoice.objects.get(
                    name='User')
                pi_project_user.save()
        else:
            message = (
                f'Project {pre_project.name} only has one PI. Skipping '
                f'demotion.')
            logger.error(message)

    def handle_unpooled_to_unpooled(self):
        """Handle the case when the preference is to stay unpooled."""
        pass

    def handle_unpooled_to_pooled(self):
        """Handle the case when the preference is to start pooling."""
        pass

    def handle_pooled_to_pooled_same(self):
        """Handle the case when the preference is to stay pooled with
        the same project."""
        pass

    def handle_pooled_to_pooled_different(self):
        """Handle the case when the preference is to stop pooling with
        the current project and start pooling with a different
        project."""
        self.demote_pi_to_user_on_pre_project()

    def handle_pooled_to_unpooled_old(self):
        """Handle the case when the preference is to stop pooling and
        reuse another existing project owned by the PI."""
        self.demote_pi_to_user_on_pre_project()

    def handle_pooled_to_unpooled_new(self):
        """Handle the case when the preference is to stop pooling and
        create a new project."""
        self.demote_pi_to_user_on_pre_project()

    def send_email(self):
        """Send a notification email to the request and PI."""
        request = self.request_obj
        try:
            send_allocation_renewal_request_processing_email(request)
        except Exception as e:
            logger.error('Failed to send notification email. Details:')
            logger.exception(e)

    def update_allocation(self, pool):
        """Perform allocation-related handling, differing based on
        whether pooling is involved."""
        project = self.request_obj.post_project
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
