import logging
from smtplib import SMTPException

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from coldfront.core.utils.common import import_from_settings

logger = logging.getLogger(__name__)
EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
if EMAIL_ENABLED:
    EMAIL_SUBJECT_PREFIX = import_from_settings('EMAIL_SUBJECT_PREFIX')
    EMAIL_DEVELOPMENT_EMAIL_LIST = import_from_settings(
        'EMAIL_DEVELOPMENT_EMAIL_LIST')


def send_email(subject, body, sender, receiver_list, cc=[], html_body=''):
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
        email = EmailMultiAlternatives(
            subject,
            body,
            sender,
            receiver_list,
            cc=cc)
        if html_body:
            email.attach_alternative(html_body, "text/html")
        email.send(fail_silently=False)

    except SMTPException as e:
        logger.error('Failed to send email to %s from %s with subject %s',
                     sender, ','.join(receiver_list), subject)


def send_email_template(subject, template_name, context, sender,
                        receiver_list, cc=[], html_template=None):
    """Helper function for sending emails from a template

    It is the responsibility of the caller to avoid duplicates between the
    receiver_list and cc list.
    """
    plain_body = render_to_string(template_name, context)

    html_body = None
    if html_template:
        html_body = render_to_string(html_template, context)

    return send_email(subject,
                      plain_body,
                      sender,
                      receiver_list,
                      cc=cc,
                      html_body=html_body)


def dummy_email_address():
    """Return the first email address in the setting
    EMAIL_DEVELOPMENT_EMAIL_LIST. Raise an exception if it is empty."""
    dev_email_list = settings.EMAIL_DEVELOPMENT_EMAIL_LIST
    if not dev_email_list:
        raise ImproperlyConfigured(
            'There should be at least one address in '
            'EMAIL_DEVELOPMENT_EMAIL_LIST.')
    return dev_email_list[0]
