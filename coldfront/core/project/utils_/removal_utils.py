from coldfront.core.project.models import (ProjectUserRemovalRequestStatusChoice,
                                           ProjectUserRemovalRequest,
                                           ProjectUserStatusChoice)
from coldfront.core.utils.mail import send_email_template
from coldfront.core.utils.common import import_from_settings


class ProjectRemovalRequestRunner(object):
    """An object that performs necessary database changes when a new
    project request is approved and processed."""

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

            manager_pi_queryset = [x.user for x in self.proj_obj.projectuser_set.filter(
                role__name__in=['Manager', 'Principal Investigator'],
                status__name='Active').exclude(user=self.requester_obj)]

            # send emails to user and all pis/managers that did not make request
            for user in manager_pi_queryset + [self.user_obj] \
                    if self.user_obj != self.requester_obj else manager_pi_queryset:
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
                    [user.email]
                )

            # send email to admins
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
                email_admin_list
            )