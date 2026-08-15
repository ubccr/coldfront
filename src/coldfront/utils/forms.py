# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0


from coldfront.users.querysets import RestrictedQuerySet


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
