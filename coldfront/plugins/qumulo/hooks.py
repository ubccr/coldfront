from django.template.loader import render_to_string

from coldfront.config.env import ENV
from coldfront.core.utils.mail import (
    EMAIL_ENABLED,
    EMAIL_SENDER,
    email_template_context,
    send_acl_reset_email,
)


def acl_reset_complete_hook(task_object):
    if EMAIL_ENABLED:
        send_acl_reset_email(task_object)
