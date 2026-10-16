# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import json

from django import forms
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from django_jsonform.models.fields import JSONFormField

from coldfront.core.choices import CommentKindChoices, CustomFieldTypeChoices
from coldfront.core.models import (
    CommentEntry,
    CustomField,
    CustomFieldChoiceSet,
    CustomLink,
    ObjectType,
    SavedFilter,
    TableConfig,
    Tag,
)
from coldfront.forms import ColdFrontModelForm
from coldfront.forms.fields import (
    CommentField,
    ContentTypeChoiceField,
    ContentTypeMultipleChoiceField,
    DynamicModelChoiceField,
    JSONField,
    SimpleArrayField,
    SlugField,
)
from coldfront.forms.layout import FieldSet
from coldfront.forms.mixins import ChangelogMessageMixin
from coldfront.tables.utils import get_table_for_model
from coldfront.utils.forms import get_field_value


class TableConfigForm(ChangelogMessageMixin, forms.ModelForm):
    object_type = ContentTypeChoiceField(
        label=_("Object type"),
        queryset=ObjectType.objects.all(),
    )
    ordering = SimpleArrayField(
        base_field=forms.CharField(),
        required=False,
        label=_("Ordering"),
        help_text=_("Enter a comma-separated list of column names. Prepend a name with a hyphen to reverse the order."),
    )
    available_columns = SimpleArrayField(
        base_field=forms.CharField(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10, "class": "no-alpine-select h-64"}),
        label=_("Available Columns"),
    )
    columns = SimpleArrayField(
        base_field=forms.CharField(),
        widget=forms.SelectMultiple(attrs={"size": 10, "class": "no-alpine-select h-64", "data-select-all": True}),
        label=_("Selected Columns"),
    )

    class Meta:
        model = TableConfig
        exclude = ("user",)

    def __init__(self, data=None, *args, **kwargs):
        super().__init__(data, *args, **kwargs)

        self.fields["available_columns"].widget.choices = ()
        self.fields["columns"].widget.choices = ()

        # Table context may be absent e.g. when the add view is requested directly
        object_type_pk = get_field_value(self, "object_type")
        object_type_pk = getattr(object_type_pk, "pk", object_type_pk)
        if not object_type_pk:
            return

        try:
            object_type = ObjectType.objects.get(pk=object_type_pk)
        except (ObjectType.DoesNotExist, TypeError, ValueError):
            return

        model = object_type.model_class()
        if model is None:
            return

        table_name = get_field_value(self, "table")
        table_class = get_table_for_model(model, table_name)
        if table_class is None:
            return

        table = table_class([])

        if columns := self._get_columns():
            table._set_columns(columns)

        # Initialize columns field based on table attributes
        self.fields["available_columns"].widget.choices = table.available_columns
        self.fields["columns"].widget.choices = table.selected_columns

    def _get_columns(self):
        if self.is_bound and (columns := self.data.getlist("columns")):
            return columns
        if "columns" in self.initial:
            columns = self.get_initial_for_field(self.fields["columns"], "columns")
            return columns.split(",") if type(columns) is str else columns
        if self.instance is not None:
            return self.instance.columns
        return None

    fieldsets = (
        FieldSet(
            "name",
            "object_type",
            "table",
            "description",
            "weight",
            "enabled",
            "shared",
            "ordering",
            name=_("Table Configuration"),
        ),
    )


class SavedFilterForm(ChangelogMessageMixin, forms.ModelForm):
    slug = SlugField()
    object_types = ContentTypeMultipleChoiceField(
        label=_("Object types"),
        queryset=ObjectType.objects.public(),
    )
    parameters = JSONField()

    class Meta:
        model = SavedFilter
        exclude = ("user",)

    fieldsets = (
        FieldSet(
            "name",
            "slug",
            "object_types",
            "description",
            "weight",
            "enabled",
            "shared",
            name=_("Saved Filter"),
        ),
        FieldSet(
            "parameters",
            name=_("Parameters"),
        ),
    )

    def __init__(self, *args, initial=None, **kwargs):
        # Convert any parameters delivered via initial data to JSON data
        if initial and "parameters" in initial:
            if type(initial["parameters"]) is str:
                initial["parameters"] = json.loads(initial["parameters"])

        super().__init__(*args, initial=initial, **kwargs)


class TagForm(ChangelogMessageMixin, forms.ModelForm):
    slug = SlugField()
    object_types = ContentTypeMultipleChoiceField(
        label=_("Object types"),
        queryset=ObjectType.objects.with_feature("tags"),
        required=False,
    )

    class Meta:
        model = Tag
        fields = [
            "name",
            "slug",
            "color",
            "weight",
            "description",
            "object_types",
        ]

    fieldsets = (
        FieldSet(
            "name",
            "slug",
            "color",
            "weight",
            "description",
            "object_types",
            name=_("Tag"),
        ),
    )


class CustomFieldChoiceSetForm(ChangelogMessageMixin, forms.ModelForm):
    choices = JSONFormField(
        schema=CustomFieldChoiceSet.CHOICES_SCHEMA,
        help_text=mark_safe(
            _("An optional label may be specified for each choice by appending it with a colon. Example:")
            + " <code>choice1:First Choice</code>"
        ),
    )

    class Meta:
        model = CustomFieldChoiceSet
        fields = [
            "name",
            "description",
            "choices",
            "order_alphabetically",
        ]

    fieldsets = (
        FieldSet(
            "name",
            "description",
            "choices",
            "order_alphabetically",
            name=_("Custom Field Choice Set"),
        ),
    )


