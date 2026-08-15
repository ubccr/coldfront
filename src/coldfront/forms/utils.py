# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext as _


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
