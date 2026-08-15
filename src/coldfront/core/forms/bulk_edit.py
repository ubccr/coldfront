# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.core.choices import (
    ColorChoices,
    CommentKindChoices,
    CustomFieldUIEditableChoices,
    CustomFieldUIVisibleChoices,
    CustomLinkButtonClassChoices,
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
from coldfront.forms import ColdFrontModelBulkEditForm
from coldfront.forms.fields import CommentField
from coldfront.forms.widgets.select import BulkEditNullBooleanSelect
from coldfront.utils.forms import add_blank_choice

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
            Fieldset(
                _("Custom Field Choice Set"),
                "description",
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
            Fieldset(
                _("Custom Field"),
                "label",
                "description",
                "group_name",
            ),
            Fieldset(
                _("Behavior"),
                "required",
                "search_weight",
                "weight",
                "ui_visible",
                "ui_editable",
                "is_cloneable",
            ),
        ]


#
# Tags
#


class TagBulkEditForm(ColdFrontModelBulkEditForm):
    color = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.Select(
            choices=add_blank_choice(ColorChoices),
            attrs={"class": "color-select"},
        ),
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
            Fieldset(
                _("Tag"),
                "color",
                "weight",
                "description",
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
            Fieldset(
                _("Saved Filter"),
                "description",
                "weight",
                "enabled",
                "shared",
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
            Fieldset(
                _("Tag"),
                "description",
                "weight",
                "enabled",
                "shared",
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
    button_class = forms.ChoiceField(
        choices=add_blank_choice(CustomLinkButtonClassChoices),
        required=False,
        label=_("Button class"),
    )
    new_window = forms.NullBooleanField(
        label=_("New window"),
        required=False,
        widget=BulkEditNullBooleanSelect,
    )
    link_text = forms.CharField(
        label=_("Link text"),
        widget=forms.Textarea(attrs={"class": "font-monospace"}),
        required=False,
    )
    link_url = forms.CharField(
        label=_("Link URL"),
        widget=forms.Textarea(attrs={"class": "font-monospace"}),
        required=False,
    )

    model = CustomLink
    nullable_fields = ("group_name", "link_text", "link_url")

    @property
    def fieldsets(self):
        return [
            Fieldset(
                _("Custom Link"),
                "enabled",
                "weight",
                "group_name",
                "button_class",
                "new_window",
            ),
            Fieldset(
                _("Templates"),
                "link_text",
                "link_url",
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
            Fieldset(
                _("Comment Entry"),
                "kind",
                "comments",
            ),
        ]
