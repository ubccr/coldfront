# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from crispy_forms.layout import Fieldset
from django import forms
from django.utils.translation import gettext_lazy as _

from coldfront.forms import ColdFrontModelFilterSetForm, ColdFrontModelForm, CSVModelForm
from coldfront.forms.fields import CSVModelChoiceField
from coldfront.ras.models import Project, ProjectInvite

__all__ = (
    "ProjectInviteForm",
    "ProjectInviteImportForm",
    "ProjectInviteFilterSetForm",
)

# Display-only statuses for the filter tab. These are never stored; they are
# computed from `created` + INVITE_CODE_EXPIRE_SECONDS and `accepted_at`.
PROJECT_INVITE_STATUS_CHOICES = (
    ("pending", _("Pending")),
    ("expired", _("Expired")),
    ("accepted", _("Accepted")),
)


class ProjectInviteForm(ColdFrontModelForm):
    """Create/edit a single project invite (one email address per invite)."""

    project = forms.ModelChoiceField(
        label=_("Project"),
        queryset=Project.objects.all(),
        required=True,
    )

    class Meta:
        model = ProjectInvite
        fields = [
            "email",
            "project",
        ]

    fieldsets = (
        Fieldset(
            _("Project Invite"),
            "email",
            "project",
        ),
    )


class ProjectInviteImportForm(CSVModelForm):
    """Bulk-import project invites from CSV (email,project columns)."""

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
        model = ProjectInvite
        fields = [
            "email",
            "project",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields.pop("id", None)


class ProjectInviteFilterSetForm(ColdFrontModelFilterSetForm):
    model = ProjectInvite
    project_id = forms.ModelChoiceField(
        queryset=Project.objects.all(),
        required=False,
        label=_("Project"),
    )
    status = forms.ChoiceField(
        choices=PROJECT_INVITE_STATUS_CHOICES,
        required=False,
        label=_("Status"),
    )

    fieldsets = (
        Fieldset(
            _("Invite"),
            "project_id",
            "status",
        ),
    )
