# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_tables2 as tables
from django.utils.html import format_html
from django.utils.translation import gettext as _

from coldfront.ras.models import ProjectInvite
from coldfront.tables import ColdFrontTable, columns


class ProjectInviteStatusColumn(tables.Column):
    """
    Render the computed invite status (pending/expired/accepted) as a colored
    badge. The status is never stored; it is derived from `get_status()`.
    """

    empty_values = ()

    def render(self, record, bound_column, value):
        status = record.get_status()
        colors = {
            "pending": "info",
            "expired": "warning",
            "accepted": "success",
        }
        labels = {
            "pending": _("Pending"),
            "expired": _("Expired"),
            "accepted": _("Accepted"),
        }
        return format_html(
            '<span class="badge text-bg-{}">{}</span>',
            colors.get(status, "secondary"),
            labels.get(status, status),
        )

    def value(self, value):
        return value


class ProjectInviteTable(ColdFrontTable):
    project = tables.Column(
        verbose_name=_("Project"),
        linkify=True,
    )

    email = tables.Column(
        verbose_name=_("Email"),
        linkify=True,
    )

    status = ProjectInviteStatusColumn(
        verbose_name=_("Status"),
        orderable=False,
    )

    created = tables.Column(
        verbose_name=_("Created"),
    )

    invited_by = tables.Column(
        verbose_name=_("Invited By"),
        linkify=True,
    )
    actions = columns.ActionsColumn(actions=("delete",), split_actions=False)

    class Meta(ColdFrontTable.Meta):
        model = ProjectInvite
        fields = (
            "pk",
            "id",
            "email",
            "project",
            "status",
            "invited_by",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "email", "project", "status")
