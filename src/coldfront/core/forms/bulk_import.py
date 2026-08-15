# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import (
    CommentKindChoices,
    CustomFieldTypeChoices,
    CustomFieldUIEditableChoices,
    CustomFieldUIVisibleChoices,
    CustomLinkButtonClassChoices,
)
from coldfront.core.models import (
    CommentEntry,
    CustomField,
    CustomFieldChoiceSet,
    CustomLink,
    ObjectType,
    SavedFilter,
    Tag,
)
from coldfront.forms import CSVModelForm
from coldfront.forms.fields import (
    CSVChoiceField,
    CSVContentTypeField,
    CSVModelChoiceField,
    CSVMultipleContentTypeField,
    SlugField,
)
from coldfront.users.models import User


class SavedFilterImportForm(CSVModelForm):
    slug = SlugField()
    object_types = CSVMultipleContentTypeField(
        label=_("Object types"),
        queryset=ObjectType.objects.public(),
        help_text=_("One or more assigned object types"),
    )

    class Meta:
        model = SavedFilter
        fields = (
            "name",
            "slug",
            "object_types",
            "description",
            "weight",
            "enabled",
            "shared",
            "parameters",
        )


class CustomFieldImportForm(CSVModelForm):
    object_types = CSVMultipleContentTypeField(
        label=_("Object types"),
        queryset=ObjectType.objects.with_feature("custom_fields"),
        help_text=_("One or more assigned object types"),
    )
    type = CSVChoiceField(
        label=_("Type"), choices=CustomFieldTypeChoices, help_text=_("Field data type (e.g. text, integer, etc.)")
    )
    related_object_type = CSVContentTypeField(
        label=_("Object type"),
        queryset=ObjectType.objects.public(),
        required=False,
        help_text=_("Object type (for object or multi-object fields)"),
    )
    choice_set = CSVModelChoiceField(
        label=_("Choice set"),
        queryset=CustomFieldChoiceSet.objects.all(),
        to_field_name="name",
        required=False,
        help_text=_("Choice set (for selection fields)"),
    )
    ui_visible = CSVChoiceField(
        label=_("UI visible"),
        choices=CustomFieldUIVisibleChoices,
        required=False,
        help_text=_("Whether the custom field is displayed in the UI"),
    )
    ui_editable = CSVChoiceField(
        label=_("UI editable"),
        choices=CustomFieldUIEditableChoices,
        required=False,
        help_text=_("Whether the custom field is editable in the UI"),
    )

    class Meta:
        model = CustomField
        fields = (
            "name",
            "label",
            "group_name",
            "type",
            "object_types",
            "related_object_type",
            "required",
            "unique",
            "description",
            "search_weight",
            "filter_logic",
            "default",
            "choice_set",
            "weight",
            "validation_minimum",
            "validation_maximum",
            "validation_regex",
            "ui_visible",
            "ui_editable",
            "is_cloneable",
        )


class CustomFieldChoiceSetImportForm(CSVModelForm):
    choices = forms.CharField(
        required=False,
        help_text=_(
            "Quoted string of comma-separated field choices with optional labels separated by colon: "
            '"choice1:First Choice,choice2:Second Choice"'
        ),
    )

    class Meta:
        model = CustomFieldChoiceSet
        fields = (
            "name",
            "description",
            "choices",
            "order_alphabetically",
        )

    def clean_choices(self):
        if isinstance(self.cleaned_data["choices"], str):
            data = []
            line = self.cleaned_data["choices"]
            try:
                choices = line.split(",")
                for c in choices:
                    data.append(c)
            except ValueError:
                raise forms.ValidationError(_("Invalid choices string"))

            return data
        return None


class TagImportForm(CSVModelForm):
    slug = SlugField()
    object_types = CSVMultipleContentTypeField(
        label=_("Object types"),
        queryset=ObjectType.objects.with_feature("tags"),
        help_text=_("One or more assigned object types"),
        required=False,
    )

    class Meta:
        model = Tag
        fields = (
            "name",
            "slug",
            "color",
            "weight",
            "description",
            "object_types",
        )


class CustomLinkImportForm(CSVModelForm):
    object_types = CSVMultipleContentTypeField(
        label=_("Object types"),
        queryset=ObjectType.objects.public(),
        help_text=_("One or more assigned object types"),
    )
    button_class = CSVChoiceField(
        label=_("Button class"),
        choices=CustomLinkButtonClassChoices,
        required=False,
        help_text=_("Button color class"),
    )

    class Meta:
        model = CustomLink
        fields = (
            "name",
            "object_types",
            "enabled",
            "link_text",
            "link_url",
            "weight",
            "group_name",
            "button_class",
            "new_window",
        )


class CommentEntryImportForm(CSVModelForm):
    kind = CSVChoiceField(
        label=_("Kind"),
        choices=CommentKindChoices,
        required=False,
        help_text=_("Comment entry kind"),
    )
    comments = forms.CharField(
        label=_("Comments"),
        required=True,
    )
    assigned_object_type = CSVContentTypeField(
        label=_("Object type"),
        queryset=ObjectType.objects.all(),
        required=True,
    )
    assigned_object_id = forms.IntegerField(
        label=_("Object ID"),
        required=True,
    )
    created_by = CSVModelChoiceField(
        label=_("Created by"),
        queryset=User.objects.all(),
        required=False,
        to_field_name="username",
        help_text=_("User who created this comment entry"),
    )

    class Meta:
        model = CommentEntry
        fields = (
            "assigned_object_type",
            "assigned_object_id",
            "kind",
            "comments",
            "created_by",
        )
