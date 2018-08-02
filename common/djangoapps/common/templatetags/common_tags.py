from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()


# settings value
@register.simple_tag
def settings_value(name):
    allowed_names = [
        'LOGIN_FAIL_MESSAGE',
        'ACCOUNT_CREATION_TEXT',
    ]
    return mark_safe(getattr(settings, name, '') if name in allowed_names else '')

@register.filter
def get_icon(expand_accordion):
    print(expand_accordion)
    if expand_accordion == 'show':
        return 'fa-minus'
    else:
        return 'fa-plus'
