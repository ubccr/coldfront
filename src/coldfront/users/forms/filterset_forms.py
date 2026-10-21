# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.lib.constants import BOOLEAN_WITH_BLANK_CHOICES
from coldfront.lib.forms import ColdFrontModelFilterSetForm
from coldfront.lib.forms.layout import FieldSet
from coldfront.ras.models import Project
from coldfront.users.models import Group, ObjectPermission, Role, Token, User


class GroupFilterSetForm(ColdFrontModelFilterSetForm):
    name = forms.CharField(
        label=_("Name"),
        required=False,
    )
    description = forms.CharField(
        label=_("Description"),
        required=False,
    )

    model = Group
    fieldsets = (
        FieldSet(
            "q",
        ),
        FieldSet(
            "name",
            "description",
            name=_("Group"),
        ),
    )


class UserFilterSetForm(ColdFrontModelFilterSetForm):
    project_id = forms.ModelMultipleChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label=_("Project"),
    )
    group_id = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label=_("Group"),
    )
    is_active = forms.NullBooleanField(
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
        label=_("Is Active"),
    )
    is_superuser = forms.NullBooleanField(
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
        label=_("Is Superuser"),
    )

    model = User
    fieldsets = (
        FieldSet(
            "q",
        ),
        FieldSet(
            "group_id",
            "project_id",
            name=_("User"),
        ),
        FieldSet(
            "is_active",
            "is_superuser",
            name=_("Status"),
        ),
    )


class RoleFilterSetForm(ColdFrontModelFilterSetForm):
    name = forms.CharField(
        label=_("Name"),
        required=False,
    )
    description = forms.CharField(
        label=_("Description"),
        required=False,
    )

    model = Role
    fieldsets = (
        FieldSet(
            "q",
        ),
        FieldSet(
            "name",
            "description",
            name=_("Role"),
        ),
    )


class ObjectPermissionFilterSetForm(ColdFrontModelFilterSetForm):
    enabled = forms.NullBooleanField(
        label=_("Enabled"), required=False, widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES)
    )
    group_id = forms.ModelMultipleChoiceField(
        queryset=Group.objects.all(),
        required=False,
        label=_("Group"),
    )
    user_id = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("User"),
    )
    can_view = forms.NullBooleanField(
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
        label=_("Can View"),
    )
    can_add = forms.NullBooleanField(
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
        label=_("Can Add"),
    )
    can_change = forms.NullBooleanField(
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
        label=_("Can Change"),
    )
    can_delete = forms.NullBooleanField(
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
        label=_("Can Delete"),
    )

    model = ObjectPermission
    fieldsets = (
        FieldSet(
            "q",
        ),
        FieldSet(
            "enabled",
            "group_id",
            "user_id",
            name=_("Permission"),
        ),
        FieldSet(
            "can_view",
            "can_add",
            "can_change",
            "can_delete",
            name=_("Actions"),
        ),
    )


class TokenFilterSetForm(ColdFrontModelFilterSetForm):
    user_id = forms.ModelMultipleChoiceField(
        queryset=User.objects.all(),
        required=False,
        label=_("User"),
    )
    enabled = forms.NullBooleanField(
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
        label=_("Enabled"),
    )
    write_enabled = forms.NullBooleanField(
        required=False,
        widget=forms.Select(choices=BOOLEAN_WITH_BLANK_CHOICES),
        label=_("Write Enabled"),
    )
    expires = forms.DateTimeField(
        required=False,
        label=_("Expires"),
    )
    last_used = forms.DateTimeField(
        required=False,
        label=_("Last Used"),
    )

    model = Token
    fieldsets = (
        FieldSet(
            "q",
        ),
        FieldSet(
            "user_id",
            "enabled",
            "write_enabled",
            "expires",
            "last_used",
            name=_("Token"),
        ),
    )
