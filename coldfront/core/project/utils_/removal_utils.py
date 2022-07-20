from itertools import chain
import logging

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.db import transaction

from coldfront.core.allocation.models import Allocation, \
    AllocationUserStatusChoice, AllocationAttributeType
from coldfront.core.allocation.utils import get_project_compute_allocation
from coldfront.core.project.models import (ProjectUserRemovalRequestStatusChoice,
                                           ProjectUserRemovalRequest,
                                           ProjectUserStatusChoice)
from coldfront.core.utils.mail import send_email_template
from coldfront.core.utils.common import import_from_settings


logger = logging.getLogger(__name__)


class ProjectRemovalRequestRunner(object):
    """An object that performs necessary database changes when a new
    project removal request is made."""

    def __init__(self, requester_obj, user_obj, proj_obj):
        self.requester_obj = requester_obj
        self.user_obj = user_obj
        self.proj_obj = proj_obj
        # A list of messages to display to the user.
        self.error_messages = []
        self.success_messages = []

    def run(self):
        pending_status = ProjectUserRemovalRequestStatusChoice.objects.get(name='Pending')
        processing_status = ProjectUserRemovalRequestStatusChoice.objects.get(name='Processing')
        flag = True
        removal_request = None

        # check for active removal request for user
        if ProjectUserRemovalRequest.objects.filter(
                project_user__user=self.user_obj,
                project_user__project=self.proj_obj,
                status__in=[pending_status, processing_status]).exists():
            message = f'Error requesting removal of user {self.user_obj.username}. ' \
                      f'An active project removal request for user ' \
                      f'{self.user_obj.username} already exists.'
            self.error_messages.append(message)
            flag = False

        # PIs cannot request to leave own project
        if self.proj_obj.projectuser_set.filter(
                user=self.user_obj,
                role__name='Principal Investigator').exists():
            message = f'Error requesting removal of user {self.user_obj.username}. ' \
                      f'PIs cannot request to leave their project.'
            self.error_messages.append(message)
            flag = False

        # Managers can only leave if there are multiple managers
        if self.proj_obj.projectuser_set.filter(
                user=self.user_obj,
                role__name='Manager').exists() \
                and len(self.proj_obj.projectuser_set.filter(
            role__name='Manager',
            status__name='Active')) == 1:
            message = f'Error requesting removal of user {self.user_obj.username}. ' \
                      f'Cannot remove the only manager in a project.'
            self.error_messages.append(message)
            flag = False

        if flag:
            removal_request, created = ProjectUserRemovalRequest.objects.get_or_create(
                project_user=self.proj_obj.projectuser_set.get(user=self.user_obj),
                requester=self.requester_obj
            )

            removal_request.status = pending_status
            removal_request.save()

            proj_user_obj = self.proj_obj.projectuser_set.get(user=self.user_obj)
            proj_user_obj.status = ProjectUserStatusChoice.objects.get(name='Pending - Remove')
            proj_user_obj.save()

            message = f'Successfully created project removal request for ' \
                      f'user {self.user_obj.username}.'
            self.success_messages.append(message)

        return removal_request

    def get_messages(self):
        """A getter for this instance's user_messages."""
        return self.success_messages, self.error_messages

    def send_emails(self):
        email_enabled = import_from_settings('EMAIL_ENABLED', False)

        if email_enabled:
            email_sender = import_from_settings('EMAIL_SENDER')
            email_signature = import_from_settings('EMAIL_SIGNATURE')
            support_email = import_from_settings('CENTER_HELP_EMAIL')
            email_admin_list = import_from_settings('EMAIL_ADMIN_LIST')

            # Send emails to the removed user, the project's PIs (who have
            # notifications enabled), and the project's managers. Exclude the
            # user who made the request.
            pi_condition = Q(
                role__name='Principal Investigator', status__name='Active',
                enable_notifications=True)
            manager_condition = Q(role__name='Manager', status__name='Active')
            manager_pi_queryset = self.proj_obj.projectuser_set.filter(
                pi_condition | manager_condition).exclude(
                    user=self.requester_obj)
            users_to_notify = [x.user for x in manager_pi_queryset]
            if self.user_obj != self.requester_obj:
                users_to_notify.append(self.user_obj)
            for user in users_to_notify:
                template_context = {
                    'user_first_name': user.first_name,
                    'user_last_name': user.last_name,
                    'requester_first_name': self.requester_obj.first_name,
                    'requester_last_name': self.requester_obj.last_name,
                    'remove_user_first_name': self.user_obj.first_name,
                    'remove_user_last_name': self.user_obj.last_name,
                    'project_name': self.proj_obj.name,
                    'signature': email_signature,
                    'support_email': support_email,
                }
                send_email_template(
                    'Project Removal Request',
                    'email/project_removal/project_removal.txt',
                    template_context,
                    email_sender,
                    [user.email])

            # Email cluster administrators.
            template_context = {
                'user_first_name': self.user_obj.first_name,
                'user_last_name': self.user_obj.last_name,
                'project_name': self.proj_obj.name,
            }
            send_email_template(
                'Project Removal Request',
                'email/project_removal/project_removal_admin.txt',
                template_context,
                email_sender,
                email_admin_list)


