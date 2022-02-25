from django.contrib.auth.models import User

from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template
from coldfront.core.project.models import ProjectUserJoinRequest, Project
from coldfront.core.project.utils import project_join_list_url
from coldfront.core.project.utils import review_project_join_requests_url
from django.conf import settings
from django.core.management.base import BaseCommand
from django.urls import reverse
from urllib.parse import urljoin
import logging
from django.db.models import Q
from django.core.mail import send_mail
from django.template.loader import render_to_string

"""An admin command that sends PIs reminder emails of pending join requests."""

class Command(BaseCommand):

    help = (
        'Send PIs reminder emails of pending join requests.')
    logger = logging.getLogger(__name__)

    def handle(self, *args, **options):

        proj_join_requests_queryset = \
            ProjectUserJoinRequest.objects.filter(
                project_user__status__name='Pending - Add')

        projects_with_pending_join_requests = proj_join_requests_queryset.values_list(
            'project_user__project', flat=True).distinct()

        users_with_pending_join_requests = proj_join_requests_queryset.values_list(
            'project_user__user', flat=True).distinct()

        emails_sent = 0
        for pk in projects_with_pending_join_requests:
            project = Project.objects.get(pk=pk)
            proj_join_requests_qeuryset = \
                ProjectUserJoinRequest.objects.filter(
                    project_user__project=project,
                    project_user__status__name='Pending - Add').\
                    order_by('project_user', '-created').\
                    distinct('project_user')

            if settings.EMAIL_ENABLED:
                request_string_list = [f'{request.project_user.user.first_name} ' \
                                       f'{request.project_user.user.last_name} | ' \
                                       f'{request.project_user.user.email} | ' \
                                       f'{request.created.strftime("%m/%d/%Y, %H:%M")}'
                                       for request in proj_join_requests_qeuryset]

                context = {
                    'project_name': project.name,
                    'request_list': '\n'.join(request_string_list),
                    'num_requests': proj_join_requests_qeuryset.count(),
                    'verb': 'are' if proj_join_requests_qeuryset.count() > 1 else 'is',
                    'pk': project.pk,
                    'review_url': review_project_join_requests_url(project),
                    'signature': settings.EMAIL_SIGNATURE,
                }

                recipients = project.managers_and_pis_emails()
                try:
                    msg_plain = \
                        render_to_string('email/project_join_request/pending_project_join_requests.txt',
                                         context)
                    msg_html = \
                        render_to_string('email/project_join_request/pending_project_join_requests.html',
                                         context)

                    send_mail(
                        'Pending Project Join Requests',
                        msg_plain,
                        settings.EMAIL_SENDER,
                        recipients,
                        html_message=msg_html,
                    )
                    emails_sent += len(recipients)
                except Exception as e:
                    message = 'Failed to send reminder email. Details:'
                    self.stderr.write(self.style.ERROR(message))
                    self.stderr.write(self.style.ERROR(str(e)))
                    self.logger.error(message)
                    self.logger.exception(e)

        for pk in users_with_pending_join_requests:
            user = User.objects.get(pk=pk)
            proj_join_requests_qeuryset = \
                ProjectUserJoinRequest.objects.filter(
                    project_user__user=user,
                    project_user__status__name='Pending - Add'). \
                    order_by('project_user', '-created'). \
                    distinct('project_user')

            if settings.EMAIL_ENABLED:
                request_string_list = [f'{request.project_user.project.name} | ' \
                                       f'{request.created.strftime("%m/%d/%Y, %H:%M")}'
                                       for request in proj_join_requests_qeuryset]

                context = {
                    'user_name': f'{user.first_name} {user.last_name}',
                    'request_list': '\n'.join(request_string_list),
                    'num_requests': proj_join_requests_qeuryset.count(),
                    'review_url': project_join_list_url(),
                    'signature': settings.EMAIL_SIGNATURE,
                }

                try:
                    send_email_template(
                        'Pending Project Join Requests',
                        'email/project_join_request/pending_project_join_request_user.txt',
                        context,
                        settings.EMAIL_SENDER,
                        [user.email])
                    emails_sent += 1
                except Exception as e:
                    message = 'Failed to send reminder email. Details:'
                    self.stderr.write(self.style.ERROR(message))
                    self.stderr.write(self.style.ERROR(str(e)))
                    self.logger.error(message)
                    self.logger.exception(e)

        self.stdout.write(self.style.SUCCESS(f'Sent {str(emails_sent)} '
                                             f'reminder emails.'))
