# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import zoneinfo
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote

import django_tables2 as tables
import humanize
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.contrib.humanize.templatetags.humanize import naturalday
from django.db.models import DateField, DateTimeField
from django.template import Context, Template
from django.urls import reverse
from django.utils.dateparse import parse_date
from django.utils.html import escape, format_html
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_cotton import render_component
from django_tables2.columns import library
from django_tables2.utils import Accessor

from coldfront.core.choices import CustomFieldTypeChoices
from coldfront.core.models import ObjectType
from coldfront.users.permissions import get_permission_for_model
from coldfront.views import get_action_url

__all__ = (
    "ActionsColumn",
    "ArrayColumn",
    "BooleanColumn",
    "BytesColumn",
    "ColorColumn",
    "ChoicesColumn",
    "ColoredLabelColumn",
    "ContentTypeColumn",
    "ContentTypesColumn",
    "ChoiceFieldColumn",
    "LinkedCountColumn",
    "MPTTColumn",
    "MarkdownColumn",
    "ManyToManyColumn",
    "TagColumn",
    "ToggleColumn",
)

#
# Django-tables2 overrides
#


@library.register
class DateColumn(tables.Column):
    """
    Render a datetime.date in ISO 8601 format.
    """

    def render(self, value):
        if value:
            # DateField values are datetime.date (no .date()); DateTimeField
            # values are datetime.datetime and need the date() conversion.
            iso = value.date().isoformat() if hasattr(value, "date") else value.isoformat()
            return naturalday(iso)

    def value(self, value):
        if value:
            return naturalday(value.date().isoformat() if hasattr(value, "date") else value.isoformat())

    @classmethod
    def from_field(cls, field, **kwargs):
        if isinstance(field, DateField):
            return cls(**kwargs)


@library.register
class DateTimeColumn(tables.Column):
    """
    Render a datetime.datetime in ISO 8601 format.

    Args:
        timespec: Granularity specification; passed through to datetime.isoformat()
    """

    def __init__(self, *args, timespec="seconds", **kwargs):
        self.timespec = timespec
        super().__init__(*args, **kwargs)

    def render(self, value):
        if value:
            current_tz = zoneinfo.ZoneInfo(settings.TIME_ZONE)
            value = value.astimezone(current_tz)
            return f"{value.date().isoformat()} {value.time().isoformat(timespec=self.timespec)}"

    def value(self, value):
        if value:
            return value.isoformat()

    @classmethod
    def from_field(cls, field, **kwargs):
        if isinstance(field, DateTimeField):
            return cls(**kwargs)


#
# Custom columns
#


def render_boolean(request, value):
    """
    Render a boolean value through the shared `c-cf.checkmark` component.

    The component handles all three states: None → em-dash placeholder, true →
    check icon, false → X icon. Requires a request for cotton's RequestContext.
    """
    return mark_safe(render_component(request, "cf.checkmark", {"value": value}))


