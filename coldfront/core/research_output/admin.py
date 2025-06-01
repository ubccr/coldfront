# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib import admin
from simple_history.admin import SimpleHistoryAdmin

from coldfront.core.research_output.models import ResearchOutput

_research_output_fields_for_end = ["created_by", "project", "created", "modified"]


@admin.register(ResearchOutput)
class ResearchOutputAdmin(SimpleHistoryAdmin):
    list_display = [
        field.name for field in ResearchOutput._meta.get_fields() if field.name not in _research_output_fields_for_end
    ] + _research_output_fields_for_end
    list_filter = (
        "project",
        "created_by",
    )
    ordering = (
        "project",
        "-created",
    )

    # display the noneditable fields on the "change" form
    readonly_fields = [field.name for field in ResearchOutput._meta.get_fields() if not field.editable]

    # the view implements some Add logic that we need not replicate here
    # to simplify: remove ability to add via admin interface
    def has_add_permission(self, request):
        return False
