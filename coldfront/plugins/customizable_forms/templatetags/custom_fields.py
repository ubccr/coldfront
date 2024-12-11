from django import template
from django.conf import settings
from django.forms import BoundField
from django.template.loader import get_template

register = template.Library()


class CustomFieldError(Exception):
    pass


@register.filter(name="custom_field")
def custom_field(field):
    if not isinstance(field, BoundField):
        if settings.DEBUG:
            raise CustomFieldError('This must be a BoundField')
        return ''
    
    custom_templates = {
        'optionalchoice': 'customizable_forms/fields/optional_choice_template.html'
    }

    custom_template = custom_templates.get(field.widget_type)
    if not custom_template:
        if settings.DEBUG:
            raise CustomFieldError('No match for this field')
        return ''

    template = get_template(custom_template)
    return template.render({"field": field})
