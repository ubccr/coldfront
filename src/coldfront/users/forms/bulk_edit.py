# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.lib.forms import BulkEditForm
from coldfront.lib.forms.fields import DynamicModelMultipleChoiceField
from coldfront.lib.forms.layout import FieldSet
from coldfront.lib.forms.widgets import BulkEditNullBooleanSelect
from coldfront.users.models import Group, ObjectPermission, Role, Token, User

#
# Users
#


class UserBulkEditForm(BulkEditForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        widget=forms.MultipleHiddenInput,
    )
    first_name = forms.CharField(
        label=_("First name"),
        max_length=150,
        required=False,
    )
    last_name = forms.CharField(
        label=_("Last name"),
        max_length=150,
        required=False,
    )
    email = forms.EmailField(
        label=_("Email"),
        required=False,
    )
    is_active = forms.NullBooleanField(
        label=_("Active"),
        widget=BulkEditNullBooleanSelect,
        required=False,
    )
    add_groups = DynamicModelMultipleChoiceField(
        label=_("Add groups"),
        queryset=Group.objects.all(),
        required=False,
    )
    remove_groups = DynamicModelMultipleChoiceField(
        label=_("Remove groups"),
        queryset=Group.objects.all(),
        required=False,
    )

    model = User
    nullable_fields = ("first_name", "last_name", "email")

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "first_name",
                "last_name",
                "email",
                name=_("User"),
            ),
            FieldSet(
                "is_active",
                name=_("Status"),
            ),
            FieldSet(
                "add_groups",
                "remove_groups",
                name=_("Groups"),
            ),
        ]


#
# Groups
#


class GroupBulkEditForm(BulkEditForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        widget=forms.MultipleHiddenInput,
    )
    description = forms.CharField(
        label=_("Description"),
        max_length=200,
        required=False,
    )

    model = Group
    nullable_fields = ("description",)

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "description",
                name=_("Group"),
            ),
        ]


#
# ObjectPermissions
#


class RoleBulkEditForm(BulkEditForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=Role.objects.all(),
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

    model = Role
    nullable_fields = ("description",)

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "description",
                "weight",
                name=_("Role"),
            ),
        ]


class ObjectPermissionBulkEditForm(BulkEditForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=ObjectPermission.objects.all(),
        widget=forms.MultipleHiddenInput,
    )
    description = forms.CharField(
        label=_("Description"),
        max_length=200,
        required=False,
    )
    enabled = forms.NullBooleanField(
        label=_("Enabled"),
        widget=BulkEditNullBooleanSelect,
        required=False,
    )

    model = ObjectPermission
    nullable_fields = ("description",)

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "description",
                "enabled",
                name=_("Object Permission"),
            ),
        ]


#
# Tokens
#


class TokenBulkEditForm(BulkEditForm):
    pk = forms.ModelMultipleChoiceField(
        queryset=Token.objects.all(),
        widget=forms.MultipleHiddenInput,
    )
    description = forms.CharField(
        label=_("Description"),
        max_length=200,
        required=False,
    )
    enabled = forms.NullBooleanField(
        label=_("Enabled"),
        widget=BulkEditNullBooleanSelect,
        required=False,
    )
    write_enabled = forms.NullBooleanField(
        label=_("Write enabled"),
        widget=BulkEditNullBooleanSelect,
        required=False,
    )

    model = Token
    nullable_fields = ("description",)

    @property
    def fieldsets(self):
        return [
            FieldSet(
                "description",
                "enabled",
                "write_enabled",
                name=_("Token"),
            ),
        ]
