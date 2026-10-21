# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext as _

from coldfront.users.querysets import RestrictedQuerySet


def parse_csv(reader):
    """
    Parse a csv_reader object into a headers dictionary and a list of records dictionaries. Raise an error
    if the records are formatted incorrectly. Return headers and records as a tuple.
    """
    records = []
    headers = {}

    # Consume the first line of CSV data as column headers. Create a dictionary mapping each header to an optional
    # "to" field specifying how the related object is being referenced. For example, importing a Resource might use a
    # `resource_type.slug` header, to indicate the related resource_type is being referenced by its slug.

    for header in next(reader):
        header = header.strip()
        if "." in header:
            field, to_field = header.split(".", 1)
            if field in headers:
                raise forms.ValidationError(
                    _('Duplicate or conflicting column header for "{field}"').format(field=field)
                )
            headers[field] = to_field
        else:
            if header in headers:
                raise forms.ValidationError(
                    _('Duplicate or conflicting column header for "{header}"').format(header=header)
                )
            headers[header] = None

    # Parse CSV rows into a list of dictionaries mapped from the column headers.
    for i, row in enumerate(reader, start=1):
        if len(row) != len(headers):
            raise forms.ValidationError(
                _("Row {row}: Expected {count_expected} columns but found {count_found}").format(
                    row=i, count_expected=len(headers), count_found=len(row)
                )
            )
        row = [col.strip() for col in row]
        record = dict(zip(headers.keys(), row))
        records.append(record)

    return headers, records


def add_blank_choice(choices):
    """
    Add a blank choice to the beginning of a choices list.
    """
    return ((None, "---------"),) + tuple(choices)


def restrict_form_fields(form, user, action="view"):
    """
    Restrict all form fields which reference a RestrictedQuerySet. This ensures that users see only permitted objects
    as available choices.
    """
    for field in form.fields.values():
        if hasattr(field, "queryset") and issubclass(field.queryset.__class__, RestrictedQuerySet):
            field.queryset = field.queryset.restrict(user, action)


def get_field_value(form, field_name):
    """
    Return the current bound or initial value associated with a form field, prior to calling
    clean() for the form.
    """
    field = form.fields[field_name]

    if form.is_bound and field_name in form.data:
        if (value := form.data[field_name]) is None:
            return None
        if hasattr(field, "valid_value") and field.valid_value(value):
            return value

    return form.get_initial_for_field(field, field_name)