class CustomFieldForm(ChangelogMessageMixin, forms.ModelForm):
    object_types = ContentTypeMultipleChoiceField(
        label=_("Object types"),
        queryset=ObjectType.objects.with_feature("custom_fields"),
        help_text=_("The type(s) of object that have this custom field"),
    )
    default = JSONField(
        label=_("Default value"),
        required=False,
    )
    related_object_type = ContentTypeChoiceField(
        label=_("Related object type"),
        queryset=ObjectType.objects.public(),
        help_text=_("Type of the related object (for object/multi-object fields only)"),
    )
    related_object_filter = JSONField(
        label=_("Related object filter"),
        required=False,
        help_text=_("Specify query parameters as a JSON object."),
    )
    choice_set = DynamicModelChoiceField(
        queryset=CustomFieldChoiceSet.objects.all(),
        required=False,
    )

    comments = forms.CharField(required=False)

    fieldsets = (
        FieldSet(
            "object_types",
            "name",
            "label",
            "group_name",
            "description",
            "type",
            "required",
            "unique",
            "default",
            name=_("Custom Field"),
        ),
        FieldSet(
            "search_weight",
            "filter_logic",
            "ui_visible",
            "ui_editable",
            "required_action",
            "weight",
            "is_cloneable",
            name=_("Behavior"),
        ),
    )

    class Meta:
        model = CustomField
        fields = "__all__"
        help_texts = {
            "type": _(
                "The type of data stored in this field. For object/multi-object fields, select the related object "
                "type below."
            ),
            "description": _("This will be displayed as help text for the form field. Markdown is supported."),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Mimic RefreshSelect()
        self.fields["type"].widget.attrs.update(
            {
                "hx-get": ".",
                "hx-include": "#form_fields",
                "hx-target": "#form_fields",
            }
        )

        # Disable changing the type of a CustomField as it almost universally causes errors if custom field data
        # is already present.
        if self.instance.pk:
            self.fields["type"].disabled = True

        field_type = get_field_value(self, "type")

        # Adjust for text fields
        if field_type in (
            CustomFieldTypeChoices.TYPE_TEXT,
            CustomFieldTypeChoices.TYPE_LONGTEXT,
        ):
            self.fieldsets = (
                self.fieldsets[0],
                FieldSet(
                    "validation_regex",
                    name=_("Validation"),
                ),
                *self.fieldsets[1:],
            )
        else:
            del self.fields["validation_regex"]

        # Adjust for numeric fields
        if field_type in (CustomFieldTypeChoices.TYPE_INTEGER, CustomFieldTypeChoices.TYPE_DECIMAL):
            self.fieldsets = (
                self.fieldsets[0],
                FieldSet(
                    "validation_minimum",
                    "validation_maximum",
                    name=_("Validation"),
                ),
                *self.fieldsets[1:],
            )
        else:
            del self.fields["validation_minimum"]
            del self.fields["validation_maximum"]

        # Adjust for object & multi-object fields
        if field_type in (CustomFieldTypeChoices.TYPE_OBJECT, CustomFieldTypeChoices.TYPE_MULTIOBJECT):
            self.fieldsets = (
                self.fieldsets[0],
                FieldSet(
                    "related_object_type",
                    "related_object_filter",
                    name=_("Related Object"),
                ),
                *self.fieldsets[1:],
            )
        else:
            del self.fields["related_object_type"]
            del self.fields["related_object_filter"]

        # Adjust for selection & multi-select fields
        if field_type in (CustomFieldTypeChoices.TYPE_SELECT, CustomFieldTypeChoices.TYPE_MULTISELECT):
            self.fieldsets = (
                self.fieldsets[0],
                FieldSet(
                    "choice_set",
                    name=_("Choices"),
                ),
                *self.fieldsets[1:],
            )
        else:
            del self.fields["choice_set"]


class CustomLinkForm(ChangelogMessageMixin, forms.ModelForm):
    object_types = ContentTypeMultipleChoiceField(
        label=_("Object types"),
        queryset=ObjectType.objects.with_feature("custom_links"),
    )

    class Meta:
        model = CustomLink
        fields = "__all__"
        widgets = {
            "link_text": forms.Textarea(attrs={"class": "font-mono"}),
            "link_url": forms.Textarea(attrs={"class": "font-mono"}),
        }
        help_texts = {
            "link_text": _("Jinja2 template code for link text. Reference the object as {{ object }}."),
            "link_url": _("Jinja2 template code for link URL. Reference the object as {{ object }}."),
        }

    fieldsets = (
        FieldSet(
            "name",
            "object_types",
            "weight",
            "group_name",
            "button_variant",
            "enabled",
            "new_window",
            name=_("Custom Link"),
        ),
        FieldSet(
            "link_text",
            "link_url",
            name=_("Templates"),
        ),
    )


class CommentEntryForm(ColdFrontModelForm):
    kind = forms.ChoiceField(
        label=_("Kind"),
        choices=CommentKindChoices,
    )
    comments = CommentField(required=True)

    class Meta:
        model = CommentEntry
        fields = [
            "assigned_object_type",
            "assigned_object_id",
            "kind",
            "comments",
            "tags",
        ]
        widgets = {
            "assigned_object_type": forms.HiddenInput,
            "assigned_object_id": forms.HiddenInput,
        }

    fieldsets = (
        FieldSet(
            "assigned_object_type",
            "assigned_object_id",
            "kind",
            "comments",
            name=_("Add Comments"),
        ),
    )
