# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import json

from django import forms
from django.conf import settings
from django.db.models import Count
from django.forms.fields import InvalidJSONInput
from django.forms.fields import JSONField as _JSONField
from django.utils.translation import gettext_lazy as _
from djmoney.forms import MoneyField as DjangoMoneyField

from coldfront.forms import widgets
from coldfront.models.utils import get_default_currency


class SimpleArrayField(forms.CharField):
    """
    A form field which represents a list of values as a comma-separated string.
    This provides a simple alternative to Django's SimpleArrayField (which requires psycopg2).
    """

    def __init__(self, base_field=None, delimiter=",", *args, **kwargs):
        self.base_field = base_field or forms.CharField()
        self.delimiter = delimiter
        kwargs.setdefault("widget", forms.TextInput(attrs={"class": "form-control"}))
        kwargs.setdefault("required", False)
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        if not value:
            return []
        if isinstance(value, list):
            return value
        return [v.strip() for v in value.split(self.delimiter) if v.strip()]

    def prepare_value(self, value):
        if isinstance(value, list):
            return self.delimiter.join(str(v) for v in value)
        return value or ""


class QueryField(forms.CharField):
    """
    A CharField subclass used for global search/query fields in filter forms.
    """

    pass


class SlugField(forms.SlugField):
    """
    Extend Django's built-in SlugField to automatically populate from a field called `name` unless otherwise specified.

    Parameters:
        slug_source: Name of the form field from which the slug value will be derived
    """

    label = _("Slug")
    help_text = _("URL-friendly unique shorthand")

    def __init__(self, *, slug_source="name", label=label, help_text=help_text, **kwargs):
        super().__init__(label=label, help_text=help_text, **kwargs)

        self.slug_source = slug_source

    def get_bound_field(self, form, field_name):
        self.widget.attrs["slug-source"] = self.slug_source

        if prefix := form.prefix:
            if self.slug_source and not self.slug_source.startswith(f"{prefix}-"):
                self.slug_source = f"{prefix}-{self.slug_source}"
                self.widget.attrs["slug-source"] = self.slug_source

        return super().get_bound_field(form, field_name)


class TagFilterField(forms.MultipleChoiceField):
    """
    A filter field for the tags of a model. Only the tags used by a model are displayed.

    :param model: The model of the filter
    """

    def __init__(self, model, *args, **kwargs):
        def get_choices():
            tags = model.tags.annotate(count=Count("core_taggeditem_items")).order_by("name")
            return [
                (settings.FILTERS_NULL_CHOICE_VALUE, settings.FILTERS_NULL_CHOICE_LABEL),  # "None" option
                *[(str(tag.slug), f"{tag.name} ({tag.count})") for tag in tags],
            ]

        # Choices are fetched each time the form is initialized
        super().__init__(label=_("Tags"), choices=get_choices, required=False, *args, **kwargs)


class JSONField(_JSONField):
    """
    Custom wrapper around Django's built-in JSONField to avoid presenting "null" as the default text.
    """

    empty_values = [None, "", ()]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.widget.attrs["placeholder"] = ""
        self.widget.attrs["class"] = "font-monospace"
        if not self.help_text:
            self.help_text = _('Enter context data in <a href="https://json.org/">JSON</a> format.')

    def prepare_value(self, value):
        if isinstance(value, InvalidJSONInput):
            return value
        if value in ("", None):
            return ""
        if type(value) is str:
            try:
                value = json.loads(value, cls=self.decoder)
            except json.decoder.JSONDecodeError:
                return f'"{value}"'
        return json.dumps(value, sort_keys=True, indent=4, ensure_ascii=False, cls=self.encoder)


class CommentField(forms.CharField):
    """
    A textarea with support for Markdown rendering.
    """

    widget = widgets.MarkdownWidget
    label = _("Comments")
    help_text = _(
        '<i class="fa-solid fa-circle-info"></i> '
        '<a href="{url}" target="_blank" tabindex="-1">Markdown</a> syntax is supported'
    ).format(url="#")

    def __init__(self, *, label=label, help_text=help_text, required=False, **kwargs):
        super().__init__(label=label, help_text=help_text, required=required, **kwargs)


class MoneyField(DjangoMoneyField):
    """
    A django-money amount + currency field rendered as a Bootstrap input-group.

    Keeps the MultiValueField contract (POST keys ``amount_awarded_0`` /
    ``amount_awarded_1``) while swapping django-money's default ``MoneyWidget``
    for ``MoneyWidget`` so the amount input and currency select sit
    side-by-side in a single row.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget = widgets.MoneyWidget(
            amount_widget=self.fields[0].widget,
            currency_widget=self.fields[1].widget,
            default_currency=get_default_currency(),
        )
