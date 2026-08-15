# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import json
from urllib.parse import quote

from django import template
from django.db.models import QuerySet
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import CustomFieldTypeChoices
from coldfront.core.models import ObjectType
from coldfront.core.utils import ActionURLNode
from coldfront.forms import TableConfigForm
from coldfront.users.permissions import get_permission_for_model

register = template.Library()


@register.filter
def get_bound_field(form, field_name):
    """
    Return the bound field for a given field name from a form.
    Usage: {{ form|get_bound_field:field_name }}
    """
    return form[field_name]


@register.inclusion_tag("builtins/customfield_value.html")
def customfield_value(customfield, value):
    """
    Render a custom field value according to the field type.

    Args:
        customfield: A CustomField instance
        value: The custom field value applied to an object
    """
    if value:
        if customfield.type == CustomFieldTypeChoices.TYPE_SELECT:
            value = customfield.get_choice_label(value)
        elif customfield.type == CustomFieldTypeChoices.TYPE_MULTISELECT:
            value = [customfield.get_choice_label(v) for v in value]
    return {
        "customfield": customfield,
        "value": value,
    }


@register.inclusion_tag("builtins/table_config_form.html")
def table_config_form(table, table_name=None):
    return {
        "table_name": table_name or table.__class__.__name__,
        "form": TableConfigForm(table=table),
    }


@register.inclusion_tag("builtins/applied_filters.html", takes_context=True)
def applied_filters(context, model, form, query_params):
    """
    Display the active filters for a given filter form.
    """
    user = context["request"].user
    form.is_valid()  # Ensure cleaned_data has been set

    applied_filters = []
    for filter_name in form.changed_data:
        if filter_name not in form.cleaned_data:
            continue

        querydict = query_params.copy()

        # Check if this is a modifier-enhanced field
        # Field may be in querydict as field__lookup instead of field
        param_name = None
        if filter_name in querydict:
            param_name = filter_name
        else:
            # Check for modifier variants (field__ic, field__isw, etc.)
            for key in querydict.keys():
                if key.startswith(f"{filter_name}__"):
                    param_name = key
                    break

        if param_name is None:
            continue

        # Skip saved filters, as they are displayed alongside the quick search widget
        if filter_name == "filter_id":
            continue

        bound_field = form.fields[filter_name].get_bound_field(form, filter_name)
        querydict.pop(param_name)

        # Extract modifier from parameter name (e.g., "serial__ic" -> "ic")
        if "__" in param_name:
            modifier = param_name.split("__", 1)[1]
        else:
            modifier = "exact"

        # Get display value
        display_value = ", ".join([str(v) for v in get_selected_values(form, filter_name)])

        # Get the correct lookup label for this field's type
        lookup_label = None
        if modifier != "exact":
            field = form.fields[filter_name]
            for field_class in field.__class__.__mro__:
                if field_lookups := FORM_FIELD_LOOKUPS.get(field_class):
                    for lookup_code, label in field_lookups:
                        if lookup_code == modifier:
                            lookup_label = label
                            break
                    if lookup_label:
                        break

        # Special handling for empty lookup (boolean value)
        if modifier == "empty":
            if display_value.lower() in ("true", "1"):
                link_text = f"{bound_field.label} {_('is empty')}"
            else:
                link_text = f"{bound_field.label} {_('is not empty')}"
        elif lookup_label:
            link_text = f"{bound_field.label} {lookup_label}: {display_value}"
        else:
            link_text = f"{bound_field.label}: {display_value}"

        applied_filters.append(
            {
                "name": param_name,  # Use actual param name for removal link
                "value": form.cleaned_data.get(filter_name),
                "link_url": f"?{querydict.urlencode()}",
                "link_text": link_text,
            }
        )

    # Handle empty modifier pills separately
    for param_name, param_value in query_params.items():
        if not param_name.endswith("__empty"):
            continue
        field_name = param_name[: -len("__empty")]
        if field_name not in form.fields or field_name == "filter_id":
            continue

        querydict = query_params.copy()
        querydict.pop(param_name)
        label = form.fields[field_name].label or field_name

        if param_value.lower() in ("true", "1"):
            link_text = f"{label} {_('is empty')}"
        else:
            link_text = f"{label} {_('is not empty')}"

        applied_filters.append(
            {
                "name": param_name,
                "value": param_value,
                "link_url": f"?{querydict.urlencode()}",
                "link_text": link_text,
            }
        )

    save_link = None
    perm = get_permission_for_model(model, "add")
    if user.has_perm(perm) and "filter_id" not in context["request"].GET:
        object_type = ObjectType.objects.get_for_model(model).pk
        parameters = json.dumps(dict(context["request"].GET.lists()))
        url = reverse("core:savedfilter_add")
        save_link = f"{url}?object_types={object_type}&parameters={quote(parameters)}"

    return {
        "applied_filters": applied_filters,
        "save_link": save_link,
    }


@register.filter
def get_selected_values(form, filter_name):
    """
    Get the display values for a filter field.
    """
    try:
        value = form.cleaned_data.get(filter_name)
        if isinstance(value, QuerySet):
            return [str(v) for v in value]
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value]
        return [str(value)]
    except (AttributeError, TypeError):
        return []


FORM_FIELD_LOOKUPS = {}


@register.tag
def action_url(parser, token):
    """
    Return an absolute URL matching the given model and action.

    This is a way to define links that aren't tied to a particular URL
    configuration::

        {% action_url model "action_name" %}

        or

        {% action_url model "action_name" pk=object.pk %}

        or

        {% action_url model "action_name" pk=object.pk as variable_name %}

    The first argument is a model or instance. The second argument is the action name.
    Additional keyword arguments can be passed for URL parameters.

    For example, if you have a Project model and want to link to its edit action::

        {% action_url project "edit" %}
        This will generate a URL like ``/ras/projects/123/edit/``.

        You can also pass additional parameters::

            {% action_url project "edit" pk=project.pk %}

        Or assign the URL to a variable::

            {% action_url project "edit" as edit_url %}
    """

    # Parse the token contents
    bits = token.split_contents()
    if len(bits) < 3:
        raise template.TemplateSyntaxError(f"'{bits[0]}' takes at least two arguments, a model and an action.")

    # Extract model and action
    model = parser.compile_filter(bits[1])
    action = bits[2].strip("\"'")  # Remove quotes from literal string
    kwargs = {}
    asvar = None
    bits = bits[3:]

    # Handle 'as' syntax for variable assignment
    if len(bits) >= 2 and bits[-2] == "as":
        asvar = bits[-1]
        bits = bits[:-2]

    # Parse remaining arguments as kwargs
    for bit in bits:
        if "=" not in bit:
            raise template.TemplateSyntaxError(
                f"'{token.contents.split()[0]}' keyword arguments must be in the format 'name=value'"
            )
        name, value = bit.split("=", 1)
        kwargs[name] = parser.compile_filter(value)

    return ActionURLNode(model, action, kwargs, asvar)


@register.simple_tag()
def qstring_update(request, **kwargs):
    """
    Append or update the page number in a querystring.
    """
    querydict = request.GET.copy()
    for k, v in kwargs.items():
        if v is not None:
            querydict[k] = str(v)
        elif k in querydict:
            querydict.pop(k)
    querystring = querydict.urlencode(safe="/")
    if querystring:
        return "?" + querystring
    else:
        return ""
