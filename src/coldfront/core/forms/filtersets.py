# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.constants import BOOLEAN_WITH_BLANK_CHOICES
from coldfront.core.choices import (
    CommentKindChoices,
    CustomFieldTypeChoices,
    CustomFieldUIEditableChoices,
    CustomFieldUIVisibleChoices,
    JobStatusChoices,
    ObjectChangeActionChoices,
)
from coldfront.core.models import (
    CommentEntry,
    CustomField,
    CustomFieldChoiceSet,
    CustomLink,
    Job,
    ObjectChange,
    ObjectType,
    SavedFilter,
    TableConfig,
    Tag,
)
from coldfront.forms import PrimaryModelFilterSetForm
from coldfront.forms.fields import (
    ContentTypeChoiceField,
    ContentTypeMultipleChoiceField,
    DynamicModelMultipleChoiceField,
)
from coldfront.forms.layouts import DateTime
from coldfront.users.models import User
from coldfront.utils.forms import add_blank_choice


class SavedFilterFilterForm(PrimaryModelFilterSetForm):
    model = SavedFilter
    fieldsets = (
        Fieldset(
            "Saved Filter",
            "object_type_id",
            "enabled",
            "shared",
            "weight",
            name=_("Attributes"),
        ),
    )
    object_type_id = ContentTypeMultipleChoiceField(
        label=_("Object types"),
        queryset=ObjectType.objects.public(),
        required=False,
    )
    enabled = forms.NullBooleanField(
        label=_("Enabled"),
        required=False,
        widget=forms.Select(
            choices=BOOLEAN_WITH_BLANK_CHOICES,
        ),
    )
    shared = forms.NullBooleanField(
        label=_("Shared"),
        required=False,
        widget=forms.Select(
            choices=BOOLEAN_WITH_BLANK_CHOICES,
        ),
    )
    weight = forms.IntegerField(
        label=_("Weight"),
        required=False,
    )


class JobFilterForm(PrimaryModelFilterSetForm):
    model = Job
    status = forms.MultipleChoiceField(
        choices=JobStatusChoices,
        required=False,
        label=_("Status"),
    )

    fieldsets = (
        Fieldset(
            "Job",
            "status",
        ),
    )


class TagFilterForm(PrimaryModelFilterSetForm):
    model = Tag
    content_type_id = ContentTypeMultipleChoiceField(
        queryset=ObjectType.objects.with_feature("tags"),
        required=False,
        label=_("Tagged object type"),
    )
    for_object_type_id = ContentTypeChoiceField(
        queryset=ObjectType.objects.with_feature("tags"),
        required=False,
        label=_("Allowed object type"),
    )

    fieldsets = (
        Fieldset(
            "Tag",
            "content_type_id",
            "for_object_type_id",
        ),
    )


class ObjectChangeFilterForm(PrimaryModelFilterSetForm):
    model = ObjectChange
    time_after = forms.DateTimeField(
        required=False,
        label=_("After"),
    )
    time_before = forms.DateTimeField(
        required=False,
        label=_("Before"),
    )
    action = forms.ChoiceField(
        label=_("Action"),
        choices=add_blank_choice(ObjectChangeActionChoices),
        required=False,
    )
    user_id = forms.ModelChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("User"),
    )
    changed_object_type_id = ContentTypeMultipleChoiceField(
        queryset=ObjectType.objects.with_feature("change_logging"),
        required=False,
        label=_("Object Type"),
    )

    fieldsets = (
        Fieldset(
            "Time",
            DateTime("time_before"),
            DateTime("time_after"),
        ),
        Fieldset(
            "Attributes",
            "action",
            "user_id",
            "changed_object_type_id",
        ),
    )


class TableConfigFilterForm(PrimaryModelFilterSetForm):
    model = TableConfig
    fieldsets = (
        Fieldset(
            "Table Config",
            "object_type_id",
            "enabled",
            "shared",
            "weight",
            name=_("Attributes"),
        ),
    )
    object_type_id = ContentTypeMultipleChoiceField(
        label=_("Object types"),
        queryset=ObjectType.objects.public(),
        required=False,
    )
    enabled = forms.NullBooleanField(
        label=_("Enabled"),
        required=False,
        widget=forms.Select(
            choices=BOOLEAN_WITH_BLANK_CHOICES,
        ),
    )
    shared = forms.NullBooleanField(
        label=_("Shared"),
        required=False,
        widget=forms.Select(
            choices=BOOLEAN_WITH_BLANK_CHOICES,
        ),
    )
    weight = forms.IntegerField(
        label=_("Weight"),
        required=False,
    )


