# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms

from coldfront.core.models import ObjectType

__all__ = (
    "ContentTypeChoiceField",
    "ContentTypeMultipleChoiceField",
)


class ContentTypeChoiceMixin:
    def __init__(self, queryset, *args, **kwargs):
        # Order ContentTypes by app_label
        queryset = queryset.order_by("app_label", "model")
        super().__init__(queryset, *args, **kwargs)

    def label_from_instance(self, obj):
        try:
            return ObjectType.display_name(obj)
        except AttributeError:
            return super().label_from_instance(obj)


class ContentTypeChoiceField(ContentTypeChoiceMixin, forms.ModelChoiceField):
    """
    Selection field for a single content type.
    """

    def __init__(self, queryset, *args, **kwargs):
        super().__init__(queryset, *args, **kwargs)


class ContentTypeMultipleChoiceField(ContentTypeChoiceMixin, forms.ModelMultipleChoiceField):
    """
    Selection field for one or more content types.
    """

    def __init__(self, queryset, *args, **kwargs):
        super().__init__(queryset, *args, **kwargs)
