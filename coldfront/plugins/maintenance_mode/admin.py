# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from coldfront.plugins.maintenance_mode.models import MaintenanceEvent


@admin.register(MaintenanceEvent)
class MaintenanceEventAdmin(admin.ModelAdmin):
    list_display = (
        "start_time",
        "end_time",
        "stop_tasks",
        "is_stopped",
        "extension",
        "message",
    )
    list_filter = (
        "start_time",
        "end_time",
        "stop_tasks",
        "is_stopped",
    )
    search_fields = ["message"]
