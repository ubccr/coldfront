# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import CustomFieldFilterLogicChoices
from coldfront.core.models import CustomField, ObjectType

from .mixins import CustomFieldsMixin, SavedFiltersMixin

__all__ = (
    "ColdFrontModelFilterSetForm",
    "PrimaryModelFilterSetForm",
    "OrganizationalModelFilterSetForm",
    "NestedGroupModelFilterSetForm",
)


class BaseModelFilterSetForm(SavedFiltersMixin, CustomFieldsMixin, forms.Form):
    """
    Base form for FilterSet forms. These are used to filter object lists in the ColdFront UI. Note that the
    corresponding FilterSet *must* provide a `q` filter.
    """

    q = forms.CharField(required=False, label=_("Search"))
    selector_fields = ("filter_id", "q")
    fieldsets = ()

    def _get_content_type(self):
        return ObjectType.objects.get_for_model(self.model)

    def _get_custom_fields(self, content_type):
        fields = []

        for cf in CustomField.objects.get_for_model(content_type.model_class()):
            # Include only custom fields that are enabled for filtering
            if cf.filter_logic == CustomFieldFilterLogicChoices.FILTER_DISABLED:
                continue
            fields.append(cf)

        return fields

    def _get_form_field(self, customfield):
        return customfield.to_form_field(
            set_initial=False,
            enforce_required=False,
            enforce_visibility=False,
            for_filterset_form=True,
        )


class ColdFrontModelFilterSetForm(BaseModelFilterSetForm):
    """
    Base form for FilterSet forms.
    """

    pass


class PrimaryModelFilterSetForm(ColdFrontModelFilterSetForm):
    """
    FilterSet form for models which inherit from PrimaryModel.
    """

    pass


class OrganizationalModelFilterSetForm(ColdFrontModelFilterSetForm):
    """
    FilterSet form for models which inherit from OrganizationalModel.
    """

    pass


class NestedGroupModelFilterSetForm(ColdFrontModelFilterSetForm):
    """
    FilterSet form for models which inherit from NestedGroupModel.
    """

    pass
