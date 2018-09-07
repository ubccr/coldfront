import logging
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from smtplib import  SMTPException

from common.djangolibs.utils import import_from_settings

logger = logging.getLogger(__name__)
EMAIL_SUBJECT_PREFIX = import_from_settings('EMAIL_SUBJECT_PREFIX')
EMAIL_DEVELOPMENT_EMAIL_LIST = import_from_settings('EMAIL_DEVELOPMENT_EMAIL_LIST')

def send_email(subject, template_name, context, sender, receiver_list):
    """Helper function for sending emails.
    """

    if len(receiver_list) == 0:
        logger.error('Failed to send email missing receiver_list')
        return

    if len(sender) == 0:
        logger.error('Failed to send email missing sender address')
        return

    email_body = render_to_string(template_name, context)
    email_receiver_list = receiver_list
    email_subject = subject
    if len(EMAIL_SUBJECT_PREFIX) > 0:
        email_subject = EMAIL_SUBJECT_PREFIX + ' ' + subject

    if settings.DEBUG:
        email_receiver_list = EMAIL_DEVELOPMENT_EMAIL_LIST

    try:
        send_mail(email_subject, email_body, sender, email_receiver_list, fail_silently=False)
    except SMTPException as e:
        logger.error('Failed to send email to %s from %s with subject %s', sender, ','.join(receiver_list), email_subject)