class ProjectRemovalRequestProcessingRunner(object):
    """An object that performs necessary database changes after a project
    removal request has been completed."""

    def __init__(self, request_obj):
        assert isinstance(request_obj, ProjectUserRemovalRequest)
        self._request_obj = request_obj
        self._removed_user = self._request_obj.project_user.user
        self._project = self._request_obj.project_user.project
        self._allocation = get_project_compute_allocation(self._project)
        # A list of messages to display to the user.
        self._success_messages = []
        self._warning_messages = []

    def run(self):
        """Apply database changes in a transaction. Log success messages
        and send emails separately to prevent failures from rolling it
        back."""
        with transaction.atomic():
            self._remove_user_from_project()
            self._remove_user_from_project_compute_allocation()
        self._log_success_messages()
        self._send_emails_safe()

    def _log_success_messages(self):
        """Write success messages to the log.

        Catch all exceptions to prevent rolling back any enclosing
        transaction.
        """
        try:
            for message in self._success_messages:
                logger.info(message)
        except Exception:
            pass

    def _remove_user_from_project(self):
        """Set the ProjectUser's status to 'Removed'."""
        removed_status = ProjectUserStatusChoice.objects.get(name='Removed')
        project_user = self._request_obj.project_user
        project_user.status = removed_status
        project_user.save()

        message = (
            f'Set ProjectUser {project_user.pk} status to '
            f'"{removed_status.name}".')
        self._success_messages.append(message)

    def _remove_user_from_project_compute_allocation(self):
        """Set the AllocationUser's status to 'Removed', if it exists.
        Set the corresponding 'Cluster Account Status' to 'Denied', if
        it exists."""
        allocation_users = \
            self._allocation.allocationuser_set.prefetch_related(
                'allocationuserattribute_set').filter(user=self._removed_user)
        if not allocation_users.exists():
            # Allow the ProjectUser to not have a corresponding AllocationUser,
            # but log an error message and store a warning.
            message = (
                f'Failed to retrieve an AllocationUser for removed User '
                f'{self._removed_user.pk} under compute Allocation '
                f'{self._allocation.pk}.')
            self._warning_messages.append(message)
            logger.error(message)
            return

        removed_status = AllocationUserStatusChoice.objects.get(
            name='Removed')
        allocation_user = allocation_users.first()
        allocation_user.status = removed_status
        allocation_user.save()

        message = (
            f'Set AllocationUser {allocation_user.pk} status to '
            f'"{removed_status.name}".')
        self._success_messages.append(message)

        cluster_account_status_type = AllocationAttributeType.objects.get(
            name='Cluster Account Status')
        try:
            cluster_account_status = \
                allocation_user.allocationuserattribute_set.get(
                    allocation_attribute_type=cluster_account_status_type)
        except ObjectDoesNotExist:
            # Allow the AllocationUser to not have a "Cluster Account Status",
            # but log an error message and store a warning message.
            message = (
                f'Failed to retrieve a "Cluster Account Status"'
                f' AllocationAttributeType for AllocationUser '
                f'{allocation_user.pk}.')
            self._warning_messages.append(message)
            logger.error(message)
            return
        else:
            cluster_account_status.value = 'Denied'
            cluster_account_status.save()
            message = (
                f'Set AllocationAttribute {cluster_account_status_type.pk} '
                f'value to "Denied".')
            self._success_messages.append(message)

    def _send_emails(self):
        """Try to send emails. If one send fails, continue with the
        rest. Return the number of failures."""
        email_enabled = import_from_settings('EMAIL_ENABLED', False)
        if not email_enabled:
            return

        email_sender = import_from_settings('EMAIL_SENDER')
        email_signature = import_from_settings('EMAIL_SIGNATURE')
        support_email = import_from_settings('CENTER_HELP_EMAIL')

        template_context = {
            'removed_user_first_name': self._removed_user.first_name,
            'removed_user_last_name': self._removed_user.last_name,
            'requester_first_name': self._request_obj.requester.first_name,
            'requester_last_name': self._request_obj.requester.last_name,
            'project_name': self._project.name,
            'signature': email_signature,
            'support_email': support_email,
        }

        unique_users_to_email = set()
        for project_user in self._project.managers_and_pis_to_email():
            unique_users_to_email.add(project_user.user)
        unique_users_to_email.add(self._removed_user)

        num_failures = []
        for user in unique_users_to_email:
            template_context['user_first_name'] = user.first_name
            template_context['user_last_name'] = user.last_name
            try:
                send_email_template(
                    'Project Removal Request Completed',
                    'email/project_removal/project_removal_complete.txt',
                    template_context,
                    email_sender,
                    [user.email])
            except Exception as e:
                message = (
                    f'Failed to send a notification email to {user.email}. '
                    f'Details: \n{e}')
                logger.exception(message)
                num_failures += 1
        return num_failures == 0

    def _send_emails_safe(self):
        """Send emails.

        Catch all exceptions to prevent rolling back any
        enclosing transaction.

        If send failures occur, store a warning message.
        """
        try:
            num_failures = self._send_emails()
        except Exception as e:
            message = (
                f'Encountered unexpected exception when sending notification '
                f'emails. Details: \n{e}')
            logger.exception(message)
        else:
            if num_failures > 0:
                message = f'Failed to send {num_failures} notification emails.'
                self._warning_messages.append(message)


