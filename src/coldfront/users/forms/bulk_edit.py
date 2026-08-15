# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.forms import BulkEditForm
from coldfront.forms.fields import DynamicModelMultipleChoiceField
from coldfront.forms.mixins import HorizontalFormMixin
from coldfront.forms.widgets import BulkEditNullBooleanSelect
from coldfront.users.models import Group, ObjectPermission, Role, Token, User

#
# Users
#


class UserBulkEditForm(HorizontalFormMixin, BulkEditForm):
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
            Fieldset(
                _("User"),
                "first_name",
                "last_name",
                "email",
            ),
            Fieldset(
                _("Status"),
                "is_active",
            ),
            Fieldset(
                _("Groups"),
                "add_groups",
                "remove_groups",
            ),
        ]


#
# Groups
#


class GroupBulkEditForm(HorizontalFormMixin, BulkEditForm):
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
            Fieldset(
                _("Group"),
                "description",
            ),
        ]


#
# ObjectPermissions
#


class RoleBulkEditForm(HorizontalFormMixin, BulkEditForm):
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
            Fieldset(
                _("Role"),
                "description",
                "weight",
            ),
        ]


class ObjectPermissionBulkEditForm(HorizontalFormMixin, BulkEditForm):
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
            Fieldset(
                _("Object Permission"),
                "description",
                "enabled",
            ),
        ]


#
# Tokens
#


class TokenBulkEditForm(HorizontalFormMixin, BulkEditForm):
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
            Fieldset(
                _("Token"),
                "description",
                "enabled",
                "write_enabled",
            ),
        ]
