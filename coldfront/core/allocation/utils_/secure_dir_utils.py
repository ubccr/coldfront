import os
import logging

from django.core.exceptions import ValidationError
from django.db.models import Q

from coldfront.config import settings
from coldfront.core.allocation.models import Allocation, AllocationStatusChoice, \
    AllocationAttributeType, AllocationAttribute, SecureDirAddUserRequest, \
    SecureDirRemoveUserRequest, SecureDirAddUserRequestStatusChoice, \
    SecureDirRemoveUserRequestStatusChoice, SecureDirRequest, \
    SecureDirRequestStatusChoice, AllocationUser, AllocationUserStatusChoice
from coldfront.core.project.models import Project, ProjectUser
from coldfront.core.resource.models import Resource, ResourceAttribute
from coldfront.core.utils.common import utc_now_offset_aware
from coldfront.core.utils.mail import send_email_template

logger = logging.getLogger(__name__)


def create_secure_dirs(project, subdirectory_name, scratch_or_groups):
    """
    Creates one secure directory allocation: either a group directory or a
    scratch2 directory, depending on scratch_or_groups. Additionally creates
    an AllocationAttribute for the new allocation that corresponds to the
    directory path on the cluster.
    Parameters:
        - project (Project): a Project object to create a secure directory
                            allocation for
        - subdirectory_name (str): the name of the subdirectory on the cluster
        - scratch_or_groups (str): one of either 'scratch' or 'groups'
    Returns:
        - allocation
    Raises:
        - TypeError, if subdirectory_name has an invalid type
        - ValueError, if scratch_or_groups does not have a valid value
        - ValidationError, if the Allocations already exist
    """

    if not isinstance(project, Project):
        raise TypeError(f'Invalid Project {project}.')
    if not isinstance(subdirectory_name, str):
        raise TypeError(f'Invalid subdirectory_name {subdirectory_name}.')
    if scratch_or_groups not in ['scratch', 'groups']:
        raise ValueError(f'Invalid scratch_or_groups arg {scratch_or_groups}.')

    if scratch_or_groups == 'scratch':
        p2p3_directory = Resource.objects.get(name='Scratch P2/P3 Directory')
    else:
        p2p3_directory = Resource.objects.get(name='Groups P2/P3 Directory')

    query = Allocation.objects.filter(project=project,
                                      resources__in=[p2p3_directory])

    if query.exists():
        raise ValidationError('Allocation already exist')

    allocation = Allocation.objects.create(
        project=project,
        status=AllocationStatusChoice.objects.get(name='Active'),
        start_date=utc_now_offset_aware())

    p2p3_path = p2p3_directory.resourceattribute_set.get(
        resource_attribute_type__name='path')

    allocation.resources.add(p2p3_directory)

    allocation_attribute_type = AllocationAttributeType.objects.get(
        name='Cluster Directory Access')

    p2p3_subdirectory = AllocationAttribute.objects.create(
        allocation_attribute_type=allocation_attribute_type,
        allocation=allocation,
        value=os.path.join(p2p3_path.value, subdirectory_name))

    return allocation


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
    setup = state['setup']
    other = state['other']

    if (rdm_consultation['status'] == 'Denied' or
            mou['status'] == 'Denied' or
            setup['status'] == 'Denied' or
            other['timestamp']):
        return SecureDirRequestStatusChoice.objects.get(name='Denied')

    # One or more steps is pending.
    if (rdm_consultation['status'] == 'Pending' or
            mou['status'] == 'Pending'):
        return SecureDirRequestStatusChoice.objects.get(
            name='Under Review')

    # The request has been approved and is processing.
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
                        'reason': self.request_obj.denial_reason().justification,
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
        self.success_messages = []
        self.error_messages = []

    def get_messages(self):
        return self.success_messages, self.error_messages

    def run(self):
        self.approve_request()
        groups_alloc, scratch_alloc = self.call_create_secure_dir()
        if groups_alloc and scratch_alloc:
            # self.create_pi_alloc_users(groups_alloc, scratch_alloc)
            self.send_email(groups_alloc, scratch_alloc)
            message = f'The secure directory for ' \
                      f'{self.request_obj.project.name} ' \
                      f'was successfully created.'
            self.success_messages.append(message)

    def approve_request(self):
        """Set the status of the request to 'Approved - Complete'."""
        self.request_obj.status = \
            SecureDirRequestStatusChoice.objects.get(name='Approved - Complete')
        self.request_obj.completion_time = utc_now_offset_aware()
        self.request_obj.save()

    def call_create_secure_dir(self):
        """Creates the groups and scratch secure directories."""

        groups_alloc, scratch_alloc = None, None
        subdirectory_name = f'pl1_{self.request_obj.directory_name}'
        try:
            groups_alloc = \
                create_secure_dirs(self.request_obj.project,
                                   subdirectory_name,
                                   'groups')
        except Exception as e:
            message = f'Failed to create groups secure directory for ' \
                      f'{self.request_obj.project.name}.'
            self.error_messages.append(message)
            logger.error(message)
            logger.exception(e)

        try:
            scratch_alloc = \
                create_secure_dirs(self.request_obj.project,
                                   subdirectory_name,
                                   'scratch')
        except Exception as e:
            message = f'Failed to create scratch secure directory for ' \
                      f'{self.request_obj.project.name}.'
            self.error_messages.append(message)
            logger.error(message)
            logger.exception(e)

        return groups_alloc, scratch_alloc

    def create_pi_alloc_users(self, groups_alloc, scratch_alloc):
        """Creates active AllocationUsers for PIs of the project."""

        pis = ProjectUser.objects.get(
            project=self.request_obj.project,
            status__name='Active',
            role__name='Principal Investigator'
        ).values_list('user', flat=True)

        for pi in pis:
            for alloc in [groups_alloc, scratch_alloc]:
                AllocationUser.objects.create(
                    allocation=alloc,
                    user=pi,
                    status=AllocationUserStatusChoice.objects.get(name='Active')
                )

    def send_email(self, groups_alloc, scratch_alloc):
        """Send a notification email to the requester and PI."""
        if settings.EMAIL_ENABLED:
            pis = self.request_obj.project.projectuser_set.filter(
                role__name='Principal Investigator',
                status__name='Active',
                enable_notifications=True)
            users_to_notify = [x.user for x in pis]
            users_to_notify.append(self.request_obj.requester)
            users_to_notify = set(users_to_notify)

            allocation_attribute_type = AllocationAttributeType.objects.get(
                name='Cluster Directory Access')

            groups_dir = AllocationAttribute.objects.get(
                allocation_attribute_type=allocation_attribute_type,
                allocation=groups_alloc).value

            scratch_dir = AllocationAttribute.objects.get(
                allocation_attribute_type=allocation_attribute_type,
                allocation=scratch_alloc).value

            for user in users_to_notify:
                try:
                    context = {
                        'user_first_name': user.first_name,
                        'user_last_name': user.last_name,
                        'project': self.request_obj.project.name,
                        'groups_dir': groups_dir,
                        'scratch_dir': scratch_dir,
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


def get_secure_dir_allocations():
    """Returns a queryset of all active secure directory allocations."""
    scratch_directory = Resource.objects.get(name='Scratch P2/P3 Directory')
    groups_directory = Resource.objects.get(name='Groups P2/P3 Directory')

    queryset = Allocation.objects.filter(
        resources__in=[scratch_directory, groups_directory],
        status__name='Active')

    return queryset


def get_default_secure_dir_paths():
    """Returns the default Groups and Scratch secure directory paths."""

    groups_path = \
        ResourceAttribute.objects.get(
            resource_attribute_type__name='path',
            resource__name='Groups P2/P3 Directory').value
    scratch_path = \
        ResourceAttribute.objects.get(
            resource_attribute_type__name='path',
            resource__name='Scratch P2/P3 Directory').value

    return groups_path, scratch_path


def pi_eligible_to_request_secure_dir(user):
    """Returns True if the user is eligible to request a secure directory."""

    projects_with_existing_requests = \
        set(SecureDirRequest.objects.exclude(
            status__name='Denied').values_list('project__pk', flat=True))

    eligible_project = Q(project__name__startswith='fc_') | \
                       Q(project__name__startswith='ic_') | \
                       Q(project__name__startswith='co_') & \
                       Q(project__status__name='Active')

    eligible_pi = ProjectUser.objects.filter(
        eligible_project,
        user=user,
        role__name='Principal Investigator',
        status__name='Active',
    ).exclude(project__pk__in=projects_with_existing_requests)

    return eligible_pi.exists()


def get_all_secure_dir_paths():
    """Returns a set of all secure directory paths."""

    group_resource = Resource.objects.get(name='Groups P2/P3 Directory')
    scratch_resource = Resource.objects.get(name='Scratch P2/P3 Directory')

    paths = \
        set(AllocationAttribute.objects.filter(
            allocation_attribute_type__name='Cluster Directory Access',
            allocation__resources__in=[scratch_resource, group_resource]).
            values_list('value', flat=True))

    return paths


def sec_dir_name_available(directory_name, request_pk=None):
    """Returns True if the proposed directory name is available
    and False otherwise."""

    paths = get_all_secure_dir_paths()
    cleaned_dir_names = set([path.strip().split('_')[-1] for path in paths])

    pending_request_dirs = \
        set(SecureDirRequest.objects.exclude(
            status__name='Denied').exclude(
            pk=request_pk).values_list('directory_name', flat=True))
    cleaned_dir_names.update(pending_request_dirs)

    return directory_name not in cleaned_dir_names