class BooleanColumn(tables.TemplateColumn):
    """
    Custom implementation of BooleanColumn to render a checkmark or X icon
    through the shared `c-cf.checkmark` component instead of a Unicode character.
    """

    template_code = """
    {% cotton cf.checkmark :value="value" /%}
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            self.template_code,
            *args,
            **kwargs,
        )

    def value(self, value):
        return str(value)


class ToggleColumn(tables.CheckBoxColumn):
    """
    Extend CheckBoxColumn to add a "toggle all" checkbox in the column header.

    Each row checkbox gets an accessible name ("Select <record>") via
    ``td__input`` — ``computed_values`` resolves the callable against the row
    ``record`` so screen readers announce which object is being selected
    (WCAG 4.1.2). The header toggle-all checkbox carries its own aria-label.
    """

    def __init__(self, *args, **kwargs):
        default = kwargs.pop("default", "")
        visible = kwargs.pop("visible", False)
        if "attrs" not in kwargs:
            kwargs["attrs"] = {
                "th": {
                    "class": "w-10",
                    "aria-label": _("Select all"),
                },
                "td": {
                    "class": "w-10",
                },
                "input": {"class": "checkbox checkbox-xs"},
                "td__input": {
                    "class": "checkbox checkbox-xs",
                    "aria-label": lambda record, value: _("Select %s") % record,
                },
            }
        super().__init__(*args, default=default, visible=visible, **kwargs)

    @property
    def header(self):
        title_text = _("Toggle all")
        return format_html(
            '<input type="checkbox" class="cf-toggle-all checkbox checkbox-xs" title="{}" aria-label="{}" />',
            title_text,
            title_text,
        )


class MPTTColumn(tables.TemplateColumn):
    """
    Display a nested hierarchy for MPTT-enabled models.
    """

    template_code = """
        {% if not table.order_by %}
          {% for i in record.level|as_range %}{% cotton cfi n="tablericon.circle-dot" size="xs" /%}{% endfor %}
        {% endif %}
        <a href="{{ record.get_absolute_url }}">{{ record.name }}</a>
    """

    def __init__(self, *args, **kwargs):
        super().__init__(
            template_code=self.template_code, attrs={"td": {"class": "whitespace-nowrap"}}, *args, **kwargs
        )

    def value(self, value):
        return value


class LinkedCountColumn(tables.Column):
    """
    Render a count of related objects linked to a filtered URL.

    :param viewname: The view name to use for URL resolution
    :param view_kwargs: Additional kwargs to pass for URL resolution (optional)
    :param url_params: A dict of query parameters to append to the URL (e.g. ?foo=bar) (optional)
    """

    def __init__(self, viewname, *args, view_kwargs=None, url_params=None, default=0, **kwargs):
        self.viewname = viewname
        self.view_kwargs = view_kwargs or {}
        self.url_params = url_params
        super().__init__(*args, default=default, **kwargs)

    def render(self, record, value):
        if value:
            kargs = {}
            for k, v in self.view_kwargs.items():
                kargs[k] = getattr(record, v)

            url = reverse(self.viewname, kwargs=kargs)
            if self.url_params:
                url += "?" + "&".join(
                    [
                        f"{k}={getattr(record, v) or settings.FILTERS_NULL_CHOICE_VALUE}"
                        for k, v in self.url_params.items()
                    ]
                )
            return format_html('<a href="{}">{}</a>', url, escape(value))
        return value

    def value(self, value):
        return value


class TagColumn(tables.TemplateColumn):
    """
    Display a list of Tags assigned to the object.
    """

    template_code = """
    {% for tag in value.all %}
        {% cotton cf.badge variant="{{ tag.color }}" as="a" href="{% url url_name %}?tag={{ tag.slug }}" %}{{ tag }}{% endcotton %}
    {% empty %}
        <span class="text-muted">&mdash;</span>
    {% endfor %}
    """

    def __init__(self, url_name=None):
        super().__init__(
            orderable=False,
            template_code=self.template_code,
            extra_context={"url_name": url_name},
            verbose_name=_("Tags"),
        )

    def value(self, value):
        return ",".join([tag.name for tag in value.all()])


@dataclass
class ActionsItem:
    title: str
    icon: str
    permission: Optional[str] = None
    css_class: Optional[str] = "secondary"


class ActionsColumn(tables.Column):
    """
    A dropdown menu which provides edit, delete, and changelog links for an object. Can optionally include
    additional buttons rendered from a template string.

    :param actions: The ordered list of dropdown menu items to include
    :param extra_buttons: A Django template string which renders additional buttons preceding the actions dropdown
    :param split_actions: When True, converts the actions dropdown menu into a split button with first action as the
        direct button link and icon (default: True)
    """

    # The column header is intentionally blank (icon-only actions); give the
    # empty <th> an accessible name so screen readers announce the column
    # (WCAG 4.1.2).
    attrs = {
        "td": {"class": "text-end whitespace-nowrap print:hidden p-1"},
        "th": {"class": "w-10", "aria-label": _("Actions")},
    }
    empty_values = ()
    actions = {
        "edit": ActionsItem("Edit", "lucideicon.pen-square", "change", "primary"),
        "delete": ActionsItem("Delete", "heroicon.trash", "delete", "error"),
        "changelog": ActionsItem("Changelog", "tablericon.history", "change", "info"),
    }

    def __init__(
        self,
        *args,
        actions=("edit", "delete", "changelog"),
        extra_buttons="",
        extra_actions=None,
        split_actions=True,
        **kwargs,
    ):
        # The actions column has no underlying sortable field, so it is never orderable.
        kwargs.setdefault("orderable", False)
        super().__init__(*args, **kwargs)

        self.extra_buttons = extra_buttons
        self.extra_actions = extra_actions
        self.split_actions = split_actions

        # Determine which actions to enable
        self.actions = {name: self.actions[name] for name in actions}

    def header(self):
        return ""

    def render(self, record, table, **kwargs):
        model = table.Meta.model

        # Skip if no actions or extra buttons are defined
        if not (self.actions or self.extra_buttons or self.extra_actions):
            return ""
        # Skip dummy records (e.g. available VLANs or IP ranges replacing individual IPs)
        if not isinstance(record, model) or not getattr(record, "pk", None):
            return ""

        # render_component needs a request (for RequestContext); tables rendered through
        # views always carry one in table.context.
        request = getattr(table, "context", {}).get("request")
        if request is None:
            return ""
        return_url = request.GET.get("return_url", request.get_full_path())
        url_appendix = f"?return_url={quote(return_url)}"

        user = getattr(request, "user", AnonymousUser())

        # Compile the permission-visible actions into render-ready items.
        items = []
        for action, attrs in self.actions.items():
            permission = get_permission_for_model(model, attrs.permission)
            if attrs.permission is None or user.has_perm(permission):
                url = get_action_url(model, action=action, kwargs={"pk": record.pk})
                items.append(
                    {
                        "title": attrs.title,
                        "icon": attrs.icon,
                        "url": url + url_appendix,
                        "css_class": attrs.css_class,
                    }
                )

        if self.extra_actions:
            if callable(self.extra_actions):
                extra_actions = self.extra_actions(record, table, user, request)
                if isinstance(extra_actions, (list, tuple)):
                    items.extend(extra_actions)

        # Render any extra buttons from template code or a callable
        extra_html = ""
        if self.extra_buttons:
            if callable(self.extra_buttons):
                extra_html = self.extra_buttons(record, user, request)
            else:
                template = Template(self.extra_buttons)
                context = getattr(table, "context", Context())
                context.update({"record": record})
                extra_html = template.render(context)

        return mark_safe(
            render_component(
                request,
                "cf.dtable.actions_column",
                {
                    "record": record,
                    "items": items,
                    "split_actions": self.split_actions,
                    "extra_buttons": extra_html,
                },
            )
        )


class ColorColumn(tables.TemplateColumn):
    """
    Display a badge variant value as a pill swatch.
    """

    template_code = """
       {% cotton cf.badge variant="{{ value|default:'neutral' }}" %}{{ value|title }}{% endcotton %}
