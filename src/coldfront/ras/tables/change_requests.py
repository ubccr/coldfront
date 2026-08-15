# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from coldfront.ras.models.change_requests import AllocationChangeRequest
from coldfront.tables import PrimaryModelTable, columns


class AllocationChangeRequestTable(PrimaryModelTable):
    slug = tables.Column(
        verbose_name=_("Change Request"),
        linkify=True,
    )
    allocation = tables.Column(
        verbose_name=_("Allocation"),
        linkify=True,
    )
    status = columns.ChoiceFieldColumn(
        verbose_name=_("Status"),
    )
    requested_by = tables.Column(
        verbose_name=_("Requested by"),
    )
    reviewer = tables.Column(
        verbose_name=_("Reviewer"),
    )

    class Meta(PrimaryModelTable.Meta):
        model = AllocationChangeRequest
        fields = (
            "pk",
            "slug",
            "allocation",
            "status",
            "requested_by",
            "reviewer",
            "justification",
            "created",
            "last_updated",
        )
        default_columns = (
            "pk",
            "slug",
            "allocation",
            "status",
            "requested_by",
            "reviewer",
            "created",
            "last_updated",
        )
