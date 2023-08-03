from coldfront.core.utils.mail import send_email
from coldfront.core.utils.common import import_from_settings

from django.utils.log import AdminEmailHandler

EMAIL_ENABLED = import_from_settings('EMAIL_ENABLED', False)
if EMAIL_ENABLED:
    EMAIL_SENDER = import_from_settings('EMAIL_SENDER')
    EMAIL_ADMIN_LIST = import_from_settings('EMAIL_ADMIN_LIST')


class CustomAdminEmailHandler(AdminEmailHandler):

    def send_mail(self, subject, message, *args, **kwargs):
        if not EMAIL_ENABLED:
            return

        last_index = message.find('\n')
        for _ in range(4):
            last_index = message.find('\n', last_index + 1)

        short_message = message[:last_index]
        if 'Service Unavailable' in short_message or 'Invalid HTTP_HOST header' in short_message:
            return

        message = "An error has occured on RT Projects. Please check the log file for more details."
        if '1045' in short_message:
            message = "Database access error has occurred. Please check the log file for more details."

        subject = 'An error occurred on RT Projects'
        send_email(subject, message, EMAIL_SENDER, EMAIL_ADMIN_LIST)
