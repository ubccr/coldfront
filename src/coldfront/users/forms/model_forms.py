# SPDX-FileCopyrightText: (C) DigitalOcean, LLC
# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import json

from crispy_forms.layout import Fieldset, Layout
from django import forms
from django.contrib.auth import password_validation
from django.core.exceptions import FieldError
from django.utils.translation import gettext_lazy as _

from coldfront.core.models import ObjectType
from coldfront.forms.fields import (
    ContentTypeMultipleChoiceField,
    DynamicModelMultipleChoiceField,
    JSONField,
)
from coldfront.forms.layouts import CopyClipboard, DateTime
from coldfront.forms.mixins import HorizontalFormMixin
from coldfront.registry import registry
from coldfront.users.constants import CONSTRAINT_TOKEN_USER, OBJECTPERMISSION_OBJECT_TYPES, RESERVED_ACTIONS
from coldfront.users.models import Group, ObjectPermission, Role, Token, User
from coldfront.users.permissions import qs_filter_from_constraints


class UserForm(HorizontalFormMixin, forms.ModelForm):
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(),
        required=True,
    )
    confirm_password = forms.CharField(
        label=_("Confirm password"),
        widget=forms.PasswordInput(),
        required=True,
        help_text=_("Enter the same password as before, for verification."),
    )
    groups = DynamicModelMultipleChoiceField(
        label=_("Groups"),
        required=False,
        queryset=Group.objects.all(),
    )
    roles = DynamicModelMultipleChoiceField(
        label=_("Roles"),
        required=False,
        queryset=Role.objects.all(),
    )
    object_permissions = DynamicModelMultipleChoiceField(
        required=False,
        label=_("Permissions"),
        queryset=ObjectPermission.objects.all(),
    )

    fieldsets = (
        Fieldset(
            _("User"),
            "username",
            "password",
            "confirm_password",
            "first_name",
            "last_name",
            "email",
        ),
        Fieldset(
            _("Groups"),
            "groups",
        ),
        Fieldset(
            _("Status"),
            "is_active",
            "is_superuser",
        ),
        Fieldset(
            _("Roles"),
            "roles",
        ),
        Fieldset(
            _("Permissions"),
            "object_permissions",
        ),
    )

    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "groups",
            "roles",
            "object_permissions",
            "is_active",
            "is_superuser",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            # Password fields are optional for existing Users
            self.fields["password"].required = False
            self.fields["confirm_password"].required = False

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        # On edit, check if we have to save the password
        if self.cleaned_data.get("password"):
            instance.set_password(self.cleaned_data.get("password"))
            instance.save()

        return instance

    def clean(self):

        # Check that password confirmation matches if password is set
        if self.cleaned_data["password"] and self.cleaned_data["password"] != self.cleaned_data["confirm_password"]:
            raise forms.ValidationError(_("Passwords do not match! Please check your input and try again."))

        # Enforce password validation rules (if configured)
        if self.cleaned_data["password"]:
            password_validation.validate_password(self.cleaned_data["password"], self.instance)