"""

    def __init__(self, *args, **kwargs):
        super().__init__(template_code=self.template_code, *args, **kwargs)

    def value(self, value):
        return value


class ColoredLabelColumn(tables.TemplateColumn):
    """
    Render a related object as a badge variant label. The related object must have a `color`
    attribute (specifying a daisyUI badge variant) and a `get_absolute_url()` method.
    """

    template_code = """
      {% if value %}
         {% cotton cf.badge variant="{{ value.color|default:'neutral' }}" %}{{ value }}{% endcotton %}
      {% else %}
         &mdash;
      {% endif %}
"""

    def __init__(self, *args, **kwargs):
        super().__init__(template_code=self.template_code, *args, **kwargs)

    def value(self, value):
        return str(value)


class ContentTypeColumn(tables.Column):
    """
    Display a ContentType instance.
    """

    def render(self, value):
        if value is None:
            return None
        return ObjectType.display_name(value, include_app=False)

    def value(self, value):
        if value is None:
            return None
        return ObjectType.identifier_string(value)


class ContentTypesColumn(tables.ManyToManyColumn):
    """
    Display a list of ContentType instances.
    """

    def __init__(self, separator=None, *args, **kwargs):
        # Use a line break as the default separator
        if separator is None:
            separator = mark_safe("<br />")
        super().__init__(separator=separator, *args, **kwargs)

    def transform(self, obj):
        return ObjectType.display_name(obj, include_app=False)

    def value(self, value):
        return ",".join([ObjectType.identifier_string(ot) for ot in self.filter(value)])


class TemplateColumn(tables.TemplateColumn):
    """
    Overrides django-tables2's stock TemplateColumn class to render a placeholder symbol if the returned value
    is an empty string.
    """

    PLACEHOLDER = mark_safe("&mdash;")

    def __init__(self, export_raw=False, **kwargs):
        """
        Args:
            export_raw: If true, data export returns the raw field value rather than the rendered template. (Default:
                        False)
        """
        super().__init__(**kwargs)
        self.export_raw = export_raw

    def render(self, *args, **kwargs):
        ret = super().render(*args, **kwargs)
        if not ret.strip():
            return self.PLACEHOLDER
        return ret

    def value(self, **kwargs):
        if self.export_raw:
            # Skip template rendering and export raw value
            return kwargs.get("value")

        ret = super().value(**kwargs)
        if ret == self.PLACEHOLDER:
            return ""
        return ret


class ChoiceFieldColumn(tables.Column):
    """
    Render a model's static ChoiceField with its value from `get_FOO_display()` as a colored badge. Background color is
    set by the instance's get_FOO_color() method, if defined, or can be overridden by a "color" callable.
    """

    DEFAULT_BG_COLOR = "secondary"

    def __init__(self, *args, color=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.color = color

    def render(self, record, bound_column, value):
        if value in self.empty_values:
            return self.default

        # Determine the background color to use (use "color" callable if given, else try calling object.get_FOO_color())
        if self.color:
            bg_color = self.color(record)
        else:
            try:
                bg_color = getattr(record, f"get_{bound_column.name}_color")() or self.DEFAULT_BG_COLOR
            except AttributeError:
                bg_color = self.DEFAULT_BG_COLOR

        return format_html('<span class="badge badge-{}">{}</span>', bg_color, value)

    def value(self, value):
        return value


class MarkdownColumn(tables.TemplateColumn):
    """
    Render a Markdown string.
    """

    template_code = """
    {% if value %}
      {{ value|markdown }}
    {% else %}
      &mdash;
    {% endif %}
    """

    def __init__(self, **kwargs):
        super().__init__(
            template_code=self.template_code,
            **kwargs,
        )

    def value(self, value):
        return value


class ChoicesColumn(tables.Column):
    """
    Display the human-friendly labels of a set of choices.
    """

    def __init__(self, *args, max_items=None, **kwargs):
        self.max_items = max_items
        super().__init__(*args, **kwargs)

    def render(self, value):
        omitted_count = 0
        value = [v[1] for v in value]

        # Limit the returned items to the specified maximum number (if any)
        if self.max_items:
            omitted_count = len(value) - self.max_items
            value = value[: self.max_items - 1]

        # Annotate omitted items (if applicable)
        if omitted_count > 0:
            value.append(f"({omitted_count} more)")

        return ", ".join(value)


class ManyToManyColumn(tables.ManyToManyColumn):
    """
    Overrides django-tables2's stock ManyToManyColumn to ensure that value() returns only plaintext data.
    """

    def value(self, value):
        items = [self.transform(item) for item in self.filter(value)]
        return self.separator.join(items)


class ArrayColumn(tables.Column):
    """
    List array items as a comma-separated list.
    """

    def __init__(self, *args, max_items=None, func=str, **kwargs):
        self.max_items = max_items
        self.func = func
        super().__init__(*args, **kwargs)

    def render(self, value):
        omitted_count = 0

        # Limit the returned items to the specified maximum number (if any)
        if self.max_items:
            omitted_count = len(value) - self.max_items
            value = value[: self.max_items - 1]

        # Apply custom processing function (if any) per item
        if self.func:
            value = [self.func(v) for v in value]

        # Annotate omitted items (if applicable)
        if omitted_count > 0:
            value.append(f"({omitted_count} more)")

        return ", ".join(value)


class CustomFieldColumn(tables.TemplateColumn):
    """
    Display custom fields in the appropriate format.
    """

    # Per-type rendering is handled in render(); this only satisfies
    # TemplateColumn's template requirement and is never rendered.
    template_code = "{% comment %}Rendered by CustomFieldColumn.render(){}{% endcomment %}"

    empty_values = (None, "")

    def __init__(self, customfield, *args, **kwargs):
        self.customfield = customfield
        kwargs["accessor"] = Accessor(f"custom_field_data__{customfield.name}")
        if "verbose_name" not in kwargs:
            kwargs["verbose_name"] = customfield.label or customfield.name
        # We can't logically sort on FK values
        if customfield.type in (CustomFieldTypeChoices.TYPE_OBJECT, CustomFieldTypeChoices.TYPE_MULTIOBJECT):
            kwargs["orderable"] = False

        super().__init__(
            self.template_code,
            *args,
            **kwargs,
        )

    @staticmethod
    def _linkify_item(item):
        if hasattr(item, "get_absolute_url"):
            return f'<a href="{item.get_absolute_url()}">{escape(item)}</a>'
        return escape(item)

    def render(self, record, table, value, bound_column, **kwargs):
        if self.customfield.type == CustomFieldTypeChoices.TYPE_BOOLEAN:
            request = getattr(table, "context", {}).get("request")
            if request is None:
                return ""
            return render_boolean(request, value)
        if self.customfield.type == CustomFieldTypeChoices.TYPE_SELECT:
            return self.customfield.get_choice_label(value)
        if self.customfield.type == CustomFieldTypeChoices.TYPE_MULTISELECT:
            return ", ".join(self.customfield.get_choice_label(v) for v in value)
        if self.customfield.type == CustomFieldTypeChoices.TYPE_MULTIOBJECT:
            return mark_safe(", ".join(self._linkify_item(obj) for obj in self.customfield.deserialize(value)))
        if self.customfield.type == CustomFieldTypeChoices.TYPE_LONGTEXT and value:
            return mark_safe(value)
        if self.customfield.type == CustomFieldTypeChoices.TYPE_DATE and value:
            return parse_date(value).isoformat()
        if value is not None:
            obj = self.customfield.deserialize(value)
            return mark_safe(self._linkify_item(obj))
        return self.default

    def value(self, value):
        if isinstance(value, list):
            return ",".join(str(v) for v in self.customfield.deserialize(value))
        if value is not None:
            return self.customfield.deserialize(value)
        return self.default


class BytesColumn(tables.Column):
    """
    Render a column as human readable bytes
    """

    def render(self, value):
        return humanize.naturalsize(value)
