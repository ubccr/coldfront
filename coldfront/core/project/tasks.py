import datetime
import logging

from coldfront.core.project.models import (Project, ProjectStatusChoice)
from coldfront.core.utils. common import import_from_settings
from coldfront.core.utils.mail import send_email_template

logger = logging.getLogger(__name__)

CENTER_NAME = import_from_settings("CENTER_NAME")
CENTER_BASE_URL = import_from_settings("CENTER_BASE_URL")
CENTER_PROJECT_RENEWAL_HELP_URL = import_from_settings(
    'CENTER_PROJECT_RENEWAL_HELP_URL'
)
EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED')

if EMAIL_ENABLED:
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
    EMAIL_OPT_OUT_INSTRUCTION_URL = import_from_settings(
        'EMAIL_OPT_OUT_INSTRUCTION_URL')
    EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
    EMAIL_PROJECT_EXPIRING_NOTIFICATION_DAYS = import_from_settings(
        'EMAIL_PROJECT_EXPIRING_NOTIFICATION_DAYS', [7, ])
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings('EMAIL_TICKET_SYSTEM_ADDRESS')


def update_statuses():
    expired_status_choice = ProjectStatusChoice.objects.get(name='Expired')
    projects_to_expire = Project.objects.filter(
        status__name='Active', end_date__lt=datetime.datetime.now().date()
    )
    for project in projects_to_expire:
        project.status = expired_status_choice
        project.save()

    logger.info('Projects set to expired: {}'. format(projects_to_expire.count()))


def send_expiry_emails():
    if EMAIL_ENABLED:
        # Projects expiring
        for days_remaining in sorted(set(EMAIL_PROJECT_EXPIRING_NOTIFICATION_DAYS)):
            expiring_in_days = datetime.datetime.today() + datetime.timedelta(days=days_remaining)

            for project_obj in Project.objects.filter(status__name='Active', end_date=expiring_in_days):
                project_review_url = '{}/{}/{}/{}'.format(
                    CENTER_BASE_URL.strip('/'), 'project', project_obj.pk, 'review'
                )

                template_context = {
                    'center_name': CENTER_NAME,
                    'project_title': project_obj.title,
                    'expiring_in_days': days_remaining,
                    'project_review_url': project_review_url,
                    'project_renewal_help_url': CENTER_PROJECT_RENEWAL_HELP_URL,
                    'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
                    'signature': EMAIL_SIGNATURE
                }

                email_receiver_list = []
                for project_user in project_obj.projectuser_set.exclude(status__name__in=['Removed', 'Denied']):
                    if project_obj.projectuser_set.get(user=project_user.user).enable_notifications:
                        email_receiver_list.append(project_user.user.email)

                send_email_template(
                    'Project {} Expiring In {} Days'.format(project_obj.title, days_remaining),
                    'email/project_expiring.txt',
                    template_context,
                    EMAIL_TICKET_SYSTEM_ADDRESS,
                    email_receiver_list
                )

                logger.info('Project {} expiring in {} days email sent to PI {}'.format(
                    project_obj.title, days_remaining, project_obj.pi.username
                ))

        # Projects expiring today
        today = datetime.datetime.today()
        for project_obj in Project.objects.filter(end_date=today):
            project_review_url = '{}/{}/{}/{}'.format(
                CENTER_BASE_URL.strip('/'), 'project', project_obj.pk, 'review'
            )

            template_context = {
                'center_name': CENTER_NAME,
                'project_title': project_obj.title,
                'project_renewal_help_url': CENTER_PROJECT_RENEWAL_HELP_URL,
                'project_review_url': project_review_url,
                'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
                'signature': EMAIL_SIGNATURE
            }

            email_receiver_list = []
            for project_user in project_obj.projectuser_set.exclude(status__name__in=['Removed', 'Denied']):
                if project_obj.projectuser_set.get(user=project_user.user).enable_notifications:
                    email_receiver_list.append(project_user.user.email)

            send_email_template(
                'Project {} Expires Today'.format(project_obj.title),
                'email/project_expires_today.txt',
                template_context,
                EMAIL_TICKET_SYSTEM_ADDRESS,
                email_receiver_list
            )

            logger.info('Project {} expires today email sent to PI {}'.format(
                project_obj.title, project_obj.pi.username
            ))
