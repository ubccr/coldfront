# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

"""
Pure layout descriptors for ColdFront forms.

These are data-only objects describing how fields are grouped and ordered in a
rendered form. They contain no rendering logic — the cotton components
(``c-cf.form``, ``c-cf.form.fieldsets``, ``c-cf.field``) interpret them.

Forms declare a ``fieldsets`` attribute (a tuple/list of :class:`FieldSet`,
or a ``@property`` returning one for dynamic forms). The renderer reads
``form.fieldsets`` directly.
"""

__all__ = ("FieldSet", "GroupFields", "DisplayField")


class FieldSet:
    """
    A grouping of fields under an optional heading.

    Parameters:
        items: An iterable of items to render within the group. Items may be
            field name strings, :class:`GroupFields` instances, or
            :class:`DisplayField` instances.
        name: The heading text shown above the group (optional). ``None``
            renders no heading.
    """

    def __init__(self, *items, name=None):
        self.items = items
        self.name = name


class GroupFields:
    """
    A set of fields rendered side-by-side in a row, with an optional shared
    label.

    If ``label`` is provided the fields share a single label on the row;
    otherwise each field renders with its own label above its control, all
    displayed side-by-side.

    Parameters:
        fields: An iterable of form field names to render in the row.
        label: The label text to render for the row (optional).
        compact_field_labels: Render field labels directly on the input field (default False).
    """

    def __init__(self, *fields, label=None, compact_field_labels=False):
        self.fields = fields
        self.label = label
        self.compact_field_labels = compact_field_labels


class DisplayField:
    """
    Renders the value for a specific attribute on the form's instance as a
    read-only display (e.g. to convey context). If the attribute value has a
    ``get_absolute_url()`` method, it is rendered as a hyperlink.

    Parameters:
        name: The name of the attribute to display.
        label: An optional display label. If ``None``, the label falls back to
            the value's ``_meta.verbose_name`` (or ``name``) with ``.title()``.
    """

    def __init__(self, name, label=None):
        self.name = name
        self.label = label
