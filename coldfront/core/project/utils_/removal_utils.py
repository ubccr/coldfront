from itertools import chain

from coldfront.core.allocation.models import Allocation, \
    AllocationUserStatusChoice, AllocationAttributeType
from coldfront.core.project.models import (ProjectUserRemovalRequestStatusChoice,
                                           ProjectUserRemovalRequest,
                                           ProjectUserStatusChoice)
from coldfront.core.utils.mail import send_email_template
from coldfront.core.utils.common import import_from_settings, \
    utc_now_offset_aware
from django.db.models import Q


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
