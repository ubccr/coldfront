from django import template

register = template.Library()


@register.filter()
def field_name_to_label(value):
    value = value.replace("_", " ")
    return value.title()
