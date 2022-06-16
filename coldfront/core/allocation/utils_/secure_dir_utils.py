import os
import logging

from django.core.exceptions import ValidationError

from coldfront.config import settings
from coldfront.core.allocation.models import Allocation, AllocationStatusChoice, \
    AllocationAttributeType, AllocationAttribute, SecureDirAddUserRequest, \
    SecureDirRemoveUserRequest, SecureDirAddUserRequestStatusChoice, \
    SecureDirRemoveUserRequestStatusChoice, SecureDirRequest, \
    SecureDirRequestStatusChoice
from coldfront.core.project.models import Project
from coldfront.core.resource.models import Resource
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.mail import send_email_template

logger = logging.getLogger(__name__)


def create_secure_dirs(project, subdirectory_name):
    """
    Creates two secure directory allocations: group directory and
    scratch2 directory. Additionally creates an AllocationAttribute for each
    new allocation that corresponds to the directory path on the cluster.

    Parameters:
        - project (Project): a Project object to create a secure directory
                            allocation for
        - subdirectory_name (str): the name of the subdirectories on the cluster

    Returns:
        - Tuple of (groups_allocation, scratch2_allocation)

    Raises:
        - TypeError, if either argument has an invalid type
        - ValidationError, if the Allocations already exist
    """

    if not isinstance(project, Project):
        raise TypeError(f'Invalid Project {project}.')
    if not isinstance(subdirectory_name, str):
        raise TypeError(f'Invalid subdirectory_name {subdirectory_name}.')

    scratch2_p2p3_directory = Resource.objects.get(name='Scratch2 P2/P3 Directory')
    groups_p2p3_directory = Resource.objects.get(name='Groups P2/P3 Directory')

    query = Allocation.objects.filter(project=project,
                                      resources__in=[scratch2_p2p3_directory,
                                                     groups_p2p3_directory])
    if query.exists():
        raise ValidationError('Allocations already exist')

    groups_allocation = Allocation.objects.create(
        project=project,
        status=AllocationStatusChoice.objects.get(name='Active'),
        start_date=utc_now_offset_aware())

    scratch2_allocation = Allocation.objects.create(
        project=project,
        status=AllocationStatusChoice.objects.get(name='Active'),
        start_date=utc_now_offset_aware())

    groups_p2p3_path = groups_p2p3_directory.resourceattribute_set.get(
        resource_attribute_type__name='path')
    scratch2_p2p3_path = scratch2_p2p3_directory.resourceattribute_set.get(
        resource_attribute_type__name='path')

    groups_allocation.resources.add(groups_p2p3_directory)
    scratch2_allocation.resources.add(scratch2_p2p3_directory)

    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Cluster Directory Access')

    groups_p2p3_subdirectory = AllocationAttribute.objects.create(
        allocation_attribute_type=allocation_attribute_type,
        allocation=groups_allocation,
        value=os.path.join(groups_p2p3_path.value, subdirectory_name))

    scratch2_p2p3_subdirectory = AllocationAttribute.objects.create(
        allocation_attribute_type=allocation_attribute_type,
        allocation=scratch2_allocation,
        value=os.path.join(scratch2_p2p3_path.value, subdirectory_name))

    return groups_allocation, scratch2_allocation


def get_secure_dir_manage_user_request_objects(self, action):
    """
    Sets attributes pertaining to a secure directory based on the
    action being performed.

    Parameters:
        - self (object): object to set attributes for
        - action (str): the action being performed, either 'add' or 'remove'

    Raises:
        - TypeError, if the 'self' object is not an object
        - ValueError, if action is not one of 'add' or 'remove'
    """

    action = action.lower()
    if not isinstance(self, object):
        raise TypeError(f'Invalid self {self}.')
    if action not in ['add', 'remove']:
        raise ValueError(f'Invalid action {action}.')

    add_bool = action == 'add'

    request_obj = SecureDirAddUserRequest \
        if add_bool else SecureDirRemoveUserRequest
    request_status_obj = SecureDirAddUserRequestStatusChoice \
        if add_bool else SecureDirRemoveUserRequestStatusChoice

    language_dict = {
        'preposition': 'to' if add_bool else 'from',
        'noun': 'addition' if add_bool else 'removal',
        'verb': 'add' if add_bool else 'remove'
    }

    setattr(self, 'action', action.lower())
    setattr(self, 'add_bool', add_bool)
    setattr(self, 'request_obj', request_obj)
    setattr(self, 'request_status_obj', request_status_obj)
    setattr(self, 'language_dict', language_dict)


