# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset, Layout
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import CustomFieldFilterLogicChoices
from coldfront.core.models import CustomField, ObjectType

from .mixins import CustomFieldsMixin, HorizontalFormMixin, SavedFiltersMixin

__all__ = (
    "ColdFrontModelFilterSetForm",
    "PrimaryModelFilterSetForm",
    "OrganizationalModelFilterSetForm",
    "NestedGroupModelFilterSetForm",
)


class BaseModelFilterSetForm(SavedFiltersMixin, HorizontalFormMixin, CustomFieldsMixin, forms.Form):
    """
    Base form for FilerSet forms. These are used to filter object lists in the ColdFront UI. Note that the
    corresponding FilterSet *must* provide a `q` filter.
    """

    q = forms.CharField(required=False, label=_("Search"))
    selector_fields = ("filter_id", "q")
    fieldsets = ()

    @property
    def helper(self):
        """
        crispy forms helper which defines the form rendering behavior. Override to set form method to get
        """
        helper = super().helper
        helper.form_method = "get"
        return helper

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

    def get_layout(self):
        """
        Override crispy layout to include search and filter fields
        """
        fieldsets = [Fieldset(_("Search"), "q", "filter_id"), *self.fieldsets]

        # Add custom fields section if any custom fields exist
        if self.custom_fields:
            custom_fieldsets = []
            for group, fields in self.custom_field_groups.items():
                if group:
                    custom_fieldsets.append(
                        Fieldset(
                            group,
                            *fields,
                        )
                    )
                else:
                    custom_fieldsets.append(
                        Fieldset(
                            _("Custom Fields"),
                            *fields,
                        )
                    )
            fieldsets.extend(custom_fieldsets)

        return Layout(*fieldsets)


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
