# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import (
    CommentKindChoices,
    CustomFieldUIEditableChoices,
    CustomFieldUIVisibleChoices,
)
from coldfront.core.models import (
    CommentEntry,
    CustomField,
    CustomFieldChoiceSet,
    CustomLink,
    SavedFilter,
    TableConfig,
    Tag,
)
from coldfront.lib.forms import ColdFrontModelBulkEditForm, add_blank_choice
from coldfront.lib.forms.fields import ColorChoiceField, CommentField
from coldfront.lib.forms.layout import FieldSet
from coldfront.lib.forms.widgets import BulkEditNullBooleanSelect

#
# Custom Field Choice Sets
#


class CustomFieldChoiceSetBulkEditForm(ColdFrontModelBulkEditForm):
    description = forms.CharField(
        label=_("Description"),
        max_length=200,
        required=False,
    )

    model = CustomFieldChoiceSet
    nullable_fields = ("description",)

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "description",
                name=_("Custom Field Choice Set"),
            ),
        ]


#
# Custom Fields
#


class CustomFieldBulkEditForm(ColdFrontModelBulkEditForm):
    label = forms.CharField(
        label=_("Label"),
        max_length=50,
        required=False,
    )
    description = forms.CharField(
        label=_("Description"),
        max_length=200,
        required=False,
    )
    group_name = forms.CharField(
        label=_("Group Name"),
        max_length=50,
        required=False,
    )
    required = forms.BooleanField(
        label=_("Required"),
        required=False,
    )
    search_weight = forms.IntegerField(
        label=_("Search Weight"),
        required=False,
    )
    weight = forms.IntegerField(
        label=_("Display Weight"),
        required=False,
    )
    ui_visible = forms.ChoiceField(
        choices=add_blank_choice(CustomFieldUIVisibleChoices),
        required=False,
        label=_("UI Visible"),
    )
    ui_editable = forms.ChoiceField(
        choices=add_blank_choice(CustomFieldUIEditableChoices),
        required=False,
        label=_("UI Editable"),
    )
    is_cloneable = forms.BooleanField(
        label=_("Cloneable"),
        required=False,
    )

    model = CustomField
    nullable_fields = (
        "label",
        "description",
        "group_name",
        "required",
        "search_weight",
        "weight",
        "ui_visible",
        "ui_editable",
        "is_cloneable",
    )

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "label",
                "description",
                "group_name",
                name=_("Custom Field"),
            ),
            FieldSet(
                "required",
                "search_weight",
                "weight",
                "ui_visible",
                "ui_editable",
                "is_cloneable",
                name=_("Behavior"),
            ),
        ]


#
# Tags
#


class TagBulkEditForm(ColdFrontModelBulkEditForm):
    color = ColorChoiceField(
        required=False,
        label=_("Color"),
    )
    weight = forms.IntegerField(
        required=False,
        label=_("Weight"),
    )
    description = forms.CharField(
        label=_("Description"),
        max_length=200,
        required=False,
    )

    model = Tag
    nullable_fields = (
        "color",
        "weight",
        "description",
    )

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "color",
                "weight",
                "description",
                name=_("Tag"),
            ),
        ]


class SavedFilterBulkEditForm(ColdFrontModelBulkEditForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=SavedFilter.objects.all(),
        widget=forms.MultipleHiddenInput,
    )
    description = forms.CharField(
        label=_("Description"),
        max_length=200,
        required=False,
    )
    weight = forms.IntegerField(
        label=_("Weight"),
        required=False,
    )
    enabled = forms.NullBooleanField(
        label=_("Enabled"),
        required=False,
        widget=BulkEditNullBooleanSelect,
    )
    shared = forms.NullBooleanField(
        label=_("Shared"),
        required=False,
        widget=BulkEditNullBooleanSelect,
    )

    model = SavedFilter
    nullable_fields = ("description",)

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "description",
                "weight",
                "enabled",
                "shared",
                name=_("Saved Filter"),
            ),
        ]


class TableConfigBulkEditForm(ColdFrontModelBulkEditForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=TableConfig.objects.all(),
        widget=forms.MultipleHiddenInput,
    )
    description = forms.CharField(
        label=_("Description"),
        max_length=200,
        required=False,
    )
    weight = forms.IntegerField(
        label=_("Weight"),
        required=False,
    )
    enabled = forms.NullBooleanField(
        label=_("Enabled"),
        required=False,
        widget=BulkEditNullBooleanSelect,
    )
    shared = forms.NullBooleanField(
        label=_("Shared"),
        required=False,
        widget=BulkEditNullBooleanSelect,
    )

    model = TableConfig
    nullable_fields = ("description",)

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "description",
                "weight",
                "enabled",
                "shared",
                name=_("Tag"),
            ),
        ]


class CustomLinkBulkEditForm(ColdFrontModelBulkEditForm):
    enabled = forms.NullBooleanField(
        label=_("Enabled"),
        required=False,
        widget=BulkEditNullBooleanSelect,
    )
    weight = forms.IntegerField(
        label=_("Weight"),
        required=False,
    )
    group_name = forms.CharField(
        label=_("Group name"),
        max_length=50,
        required=False,
    )
    button_variant = ColorChoiceField(
        required=False,
        label=_("Button variant"),
    )
    new_window = forms.NullBooleanField(
        label=_("New window"),
        required=False,
        widget=BulkEditNullBooleanSelect,
    )
    link_text = forms.CharField(
        label=_("Link text"),
        widget=forms.Textarea(attrs={"class": "font-mono"}),
        required=False,
    )
    link_url = forms.CharField(
        label=_("Link URL"),
        widget=forms.Textarea(attrs={"class": "font-mono"}),
        required=False,
    )

    model = CustomLink
    nullable_fields = ("group_name", "link_text", "link_url")

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "enabled",
                "weight",
                "group_name",
                "button_variant",
                "new_window",
                name=_("Custom Link"),
            ),
            FieldSet(
                "link_text",
                "link_url",
                name=_("Templates"),
            ),
        ]


class CommentEntryBulkEditForm(ColdFrontModelBulkEditForm):
    kind = forms.ChoiceField(
        label=_("Kind"),
        choices=add_blank_choice(CommentKindChoices),
        required=False,
    )
    comments = CommentField(required=False)

    model = CommentEntry
    nullable_fields = ()

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "kind",
                "comments",
                name=_("Comment Entry"),
            ),
        ]
