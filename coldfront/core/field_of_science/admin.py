# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib import admin

from coldfront.core.field_of_science.models import FieldOfScience


@admin.register(FieldOfScience)
class FieldOfScienceAdmin(admin.ModelAdmin):
    list_display = (
        "description",
        "is_selectable",
        "parent_id",
        "fos_nsf_id",
        "fos_nsf_abbrev",
        "directorate_fos_id",
    )
    list_filter = ("is_selectable",)
    search_fields = ["description"]
