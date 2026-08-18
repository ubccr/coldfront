# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_filters
from django.utils.translation import gettext as _

from coldfront.ras.models import Project, ProjectInvite
from coldfront.views.filtersets import ChangeLoggedModelFilterSet

__all__ = ("ProjectInviteFilterSet",)


class ProjectInviteFilterSet(ChangeLoggedModelFilterSet):
    project_id = django_filters.ModelChoiceFilter(
        queryset=Project.objects.all(),
        label=_("Project"),
    )

    status = django_filters.ChoiceFilter(
        choices=[
            ("pending", _("Pending")),
            ("expired", _("Expired")),
            ("accepted", _("Accepted")),
        ],
        method="filter_status",
        label=_("Status"),
    )

    class Meta:
        model = ProjectInvite
        fields = (
            "id",
            "email",
            "project_id",
            "created",
            "modified",
        )

    def filter_status(self, queryset, name, value):
        """Filter by the computed invite status (never stored)."""
        return {
            "pending": queryset.pending(),
            "expired": queryset.expired(),
            "accepted": queryset.accepted(),
        }.get(value, queryset)
