from coldfront.api.statistics.utils import set_project_user_allocation_value
from coldfront.core.allocation.models import AllocationAttribute
from coldfront.core.allocation.models import AllocationAttributeType
from coldfront.core.allocation.models import AllocationPeriod
from coldfront.core.allocation.models import AllocationRenewalRequest
from coldfront.core.allocation.models import AllocationRenewalRequestStatusChoice
from coldfront.core.allocation.models import AllocationStatusChoice
from coldfront.core.allocation.utils import get_or_create_active_allocation_user
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.allocation.utils import next_allocation_start_datetime
from coldfront.core.project.models import Project
from coldfront.core.project.models import ProjectAllocationRequestStatusChoice
from coldfront.core.project.models import ProjectStatusChoice
from coldfront.core.project.models import ProjectUser
from coldfront.core.project.models import ProjectUserRoleChoice
from coldfront.core.project.models import ProjectUserStatusChoice
from coldfront.core.project.models import SavioProjectAllocationRequest
from coldfront.core.project.utils_.request_utils import project_allocation_request_latest_update_timestamp
from coldfront.core.project.utils_.request_utils import savio_request_denial_reason
from coldfront.core.statistics.models import ProjectTransaction
from coldfront.core.statistics.models import ProjectUserTransaction
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.common import project_detail_url
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.common import validate_num_service_units
from coldfront.core.utils.mail import send_email_template
from collections import namedtuple
from datetime import timedelta
from decimal import Decimal
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from django.urls import reverse
from urllib.parse import urljoin
import logging


logger = logging.getLogger(__name__)


def get_current_allocation_period():
    return AllocationPeriod.objects.get(name='AY21-22')


def get_pi_current_active_fca_project(pi_user):
    """Given a User object representing a PI, return its current,
    active fc_ Project.

    A Project is considered "active" if it has a completed
    AllocationRenewalRequest for the current AllocationPeriod or if it
    has a completed SavioProjectAllocationRequest during the period.

    Parameters:
        - pi_user: a User object.

    Returns:
        - A Project object.

    Raises:
        - AllocationRenewalRequest.MultipleObjectsReturned, if the PI
          has more than one 'Complete' renewal request during the
          current AllocationPeriod.
        - Project.DoesNotExist, if none are found.
        - Project.MultipleObjectsReturned, if multiple are found.
        - SavioProjectAllocationRequest.MultipleObjectsReturned, if the
          PI has more than one 'Approved - Complete' request.
        - Exception, if any other errors occur.

    TODO: Once the first AllocationPeriod has ended, this will need to
    TODO: be refined to filter on time.
    """
    project = None

    # Check AllocationRenewalRequests.
    allocation_period = get_current_allocation_period()
    renewal_request_status = AllocationRenewalRequestStatusChoice.objects.get(
        name='Complete')
    renewal_requests = AllocationRenewalRequest.objects.filter(
        allocation_period=allocation_period,
        pi=pi_user,
        status=renewal_request_status,
        post_project__name__startswith='fc_')
    if renewal_requests.exists():
        if renewal_requests.count() > 1:
            message = (
                f'PI {pi_user.username} unexpectedly has more than one '
                f'completed FCA AllocationRenewalRequest during '
                f'AllocationPeriod {allocation_period.name}.')
            logger.error(message)
            raise AllocationRenewalRequest.MultipleObjectsReturned(message)
        project = renewal_requests.first().post_project

    # Check SavioProjectAllocationRequests.
    project_request_status = ProjectAllocationRequestStatusChoice.objects.get(
        name='Approved - Complete')
    project_requests = SavioProjectAllocationRequest.objects.filter(
        allocation_type=SavioProjectAllocationRequest.FCA,
        pi=pi_user,
        status=project_request_status)
    if project_requests.exists():
        if project_requests.count() > 1:
            message = (
                f'PI {pi_user.username} unexpectedly has more than one '
                f'completed FCA SavioProjectAllocationRequest.')
            logger.error(message)
            raise SavioProjectAllocationRequest.MultipleObjectsReturned(
                message)
        # The PI should not have both a renewal request and a project request.
        if project:
            message = (
                f'PI {pi_user.username} unexpectedly has both an FCA '
                f'AllocationRenewalRequest and an FCA'
                f'SavioProjectAllocationRequest.')
            raise Exception(message)
        project = project_requests.first().project

    if not project:
        message = f'PI {pi_user.username} has no active FCA Project.'
        raise Project.DoesNotExist(message)

    return project


