import datetime
import logging

from coldfront.core.project.models import (Project, ProjectStatusChoice)
from coldfront.core.project.utils import get_project_user_emails, check_if_pi_eligible
from coldfront.core.utils.common import import_from_settings
from coldfront.core.utils.mail import send_email_template
from coldfront.plugins.ldap_user_info.utils import get_users_info

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
        status__name='Active',
        end_date__lt=datetime.datetime.now().date(),
        requires_review=True
    )
    for project in projects_to_expire:
        project.status = expired_status_choice
        project.save()

    logger.info(f'Projects set to expired: {projects_to_expire.count()}')


def send_expiry_emails():
    """
    Sends an email if the project has no active allocations in it. The allocation expiry emails take
    care of the projects that have active allocations.
    """
    if EMAIL_ENABLED:
        # Projects expiring
        for days_remaining in sorted(set(EMAIL_PROJECT_EXPIRING_NOTIFICATION_DAYS)):
            expiring_in_days = datetime.datetime.today() + datetime.timedelta(days=days_remaining)

            projects_expiring_soon = Project.objects.filter(
                status__name='Active',
                end_date=expiring_in_days,
                requires_review=True,
            ).prefetch_related('allocation_set')

            for project_obj in projects_expiring_soon:
                if project_obj.allocation_set.filter(status__name='Active').exists():
                    continue

                template_context = {
                    'center_name': CENTER_NAME,
                    'project_title': project_obj.title,
                    'is_renewable': project_obj.get_env.get('is_renewable'),
                    'expiring_in_days': days_remaining,
                    'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
                    'signature': EMAIL_SIGNATURE
                }

                email_receiver_list = get_project_user_emails(project_obj)
                send_email_template(
                    'Project {} Expiring In {} Days'.format(project_obj.title, days_remaining),
                    'email/project_expiring.txt',
                    template_context,
                    EMAIL_TICKET_SYSTEM_ADDRESS,
                    email_receiver_list
                )

                logger.info(
                    f'Project with no allocations {project_obj.title} expiring in {days_remaining} '
                    f'days, email sent to project users (project pk={project_obj.pk})'
                )

        # Projects expiring today
        today = datetime.datetime.today()
        projects_expiring_today = Project.objects.filter(
            status__name='Active',
            end_date=today,
            requires_review=True
        ).prefetch_related('allocation_set')
        for project_obj in projects_expiring_today:
            if project_obj.allocation_set.filter(status__name='Active').exists():
                continue

            template_context = {
                'center_name': CENTER_NAME,
                'project_title': project_obj.title,
                'help_email': EMAIL_TICKET_SYSTEM_ADDRESS,
                'signature': EMAIL_SIGNATURE
            }

            email_receiver_list = get_project_user_emails(project_obj)
            send_email_template(
                'Project {} Expires Today'.format(project_obj.title),
                'email/project_expires_today.txt',
                template_context,
                EMAIL_TICKET_SYSTEM_ADDRESS,
                email_receiver_list
            )

            logger.info(
                f'Project with no allocations {project_obj.title} expires today, email sent to '
                f'project users (project pk={project_obj.pk})'
            )


def check_current_pi_eligibilities():
    project_pis = set(Project.objects.filter(status__name='Active').values_list('pi__username', flat=True))
    project_pi_memberships = get_users_info(project_pis, ['memberOf'])
    logger.info('Checking PI eligibilities...')
    for project_pi, memberships in project_pi_memberships.items():
        if not check_if_pi_eligible(project_pi, memberships.get('memberOf')):
            logger.warning(f'PI {project_pi} is no longer eligible to be a PI')
    logger.info('Done checking PI eligibilities')
