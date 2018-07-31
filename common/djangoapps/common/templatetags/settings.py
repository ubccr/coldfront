from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


# settings value
@register.simple_tag
def settings_value(name):
    allowed_names = [
        'IMPORT_BIBTEX_INITIAL_TEXT_PRIMARY',
        'IMPORT_BIBTEX_INITIAL_TEXT_SECONDARY',
        'IMPORT_BIBTEX_INITIAL_HELP_URL',
        'DELETE_USER_EXTRA_NOTE',
        'LOGIN_FAIL_MESSAGE',
        'LOGIN_USERNAME_LABEL',
        'LOGIN_USERNAME_PASSWORD',
        'ACCOUNT_CREATION_TEXT',
        'SUBSCRIPTION_TEXT',
    ]
    return mark_safe(getattr(settings, name, '') if name in allowed_names else '')