def has_non_denied_project_request(pi):
    """Return whether or not the given PI User has a non-"Denied"
    SavioProjectAllocationRequest.

    TODO: Once the first AllocationPeriod has ended, this will need to
    TODO: be refined to filter on time.
    """
    if not isinstance(pi, User):
        raise TypeError(f'{pi} is not a User object.')
    status_names = [
        'Under Review', 'Approved - Processing', 'Approved - Complete']
    return SavioProjectAllocationRequest.objects.filter(
        pi=pi,
        status__name__in=status_names).exists()


def has_non_denied_renewal_request(pi, allocation_period):
    """Return whether or not the given PI User has a non-"Denied"
    AllocationRenewalRequest for the given AllocationPeriod."""
    if not isinstance(pi, User):
        raise TypeError(f'{pi} is not a User object.')
    if not isinstance(allocation_period, AllocationPeriod):
        raise TypeError(
            f'{allocation_period} is not an AllocationPeriod object.')
    status_names = ['Under Review', 'Approved', 'Complete']
    return AllocationRenewalRequest.objects.filter(
        pi=pi,
        allocation_period=allocation_period,
        status__name__in=status_names).exists()


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
        'signature': settings.EMAIL_SIGNATURE,
        'support_email': settings.CENTER_HELP_EMAIL,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [request.requester.email, request.pi.email]
    cc = settings.REQUEST_APPROVAL_CC_LIST

    send_email_template(
        subject, template_name, context, sender, receiver_list, cc=cc)


