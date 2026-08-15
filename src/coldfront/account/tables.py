# SPDX-FileCopyrightText: (C) University at Buffalo
#
# SPDX-License-Identifier: Apache-2.0

import django_tables2 as tables
from django.utils.translation import gettext_lazy as _
from generic_notifications.models import Notification as GenericNotification

from coldfront.tables import ColdFrontTable, columns
from coldfront.users.tables import TokenTable

from .models import UserToken


class UserTokenTable(TokenTable):
    class Meta(TokenTable.Meta):
        model = UserToken


class NotificationTable(ColdFrontTable):
    actions = None
    extra_buttons = None

    subject = tables.Column(
        verbose_name=_("Subject"),
        linkify=True,
    )
    text = tables.Column(
        verbose_name=_("Message"),
        linkify=("account:notification", {"pk": tables.A("id")}),
    )
    added = columns.DateTimeColumn(
        verbose_name=_("Added"),
        timespec="minutes",
    )
    read = tables.TemplateColumn(
        template_code='{% load humanize %}{% if value %}{{ value|naturaltime }}{% else %}{% cotton ui.badge bg_color="primary" value="New" /%}{% endif %}',
        verbose_name=_("Read"),
    )
    notification_type = tables.Column(
        verbose_name=_("Type"),
    )

    class Meta(ColdFrontTable.Meta):
        model = GenericNotification
        order_by = "read"
        fields = (
            "pk",
            "id",
            "subject",
            "text",
            "notification_type",
            "added",
            "read",
        )
        default_columns = (
            "pk",
            "read",
            "subject",
            "text",
            "notification_type",
            "added",
        )
