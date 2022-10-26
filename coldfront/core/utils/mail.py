import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string
from django.urls import reverse

from coldfront.core.utils.common import import_from_settings

logger = logging.getLogger(__name__)
EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
EMAIL_ADDED_PROJECT_USERS = import_from_settings('EMAIL_ADDED_PROJECT_USERS', False)
EMAIL_SUBJECT_PREFIX = import_from_settings('EMAIL_SUBJECT_PREFIX')
EMAIL_DEVELOPMENT_EMAIL_LIST = import_from_settings('EMAIL_DEVELOPMENT_EMAIL_LIST')
EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings('EMAIL_TICKET_SYSTEM_ADDRESS')
EMAIL_OPT_OUT_INSTRUCTION_URL = import_from_settings('EMAIL_OPT_OUT_INSTRUCTION_URL')
EMAIL_SIGNATURE = import_from_settings('EMAIL_SIGNATURE')
EMAIL_CENTER_NAME = import_from_settings('CENTER_NAME')
CENTER_BASE_URL = import_from_settings('CENTER_BASE_URL')

def send_email(subject, body, sender, receiver_list, cc=[]):
    """Helper function for sending emails
    """

    if not EMAIL_ENABLED:
        return

    if len(receiver_list) == 0:
        logger.error('Failed to send email missing receiver_list')
        return

    if len(sender) == 0:
        logger.error('Failed to send email missing sender address')
        return

    if len(EMAIL_SUBJECT_PREFIX) > 0:
        subject = EMAIL_SUBJECT_PREFIX + ' ' + subject

    if settings.DEBUG:
        receiver_list = EMAIL_DEVELOPMENT_EMAIL_LIST

    if cc and settings.DEBUG:
        cc = EMAIL_DEVELOPMENT_EMAIL_LIST

    try:
        if cc:
            email = EmailMessage(
                subject,
                body,
                sender,
                receiver_list,
                cc=cc)
            email.send(fail_silently=False)
        else:
            send_mail(subject, body, sender,
                      receiver_list, fail_silently=False)
    except SMTPException as e:
        logger.error('Failed to send email to %s from %s with subject %s',
                     sender, ','.join(receiver_list), subject)


def send_email_template(subject, template_name, template_context, sender, receiver_list):
    """Helper function for sending emails from a template
    """
    if not EMAIL_ENABLED:
        return

    body = render_to_string(template_name, template_context)

    return send_email(subject, body, sender, receiver_list)

def email_template_context():
    """Basic email template context used as base for all templates
    """
    return {
        'center_name': EMAIL_CENTER_NAME,
        'signature': EMAIL_SIGNATURE,
        'opt_out_instruction_url': EMAIL_OPT_OUT_INSTRUCTION_URL
    }

def build_link(url_path, domain_url=''):
    if not domain_url:
        domain_url = CENTER_BASE_URL
    return f'{domain_url}{url_path}'

def send_admin_email_template(subject, template_name, template_context):
    """Helper function for sending admin emails using a template
    """
    send_email_template(subject, template_name, template_context, EMAIL_SENDER, [EMAIL_TICKET_SYSTEM_ADDRESS, ])

def send_allocation_admin_email(allocation_obj, subject, template_name, url_path='', domain_url=''):
    """Send allocation admin emails
    """
    if not url_path:
        url_path = reverse('allocation-request-list')

    url = build_link(url_path, domain_url=domain_url)
    pi_name = f'{allocation_obj.project.pi.first_name} {allocation_obj.project.pi.last_name} ({allocation_obj.project.pi.username})'
    resource_name = allocation_obj.get_parent_resource

    ctx = email_template_context()
    ctx['pi'] = pi_name
    ctx['resource'] = resource_name
    ctx['url'] = url

    send_admin_email_template(
        f'{subject}: {pi_name} - {resource_name}',
        template_name,
        ctx,
    )

def send_allocation_customer_email(allocation_obj, subject, template_name, url_path='', domain_url=''):
    """Send allocation customer emails
    """
    if not url_path:
        url_path = reverse('allocation-detail', kwargs={'pk': allocation_obj.pk})

    url = build_link(url_path, domain_url=domain_url)
    ctx = email_template_context()
    ctx['resource'] = allocation_obj.get_parent_resource
    ctx['url'] = url

    allocation_users = allocation_obj.allocationuser_set.exclude(status__name__in=['Removed', 'Error'])
    email_receiver_list = []
    for allocation_user in allocation_users:
        if allocation_user.allocation.project.projectuser_set.get(
                                user=allocation_user.user).enable_notifications:
            email_receiver_list.append(allocation_user.user.email)

    send_email_template(
        subject,
        template_name,
        ctx,
        EMAIL_SENDER,
        email_receiver_list
    )

def send_project_user_email(project_obj, subject, template_name, receiver, url_path='', domain_url=''):
    """Send project user email when added to project, can expand to more uses
    """
    if EMAIL_ADDED_PROJECT_USERS:
        if not url_path:
            url_path = reverse('project-detail', kwargs={'pk': project_obj.pk})
        
        url = build_link(url_path, domain_url)
        ctx = email_template_context()
        ctx['project'] = project_obj
        ctx['project_url'] = url

        send_email_template(
            subject,
            template_name,
            ctx,
            EMAIL_SENDER,
            receiver
        )
