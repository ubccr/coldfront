# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms, template

from coldfront.constants import COLDFRONT_BLANK_CHOICE_LABEL

register = template.Library()

# Alpine selects show their popup search input only when the option list is
# longer than this threshold (unless search is forced on/off explicitly or the
# select is remote/API-backed, which always searches).
SEARCH_THRESHOLD = 10


@register.filter()
def fieldset_rows(fieldset, form):
    """
    Normalize a FieldSet's items into ``(kind, title, items)`` rows for
    rendering:
      * field name string  -> ('field', None, [bound_field])
      * GroupFields        -> ('group', groupFields, [bound_fields])
      * DisplayField       -> ('display', displayField, [instance_value])

    Fields listed in ``form.meta_fields`` or absent from ``form.fields`` are
    skipped. Empty GroupFields rows (all fields skipped) are dropped.
    """
    # Imported lazily to avoid pulling in the whole coldfront.forms package
    # (which imports every form module) at template-load time.
    from coldfront.forms.layout import DisplayField, GroupFields

    meta_fields = getattr(form, "meta_fields", ())
    rows = []
    for item in fieldset.items:
        if isinstance(item, GroupFields):
            fields = [form[name] for name in item.fields if name in form.fields and name not in meta_fields]
            if fields:
                rows.append(("group", item, fields))
        elif isinstance(item, DisplayField):
            instance = getattr(form, "instance", None)
            value = getattr(instance, item.name, None)
            if item.label:
                label = item.label
            else:
                label = value._meta.verbose_name if hasattr(value, "_meta") else item.name
                label = label.title()
            rows.append(("display", item, [value]))
        elif item in form.fields and item not in meta_fields:
            rows.append(("field", None, [form[item]]))
    return rows


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


@register.filter
def get_bound_field(form, field_name):
    """
    Return the bound field for a given field name from a form.
    Usage: {{ form|get_bound_field:field_name }}
    """
    return form[field_name]


@register.simple_tag
def render_field_with_aria(field, show_help=True, show_errors=True):
    """
    Render a bound field with WAI-ARIA: ``aria-describedby`` pointing at the
    help/error ids and ``aria-invalid`` on errors, plus the daisyUI error
    class on the control.

    ``show_help`` / ``show_errors`` gate whether the corresponding ids are
    referenced (the help/errors are rendered by the caller, outside the
    control). Any ``aria-describedby`` already set on the widget is merged
    rather than clobbered.
    """
    widget_attrs = field.field.widget.attrs
    described_by = []
    if show_errors and field.errors:
        described_by.append(f"{field.auto_id}_errors")
    if show_help and field.help_text:
        described_by.append(f"{field.auto_id}_helptext")
    extra = {}
    if described_by:
        existing = widget_attrs.get("aria-describedby", "").strip()
        extra["aria-describedby"] = " ".join(filter(None, [existing, *described_by]))
    if show_errors and field.errors:
        extra["aria-invalid"] = "true"
        widget = field.field.widget
        error_class = "input-error"
        if isinstance(widget, forms.Textarea):
            error_class = "textarea-error"
        elif isinstance(widget, forms.Select):
            error_class = "select-error"
        elif isinstance(widget, forms.FileInput):
            error_class = "file-input-error"
        # Preserve any widget-set class while adding the error class
        extra["class"] = " ".join(filter(None, [widget_attrs.get("class", ""), error_class]))
    # Alpine select widget templates read label/errors from attrs (they cannot
    # see the field), so mirror them onto the widget attrs.
    if isinstance(field.field.widget, forms.Select):
        if field.label:
            extra["data-cf-label"] = str(field.label)
        if show_errors and field.errors:
            extra["data-cf-invalid"] = "1"
    return field.as_widget(attrs=extra)


@register.simple_tag
def select_option_count(widget):
    """
    Return the number of selectable options on a widget, flattening optgroups.

    Operates on the widget render context (a dict), so it can be called from
    widget templates like ``alpine_select.html``. Counts the rendered
    ``optgroups`` — the same options a native select would display — rather
    than ``widget.choices`` (which is only on the widget instance).
    """
    count = 0
    for _group_name, group_choices, _group_index in widget["optgroups"]:
        count += len(group_choices)
    return count


@register.simple_tag
def select_should_show_search(widget):
    """
    Decide whether an Alpine select should render its popup search input.

    ``widget["searchable"]`` is the explicit ``True``/``False``/``None`` value
    set by ``AlpineSelectWidget.get_context``: ``True``/``False`` force the
    choice, ``None`` (the default) auto-derives it. Remote (API-backed) selects
    always search because their options are loaded asynchronously and the local
    option list is empty at render time. Otherwise the search box is shown only
    when the option list is longer than ``SEARCH_THRESHOLD``.
    """
    explicit = widget.get("searchable")
    if explicit is not None:
        return explicit
    if widget["attrs"].get("data-url"):
        return True
    return select_option_count(widget) > SEARCH_THRESHOLD


@register.simple_tag
def select_blank_label(widget):
    """
    Return the placeholder label for an Alpine select.

    A widget may set ``widget["blank_label"]`` in ``get_context`` to override
    the placeholder; otherwise it defaults to ``COLDFRONT_BLANK_CHOICE_LABEL``
    (the same label the stock blank option carries, so the placeholder always
    matches the actual blank option).
    """
    return widget.get("blank_label") or COLDFRONT_BLANK_CHOICE_LABEL
