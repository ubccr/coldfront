# SPDX-FileCopyrightText: (C) ColdFront Authors
#
# SPDX-License-Identifier: AGPL-3.0-or-later

from django.contrib import admin

from coldfront.core.tag.models import Tag


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    add_form_template = "tag/admin/add_form.html"

    fields_change = (
        "parent_tag",
        "name",
        "allowed_models",
        "html_classes",
    )
    list_display = (
        "name",
        "parent_tag",
        "created",
        "modified",
    )
    filter_horizontal = [
        "allowed_models",
    ]
    search_fields = ("name",)
