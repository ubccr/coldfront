# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

from urllib.parse import quote

import django_tables2 as tables
from django.utils.translation import gettext_lazy as _
from django_cotton import render_component

from coldfront.ras.flows import get_permitted_transition_actions
from coldfront.ras.models import Allocation
from coldfront.tables import PrimaryModelTable, columns
from coldfront.tenancy.tables import TenancyColumnsMixin

ALLOWED_TABLE_BUTTONS = {"approve", "deny", "activate"}


def _render_table_action_buttons(record, user, request):
    """
    Render approve/deny/activate buttons for an allocation row.
    """
    actions = get_permitted_transition_actions(record, user)
    html = ""
    return_url = quote(request.get_full_path())

    for action in actions:
        if action.name not in ALLOWED_TABLE_BUTTONS:
            continue
        url = action.get_url(record)
        if not url:
            continue
        url += f"?return_url={return_url}"
        html += render_component(
            request,
            action.template_name,
            url=url,
            title=action.label,
            small=True,
            type="link",
        )

    return html


class AllocationTable(TenancyColumnsMixin, PrimaryModelTable):
    actions = columns.ActionsColumn(
        extra_buttons=_render_table_action_buttons,
    )

    slug = tables.Column(
        verbose_name=_("Allocation"),
        linkify=True,
    )

    project = tables.Column(
        verbose_name=_("Project"),
        linkify=True,
    )
    owner = tables.Column(
        verbose_name=_("Owner"),
    )

    resource_object = tables.Column(
        verbose_name=_("Resource"),
        linkify=True,
        accessor=tables.A("resource_object"),
        order_by=("resource_object_type__model", "resource_object_id"),
    )

    start_date = columns.DateColumn(
        verbose_name=_("Start Date"),
    )

    end_date = columns.DateColumn(
        verbose_name=_("End Date"),
    )

    status = columns.ChoiceFieldColumn(
        verbose_name=_("Status"),
    )

    tags = columns.TagColumn(
        url_name="ras:allocation_list",
    )

    class Meta(PrimaryModelTable.Meta):
        model = Allocation
        fields = (
            "pk",
            "id",
            "slug",
            "project",
            "owner",
            "resource_object",
            "status",
            "description",
            "justification",
            "tags",
            "tenant_group",
            "tenant",
            "start_date",
            "end_date",
            "created",
            "last_updated",
        )
        default_columns = ("pk", "slug", "resource_object", "owner", "project", "status", "start_date", "end_date")
