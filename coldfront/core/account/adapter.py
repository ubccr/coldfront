from allauth.account.adapter import DefaultAccountAdapter

from django.conf import settings

from coldfront.core.utils.mail import dummy_email_address


class AccountAdapter(DefaultAccountAdapter):
    """An adapter that adjusts handling for emails."""

    def send_mail(self, template_prefix, email, context):
        """Only send an email if email is enabled. Replace the target
        email with a fake value if DEBUG is True."""
        if not settings.EMAIL_ENABLED:
            return
        if settings.DEBUG:
            email = dummy_email_address()
        super().send_mail(template_prefix, email, context)