class CustomFieldChoiceSetFilterForm(PrimaryModelFilterSetForm):
    model = CustomFieldChoiceSet
    choice = forms.CharField(required=False)

    fieldsets = (
        Fieldset(
            "Choices",
            "choice",
        ),
    )


class CustomFieldFilterForm(PrimaryModelFilterSetForm):
    model = CustomField
    object_type_id = ContentTypeMultipleChoiceField(
        queryset=ObjectType.objects.with_feature("custom_fields"),
        required=False,
        label=_("Object types"),
    )
    related_object_type_id = ContentTypeMultipleChoiceField(
        queryset=ObjectType.objects.public(),
        required=False,
        label=_("Related object type"),
    )
    type = forms.MultipleChoiceField(
        choices=CustomFieldTypeChoices,
        required=False,
        label=_("Field type"),
    )
    group_name = forms.CharField(
        label=_("Group name"),
        required=False,
    )
    weight = forms.IntegerField(
        label=_("Weight"),
        required=False,
    )
    required = forms.NullBooleanField(
        label=_("Required"),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    unique = forms.NullBooleanField(
        label=_("Must be unique"),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    choice_set_id = forms.ModelMultipleChoiceField(
        queryset=CustomFieldChoiceSet.objects.all(),
        required=False,
        label=_("Choice set"),
    )
    ui_visible = forms.ChoiceField(
        choices=add_blank_choice(CustomFieldUIVisibleChoices),
        required=False,
        label=_("UI visible"),
    )
    ui_editable = forms.ChoiceField(
        choices=add_blank_choice(CustomFieldUIEditableChoices),
        required=False,
        label=_("UI editable"),
    )
    is_cloneable = forms.NullBooleanField(
        label=_("Is cloneable"),
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
    )
    validation_minimum = forms.DecimalField(
        label=_("Minimum value"),
        required=False,
    )
    validation_maximum = forms.DecimalField(
        label=_("Maximum value"),
        required=False,
    )
    validation_regex = forms.CharField(
        label=_("Validation regex"),
        required=False,
    )

    fieldsets = (
        Fieldset(
            "Attributes",
            "object_type_id",
            "type",
            "group_name",
            "weight",
            "required",
            "unique",
        ),
        Fieldset(
            "Type Options",
            "choice_set_id",
            "related_object_type_id",
        ),
        Fieldset(
            "Behavior",
            "ui_visible",
            "ui_editable",
            "is_cloneable",
        ),
        Fieldset(
            "Validation",
            "validation_minimum",
            "validation_maximum",
            "validation_regex",
        ),
    )


class CustomLinkFilterForm(PrimaryModelFilterSetForm):
    model = CustomLink
    fieldsets = (
        Fieldset(
            _("Attributes"),
            "object_type_id",
            "enabled",
            "new_window",
            "weight",
        ),
    )
    object_type_id = ContentTypeMultipleChoiceField(
        label=_("Object types"),
        queryset=ObjectType.objects.public(),
        required=False,
    )
    enabled = forms.NullBooleanField(
        label=_("Enabled"),
        required=False,
        widget=forms.Select(
            choices=BOOLEAN_WITH_BLANK_CHOICES,
        ),
    )
    new_window = forms.NullBooleanField(
        label=_("New window"),
        required=False,
        widget=forms.Select(
            choices=BOOLEAN_WITH_BLANK_CHOICES,
        ),
    )
    weight = forms.IntegerField(
        label=_("Weight"),
        required=False,
    )


class CommentEntryFilterForm(PrimaryModelFilterSetForm):
    created_after = forms.DateTimeField(
        required=False,
        label=_("After"),
    )
    created_before = forms.DateTimeField(
        required=False,
        label=_("Before"),
    )
    created_by_id = DynamicModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("User"),
    )
    assigned_object_type_id = ContentTypeMultipleChoiceField(
        queryset=ObjectType.objects.with_feature("commenting"),
        required=False,
        label=_("Object Type"),
    )
    kind = forms.ChoiceField(
        label=_("Kind"),
        choices=add_blank_choice(CommentKindChoices),
        required=False,
    )

    model = CommentEntry
    fieldsets = (
        Fieldset(
            "Comment Entry",
            DateTime("created_before"),
            DateTime("created_after"),
            "created_by_id",
        ),
        Fieldset(
            "Attributes",
            "assigned_object_type_id",
            "kind",
        ),
    )