class ProjectRemovalRequestUpdateRunner(object):
    """An object that performs necessary database changes when a new
    project request is approved."""

    def __init__(self, request_obj):
        self.request_obj = request_obj
        self.removed_user = request_obj.project_user.user
        self.project = request_obj.project_user.project
        # A list of messages to display to the user.
        self.error_messages = []
        self.success_messages = []

    def update_request(self, status):
        project_removal_status_choice, _ = \
            ProjectUserRemovalRequestStatusChoice.objects.get_or_create(
                name=status)
        self.request_obj.status = project_removal_status_choice
        self.request_obj.save()

    def complete_request(self, completion_time):
        try:
            self.request_obj.completion_time = completion_time
            self.request_obj.save()

            project_user_status_removed, _ = \
                ProjectUserStatusChoice.objects.get_or_create(
                    name='Removed')
            self.request_obj.project_user.status = project_user_status_removed
            self.request_obj.project_user.save()
        except Exception as e:
            message = f'Unexpected error setting fields for project removal ' \
                      f'request {self.request_obj.pk}.'
            self.error_messages.append(message)

        try:
            allocation_obj = Allocation.objects.get(project=self.project)
            allocation_user = \
                allocation_obj.allocationuser_set.get(user=self.removed_user)
            allocation_user_status_choice_removed = \
                AllocationUserStatusChoice.objects.get(name='Removed')
            allocation_user.status = allocation_user_status_choice_removed
            allocation_user.save()

            cluster_account_status = \
                allocation_user.allocationuserattribute_set.get(
                    allocation_attribute_type=AllocationAttributeType.objects.get(
                        name='Cluster Account Status'))
            cluster_account_status.value = 'Denied'
            cluster_account_status.save()

        except Exception as e:
            message = f'Unexpected error setting AllocationAttributeType' \
                      f'Cluster Account Status to "Denied" and ' \
                      f'AllocationUserStatusChoice to "Removed" ' \
                      f'for user {self.removed_user.username}.'
            self.error_messages.append(message)

        message = (
            f'Project removal request initiated by '
            f'{self.request_obj.requester.username} for User '
            f'{self.removed_user.username} under '
            f'Project {self.project.name} '
            f'has been marked as Completed.')
        self.success_messages.append(message)

        return self.request_obj

    def get_messages(self):
        """A getter for this instance's user_messages."""
        return self.success_messages, self.error_messages

    def send_emails(self):
        email_enabled = import_from_settings('EMAIL_ENABLED', False)

        if email_enabled:
            email_sender = import_from_settings('EMAIL_SENDER')
            email_signature = import_from_settings('EMAIL_SIGNATURE')
            support_email = import_from_settings('CENTER_HELP_EMAIL')

            for user in list(chain(self.project.pis(),
                                   self.project.managers(),
                                   [self.request_obj.project_user.user])):
                template_context = {
                    'user_first_name': user.first_name,
                    'user_last_name': user.last_name,
                    'removed_user_first_name': self.removed_user.first_name,
                    'removed_user_last_name': self.removed_user.last_name,
                    'requester_first_name': self.request_obj.requester.first_name,
                    'requester_last_name': self.request_obj.requester.last_name,
                    'project_name': self.project.name,
                    'signature': email_signature,
                    'support_email': support_email,
                }

                send_email_template(
                    'Project Removal Request Completed',
                    'email/project_removal/project_removal_complete.txt',
                    template_context,
                    email_sender,
                    [user.email]
                )
