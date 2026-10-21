# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _

from coldfront.lib.forms import (
    OrganizationalModelForm,
    PrimaryModelForm,
    PrimaryModelImportForm,
    TenancyForm,
    TenancyImportForm,
    get_field_value,
)
from coldfront.lib.forms.fields import CSVModelChoiceField, DynamicModelChoiceField
from coldfront.lib.forms.layout import FieldSet
from coldfront.ras.models import Project, ProjectUser
from coldfront.users.models import Group, User


class ProjectForm(TenancyForm, OrganizationalModelForm):
    class Meta:
        model = Project
        fields = [
            "name",
            "slug",
            "description",
            "group",
            "tags",
            "tenant",
            "tenant_group",
        ]

    fieldsets = (
        FieldSet(
            "name",
            "slug",
            "description",
            "group",
            name=_("Project"),
        ),
        FieldSet(
            "tenant_group",
            "tenant",
            name=_("Tenant"),
        ),
        FieldSet(
            "tags",
            name=_("Tags"),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only admins can modify slug
        if hasattr(self, "user") and self.user and self.user.is_authenticated and self.user.is_superuser:
            return

        self.fields["slug"].widget.attrs["disabled"] = "disabled"
        self.fields["slug"].required = False
        self.fields["slug"].disabled = True


class ProjectUserForm(PrimaryModelForm):
    user = DynamicModelChoiceField(
        label=_("User"),
        queryset=User.objects.all(),
        required=True,
        selector=True,
        context={
            "label": "username",
            "title": "Username,First Name,Last Name,Email",
            "extra-columns": "first_name,last_name,email",
        },
    )

    class Meta:
        model = ProjectUser
        fields = [
            "project",
            "user",
        ]

    fieldsets = (
        FieldSet(
            "project",
            "user",
            name=_("Project User"),
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if project_id := get_field_value(self, "project"):
            try:
                Project.objects.get(pk=project_id)
                self.fields["project"].widget.attrs["data-readonly"] = "readonly"
            except ObjectDoesNotExist:
                pass


class ProjectImportForm(TenancyImportForm, PrimaryModelImportForm):
    owner = CSVModelChoiceField(
        label=_("Owner"),
        queryset=User.objects.all(),
        required=True,
        to_field_name="username",
        help_text=_("Owner of the project"),
        error_messages={
            "invalid_choice": _("User not found."),
        },
    )

    group = CSVModelChoiceField(
        label=_("Group"),
        queryset=Group.objects.all(),
        required=False,
        to_field_name="name",
        help_text=_("Group that maps to this project"),
    )

    class Meta:
        model = Project
        fields = [
            "name",
            "owner",
            "description",
            "group",
            "tags",
            "tenant",
        ]


class ProjectUserImportForm(PrimaryModelImportForm):
    user = CSVModelChoiceField(
        label=_("User"),
        queryset=User.objects.all(),
        required=True,
        to_field_name="username",
        help_text=_("User to add to project"),
        error_messages={
            "invalid_choice": _("User not found."),
        },
    )

    project = CSVModelChoiceField(
        label=_("Project"),
        queryset=Project.objects.all(),
        required=True,
        to_field_name="name",
        error_messages={
            "invalid_choice": _("Project not found."),
        },
    )

    class Meta:
        model = ProjectUser
        fields = [
            "user",
            "project",
        ]
