# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset, Layout
from django import forms
from django.contrib.contenttypes.models import ContentType
from django.utils.translation import gettext as _

from coldfront.forms.fields import SlugField

from .forms import TenancyForm
from .mixins import ChangelogMessageMixin, CheckLastUpdatedMixin, CustomFieldsMixin, HorizontalFormMixin, TagsMixin


class ColdFrontModelForm(
    HorizontalFormMixin,
    ChangelogMessageMixin,
    CheckLastUpdatedMixin,
    CustomFieldsMixin,
    TagsMixin,
    forms.ModelForm,
):
    """
    Base form for creating & editing ColdFront models.
    """

    user = None
    fieldsets = ()

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)

    def _get_content_type(self):
        return ContentType.objects.get_for_model(self._meta.model)

    def _post_clean(self):
        """
        Override BaseModelForm's _post_clean() to store many-to-many field values on the model instance.
        """
        self.instance._m2m_values = {}
        for field in self.instance._meta.local_many_to_many:
            if field.name in self.cleaned_data:
                self.instance._m2m_values[field.name] = list(self.cleaned_data[field.name])

        return super()._post_clean()

    def _get_form_field(self, customfield):
        if self.instance.pk:
            form_field = customfield.to_form_field(set_initial=False)
            form_field.initial = self.instance.custom_field_data.get(customfield.name)
            return form_field

        return customfield.to_form_field()

    def clean(self):

        # Save custom field data on instance
        for cf_name, customfield in self.custom_fields.items():
            if cf_name not in self.fields:
                # Custom fields may be absent when performing bulk updates via import
                continue
            key = cf_name[3:]  # Strip "cf_" from field name
            value = self.cleaned_data.get(cf_name)

            # Convert "empty" values to null
            if value in self.fields[cf_name].empty_values:
                self.instance.custom_field_data[key] = None
            else:
                self.instance.custom_field_data[key] = customfield.serialize(value)

        return super().clean()

    def get_layout(self):
        """
        Override crispy layout to include Tenant and Tag fieldsets if user has view permissions.
        """
        if not self.user:
            return Layout(*self.fieldsets)

        fieldsets = [*self.fieldsets]

        if (
            issubclass(self.__class__, TenancyForm)
            and self.user.has_perms(["tenancy.view_tenant"])
            and ("tenant" in self._meta.fields or "tenant_group" in self._meta.fields)
        ):
            tenant_fields = []
            if "tenant_group" in self._meta.fields:
                tenant_fields.append("tenant_group")
            if "tenant" in self._meta.fields:
                tenant_fields.append("tenant")

            fieldsets.append(
                Fieldset(
                    _("Tenant"),
                    *tenant_fields,
                )
            )

        if (
            issubclass(self.__class__, TagsMixin)
            and "tags" in self._meta.fields
            and self.user.has_perms(["core.view_tag"])
        ):
            fieldsets.append(
                Fieldset(
                    _("Tags"),
                    "tags",
                )
            )

        return Layout(*fieldsets)


class PrimaryModelForm(ColdFrontModelForm):
    """
    Form for models which inherit from PrimaryModel.
    """

    pass


class OrganizationalModelForm(ColdFrontModelForm):
    """
    Form for models which inherit from OrganizationalModel.
    """

    pass


class NestedGroupModelForm(ColdFrontModelForm):
    """
    Form for models which inherit from NestedGroupModel.
    """

    slug = SlugField()

    pass


class CSVModelForm(forms.ModelForm):
    """
    ModelForm used for the import of objects in CSV format.
    """

    id = forms.IntegerField(
        label=_("ID"),
        required=False,
        help_text=_("Numeric ID of an existing object to update (if not creating a new object)"),
    )

    def __init__(self, *args, headers=None, **kwargs):
        self.headers = headers or {}
        super().__init__(*args, **kwargs)

        # Modify the model form to accommodate any customized to_field_name properties
        for field, to_field in self.headers.items():
            if to_field is not None:
                self.fields[field].to_field_name = to_field

    def clean(self):
        # Flag any invalid CSV headers
        for header in self.headers:
            if header not in self.fields:
                raise forms.ValidationError(_("Unrecognized header: {name}").format(name=header))

        return super().clean()