def send_allocation_renewal_request_processing_email(request,
                                                     num_service_units):
    """Send a notification email to the requester and PI associated with
    the given AllocationRenewalRequest stating that the request has been
    processed, and the given number of service units have been added."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = f'{str(request)} Processed'
    template_name = (
        'email/project_renewal/project_renewal_request_processed.txt')

    context = {
        'center_name': settings.CENTER_NAME,
        'num_service_units': str(num_service_units),
        'pi_name': f'{request.pi.first_name} {request.pi.last_name}',
        'requested_project_name': request.post_project.name,
        'requested_project_url': project_detail_url(request.post_project),
        'signature': settings.EMAIL_SIGNATURE,
        'support_email': settings.CENTER_HELP_EMAIL,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [request.requester.email, request.pi.email]
    cc = settings.REQUEST_APPROVAL_CC_LIST

    send_email_template(
        subject, template_name, context, sender, receiver_list, cc=cc)


def send_new_allocation_renewal_request_admin_notification_email(request):
    """Send an email to admins notifying them of a new
    AllocationRenewalRequest."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = 'New Allocation Renewal Request'
    template_name = (
        'email/project_renewal/admins_new_project_renewal_request.txt')

    requester = request.requester
    requester_str = (
        f'{requester.first_name} {requester.last_name} ({requester.email})')

    pi = request.pi
    pi_str = f'{pi.first_name} {pi.last_name} ({pi.email})'

    detail_view_name = 'pi-allocation-renewal-request-detail'
    review_url = urljoin(
        settings.CENTER_BASE_URL,
        reverse(detail_view_name, kwargs={'pk': request.pk}))

    context = {
        'pi_str': pi_str,
        'requester_str': requester_str,
        'review_url': review_url,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = settings.EMAIL_ADMIN_LIST

    send_email_template(subject, template_name, context, sender, receiver_list)


def send_new_allocation_renewal_request_pi_notification_email(request):
    """Send an email to the PI of the given request notifying them that
    someone has made a new AllocationRenewalRequest under their name.

    It is the caller's responsibility to ensure that the requester and
    PI are different (so the PI does not get a notification for their
    own request)."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = 'New Allocation Renewal Request under Your Name'
    template_name = 'email/project_renewal/pi_new_project_renewal_request.txt'

    requester = request.requester
    requester_str = (
        f'{requester.first_name} {requester.last_name} ({requester.email})')

    pi = request.pi
    pi_str = f'{pi.first_name} {pi.last_name}'

    detail_view_name = 'pi-allocation-renewal-request-detail'
    center_base_url = settings.CENTER_BASE_URL
    review_url = urljoin(
        center_base_url, reverse(detail_view_name, kwargs={'pk': request.pk}))
    login_url = urljoin(center_base_url, reverse('login'))

    context = {
        'login_url': login_url,
        'pi_str': pi_str,
        'requested_project_name': request.post_project.name,
        'requester_str': requester_str,
        'review_url': review_url,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = [pi.email]

    send_email_template(subject, template_name, context, sender, receiver_list)


def send_new_allocation_renewal_request_pooling_notification_email(request):
    """Send a notification email to the managers and PIs of the project
    being requested to pool with stating that someone is attempting to
    pool."""
    email_enabled = import_from_settings('EMAIL_ENABLED', False)
    if not email_enabled:
        return

    subject = (
        f'New request to pool with your project {request.post_project.name}')
    template_name = (
        'email/project_renewal/'
        'managers_new_pooled_project_renewal_request.txt')

    requester = request.requester
    requester_str = (
        f'{requester.first_name} {requester.last_name} ({requester.email})')

    pi = request.pi
    pi_str = f'{pi.first_name} {pi.last_name} ({pi.email})'

    context = {
        'center_name': settings.CENTER_NAME,
        'requested_project_name': request.post_project.name,
        'requester_str': requester_str,
        'pi_str': pi_str,
        'support_email': settings.CENTER_HELP_EMAIL,
        'signature': settings.EMAIL_SIGNATURE,
    }

    sender = settings.EMAIL_SENDER
    receiver_list = request.post_project.managers_and_pis_emails()

    send_email_template(subject, template_name, context, sender, receiver_list)


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
        'DenialReason', 'category justification timestamp')

    new_project_request = request.new_project_request

    if other['timestamp']:
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
        request_updated = project_allocation_request_latest_update_timestamp(
            new_project_request)
        max_timestamp = max(max_timestamp, request_updated)

    return max_timestamp


def allocation_renewal_request_state_status(request):
    """Return an AllocationRenewalRequestStatusChoice, based on the
    'state' field of the given AllocationRenewalRequest, and/or an
    associated SavioProjectAllocationRequest.

    This method returns one of only two states: 'Denied' or 'Under
    Review'. The other two possible states, 'Approved' and 'Complete',
    should be set by some other process.
        - 'Approved' should be set when the request is scheduled for
           processing.
        - 'Complete' should be set when the request is actually
          processed.

    # TODO: Currently, the request is set to 'Approved' and then
    # TODO: immediately changed to 'Complete' when an administrator
    # TODO: clicks the 'Submit' button. In the future, requests may not
    # TODO: be processed immediately; instead, it will be handled by
    # TODO: some other process (e.g., a cron job).
    """
    if not isinstance(request, AllocationRenewalRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(request)}.')

    state = request.state
    eligibility = state['eligibility']
    other = state['other']

    denied_status = AllocationRenewalRequestStatusChoice.objects.get(
        name='Denied')

    # The request was denied for some other non-listed reason.
    if other['timestamp']:
        return denied_status

    new_project_request = request.new_project_request
    if new_project_request:
        # The request was for a new Project, which was denied.
        status_name = new_project_request.status.name
        if status_name == 'Denied':
            return denied_status
    else:
        # The PI was ineligible.
        if eligibility['status'] == 'Denied':
            return denied_status

    # The request has not been denied, so it is under review.
    return AllocationRenewalRequestStatusChoice.objects.get(
        name='Under Review')


class AllocationRenewalRunnerBase(object):
    """A base class that Runners for handling AllocationRenewalsRequests
    should inherit from."""

    def __init__(self, request_obj, *args, **kwargs):
        self.request_obj = request_obj

    def run(self):
        raise NotImplementedError('This method is not implemented.')

    def assert_request_not_status(self, unexpected_status):
        """Raise an assertion error if the request has the given
        unexpected status."""
        if not isinstance(
                unexpected_status, AllocationRenewalRequestStatusChoice):
            raise TypeError(
                'Status is not an AllocationRenewalRequestStatusChoice.')
        message = f'The request must not have status \'{unexpected_status}\'.'
        assert self.request_obj.status != unexpected_status, message

    def assert_request_status(self, expected_status):
        """Raise an assertion error if the request does not have the
        given expected status."""
        if not isinstance(
                expected_status, AllocationRenewalRequestStatusChoice):
            raise TypeError(
                'Status is not an AllocationRenewalRequestStatusChoice.')
        message = f'The request must have status \'{expected_status}\'.'
        assert self.request_obj.status == expected_status, message

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
        project = self.request_obj.post_project
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
        pre_project = request.pre_project
        post_project = request.post_project
        is_pooled_pre = pre_project and pre_project.is_pooled()
        is_pooled_post = post_project.is_pooled()

        def log_message():
            pre_str = 'non-pooling' if not is_pooled_pre else 'pooling'
            post_str = 'non-pooling' if not is_pooled_post else 'pooling'
            return (
                f'AllocationRenewalRequest {request.pk}: {pre_str} in '
                f'pre-project {pre_project.name if pre_project else None} to '
                f'{post_str} in post-project {post_project.name}.')

        try:
            preference_case = request.get_pooling_preference_case()
        except ValueError as e:
            logger.error(log_message())
            raise e
        if preference_case == request.UNPOOLED_TO_UNPOOLED:
            logger.info(log_message())
            self.handle_unpooled_to_unpooled()
        elif preference_case == request.UNPOOLED_TO_POOLED:
            logger.info(log_message())
            self.handle_unpooled_to_pooled()
        elif preference_case == request.POOLED_TO_POOLED_SAME:
            logger.info(log_message())
            self.handle_pooled_to_pooled_same()
        elif preference_case == request.POOLED_TO_POOLED_DIFFERENT:
            logger.info(log_message())
            self.handle_pooled_to_pooled_different()
        elif preference_case == request.POOLED_TO_UNPOOLED_OLD:
            logger.info(log_message())
            self.handle_pooled_to_unpooled_old()
        elif preference_case == request.POOLED_TO_UNPOOLED_NEW:
            logger.info(log_message())
            self.handle_pooled_to_unpooled_new()

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
        unexpected_status = AllocationRenewalRequestStatusChoice.objects.get(
            name='Complete')
        self.assert_request_not_status(unexpected_status)

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
        self.num_service_units = num_service_units

    def run(self):
        request = self.request_obj
        post_project = request.post_project

        self.upgrade_pi_user()
        old_project_status = post_project.status
        post_project = self.activate_project(post_project)

        allocation, new_value = self.update_allocation(old_project_status)
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
        self.complete_request(self.num_service_units)
        self.send_email()

        return post_project, allocation

    @staticmethod
    def activate_project(project):
        """Set the given Project's status to 'Active'."""
        status = ProjectStatusChoice.objects.get(name='Active')
        project.status = status
        project.save()
        return project

    def complete_request(self, num_service_units):
        """Set the status of the request to 'Complete', set its number
        of service units, and set its completion_time."""
        self.request_obj.status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Complete')
        self.request_obj.num_service_units = num_service_units
        self.request_obj.completion_time = utc_now_offset_aware()
        self.request_obj.save()

    def deactivate_pre_project(self):
        """Deactivate the request's pre_project, which involves setting
        its status to 'Inactive and its corresponding compute
        Allocation's status to 'Expired', unless either of the following
        is true:
            (a) The pre_project has been renewed during this
                AllocationPeriod, or
            (b) A different PI made an approved and complete request to
                pool with the pre_project.

        TODO: Once the first AllocationPeriod has ended, criterion (b)
        TODO: will need to be refined to filter on time.

        If the pre_project is None, do nothing."""
        request = self.request_obj
        pre_project = request.pre_project
        if not pre_project:
            logger.info(
                f'AllocationRenewalRequest {request.pk} has no pre-Project. '
                f'Skipping deactivation.')
            return

        # (a) If the pre_project has been renewed during this AllocationPeriod,
        # do not deactivate it.
        # TODO: Reconsider the use of this AllocationPeriod moving forward.
        allocation_period = get_current_allocation_period()
        complete_renewal_request_status = \
            AllocationRenewalRequestStatusChoice.objects.get(name='Complete')
        completed_renewals = AllocationRenewalRequest.objects.filter(
            allocation_period=allocation_period,
            status=complete_renewal_request_status,
            post_project=pre_project)
        if completed_renewals.exists():
            message = (
                f'Project {pre_project.name} has been renewed during '
                f'AllocationPeriod {allocation_period.name}. Skipping '
                f'deactivation.')
            logger.info(message)
            return

        # (b) If a different PI made an 'Approved - Complete' request to pool
        # with the pre_project, do not deactivate it.
        # TODO: Once the first AllocationPeriod has ended, this will need to be
        # TODO: refined to filter on time.
        approved_complete_request_status = \
            ProjectAllocationRequestStatusChoice.objects.get(
                name='Approved - Complete')
        approved_complete_pool_requests_from_other_pis = \
            SavioProjectAllocationRequest.objects.filter(
                Q(allocation_type=SavioProjectAllocationRequest.FCA) &
                ~Q(pi=request.pi) &
                Q(pool=True) &
                Q(project=pre_project),
                Q(status=approved_complete_request_status))
        if approved_complete_pool_requests_from_other_pis.exists():
            message = (
                f'Project {pre_project.name} has been pooled with by a '
                f'different PI. Skipping deactivation.')
            logger.info(message)
            return

        pre_project.status = ProjectStatusChoice.objects.get(
            name='Inactive')
        pre_project.save()
        allocation = get_project_compute_allocation(pre_project)
        allocation.status = AllocationStatusChoice.objects.get(
            name='Expired')
        allocation.save()
        message = (
            f'Set Project {pre_project.name}\'s status to '
            f'{pre_project.status.name} and Allocation {allocation.pk}\'s '
            f'status to {allocation.status.name}.')
        logger.info(message)

    def demote_pi_to_user_on_pre_project(self):
        """If the pre_project is pooled (i.e., it has more than one PI),
        demote the PI from 'Principal Investigator' to 'User'.

        If the pre_project is None, do nothing."""
        request = self.request_obj
        pi = request.pi
        pre_project = request.pre_project
        if not pre_project:
            logger.info(
                f'AllocationRenewalRequest {request.pk} has no pre-Project. '
                f'Skipping demotion.')
            return
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
                message = (
                    f'Demoted {pi.username} from \'Principal Investigator\' '
                    f'to \'User\' on Project {pre_project.name}.')
                logger.info(message)
        else:
            message = (
                f'Project {pre_project.name} only has one PI. Skipping '
                f'demotion.')
            logger.info(message)

    def handle_unpooled_to_unpooled(self):
        """Handle the case when the preference is to stay unpooled."""
        pass

    def handle_unpooled_to_pooled(self):
        """Handle the case when the preference is to start pooling."""
        self.deactivate_pre_project()

    def handle_pooled_to_pooled_same(self):
        """Handle the case when the preference is to stay pooled with
        the same project."""
        pass

    def handle_pooled_to_pooled_different(self):
        """Handle the case when the preference is to stop pooling with
        the current project and start pooling with a different
        project."""
        self.demote_pi_to_user_on_pre_project()
        self.deactivate_pre_project()

    def handle_pooled_to_unpooled_old(self):
        """Handle the case when the preference is to stop pooling and
        reuse another existing project owned by the PI."""
        self.demote_pi_to_user_on_pre_project()
        self.deactivate_pre_project()

    def handle_pooled_to_unpooled_new(self):
        """Handle the case when the preference is to stop pooling and
        create a new project."""
        self.demote_pi_to_user_on_pre_project()
        self.deactivate_pre_project()

    def send_email(self):
        """Send a notification email to the request and PI."""
        request = self.request_obj
        try:
            send_allocation_renewal_request_processing_email(
                request, self.num_service_units)
        except Exception as e:
            logger.error('Failed to send notification email. Details:')
            logger.exception(e)

    def update_allocation(self, old_project_status):
        """Perform allocation-related handling. Use the given
        ProjectStatusChoice, which the post_project had prior to being
        activated, to potentially set the start and end dates."""
        project = self.request_obj.post_project
        allocation_type = SavioProjectAllocationRequest.FCA

        allocation = get_project_compute_allocation(project)
        allocation.status = AllocationStatusChoice.objects.get(name='Active')
        # For the start and end dates, if the Project is not 'Active' or the
        # date is not set, set it.
        if old_project_status.name != 'Active' or not allocation.start_date:
            allocation.start_date = utc_now_offset_aware()
        if old_project_status.name != 'Active' or not allocation.end_date:
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

        # Increase the allocation's service units.
        allocation_attribute_type = AllocationAttributeType.objects.get(
            name='Service Units')
        allocation_attribute, _ = \
            AllocationAttribute.objects.get_or_create(
                allocation_attribute_type=allocation_attribute_type,
                allocation=allocation)
        existing_value = (
            Decimal(allocation_attribute.value) if allocation_attribute.value
            else settings.ALLOCATION_MIN)
        new_value = existing_value + self.num_service_units
        validate_num_service_units(new_value)
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
        project = self.request_obj.post_project
        date_time = utc_now_offset_aware()
        for project_user in project.projectuser_set.all():
            user = project_user.user
            allocation_updated = set_project_user_allocation_value(
                user, project, value)
            if allocation_updated:
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
