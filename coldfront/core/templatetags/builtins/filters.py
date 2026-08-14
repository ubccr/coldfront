# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import datetime
import json
import re

import humanize
from django import template
from django.conf import settings
from django.contrib.humanize.templatetags.humanize import naturaltime
from django.core.serializers.json import DjangoJSONEncoder
from django.urls import NoReverseMatch, reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe
from django.utils.timezone import localtime
from markdown import markdown
from markdown.extensions.tables import TableExtension

from coldfront.utils.html import clean_html, foreground_color
from coldfront.utils.strings import title
from coldfront.views import get_viewname

register = template.Library()


@register.filter()
def as_range(n):
    """
    Return a range of n items.
    """
    try:
        int(n)
    except TypeError:
        return list()
    return range(n)


@register.filter()
def placeholder(value):
    """
    Render a muted placeholder if the value equates to False.
    """
    if value not in ("", None):
        return value

    return mark_safe('<span class="text-muted">&mdash;</span>')


@register.filter()
def meta(model, attr):
    """
    Return the specified Meta attribute of a model. This is needed because Django does not permit templates
    to access attributes which begin with an underscore (e.g. _meta).

    Args:
        model: A Django model class or instance
        attr: The attribute name
    """
    return getattr(model._meta, attr, "")


@register.filter()
def linkify(instance, attr=None):
    """
    Render a hyperlink for an object with a `get_absolute_url()` method, optionally specifying the name of an
    attribute to use for the link text. If no attribute is given, the object's string representation will be
    used.

    If the object has no `get_absolute_url()` method, return the text without a hyperlink element.
    """
    if instance is None:
        return ""

    text = getattr(instance, attr) if attr is not None else str(instance)
    try:
        url = instance.get_absolute_url()
        return mark_safe(f'<a href="{url}">{escape(text)}</a>')
    except (AttributeError, TypeError):
        return escape(text)


@register.filter()
def fgcolor(value, dark="000000", light="ffffff"):
    """
    Return black (#000000) or white (#ffffff) given an arbitrary background color in RRGGBB format. The foreground
    color with the better contrast is returned.

    Args:
        value: The background color
        dark: The foreground color to use for light backgrounds
        light: The foreground color to use for dark backgrounds
    """
    value = value.lower().strip("#")
    if not re.match("^[0-9a-f]{6}$", value):
        return ""
    return f"#{foreground_color(value, dark, light)}"


@register.filter()
def isodate(value):
    if type(value) is datetime.date:
        text = value.isoformat()
        # ``naturaltime`` requires a datetime (it calls ``utcoffset()``), so a
        # bare ``date`` must be combined with a time before formatting.
        natural = naturaltime(datetime.datetime.combine(value, datetime.time.min))
        return mark_safe(f'<span title="{natural}">{text}</span>')
    elif type(value) is datetime.datetime:
        local_value = localtime(value) if value.tzinfo else value
        text = local_value.date().isoformat()
        return mark_safe(f'<span title="{naturaltime(value)}">{text}</span>')
    else:
        return ""


@register.filter()
def isotime(value, spec="seconds"):
    if type(value) is datetime.time:
        return value.isoformat(timespec=spec)
    if type(value) is datetime.datetime:
        local_value = localtime(value) if value.tzinfo else value
        return local_value.time().isoformat(timespec=spec)
    return ""


@register.filter()
def isodatetime(value, spec="seconds"):
    if type(value) is datetime.datetime:
        text = f"{isodate(value)} {isotime(value, spec=spec)}"
    else:
        return ""
    return mark_safe(f'<span title="{naturaltime(value)}">{text}</span>')


@register.filter("json")
def render_json(value):
    """
    Render a dictionary as formatted JSON. This filter is invoked as "json":

        {{ data_dict|json }}
    """
    return json.dumps(value, ensure_ascii=False, indent=4, sort_keys=True, cls=DjangoJSONEncoder)


@register.filter(name="split")
def split(string, sep):
    """Return the string split by sep."""
    return string.split(sep)


@register.filter("markdown", is_safe=True)
def render_markdown(value):
    """
    Render a string as Markdown. This filter is invoked as "markdown":

        {{ md_source_text|markdown }}
    """
    if not value:
        return ""

    # Render Markdown
    html = markdown(
        value,
        extensions=[
            "def_list",
            "fenced_code",
            TableExtension(use_align_attribute=True),
        ],
    )

    # If the string is not empty wrap it in rendered-markdown to style tables
    if html:
        html = f'<div class="rendered-markdown">{html}</div>'

    schemes = settings.ALLOWED_URL_SCHEMES

    # Sanitize HTML
    html = clean_html(html, schemes)

    return mark_safe(html)


@register.filter()
def bettertitle(value):
    """
    Alternative to the builtin title(). Ensures that the first letter of each word is uppercase but retains the
    original case of all others.
    """
    return title(value)


@register.filter()
def getfield(form, fieldname):
    """
    Return the specified bound field of a Form.
    """
    try:
        return form[fieldname]
    except KeyError:
        return None


@register.filter()
def validated_viewname(model, action):
    """
    Return the view name for the given model and action if valid, or None if invalid.
    """
    viewname = get_viewname(model, action)

    # Validate the view name
    try:
        reverse(viewname)
        return viewname
    except NoReverseMatch:
        return None


@register.filter(name="widget_type")
def widget_type(field):
    """
    Return the widget type
    """
    if hasattr(field, "widget"):
        return field.widget.__class__.__name__.lower()
    if hasattr(field, "field"):
        return field.field.widget.__class__.__name__.lower()
    return None


@register.filter()
def dict_get(dictionary, key):
    """
    Get a value from a dictionary by key.
    """
    return dictionary.get(key)


@register.filter()
def add_days(value, days):
    """
    Add the given number of days to a date or datetime and return the result.
    Days must be coercible to int.
    """
    from datetime import timedelta

    try:
        n = int(days)
    except (ValueError, TypeError):
        return value

    if value is None:
        return value

    try:
        return value + timedelta(days=n)
    except TypeError:
        return value


@register.filter()
def naturalsize(value):
    """
    Return human readable bytes
    """
    if value not in ("", None):
        return humanize.naturalsize(value)

    return placeholder(value)


@register.filter
def status_from_tag(tag: str = "info") -> str:
    """
    Determine Bootstrap theme status/level from Django's Message.level_tag.
    """
    status_map = {
        "warning": "warning",
        "success": "success",
        "error": "danger",
        "danger": "danger",
        "debug": "info",
        "info": "info",
    }
    return status_map.get(tag.lower(), "info")


@register.filter
def icon_from_status(status: str = "info") -> str:
    """
    Determine icon class name from Bootstrap theme status/level.
    """
    icon_map = {
        "warning": "fa-solid fa-circle-exclamation",
        "success": "fa-solid fa-check-circle",
        "info": "fa-solid fa-circle-info",
        "danger": "fa-solid fa-circle-exclamation",
    }
    return icon_map.get(status.lower(), "information")
