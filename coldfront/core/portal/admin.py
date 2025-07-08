# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib import admin
from django.contrib.admin.models import LogEntry


@admin.register(LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    list_display = (
        "content_type",
        "user",
        "action_time",
        "object_id",
        "object_repr",
        "action_flag",
        "change_message",
    )

    search_fields = ["user__username", "user__first_name", "user__last_name"]