class GroupForm(HorizontalFormMixin, forms.ModelForm):
    users = DynamicModelMultipleChoiceField(
        label=_("Users"),
        required=False,
        queryset=User.objects.all(),
    )
    roles = DynamicModelMultipleChoiceField(
        label=_("Roles"),
        required=False,
        queryset=Role.objects.all(),
    )
    object_permissions = DynamicModelMultipleChoiceField(
        required=False,
        label=_("Permissions"),
        queryset=ObjectPermission.objects.all(),
    )

    fieldsets = (
        Fieldset(
            _("Group"),
            "name",
            "description",
        ),
        Fieldset(
            _("Users"),
            "users",
        ),
        Fieldset(
            _("Roles"),
            "roles",
        ),
        Fieldset(
            _("Permissions"),
            "object_permissions",
        ),
    )

    class Meta:
        model = Group
        fields = [
            "name",
            "description",
            "users",
            "roles",
            "object_permissions",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate assigned users and permissions
        if self.instance.pk:
            self.fields["users"].initial = self.instance.users.values_list("id", flat=True)
            self.fields["roles"].initial = self.instance.roles.values_list("id", flat=True)

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        # Update assigned users and roles
        instance.users.set(self.cleaned_data["users"])
        instance.roles.set(self.cleaned_data["roles"])

        return instance


class ObjectPermissionForm(HorizontalFormMixin, forms.ModelForm):
    object_types = ContentTypeMultipleChoiceField(
        label=_("Object types"),
        queryset=ObjectType.objects.filter(OBJECTPERMISSION_OBJECT_TYPES),
        help_text=_("Select the types of objects to which the permission will apply."),
    )
    can_view = forms.BooleanField(required=False)
    can_add = forms.BooleanField(required=False)
    can_change = forms.BooleanField(required=False)
    can_delete = forms.BooleanField(required=False)
    actions = JSONField(
        label=_("Additional actions"),
        required=False,
        help_text=_("JSON array of actions granted in addition to those listed above"),
    )
    users = DynamicModelMultipleChoiceField(
        label=_("Users"),
        required=False,
        queryset=User.objects.all(),
    )
    groups = DynamicModelMultipleChoiceField(
        label=_("Groups"),
        required=False,
        queryset=Group.objects.all(),
    )
    constraints = JSONField(
        required=False,
        label=_("Constraints"),
        help_text=_(
            "JSON expression of a queryset filter that will return only permitted objects. Leave null "
            "to match all objects of this type. A list of multiple objects will result in a logical OR "
            "operation."
        ),
    )

    fieldsets = (
        Fieldset(
            _("Permission"),
            "name",
            "description",
            "enabled",
        ),
        Fieldset(
            _("Actions"),
            "can_view",
            "can_add",
            "can_change",
            "can_delete",
            "actions",
        ),
        Fieldset(
            _("Objects"),
            "object_types",
        ),
        Fieldset(
            _("Assignment"),
            "groups",
            "users",
        ),
        Fieldset(
            _("Constraints"),
            "constraints",
        ),
    )

    class Meta:
        model = ObjectPermission
        fields = [
            "name",
            "description",
            "enabled",
            "object_types",
            "users",
            "groups",
            "constraints",
            "actions",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Build dynamic BooleanFields for registered actions (deduplicated, sorted by name)
        seen = {}
        for model_actions in registry["model_actions"].values():
            for action in model_actions:
                if action.name not in seen:
                    seen[action.name] = action
        registered_action_names = sorted(seen)

        action_field_names = []
        for action_name in registered_action_names:
            field_name = f"action_{action_name}"
            self.fields[field_name] = forms.BooleanField(
                required=False,
                label=action_name,
                help_text=seen[action_name].help_text,
            )
            action_field_names.append(field_name)

        # Rebuild the Actions fieldset to include dynamic fields
        if action_field_names:
            self.fieldsets = (
                Fieldset(
                    _("Permission"),
                    "name",
                    "description",
                    "enabled",
                ),
                Fieldset(
                    _("Actions"),
                    "can_view",
                    "can_add",
                    "can_change",
                    "can_delete",
                    *action_field_names,
                    "actions",
                ),
                Fieldset(
                    _("Objects"),
                    "object_types",
                ),
                Fieldset(
                    _("Assignment"),
                    "groups",
                    "users",
                ),
                Fieldset(
                    _("Constraints"),
                    "constraints",
                ),
            )

        # Make the actions field optional since the form uses it only for non-CRUD actions
        self.fields["actions"].required = False

        # Prepare the appropriate fields when editing an existing ObjectPermission
        if self.instance.pk:
            # Populate assigned users and groups
            self.fields["groups"].initial = self.instance.groups.values_list("id", flat=True)
            self.fields["users"].initial = self.instance.users.values_list("id", flat=True)

            # Work with a copy to avoid mutating the instance
            remaining_actions = list(self.instance.actions)

            # Check the appropriate CRUD checkboxes
            for action in RESERVED_ACTIONS:
                if action in remaining_actions:
                    self.fields[f"can_{action}"].initial = True
                    remaining_actions.remove(action)

            # Pre-select registered action checkboxes
            for action_name in registered_action_names:
                if action_name in remaining_actions:
                    self.fields[f"action_{action_name}"].initial = True
                    remaining_actions.remove(action_name)

            # Remaining actions go to the additional actions field
            self.initial["actions"] = remaining_actions

        # Populate initial data for a new ObjectPermission
        elif self.initial:
            # Handle cloned objects - actions come from initial data (URL parameters)
            if "actions" in self.initial:
                # Normalize actions to a list of strings
                if isinstance(self.initial["actions"], str):
                    self.initial["actions"] = [self.initial["actions"]]
                if cloned_actions := self.initial["actions"]:
                    for action in RESERVED_ACTIONS:
                        if action in cloned_actions:
                            self.fields[f"can_{action}"].initial = True
                            self.initial["actions"].remove(action)
                    # Pre-select registered action checkboxes from cloned data
                    for action_name in registered_action_names:
                        if action_name in cloned_actions:
                            self.fields[f"action_{action_name}"].initial = True
                            self.initial["actions"].remove(action_name)
            # Convert data delivered via initial data to JSON data
            if "constraints" in self.initial:
                if type(self.initial["constraints"]) is str:
                    self.initial["constraints"] = json.loads(self.initial["constraints"])

    def clean(self):
        super().clean()

        object_types = self.cleaned_data.get("object_types")
        constraints = self.cleaned_data.get("constraints")

        # Merge all actions: registered action checkboxes, CRUD checkboxes, and additional
        final_actions = []
        for key, value in self.cleaned_data.items():
            if key.startswith("action_") and value:
                action_name = key[7:]
                if action_name not in final_actions:
                    final_actions.append(action_name)

        for action in RESERVED_ACTIONS:
            if self.cleaned_data.get(f"can_{action}") and action not in final_actions:
                final_actions.append(action)

        if additional_actions := self.cleaned_data.get("actions"):
            for action in additional_actions:
                if action not in final_actions:
                    final_actions.append(action)

        self.cleaned_data["actions"] = final_actions

        # At least one action must be specified
        if not self.cleaned_data["actions"]:
            raise forms.ValidationError(_("At least one action must be selected."))

        # Validate the specified model constraints by attempting to execute a query. We don't care whether the query
        # returns anything; we just want to make sure the specified constraints are valid.
        if object_types and constraints:
            # Normalize the constraints to a list of dicts
            if type(constraints) is not list:
                constraints = [constraints]
            for ct in object_types:
                model = ct.model_class()

                try:
                    tokens = {
                        CONSTRAINT_TOKEN_USER: 0,  # Replace token with a null user ID
                    }
                    model.objects.filter(qs_filter_from_constraints(constraints, tokens)).exists()
                except (FieldError, ValueError, LookupError) as e:
                    raise forms.ValidationError(
                        {"constraints": _("Invalid filter for {model}: {error}").format(model=model, error=e)}
                    )

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        # Update assigned users and groups
        instance.users.set(self.cleaned_data["users"])
        instance.groups.set(self.cleaned_data["groups"])

        return instance


class RoleForm(HorizontalFormMixin, forms.ModelForm):
    object_permissions = DynamicModelMultipleChoiceField(
        required=False,
        label=_("Permissions"),
        queryset=ObjectPermission.objects.all(),
    )
    users = DynamicModelMultipleChoiceField(
        label=_("Users"),
        required=False,
        queryset=User.objects.all(),
    )
    groups = DynamicModelMultipleChoiceField(
        label=_("Groups"),
        required=False,
        queryset=Group.objects.all(),
    )

    fieldsets = (
        Fieldset(
            _("Role"),
            "name",
            "description",
            "weight",
        ),
        Fieldset(
            _("Permissions"),
            "object_permissions",
        ),
        Fieldset(
            _("Users"),
            "users",
        ),
        Fieldset(
            _("Groups"),
            "groups",
        ),
    )

    class Meta:
        model = Role
        fields = [
            "name",
            "description",
            "weight",
            "object_permissions",
            "users",
            "groups",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Populate assigned users, groups, and permissions when editing
        if self.instance.pk:
            self.fields["users"].initial = self.instance.users.values_list("id", flat=True)
            self.fields["groups"].initial = self.instance.groups.values_list("id", flat=True)

    def save(self, *args, **kwargs):
        instance = super().save(*args, **kwargs)

        # Update assigned users and groups
        instance.users.set(self.cleaned_data["users"])
        instance.groups.set(self.cleaned_data["groups"])

        return instance


class UserTokenForm(HorizontalFormMixin, forms.ModelForm):
    token = forms.CharField(
        label=_("Token"),
        help_text=_(
            "Tokens must be at least 40 characters in length. <strong>Be sure to record your token</strong> prior to "
            "submitting this form, as it will no longer be accessible once the token has been created."
        ),
    )

    fieldsets = (
        Layout(
            CopyClipboard("token"),
            "enabled",
            "write_enabled",
            DateTime("expires"),
            "description",
        ),
    )

    class Meta:
        model = Token
        fields = [
            "token",
            "enabled",
            "write_enabled",
            "expires",
            "description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.pk:
            # Omit the key field when editing an existing Token
            del self.fields["token"]
            self.fieldsets = (*self.fieldsets[1:],)

        # Generate an initial random key if none has been specified
        elif self.instance._state.adding and not self.initial.get("token"):
            self.initial["token"] = Token.generate()

    def save(self, commit=True):
        if self.instance._state.adding and self.cleaned_data.get("token"):
            self.instance.token = self.cleaned_data["token"]

        return super().save(commit=commit)


class TokenForm(UserTokenForm):
    user = forms.ModelChoiceField(
        queryset=User.objects.order_by("username"),
        label=_("User"),
    )

    fieldsets = (
        Layout(
            CopyClipboard("token"),
            "user",
            "enabled",
            "write_enabled",
            DateTime("expires"),
            "description",
        ),
    )

    class Meta(UserTokenForm.Meta):
        model = Token
        fields = [
            "token",
            "user",
            "enabled",
            "write_enabled",
            "expires",
            "description",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # If not creating a new Token, disable the user field
        if self.instance and not self.instance._state.adding:
            self.fields["user"].disabled = True
