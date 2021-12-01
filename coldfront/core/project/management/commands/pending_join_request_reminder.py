from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template
from coldfront.core.project.models import ProjectUserJoinRequest
from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse
from urllib.parse import urljoin
import logging

from coldfront.core.utils.common import utc_now_offset_aware
from datetime import datetime
from datetime import timedelta

"""An admin command that sends PIs reminder emails of pending join requests."""

TIME_DELTA = timedelta(days=4)

class Command(BaseCommand):

    help = (
        'Send PIs reminder emails of pending join requests.')
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):

        proj_join_requests_qeuryset = ProjectUserJoinRequest.objects.filter(project_user__status__name='Pending - Add')

        emails_sent = 0
        for request in proj_join_requests_qeuryset:
            creation_time = request.created
            now = utc_now_offset_aware()
            diff = now - creation_time

            if diff > TIME_DELTA and settings.EMAIL_ENABLED:
                subject = 'Pending Project Join Requests'
                template_names = ['email/pending_project_join_requests.txt',
                                  'email/pending_project_join_request_user.txt']
                context = {
                    'project_name': request.project_user.project.name,
                    'user_first_name': request.project_user.user.first_name,
                    'user_last_name': request.project_user.user.last_name,
                    'user_email': request.project_user.user.email,
                    'signature': settings.EMAIL_SIGNATURE
                }
                sender = settings.EMAIL_SENDER
                manager_pi_set = request.project_user.project.projectuser_set.filter(
                    role__name__in=['Manager', 'Principal Investigator'],
                    status__name='Active')
                receiver_list = [[proj_user.user.email for proj_user in manager_pi_set],
                                 [request.project_user.user.email]]
                try:
                    for template, recipients in zip(template_names, receiver_list):
                        send_email_template(
                            subject, template, context, sender, recipients)
                        emails_sent += len(recipients)
                except Exception as e:
                    message = 'Failed to send reminder email. Details:'
                    self.stderr.write(self.style.ERROR(message))
                    self.stderr.write(self.style.ERROR(str(e)))
                    self.logger.error(message)
                    self.logger.exception(e)

        self.stdout.write(self.style.SUCCESS(f'Sent {str(emails_sent)} '
                                             f'reminder emails.'))