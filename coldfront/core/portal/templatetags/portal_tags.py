from django import template
from django.conf import settings

register = template.Library()


@register.simple_tag
def get_version():
    return settings.VERSION


@register.simple_tag
def get_setting(name):
    return getattr(settings, name, "")
