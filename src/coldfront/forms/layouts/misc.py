# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.bootstrap import AppendedText
from crispy_forms.layout import Field
from django.utils.html import format_html
from django.utils.safestring import mark_safe


class Date(Field):
    def __init__(self, name):
        super().__init__(name, css_class="date-picker")


class DateTime(Field):
    def __init__(self, name):
        super().__init__(name, css_class="datetime-picker")


class Time(Field):
    def __init__(self, name):
        super().__init__(name, css_class="time-picker")


class Slug(AppendedText):
    def __init__(self, name="slug"):
        super().__init__(
            name,
            mark_safe(
                '<button type="button" title="Regenerate Slug" class="btn reslug"> <i class="fa-solid fa-rotate"></i></button>'
            ),
            css_class="slug-field",
        )


class CopyClipboard(AppendedText):
    def __init__(self, name):
        super().__init__(
            name,
            format_html(
                '<button type="button" title="Copy to clipboard" class="btn copy-content" data-clipboard-target="#id_{}"><i class="fa-solid fa-copy"></i></button>',
                name,
            ),
        )
