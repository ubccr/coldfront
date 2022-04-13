import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import EmailMessage, send_mail
from django.template.loader import render_to_string

from coldfront.core.utils.common import import_from_settings

logger = logging.getLogger(__name__)
EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
if EMAIL_ENABLED:
    EMAIL_SUBJECT_PREFIX = import_from_settings('EMAIL_SUBJECT_PREFIX')
    EMAIL_DEVELOPMENT_EMAIL_LIST = import_from_settings(
        'EMAIL_DEVELOPMENT_EMAIL_LIST')
    EMAIL_GROUP_TO_EMAIL_MAPPING = import_from_settings('EMAIL_GROUP_TO_EMAIL_MAPPING')
    EMAIL_TICKET_SYSTEM_ADDRESS = import_from_settings('EMAIL_TICKET_SYSTEM_ADDRESS')


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


def send_email_template(subject, template_name, context, sender, receiver_list):
    """Helper function for sending emails from a template
    """
    body = render_to_string(template_name, context)

    return send_email(subject, body, sender, receiver_list)


def get_email_recipient_from_groups(groups):
    """
    Returns a group's email if it exists in EMAIL_GROUP_TO_EMAIL_MAPPING. Only returns the first
    email it finds, if no email is found then EMAIL_TICKET_SYSTEM_ADDRESS is returned.

    :params groups: List/QuerySet of Groups
    :return: Email address for a group if found, else EMAIL_TICKET_SYSTEM_ADDRESS
    """
    for group in groups:
        email = EMAIL_GROUP_TO_EMAIL_MAPPING.get(group.name)
        if email is not None:
            return email

    return EMAIL_TICKET_SYSTEM_ADDRESS