def secure_dir_request_state_status(secure_dir_request):
    """Return a SecureDirRequestStatusChoice, based on the
    'state' field of the given SecureDirRequest."""
    if not isinstance(secure_dir_request, SecureDirRequest):
        raise TypeError(
            f'Provided request has unexpected type {type(secure_dir_request)}.')

    state = secure_dir_request.state
    rdm_consultation = state['rdm_consultation']
    mou = state['mou']
    other = state['other']

    if (rdm_consultation['status'] == 'Denied' or
            mou['status'] == 'Denied' or
            other['timestamp']):
        return SecureDirRequestStatusChoice.objects.get(name='Denied')

    # One or more steps is pending.
    if (rdm_consultation['status'] == 'Pending' or
            mou['status'] == 'Pending'):
        return SecureDirRequestStatusChoice.objects.get(
            name='Under Review')

    # The request has been approved, and is processing, scheduled, or complete.
    # The states 'Approved - Scheduled' and 'Approved - Complete' should only
    # be set once the request is scheduled for activation or activated.
    return SecureDirRequestStatusChoice.objects.get(
        name='Approved - Processing')


class SecureDirRequestDenialRunner(object):
    """An object that performs necessary database changes when a new
    secure directory request is denied."""

    def __init__(self, request_obj):
        self.request_obj = request_obj

    def run(self):
        self.deny_request()
        self.send_email()

    def deny_request(self):
        """Set the status of the request to 'Denied'."""
        self.request_obj.status = \
            SecureDirRequestStatusChoice.objects.get(name='Denied')
        self.request_obj.save()

    def send_email(self):
        """Send a notification email to the requester and PI."""
        if settings.EMAIL_ENABLED:
            pis = self.request_obj.project.projectuser_set.filter(
                role__name='Principal Investigator',
                status__name='Active',
                enable_notifications=True)
            users_to_notify = [x.user for x in pis]
            users_to_notify.append(self.request_obj.requester)
            users_to_notify = set(users_to_notify)

            for user in users_to_notify:
                try:
                    context = {
                        'user_first_name': user.first_name,
                        'user_last_name': user.last_name,
                        'project': self.request_obj.project.name,
                        'reason': self.request_obj.denial_reason(),
                        'signature': settings.EMAIL_SIGNATURE,
                        'support_email': settings.CENTER_HELP_EMAIL,
                    }

                    send_email_template(
                        f'Secure Directory Request Denied',
                        'email/secure_dir_request/secure_dir_request_denied.txt',
                        context,
                        settings.EMAIL_SENDER,
                        [user.email])

                except Exception as e:
                    logger.error('Failed to send notification email. Details:\n')
                    logger.exception(e)


class SecureDirRequestApprovalRunner(object):
    """An object that performs necessary database changes when a new
    secure directory request is approved and completed."""

    def __init__(self, request_obj):
        self.request_obj = request_obj

    def run(self):
        self.approve_request()
        self.send_email()

    def approve_request(self):
        """Set the status of the request to 'Approved - Complete'."""
        self.request_obj.status = \
            SecureDirRequestStatusChoice.objects.get(name='Approved - Complete')
        self.request_obj.completion_time = utc_now_offset_aware()
        self.request_obj.save()

    def send_email(self):
        """Send a notification email to the requester and PI."""
        if settings.EMAIL_ENABLED:
            pis = self.request_obj.project.projectuser_set.filter(
                role__name='Principal Investigator',
                status__name='Active',
                enable_notifications=True)
            users_to_notify = [x.user for x in pis]
            users_to_notify.append(self.request_obj.requester)
            users_to_notify = set(users_to_notify)

            for user in users_to_notify:
                try:
                    context = {
                        'user_first_name': user.first_name,
                        'user_last_name': user.last_name,
                        'project': self.request_obj.project.name,
                        'groups': self.request_obj.state['paths']['groups'],
                        'scratch': self.request_obj.state['paths']['scratch'],
                        'signature': settings.EMAIL_SIGNATURE,
                        'support_email': settings.CENTER_HELP_EMAIL,
                    }

                    send_email_template(
                        f'Secure Directory Request Approved',
                        'email/secure_dir_request/secure_dir_request_approved.txt',
                        context,
                        settings.EMAIL_SENDER,
                        [user.email])

                except Exception as e:
                    logger.error('Failed to send notification email. Details:\n')
                    logger.exception(e)