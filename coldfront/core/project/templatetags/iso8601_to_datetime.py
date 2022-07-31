from datetime import datetime
from django import template
from django.template.defaultfilters import stringfilter
import iso8601


register = template.Library()


@register.filter
@stringfilter
def iso8601_to_datetime(s):
    # TODO: Upgrade to Python 3.7+ to use this.
    # return datetime.fromisoformat(s)
    if s == '':
        return None
    return iso8601.parse_date(s)
