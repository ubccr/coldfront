# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _
from djmoney.forms.widgets import MoneyWidget as _MoneyWidget


class MarkdownWidget(forms.Textarea):
    """
    Provide a live preview for Markdown-formatted content.
    """

    template_name = "widgets/markdown_input.html"

    def __init__(self, attrs=None):
        # Markdown fields should use monospace font and the daisyUI textarea style
        default_attrs = {
            "class": "font-mono min-h-48 textarea w-full",
        }
        if attrs:
            default_attrs.update(attrs)

        super().__init__(default_attrs)


class SlugWidget(forms.TextInput):
    """
    A slug field with an appended "regenerate slug" button.

    The ``template_name`` owns the ``.join`` wrapper + action button; the
    ``slug_source`` attr is set on the widget by ``SlugField.get_bound_field``
    and rendered onto the input for the reslug JS.
    """

    template_name = "widgets/slug.html"

    def __init__(self, attrs=None):
        default_attrs = {
            "class": "join-item rounded-l-field input w-full",
        }
        if attrs:
            default_attrs.update(attrs)

        super().__init__(default_attrs)


class CopyWidget(forms.TextInput):
    """
    A read-only field with an appended "copy to clipboard" button.
    """

    template_name = "widgets/copy.html"

    def __init__(self, attrs=None):
        default_attrs = {
            "class": "join-item rounded-l-field input w-full",
        }
        if attrs:
            default_attrs.update(attrs)

        super().__init__(default_attrs)


class BooleanSelectWidget(forms.NullBooleanSelect):
    """
    A boolean field rendered as a yes/no select instead of a checkbox.

    ``labels`` is a tuple, defaulting to ("Yes", "No") for the true/false values.
    """

    def __init__(self, attrs=None, labels=None, blank_label=_("---------")):
        yes, no = labels or (_("Yes"), _("No"))
        choices = []
        if blank_label:
            choices.append(("unknown", blank_label))
        choices += [("true", yes), ("false", no)]

        super().__init__(attrs)
        self.choices = choices


class MoneyWidget(_MoneyWidget):
    """
    Render a django-money amount + currency pair as a daisyUI join.

    The amount input and the currency select are emitted as siblings inside a
    single ``.join`` so they sit side-by-side in one row. The amount input
    receives the daisyUI ``input`` class and the currency select ``select``.
    """

    template_name = "widgets/money_input.html"

    # Render with a normal <label> like the other form fields instead of
    # Django's default <fieldset>/<legend> wrapper for MultiWidgets.
    use_fieldset = False

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        subwidgets = context["widget"]["subwidgets"]
        if len(subwidgets) >= 2:
            subwidgets[0]["attrs"]["class"] = "input join-item w-full rounded-l-field"
            subwidgets[1]["attrs"]["class"] = "select join-item rounded-r-field"
        return context
