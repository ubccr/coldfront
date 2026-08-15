# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.db import models
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import CustomFieldUIEditableChoices
from coldfront.core.models import CustomField, Tag

from .fields import CSVModelMultipleChoiceField, SlugField
from .model_forms import ColdFrontModelForm, CSVModelForm


class ColdFrontModelImportForm(CSVModelForm, ColdFrontModelForm):
    """
    Base form for creating ColdFront objects from CSV data. Used for bulk importing.
    """

    tags = CSVModelMultipleChoiceField(
        label=_("Tags"),
        queryset=Tag.objects.all(),
        required=False,
        to_field_name="slug",
        help_text=_('Tag slugs separated by commas, encased with double quotes (e.g. "tag1,tag2,tag3")'),
    )

    def _get_custom_fields(self, content_type):
        # Return only custom fields that are editable in the UI
        return [
            cf
            for cf in CustomField.objects.get_for_model(content_type.model_class())
            if cf.ui_editable == CustomFieldUIEditableChoices.YES
        ]

    def _get_form_field(self, customfield):
        return customfield.to_form_field(for_csv_import=True)

    def clean(self):
        """
        Cleans data in a form, ensuring proper handling of model fields with `null=True`.
        Overrides the `clean` method from the parent form to process and sanitize cleaned
        data for defined fields in the associated model.
        """
        super().clean()
        cleaned = self.cleaned_data

        model = getattr(self._meta, "model", None)
        if not model:
            return cleaned

        for f in model._meta.get_fields():
            # Only forward, DB-backed fields (skip M2M & reverse relations)
            if not isinstance(f, models.Field) or not f.concrete or f.many_to_many:
                continue

            if getattr(f, "null", False):
                name = f.name
                if name not in cleaned:
                    continue
                val = cleaned[name]
                # Only coerce empty strings; leave other types alone
                if isinstance(val, str) and val.strip() == "":
                    cleaned[name] = None

        return cleaned


class PrimaryModelImportForm(ColdFrontModelImportForm):
    """
    Bulk import form for models which inherit from PrimaryModel.
    """

    pass


class OrganizationalModelImportForm(ColdFrontModelImportForm):
    """
    Bulk import form for models which inherit from OrganizationalModel.
    """


class NestedGroupModelImportForm(ColdFrontModelImportForm):
    """
    Bulk import form for models which inherit from NestedGroupModel.
    """

    slug = SlugField()
